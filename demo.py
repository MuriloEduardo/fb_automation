#!/usr/bin/env python
"""
Script de demonstração do Facebook Automation
Este script cria dados de exemplo e demonstra as funcionalidades principais
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Configurar Django
sys.path.append('/home/murilo/Personal/fb_automation')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fb_automation.settings')
django.setup()

from django.contrib.auth.models import User
from facebook_integration.models import (
    FacebookPage, PostTemplate, ScheduledPost, 
    AIConfiguration, PublishedPost
)
from django.utils import timezone


def create_demo_data():
    """Cria dados de demonstração"""
    print("🚀 Criando dados de demonstração...")
    
    # 1. Buscar ou criar usuário admin
    try:
        user = User.objects.get(username='murilo')
        print(f"✅ Usuário encontrado: {user.username}")
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='demo_user',
            email='demo@example.com',
            password='demo123'
        )
        print(f"✅ Usuário criado: {user.username}")
    
    # 2. Criar configuração de IA padrão
    ai_config, created = AIConfiguration.objects.get_or_create(
        name="Configuração Demo",
        defaults={
            'model': 'gpt-3.5-turbo',
            'max_tokens': 500,
            'temperature': 0.7,
            'include_hashtags': True,
            'max_hashtags': 5,
            'include_emojis': True,
            'is_default': True,
        }
    )
    print(f"✅ Configuração IA: {'criada' if created else 'já existe'}")
    
    # 3. Criar página demo do Facebook
    fb_page, created = FacebookPage.objects.get_or_create(
        page_id="123456789_DEMO",
        defaults={
            'name': "Página Demo - Tecnologia",
            'access_token': "demo_token_aqui",
            'is_active': True,
        }
    )
    print(f"✅ Página Facebook: {'criada' if created else 'já existe'}")
    
    # 4. Criar templates de exemplo
    templates_data = [
        {
            'name': "Post Motivacional Tech",
            'prompt': "Crie um post motivacional sobre tecnologia e inovação. Use linguagem inspiradora e inclua call-to-action para engajamento.",
            'category': "motivacional"
        },
        {
            'name': "Dica de Programação",
            'prompt': "Compartilhe uma dica útil de programação ou desenvolvimento. Seja didático e inclua exemplo prático.",
            'category': "educativo"
        },
        {
            'name': "Novidade em IA",
            'prompt': "Fale sobre uma novidade ou tendência em Inteligência Artificial. Use linguagem acessível para explicar conceitos técnicos.",
            'category': "tecnologia"
        },
        {
            'name': "Reflexão sobre Futuro",
            'prompt': "Crie uma reflexão sobre o futuro da tecnologia e seu impacto na sociedade. Seja reflexivo e estimule discussão.",
            'category': "reflexao"
        }
    ]
    
    for template_data in templates_data:
        template, created = PostTemplate.objects.get_or_create(
            name=template_data['name'],
            defaults={
                'prompt': template_data['prompt'],
                'category': template_data['category'],
                'created_by': user,
                'is_active': True,
            }
        )
        print(f"✅ Template '{template.name}': {'criado' if created else 'já existe'}")
    
    # 5. Criar alguns posts agendados de exemplo
    templates = PostTemplate.objects.all()
    
    for i, template in enumerate(templates[:3]):
        scheduled_time = timezone.now() + timedelta(hours=i+1, minutes=30)
        
        scheduled_post, created = ScheduledPost.objects.get_or_create(
            facebook_page=fb_page,
            template=template,
            scheduled_time=scheduled_time,
            defaults={
                'status': 'pending',
                'created_by': user,
            }
        )
        print(f"✅ Post agendado '{template.name}': {'criado' if created else 'já existe'}")
    
    # 6. Criar alguns posts "publicados" de exemplo (simulados)
    for i, template in enumerate(templates[:2]):
        published_time = timezone.now() - timedelta(days=i+1)
        
        published_post, created = PublishedPost.objects.get_or_create(
            facebook_page=fb_page,
            facebook_post_id=f"fake_post_id_{i+1}",
            defaults={
                'content': f"Este é um post de exemplo gerado pelo template '{template.name}'. 🚀 #tecnologia #inovacao",
                'facebook_post_url': f"https://facebook.com/fake_post_id_{i+1}",
                'likes_count': 15 + (i * 10),
                'comments_count': 3 + i,
                'shares_count': 2 + i,
                'reach': 150 + (i * 50),
                'published_at': published_time,
            }
        )
        print(f"✅ Post publicado simulado: {'criado' if created else 'já existe'}")
    
    print("\n🎉 Dados de demonstração criados com sucesso!")
    return True


def show_demo_info():
    """Mostra informações sobre a demonstração"""
    print("\n" + "="*60)
    print("📊 DEMONSTRAÇÃO DO FACEBOOK AUTOMATION")
    print("="*60)
    
    print(f"\n📈 ESTATÍSTICAS:")
    print(f"   • Páginas Facebook: {FacebookPage.objects.count()}")
    print(f"   • Templates criados: {PostTemplate.objects.count()}")
    print(f"   • Posts agendados: {ScheduledPost.objects.count()}")
    print(f"   • Posts publicados: {PublishedPost.objects.count()}")
    print(f"   • Configurações IA: {AIConfiguration.objects.count()}")
    
    print(f"\n🌐 ACESSO:")
    print(f"   • Dashboard: http://localhost:8000/")
    print(f"   • Admin: http://localhost:8000/admin/")
    print(f"   • Usuário: murilo")
    
    print(f"\n🔧 TESTES DISPONÍVEIS:")
    print(f"   • Testar IA: Clique no botão 'Testar IA' no dashboard")
    print(f"   • Gerar prévia: Crie um novo post agendado")
    print(f"   • Ver templates: Acesse a seção Templates")
    print(f"   • Histórico: Veja posts publicados")
    
    print(f"\n⚠️  PARA USAR COM APIS REAIS:")
    print(f"   1. Configure as chaves no arquivo .env")
    print(f"   2. Leia o guia: CONFIGURACAO_APIS.md")
    print(f"   3. Certifique-se que RabbitMQ está rodando")
    print(f"   4. Teste as conexões no dashboard")
    
    print(f"\n🚀 PRÓXIMOS PASSOS:")
    print(f"   1. Acesse http://localhost:8000/")
    print(f"   2. Explore o dashboard")
    print(f"   3. Configure suas APIs reais")
    print(f"   4. Comece a automatizar!")
    
    print("\n" + "="*60)


def main():
    """Função principal"""
    print("🤖 Facebook Automation - Script de Demonstração")
    print("-" * 50)
    
    try:
        # Criar dados de exemplo
        create_demo_data()
        
        # Mostrar informações
        show_demo_info()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante a demonstração: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)