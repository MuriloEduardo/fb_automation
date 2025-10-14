from django.core.management.base import BaseCommand
from django.conf import settings
from facebook_integration.models_groups import FacebookGroup
from facebook_integration.services.groups_collector import GroupsCollector
from facebook_integration.services.facebook_api import FacebookAPIClient
from django.utils import timezone


class Command(BaseCommand):
    help = 'Sincroniza grupos do Facebook'

    def handle(self, *args, **options):
        self.stdout.write("Sincronizando grupos do Facebook...")
        
        try:
            user_token = settings.FACEBOOK_ACCESS_TOKEN
            api_client = FacebookAPIClient(user_token)
            groups_collector = GroupsCollector(api_client)
            
            result = groups_collector.get_user_groups()
            
            if result['status'] == 'no_permission':
                self.stdout.write(
                    self.style.WARNING(
                        "⚠️  Sem permissão para acessar grupos"
                    )
                )
                self.stdout.write(
                    "Adicione 'groups_access_member_info' ao token"
                )
                return
            
            if result['status'] != 'success':
                self.stdout.write(
                    self.style.ERROR(f"❌ Erro: {result.get('error')}")
                )
                return
            
            synced = 0
            updated = 0
            
            for group_data in result['groups']:
                group, created = FacebookGroup.objects.update_or_create(
                    group_id=group_data['group_id'],
                    defaults={
                        'name': group_data['name'],
                        'description': group_data.get('description', ''),
                        'privacy': group_data.get('privacy', 'CLOSED'),
                        'member_count': group_data.get('member_count', 0),
                        'cover_photo': group_data.get('cover_photo'),
                        'permalink_url': group_data.get('permalink_url'),
                        'can_publish': group_data.get('is_admin', False),
                        'can_read': True,
                        'last_sync': timezone.now(),
                    }
                )
                
                if created:
                    synced += 1
                    self.stdout.write(f"  ✅ {group_data['name']}")
                else:
                    updated += 1
                    self.stdout.write(f"  🔄 {group_data['name']}")
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Sucesso! {synced} novos, {updated} atualizados"
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Erro: {e}")
            )
