from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from .models import (
    FacebookPage, PostTemplate, ScheduledPost, 
    PublishedPost, AIConfiguration
)
from .services.facebook_api import FacebookAPIClient, FacebookAPIException
from .services.openai_service import OpenAIService, OpenAIServiceException
import json
from datetime import datetime


@login_required
def dashboard(request):
    """Dashboard principal com estatísticas"""
    context = {
        'total_pages': FacebookPage.objects.filter(is_active=True).count(),
        'total_templates': PostTemplate.objects.filter(is_active=True).count(),
        'pending_posts': ScheduledPost.objects.filter(status='pending').count(),
        'published_today': PublishedPost.objects.filter(
            published_at__date=timezone.now().date()
        ).count(),
        'recent_posts': PublishedPost.objects.order_by('-published_at')[:5],
        'upcoming_posts': ScheduledPost.objects.filter(
            status__in=['pending', 'ready'],
            scheduled_time__gte=timezone.now()
        ).order_by('scheduled_time')[:5]
    }
    return render(request, 'facebook_integration/dashboard.html', context)


@login_required
def facebook_pages(request):
    """Redireciona para o novo gerenciador de páginas"""
    return redirect('facebook_integration:page_manager')


@login_required
def test_facebook_connection(request, page_id):
    """Testa a conexão com uma página do Facebook"""
    page = get_object_or_404(FacebookPage, id=page_id)
    
    try:
        client = FacebookAPIClient(
            access_token=page.access_token, 
            page_id=page.page_id
        )
        
        if client.validate_access_token():
            page_info = client.get_page_info()
            messages.success(request, f"Conexão OK! Página: {page_info.get('name')}")
        else:
            messages.error(request, "Token de acesso inválido")
            
    except FacebookAPIException as e:
        messages.error(request, f"Erro na conexão: {str(e)}")
    
    return redirect('facebook_integration:facebook_pages')


@login_required
def post_templates(request):
    """Lista e gerencia templates de posts"""
    templates = PostTemplate.objects.filter(
        created_by=request.user
    ).order_by('-created_at')
    
    paginator = Paginator(templates, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'facebook_integration/post_templates.html', {
        'page_obj': page_obj
    })


@login_required
def create_template(request):
    """Cria um novo template de post"""
    if request.method == 'POST':
        name = request.POST.get('name')
        prompt = request.POST.get('prompt')
        category = request.POST.get('category')
        
        if name and prompt and category:
            PostTemplate.objects.create(
                name=name,
                prompt=prompt,
                category=category,
                created_by=request.user
            )
            messages.success(request, 'Template criado com sucesso!')
            return redirect('facebook_integration:post_templates')
        else:
            messages.error(request, 'Todos os campos são obrigatórios')
    
    return render(request, 'facebook_integration/create_template.html')


@login_required
def scheduled_posts(request):
    """Lista posts agendados"""
    posts = ScheduledPost.objects.filter(
        created_by=request.user
    ).order_by('-scheduled_time')
    
    paginator = Paginator(posts, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'facebook_integration/scheduled_posts.html', {
        'page_obj': page_obj
    })


@login_required
def create_scheduled_post(request):
    """Cria um novo post agendado"""
    if request.method == 'POST':
        facebook_page_id = request.POST.get('facebook_page')
        template_id = request.POST.get('template')
        scheduled_time = request.POST.get('scheduled_time')
        
        try:
            facebook_page = FacebookPage.objects.get(id=facebook_page_id)
            template = PostTemplate.objects.get(id=template_id)
            scheduled_time = datetime.fromisoformat(scheduled_time)
            
            ScheduledPost.objects.create(
                facebook_page=facebook_page,
                template=template,
                scheduled_time=scheduled_time,
                created_by=request.user
            )
            
            messages.success(request, 'Post agendado com sucesso!')
            return redirect('facebook_integration:scheduled_posts')
            
        except (ValueError, FacebookPage.DoesNotExist, PostTemplate.DoesNotExist) as e:
            messages.error(request, f'Erro ao agendar post: {str(e)}')
    
    context = {
        'facebook_pages': FacebookPage.objects.filter(is_active=True),
        'templates': PostTemplate.objects.filter(
            created_by=request.user, 
            is_active=True
        )
    }
    return render(request, 'facebook_integration/create_scheduled_post.html', context)


@login_required
def generate_content_preview(request):
    """Gera uma prévia do conteúdo usando IA"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            template_id = data.get('template_id')
            context_data = data.get('context', {})
            
            template = get_object_or_404(PostTemplate, id=template_id)
            
            # Gera conteúdo usando OpenAI
            openai_service = OpenAIService()
            content = openai_service.generate_post_content(
                template.prompt, 
                context_data
            )
            
            # Gera prompt para imagem
            image_prompt = openai_service.generate_image_prompt(content)
            
            return JsonResponse({
                'success': True,
                'content': content,
                'image_prompt': image_prompt
            })
            
        except (OpenAIServiceException, ValueError) as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})


@login_required
def published_posts(request):
    """Lista posts publicados com métricas"""
    posts = PublishedPost.objects.order_by('-published_at')
    
    paginator = Paginator(posts, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'facebook_integration/published_posts.html', {
        'page_obj': page_obj
    })


@login_required
def ai_configurations(request):
    """Gerencia configurações de IA"""
    configs = AIConfiguration.objects.all().order_by('-created_at')
    return render(request, 'facebook_integration/ai_configurations.html', {
        'configs': configs
    })


def test_openai_connection(request):
    """Testa a conexão com OpenAI API"""
    try:
        openai_service = OpenAIService()
        if openai_service.test_connection():
            return JsonResponse({'success': True, 'message': 'Conexão OK!'})
        else:
            return JsonResponse({'success': False, 'error': 'Falha na conexão'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
