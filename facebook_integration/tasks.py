from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from .models import ScheduledPost, PublishedPost
from .services.facebook_api import FacebookAPIClient, FacebookAPIException
from .services.openai_service import OpenAIService, OpenAIServiceException
import logging

logger = logging.getLogger(__name__)


@shared_task
def process_scheduled_posts():
    """Processa posts que estão prontos para serem publicados"""
    due_posts = ScheduledPost.objects.filter(
        status='ready',
        scheduled_time__lte=timezone.now()
    )
    
    processed_count = 0
    for post in due_posts:
        try:
            # Atualiza status para publishing
            post.status = 'publishing'
            post.save()
            
            # Publica o post
            result = publish_post_task.delay(post.id)
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Erro ao processar post {post.id}: {e}")
            post.status = 'failed'
            post.error_message = str(e)
            post.save()
    
    return f"Processados {processed_count} posts"


@shared_task
def generate_content_for_post(post_id):
    """Gera conteúdo para um post agendado usando IA"""
    try:
        post = ScheduledPost.objects.get(id=post_id)
        
        # Atualiza status
        post.status = 'generating'
        post.save()
        
        # Gera conteúdo usando OpenAI
        openai_service = OpenAIService()
        
        # Contexto baseado na página e template
        context = {
            'page_name': post.facebook_page.name,
            'category': post.template.category,
            'current_time': timezone.now().strftime('%Y-%m-%d %H:%M'),
        }
        
        # Gera conteúdo
        content = openai_service.generate_post_content(
            post.template.prompt,
            context
        )
        
        # Gera prompt para imagem (opcional)
        image_prompt = openai_service.generate_image_prompt(content)
        
        # Salva o conteúdo gerado
        post.generated_content = content
        post.generated_image_prompt = image_prompt
        post.status = 'ready'
        post.save()
        
        logger.info(f"Conteúdo gerado para post {post_id}")
        return f"Conteúdo gerado para post {post_id}"
        
    except ScheduledPost.DoesNotExist:
        logger.error(f"Post {post_id} não encontrado")
        return f"Post {post_id} não encontrado"
        
    except OpenAIServiceException as e:
        logger.error(f"Erro na IA para post {post_id}: {e}")
        post.status = 'failed'
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
            page_id=post.facebook_page.page_id
        )
        
        # Publica o post
        result = facebook_client.create_post(
            message=post.generated_content
        )
        
        # Extrai informações do resultado
        facebook_post_id = result.get('id')
        facebook_post_url = f"https://facebook.com/{facebook_post_id}"
        
        # Atualiza o post agendado
        post.status = 'published'
        post.facebook_post_id = facebook_post_id
        post.facebook_post_url = facebook_post_url
        post.save()
        
        # Cria registro do post publicado
        PublishedPost.objects.create(
            facebook_page=post.facebook_page,
            scheduled_post=post,
            content=post.generated_content,
            facebook_post_id=facebook_post_id,
            facebook_post_url=facebook_post_url
        )
        
        logger.info(f"Post {post_id} publicado com sucesso: {facebook_post_id}")
        return f"Post {post_id} publicado: {facebook_post_id}"
        
    except ScheduledPost.DoesNotExist:
        logger.error(f"Post {post_id} não encontrado")
        return f"Post {post_id} não encontrado"
        
    except FacebookAPIException as e:
        logger.error(f"Erro do Facebook para post {post_id}: {e}")
        post.status = 'failed'
        post.error_message = f"Erro do Facebook: {str(e)}"
        post.save()
        return f"Erro do Facebook para post {post_id}"
        
    except Exception as e:
        logger.error(f"Erro geral para post {post_id}: {e}")
        post.status = 'failed'
        post.error_message = str(e)
        post.save()
        return f"Erro para post {post_id}: {str(e)}"


@shared_task
def update_post_metrics():
    """Atualiza métricas dos posts publicados"""
    recent_posts = PublishedPost.objects.filter(
        published_at__gte=timezone.now() - timezone.timedelta(days=30)
    ).order_by('-published_at')[:50]  # Últimos 50 posts do mês
    
    updated_count = 0
    
    for published_post in recent_posts:
        try:
            facebook_client = FacebookAPIClient(
                access_token=published_post.facebook_page.access_token,
                page_id=published_post.facebook_page.page_id
            )
            
            # Obtém detalhes do post
            post_details = facebook_client.get_post_details(
                published_post.facebook_post_id
            )
            
            # Atualiza métricas
            published_post.likes_count = post_details.get('likes', {}).get('summary', {}).get('total_count', 0)
            published_post.comments_count = post_details.get('comments', {}).get('summary', {}).get('total_count', 0)
            published_post.shares_count = post_details.get('shares', {}).get('count', 0)
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
        status='pending',
        scheduled_time__gte=timezone.now(),
        scheduled_time__lte=timezone.now() + timezone.timedelta(hours=2)
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
    published_today = PublishedPost.objects.filter(
        published_at__date=today
    ).count()
    
    scheduled_tomorrow = ScheduledPost.objects.filter(
        scheduled_time__date=today + timezone.timedelta(days=1),
        status__in=['pending', 'ready']
    ).count()
    
    failed_today = ScheduledPost.objects.filter(
        updated_at__date=today,
        status='failed'
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