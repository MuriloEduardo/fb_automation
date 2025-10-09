import os
import logging
from typing import Optional
from uuid import uuid4
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
except Exception:
    genai = None  # type: ignore
    types = None  # type: ignore


def generate_image_file(
    image_prompt: str,
    *,
    size: str = "1024x1024",
    image_format: str = "png",
    subdir: str = "generated_images",
    model_name: str = "imagen-3.0-generate-001",
) -> Optional[str]:
    if not image_prompt:
        return None

    if genai is None or types is None:
        logger.info("Biblioteca google-genai não disponível; ignorando Gemini.")
        return None

    project = getattr(settings, "GOOGLE_CLOUD_PROJECT", "") or os.environ.get(
        "GOOGLE_CLOUD_PROJECT", ""
    )
    location = getattr(settings, "GOOGLE_CLOUD_LOCATION", "") or os.environ.get(
        "GOOGLE_CLOUD_LOCATION", "us-central1"
    )

    if not project:
        logger.info("GOOGLE_CLOUD_PROJECT não configurado; ignorando Gemini.")
        return None

    try:
        client = genai.Client(
            vertexai=True, project=project, location=location
        )

        aspect_ratio = "1:1" if size == "1024x1024" else "16:9"

        response = client.models.generate_images(
            model=model_name,
            prompt=image_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                output_mime_type=f"image/{image_format}",
            ),
        )

        if not response.generated_images:
            logger.error("Resposta de imagem do Gemini vazia")
            return None

        img = response.generated_images[0]
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

        if hasattr(img, "image") and hasattr(img.image, "_pil_image"):
            img.image._pil_image.save(out_path)
        elif hasattr(img, "image_bytes"):
            with open(out_path, "wb") as f:
                f.write(img.image_bytes)
        else:
            logger.error("Formato de imagem do Gemini não reconhecido")
            return None

        logger.info("Imagem (Gemini) salva em: %s", out_path)
        return out_path

    except Exception as e:
        logger.error("Erro ao gerar imagem com Gemini: %s", str(e))
        return None
