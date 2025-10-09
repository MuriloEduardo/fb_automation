import logging
from typing import Optional
from django.conf import settings
from .openai_service import OpenAIService, OpenAIServiceException
from ..models import AIConfiguration

logger = logging.getLogger(__name__)


def _generate_with_openai(
    post_content: str, ai_config: AIConfiguration
) -> Optional[str]:
    try:
        service = OpenAIService()
        return service.generate_image_prompt(post_content, ai_config)
    except Exception as e:
        logger.warning("OpenAI falhou na geração de prompt de imagem: %s", str(e)[:100])
        return None


def _generate_with_gemini(
    post_content: str, ai_config: AIConfiguration
) -> Optional[str]:
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore
    except Exception:
        logger.warning("google-genai não instalado/configurado para prompt de imagem")
        return None

    # Tenta usar API Key primeiro
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    
    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        # Fallback para Vertex AI
        project = getattr(settings, "GOOGLE_CLOUD_PROJECT", "")
        location = getattr(settings, "GOOGLE_CLOUD_LOCATION", "us-central1")

        if not project:
            logger.warning(
                "GEMINI_API_KEY ou GOOGLE_CLOUD_PROJECT não configurado"
            )
            return None

        client = genai.Client(vertexai=True, project=project, location=location)
    
    model_name = getattr(ai_config, "model", "gemini-1.5-flash")
    
    # API Key requer prefixo "models/", Vertex AI não
    if api_key and not model_name.startswith("models/"):
        model_name = f"models/{model_name}"

    prompt = (
        "Você é especialista em criação de prompts para geração de imagens. "
        "Baseado no conteúdo abaixo, gere um prompt em inglês conciso "
        "(max 100 palavras) para gerar uma imagem. "
        "Inclua: estilo visual, cores, elementos, atmosfera. "
        "Retorne apenas o prompt.\n\n"
        f"Conteúdo: {post_content}"
    )

    try:
        result = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.8),
        )
        text = getattr(result, "text", None)
        if text:
            return text.strip()
        if hasattr(result, "candidates") and result.candidates:
            parts_text = []
            for c in result.candidates:
                parts = getattr(getattr(c, "content", None), "parts", None)
                if parts:
                    for p in parts:
                        if getattr(p, "text", None):
                            parts_text.append(p.text)
            if parts_text:
                return "\n".join(parts_text).strip()
        logger.warning("Gemini retornou resposta vazia (prompt de imagem)")
        return None
    except Exception as e:
        logger.warning("Gemini falhou na geração de prompt de imagem: %s", str(e)[:100])
        return None


def generate_image_prompt_with_fallback(post_content: str) -> Optional[str]:
    """
    Gera prompt de imagem tentando configs na ordem.
    Ordem: default first, depois outras por created_at.
    """
    if not post_content:
        logger.warning("Conteúdo vazio para gerar prompt de imagem")
        return None

    # Busca configs ordenadas
    all_configs = list(
        AIConfiguration.objects.all().order_by("-is_default", "created_at")
    )

    if not all_configs:
        logger.warning("Nenhuma config AI para gerar prompt de imagem")
        return None

    logger.info("Tentando gerar prompt de imagem com %d configs", len(all_configs))

    for idx, cfg in enumerate(all_configs, 1):
        # Usa campo provider se existir, senão identifica pelo modelo
        provider = getattr(cfg, "provider", None)
        if not provider:
            model_lower = str(cfg.model).lower()
            if model_lower.startswith("gpt") or model_lower.startswith("o"):
                provider = "openai"
            elif model_lower.startswith("gemini"):
                provider = "gemini"
            else:
                provider = "desconhecido"

        logger.info(
            "Tentativa %d/%d (prompt img): config id=%s, provider=%s, " "model=%s",
            idx,
            len(all_configs),
            getattr(cfg, "id", "-"),
            provider,
            cfg.model,
        )

        result = None
        if provider == "openai":
            result = _generate_with_openai(post_content, cfg)
        elif provider == "gemini":
            result = _generate_with_gemini(post_content, cfg)
        else:
            logger.warning(
                "Modelo desconhecido '%s' config %s, pulando",
                cfg.model,
                getattr(cfg, "id", "-"),
            )
            continue

        if result:
            logger.info(
                "✓ Prompt de imagem gerado com %s config id=%s",
                provider,
                getattr(cfg, "id", "-"),
            )
            return result

        logger.warning(
            "✗ Config %s (%s) não gerou prompt. Tentando próxima...",
            getattr(cfg, "id", "-"),
            provider,
        )

    logger.error(
        "Todas as %d configs falharam ao gerar prompt de imagem", len(all_configs)
    )
    return None
