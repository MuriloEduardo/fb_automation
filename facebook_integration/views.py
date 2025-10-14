import json
import logging
import requests
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect, get_object_or_404
from .models import (
    FacebookPage,
    PostTemplate,
    ScheduledPost,
    PublishedPost,
    AIConfiguration,
)
from .services.image_prompt_generation import (
    generate_image_prompt_with_fallback,
)
from .services.openai_service import OpenAIService
from .services.text_generation import generate_text_with_fallback
from .services.facebook_api import FacebookAPIClient, FacebookAPIException

logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    """Dashboard principal com estatísticas e métricas"""
    from .models import PageMetrics, PostMetrics
    from django.db.models import Sum, Avg, Max
    from datetime import timedelta

    # Estatísticas básicas
    total_pages = FacebookPage.objects.filter(is_active=True).count()
    total_templates = PostTemplate.objects.filter(is_active=True).count()
    pending_posts = ScheduledPost.objects.filter(status="pending").count()
    published_today = PublishedPost.objects.filter(
        published_at__date=timezone.now().date()
    ).count()

    # Métricas agregadas de todas as páginas (últimos 7 dias)
    week_ago = timezone.now() - timedelta(days=7)

    # Última métrica de cada página
    pages_with_metrics = FacebookPage.objects.filter(
        is_active=True, metrics__isnull=False
    ).annotate(
        latest_followers=Max("metrics__followers_count"),
        latest_likes=Max("metrics__likes_count"),
    )

    total_followers = (
        sum(p.latest_followers for p in pages_with_metrics if p.latest_followers) or 0
    )
    total_likes = sum(p.latest_likes for p in pages_with_metrics if p.latest_likes) or 0

    # Engagement médio dos posts recentes
    recent_posts_metrics = PostMetrics.objects.filter(
        collected_at__gte=week_ago
    ).aggregate(
        avg_likes=Avg("likes_count"),
        avg_comments=Avg("comments_count"),
        avg_shares=Avg("shares_count"),
        avg_engagement=Avg("engagement_rate"),
    )

    context = {
        "total_pages": total_pages,
        "total_templates": total_templates,
        "pending_posts": pending_posts,
        "published_today": published_today,
        "total_followers": total_followers,
        "total_likes": total_likes,
        "avg_engagement": round(recent_posts_metrics["avg_engagement"] or 0, 2),
        "avg_likes": int(recent_posts_metrics["avg_likes"] or 0),
        "avg_comments": int(recent_posts_metrics["avg_comments"] or 0),
        "recent_posts": PublishedPost.objects.order_by("-published_at")[:5],
        "upcoming_posts": ScheduledPost.objects.filter(
            status__in=["pending", "ready"], scheduled_time__gte=timezone.now()
        ).order_by("scheduled_time")[:5],
        "active_pages": FacebookPage.objects.filter(is_active=True)[:6],
    }
    return render(request, "facebook_integration/dashboard.html", context)


@login_required
def facebook_pages(request):
    """Lista e gerencia páginas do Facebook (legacy - redireciona para page_manager)"""
    return redirect("facebook_integration:page_manager")


@login_required
def test_facebook_connection(request, page_id):
    """Testa a conexão com uma página do Facebook"""
    page = get_object_or_404(FacebookPage, id=page_id)

    try:
        client = FacebookAPIClient(access_token=page.access_token, page_id=page.page_id)

        if client.validate_access_token():
            page_info = client.get_page_info()
            messages.success(request, f"Conexão OK! Página: {page_info.get('name')}")
        else:
            messages.error(request, "Token de acesso inválido")

    except FacebookAPIException as e:
        messages.error(request, f"Erro na conexão: {str(e)}")

    return redirect("facebook_integration:facebook_pages")


@login_required
def post_templates(request):
    """Lista e gerencia templates de posts"""
    templates = PostTemplate.objects.filter(created_by=request.user).order_by(
        "-created_at"
    )

    paginator = Paginator(templates, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request, "facebook_integration/post_templates.html", {"page_obj": page_obj}
    )


@login_required
def create_template(request):
    """Cria um novo template de post"""
    if request.method == "POST":
        name = request.POST.get("name")
        prompt = request.POST.get("prompt")
        category = request.POST.get("category")

        if name and prompt and category:
            PostTemplate.objects.create(
                name=name, prompt=prompt, category=category, created_by=request.user
            )
            messages.success(request, "Template criado com sucesso!")
            return redirect("facebook_integration:post_templates")
        else:
            messages.error(request, "Todos os campos são obrigatórios")

    return render(request, "facebook_integration/create_template.html")


