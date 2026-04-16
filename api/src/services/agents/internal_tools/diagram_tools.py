"""
Diagram generation tools for Synkora agents.

Generates publication-quality technical diagrams from structured JSON specs.
Uses the deterministic SVG rendering engine (no LLM writes raw SVG).
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


async def internal_generate_diagram(
    diagram_spec: str,
    title: str = "Diagram",
    style: int = 4,
    output_format: str = "svg",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a publication-quality technical diagram from a structured JSON specification.

    The spec follows the fireworks-tech-graph format with nodes, arrows, containers.
    Nodes use semantic shapes: hexagon=agent, cylinder=DB, double_rect=LLM, gear=tool.
    Arrows use flow types: control, data, read, write, feedback, async.
    """
    try:
        # 1. Parse & validate JSON spec
        if len(diagram_spec) > 100 * 1024:
            return {"success": False, "error": "Spec too large (max 100KB)"}

        try:
            spec = json.loads(diagram_spec)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {e}"}

        if not isinstance(spec, dict):
            return {"success": False, "error": "Spec must be a JSON object"}

        # 2. Apply style and title overrides
        spec.setdefault("title", title)
        if style and style != spec.get("style"):
            spec["style"] = style

        # 3. Get style profile
        from src.services.diagrams.styles import get_style

        style_id = spec.get("style", style)
        style_profile = get_style(style_id)

        # 4. Run auto-layout for nodes missing positions
        from src.services.diagrams.layout import auto_layout

        spec = auto_layout(spec)

        # 5. Render SVG
        from src.services.diagrams.svg_renderer import DiagramRenderer

        renderer = DiagramRenderer(style=style_profile)
        svg_content = renderer.render(spec)

        # 6. Try uploading to S3
        svg_url = None
        png_url = None
        try:
            from src.services.agents.internal_tools.storage_tools import internal_s3_upload_file

            tenant_id = (config or {}).get("tenant_id", "default")
            date_prefix = datetime.now(UTC).strftime("%Y-%m-%d")
            file_id = uuid.uuid4().hex[:12]
            s3_key = f"diagrams/{tenant_id}/{date_prefix}/{file_id}.svg"

            upload_result = await internal_s3_upload_file(
                file_content=svg_content,
                file_path=s3_key,
                content_type="image/svg+xml",
                config=config,
            )
            if isinstance(upload_result, dict) and upload_result.get("success"):
                svg_url = upload_result.get("url") or upload_result.get("presigned_url")
        except Exception:
            logger.debug("S3 upload skipped (not configured or failed)")

        # 7. PNG conversion (optional, if cairosvg available)
        if output_format in ("png", "both"):
            try:
                import cairosvg

                png_bytes = cairosvg.svg2png(bytestring=svg_content.encode(), output_width=1920)
                if png_bytes and config:
                    png_key = s3_key.replace(".svg", ".png")
                    png_upload = await internal_s3_upload_file(
                        file_content=png_bytes,
                        file_path=png_key,
                        content_type="image/png",
                        config=config,
                    )
                    if isinstance(png_upload, dict) and png_upload.get("success"):
                        png_url = png_upload.get("url") or png_upload.get("presigned_url")
            except ImportError:
                logger.debug("cairosvg not installed, skipping PNG export")
            except Exception as e:
                logger.warning(f"PNG conversion failed: {e}")

        # 8. Return result
        diagram_type = spec.get("template_type", spec.get("diagram_type", "architecture"))
        return {
            "success": True,
            "diagram": {
                "title": spec.get("title", title),
                "diagram_type": diagram_type,
                "style": style_id,
                "svg_url": svg_url,
                "svg_content": svg_content if len(svg_content) < 50000 else None,
                "png_url": png_url,
            },
        }

    except ValueError as e:
        return {"success": False, "error": f"Validation error: {e}"}
    except Exception as e:
        logger.exception("Diagram generation failed")
        return {"success": False, "error": f"Generation failed: {e}"}


async def internal_generate_quick_diagram(
    nodes: str,
    edges: str,
    title: str = "Diagram",
    diagram_type: str = "architecture",
    style: int = 4,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Simplified diagram generation - just provide nodes and edges, auto-layout handles the rest.

    Nodes: JSON array of [{id, label, kind, icon?, group?}]
    Edges: JSON array of [{from, to, label?, flow?}]
    """
    try:
        try:
            nodes_list = json.loads(nodes)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid nodes JSON: {e}"}

        try:
            edges_list = json.loads(edges)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid edges JSON: {e}"}

        if not isinstance(nodes_list, list):
            return {"success": False, "error": "Nodes must be a JSON array"}
        if not isinstance(edges_list, list):
            return {"success": False, "error": "Edges must be a JSON array"}

        # Build full spec from simplified input
        spec_nodes = []
        for node in nodes_list:
            if isinstance(node, dict):
                spec_nodes.append(
                    {
                        "id": node.get("id", f"node_{len(spec_nodes)}"),
                        "label": node.get("label", node.get("id", "")),
                        "kind": node.get("kind", "rounded_rect"),
                        "icon": node.get("icon", ""),
                        "group": node.get("group"),
                    }
                )

        spec_arrows = []
        for edge in edges_list:
            if isinstance(edge, dict):
                spec_arrows.append(
                    {
                        "source": edge.get("from") or edge.get("source", ""),
                        "target": edge.get("to") or edge.get("target", ""),
                        "label": edge.get("label", ""),
                        "flow": edge.get("flow", "data"),
                    }
                )

        spec = {
            "template_type": diagram_type,
            "title": title,
            "style": style,
            "nodes": spec_nodes,
            "arrows": spec_arrows,
        }

        return await internal_generate_diagram(
            diagram_spec=json.dumps(spec),
            title=title,
            style=style,
            config=config,
        )

    except Exception as e:
        logger.exception("Quick diagram generation failed")
        return {"success": False, "error": f"Generation failed: {e}"}
