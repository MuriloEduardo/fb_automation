from django.urls import path
from celery import current_app
from django.contrib import admin
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.html import format_html

from .models import CeleryTask, CeleryWorker, CeleryTaskTemplate


@admin.register(CeleryTask)
class CeleryTaskAdmin(admin.ModelAdmin):
    list_display = [
        "task_name",
        "status_display",
        "scheduled_post",
        "duration_display",
        "created_at",
        "actions_display",
    ]
    list_filter = ["status", "task_name", "created_at"]
    search_fields = ["task_id", "task_name", "scheduled_post__facebook_page__name"]
    readonly_fields = [
        "task_id",
        "result",
        "traceback",
        "started_at",
        "completed_at",
        "created_at",
        "duration_display",
    ]

    fieldsets = (
        ("Informações da Task", {"fields": ("task_name", "task_id", "status")}),
        ("Parâmetros", {"fields": ("args", "kwargs"), "classes": ("collapse",)}),
        (
            "Resultado",
            {
                "fields": ("result", "traceback"),
            },
        ),
        ("Relacionamentos", {"fields": ("scheduled_post", "created_by")}),
        (
            "Metadados",
            {
                "fields": (
                    "started_at",
                    "completed_at",
                    "created_at",
                    "duration_display",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def status_display(self, obj):
        color_map = {
            "SUCCESS": "green",
            "FAILURE": "red",
            "PENDING": "orange",
            "STARTED": "blue",
            "RETRY": "purple",
            "REVOKED": "gray",
        }
        color = color_map.get(obj.status, "black")
        return format_html(
            '<span style="color: {};">● {}</span>', color, obj.get_status_display()
        )

    status_display.short_description = "Status"

    def duration_display(self, obj):
        duration = obj.duration
        if duration:
            total_seconds = int(duration.total_seconds())
            minutes, seconds = divmod(total_seconds, 60)
            return f"{minutes}m {seconds}s"
        return "-"

    duration_display.short_description = "Duração"

    def actions_display(self, obj):
        actions = []
        if obj.is_running:
            actions.append(
                f'<a href="/admin/facebook_integration/celerytask/{obj.pk}/revoke/" '
                f'class="button" style="background: red; color: white;">Cancelar</a>'
            )
        actions.append(
            f'<a href="/admin/facebook_integration/celerytask/{obj.pk}/refresh/" '
            f'class="button">Atualizar</a>'
        )
        return format_html(" ".join(actions))

    actions_display.short_description = "Ações"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:task_id>/refresh/",
                self.admin_site.admin_view(self.refresh_task),
                name="celerytask_refresh",
            ),
            path(
                "<int:task_id>/revoke/",
                self.admin_site.admin_view(self.revoke_task),
                name="celerytask_revoke",
            ),
        ]
        return custom_urls + urls

    def refresh_task(self, request, task_id):
        try:
            task = CeleryTask.objects.get(pk=task_id)
            task.update_from_celery()
            messages.success(request, f"Task {task.task_name} atualizada!")
        except CeleryTask.DoesNotExist:
            messages.error(request, "Task não encontrada!")

        return redirect("admin:facebook_integration_celerytask_changelist")

    def revoke_task(self, request, task_id):
        try:
            task = CeleryTask.objects.get(pk=task_id)
            current_app.control.revoke(task.task_id, terminate=True)
            task.status = "REVOKED"
            task.save()
            messages.success(request, f"Task {task.task_name} cancelada!")
        except CeleryTask.DoesNotExist:
            messages.error(request, "Task não encontrada!")

        return redirect("admin:facebook_integration_celerytask_changelist")

    actions = ["update_selected_tasks", "revoke_selected_tasks"]

    def update_selected_tasks(self, request, queryset):
        updated = 0
        for task in queryset:
            if task.update_from_celery():
                updated += 1
        self.message_user(request, f"{updated} tasks atualizadas com sucesso!")

    update_selected_tasks.short_description = "Atualizar tasks selecionadas"

    def revoke_selected_tasks(self, request, queryset):
        revoked = 0
        for task in queryset.filter(status__in=["PENDING", "STARTED"]):
            current_app.control.revoke(task.task_id, terminate=True)
            task.status = "REVOKED"
            task.save()
            revoked += 1
        self.message_user(request, f"{revoked} tasks canceladas!")

    revoke_selected_tasks.short_description = "Cancelar tasks selecionadas"


@admin.register(CeleryWorker)
class CeleryWorkerAdmin(admin.ModelAdmin):
    list_display = [
        "hostname",
        "status_display",
        "active_tasks",
        "processed_tasks",
        "last_heartbeat",
    ]
    list_filter = ["is_active", "last_heartbeat"]
    readonly_fields = ["hostname", "last_heartbeat", "created_at"]

    def status_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">● Online</span>')
        return format_html('<span style="color: red;">● Offline</span>')

    status_display.short_description = "Status"

    actions = ["update_workers_status"]

    def update_workers_status(self, request, queryset):
        if CeleryWorker.update_workers_status():
            self.message_user(request, "Status dos workers atualizado!")
        else:
            self.message_user(request, "Erro ao atualizar workers!", level="ERROR")

    update_workers_status.short_description = "Atualizar status dos workers"


@admin.register(CeleryTaskTemplate)
class CeleryTaskTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "task_name", "is_active", "created_at", "execute_action"]
    list_filter = ["is_active", "task_name"]
    search_fields = ["name", "task_name", "description"]

    fieldsets = (
        (
            "Informações Básicas",
            {"fields": ("name", "task_name", "description", "is_active")},
        ),
        (
            "Parâmetros Padrão",
            {
                "fields": ("default_args", "default_kwargs"),
                "description": "Use formato JSON para os parâmetros",
            },
        ),
    )

    def execute_action(self, obj):
        return format_html(
            '<a href="/admin/facebook_integration/celerytasktemplate/{}/execute/" '
            'class="button" style="background: green; color: white;">Executar</a>',
            obj.pk,
        )

    execute_action.short_description = "Executar"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:template_id>/execute/",
                self.admin_site.admin_view(self.execute_template),
                name="celerytasktemplate_execute",
            ),
        ]
        return custom_urls + urls

    def execute_template(self, request, template_id):
        try:
            template = CeleryTaskTemplate.objects.get(pk=template_id)
            task = template.execute()
            if task:
                messages.success(
                    request, f"Task '{template.name}' executada! ID: {task.id}"
                )
            else:
                messages.error(request, "Erro ao executar a task!")
        except CeleryTaskTemplate.DoesNotExist:
            messages.error(request, "Template não encontrado!")

        return redirect("admin:facebook_integration_celerytasktemplate_changelist")

    actions = ["execute_selected_templates"]

    def execute_selected_templates(self, request, queryset):
        executed = 0
        for template in queryset.filter(is_active=True):
            if template.execute():
                executed += 1
        self.message_user(request, f"{executed} templates executados!")

    execute_selected_templates.short_description = "Executar templates selecionados"
