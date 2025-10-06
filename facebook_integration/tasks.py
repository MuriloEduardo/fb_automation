import re
import logging
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth.models import User
from .models import ScheduledPost, PublishedPost, FacebookPage, PostTemplate
from .services.facebook_api import FacebookAPIClient, FacebookAPIException
from .services.openai_service import OpenAIService, OpenAIServiceException

logger = logging.getLogger(__name__)


def register_task(task_instance, scheduled_post=None, user=None):
    """Registra uma task no sistema de monitoramento"""
    try:
        from .models_celery import CeleryTask

        CeleryTask.objects.create(
            task_id=task_instance.id,
            task_name=task_instance.name,
            status="PENDING",
            scheduled_post=scheduled_post,
            created_by=user,
        )
    except Exception as e:
        logger.warning(f"Erro ao registrar task: {e}")


@shared_task(bind=True)
def process_scheduled_posts(self):
    """Processa posts que estão prontos para serem publicados"""
    # Registrar task
    register_task(self)

    due_posts = ScheduledPost.objects.filter(
        status="ready", scheduled_time__lte=timezone.now()
    )

    processed_count = 0
    for post in due_posts:
        try:
            # Atualiza status para publishing
            post.status = "publishing"
            post.save()

            # Publica o post
            result = publish_post_task.delay(post.id)
            register_task(result, scheduled_post=post)
            processed_count += 1

        except Exception as e:
            logger.error(f"Erro ao processar post {post.id}: {e}")
            post.status = "failed"
            post.error_message = str(e)
            post.save()

    return f"Processados {processed_count} posts"


@shared_task(bind=True)
def generate_content_for_post(self, post_id):
    """Gera conteúdo para um post agendado usando IA"""
    try:
        post = ScheduledPost.objects.get(id=post_id)

        # Registrar task
        register_task(self, scheduled_post=post)

        # Atualiza status
        post.status = "generating"
        post.save()

        # Gera conteúdo usando OpenAI
        openai_service = OpenAIService()

        # Contexto baseado na página e template
        context = {
            "page_name": post.facebook_page.name,
            "category": post.template.category,
            "current_time": timezone.now().strftime("%Y-%m-%d %H:%M"),
        }

        # Gera conteúdo
        content = openai_service.generate_post_content(post.template.prompt, context)

        # Gera prompt para imagem (opcional)
        image_prompt = openai_service.generate_image_prompt(content)

        # Salva o conteúdo gerado
        post.generated_content = content
        post.generated_image_prompt = image_prompt
        post.status = "ready"
        post.save()

        logger.info(f"Conteúdo gerado para post {post_id}")
        return f"Conteúdo gerado para post {post_id}"

    except ScheduledPost.DoesNotExist:
        logger.error(f"Post {post_id} não encontrado")
        return f"Post {post_id} não encontrado"

    except OpenAIServiceException as e:
        logger.error(f"Erro na IA para post {post_id}: {e}")
        post.status = "failed"
        post.error_message = f"Erro na IA: {str(e)}"
        post.save()
        return f"Erro na IA para post {post_id}"


@shared_task
def publish_post_task(post_id):
    """Publica um post no Facebook"""
    try:
        post = ScheduledPost.objects.get(id=post_id)

        if not post.generated_content:
            raise ValueError("Post não tem conteúdo gerado")

        # Cliente do Facebook
        facebook_client = FacebookAPIClient(
            access_token=post.facebook_page.access_token,
            page_id=post.facebook_page.page_id,
        )

        # Publica o post
        result = facebook_client.create_post(message=post.generated_content)

        # Extrai informações do resultado
        facebook_post_id = result.get("id")
        facebook_post_url = f"https://facebook.com/{facebook_post_id}"

        # Atualiza o post agendado
        post.status = "published"
        post.facebook_post_id = facebook_post_id
        post.facebook_post_url = facebook_post_url
        post.save()

        # Cria registro do post publicado
        PublishedPost.objects.create(
            facebook_page=post.facebook_page,
            scheduled_post=post,
            content=post.generated_content,
            facebook_post_id=facebook_post_id,
            facebook_post_url=facebook_post_url,
        )

        logger.info(f"Post {post_id} publicado com sucesso: {facebook_post_id}")
        return f"Post {post_id} publicado: {facebook_post_id}"

    except ScheduledPost.DoesNotExist:
        logger.error(f"Post {post_id} não encontrado")
        return f"Post {post_id} não encontrado"

    except FacebookAPIException as e:
        logger.error(f"Erro do Facebook para post {post_id}: {e}")
        post.status = "failed"
        post.error_message = f"Erro do Facebook: {str(e)}"
        post.save()
        return f"Erro do Facebook para post {post_id}"

    except Exception as e:
        logger.error(f"Erro geral para post {post_id}: {e}")
        post.status = "failed"
        post.error_message = str(e)
        post.save()
        return f"Erro para post {post_id}: {str(e)}"


