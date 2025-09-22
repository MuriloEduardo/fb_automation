from django.core.management.base import BaseCommand
from facebook_integration.tasks import (
    process_scheduled_posts, 
    schedule_content_generation,
    update_post_metrics
)


class Command(BaseCommand):
    help = 'Executa tasks de automação do Facebook'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            type=str,
            help='Especifica qual task executar',
            choices=['process_posts', 'generate_content', 'update_metrics', 'all'],
            default='all'
        )
    
    def handle(self, *args, **options):
        task = options['task']
        
        self.stdout.write(
            self.style.SUCCESS(f'Executando task: {task}')
        )
        
        if task == 'process_posts' or task == 'all':
            self.stdout.write('Processando posts agendados...')
            result = process_scheduled_posts()
            self.stdout.write(self.style.SUCCESS(result))
        
        if task == 'generate_content' or task == 'all':
            self.stdout.write('Agendando geração de conteúdo...')
            result = schedule_content_generation()
            self.stdout.write(self.style.SUCCESS(result))
        
        if task == 'update_metrics' or task == 'all':
            self.stdout.write('Atualizando métricas...')
            result = update_post_metrics()
            self.stdout.write(self.style.SUCCESS(result))
        
        self.stdout.write(
            self.style.SUCCESS('Tasks executadas com sucesso!')
        )