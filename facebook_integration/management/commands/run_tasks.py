from django.core.management.base import BaseCommand
from django.utils import timezone
from facebook_integration.models import ScheduledPost, PostTemplate
from facebook_integration.tasks import (
    generate_content_for_post, 
    publish_post_task,
    process_scheduled_posts
)
from facebook_integration.models_celery import CeleryTaskTemplate
import json


class Command(BaseCommand):
    help = 'Executa tasks do Celery e gerencia o fluxo de posts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['generate', 'publish', 'process', 'create-template', 'list-tasks'],
            help='Ação a ser executada'
        )
        parser.add_argument(
            '--post-id',
            type=int,
            help='ID do post para ações específicas'
        )
        parser.add_argument(
            '--template-id',
            type=int,
            help='ID do template para criar posts'
        )

    def handle(self, *args, **options):
        action = options.get('action')
        
        if action == 'generate':
            self.generate_content(options.get('post_id'))
        elif action == 'publish':
            self.publish_post(options.get('post_id'))
        elif action == 'process':
            self.process_pending_posts()
        elif action == 'create-template':
            self.create_task_templates()
        elif action == 'list-tasks':
            self.list_active_tasks()
        else:
            self.show_help()

    def generate_content(self, post_id):
        """Gera conteúdo para um post específico"""
        if not post_id:
            self.stdout.write(
                self.style.ERROR('É necessário fornecer --post-id')
            )
            return

        try:
            post = ScheduledPost.objects.get(id=post_id)
            self.stdout.write(f'📝 Gerando conteúdo para post {post_id}...')
            
            task = generate_content_for_post.delay(post_id)
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Task iniciada: {task.id}')
            )
        except ScheduledPost.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Post {post_id} não encontrado')
            )

    def publish_post(self, post_id):
        """Publica um post específico"""
        if not post_id:
            self.stdout.write(
                self.style.ERROR('É necessário fornecer --post-id')
            )
            return

        try:
            post = ScheduledPost.objects.get(id=post_id)
            self.stdout.write(f'🚀 Publicando post {post_id}...')
            
            task = publish_post_task.delay(post_id)
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Task iniciada: {task.id}')
            )
        except ScheduledPost.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Post {post_id} não encontrado')
            )

    def process_pending_posts(self):
        """Processa todos os posts pendentes"""
        self.stdout.write('⚡ Processando posts pendentes...')
        
        task = process_scheduled_posts.delay()
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Task iniciada: {task.id}')
        )

    def create_task_templates(self):
        """Cria templates de tasks comuns"""
        templates_data = [
            {
                'name': 'Gerar Conteúdo',
                'task_name': 'facebook_integration.tasks.generate_content_for_post',
                'description': 'Gera conteúdo usando IA para um post agendado',
                'default_args': '[]',
                'default_kwargs': '{}'
            },
            {
                'name': 'Publicar Post',
                'task_name': 'facebook_integration.tasks.publish_post_task',
                'description': 'Publica um post no Facebook',
                'default_args': '[]',
                'default_kwargs': '{}'
            },
            {
                'name': 'Processar Posts Pendentes',
                'task_name': 'facebook_integration.tasks.process_scheduled_posts',
                'description': 'Processa todos os posts prontos para publicação',
                'default_args': '[]',
                'default_kwargs': '{}'
            }
        ]

        created_count = 0
        for template_data in templates_data:
            template, created = CeleryTaskTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults=template_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Template "{template.name}" criado')
                )
            else:
                self.stdout.write(f'📋 Template "{template.name}" já existe')

        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 {created_count} templates criados!')
        )

    def list_active_tasks(self):
        """Lista tasks ativas no sistema"""
        from facebook_integration.models_celery import CeleryTask
        
        active_tasks = CeleryTask.objects.filter(
            status__in=['PENDING', 'RECEIVED', 'STARTED']
        ).order_by('-created_at')

        if not active_tasks:
            self.stdout.write('📋 Nenhuma task ativa encontrada')
            return

        self.stdout.write('\n📊 TASKS ATIVAS:')
        self.stdout.write('-' * 60)
        
        for task in active_tasks:
            duration = ''
            if task.started_at:
                elapsed = timezone.now() - task.started_at
                duration = f' ({elapsed.seconds}s)'
            
            self.stdout.write(
                f'🔄 {task.task_name} | {task.status}{duration}'
            )
            if task.scheduled_post:
                self.stdout.write(
                    f'   📱 Post: {task.scheduled_post.facebook_page.name}'
                )

    def show_help(self):
        """Mostra ajuda de uso"""
        self.stdout.write('\n🤖 GERENCIADOR DE TASKS DO CELERY')
        self.stdout.write('=' * 50)
        self.stdout.write('\nComandos disponíveis:')
        self.stdout.write('  --action generate --post-id ID    | Gerar conteúdo')
        self.stdout.write('  --action publish --post-id ID     | Publicar post') 
        self.stdout.write('  --action process                  | Processar pendentes')
        self.stdout.write('  --action create-template          | Criar templates')
        self.stdout.write('  --action list-tasks               | Listar tasks ativas')
        self.stdout.write('\n📖 Exemplos:')
        self.stdout.write('  python manage.py run_tasks --action process')
        self.stdout.write('  python manage.py run_tasks --action generate --post-id 1')
        self.stdout.write('  python manage.py run_tasks --action create-template')