@login_required
def scheduled_posts(request):
    """Lista posts agendados"""
    posts = ScheduledPost.objects.filter(created_by=request.user).order_by(
        "-scheduled_time"
    )

    paginator = Paginator(posts, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "facebook_integration/scheduled_posts.html",
        {"page_obj": page_obj, "posts": page_obj},
    )


@login_required
def create_scheduled_post(request):
    """Cria um novo post agendado ou publica imediatamente em múltiplas páginas"""
    if request.method == "POST":
        try:
            from .tasks import publish_to_multiple_pages, schedule_multiple_posts

            page_ids = request.POST.getlist("facebook_pages")
            template_id = request.POST.get("template") or None
            content = request.POST.get("content", "").strip()
            use_markdown = request.POST.get("use_markdown") == "on"
            post_type = request.POST.get("post_type", "immediate")
            scheduled_time = request.POST.get("scheduled_time")
            image_path = request.POST.get("image_path", "").strip()

            # Validações
            if not page_ids:
                return JsonResponse(
                    {"success": False, "error": "Selecione pelo menos uma página"}
                )

            if not content and not template_id:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Digite o conteúdo ou selecione um template",
                    }
                )

            is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

            if post_type == "immediate":
                task = publish_to_multiple_pages.delay(
                    page_ids=page_ids,
                    content=content,
                    user_id=request.user.id,
                    template_id=template_id,
                    use_markdown=use_markdown,
                    image_path=image_path,
                )

                if is_ajax:
                    return JsonResponse(
                        {
                            "success": True,
                            "task_id": task.id,
                            "message": f"Publicação iniciada para {len(page_ids)} páginas",
                        }
                    )
                else:
                    messages.success(
                        request,
                        f"Publicação iniciada para {len(page_ids)} páginas. "
                        "Você será notificado quando concluir.",
                    )
                    return redirect("facebook_integration:scheduled_posts")

            else:
                if not scheduled_time:
                    return JsonResponse(
                        {
                            "success": False,
                            "error": "Data e hora são obrigatórias para agendamento",
                        }
                    )

                task = schedule_multiple_posts.delay(
                    page_ids=page_ids,
                    content=content,
                    scheduled_time_str=scheduled_time,
                    user_id=request.user.id,
                    template_id=template_id,
                    use_markdown=use_markdown,
                    image_path=image_path,
                )

                if is_ajax:
                    return JsonResponse(
                        {
                            "success": True,
                            "task_id": task.id,
                            "message": f"Agendamento iniciado para {len(page_ids)} páginas",
                        }
                    )
                else:
                    messages.success(
                        request,
                        f"Posts agendados para {len(page_ids)} páginas em {scheduled_time}",
                    )
                    return redirect("facebook_integration:scheduled_posts")

        except Exception as e:
            error_msg = f"Erro ao processar solicitação: {str(e)}"
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": error_msg})
            else:
                messages.error(request, error_msg)
                return redirect("facebook_integration:create_scheduled_post")

    context = {
        "facebook_pages": FacebookPage.objects.filter(is_active=True).order_by("name"),
        "templates": PostTemplate.objects.filter(
            created_by=request.user, is_active=True
        ).order_by("name"),
    }
    return render(request, "facebook_integration/create_scheduled_post.html", context)


@login_required
def generate_content_preview(request):
    """Gera uma prévia do conteúdo usando IA"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            template_id = data.get("template_id")
            prompt = data.get("prompt")
            context_data = data.get("context", {})

            # Se tem template_id, usar o template
            if template_id:
                template = get_object_or_404(PostTemplate, id=template_id)
                final_prompt = template.prompt
            # Se tem prompt direto, usar ele
            elif prompt:
                final_prompt = prompt
            else:
                return JsonResponse(
                    {"success": False, "error": "Template ou prompt é obrigatório"}
                )

            content = generate_text_with_fallback(final_prompt, context_data)

            image_prompt = generate_image_prompt_with_fallback(content)

            return JsonResponse(
                {"success": True, "content": content, "image_prompt": image_prompt}
            )

        except (ValueError, RuntimeError) as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Método não permitido"})


@login_required
def generate_intelligent_content(request):
    """Gera conteúdo inteligente baseado nas páginas selecionadas"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            pages_data = data.get("pages", [])
            content_type = data.get("content_type", "informative")
            content_tone = data.get("content_tone", "professional")
            template_id = data.get("template_id")

            if not pages_data:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Pelo menos uma página deve ser selecionada",
                    }
                )

            # Buscar informações detalhadas das páginas
            page_ids = [page["id"] for page in pages_data]
            pages = FacebookPage.objects.filter(id__in=page_ids)

            # Construir contexto inteligente baseado nas páginas
            context = {
                "pages": [],
                "content_type": content_type,
                "content_tone": content_tone,
                "total_followers": 0,
                "categories": set(),
                "page_count": len(pages),
            }

            for page in pages:
                page_info = {
                    "name": page.name,
                    "category": page.category,
                    "followers": page.followers_count,
                }
                context["pages"].append(page_info)
                context["total_followers"] += page.followers_count
                if page.category:
                    context["categories"].add(page.category)

            context["categories"] = list(context["categories"])

            # Gerar prompt inteligente baseado no contexto
            intelligent_prompt = _build_intelligent_prompt(context, template_id)

            content = generate_text_with_fallback(intelligent_prompt, context)

            return JsonResponse(
                {"success": True, "content": content, "context_used": context}
            )

        except Exception as e:
            logger.error(f"Erro ao gerar conteúdo inteligente: {e}")
            return JsonResponse({"success": False, "error": f"Erro interno: {str(e)}"})

    return JsonResponse({"success": False, "error": "Método não permitido"})


