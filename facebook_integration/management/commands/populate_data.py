from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from facebook_integration.models import PostTemplate, AIConfiguration


class Command(BaseCommand):
    help = "Popula o banco de dados com dados iniciais para demonstração"

    def handle(self, *args, **options):
        self.stdout.write("Populando dados iniciais...")

        # Criar usuário admin se não existir
        if not User.objects.filter(username="admin").exists():
            admin_user = User.objects.create_superuser(
                username="admin", email="admin@example.com", password="admin123"
            )
            self.stdout.write(
                self.style.SUCCESS("✅ Usuário admin criado (admin/admin123)")
            )
        else:
            admin_user = User.objects.get(username="admin")
            self.stdout.write("📋 Usuário admin já existe")

        # Criar configuração padrão de IA
        ai_config, created = AIConfiguration.objects.get_or_create(
            is_default=True,
            defaults={
                "name": "Configuração Padrão",
                "model": "gpt-3.5-turbo",
                "max_tokens": 500,
                "temperature": 0.7,
                "include_hashtags": True,
                "max_hashtags": 5,
                "include_emojis": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("✅ Configuração de IA criada"))
        else:
            self.stdout.write("📋 Configuração de IA já existe")

        # Templates de exemplo
        templates_data = [
            {
                "name": "Post Motivacional",
                "category": "Motivação",
                "prompt": "Crie um post motivacional para redes sociais sobre superação e determinação. Use linguagem inspiradora e inclua hashtags relevantes. Mantenha o tom positivo e energético.",
            },
            {
                "name": "Dica de Tecnologia",
                "category": "Tecnologia",
                "prompt": "Crie um post sobre uma dica útil de tecnologia ou produtividade. Explique de forma simples e clara, incluindo benefícios práticos. Use hashtags relacionadas à tecnologia.",
            },
            {
                "name": "Curiosidade do Dia",
                "category": "Educativo",
                "prompt": "Compartilhe uma curiosidade interessante e educativa. Pode ser sobre ciência, história, natureza ou qualquer tópico fascinante. Mantenha o tom informativo mas divertido.",
            },
            {
                "name": "Reflexão Profissional",
                "category": "Carreira",
                "prompt": "Crie um post reflexivo sobre desenvolvimento profissional, liderança ou habilidades de carreira. Use linguagem profissional mas acessível, com insights valiosos.",
            },
            {
                "name": "Frase Inspiradora",
                "category": "Inspiração",
                "prompt": "Crie um post com uma frase inspiradora original sobre crescimento pessoal, sucesso ou realização de sonhos. Complemente com uma reflexão breve e hashtags motivacionais.",
            },
        ]

        for template_data in templates_data:
            template, created = PostTemplate.objects.get_or_create(
                name=template_data["name"],
                defaults={
                    "category": template_data["category"],
                    "prompt": template_data["prompt"],
                    "created_by": admin_user,
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Template "{template.name}" criado')
                )
            else:
                self.stdout.write(f'📋 Template "{template.name}" já existe')

        self.stdout.write(
            self.style.SUCCESS(
                "\n🎉 Dados iniciais populados com sucesso!\n"
                "📱 Acesse: http://localhost:8000\n"
                "👤 Admin: http://localhost:8000/admin (admin/admin123)\n"
                "📄 Páginas: http://localhost:8000/pages\n"
            )
        )
