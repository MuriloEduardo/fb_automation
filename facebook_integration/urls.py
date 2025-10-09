from . import views
from django.urls import path

app_name = "facebook_integration"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    # Facebook Pages Management
    path("pages/", views.page_manager, name="page_manager"),
    path("pages/sync/", views.sync_facebook_pages, name="sync_facebook_pages"),
    path("pages/<int:page_id>/", views.page_detail, name="page_detail"),
    path(
        "pages/<int:page_id>/toggle/",
        views.toggle_page_status,
        name="toggle_page_status",
    ),
    path(
        "pages/<int:page_id>/test/",
        views.test_page_permissions,
        name="test_page_permissions",
    ),
    path(
        "pages/<int:page_id>/schedule/",
        views.schedule_post_for_page,
        name="schedule_post_for_page",
    ),
    # Legacy Facebook Pages (manter compatibilidade)
    path("facebook-pages/", views.facebook_pages, name="facebook_pages"),
    path(
        "facebook-pages/<int:page_id>/test/",
        views.test_facebook_connection,
        name="test_facebook_connection",
    ),
    # Post Templates
    path("templates/", views.post_templates, name="post_templates"),
    path("templates/create/", views.create_template, name="create_template"),
    # Scheduled Posts
    path("scheduled/", views.scheduled_posts, name="scheduled_posts"),
    path(
        "scheduled/create/", views.create_scheduled_post, name="create_scheduled_post"
    ),
    # AJAX endpoints
    path(
        "api/generate-content/",
        views.generate_content_preview,
        name="generate_content_preview",
    ),
    path(
        "api/generate-intelligent-content/",
        views.generate_intelligent_content,
        name="generate_intelligent_content",
    ),
    path(
        "api/test-openai/", views.test_openai_connection, name="test_openai_connection"
    ),
    path("task-status/<str:task_id>/", views.task_status, name="task_status"),
    # Published Posts
    path("published/", views.published_posts, name="published_posts"),
    path("posts/", views.posts, name="posts"),
    # AI Configurations
    path("ai-config/", views.ai_configurations, name="ai_configurations"),
    path(
        "ai-config/create/",
        views.create_ai_configuration,
        name="create_ai_configuration",
    ),
    path(
        "ai-config/<int:config_id>/test/",
        views.test_ai_configuration,
        name="test_ai_configuration",
    ),
]