@login_required
def generate_image(request):
    if request.method == "POST":
        try:
            from .services.openai_service import OpenAIService
            from .services.image_generation import generate_image_with_fallback
            import os

            data = json.loads(request.body)
            content = data.get("content", "").strip()

            if not content:
                return JsonResponse(
                    {"success": False, "error": "Conteúdo é obrigatório"}
                )

            image_prompt = generate_image_prompt_with_fallback(content)

            if not image_prompt:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Não foi possível gerar prompt de imagem",
                    }
                )

            image_path = generate_image_with_fallback(image_prompt)

            if not image_path:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Não foi possível gerar imagem. Verifique as configurações.",
                    }
                )

            rel_path = os.path.relpath(image_path, start=str(settings.MEDIA_ROOT))
            image_url = settings.MEDIA_URL + rel_path

            return JsonResponse(
                {
                    "success": True,
                    "image_path": rel_path,
                    "image_url": image_url,
                    "image_prompt": image_prompt,
                }
            )

        except Exception as e:
            logger.error(f"Erro ao gerar imagem: {e}")
            return JsonResponse({"success": False, "error": f"Erro interno: {str(e)}"})

    return JsonResponse({"success": False, "error": "Método não permitido"})


def _build_intelligent_prompt(context, template_id=None):
    """Constrói um prompt inteligente baseado no contexto das páginas"""

    # Se há um template, usar como base
    base_prompt = ""
    if template_id:
        try:
            template = PostTemplate.objects.get(id=template_id)
            base_prompt = template.prompt + "\n\n"
        except PostTemplate.DoesNotExist:
            pass

    # Informações das páginas
    pages_info = ""
    if len(context["pages"]) == 1:
        page = context["pages"][0]
        pages_info = f"Página: {page['name']}"
        if page["category"]:
            pages_info += f" (Categoria: {page['category']})"
        if page["followers"]:
            pages_info += f" com {page['followers']:,} seguidores"
    else:
        pages_info = f"Múltiplas páginas ({context['page_count']} páginas)"
        if context["categories"]:
            pages_info += f" - Categorias: {', '.join(context['categories'])}"
        if context["total_followers"]:
            pages_info += f" - Total de seguidores: {context['total_followers']:,}"

    # Tipo de conteúdo
    content_descriptions = {
        "promotional": "conteúdo promocional para gerar interesse em produtos/serviços",
        "informative": "conteúdo informativo e educativo para a audiência",
        "engaging": "conteúdo envolvente para aumentar interação e engajamento",
        "news": "conteúdo de notícias ou atualizações relevantes",
        "behind-scenes": "conteúdo de bastidores para mostrar o lado humano",
        "educational": "conteúdo educativo para ensinar algo útil",
    }

    # Tom de voz
    tone_descriptions = {
        "professional": "tom profissional e corporativo",
        "friendly": "tom amigável e próximo",
        "casual": "tom casual e descontraído",
        "formal": "tom formal e respeitoso",
        "enthusiastic": "tom entusiasmado e energético",
        "inspirational": "tom inspiracional e motivador",
    }

    content_desc = content_descriptions.get(
        context["content_type"], "conteúdo relevante"
    )
    tone_desc = tone_descriptions.get(context["content_tone"], "tom apropriado")

    # Montar prompt final
    prompt = f"""{base_prompt}Crie {content_desc} com {tone_desc} para Facebook.

Informações do contexto:
- {pages_info}
- Tipo de conteúdo: {context["content_type"]}
- Tom desejado: {context["content_tone"]}

Instruções específicas:
- O conteúdo deve ser adequado para as características da(s) página(s)
- Use linguagem que ressoe com o público-alvo
- Inclua elementos que gerem engajamento (perguntas, call-to-action)
- Mantenha o comprimento ideal para Facebook (100-250 palavras)
- Use emojis apropriados para tornar o conteúdo mais atrativo
- Inclua hashtags relevantes (#)

Crie um post que seja autêntico e que funcione bem para todas as páginas selecionadas."""

    return prompt


