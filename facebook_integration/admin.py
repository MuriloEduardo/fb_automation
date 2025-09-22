from django.contrib import admin
from .models import (
    FacebookPage, PostTemplate, ScheduledPost, 
    PublishedPost, AIConfiguration
)


@admin.register(FacebookPage)
class FacebookPageAdmin(admin.ModelAdmin):
    list_display = ['name', 'page_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'page_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PostTemplate)
class PostTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'created_by', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'category']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ScheduledPost)
class ScheduledPostAdmin(admin.ModelAdmin):
    list_display = [
        'facebook_page', 'status', 'scheduled_time', 
        'created_by', 'created_at'
    ]
    list_filter = ['status', 'facebook_page', 'scheduled_time', 'created_at']
    search_fields = ['facebook_page__name', 'generated_content']
    readonly_fields = [
        'facebook_post_id', 'facebook_post_url', 
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'scheduled_time'


@admin.register(PublishedPost)
class PublishedPostAdmin(admin.ModelAdmin):
    list_display = [
        'facebook_page', 'published_at', 'likes_count', 
        'comments_count', 'shares_count'
    ]
    list_filter = ['facebook_page', 'published_at']
    search_fields = ['facebook_page__name', 'content']
    readonly_fields = [
        'facebook_post_id', 'facebook_post_url', 
        'published_at', 'metrics_updated_at'
    ]
    date_hierarchy = 'published_at'


@admin.register(AIConfiguration)
class AIConfigurationAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'model', 'temperature', 'max_tokens', 
        'is_default', 'created_at'
    ]
    list_filter = ['model', 'is_default', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
