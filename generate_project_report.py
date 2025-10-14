#!/usr/bin/env python
"""Gera relatório completo do status do projeto"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fb_automation.settings")
django.setup()

from django.contrib.auth.models import User
from facebook_integration.models import (
    FacebookPage,
    PostTemplate,
    ScheduledPost,
    PublishedPost,
    AIConfiguration,
)


def generate_report():
    """Gera relatório do projeto"""

    print("=" * 70)
    print("📊 RELATÓRIO COMPLETO DO PROJETO - Facebook Automation")
    print("=" * 70)

    # Usuários
    print("\n👥 USUÁRIOS")
    print("-" * 70)
    total_users = User.objects.count()
    superusers = User.objects.filter(is_superuser=True).count()
    print(f"Total de usuários: {total_users}")
    print(f"Superusuários: {superusers}")
    if superusers > 0:
        admin = User.objects.filter(is_superuser=True).first()
        print(f"Admin principal: {admin.username}")

    # Páginas do Facebook
    print("\n📄 PÁGINAS DO FACEBOOK")
    print("-" * 70)
    total_pages = FacebookPage.objects.count()
    active_pages = FacebookPage.objects.filter(is_active=True).count()
    print(f"Total de páginas: {total_pages}")
    print(f"Páginas ativas: {active_pages}")

    if total_pages > 0:
        print("\nPáginas cadastradas:")
        for page in FacebookPage.objects.all()[:10]:
            status = "✅ Ativa" if page.is_active else "⏸️  Inativa"
            print(f"  • {page.name} ({page.followers_count} seguidores) - {status}")

    # Templates
    print("\n📝 TEMPLATES DE POSTS")
    print("-" * 70)
    total_templates = PostTemplate.objects.count()
    active_templates = PostTemplate.objects.filter(is_active=True).count()
    print(f"Total de templates: {total_templates}")
    print(f"Templates ativos: {active_templates}")

    if total_templates > 0:
        print("\nTemplates disponíveis:")
        for template in PostTemplate.objects.filter(is_active=True):
            print(f"  • {template.name} (Categoria: {template.category})")

    # Configurações de IA
    print("\n🤖 CONFIGURAÇÕES DE IA")
    print("-" * 70)
    ai_configs = AIConfiguration.objects.count()
    default_config = AIConfiguration.objects.filter(is_default=True).first()
    print(f"Total de configurações: {ai_configs}")
    if default_config:
        print(f"Configuração padrão: {default_config.name}")
        print(f"  • Provedor: {default_config.get_provider_display()}")
        print(f"  • Modelo: {default_config.model}")
        print(f"  • Temperature: {default_config.temperature}")
        print(f"  • Max Tokens: {default_config.max_tokens}")

    # Posts Agendados
    print("\n📅 POSTS AGENDADOS")
    print("-" * 70)
    scheduled = ScheduledPost.objects.count()
    by_status = {}
    for status, label in ScheduledPost.STATUS_CHOICES:
        count = ScheduledPost.objects.filter(status=status).count()
        if count > 0:
            by_status[label] = count

    print(f"Total de posts agendados: {scheduled}")
    if by_status:
        print("Por status:")
        for status_label, count in by_status.items():
            print(f"  • {status_label}: {count}")

    # Posts Publicados
    print("\n✅ POSTS PUBLICADOS")
    print("-" * 70)
    published = PublishedPost.objects.count()
    auto_generated = PublishedPost.objects.filter(auto_generated=True).count()
    print(f"Total de posts publicados: {published}")
    print(f"Posts gerados automaticamente: {auto_generated}")

    if published > 0:
        # Estatísticas
        from django.db.models import Sum, Avg

        stats = PublishedPost.objects.aggregate(
            total_likes=Sum("likes_count"),
            total_comments=Sum("comments_count"),
            total_shares=Sum("shares_count"),
            avg_likes=Avg("likes_count"),
            avg_comments=Avg("comments_count"),
        )

        print(f"\nEstatísticas de Engajamento:")
        print(f"  • Total de curtidas: {stats['total_likes'] or 0}")
        print(f"  • Total de comentários: {stats['total_comments'] or 0}")
        print(f"  • Total de compartilhamentos: {stats['total_shares'] or 0}")
        print(f"  • Média de curtidas por post: {stats['avg_likes'] or 0:.1f}")
        print(f"  • Média de comentários por post: {stats['avg_comments'] or 0:.1f}")

    # URLs disponíveis
    print("\n🔗 URLS DISPONÍVEIS")
    print("-" * 70)
    print("Dashboard: http://localhost:8000/")
    print("Admin: http://localhost:8000/admin/")
    print("Gerenciar Páginas: http://localhost:8000/pages/")
    print("Templates: http://localhost:8000/templates/")
    print("Posts Agendados: http://localhost:8000/scheduled/")
    print("Posts Publicados: http://localhost:8000/published/")
    print("Configurações IA: http://localhost:8000/ai-config/")

    # Status do Sistema
    print("\n⚙️  STATUS DO SISTEMA")
    print("-" * 70)

    # Verificar se há erros
    issues = []
    if total_users == 0:
        issues.append("⚠️  Nenhum usuário cadastrado")
    if total_pages == 0:
        issues.append("⚠️  Nenhuma página do Facebook cadastrada")
    if total_templates == 0:
        issues.append("⚠️  Nenhum template de post cadastrado")
    if not default_config:
        issues.append("⚠️  Nenhuma configuração de IA padrão")

    if issues:
        print("Avisos:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✅ Sistema configurado e pronto para uso!")

    print("\n" + "=" * 70)
    print("📋 Para começar a usar:")
    print("1. python manage.py runserver")
    print("2. Acesse http://localhost:8000/")
    print("3. Faça login com suas credenciais")
    print("4. Crie posts agendados em 'Posts Agendados'")
    print("=" * 70)


if __name__ == "__main__":
    generate_report()