@shared_task
def update_post_metrics():
    """Atualiza métricas dos posts publicados"""
    recent_posts = PublishedPost.objects.filter(
        published_at__gte=timezone.now() - timezone.timedelta(days=30)
    ).order_by("-published_at")[
        :50
    ]  # Últimos 50 posts do mês

    updated_count = 0

    for published_post in recent_posts:
        try:
            facebook_client = FacebookAPIClient(
                access_token=published_post.facebook_page.access_token,
                page_id=published_post.facebook_page.page_id,
            )

            # Obtém detalhes do post
            post_details = facebook_client.get_post_details(
                published_post.facebook_post_id
            )

            # Atualiza métricas
            published_post.likes_count = (
                post_details.get("likes", {}).get("summary", {}).get("total_count", 0)
            )
            published_post.comments_count = (
                post_details.get("comments", {})
                .get("summary", {})
                .get("total_count", 0)
            )
            published_post.shares_count = post_details.get("shares", {}).get("count", 0)
            published_post.metrics_updated_at = timezone.now()
            published_post.save()

            updated_count += 1

        except Exception as e:
            logger.error(f"Erro ao atualizar métricas do post {published_post.id}: {e}")
            continue

    return f"Métricas atualizadas para {updated_count} posts"


@shared_task
def schedule_content_generation():
    """Agenda geração de conteúdo para posts pendentes"""
    pending_posts = ScheduledPost.objects.filter(
        status="pending",
        scheduled_time__gte=timezone.now(),
        scheduled_time__lte=timezone.now() + timezone.timedelta(hours=2),
    )

    scheduled_count = 0

    for post in pending_posts:
        # Gera conteúdo 30 minutos antes do horário agendado
        generate_at = post.scheduled_time - timezone.timedelta(minutes=30)

        if timezone.now() >= generate_at:
            generate_content_for_post.delay(post.id)
            scheduled_count += 1

    return f"Geração de conteúdo agendada para {scheduled_count} posts"


@shared_task
def send_daily_report():
    """Envia relatório diário por email"""
    today = timezone.now().date()

    # Estatísticas do dia
    published_today = PublishedPost.objects.filter(published_at__date=today).count()

    scheduled_tomorrow = ScheduledPost.objects.filter(
        scheduled_time__date=today + timezone.timedelta(days=1),
        status__in=["pending", "ready"],
    ).count()

    failed_today = ScheduledPost.objects.filter(
        updated_at__date=today, status="failed"
    ).count()

    report = f"""
    Relatório Diário - {today.strftime('%d/%m/%Y')}
    
    📊 Estatísticas:
    • Posts publicados hoje: {published_today}
    • Posts agendados para amanhã: {scheduled_tomorrow}
    • Posts que falharam: {failed_today}
    
    🤖 Sistema funcionando normalmente.
    """

    # Aqui você pode configurar o envio de email
    # send_mail(
    #     'Relatório Diário - Facebook Automation',
    #     report,
    #     'noreply@seudominio.com',
    #     ['admin@seudominio.com'],
    #     fail_silently=False,
    # )

    logger.info(f"Relatório diário gerado: {published_today} posts publicados")
    return report


@shared_task(bind=True)
def publish_to_multiple_pages(
    self, page_ids, content, user_id, template_id=None, use_markdown=False
):
    """
    Task para publicar conteúdo em múltiplas páginas simultaneamente
    """
    user = User.objects.get(id=user_id)
    results = {
        "success": [],
        "failed": [],
        "total_pages": len(page_ids),
        "processed": 0,
    }

    # Processar markdown se necessário
    processed_content = content
    if use_markdown:
        processed_content = convert_html_to_facebook_text(content)

    # Buscar template se fornecido
    template = None
    if template_id:
        try:
            template = PostTemplate.objects.get(id=template_id)
        except PostTemplate.DoesNotExist:
            logger.warning(f"Template {template_id} não encontrado")

    for i, page_id in enumerate(page_ids):
        try:
            # Atualizar progresso
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": len(page_ids),
                    "status": f"Publicando na página {i + 1} de {len(page_ids)}",
                },
            )

            page = FacebookPage.objects.get(id=page_id)

            # Verificar se a página pode publicar
            if not page.can_publish:
                results["failed"].append(
                    {
                        "page_id": page_id,
                        "page_name": page.name,
                        "error": "Página não tem permissão para publicar",
                    }
                )
                continue

            # Publicar usando a API do Facebook
            api_client = FacebookAPIClient(page.access_token, page.page_id)
            post_response = api_client.create_post(processed_content)

            # Registrar post publicado
            published_post = PublishedPost.objects.create(
                facebook_page=page,
                template=template,
                content=processed_content,
                facebook_post_id=post_response.get("id"),
                published_at=timezone.now(),
                created_by=user,
                metrics={},
            )

            results["success"].append(
                {
                    "page_id": page_id,
                    "page_name": page.name,
                    "post_id": published_post.pk,
                    "facebook_post_id": post_response.get("id"),
                }
            )

        except FacebookPage.DoesNotExist:
            results["failed"].append(
                {
                    "page_id": page_id,
                    "page_name": "Desconhecida",
                    "error": "Página não encontrada",
                }
            )
        except FacebookAPIException as e:
            results["failed"].append(
                {
                    "page_id": page_id,
                    "page_name": page.name if "page" in locals() else "Desconhecida",
                    "error": f"Erro na API do Facebook: {str(e)}",
                }
            )
        except Exception as e:
            logger.error(f"Erro ao publicar na página {page_id}: {str(e)}")
            results["failed"].append(
                {
                    "page_id": page_id,
                    "page_name": page.name if "page" in locals() else "Desconhecida",
                    "error": f"Erro interno: {str(e)}",
                }
            )

        results["processed"] += 1

    return results


