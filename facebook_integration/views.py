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
from .services.facebook_api import FacebookAPIClient, FacebookAPIException
from .services.openai_service import OpenAIService, OpenAIServiceException

logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    """Dashboard principal com estatísticas"""
    context = {
        "total_pages": FacebookPage.objects.filter(is_active=True).count(),
        "total_templates": PostTemplate.objects.filter(is_active=True).count(),
        "pending_posts": ScheduledPost.objects.filter(status="pending").count(),
        "published_today": PublishedPost.objects.filter(
            published_at__date=timezone.now().date()
        ).count(),
        "recent_posts": PublishedPost.objects.order_by("-published_at")[:5],
        "upcoming_posts": ScheduledPost.objects.filter(
            status__in=["pending", "ready"], scheduled_time__gte=timezone.now()
        ).order_by("scheduled_time")[:5],
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
            # Importar as tasks
            from .tasks import publish_to_multiple_pages, schedule_multiple_posts

            page_ids = request.POST.getlist("facebook_pages")
            template_id = request.POST.get("template") or None
            content = request.POST.get("content", "").strip()
            use_markdown = request.POST.get("use_markdown") == "on"
            post_type = request.POST.get("post_type", "immediate")
            scheduled_time = request.POST.get("scheduled_time")

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

            # Verificar se é AJAX request
            is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

            if post_type == "immediate":
                # Publicar imediatamente via task
                task = publish_to_multiple_pages.delay(
                    page_ids=page_ids,
                    content=content,
                    user_id=request.user.id,
                    template_id=template_id,
                    use_markdown=use_markdown,
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

            else:  # scheduled
                if not scheduled_time:
                    return JsonResponse(
                        {
                            "success": False,
                            "error": "Data e hora são obrigatórias para agendamento",
                        }
                    )

                # Agendar posts via task
                task = schedule_multiple_posts.delay(
                    page_ids=page_ids,
                    content=content,
                    scheduled_time_str=scheduled_time,
                    user_id=request.user.id,
                    template_id=template_id,
                    use_markdown=use_markdown,
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

    # GET request - mostrar formulário
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

            # Gera conteúdo usando OpenAI
            openai_service = OpenAIService()
            content = openai_service.generate_post_content(final_prompt, context_data)

            # Gera prompt para imagem
            image_prompt = openai_service.generate_image_prompt(content)

            return JsonResponse(
                {"success": True, "content": content, "image_prompt": image_prompt}
            )

        except (OpenAIServiceException, ValueError) as e:
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

            # Gerar conteúdo usando OpenAI
            openai_service = OpenAIService()
            content = openai_service.generate_post_content(intelligent_prompt, context)

            return JsonResponse(
                {"success": True, "content": content, "context_used": context}
            )

        except Exception as e:
            logger.error(f"Erro ao gerar conteúdo inteligente: {e}")
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
    pages = FacebookPage.objects.all().order_by("-is_active", "name")

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
