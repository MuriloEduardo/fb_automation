import os
from celery import Celery
from django.conf import settings

# Define o módulo de configurações Django para o Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fb_automation.settings")

app = Celery("fb_automation")

# Usa a configuração do Django
app.config_from_object("django.conf:settings", namespace="CELERY")

# Descobre tasks automaticamente
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
