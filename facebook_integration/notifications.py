"""
Sistema de notificações por email para alertas e relatórios
"""

import logging
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


def send_task_failure_notification(
    task_name, task_id, error_message, scheduled_post=None
):
    """
    Envia notificação quando uma task falha

    Args:
        task_name: Nome da task que falhou
        task_id: ID da task
        error_message: Mensagem de erro
        scheduled_post: Post agendado relacionado (opcional)
    """
    if not _should_send_email():
        logger.info("Email desabilitado - notificação ignorada")
        return False

    subject = f"❌ Task Failed: {task_name}"

    message = f"""
Task Failure Alert
==================

Task: {task_name}
Task ID: {task_id}
Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

Error Message:
{error_message}

"""

    if scheduled_post:
        message += f"""
Scheduled Post Details:
- ID: {scheduled_post.id}
- Page: {scheduled_post.facebook_page.name}
- Scheduled Time: {scheduled_post.scheduled_time}
- Status: {scheduled_post.status}
"""

    message += f"""
---
Facebook Automation System
{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'}
"""

    try:
        recipient_list = _get_admin_emails()
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
        logger.info(
            f"Notificação de falha enviada para {len(recipient_list)} destinatários"
        )
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar notificação de falha: {e}")
        return False


def send_daily_summary_email():
    """
    Envia resumo diário das atividades do sistema
    """
    if not _should_send_email():
        logger.info("Email desabilitado - resumo diário ignorado")
        return False

    from facebook_integration.models import PublishedPost, ScheduledPost

    today = timezone.now().date()
    yesterday = today - timedelta(days=1)

    # Estatísticas de ontem
    published_yesterday = PublishedPost.objects.filter(
        published_at__date=yesterday
    ).count()

    scheduled_today = ScheduledPost.objects.filter(
        scheduled_time__date=today, status__in=["pending", "ready"]
    ).count()

    failed_yesterday = ScheduledPost.objects.filter(
        updated_at__date=yesterday, status="failed"
    ).count()

    # Posts mais populares de ontem
    top_posts = PublishedPost.objects.filter(published_at__date=yesterday).order_by(
        "-likes_count"
    )[:5]

    subject = f"📊 Daily Summary - {yesterday.strftime('%d/%m/%Y')}"

    message = f"""
Daily Summary Report
====================
Date: {yesterday.strftime('%d/%m/%Y')}

📈 Statistics:
• Posts Published: {published_yesterday}
• Posts Scheduled for Today: {scheduled_today}
• Failed Posts: {failed_yesterday}

"""

    if top_posts:
        message += "🏆 Top Posts (by likes):\n"
        for i, post in enumerate(top_posts, 1):
            message += f"{i}. {post.facebook_page.name} - {post.likes_count} likes\n"
            message += f"   {post.content[:80]}...\n\n"

    message += f"""
---
Facebook Automation System
{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'}
"""

    try:
        recipient_list = _get_admin_emails()
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
        logger.info(f"Resumo diário enviado para {len(recipient_list)} destinatários")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar resumo diário: {e}")
        return False


def send_post_published_notification(published_post):
    """
    Envia notificação quando um post é publicado com sucesso

    Args:
        published_post: Instância de PublishedPost
    """
    if not _should_send_email():
        return False

    subject = f"✅ Post Published: {published_post.facebook_page.name}"

    message = f"""
Post Published Successfully
==========================

Page: {published_post.facebook_page.name}
Published: {published_post.published_at.strftime('%Y-%m-%d %H:%M:%S')}
Facebook URL: {published_post.facebook_post_url or 'N/A'}

Content:
{published_post.content[:200]}{'...' if len(published_post.content) > 200 else ''}

Current Metrics:
• Likes: {published_post.likes_count}
• Comments: {published_post.comments_count}
• Shares: {published_post.shares_count}

---
Facebook Automation System
"""

    try:
        recipient_list = _get_admin_emails()
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=True,  # Não falhar se email não funcionar
        )
        logger.info(f"Notificação de publicação enviada")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar notificação de publicação: {e}")
        return False


def send_metrics_alert(
    page_name, metric_name, current_value, threshold, comparison="below"
):
    """
    Envia alerta quando uma métrica atinge um threshold

    Args:
        page_name: Nome da página
        metric_name: Nome da métrica (ex: 'followers', 'engagement_rate')
        current_value: Valor atual da métrica
        threshold: Limite configurado
        comparison: 'below' ou 'above'
    """
    if not _should_send_email():
        return False

    emoji = "⚠️" if comparison == "below" else "🎉"
    direction = "fell below" if comparison == "below" else "exceeded"

    subject = f"{emoji} Metric Alert: {page_name} - {metric_name}"

    message = f"""
Metric Alert
============

Page: {page_name}
Metric: {metric_name}
Current Value: {current_value}
Threshold: {threshold}

The metric has {direction} the configured threshold.

Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

---
Facebook Automation System
"""

    try:
        recipient_list = _get_admin_emails()
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=True,
        )
        logger.info(f"Alerta de métrica enviado para {page_name}")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar alerta de métrica: {e}")
        return False


def _should_send_email():
    """Verifica se o email está configurado e habilitado"""
    return (
        hasattr(settings, "EMAIL_HOST")
        and settings.EMAIL_HOST
        and hasattr(settings, "EMAIL_NOTIFICATIONS_ENABLED")
        and settings.EMAIL_NOTIFICATIONS_ENABLED
    )


def _get_admin_emails():
    """Retorna lista de emails dos administradores"""
    if hasattr(settings, "ADMIN_EMAILS") and settings.ADMIN_EMAILS:
        return settings.ADMIN_EMAILS

    # Fallback para ADMINS do Django
    if hasattr(settings, "ADMINS") and settings.ADMINS:
        return [email for name, email in settings.ADMINS]

    # Fallback padrão
    return ["admin@localhost"]


def test_email_configuration():
    """
    Testa a configuração de email enviando um email de teste
    """
    if not _should_send_email():
        return {"success": False, "message": "Email não configurado ou desabilitado"}

    try:
        send_mail(
            "Test Email - Facebook Automation",
            "This is a test email from the Facebook Automation system.",
            settings.DEFAULT_FROM_EMAIL,
            _get_admin_emails(),
            fail_silently=False,
        )
        return {
            "success": True,
            "message": f"Email de teste enviado para {_get_admin_emails()}",
        }
    except Exception as e:
        return {"success": False, "message": f"Erro ao enviar email: {str(e)}"}
