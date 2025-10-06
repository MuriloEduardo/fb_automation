from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    FacebookPage,
    PostTemplate,
    ScheduledPost,
    PublishedPost,
    AIConfiguration,
)

# Importar admins do Celery
from .admin_celery import CeleryTaskAdmin, CeleryWorkerAdmin, CeleryTaskTemplateAdmin


@admin.register(FacebookPage)
class FacebookPageAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "page_id",
        "permissions_display",
        "followers_count",
        "status_display",
        "last_sync",
    ]
    list_filter = ["is_active", "can_publish", "can_read_insights", "created_at"]
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
        ("Configurações", {"fields": ("is_active", "auto_sync")}),
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

    actions = ["activate_pages", "deactivate_pages"]

    def activate_pages(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} páginas foram ativadas.")

    activate_pages.short_description = "Ativar páginas selecionadas"

    def deactivate_pages(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} páginas foram desativadas.")

    deactivate_pages.short_description = "Desativar páginas selecionadas"


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
        "scheduled_time",
        "created_by",
        "created_at",
    ]
    list_filter = ["status", "facebook_page", "scheduled_time", "created_at"]
    search_fields = ["facebook_page__name", "generated_content"]
    readonly_fields = [
        "facebook_post_id",
        "facebook_post_url",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "scheduled_time"


@admin.register(PublishedPost)
class PublishedPostAdmin(admin.ModelAdmin):
    list_display = [
        "facebook_page",
        "published_at",
        "likes_count",
        "comments_count",
        "shares_count",
    ]
    list_filter = ["facebook_page", "published_at"]
    search_fields = ["facebook_page__name", "content"]
    readonly_fields = [
        "facebook_post_id",
        "facebook_post_url",
        "published_at",
        "metrics_updated_at",
    ]
    date_hierarchy = "published_at"


@admin.register(AIConfiguration)
class AIConfigurationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "model",
        "temperature",
        "max_tokens",
        "is_default",
        "created_at",
    ]
    list_filter = ["model", "is_default", "created_at"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at"]
