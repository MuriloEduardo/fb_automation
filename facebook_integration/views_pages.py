from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from django.db import models
import requests

from .models import FacebookPage, ScheduledPost, PostTemplate
from .services.facebook_api import FacebookAPIClient


@login_required
def page_manager(request):
    """Página principal para gerenciar páginas do Facebook"""
    pages = FacebookPage.objects.all().order_by('-is_active', 'name')
    
    # Estatísticas
    active_pages_count = pages.filter(is_active=True).count()
    publishable_pages_count = pages.filter(can_publish=True).count()
    max_followers = pages.aggregate(
        max_followers=models.Max('followers_count')
    )['max_followers'] or 0
    
    return render(request, 'facebook_integration/page_manager.html', {
        'pages': pages,
        'active_pages_count': active_pages_count,
        'publishable_pages_count': publishable_pages_count,
        'max_followers': max_followers,
        'title': 'Gerenciar Páginas do Facebook'
    })


@login_required
@require_http_methods(["POST"])
def sync_facebook_pages(request):
    """Sincroniza páginas do Facebook usando a API"""
    try:
        # Usar token do usuário para listar páginas
        user_token = settings.FACEBOOK_ACCESS_TOKEN
        url = "https://graph.facebook.com/v18.0/me/accounts"
        params = {
            'access_token': user_token,
            'fields': 'id,name,access_token,category,fan_count,tasks'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            pages_data = data.get('data', [])
            
            synced_count = 0
            updated_count = 0
            
            for page_data in pages_data:
                page_id = page_data['id']
                page_name = page_data['name']
                page_token = page_data['access_token']
                category = page_data.get('category', '')
                followers = page_data.get('fan_count', 0)
                tasks = page_data.get('tasks', [])
                
                # Verificar permissões
                can_publish = 'CREATE_CONTENT' in tasks
                can_read_insights = 'ANALYZE' in tasks
                can_manage_ads = 'ADVERTISE' in tasks
                
                # Criar ou atualizar página
                page, created = FacebookPage.objects.update_or_create(
                    page_id=page_id,
                    defaults={
                        'name': page_name,
                        'access_token': page_token,
                        'category': category,
                        'followers_count': followers,
                        'can_publish': can_publish,
                        'can_read_insights': can_read_insights,
                        'can_manage_ads': can_manage_ads,
                        'last_sync': timezone.now()
                    }
                )
                
                if created:
                    synced_count += 1
                else:
                    updated_count += 1
            
            message = f"✅ Sincronização concluída! {synced_count} páginas adicionadas, {updated_count} atualizadas."
            messages.success(request, message)
            
            return JsonResponse({
                'success': True,
                'message': message,
                'synced': synced_count,
                'updated': updated_count
            })
        else:
            error_msg = f"Erro na API do Facebook: {response.text}"
            messages.error(request, error_msg)
            return JsonResponse({'success': False, 'error': error_msg})
            
    except Exception as e:
        error_msg = f"Erro ao sincronizar páginas: {str(e)}"
        messages.error(request, error_msg)
        return JsonResponse({'success': False, 'error': error_msg})


@login_required
def page_detail(request, page_id):
    """Detalhes de uma página específica"""
    page = get_object_or_404(FacebookPage, pk=page_id)
    
    # Buscar posts agendados e publicados
    scheduled_posts = ScheduledPost.objects.filter(
        facebook_page=page
    ).order_by('-scheduled_time')[:10]
    
    # Buscar templates
    templates = PostTemplate.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page': page,
        'scheduled_posts': scheduled_posts,
        'templates': templates,
        'title': f'Página: {page.name}'
    }
    
    return render(request, 'facebook_integration/page_detail.html', context)


@login_required
@require_http_methods(["POST"])
def toggle_page_status(request, page_id):
    """Ativa/desativa uma página"""
    page = get_object_or_404(FacebookPage, pk=page_id)
    page.is_active = not page.is_active
    page.save()
    
    status = "ativada" if page.is_active else "desativada"
    messages.success(request, f"Página {page.name} foi {status}.")
    
    return JsonResponse({
        'success': True,
        'is_active': page.is_active,
        'message': f"Página {status} com sucesso!"
    })


@login_required
@require_http_methods(["POST"])
def test_page_permissions(request, page_id):
    """Testa as permissões de uma página"""
    page = get_object_or_404(FacebookPage, pk=page_id)
    
    try:
        client = FacebookAPIClient(page.access_token)
        
        # Testar acesso básico à página
        page_info = client.get_page_info(page.page_id)
        
        # Testar permissões de publicação
        can_post = client.test_publish_permission(page.page_id)
        
        # Testar permissões de insights
        can_insights = client.test_insights_permission(page.page_id)
        
        result = {
            'success': True,
            'page_info': page_info,
            'permissions': {
                'can_post': can_post,
                'can_insights': can_insights
            }
        }
        
        messages.success(request, f"✅ Teste de permissões concluído para {page.name}")
        return JsonResponse(result)
        
    except Exception as e:
        error_msg = f"Erro ao testar permissões: {str(e)}"
        messages.error(request, error_msg)
        return JsonResponse({'success': False, 'error': error_msg})


@login_required
def schedule_post_for_page(request, page_id):
    """Agenda um post para uma página específica"""
    page = get_object_or_404(FacebookPage, pk=page_id)
    
    if request.method == 'POST':
        template_id = request.POST.get('template')
        scheduled_time = request.POST.get('scheduled_time')
        
        if template_id and scheduled_time:
            template = get_object_or_404(PostTemplate, pk=template_id)
            
            scheduled_post = ScheduledPost.objects.create(
                facebook_page=page,
                template=template,
                scheduled_time=scheduled_time,
                created_by=request.user
            )
            
            messages.success(request, 
                f"✅ Post agendado para {page.name} em {scheduled_time}")
            
            return redirect('page_detail', page_id=page.pk)
        else:
            messages.error(request, "Template e horário são obrigatórios")
    
    return redirect('page_detail', page_id=page.pk)