import logging
from typing import Optional

from .openai_service import OpenAIService
from . import gemini_service

logger = logging.getLogger(__name__)


def generate_image_with_fallback(
    image_prompt: str,
    *,
    size: str = "1024x1024",
    image_format: str = "png",
    subdir: str = "generated_images",
) -> Optional[str]:
    if not image_prompt:
        return None

    try:
        openai_service = OpenAIService()
        path = openai_service.generate_image_file(
            image_prompt, size=size, image_format=image_format, subdir=subdir
        )
        if path:
            logger.info("Imagem gerada com sucesso usando OpenAI")
            return path
        logger.warning("OpenAI retornou None, tentando Gemini")
    except Exception as e:
        logger.warning("OpenAI falhou (%s), tentando Gemini", str(e))

    try:
        path = gemini_service.generate_image_file(
            image_prompt, size=size, image_format=image_format, subdir=subdir
        )
        if path:
            logger.info("Imagem gerada com sucesso usando Gemini")
            return path
        logger.error("Gemini também retornou None")
    except Exception as e:
        logger.error("Gemini também falhou: %s", str(e))

    logger.error("Todos os provedores de imagem falharam")
    return None
