from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django import forms
from .models import (
    FacebookPage,
    PostTemplate,
    ScheduledPost,
    PublishedPost,
    AIConfiguration,
    PageMetrics,
    PostMetrics,
    Lead,
)
from .models_groups import FacebookGroup, GroupPost


@admin.register(FacebookPage)
class FacebookPageAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "page_id",
        "permissions_display",
        "followers_count",
        "auto_posting_display",
        "status_display",
        "last_sync",
    ]
    list_filter = [
        "is_active",
        "auto_posting_enabled",
        "can_publish",
        "can_read_insights",
        "created_at",
    ]
    search_fields = ["name", "page_id", "category"]
    readonly_fields = ["created_at", "updated_at", "last_sync"]
    fieldsets = (
        (
            "Informações Básicas",
            {"fields": ("name", "page_id", "category", "followers_count")},
        ),
        ("Token e Acesso", {"fields": ("access_token",), "classes": ("collapse",)}),
        (
            "Permissões",
            {"fields": ("can_publish", "can_read_insights", "can_manage_ads")},
        ),
        (
            "Configurações",
            {"fields": ("is_active", "auto_sync", "auto_posting_enabled")},
        ),
        (
            "Metadados",
            {
                "fields": ("created_at", "updated_at", "last_sync"),
                "classes": ("collapse",),
            },
        ),
    )

    def permissions_display(self, obj):
        permissions = []
        if obj.can_publish:
            permissions.append('<span class="badge bg-success">Publicar</span>')
        if obj.can_read_insights:
            permissions.append('<span class="badge bg-info">Métricas</span>')
        if obj.can_manage_ads:
            permissions.append('<span class="badge bg-warning">Anúncios</span>')

        return mark_safe(" ".join(permissions)) if permissions else "❌ Sem permissões"

    permissions_display.short_description = "Permissões"

    def status_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">●</span> Ativa')
        return format_html('<span style="color: red;">●</span> Inativa')

    status_display.short_description = "Status"

    def auto_posting_display(self, obj):
        if obj.auto_posting_enabled:
            return format_html('<span style="color: green;">●</span> Automático')
        return format_html('<span style="color: orange;">●</span> Manual')

    auto_posting_display.short_description = "Postagem"

    actions = [
        "activate_pages",
        "deactivate_pages",
        "enable_auto_posting",
        "disable_auto_posting",
        "sync_metrics_now",
    ]

    def activate_pages(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} páginas foram ativadas.")

    activate_pages.short_description = "Ativar páginas selecionadas"

    def deactivate_pages(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} páginas foram desativadas.")

    deactivate_pages.short_description = "Desativar páginas selecionadas"

    def enable_auto_posting(self, request, queryset):
        count = queryset.update(auto_posting_enabled=True)
        self.message_user(request, f"{count} páginas agora têm postagem automática.")

    enable_auto_posting.short_description = "Habilitar postagem automática"

    def disable_auto_posting(self, request, queryset):
        count = queryset.update(auto_posting_enabled=False)
        self.message_user(request, f"{count} páginas agora têm postagem manual.")

    disable_auto_posting.short_description = "Desabilitar postagem automática"

    def sync_metrics_now(self, request, queryset):
        from .tasks import sync_facebook_metrics

        count = 0
        for page in queryset:
            sync_facebook_metrics.delay(page_id=page.id)
            count += 1

        self.message_user(
            request,
            f"Sincronização de métricas iniciada para {count} página(s). "
            "Verifique os resultados em alguns minutos.",
        )

    sync_metrics_now.short_description = "🔄 Sincronizar métricas agora"


@admin.register(PostTemplate)
class PostTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "is_active", "created_by", "created_at"]
    list_filter = ["category", "is_active", "created_at"]
    search_fields = ["name", "category"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ScheduledPost)
