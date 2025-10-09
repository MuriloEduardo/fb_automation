import os
import base64
import openai
import logging
import requests
from uuid import uuid4
from typing import Dict, Any, Optional
from django.conf import settings
from ..models import AIConfiguration

logger = logging.getLogger(__name__)


class OpenAIService:
    """Serviço para integração com OpenAI API"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key não configurada")

        # Nova forma de configurar na versão 1.0+
        self.client = openai.OpenAI(api_key=self.api_key)

    def _get_ai_config(self) -> AIConfiguration:
        """Obtém a configuração padrão da IA ou cria uma se não existir"""
        config = AIConfiguration.objects.filter(is_default=True).first()
        if not config:
            config, created = AIConfiguration.objects.get_or_create(
                name="Configuração Padrão",
                defaults={
                    "is_default": True,
                    "model": "gpt-3.5-turbo",
                    "max_tokens": 500,
                    "temperature": 0.7,
                    "include_hashtags": True,
                    "max_hashtags": 5,
                    "include_emojis": True,
                },
            )
        return config

    def generate_post_content(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        ai_config: AIConfiguration = None,
    ) -> str:
        """Gera conteúdo para post usando OpenAI"""
        if not ai_config:
            ai_config = self._get_ai_config()

        # Constrói o prompt final
        system_prompt = self._build_system_prompt(ai_config)
        user_prompt = self._build_user_prompt(prompt, context, ai_config)

        try:
            response = self.client.chat.completions.create(
                model=ai_config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=ai_config.max_tokens,
                temperature=ai_config.temperature,
                n=1,
            )

            content = (response.choices[0].message.content or "").strip()
            logger.info(f"Conteúdo gerado com sucesso usando {ai_config.model}")
            return content

        except Exception as e:
            logger.error(f"Erro ao gerar conteúdo com OpenAI: {e}")
            raise OpenAIServiceException(f"Erro na geração de conteúdo: {str(e)}")

    def generate_image_prompt(
        self, post_content: str, ai_config: Optional[AIConfiguration] = None
    ) -> str:
        """Gera um prompt para criação de imagem baseado no conteúdo do post"""
        if not ai_config:
            ai_config = self._get_ai_config()

        system_prompt = (
            "Você é um especialista em criação de prompts para "
            "geração de imagens.\n"
            "Baseado no conteúdo de um post de rede social, crie um "
            "prompt detalhado para gerar uma imagem que complemente o "
            "post. O prompt deve ser em inglês, descritivo e "
            "específico."
        )

        user_prompt = (
            "Baseado neste conteúdo de post:\n"
            f'"{post_content}"\n\n'
            "Crie um prompt em inglês para gerar uma imagem que "
            "complemente este post.\n"
            "O prompt deve ser conciso (máximo 100 palavras) e incluir:\n"
            "- Estilo visual apropriado\n"
            "- Cores sugeridas\n"
            "- Elementos visuais relevantes\n"
            "- Atmosfera desejada\n\n"
            "Retorne apenas o prompt da imagem, sem explicações adicionais."
        )

        try:
            response = self.client.chat.completions.create(
                model=ai_config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=200,
                temperature=0.8,
                n=1,
            )

            image_prompt = (response.choices[0].message.content or "").strip()
            logger.info("Prompt de imagem gerado com sucesso")
            return image_prompt

        except Exception as e:
            logger.error(f"Erro ao gerar prompt de imagem: {e}")
            return ""

    def _build_system_prompt(self, ai_config: AIConfiguration) -> str:
        """Constrói o prompt do sistema baseado na configuração"""
        base_prompt = (
            "Você é um especialista em marketing digital e criação de "
            "conteúdo para redes sociais.\n"
            "Sua tarefa é criar posts envolventes, autênticos e "
            "adequados para o Facebook.\n\n"
            "Diretrizes:\n"
            "- Use uma linguagem natural e envolvente\n"
            "- Mantenha o tom profissional mas acessível\n"
            "- Evite excesso de jargões técnicos\n"
            "- Foque em valor para o leitor"
        )

        if ai_config.include_emojis:
            base_prompt += "\n- Use emojis de forma moderada e apropriada"

        if ai_config.include_hashtags:
            base_prompt += (
                "\n- Inclua no máximo " f"{ai_config.max_hashtags} hashtags relevantes"
            )

        base_prompt += (
            "\n\nRetorne apenas o conteúdo do post, sem " "explicações adicionais."
        )

        return base_prompt

    def _build_user_prompt(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]],
        ai_config: AIConfiguration,
    ) -> str:
        """Constrói o prompt do usuário com contexto adicional"""
        user_prompt = f"Crie um post para Facebook baseado neste tema:\n{prompt}"

        if context:
            user_prompt += "\n\nContexto adicional:"
            for key, value in context.items():
                user_prompt += f"\n- {key}: {value}"

        # Adiciona requisitos específicos
        requirements = []

        if ai_config.include_hashtags and ai_config.max_hashtags > 0:
            requirements.append(
                f"Inclua até {ai_config.max_hashtags} hashtags relevantes"
            )

        if ai_config.include_emojis:
            requirements.append("Use emojis apropriados")

        if requirements:
            user_prompt += "\n\nRequisitos:\n" + "\n".join(
                f"- {req}" for req in requirements
            )

        return user_prompt

    def generate_image_file(
        self,
        image_prompt: str,
        *,
        size: str = "1024x1024",
        image_format: str = "png",
        subdir: str = "generated_images",
        model: str = "gpt-image-1",
    ) -> Optional[str]:
        """Gera uma imagem usando a OpenAI Images API, salva em MEDIA_ROOT e
        retorna o caminho do arquivo. Retorna None se a geração falhar."""
        if not image_prompt:
            return None

        try:
            # Geração da imagem (API atual não aceita response_format)
            response = self.client.images.generate(
                model=model, prompt=image_prompt, size=size
            )

            data_list = getattr(response, "data", None)
            if not data_list or len(data_list) == 0:
                logger.error("Resposta de imagem sem dados da OpenAI")
                return None

            first_item = data_list[0]
            b64 = getattr(first_item, "b64_json", None)
            url = getattr(first_item, "url", None)

            # Preparar diretório em MEDIA_ROOT
            media_root = str(settings.MEDIA_ROOT)
            out_dir = os.path.join(media_root, subdir)
            
            try:
                os.makedirs(out_dir, mode=0o755, exist_ok=True)
            except PermissionError as perm_err:
                logger.error(
                    "Sem permissão para criar diretório %s: %s. "
                    "Execute: sudo chown -R $USER:$USER %s",
                    out_dir,
                    str(perm_err),
                    media_root,
                )
                return None

            filename = f"{uuid4().hex}.{image_format}"
            out_path = os.path.join(out_dir, filename)

            # Salvar arquivo (prioriza base64; se não houver, baixa URL)
            if b64:
                with open(out_path, "wb") as f:
                    f.write(base64.b64decode(b64))
            elif url:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                with open(out_path, "wb") as f:
                    f.write(resp.content)
            else:
                logger.error("Resposta de imagem sem b64_json ou url")
                return None

            logger.info(f"Imagem gerada e salva em: {out_path}")
            return out_path

        except Exception as e:
            logger.error(f"Erro ao gerar imagem com OpenAI: {e}")
            return None

    def test_connection(self) -> bool:
        """Testa a conexão com a API da OpenAI"""
        try:
            self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Teste"}],
                max_tokens=10,
            )
            return True
        except Exception as e:
            logger.error(f"Erro ao testar conexão OpenAI: {e}")
            return False


class OpenAIServiceException(Exception):
    """Exceção customizada para erros do serviço OpenAI"""

    pass
