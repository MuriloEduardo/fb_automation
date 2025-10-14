"""
Comando para listar e executar tasks do Celery Beat
"""

from django.core.management.base import BaseCommand
from fb_automation.celery import app


class Command(BaseCommand):
    help = "Gerenciar tasks agendadas do Celery Beat"

    def add_arguments(self, parser):
        parser.add_argument(
            "--list",
            action="store_true",
            help="Listar todas as tasks agendadas",
        )
        parser.add_argument(
            "--execute",
            type=str,
            help="Executar uma task específica (nome da task)",
        )

    def handle(self, *args, **options):
        if options["list"]:
            self.list_scheduled_tasks()
        elif options["execute"]:
            self.execute_task(options["execute"])
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Use --list para listar ou --execute <task_name> para executar"
                )
            )

    def list_scheduled_tasks(self):
        """Lista todas as tasks agendadas"""
        self.stdout.write(self.style.SUCCESS("\n📋 Tasks Agendadas no Celery Beat:\n"))

        if not app.conf.beat_schedule:
            self.stdout.write(self.style.WARNING("Nenhuma task agendada configurada."))
            return

        for task_name, task_config in app.conf.beat_schedule.items():
            self.stdout.write(f"\n🔹 {task_name}")
            self.stdout.write(f"   Task: {task_config['task']}")

            schedule = task_config["schedule"]
            if hasattr(schedule, "__str__"):
                self.stdout.write(f"   Agendamento: {schedule}")

            if "kwargs" in task_config and task_config["kwargs"]:
                self.stdout.write(f"   Argumentos: {task_config['kwargs']}")

        self.stdout.write("\n")

    def execute_task(self, task_name):
        """Executa uma task específica"""
        from facebook_integration import tasks

        # Mapeamento de tasks disponíveis
        available_tasks = {
            "sync_metrics": tasks.sync_facebook_metrics,
            "check_scheduled": tasks.check_and_publish_scheduled_posts,
            "cleanup_metrics": tasks.cleanup_old_metrics,
            "process_scheduled": tasks.process_scheduled_posts,
        }

        if task_name not in available_tasks:
            self.stdout.write(
                self.style.ERROR(f'\n❌ Task "{task_name}" não encontrada.')
            )
            self.stdout.write("\nTasks disponíveis:")
            for name in available_tasks.keys():
                self.stdout.write(f"  - {name}")
            return

        self.stdout.write(self.style.WARNING(f"\n🚀 Executando task: {task_name}...\n"))

        try:
            task_func = available_tasks[task_name]

            # Executar task de forma assíncrona
            if task_name == "cleanup_metrics":
                result = task_func.delay(days_to_keep=90)
            else:
                result = task_func.delay()

            self.stdout.write(
                self.style.SUCCESS(f"✅ Task enfileirada com ID: {result.id}")
            )
            self.stdout.write(
                "Use Flower (http://localhost:5555) para monitorar o progresso.\n"
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Erro ao executar task: {e}\n"))
