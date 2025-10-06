import requests
import logging
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class FacebookAPIClient:
    """Cliente para interagir com a Facebook Graph API"""

    def __init__(self, access_token: str = None, page_id: str = None):
        self.access_token = access_token or settings.FACEBOOK_ACCESS_TOKEN
        self.page_id = page_id or settings.FACEBOOK_PAGE_ID
        self.base_url = "https://graph.facebook.com/v18.0"

    def _make_request(
        self, method: str, endpoint: str, data: Dict = None, files: Dict = None
    ) -> Dict[str, Any]:
        """Faz uma requisição para a API do Facebook"""
        url = f"{self.base_url}/{endpoint}"

        # Adiciona o token de acesso nos parâmetros
        if data is None:
            data = {}
        data["access_token"] = self.access_token

        try:
            if method.upper() == "GET":
                response = requests.get(url, params=data)
            elif method.upper() == "POST":
                if files:
                    response = requests.post(url, data=data, files=files)
                else:
                    response = requests.post(url, data=data)
            else:
                raise ValueError(f"Método HTTP não suportado: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição para Facebook API: {e}")
            raise FacebookAPIException(f"Erro na API do Facebook: {str(e)}")

    def get_page_info(self, page_id: str = None) -> Dict[str, Any]:
        """Obtém informações da página do Facebook"""
        target_page_id = page_id or self.page_id
        endpoint = f"{target_page_id}"
        params = {"fields": "id,name,category,fan_count,followers_count,link"}
        return self._make_request("GET", endpoint, params)

    def test_publish_permission(self, page_id: str = None) -> bool:
        """Testa se é possível publicar na página"""
        try:
            target_page_id = page_id or self.page_id
            endpoint = f"{target_page_id}/feed"
            
            # Fazer uma requisição POST de teste sem publicar
            test_data = {
                "message": "TEST_POST_PERMISSION_CHECK",
                "published": False  # Não publica o post
            }
            
            result = self._make_request("POST", endpoint, test_data)
            return True  # Se chegou até aqui, tem permissão
            
        except Exception as e:
            logger.warning(f"Teste de permissão de publicação falhou: {e}")
            return False

    def test_insights_permission(self, page_id: str = None) -> bool:
        """Testa se é possível ler insights da página"""
        try:
            target_page_id = page_id or self.page_id
            endpoint = f"{target_page_id}/insights"
            params = {"metric": "page_fan_adds", "period": "day"}
            
            self._make_request("GET", endpoint, params)
            return True
            
        except Exception as e:
            logger.warning(f"Teste de permissão de insights falhou: {e}")
            return False

    def get_user_pages(self) -> Dict[str, Any]:
        """Obtém todas as páginas que o usuário administra"""
        endpoint = "me/accounts"
        params = {
            "fields": "id,name,access_token,category,fan_count,tasks"
        }
        return self._make_request("GET", endpoint, params)

    def create_post(
        self, message: str, image_path: str = None, link: str = None
    ) -> Dict[str, Any]:
        """Cria um post na página do Facebook"""
        endpoint = f"{self.page_id}/feed"

        data = {"message": message}

        if link:
            data["link"] = link

        files = None
        if image_path:
            # Se há uma imagem, usa o endpoint de photos
            endpoint = f"{self.page_id}/photos"
            data["caption"] = message
            try:
                with open(image_path, "rb") as img:
                    files = {"source": img}
                    return self._make_request("POST", endpoint, data, files)
            except FileNotFoundError:
                logger.error(f"Arquivo de imagem não encontrado: {image_path}")
                raise FacebookAPIException(f"Imagem não encontrada: {image_path}")

        return self._make_request("POST", endpoint, data)

    def get_post_insights(self, post_id: str) -> Dict[str, Any]:
        """Obtém métricas de um post específico"""
        endpoint = f"{post_id}/insights"
        params = {"metric": "post_impressions,post_engaged_users,post_clicks"}
        return self._make_request("GET", endpoint, params)

    def get_post_details(self, post_id: str) -> Dict[str, Any]:
        """Obtém detalhes de um post específico"""
        endpoint = f"{post_id}"
        params = {
            "fields": "id,message,created_time,permalink_url,likes.summary(true),comments.summary(true),shares"
        }
        return self._make_request("GET", endpoint, params)

    def validate_access_token(self) -> bool:
        """Valida se o token de acesso está válido"""
        try:
            endpoint = "me"
            params = {"fields": "id,name"}
            result = self._make_request("GET", endpoint, params)
            return "id" in result
        except FacebookAPIException:
            return False

    def get_page_access_token(self, user_access_token: str) -> Optional[str]:
        """Obtém o token de acesso da página usando um token de usuário"""
        try:
            endpoint = "me/accounts"
            params = {
                "access_token": user_access_token,
                "fields": "id,name,access_token",
            }

            # Temporariamente usa o token do usuário
            original_token = self.access_token
            self.access_token = user_access_token

            result = self._make_request("GET", endpoint, params)

            # Restaura o token original
            self.access_token = original_token

            # Procura pela página específica
            for page in result.get("data", []):
                if page["id"] == self.page_id:
                    return page["access_token"]

            return None

        except FacebookAPIException as e:
            logger.error(f"Erro ao obter token da página: {e}")
            return None


class FacebookAPIException(Exception):
    """Exceção customizada para erros da API do Facebook"""

    pass
