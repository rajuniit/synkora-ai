"""
AI image generation tool.

Works with any provider the agent is configured to use:
  - OpenAI / LiteLLM proxy / Azure / OpenRouter → gpt-image-2
  - Google / Gemini (direct)                    → Imagen 3
  - xAI / Grok                                  → grok-2-image
  - Anthropic                                   → not supported (clear error)
  - Unknown                                     → gpt-image-2 attempt

The agent's existing api_key and api_base are reused — no extra setup.
"""

from __future__ import annotations

import base64
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

_SIZE_MAP: dict[str, tuple[str, str]] = {
    # alias → (openai_size, google_aspect_ratio)
    "square": ("1024x1024", "1:1"),
    "portrait": ("1024x1536", "9:16"),
    "landscape": ("1536x1024", "16:9"),
}

_QUALITY_MAP: dict[str, str] = {
    "standard": "medium",
    "hd": "high",
    "low": "low",
    "medium": "medium",
    "high": "high",
}

_GPT_IMAGE_2 = "gpt-image-2"
_IMAGEN_3 = "imagen-3.0-generate-002"
_GROK_IMAGE = "grok-2-image"

# Providers that use the OpenAI /images/generations endpoint
_OPENAI_COMPAT = {"openai", "litellm", "azure", "openrouter", "lm_studio", "vllm"}
_GOOGLE_PROVIDERS = {"google", "gemini", "google-genai", "google_genai"}
_GROK_PROVIDERS = {"xai", "grok", "x-ai", "x_ai"}

# Models that speak the OpenAI images API (not chat models)
_OPENAI_IMAGE_MODELS = {"gpt-image-2", "dall-e-3", "dall-e-2"}
# Models that are Google Imagen (use Google GenAI SDK)
_GOOGLE_IMAGE_MODELS = {"imagen-3.0-generate-002", "imagen-3.0-fast-generate-001"}


