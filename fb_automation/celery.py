import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Define o módulo de configurações Django para o Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fb_automation.settings")

app = Celery("fb_automation")

# Usa a configuração do Django
app.config_from_object("django.conf:settings", namespace="CELERY")

# Descobre tasks automaticamente
app.autodiscover_tasks()

# Agendamento de tarefas periódicas
app.conf.beat_schedule = {
    # Sincronizar métricas do Facebook a cada 6 horas
    "sync-facebook-metrics-every-6h": {
        "task": "facebook_integration.tasks.sync_facebook_metrics",
        "schedule": crontab(minute=0, hour="*/6"),  # 00:00, 06:00, 12:00, 18:00
        "kwargs": {},  # Sincroniza todas as páginas
    },
    # Processar posts agendados a cada 5 minutos
    "check-scheduled-posts": {
        "task": "facebook_integration.tasks.check_and_publish_scheduled_posts",
        "schedule": crontab(minute="*/5"),  # A cada 5 minutos
    },
    # Limpar posts antigos (opcional) - 1x por semana
    "cleanup-old-metrics": {
        "task": "facebook_integration.tasks.cleanup_old_metrics",
        "schedule": crontab(minute=0, hour=3, day_of_week=1),  # Segunda às 03:00
        "kwargs": {"days_to_keep": 90},  # Manter últimos 90 dias
    },
}

# Configurações adicionais do Celery Beat
app.conf.timezone = "America/Sao_Paulo"


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
