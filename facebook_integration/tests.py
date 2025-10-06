from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch, MagicMock
from .models import (
    FacebookPage,
    PostTemplate,
    ScheduledPost,
    AIConfiguration,
    PublishedPost,
)
from .services.facebook_api import FacebookAPIClient, FacebookAPIException
from .services.openai_service import OpenAIService, OpenAIServiceException
import json


class FacebookPageModelTest(TestCase):
    """Testes para o model FacebookPage"""

    def setUp(self):
        self.page = FacebookPage.objects.create(
            name="Página Teste",
            page_id="123456789",
            access_token="fake_token",
            is_active=True,
        )

    def test_facebook_page_creation(self):
        """Testa criação de página do Facebook"""
        self.assertEqual(self.page.name, "Página Teste")
        self.assertEqual(self.page.page_id, "123456789")
        self.assertTrue(self.page.is_active)
        self.assertEqual(str(self.page), "Página Teste")


class PostTemplateModelTest(TestCase):
    """Testes para o model PostTemplate"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.template = PostTemplate.objects.create(
            name="Template Teste",
            prompt="Crie um post sobre {topic}",
            category="marketing",
            created_by=self.user,
        )

    def test_template_creation(self):
        """Testa criação de template"""
        self.assertEqual(self.template.name, "Template Teste")
        self.assertEqual(self.template.category, "marketing")
        self.assertTrue(self.template.is_active)
        self.assertEqual(str(self.template), "Template Teste")


class ScheduledPostModelTest(TestCase):
    """Testes para o model ScheduledPost"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.page = FacebookPage.objects.create(
            name="Página Teste", page_id="123456789", access_token="fake_token"
        )
        self.template = PostTemplate.objects.create(
            name="Template Teste",
            prompt="Teste prompt",
            category="teste",
            created_by=self.user,
        )
        self.scheduled_post = ScheduledPost.objects.create(
            facebook_page=self.page,
            template=self.template,
            scheduled_time=timezone.now() + timezone.timedelta(hours=1),
            created_by=self.user,
        )

    def test_scheduled_post_creation(self):
        """Testa criação de post agendado"""
        self.assertEqual(self.scheduled_post.status, "pending")
        self.assertEqual(self.scheduled_post.facebook_page, self.page)
        self.assertEqual(self.scheduled_post.template, self.template)

    def test_is_due_property(self):
        """Testa propriedade is_due"""
        # Post no futuro
        self.assertFalse(self.scheduled_post.is_due)

        # Post no passado com status ready
        past_post = ScheduledPost.objects.create(
            facebook_page=self.page,
            template=self.template,
            scheduled_time=timezone.now() - timezone.timedelta(hours=1),
            status="ready",
            created_by=self.user,
        )
        self.assertTrue(past_post.is_due)


class FacebookAPIClientTest(TestCase):
    """Testes para o cliente da API do Facebook"""

    def setUp(self):
        self.client = FacebookAPIClient(access_token="fake_token", page_id="123456789")

    @patch("requests.get")
    def test_get_page_info_success(self, mock_get):
        """Testa obtenção de informações da página"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "123456789",
            "name": "Página Teste",
            "category": "Business",
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = self.client.get_page_info()

        self.assertEqual(result["name"], "Página Teste")
        self.assertEqual(result["id"], "123456789")

    @patch("requests.get")
    def test_validate_access_token_success(self, mock_get):
        """Testa validação de token válido"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "user123", "name": "Usuario"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = self.client.validate_access_token()

        self.assertTrue(result)

    @patch("requests.get")
    def test_validate_access_token_failure(self, mock_get):
        """Testa validação de token inválido"""
        mock_get.side_effect = Exception("Token inválido")

        result = self.client.validate_access_token()

        self.assertFalse(result)


class OpenAIServiceTest(TestCase):
    """Testes para o serviço OpenAI"""

    def setUp(self):
        # Cria configuração padrão
        self.ai_config = AIConfiguration.objects.create(
            name="Teste Config",
            model="gpt-3.5-turbo",
            max_tokens=500,
            temperature=0.7,
            is_default=True,
        )

    @patch("openai.ChatCompletion.create")
    def test_generate_post_content_success(self, mock_openai):
        """Testa geração de conteúdo com sucesso"""
        mock_openai.return_value = MagicMock()
        mock_openai.return_value.choices = [
            MagicMock(message=MagicMock(content="Conteúdo gerado pela IA"))
        ]

        service = OpenAIService(api_key="fake_key")
        result = service.generate_post_content("Criar post sobre tecnologia")

        self.assertEqual(result, "Conteúdo gerado pela IA")

    @patch("openai.ChatCompletion.create")
    def test_generate_post_content_failure(self, mock_openai):
        """Testa falha na geração de conteúdo"""
        mock_openai.side_effect = Exception("API Error")

        service = OpenAIService(api_key="fake_key")

        with self.assertRaises(OpenAIServiceException):
            service.generate_post_content("Criar post sobre tecnologia")


