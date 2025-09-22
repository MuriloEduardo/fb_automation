from django.urls import path
from . import views

app_name = 'facebook_integration'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Facebook Pages
    path('pages/', views.facebook_pages, name='facebook_pages'),
    path('pages/<int:page_id>/test/', views.test_facebook_connection, 
         name='test_facebook_connection'),
    
    # Post Templates
    path('templates/', views.post_templates, name='post_templates'),
    path('templates/create/', views.create_template, name='create_template'),
    
    # Scheduled Posts
    path('scheduled/', views.scheduled_posts, name='scheduled_posts'),
    path('scheduled/create/', views.create_scheduled_post, 
         name='create_scheduled_post'),
    
    # AJAX endpoints
    path('api/generate-content/', views.generate_content_preview, 
         name='generate_content_preview'),
    path('api/test-openai/', views.test_openai_connection, 
         name='test_openai_connection'),
    
    # Published Posts
    path('published/', views.published_posts, name='published_posts'),
    
    # AI Configurations
    path('ai-config/', views.ai_configurations, name='ai_configurations'),
]