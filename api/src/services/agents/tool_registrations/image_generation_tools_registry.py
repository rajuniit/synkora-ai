"""Register AI image generation tools."""

from __future__ import annotations


def register_image_generation_tools(registry) -> None:
    """Register image generation tools with the ADK tool registry."""
    from src.services.agents.internal_tools.image_generation_tools import internal_generate_image

    registry.register_tool(
        name="internal_generate_image",
        description=(
            "Generate an AI image from a text prompt using the agent's configured LLM provider.\n\n"
            "Automatically selects the best available image model:\n"
            "  • OpenAI / LiteLLM proxy → gpt-image-2\n"
            "  • Google / Gemini        → Imagen 3\n"
            "  • xAI / Grok             → grok-2-image (Aurora)\n\n"
            "No extra API key needed — reuses the agent's existing AI Model configuration.\n\n"
            "IMPORTANT: After calling this tool the image is rendered inline in the chat — "
            "do NOT embed any URL or markdown image syntax in your response. "
            "Simply describe what you generated.\n\n"
            "Tips for good prompts:\n"
            "- Be specific: describe style, lighting, colours, composition\n"
            "- Include art direction: 'photorealistic', 'oil painting', 'flat illustration', etc.\n"
            "- Mention what should NOT appear using 'without ...' phrasing\n\n"
            "Size options:\n"
            "  square (default) — 1024x1024, best for profile pics, icons, social posts\n"
            "  portrait         — 1024x1536, best for phone wallpapers, posters\n"
            "  landscape        — 1536x1024, best for banners, cinematic shots\n\n"
            "Quality options:\n"
            "  standard (default) — balanced speed and detail\n"
            "  hd / high          — maximum detail, slower\n"
            "  low                — fastest, lowest cost"
        ),
        parameters={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "Detailed description of the image to generate. "
                        "Be specific about style, subject, colours, and composition."
                    ),
                },
                "size": {
                    "type": "string",
                    "enum": ["square", "portrait", "landscape"],
                    "default": "square",
                    "description": "Image dimensions. square=1024x1024, portrait=1024x1536, landscape=1536x1024.",
                },
                "quality": {
                    "type": "string",
                    "enum": ["standard", "hd", "low", "medium", "high"],
                    "default": "standard",
                    "description": "Image quality level. 'hd'/'high' gives more detail; 'low' is fastest.",
                },
            },
            "required": ["prompt"],
        },
        function=internal_generate_image,
        tool_category="image_generation",
    )
