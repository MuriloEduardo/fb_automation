from django.core.management.base import BaseCommand
from django.conf import settings
from facebook_integration.models import FacebookPage
import requests


class Command(BaseCommand):
    help = 'Ressincroniza tokens das páginas do Facebook'

    def handle(self, *args, **options):
        self.stdout.write("Ressincronizando páginas...")
        
        try:
            user_token = settings.FACEBOOK_ACCESS_TOKEN
            
            url = "https://graph.facebook.com/v23.0/me/accounts"
            params = {
                'access_token': user_token,
                'fields': 'id,name,access_token,category,fan_count,tasks',
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                self.stdout.write(
                    self.style.ERROR(
                        f"Erro na API: {response.text}"
                    )
                )
                return
            
            data = response.json()
            pages_data = data.get('data', [])
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nEncontradas {len(pages_data)} páginas\n"
                )
            )
            
            for page_data in pages_data:
                page_id = page_data['id']
                page_name = page_data['name']
                page_token = page_data['access_token']
                
                page, created = FacebookPage.objects.get_or_create(
                    page_id=page_id
                )
                
                old_token = page.access_token
                page.access_token = page_token
                page.name = page_name
                page.save()
                
                status = "CRIADA" if created else "ATUALIZADA"
                
                self.stdout.write(
                    f"  [{status}] {page_name} (ID: {page_id})"
                )
                
                if not created and old_token != page_token:
                    self.stdout.write(
                        self.style.WARNING(
                            f"    ⚠️  Token atualizado (mudou)"
                        )
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Sincronização concluída!"
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Erro: {e}")
            )
