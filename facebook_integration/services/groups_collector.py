from typing import Dict, List, Optional
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class GroupsCollector:
    """Service para coletar e gerenciar grupos do Facebook"""
    
    def __init__(self, api_client):
        self.api_client = api_client
    
    def get_user_groups(self) -> Dict:
        """
        Lista todos os grupos do usuário.
        Requer token de USUÁRIO, não de página.
        """
        endpoint = "me/groups"
        params = {
            'fields': (
                'id,name,description,privacy,member_count,'
                'cover,permalink_url,administrator,created_time'
            ),
        }
        
        try:
            response = self.api_client._make_request('GET', endpoint, params)
            
            groups = response.get('data', [])
            
            processed_groups = []
            for group in groups:
                processed_group = {
                    'group_id': group['id'],
                    'name': group['name'],
                    'description': group.get('description', ''),
                    'privacy': group.get('privacy', 'CLOSED'),
                    'member_count': group.get('member_count', 0),
                    'cover_photo': group.get('cover', {}).get('source'),
                    'permalink_url': group.get('permalink_url'),
                    'is_admin': group.get('administrator', False),
                    'created_time': group.get('created_time'),
                }
                processed_groups.append(processed_group)
            
            return {
                'status': 'success',
                'total_groups': len(processed_groups),
                'groups': processed_groups,
                'collected_at': timezone.now().isoformat(),
            }
            
        except Exception as e:
            error_str = str(e)
            
            if '403' in error_str or 'Forbidden' in error_str:
                logger.warning("Sem permissão para acessar grupos do usuário")
                return {
                    'status': 'no_permission',
                    'error': 'Permissão insuficiente para acessar grupos',
                    'groups': [],
                }
            
            logger.error(f"Erro ao buscar grupos do usuário: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'groups': [],
            }
    
    def get_group_info(self, group_id: str) -> Dict:
        """Obtém informações detalhadas de um grupo"""
        endpoint = f"{group_id}/"
        params = {
            'fields': (
                'id,name,description,privacy,member_count,'
                'cover,permalink_url,created_time,updated_time'
            ),
        }
        
        try:
            group = self.api_client._make_request('GET', endpoint, params)
            
            return {
                'status': 'success',
                'group': {
                    'group_id': group['id'],
                    'name': group['name'],
                    'description': group.get('description', ''),
                    'privacy': group.get('privacy', 'CLOSED'),
                    'member_count': group.get('member_count', 0),
                    'cover_photo': group.get('cover', {}).get('source'),
                    'permalink_url': group.get('permalink_url'),
                    'created_time': group.get('created_time'),
                    'updated_time': group.get('updated_time'),
                },
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar info do grupo {group_id}: {e}")
            return {
                'status': 'error',
                'error': str(e),
            }
    
    def check_group_permissions(self, group_id: str) -> Dict:
        """
        Verifica permissões em um grupo específico.
        Tenta publicar um post de teste (não publicado).
        """
        permissions = {
            'can_post': False,
            'can_read': False,
            'is_member': False,
            'is_admin': False,
        }
        
        # Verificar se consegue ler o grupo
        try:
            endpoint = f"{group_id}/"
            params = {'fields': 'id,name'}
            self.api_client._make_request('GET', endpoint, params)
            permissions['can_read'] = True
            permissions['is_member'] = True
        except Exception:
            pass
        
        # Verificar se consegue postar (teste sem publicar)
        try:
            endpoint = f"{group_id}/feed"
            test_data = {
                'message': 'TEST_POST_PERMISSION_CHECK',
                'published': False,
            }
            self.api_client._make_request('POST', endpoint, test_data)
            permissions['can_post'] = True
        except Exception:
            pass
        
        return {
            'status': 'success',
            'group_id': group_id,
            'permissions': permissions,
            'checked_at': timezone.now().isoformat(),
        }
    
    def get_group_feed(
        self, 
        group_id: str, 
        limit: int = 25
    ) -> Dict:
        """Obtém posts recentes de um grupo"""
        endpoint = f"{group_id}/feed"
        params = {
            'fields': (
                'id,message,created_time,updated_time,'
                'from,permalink_url,type,link,picture'
            ),
            'limit': limit,
        }
        
        try:
            response = self.api_client._make_request('GET', endpoint, params)
            
            posts = response.get('data', [])
            
            processed_posts = []
            for post in posts:
                processed_post = {
                    'post_id': post['id'],
                    'message': post.get('message', ''),
                    'created_time': post.get('created_time'),
                    'author_id': post.get('from', {}).get('id'),
                    'author_name': post.get('from', {}).get('name'),
                    'permalink_url': post.get('permalink_url'),
                    'type': post.get('type'),
                    'link': post.get('link'),
                    'picture': post.get('picture'),
                }
                processed_posts.append(processed_post)
            
            return {
                'status': 'success',
                'group_id': group_id,
                'total_posts': len(processed_posts),
                'posts': processed_posts,
                'collected_at': timezone.now().isoformat(),
            }
            
        except Exception as e:
            error_str = str(e)
            
            if '403' in error_str or 'Forbidden' in error_str:
                return {
                    'status': 'no_permission',
                    'group_id': group_id,
                    'error': 'Sem permissão para ler feed do grupo',
                    'posts': [],
                }
            
            logger.error(f"Erro ao buscar feed do grupo {group_id}: {e}")
            return {
                'status': 'error',
                'group_id': group_id,
                'error': str(e),
                'posts': [],
            }
    
    def publish_to_group(
        self, 
        group_id: str, 
        message: str,
        link: Optional[str] = None,
        image_path: Optional[str] = None
    ) -> Dict:
        """Publica um post em um grupo"""
        endpoint = f"{group_id}/feed"
        
        data = {'message': message}
        
        if link:
            data['link'] = link
        
        files = None
        if image_path:
            try:
                files = {'source': open(image_path, 'rb')}
            except Exception as e:
                logger.error(f"Erro ao abrir imagem {image_path}: {e}")
        
        try:
            response = self.api_client._make_request(
                'POST', 
                endpoint, 
                data,
                files=files
            )
            
            return {
                'status': 'success',
                'group_id': group_id,
                'post_id': response.get('id'),
                'published_at': timezone.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Erro ao publicar no grupo {group_id}: {e}")
            return {
                'status': 'error',
                'group_id': group_id,
                'error': str(e),
            }
        finally:
            if files:
                files['source'].close()