@login_required
def published_posts(request):
    """Lista posts publicados com métricas"""
    posts = PublishedPost.objects.order_by("-published_at")

    paginator = Paginator(posts, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request, "facebook_integration/published_posts.html", {"page_obj": page_obj}
    )


@login_required
def posts(request):
    """Página unificada de posts: publicados e agendados, com ações."""
    published = PublishedPost.objects.order_by("-published_at")[:12]
    scheduled = ScheduledPost.objects.filter(status__in=["pending", "ready"]).order_by(
        "scheduled_time"
    )[:12]

    context = {
        "published": published,
        "scheduled": scheduled,
    }
    return render(request, "facebook_integration/posts.html", context)


@login_required
def ai_configurations(request):
    """Gerencia configurações de IA"""
    configs = AIConfiguration.objects.all().order_by("-created_at")
    return render(
        request,
        "facebook_integration/ai_configurations.html",
        {"configurations": configs},
    )


@login_required
def create_ai_configuration(request):
    """Cria uma nova configuração de IA"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            # Validar dados obrigatórios
            name = data.get("name", "").strip()
            if not name:
                return JsonResponse({"success": False, "error": "Nome é obrigatório"})

            # Criar configuração
            config = AIConfiguration.objects.create(
                name=name,
                description=data.get("description", ""),
                model=data.get("model", "gpt-3.5-turbo"),
                max_tokens=int(data.get("max_tokens", 500)),
                temperature=float(data.get("temperature", 0.7)),
                include_hashtags=data.get("include_hashtags", True),
                max_hashtags=int(data.get("max_hashtags", 5)),
                include_emojis=data.get("include_emojis", True),
                is_default=data.get("is_default", False),
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": "Configuração criada com sucesso!",
                    "config_id": config.id,
                }
            )

        except (ValueError, KeyError) as e:
            return JsonResponse(
                {"success": False, "error": f"Dados inválidos: {str(e)}"}
            )
        except Exception as e:
            return JsonResponse({"success": False, "error": f"Erro interno: {str(e)}"})

    return JsonResponse({"success": False, "error": "Método não permitido"})


@login_required
def test_ai_configuration(request, config_id):
    """Testa uma configuração específica de IA"""
    try:
        config = get_object_or_404(AIConfiguration, id=config_id)
        openai_service = OpenAIService()

        # Teste simples de geração de conteúdo
        test_prompt = "Crie um post sobre tecnologia e inovação"
        content = openai_service.generate_post_content(test_prompt, ai_config=config)

        return JsonResponse(
            {
                "success": True,
                "message": "Configuração testada com sucesso!",
                "test_content": content,
            }
        )

    except AIConfiguration.DoesNotExist:
        return JsonResponse({"success": False, "error": "Configuração não encontrada"})
    except Exception as e:
        return JsonResponse({"success": False, "error": f"Erro no teste: {str(e)}"})


def test_openai_connection(request):
    """Testa a conexão com OpenAI API"""
    try:
        openai_service = OpenAIService()
        if openai_service.test_connection():
            return JsonResponse({"success": True, "message": "Conexão OK!"})
        else:
            return JsonResponse({"success": False, "error": "Falha na conexão"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
def task_status(request, task_id):
    """Retorna o status de uma task Celery"""
    from celery.result import AsyncResult

    try:
        task = AsyncResult(task_id)

        if task.state == "PENDING":
            response = {
                "state": task.state,
                "current": 0,
                "total": 1,
                "status": "Aguardando...",
            }
        elif task.state == "PROGRESS":
            response = {
                "state": task.state,
                "current": task.info.get("current", 0),
                "total": task.info.get("total", 1),
                "status": task.info.get("status", ""),
            }
        elif task.state == "SUCCESS":
            response = {
                "state": task.state,
                "current": 100,
                "total": 100,
                "result": task.result,
            }
        else:  # FAILURE
            response = {
                "state": task.state,
                "current": 100,
                "total": 100,
                "result": str(task.info),
            }

        return JsonResponse(response)

    except Exception as e:
        return JsonResponse(
            {"state": "FAILURE", "result": f"Erro ao verificar status: {str(e)}"}
        )


@login_required
def page_manager(request):
    """Página principal para gerenciar páginas do Facebook"""
    pages = (
        FacebookPage.objects.exclude(is_active=False)
        .all()
        .order_by("-followers_count", "name")
    )

    # Estatísticas
    active_pages_count = pages.filter(is_active=True).count()
    publishable_pages_count = pages.filter(can_publish=True).count()
    max_followers = (
        pages.aggregate(max_followers=models.Max("followers_count"))["max_followers"]
        or 0
    )

    return render(
        request,
        "facebook_integration/page_manager.html",
        {
            "pages": pages,
            "active_pages_count": active_pages_count,
            "publishable_pages_count": publishable_pages_count,
            "max_followers": max_followers,
            "title": "Gerenciar Páginas do Facebook",
        },
    )


@login_required
@require_http_methods(["POST"])
def sync_facebook_pages(request):
    """Sincroniza páginas do Facebook usando a API"""
    try:
        # Usar token do usuário para listar páginas
        user_token = settings.FACEBOOK_ACCESS_TOKEN
        url = "https://graph.facebook.com/v23.0/me"
        params = {
            "access_token": user_token,
            "fields": "id,name,accounts{id,name,access_token,category,fan_count,tasks}",
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            accounts = data.get("accounts", {})
            pages_data = accounts.get("data", [])

            synced_count = 0
            updated_count = 0

            for page_data in pages_data:
                page_id = page_data["id"]
                page_name = page_data["name"]
                page_token = page_data["access_token"]
                category = page_data.get("category", "")
                followers = page_data.get("fan_count", 0)
                tasks = page_data.get("tasks", [])

                # Verificar permissões
                can_publish = "CREATE_CONTENT" in tasks
                can_read_insights = "ANALYZE" in tasks
                can_manage_ads = "ADVERTISE" in tasks

                # Criar ou atualizar página
                page, created = FacebookPage.objects.update_or_create(
                    page_id=page_id,
                    defaults={
                        "name": page_name,
                        "access_token": page_token,
                        "category": category,
                        "followers_count": followers,
                        "can_publish": can_publish,
                        "can_read_insights": can_read_insights,
                        "can_manage_ads": can_manage_ads,
                        "last_sync": timezone.now(),
                    },
                )

                if created:
                    synced_count += 1
                else:
                    updated_count += 1

            message = f"✅ Sincronização concluída! {synced_count} páginas adicionadas, {updated_count} atualizadas."
            messages.success(request, message)

            return JsonResponse(
                {
                    "success": True,
                    "message": message,
                    "synced": synced_count,
                    "updated": updated_count,
                }
            )
        else:
            error_msg = f"Erro na API do Facebook: {response.text}"
            messages.error(request, error_msg)
            return JsonResponse({"success": False, "error": error_msg})

    except Exception as e:
        error_msg = f"Erro ao sincronizar páginas: {str(e)}"
        messages.error(request, error_msg)
        return JsonResponse({"success": False, "error": error_msg})


@login_required
def page_detail(request, page_id):
    """Detalhes de uma página específica"""
    page = get_object_or_404(FacebookPage, pk=page_id)

    # Buscar posts agendados e publicados
    scheduled_posts = ScheduledPost.objects.filter(facebook_page=page).order_by(
        "-scheduled_time"
    )[:10]

    # Buscar templates
    templates = PostTemplate.objects.filter(is_active=True).order_by("name")

    context = {
        "page": page,
        "scheduled_posts": scheduled_posts,
        "templates": templates,
        "title": f"Página: {page.name}",
    }

    return render(request, "facebook_integration/page_detail.html", context)


@login_required
@require_http_methods(["POST"])
def toggle_page_status(request, page_id):
    """Ativa/desativa uma página"""
    page = get_object_or_404(FacebookPage, pk=page_id)
    page.is_active = not page.is_active
    page.save()

    status = "ativada" if page.is_active else "desativada"
    messages.success(request, f"Página {page.name} foi {status}.")

    return JsonResponse(
        {
            "success": True,
            "is_active": page.is_active,
            "message": f"Página {status} com sucesso!",
        }
    )


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
            "success": True,
            "page_info": page_info,
            "permissions": {"can_post": can_post, "can_insights": can_insights},
        }

        messages.success(request, f"✅ Teste de permissões concluído para {page.name}")
        return JsonResponse(result)

    except Exception as e:
        error_msg = f"Erro ao testar permissões: {str(e)}"
        messages.error(request, error_msg)
        return JsonResponse({"success": False, "error": error_msg})


@login_required
def schedule_post_for_page(request, page_id):
    """Agenda um post para uma página específica"""
    page = get_object_or_404(FacebookPage, pk=page_id)

    if request.method == "POST":
        template_id = request.POST.get("template")
        scheduled_time = request.POST.get("scheduled_time")

        if template_id and scheduled_time:
            template = get_object_or_404(PostTemplate, pk=template_id)

            scheduled_post = ScheduledPost.objects.create(
                facebook_page=page,
                template=template,
                scheduled_time=scheduled_time,
                created_by=request.user,
            )

            messages.success(
                request, f"✅ Post agendado para {page.name} em {scheduled_time}"
            )

            return redirect("page_detail", page_id=page.pk)
        else:
            messages.error(request, "Template e horário são obrigatórios")

    return redirect("page_detail", page_id=page.pk)


@login_required
def page_metrics_api(request, page_id):
    """API para retornar métricas históricas de uma página"""
    from .models import PageMetrics
    from django.db.models import Avg
    from datetime import timedelta

    page = get_object_or_404(FacebookPage, pk=page_id)

    # Período (últimos 30 dias por padrão)
    days = int(request.GET.get("days", 30))
    start_date = timezone.now() - timedelta(days=days)

    # Buscar métricas
    metrics = (
        PageMetrics.objects.filter(page=page, collected_at__gte=start_date)
        .order_by("collected_at")
        .values(
            "followers_count",
            "likes_count",
            "page_impressions",
            "page_impressions_unique",
            "page_engaged_users",
            "collected_at",
        )
    )

    # Formatar dados para o gráfico
    data = {
        "labels": [],
        "followers": [],
        "likes": [],
        "impressions": [],
        "engaged_users": [],
    }

    for metric in metrics:
        data["labels"].append(metric["collected_at"].strftime("%d/%m/%Y %H:%M"))
        data["followers"].append(metric["followers_count"])
        data["likes"].append(metric["likes_count"])
        data["impressions"].append(metric["page_impressions"])
        data["engaged_users"].append(metric["page_engaged_users"])

    # Estatísticas gerais
    latest = metrics.last() if metrics else None

    # Se não houver métricas, usar dados da própria página
    if not latest:
        stats = {
            "current_followers": page.followers_count or 0,
            "current_likes": 0,  # Não temos esse campo na página
            "avg_impressions": 0,
            "avg_engaged": 0,
        }
        # Adicionar pelo menos um ponto de dados com os valores atuais
        if page.followers_count:
            data["labels"].append(timezone.now().strftime("%d/%m/%Y %H:%M"))
            data["followers"].append(page.followers_count)
            data["likes"].append(0)
            data["impressions"].append(0)
            data["engaged_users"].append(0)
    else:
        stats = {
            "current_followers": latest["followers_count"],
            "current_likes": latest["likes_count"],
            "avg_impressions": int(
                metrics.aggregate(Avg("page_impressions"))["page_impressions__avg"] or 0
            ),
            "avg_engaged": int(
                metrics.aggregate(Avg("page_engaged_users"))["page_engaged_users__avg"]
                or 0
            ),
        }

    return JsonResponse(
        {
            "data": data,
            "stats": stats,
        }
    )


@login_required
def post_metrics_api(request, post_id):
    """API para retornar métricas históricas de um post"""
    from .models import PostMetrics

    post = get_object_or_404(PublishedPost, pk=post_id)

    # Buscar métricas
    metrics = (
        PostMetrics.objects.filter(post=post)
        .order_by("collected_at")
        .values(
            "likes_count",
            "comments_count",
            "shares_count",
            "reach",
            "impressions",
            "engagement_rate",
            "collected_at",
        )
    )

    # Formatar dados para o gráfico
    data = {
        "labels": [],
        "likes": [],
        "comments": [],
        "shares": [],
        "reach": [],
        "engagement_rate": [],
    }

    for metric in metrics:
        data["labels"].append(metric["collected_at"].strftime("%d/%m/%Y %H:%M"))
        data["likes"].append(metric["likes_count"])
        data["comments"].append(metric["comments_count"])
        data["shares"].append(metric["shares_count"])
        data["reach"].append(metric["reach"])
        data["engagement_rate"].append(round(metric["engagement_rate"], 2))

    # Estatísticas atuais
    latest = metrics.last() if metrics else None
    stats = {
        "likes": latest["likes_count"] if latest else 0,
        "comments": latest["comments_count"] if latest else 0,
        "shares": latest["shares_count"] if latest else 0,
        "reach": latest["reach"] if latest else 0,
        "engagement_rate": round(latest["engagement_rate"], 2) if latest else 0,
    }

    return JsonResponse(
        {
            "data": data,
            "stats": stats,
        }
    )


@login_required
def posts_comparison_api(request, page_id):
    """API para comparar métricas de múltiplos posts"""
    from .models import PostMetrics
    from django.db.models import Max

    page = get_object_or_404(FacebookPage, pk=page_id)

    # Buscar últimos posts com métricas
    posts = (
        PublishedPost.objects.filter(facebook_page=page)
        .annotate(latest_metrics=Max("metrics__collected_at"))
        .filter(latest_metrics__isnull=False)
        .order_by("-published_at")[:10]
    )

    data = {
        "labels": [],
        "likes": [],
        "comments": [],
        "shares": [],
        "engagement_rate": [],
    }

    for post in posts:
        # Pegar última métrica de cada post
        latest_metric = post.metrics.order_by("-collected_at").first()

        if latest_metric:
            # Truncar conteúdo para label
            label = (
                post.content[:30] + "..." if len(post.content) > 30 else post.content
            )
            data["labels"].append(label)
            data["likes"].append(latest_metric.likes_count)
            data["comments"].append(latest_metric.comments_count)
            data["shares"].append(latest_metric.shares_count)
            data["engagement_rate"].append(round(latest_metric.engagement_rate, 2))

    return JsonResponse({"data": data})


@login_required
def page_capabilities(request, page_id):
    """Exibe todas as capabilities de uma página"""
    from .services.permissions_checker import PermissionsChecker
    from .services.facebook_api import FacebookAPIClient

    page = get_object_or_404(FacebookPage, pk=page_id)

    api_client = FacebookAPIClient(page.access_token)
    permissions_checker = PermissionsChecker(api_client)

    try:
        capabilities = permissions_checker.get_full_capabilities(page.page_id)

        context = {
            "page": page,
            "capabilities": capabilities,
            "capabilities_json": json.dumps(capabilities, indent=2),
        }

        return render(request, "facebook_integration/page_capabilities.html", context)

    except Exception as e:
        messages.error(request, f"Erro ao verificar capabilities: {e}")
        return redirect("facebook_integration:page_detail", page_id=page_id)


@login_required
def page_insights_advanced(request, page_id):
    """Exibe insights avançados com gráficos demográficos"""
    from .services.insights_collector import InsightsCollector
    from .services.facebook_api import FacebookAPIClient

    page = get_object_or_404(FacebookPage, pk=page_id)
    days_back = int(request.GET.get("days", 30))

    api_client = FacebookAPIClient(page.access_token)
    insights_collector = InsightsCollector(api_client)

    try:
        complete_insights = insights_collector.get_complete_insights(
            page.page_id, days_back=days_back
        )

        context = {
            "page": page,
            "insights": complete_insights,
            "days_back": days_back,
        }

        return render(
            request, "facebook_integration/page_insights_advanced.html", context
        )

    except Exception as e:
        messages.error(request, f"Erro ao coletar insights: {e}")
        return redirect("facebook_integration:page_detail", page_id=page_id)


@login_required
def leads_list(request):
    """Lista todos os leads capturados"""
    from .models import Lead

    leads = Lead.objects.select_related("page").all()

    status_filter = request.GET.get("status")
    if status_filter:
        leads = leads.filter(status=status_filter)

    page_filter = request.GET.get("page")
    if page_filter:
        leads = leads.filter(page_id=page_filter)

    search = request.GET.get("search")
    if search:
        leads = leads.filter(
            models.Q(contact_fields__icontains=search)
            | models.Q(form_name__icontains=search)
            | models.Q(campaign_name__icontains=search)
        )

    paginator = Paginator(leads, 50)
    page_number = request.GET.get("page_num", 1)
    page_obj = paginator.get_page(page_number)

    pages = FacebookPage.objects.filter(is_active=True)

    context = {
        "leads": page_obj,
        "pages": pages,
        "status_choices": Lead.STATUS_CHOICES,
        "current_filters": {
            "status": status_filter,
            "page": page_filter,
            "search": search,
        },
        "total_leads": leads.count(),
    }

    return render(request, "facebook_integration/leads_list.html", context)


@login_required
def lead_detail(request, lead_id):
    """Exibe detalhes de um lead"""
    from .models import Lead

    lead = get_object_or_404(Lead, pk=lead_id)

    if request.method == "POST":
        new_status = request.POST.get("status")
        new_notes = request.POST.get("notes")

        if new_status:
            lead.status = new_status
        if new_notes is not None:
            lead.notes = new_notes

        lead.save()
        messages.success(request, "Lead atualizado com sucesso!")
        return redirect("lead_detail", lead_id=lead_id)

    context = {
        "lead": lead,
        "status_choices": Lead.STATUS_CHOICES,
    }

    return render(request, "facebook_integration/lead_detail.html", context)


@login_required
def sync_leads_view(request, page_id):
    """Dispara task para sincronizar leads de uma página"""
    from .tasks import sync_page_leads

    page = get_object_or_404(FacebookPage, pk=page_id)

    try:
        task = sync_page_leads.delay(page.page_id)
        messages.success(
            request, f"Sincronização de leads iniciada! Task ID: {task.id}"
        )
    except Exception as e:
        messages.error(request, f"Erro ao iniciar sincronização: {e}")

    return redirect("facebook_integration:page_detail", page_id=page_id)


@login_required
def sync_advanced_insights_view(request, page_id):
    """Dispara task para sincronizar insights avançados"""
    from .tasks import sync_advanced_insights

    page = get_object_or_404(FacebookPage, pk=page_id)
    days_back = int(request.GET.get("days", 30))

    try:
        task = sync_advanced_insights.delay(page.page_id, days_back)
        messages.success(
            request, f"Sincronização de insights iniciada! Task ID: {task.id}"
        )
    except Exception as e:
        messages.error(request, f"Erro ao iniciar sincronização: {e}")

    return redirect("facebook_integration:page_detail", page_id=page_id)


@login_required
def groups_manager(request):
    """Lista todos os grupos do Facebook"""
    from .models_groups import FacebookGroup

    groups = FacebookGroup.objects.all().order_by("-is_active", "-member_count")

    context = {
        "groups": groups,
        "total_groups": groups.count(),
        "active_groups": groups.filter(is_active=True).count(),
        "publishable_groups": groups.filter(can_publish=True).count(),
        "title": "Gerenciar Grupos do Facebook",
    }

    return render(request, "facebook_integration/groups_manager.html", context)


@login_required
@require_http_methods(["POST"])
def sync_facebook_groups(request):
    """Sincroniza grupos do Facebook usando o token do usuário"""
    from .models_groups import FacebookGroup
    from .services.groups_collector import GroupsCollector
    from .services.facebook_api import FacebookAPIClient
    from django.conf import settings

    try:
        user_token = settings.FACEBOOK_ACCESS_TOKEN
        api_client = FacebookAPIClient(user_token)
        groups_collector = GroupsCollector(api_client)

        result = groups_collector.get_user_groups()

        if result["status"] == "no_permission":
            messages.warning(
                request,
                "Sem permissão para acessar grupos. "
                "Verifique se o token tem 'groups_access_member_info'",
            )
            return JsonResponse({"success": False, "error": result["error"]})

        if result["status"] != "success":
            messages.error(request, f"Erro: {result.get('error')}")
            return JsonResponse({"success": False, "error": result.get("error")})

        synced = 0
        updated = 0

        for group_data in result["groups"]:
            group, created = FacebookGroup.objects.update_or_create(
                group_id=group_data["group_id"],
                defaults={
                    "name": group_data["name"],
                    "description": group_data.get("description", ""),
                    "privacy": group_data.get("privacy", "CLOSED"),
                    "member_count": group_data.get("member_count", 0),
                    "cover_photo": group_data.get("cover_photo"),
                    "permalink_url": group_data.get("permalink_url"),
                    "can_publish": group_data.get("is_admin", False),
                    "can_read": True,
                    "last_sync": timezone.now(),
                },
            )

            if created:
                synced += 1
            else:
                updated += 1

        message = f"✅ {synced} grupos adicionados, {updated} atualizados"
        messages.success(request, message)

        return JsonResponse(
            {
                "success": True,
                "message": message,
                "synced": synced,
                "updated": updated,
            }
        )

    except Exception as e:
        error_msg = f"Erro ao sincronizar grupos: {str(e)}"
        messages.error(request, error_msg)
        return JsonResponse({"success": False, "error": error_msg})


@login_required
def group_detail(request, group_id):
    """Detalhes de um grupo específico"""
    from .models_groups import FacebookGroup, GroupPost

    group = get_object_or_404(FacebookGroup, pk=group_id)

    recent_posts = GroupPost.objects.filter(group=group).order_by("-published_at")[:20]

    accessible_pages = group.accessible_by_pages.all()

    context = {
        "group": group,
        "recent_posts": recent_posts,
        "accessible_pages": accessible_pages,
        "title": f"Grupo: {group.name}",
    }

    return render(request, "facebook_integration/group_detail.html", context)


@login_required
@require_http_methods(["POST"])
def check_group_permissions(request, group_id):
    """Verifica permissões de um grupo"""
    from .models_groups import FacebookGroup
    from .services.groups_collector import GroupsCollector
    from .services.facebook_api import FacebookAPIClient
    from django.conf import settings

    group = get_object_or_404(FacebookGroup, pk=group_id)

    try:
        user_token = settings.FACEBOOK_ACCESS_TOKEN
        api_client = FacebookAPIClient(user_token)
        groups_collector = GroupsCollector(api_client)

        result = groups_collector.check_group_permissions(group.group_id)

        if result["status"] == "success":
            perms = result["permissions"]

            group.can_publish = perms["can_post"]
            group.can_read = perms["can_read"]
            group.permissions = perms
            group.save()

            messages.success(
                request,
                f"Permissões atualizadas: "
                f"Ler={perms['can_read']}, Publicar={perms['can_post']}",
            )
        else:
            messages.error(request, f"Erro: {result.get('error')}")

        return JsonResponse(result)

    except Exception as e:
        error_msg = f"Erro ao verificar permissões: {str(e)}"
        messages.error(request, error_msg)
        return JsonResponse({"success": False, "error": error_msg})