async def internal_generate_image(
    prompt: str,
    size: str = "square",
    quality: str = "standard",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate an AI image from a text prompt.

    Works automatically with whatever provider the agent is configured to use.

    Args:
        prompt:  Detailed description of the image to generate.
        size:    "square" | "portrait" | "landscape".  Defaults to "square".
        quality: "standard" | "hd" | "low" | "medium" | "high".
        config:  Injected runtime config (contains _runtime_context).
    """
    config = config or {}
    runtime_context = config.get("_runtime_context")

    provider = "openai"
    api_key: str | None = None
    api_base: str | None = None
    configured_model: str | None = None

    if runtime_context and runtime_context.llm_client:
        llm = runtime_context.llm_client
        provider = getattr(llm, "provider", "openai").lower()
        llm_cfg = getattr(llm, "config", None)
        if llm_cfg:
            api_key = getattr(llm_cfg, "api_key", None)
            api_base = getattr(llm_cfg, "api_base", None)
            configured_model = getattr(llm_cfg, "model_name", None)

    if not api_key:
        return {
            "success": False,
            "error": "No API key found in the agent's LLM configuration.",
        }

    # Anthropic has no image generation API
    if provider == "anthropic":
        return {
            "success": False,
            "error": (
                "Anthropic does not support image generation. "
                "To use this tool, configure the agent with an OpenAI, Google, or xAI model."
            ),
        }

    size_key = size.lower().strip() if size.lower().strip() in _SIZE_MAP else "square"
    openai_size, google_ratio = _SIZE_MAP[size_key]
    gpt_quality = _QUALITY_MAP.get(quality.lower().strip(), "medium")

    tenant_id = str(runtime_context.tenant_id) if runtime_context else "default"
    date_path = datetime.now(UTC).strftime("%Y-%m-%d")
    file_id = uuid.uuid4().hex[:12]

    # If the agent's LLM config is explicitly set to a Google Imagen model, use Google SDK
    if configured_model in _GOOGLE_IMAGE_MODELS:
        return await _generate_google(
            prompt=prompt,
            api_key=api_key,
            aspect_ratio=google_ratio,
            model=configured_model,
            tenant_id=tenant_id,
            date_path=date_path,
            file_id=file_id,
        )

    # If the agent's LLM config is explicitly set to an OpenAI image model, use it directly
    if configured_model in _OPENAI_IMAGE_MODELS:
        return await _generate_openai_compat(
            prompt=prompt,
            api_key=api_key,
            api_base=api_base,
            model=configured_model,
            size=openai_size,
            quality=gpt_quality,
            tenant_id=tenant_id,
            date_path=date_path,
            file_id=file_id,
            provider_label=provider,
        )

    # Google direct (uses google-genai SDK, not OpenAI-compat)
    if provider in _GOOGLE_PROVIDERS:
        return await _generate_google(
            prompt=prompt,
            api_key=api_key,
            aspect_ratio=google_ratio,
            tenant_id=tenant_id,
            date_path=date_path,
            file_id=file_id,
        )

    # xAI / Grok — OpenAI-compat but different default base URL
    if provider in _GROK_PROVIDERS:
        return await _generate_openai_compat(
            prompt=prompt,
            api_key=api_key,
            api_base=api_base or "https://api.x.ai/v1",
            model=_GROK_IMAGE,
            size=openai_size,
            quality=None,
            tenant_id=tenant_id,
            date_path=date_path,
            file_id=file_id,
            provider_label="xai",
        )

    # OpenAI / LiteLLM proxy / Azure / OpenRouter / unknown → gpt-image-2
    # AsyncOpenAI with api_base routes through the proxy's /images/generations endpoint
    return await _generate_openai_compat(
        prompt=prompt,
        api_key=api_key,
        api_base=api_base,
        model=_GPT_IMAGE_2,
        size=openai_size,
        quality=gpt_quality,
        tenant_id=tenant_id,
        date_path=date_path,
        file_id=file_id,
        provider_label=provider,
    )


async def _generate_openai_compat(
    prompt: str,
    api_key: str,
    api_base: str | None,
    model: str,
    size: str,
    quality: str | None,
    tenant_id: str,
    date_path: str,
    file_id: str,
    provider_label: str = "openai",
) -> dict[str, Any]:
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=api_key,
            **({"base_url": api_base} if api_base else {}),
        )
        kwargs: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": 1,
            "response_format": "b64_json",
        }
        if quality is not None:
            kwargs["quality"] = quality

        response = await client.images.generate(**kwargs)  # type: ignore[arg-type]
        img = response.data[0]
        image_bytes = base64.b64decode(img.b64_json or "")
        revised_prompt: str = getattr(img, "revised_prompt", None) or prompt
    except Exception as exc:
        logger.error(f"Image generation failed ({provider_label}/{model}): {exc}")
        return {"success": False, "error": f"Image generation failed: {exc}"}

    url = _upload_to_s3(image_bytes, tenant_id, date_path, file_id, "png")
    return {
        "success": True,
        "url": url,
        "prompt": prompt,
        "revised_prompt": revised_prompt,
        "model": model,
        "provider": provider_label,
        "size": size,
    }


async def _generate_google(
    prompt: str,
    api_key: str,
    aspect_ratio: str,
    tenant_id: str,
    date_path: str,
    file_id: str,
    model: str = _IMAGEN_3,
) -> dict[str, Any]:
    try:
        import asyncio

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_images(
                model=model,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=aspect_ratio,
                    safety_filter_level="block_only_high",
                ),
            ),
        )
        if not response.generated_images:
            return {"success": False, "error": "Google Imagen returned no images (prompt may have been filtered)"}
        image_bytes = response.generated_images[0].image.image_bytes
    except Exception as exc:
        logger.error(f"Google Imagen generation failed: {exc}")
        return {"success": False, "error": f"Google Imagen generation failed: {exc}"}

    url = _upload_to_s3(image_bytes, tenant_id, date_path, file_id, "png")
    return {
        "success": True,
        "url": url,
        "prompt": prompt,
        "revised_prompt": prompt,
        "model": model,
        "provider": "google",
        "size": aspect_ratio,
    }


def _upload_to_s3(image_bytes: bytes, tenant_id: str, date_path: str, file_id: str, ext: str) -> str | None:
    s3_key = f"generated-images/{tenant_id}/{date_path}/{file_id}.{ext}"
    try:
        from src.services.storage.s3_storage import get_s3_storage

        s3 = get_s3_storage()
        s3.upload_file(file_content=image_bytes, key=s3_key, content_type=f"image/{ext}")
        return s3.generate_presigned_url(key=s3_key, expiration=86400 * 7)
    except Exception:
        logger.debug("S3 upload skipped (not configured); returning None URL")
        return None
