from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from celery import current_app
from celery.result import AsyncResult
import json


class CeleryTask(models.Model):
    """Modelo para rastrear tasks do Celery"""

    TASK_STATUS_CHOICES = [
        ("PENDING", "Pendente"),
        ("RECEIVED", "Recebido"),
        ("STARTED", "Iniciado"),
        ("SUCCESS", "Sucesso"),
        ("FAILURE", "Falha"),
        ("RETRY", "Tentando Novamente"),
        ("REVOKED", "Revogado"),
    ]

    task_id = models.CharField(max_length=255, unique=True, verbose_name="ID da Task")
    task_name = models.CharField(max_length=255, verbose_name="Nome da Task")
    status = models.CharField(
        max_length=20,
        choices=TASK_STATUS_CHOICES,
        default="PENDING",
        verbose_name="Status",
    )

    # Parâmetros da task
    args = models.TextField(blank=True, verbose_name="Argumentos")
    kwargs = models.TextField(blank=True, verbose_name="Parâmetros")

    # Resultado
    result = models.TextField(blank=True, verbose_name="Resultado")
    traceback = models.TextField(blank=True, verbose_name="Erro")

    # Metadados
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Iniciado em")
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Finalizado em"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    # Relacionamentos
    scheduled_post = models.ForeignKey(
        "ScheduledPost",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Post Agendado",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Criado por",
    )

    class Meta:
        verbose_name = "Task do Celery"
        verbose_name_plural = "Tasks do Celery"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.task_name} - {self.status}"

    def update_from_celery(self):
        """Atualiza status da task consultando o Celery"""
        try:
            result = AsyncResult(self.task_id)
            self.status = result.status

            if result.successful():
                self.result = str(result.result)
                self.completed_at = timezone.now()
            elif result.failed():
                self.traceback = str(result.traceback)
                self.completed_at = timezone.now()

            self.save()
            return True
        except Exception as e:
            return False

    @property
    def duration(self):
        """Duração da execução da task"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def is_running(self):
        """Verifica se a task está executando"""
        return self.status in ["PENDING", "RECEIVED", "STARTED"]


class CeleryWorker(models.Model):
    """Modelo para monitorar workers do Celery"""

    hostname = models.CharField(max_length=255, unique=True, verbose_name="Hostname")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    # Estatísticas
    total_tasks = models.IntegerField(default=0, verbose_name="Total de Tasks")
    active_tasks = models.IntegerField(default=0, verbose_name="Tasks Ativas")
    processed_tasks = models.IntegerField(default=0, verbose_name="Tasks Processadas")

    # Metadados
    last_heartbeat = models.DateTimeField(
        auto_now=True, verbose_name="Último Heartbeat"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Worker do Celery"
        verbose_name_plural = "Workers do Celery"
        ordering = ["-last_heartbeat"]

    def __str__(self):
        return f"{self.hostname} ({'Ativo' if self.is_active else 'Inativo'})"

    @classmethod
    def update_workers_status(cls):
        """Atualiza status de todos os workers"""
        try:
            inspect = current_app.control.inspect()
            active_workers = inspect.active()

            if active_workers:
                for hostname, tasks in active_workers.items():
                    worker, created = cls.objects.get_or_create(
                        hostname=hostname, defaults={"is_active": True}
                    )
                    worker.is_active = True
                    worker.active_tasks = len(tasks)
                    worker.save()

                # Marcar workers inativos
                active_hostnames = list(active_workers.keys())
                cls.objects.exclude(hostname__in=active_hostnames).update(
                    is_active=False
                )

            return True
        except Exception as e:
            return False


class CeleryTaskTemplate(models.Model):
    """Templates para executar tasks comuns"""

    name = models.CharField(max_length=255, verbose_name="Nome")
    task_name = models.CharField(max_length=255, verbose_name="Nome da Task")
    description = models.TextField(verbose_name="Descrição")

    # Parâmetros padrão
    default_args = models.TextField(
        blank=True,
        help_text="JSON com argumentos padrão",
        verbose_name="Argumentos Padrão",
    )
    default_kwargs = models.TextField(
        blank=True,
        help_text="JSON com parâmetros padrão",
        verbose_name="Parâmetros Padrão",
    )

    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Template de Task"
        verbose_name_plural = "Templates de Tasks"

    def __str__(self):
        return self.name

    def execute(self, custom_args=None, custom_kwargs=None):
        """Executa a task com os parâmetros definidos"""
        try:
            # Combinar argumentos padrão com customizados
            args = json.loads(self.default_args) if self.default_args else []
            kwargs = json.loads(self.default_kwargs) if self.default_kwargs else {}

            if custom_args:
                args.extend(custom_args)
            if custom_kwargs:
                kwargs.update(custom_kwargs)

            # Executar task
            task = current_app.send_task(self.task_name, args=args, kwargs=kwargs)

            # Registrar no banco
            CeleryTask.objects.create(
                task_id=task.id,
                task_name=self.task_name,
                args=json.dumps(args),
                kwargs=json.dumps(kwargs),
            )

            return task
        except Exception as e:
            return None