class ScheduledPostAdmin(admin.ModelAdmin):
    list_display = [
        "facebook_page",
        "status",
        "image_thumb",
        "scheduled_time",
        "created_by",
        "created_at",
    ]
    list_filter = ["status", "facebook_page", "scheduled_time", "created_at"]
    search_fields = ["facebook_page__name", "generated_content"]
    readonly_fields = [
        "facebook_post_id",
        "facebook_post_url",
        "image_preview",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "scheduled_time"

    fieldsets = (
        (
            "Conteúdo",
            {
                "fields": (
                    "facebook_page",
                    "template",
                    "status",
                    "content",
                    "generated_content",
                    "generated_image_prompt",
                    "generated_image_file",
                    "image_preview",
                    "use_markdown",
                )
            },
        ),
        (
            "Agendamento",
            {"fields": ("scheduled_time",)},
        ),
        (
            "Facebook",
            {"fields": ("facebook_post_id", "facebook_post_url")},
        ),
        (
            "Metadados",
            {"fields": ("created_by", "created_at", "updated_at")},
        ),
    )

    def image_thumb(self, obj):
        if obj.generated_image_file:
            html = (
                '<img src="{}" style="height:40px;width:auto;' 'border-radius:4px;"/>'
            )
            return format_html(html, obj.generated_image_file.url)
        return "—"

    image_thumb.short_description = "Imagem"

    def image_preview(self, obj):
        if obj.generated_image_file:
            html = (
                '<img src="{}" style="max-height:240px;width:auto;'
                'border:1px solid #ddd;"/>'
            )
            return format_html(html, obj.generated_image_file.url)
        return "—"

    image_preview.short_description = "Pré-visualização"


@admin.register(PublishedPost)
class PublishedPostAdmin(admin.ModelAdmin):
    list_display = [
        "facebook_page",
        "published_at",
        "auto_generated_display",
        "content_type",
        "image_thumb",
        "likes_count",
        "comments_count",
        "shares_count",
    ]
    list_filter = [
        "facebook_page",
        "auto_generated",
        "content_type",
        "content_tone",
        "published_at",
    ]
    search_fields = ["facebook_page__name", "content"]
    readonly_fields = [
        "facebook_post_id",
        "facebook_post_url",
        "image_preview",
        "published_at",
        "metrics_updated_at",
    ]
    date_hierarchy = "published_at"

    def auto_generated_display(self, obj):
        if obj.auto_generated:
            return format_html('<span style="color: blue;">🤖</span> Automático')
        return format_html('<span style="color: green;">👤</span> Manual')

    auto_generated_display.short_description = "Origem"

    def image_thumb(self, obj):
        if obj.image_file:
            html = (
                '<img src="{}" style="height:40px;width:auto;' 'border-radius:4px;"/>'
            )
            return format_html(html, obj.image_file.url)
        return "—"

    image_thumb.short_description = "Imagem"

    def image_preview(self, obj):
        if obj.image_file:
            html = (
                '<img src="{}" style="max-height:240px;width:auto;'
                'border:1px solid #ddd;"/>'
            )
            return format_html(html, obj.image_file.url)
        return "—"

    image_preview.short_description = "Pré-visualização"


class AIConfigurationForm(forms.ModelForm):
    """
    Custom form for AIConfiguration with dynamic model choices
    based on selected provider.
    """

    class Meta:
        model = AIConfiguration
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add help text for provider field
        self.fields["provider"].help_text = (
            "Selecione o provedor de IA: OpenAI ou Google Gemini"
        )

        # Add help text for model field with available models
        openai_models = ", ".join(
            [name for code, name in AIConfiguration.OPENAI_MODELS]
        )
        gemini_models = ", ".join(
            [name for code, name in AIConfiguration.GEMINI_MODELS]
        )

        self.fields["model"].help_text = (
            f"<strong>Modelos OpenAI:</strong> {openai_models}<br>"
            f"<strong>Modelos Gemini:</strong> {gemini_models}"
        )

        # Add widget attributes for better UX
        self.fields["provider"].widget.attrs.update(
            {"class": "provider-select", "onchange": "updateModelHelpText(this.value)"}
        )


@admin.register(AIConfiguration)
class AIConfigurationAdmin(admin.ModelAdmin):
    form = AIConfigurationForm
    list_display = [
        "name",
        "provider",
        "model",
        "temperature",
        "max_tokens",
        "is_default",
        "created_at",
    ]
    list_filter = ["provider", "is_default", "created_at"]
    search_fields = ["name", "model"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Informações Básicas",
            {"fields": ("name", "description", "is_default")},
        ),
        (
            "Provedor e Modelo",
            {"fields": ("provider", "model")},
        ),
        (
            "Parâmetros de Geração",
            {"fields": ("max_tokens", "temperature")},
        ),
        (
            "Configurações de Posts",
            {"fields": ("include_hashtags", "max_hashtags", "include_emojis")},
        ),
        (
            "Metadados",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(PageMetrics)
class PageMetricsAdmin(admin.ModelAdmin):
    list_display = [
        "page",
        "followers_count",
        "likes_count",
        "page_engaged_users",
        "collected_at",
    ]
    list_filter = ["page", "collected_at"]
    search_fields = ["page__name"]
    readonly_fields = ["collected_at"]
    date_hierarchy = "collected_at"

    def has_add_permission(self, request):
        return False


@admin.register(PostMetrics)
class PostMetricsAdmin(admin.ModelAdmin):
    list_display = [
        "post",
        "likes_count",
        "comments_count",
        "shares_count",
        "reach",
        "engagement_rate",
        "collected_at",
    ]
    list_filter = ["post__facebook_page", "collected_at"]
    search_fields = ["post__post_id"]
    readonly_fields = ["collected_at", "engagement_rate"]
    date_hierarchy = "collected_at"

    def has_add_permission(self, request):
        return False


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = [
        "created_time",
        "get_contact_name",
        "get_contact_email",
        "page",
        "form_name",
        "status",
        "is_organic",
    ]
    list_filter = ["status", "is_organic", "page", "created_time"]
    search_fields = [
        "contact_fields",
        "form_name",
        "campaign_name",
        "ad_name",
    ]
    readonly_fields = [
        "lead_id",
        "form_id",
        "created_time",
        "collected_at",
        "updated_at",
        "contact_fields",
        "ad_id",
        "campaign_id",
    ]
    
    fieldsets = (
        (
            "Informações do Contato",
            {
                "fields": (
                    "contact_fields",
                    "status",
                    "notes",
                )
            },
        ),
        (
            "Origem",
            {
                "fields": (
                    "page",
                    "form_id",
                    "form_name",
                    "is_organic",
                )
            },
        ),
        (
            "Campanha (se pago)",
            {
                "fields": (
                    "campaign_id",
                    "campaign_name",
                    "ad_id",
                    "ad_name",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadados",
            {
                "fields": (
                    "lead_id",
                    "created_time",
                    "collected_at",
                    "updated_at",
                )
            },
        ),
    )
    
    def has_add_permission(self, request):
        return False