@shared_task(bind=True)
def schedule_multiple_posts(
    self,
    page_ids,
    content,
    scheduled_time_str,
    user_id,
    template_id=None,
    use_markdown=False,
):
    """
    Task para agendar posts em múltiplas páginas
    """
    from django.contrib.auth.models import User
    from datetime import datetime

    user = User.objects.get(id=user_id)
    scheduled_time = datetime.fromisoformat(scheduled_time_str)

    results = {
        "success": [],
        "failed": [],
        "total_pages": len(page_ids),
        "processed": 0,
    }

    # Buscar template se fornecido
    template = None
    if template_id:
        try:
            template = PostTemplate.objects.get(id=template_id)
        except PostTemplate.DoesNotExist:
            logger.warning(f"Template {template_id} não encontrado")

    for i, page_id in enumerate(page_ids):
        try:
            # Atualizar progresso
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": len(page_ids),
                    "status": f"Agendando para página {i + 1} de {len(page_ids)}",
                },
            )

            page = FacebookPage.objects.get(id=page_id)

            # Criar post agendado
            scheduled_post = ScheduledPost.objects.create(
                facebook_page=page,
                template=template,
                content=content,
                scheduled_time=scheduled_time,
                created_by=user,
                use_markdown=use_markdown,
                status="pending",
            )

            results["success"].append(
                {
                    "page_id": page_id,
                    "page_name": page.name,
                    "scheduled_post_id": scheduled_post.pk,
                }
            )

        except FacebookPage.DoesNotExist:
            results["failed"].append(
                {
                    "page_id": page_id,
                    "page_name": "Desconhecida",
                    "error": "Página não encontrada",
                }
            )
        except Exception as e:
            logger.error(f"Erro ao agendar post para página {page_id}: {str(e)}")
            results["failed"].append(
                {
                    "page_id": page_id,
                    "page_name": page.name if "page" in locals() else "Desconhecida",
                    "error": f"Erro interno: {str(e)}",
                }
            )

        results["processed"] += 1

    return results


def convert_html_to_facebook_text(content):
    """
    Converte markdown básico para texto formatado apropriado para Facebook
    (sem dependências externas)
    """
    if not content:
        return ""

    text = content

    # Processar markdown básico se detectado
    if any(marker in content for marker in ["**", "*", "#", "`", "- ", "1. ", "---"]):
        text = process_simple_markdown(text)

    # Limpar espaços extras e normalizar quebras de linha
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)  # Max 2 quebras consecutivas
    text = re.sub(r"[ \t]+", " ", text)  # Normalizar espaços
    text = text.strip()

    return text


def process_simple_markdown(text):
    """
    Processador simples de markdown sem bibliotecas externas
    """
    # Títulos (# ## ###)
    text = re.sub(r"^### (.+)$", r"🔹 \1", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.+)$", r"🔸 \1", text, flags=re.MULTILINE)
    text = re.sub(r"^# (.+)$", r"📌 \1", text, flags=re.MULTILINE)

    # Negrito (**texto**)
    text = re.sub(r"\*\*([^*]+)\*\*", r"𝗧𝗘𝗫𝗧𝗢_𝗣𝗥𝗢𝗩𝗜𝗦𝗢𝗥𝗜𝗢_\1_𝗙𝗜𝗠", text)
    text = re.sub(r"𝗧𝗘𝗫𝗧𝗢_𝗣𝗥𝗢𝗩𝗜𝗦𝗢𝗥𝗜𝗢_(.+?)_𝗙𝗜𝗠", r"𝗧\1", text)

    # Itálico (*texto*)
    text = re.sub(r"\*([^*\n]+)\*", r"𝘛\1", text)

    # Links [texto](url) -> apenas o texto com emoji
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"🔗 \1", text)

    # Listas com traço (- item)
    text = re.sub(r"^- (.+)$", r"• \1", text, flags=re.MULTILINE)

    # Listas numeradas (1. item)
    def replace_numbered_list(match):
        return f"{match.group(1)}. {match.group(2)}"

    text = re.sub(r"^(\d+)\. (.+)$", replace_numbered_list, text, flags=re.MULTILINE)

    # Código inline (`código`)
    text = re.sub(r"`([^`]+)`", r"▶️ \1", text)

    # Linha horizontal (---)
    text = re.sub(r"^---+$", "━━━━━━━━━━━━━━━━━━━━", text, flags=re.MULTILINE)

    # Citações (> texto)
    text = re.sub(r"^> (.+)$", r'💬 "\1"', text, flags=re.MULTILINE)

    return text
