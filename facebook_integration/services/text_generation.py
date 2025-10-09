import logging
from typing import Dict, Any, Optional

from django.conf import settings

from .openai_service import OpenAIService, OpenAIServiceException
from ..models import AIConfiguration

logger = logging.getLogger(__name__)


def _get_default_ai_config() -> AIConfiguration:
    config = AIConfiguration.objects.filter(is_default=True).first()
    if not config:
        config = AIConfiguration.objects.create(
            name="Configuração Padrão",
            is_default=True,
        )
    return config


def _generate_with_openai(
    prompt: str, context: Optional[Dict[str, Any]], ai_config: AIConfiguration
) -> str:
    service = OpenAIService()
    return service.generate_post_content(prompt, context, ai_config)


def _generate_with_gemini(
    prompt: str, context: Optional[Dict[str, Any]], ai_config: AIConfiguration
) -> str:
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore
    except Exception:
        raise RuntimeError("google-genai não está instalado/configurado")

    # Tenta usar API Key primeiro (mais simples e direto)
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    
    if api_key:
        # Usa Gemini API diretamente com API Key
        client = genai.Client(api_key=api_key)
    else:
        # Fallback para Vertex AI
        project = getattr(
            settings, "GOOGLE_CLOUD_PROJECT", ""
        ) or settings.__dict__.get("GOOGLE_CLOUD_PROJECT", "")
        location = getattr(settings, "GOOGLE_CLOUD_LOCATION", "us-central1")

        if not project:
            raise RuntimeError(
                "GEMINI_API_KEY ou GOOGLE_CLOUD_PROJECT não configurado"
            )

        client = genai.Client(vertexai=True, project=project, location=location)

    system = (
        "Você é especialista em marketing digital e criação de conteúdo para "
        "redes sociais. Crie posts envolventes, diretos e adequados para "
        "Facebook."
    )
    user = prompt

    model_name = getattr(ai_config, "model", "gemini-1.5-flash")
    
    # API Key requer prefixo "models/", Vertex AI não
    if api_key and not model_name.startswith("models/"):
        model_name = f"models/{model_name}"

    # The new google-genai text generation uses generate_content
    # We'll pass system+user as a single prompt string for simplicity
    full_prompt = f"System: {system}\n\nUser: {user}"

    # Temperature handling similar to OpenAI
    temperature = float(getattr(ai_config, "temperature", 0.7) or 0.7)

    try:
        result = client.models.generate_content(
            model=model_name,
            contents=full_prompt,
            config=types.GenerateContentConfig(temperature=temperature),
        )

        # The result output can be in text parts
        text = getattr(result, "text", None)
        if text:
            return text.strip()

        # Fallback: try to concatenate parts
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

        raise RuntimeError("Resposta vazia do Gemini")
    except Exception as e:
        raise RuntimeError(f"Gemini falhou: {str(e)}")


def generate_text_with_fallback(
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
    ai_config: Optional[AIConfiguration] = None,
) -> str:
    """
    Orquestra geração de texto com fallback entre configs.
    Tenta configs na ordem: default primeiro, depois outras por ID.
    Para cada config, identifica provedor pelo nome do modelo.
    """
    last_error = None

    # Monta lista ordenada: config passada, default, depois resto
    configs_to_try = []

    if ai_config:
        configs_to_try.append(ai_config)
        logger.info(
            "Iniciando com config passada: id=%s, model=%s",
            getattr(ai_config, "id", "-"),
            ai_config.model,
        )

    # Busca todas configs ordenadas: default first, depois por created_at
    all_configs = list(
        AIConfiguration.objects.all().order_by("-is_default", "created_at")
    )

    for cfg in all_configs:
        if cfg not in configs_to_try:
            configs_to_try.append(cfg)

    if not configs_to_try:
        logger.warning("Nenhuma config AI encontrada, criando default")
        configs_to_try = [_get_default_ai_config()]

    logger.info("Total de %d configs para tentar na ordem", len(configs_to_try))

    # Tenta cada config na ordem
    for idx, cfg in enumerate(configs_to_try, 1):
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
            "Tentativa %d/%d: config id=%s, provider=%s, model=%s",
            idx,
            len(configs_to_try),
            getattr(cfg, "id", "-"),
            provider,
            cfg.model,
        )

        try:
            if provider == "openai":
                result = _generate_with_openai(prompt, context, cfg)
                logger.info(
                    "✓ Sucesso com OpenAI config id=%s", getattr(cfg, "id", "-")
                )
                return result
            elif provider == "gemini":
                result = _generate_with_gemini(prompt, context, cfg)
                logger.info(
                    "✓ Sucesso com Gemini config id=%s", getattr(cfg, "id", "-")
                )
                return result
            else:
                logger.warning(
                    "Modelo desconhecido '%s' na config %s, pulando",
                    cfg.model,
                    getattr(cfg, "id", "-"),
                )
                continue

        except OpenAIServiceException as e:
            msg = str(e)
            if "429" in msg or "insufficient_quota" in msg.lower():
                logger.warning(
                    "✗ Config %s (OpenAI) - Erro 429/quota. " "Tentando próxima...",
                    getattr(cfg, "id", "-"),
                )
            else:
                logger.warning(
                    "✗ Config %s (OpenAI) - Erro: %s. Tentando próxima...",
                    getattr(cfg, "id", "-"),
                    str(e)[:100],
                )
            last_error = e
            continue

        except RuntimeError as e:
            logger.warning(
                "✗ Config %s (%s) - Erro: %s. Tentando próxima...",
                getattr(cfg, "id", "-"),
                provider,
                str(e)[:100],
            )
            last_error = e
            continue

        except Exception as e:
            logger.warning(
                "✗ Config %s (%s) - Erro inesperado: %s. " "Tentando próxima...",
                getattr(cfg, "id", "-"),
                provider,
                str(e)[:100],
            )
            last_error = e
            continue

    # Se chegou aqui, todas falharam
    logger.error(
        "Todas as %d configs falharam. Último erro: %s",
        len(configs_to_try),
        str(last_error)[:200],
    )

    if last_error:
        raise RuntimeError(
            f"Todas as {len(configs_to_try)} configs falharam. "
            f"Último erro: {str(last_error)}"
        )
    raise RuntimeError("Nenhuma configuração de IA válida para gerar texto")
