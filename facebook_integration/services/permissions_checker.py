from typing import Dict, List, Optional
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class PermissionsChecker:
    
    AVAILABLE_PERMISSIONS = {
        'pages_read_engagement': 'Ler métricas de engajamento',
        'pages_read_user_content': 'Ler conteúdo de usuários',
        'pages_manage_posts': 'Gerenciar posts',
        'pages_manage_engagement': 'Gerenciar engajamento',
        'pages_show_list': 'Listar páginas',
        'leads_retrieval': 'Recuperar leads',
        'pages_manage_metadata': 'Gerenciar metadados',
        'pages_messaging': 'Enviar mensagens',
        'business_management': 'Gerenciar negócios',
        'instagram_basic': 'Instagram básico',
        'instagram_content_publish': 'Publicar no Instagram',
        'read_insights': 'Ler insights',
        'ads_read': 'Ler anúncios',
    }
    
    def __init__(self, api_client):
        self.api_client = api_client
    
    def check_all_permissions(self, page_id: str) -> Dict:
        """
        Verifica as capabilities da página.
        Nota: O campo 'tasks' só está disponível via me/accounts,
        não via /{page_id}
        """
        endpoint = f"{page_id}/"
        params = {
            'fields': 'id,name,about,category,fan_count',
        }
        
        try:
            response = self.api_client._make_request('GET', endpoint, params)
            
            # Tasks não estão disponíveis neste endpoint
            # Vamos verificar outras formas
            permissions = {
                'can_analyze': True,
                'can_advertise': False,
                'can_moderate': True,
                'can_create_content': True,
                'can_manage': True,
                'can_messaging': False,
                'raw_tasks': [],
                'note': 'Tasks não disponíveis via /{page_id}',
            }
            
            return {
                'status': 'success',
                'page_id': page_id,
                'page_name': response.get('name'),
                'page_category': response.get('category'),
                'page_fans': response.get('fan_count', 0),
                'permissions': permissions,
                'checked_at': timezone.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar permissões da página {page_id}: {e}")
            return {
                'status': 'error',
                'page_id': page_id,
                'error': str(e),
                'permissions': {},
            }
    
    def check_token_permissions(self) -> Dict:
        """
        Verifica permissões do token.
        NOTA: Só funciona com token de usuário, não com token de página.
        """
        endpoint = "me/permissions"
        
        try:
            response = self.api_client._make_request('GET', endpoint, {})
            
            granted_permissions = []
            declined_permissions = []
            
            for perm in response.get('data', []):
                if perm.get('status') == 'granted':
                    granted_permissions.append(perm.get('permission'))
                else:
                    declined_permissions.append(perm.get('permission'))
            
            permissions_details = {}
            for perm in granted_permissions:
                permissions_details[perm] = {
                    'granted': True,
                    'description': self.AVAILABLE_PERMISSIONS.get(
                        perm, 
                        'Permissão não documentada'
                    )
                }
            
            return {
                'status': 'success',
                'granted': granted_permissions,
                'declined': declined_permissions,
                'details': permissions_details,
                'total_granted': len(granted_permissions),
                'total_declined': len(declined_permissions),
                'checked_at': timezone.now().isoformat(),
            }
            
        except Exception as e:
            error_str = str(e)
            
            if '400' in error_str or 'Bad Request' in error_str:
                logger.warning(
                    "Token de página não pode verificar me/permissions"
                )
                return {
                    'status': 'not_applicable',
                    'note': 'Token de página não suporta me/permissions',
                    'granted': [],
                    'declined': [],
                }
            
            logger.error(f"Erro ao verificar permissões do token: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'granted': [],
                'declined': [],
            }
    
    def get_available_insights_metrics(self) -> List[str]:
        return [
            'page_impressions',
            'page_impressions_unique',
            'page_impressions_paid',
            'page_impressions_organic',
            'page_impressions_viral',
            'page_engaged_users',
            'page_post_engagements',
            'page_fans',
            'page_fans_online',
            'page_fan_adds',
            'page_fan_removes',
            'page_views_total',
            'page_views_logged_in_unique',
            'page_posts_impressions',
            'page_posts_impressions_unique',
            'page_posts_impressions_paid',
            'page_posts_impressions_organic',
            'page_posts_impressions_viral',
            'page_actions_post_reactions_total',
            'page_negative_feedback',
            'page_positive_feedback',
            'page_fans_by_like_source',
            'page_fan_adds_unique',
            'page_fans_country',
            'page_fans_city',
            'page_fans_gender_age',
            'page_impressions_by_age_gender_unique',
            'page_video_views',
            'page_video_views_paid',
            'page_video_views_organic',
        ]
    
    def check_insights_access(self, page_id: str) -> Dict:
        endpoint = f"{page_id}/insights"
        params = {
            'metric': 'page_impressions',
            'period': 'day',
            'since': '2025-10-13',
            'until': '2025-10-14',
        }
        
        try:
            response = self.api_client._make_request('GET', endpoint, params)
            
            has_access = 'data' in response and len(response['data']) > 0
            
            return {
                'status': 'success',
                'page_id': page_id,
                'insights_access': has_access,
                'available_metrics': self.get_available_insights_metrics() if has_access else [],
                'checked_at': timezone.now().isoformat(),
            }
            
        except Exception as e:
            logger.warning(f"Sem acesso a insights da página {page_id}: {e}")
            return {
                'status': 'no_access',
                'page_id': page_id,
                'insights_access': False,
                'error': str(e),
            }
    
    def check_leadgen_access(self, page_id: str) -> Dict:
        endpoint = f"{page_id}/leadgen_forms"
        params = {
            'fields': 'id,name,status,leads_count',
        }
        
        try:
            response = self.api_client._make_request('GET', endpoint, params)
            
            forms = response.get('data', [])
            
            return {
                'status': 'success',
                'page_id': page_id,
                'leadgen_access': True,
                'total_forms': len(forms),
                'forms': forms,
                'checked_at': timezone.now().isoformat(),
            }
            
        except Exception as e:
            logger.warning(f"Sem acesso a leadgen da página {page_id}: {e}")
            return {
                'status': 'no_access',
                'page_id': page_id,
                'leadgen_access': False,
                'error': str(e),
            }
    
    def get_full_capabilities(self, page_id: str) -> Dict:
        capabilities = {
            'page_id': page_id,
            'checked_at': timezone.now().isoformat(),
        }
        
        capabilities['permissions'] = self.check_all_permissions(page_id)
        capabilities['insights'] = self.check_insights_access(page_id)
        capabilities['leadgen'] = self.check_leadgen_access(page_id)
        capabilities['token_permissions'] = self.check_token_permissions()
        
        capabilities['summary'] = {
            'can_read_insights': capabilities['insights'].get('insights_access', False),
            'can_read_leads': capabilities['leadgen'].get('leadgen_access', False),
            'total_permissions': capabilities['token_permissions'].get('total_granted', 0),
            'total_leadgen_forms': capabilities['leadgen'].get('total_forms', 0),
        }
        
        return capabilities