class ViewsTest(TestCase):
    """Testes para as views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.page = FacebookPage.objects.create(
            name="Página Teste", page_id="123456789", access_token="fake_token"
        )

    def test_dashboard_view(self):
        """Testa view do dashboard"""
        response = self.client.get(reverse("facebook_integration:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")
        self.assertContains(response, "Páginas Ativas")

    def test_facebook_pages_view_requires_login(self):
        """Testa que view de páginas requer login"""
        response = self.client.get(reverse("facebook_integration:facebook_pages"))

        # Deve redirecionar para login
        self.assertEqual(response.status_code, 302)

    def test_facebook_pages_view_authenticated(self):
        """Testa view de páginas com usuário autenticado"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("facebook_integration:facebook_pages"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Página Teste")

    def test_create_template_post(self):
        """Testa criação de template via POST"""
        self.client.login(username="testuser", password="testpass123")

        data = {
            "name": "Novo Template",
            "prompt": "Prompt de teste",
            "category": "teste",
        }

        response = self.client.post(
            reverse("facebook_integration:create_template"), data
        )

        self.assertEqual(response.status_code, 302)  # Redirect após sucesso
        self.assertTrue(PostTemplate.objects.filter(name="Novo Template").exists())


class TasksTest(TestCase):
    """Testes para as tasks do Celery"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.page = FacebookPage.objects.create(
            name="Página Teste", page_id="123456789", access_token="fake_token"
        )
        self.template = PostTemplate.objects.create(
            name="Template Teste",
            prompt="Teste prompt",
            category="teste",
            created_by=self.user,
        )

    @patch(
        "facebook_integration.services.openai_service.OpenAIService.generate_post_content"
    )
    @patch(
        "facebook_integration.services.openai_service.OpenAIService.generate_image_prompt"
    )
    def test_generate_content_for_post_success(self, mock_image_prompt, mock_content):
        """Testa geração de conteúdo para post"""
        from .tasks import generate_content_for_post

        mock_content.return_value = "Conteúdo gerado"
        mock_image_prompt.return_value = "Prompt da imagem"

        # Cria post agendado
        scheduled_post = ScheduledPost.objects.create(
            facebook_page=self.page,
            template=self.template,
            scheduled_time=timezone.now() + timezone.timedelta(hours=1),
            created_by=self.user,
        )

        # Executa task
        result = generate_content_for_post(scheduled_post.id)

        # Recarrega do banco
        scheduled_post.refresh_from_db()

        self.assertEqual(scheduled_post.generated_content, "Conteúdo gerado")
        self.assertEqual(scheduled_post.generated_image_prompt, "Prompt da imagem")
        self.assertEqual(scheduled_post.status, "ready")
        self.assertIn("Conteúdo gerado para post", result)


class IntegrationTest(TestCase):
    """Testes de integração end-to-end"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.page = FacebookPage.objects.create(
            name="Página Teste", page_id="123456789", access_token="fake_token"
        )
        self.template = PostTemplate.objects.create(
            name="Template Teste",
            prompt="Crie um post sobre {topic}",
            category="tecnologia",
            created_by=self.user,
        )
        # Configuração padrão de IA
        AIConfiguration.objects.create(name="Config Padrão", is_default=True)

    def test_complete_post_workflow(self):
        """Testa fluxo completo de criação e agendamento de post"""
        self.client.login(username="testuser", password="testpass123")

        # 1. Cria post agendado
        scheduled_time = (timezone.now() + timezone.timedelta(hours=1)).isoformat()
        data = {
            "facebook_page": self.page.id,
            "template": self.template.id,
            "scheduled_time": scheduled_time,
        }

        response = self.client.post(
            reverse("facebook_integration:create_scheduled_post"), data
        )

        self.assertEqual(response.status_code, 302)

        # 2. Verifica que post foi criado
        scheduled_post = ScheduledPost.objects.filter(
            facebook_page=self.page, template=self.template
        ).first()

        self.assertIsNotNone(scheduled_post)
        self.assertEqual(scheduled_post.status, "pending")

        # 3. Testa geração de prévia de conteúdo
        preview_data = {
            "template_id": self.template.id,
            "context": {"topic": "inteligência artificial"},
        }

        with patch(
            "facebook_integration.services.openai_service.OpenAIService.generate_post_content"
        ) as mock_content:
            with patch(
                "facebook_integration.services.openai_service.OpenAIService.generate_image_prompt"
            ) as mock_image:
                mock_content.return_value = "Post sobre IA gerado"
                mock_image.return_value = "Imagem de IA"

                response = self.client.post(
                    reverse("facebook_integration:generate_content_preview"),
                    json.dumps(preview_data),
                    content_type="application/json",
                )

                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data["success"])
                self.assertEqual(data["content"], "Post sobre IA gerado")
                self.assertEqual(data["image_prompt"], "Imagem de IA")
