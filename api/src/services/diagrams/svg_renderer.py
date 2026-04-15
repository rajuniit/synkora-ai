"""
Deterministic SVG Rendering Engine for technical diagrams.

Pure Python, zero external dependencies. Takes a structured JSON spec
and renders pixel-perfect SVG output.

Rendering pipeline:
1. Parse JSON spec + validate structure
2. Apply style theme
3. Auto-layout if positions omitted
4. Render SVG layers in z-order
"""

import math
from dataclasses import dataclass
from typing import Any
from xml.sax.saxutils import escape


@dataclass
class Point:
    x: float
    y: float


@dataclass
class Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def cx(self) -> float:
        return self.x + self.width / 2

    @property
    def cy(self) -> float:
        return self.y + self.height / 2

    def port(self, side: str, offset: float = 0) -> Point:
        """Get connection point on a given side."""
        if side == "top":
            return Point(self.cx + offset, self.y)
        elif side == "bottom":
            return Point(self.cx + offset, self.y + self.height)
        elif side == "left":
            return Point(self.x, self.cy + offset)
        elif side == "right":
            return Point(self.x + self.width, self.cy + offset)
        return Point(self.cx, self.cy)


# Maximum spec size to prevent abuse
MAX_SPEC_SIZE = 100 * 1024  # 100KB
MAX_NODES = 200
MAX_ARROWS = 500
MAX_CONTAINERS = 50


def validate_spec(spec: dict[str, Any]) -> list[str]:
    """Validate diagram spec structure. Returns list of errors."""
    errors = []

    if not isinstance(spec, dict):
        return ["Spec must be a dictionary"]

    tt = spec.get("template_type", "architecture")

    # Dedicated diagram types use their own fields — skip architecture node/arrow checks
    if tt == "sequence":
        participants = spec.get("participants", [])
        if not isinstance(participants, list):
            errors.append("'participants' must be a list")
        elif len(participants) > 20:
            errors.append(f"Too many participants: {len(participants)} (max 20)")
        messages = spec.get("messages", [])
        if not isinstance(messages, list):
            errors.append("'messages' must be a list")
        elif len(messages) > 100:
            errors.append(f"Too many messages: {len(messages)} (max 100)")
        return errors

    if tt == "comparison":
        if not isinstance(spec.get("columns", []), list):
            errors.append("'columns' must be a list")
        if not isinstance(spec.get("rows", []), list):
            errors.append("'rows' must be a list")
        return errors

    if tt == "timeline":
        if not isinstance(spec.get("tracks", []), list):
            errors.append("'tracks' must be a list")
        return errors

    if tt in ("mind-map", "mind_map"):
        if not isinstance(spec.get("branches", []), list):
            errors.append("'branches' must be a list")
        return errors

    if tt in ("er-diagram", "er_diagram"):
        if not isinstance(spec.get("entities", []), list):
            errors.append("'entities' must be a list")
        return errors

    if tt in ("class-diagram", "class_diagram", "class"):
        if not isinstance(spec.get("classes", []), list):
            errors.append("'classes' must be a list")
        return errors

    if tt in ("use-case", "use_case"):
        if not isinstance(spec.get("use_cases", []), list):
            errors.append("'use_cases' must be a list")
        return errors

    # state-machine and flowchart reuse architecture renderer — fall through to node checks

    # Check nodes
    nodes = spec.get("nodes", [])
    if not isinstance(nodes, list):
        errors.append("'nodes' must be a list")
    elif len(nodes) > MAX_NODES:
        errors.append(f"Too many nodes: {len(nodes)} (max {MAX_NODES})")

    # Check arrows
    arrows = spec.get("arrows", [])
    if not isinstance(arrows, list):
        errors.append("'arrows' must be a list")
    elif len(arrows) > MAX_ARROWS:
        errors.append(f"Too many arrows: {len(arrows)} (max {MAX_ARROWS})")

    # Check containers
    containers = spec.get("containers", [])
    if not isinstance(containers, list):
        errors.append("'containers' must be a list")
    elif len(containers) > MAX_CONTAINERS:
        errors.append(f"Too many containers: {len(containers)} (max {MAX_CONTAINERS})")

    # Validate node structure
    node_ids = set()
    for i, node in enumerate(nodes if isinstance(nodes, list) else []):
        if not isinstance(node, dict):
            errors.append(f"Node {i} must be a dictionary")
            continue
        nid = node.get("id")
        if not nid:
            errors.append(f"Node {i} missing 'id'")
        elif nid in node_ids:
            errors.append(f"Duplicate node id: {nid}")
        else:
            node_ids.add(nid)

    # Validate arrow references
    for i, arrow in enumerate(arrows if isinstance(arrows, list) else []):
        if not isinstance(arrow, dict):
            errors.append(f"Arrow {i} must be a dictionary")
            continue
        src = arrow.get("source") or arrow.get("from")
        tgt = arrow.get("target") or arrow.get("to")
        if src and src not in node_ids:
            errors.append(f"Arrow {i} references unknown source: {src}")
        if tgt and tgt not in node_ids:
            errors.append(f"Arrow {i} references unknown target: {tgt}")

    return errors


# --- SVG rendering helpers ---


def _svg_rect(
    x: float,
    y: float,
    w: float,
    h: float,
    rx: float = 0,
    fill: str = "white",
    stroke: str = "#e5e7eb",
    stroke_width: float = 1.5,
    opacity: float = 1.0,
    filter_id: str = "",
    css_class: str = "",
) -> str:
    parts = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}"']
    if rx > 0:
        parts.append(f' rx="{rx}"')
    parts.append(f' fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"')
    if opacity < 1.0:
        parts.append(f' opacity="{opacity}"')
    if filter_id:
        parts.append(f' filter="url(#{filter_id})"')
    if css_class:
        parts.append(f' class="{css_class}"')
    parts.append("/>")
    return "".join(parts)


def _svg_text(
    x: float,
    y: float,
    text: str,
    font_size: float = 14,
    fill: str = "#1f2937",
    font_family: str = "system-ui, -apple-system, sans-serif",
    font_weight: str = "normal",
    anchor: str = "middle",
    dominant_baseline: str = "central",
) -> str:
    return (
        f'<text x="{x}" y="{y}" font-size="{font_size}" fill="{fill}" '
        f'font-family="{font_family}" font-weight="{font_weight}" '
        f'text-anchor="{anchor}" dominant-baseline="{dominant_baseline}">'
        f"{escape(str(text))}</text>"
    )


def _svg_line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    stroke: str = "#9ca3af",
    stroke_width: float = 1.5,
    marker_end: str = "",
    dash: str = "",
) -> str:
    parts = [f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{stroke_width}"']
    if marker_end:
        parts.append(f' marker-end="url(#{marker_end})"')
    if dash:
        parts.append(f' stroke-dasharray="{dash}"')
    parts.append("/>")
    return "".join(parts)


def _svg_path(
    d: str,
    stroke: str = "#9ca3af",
    stroke_width: float = 1.5,
    fill: str = "none",
    marker_end: str = "",
    dash: str = "",
) -> str:
    parts = [f'<path d="{d}" stroke="{stroke}" stroke-width="{stroke_width}" fill="{fill}"']
    if marker_end:
        parts.append(f' marker-end="url(#{marker_end})"')
    if dash:
        parts.append(f' stroke-dasharray="{dash}"')
    parts.append("/>")
    return "".join(parts)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert #RRGGBB hex to (r, g, b) integers. Falls back to (128,128,128) on parse error."""
    try:
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = h[0] * 2 + h[1] * 2 + h[2] * 2
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except Exception:
        return 128, 128, 128


class DiagramRenderer:
    """Main SVG rendering engine."""

    def __init__(self, style: dict[str, Any] | None = None):
        self.style = style or {}
        self._node_rects: dict[str, Rect] = {}

    # Per-kind color palette: (gradient_start, gradient_end, stroke, text, icon_bg)
    _KIND_PALETTE: dict[str, tuple[str, str, str, str, str]] = {
        "rounded_rect": ("#EFF6FF", "#DBEAFE", "#93C5FD", "#1D4ED8", "#DBEAFE"),
        "hexagon": ("#F5F3FF", "#EDE9FE", "#C4B5FD", "#5B21B6", "#EDE9FE"),
        "cylinder": ("#ECFDF5", "#D1FAE5", "#6EE7B7", "#065F46", "#D1FAE5"),
        "diamond": ("#FFFBEB", "#FEF3C7", "#FCD34D", "#92400E", "#FEF3C7"),
        "double_rect": ("#EEF2FF", "#E0E7FF", "#A5B4FC", "#3730A3", "#E0E7FF"),
        "circle": ("#ECFEFF", "#CFFAFE", "#67E8F9", "#0E7490", "#CFFAFE"),
        "gear": ("#F8FAFC", "#F1F5F9", "#CBD5E1", "#334155", "#F1F5F9"),
        "document": ("#FFFBEB", "#FEF3C7", "#FDE68A", "#92400E", "#FEF3C7"),
        "folder": ("#FFF7ED", "#FFEDD5", "#FED7AA", "#9A3412", "#FFEDD5"),
        "terminal": ("#0F172A", "#1E293B", "#334155", "#E2E8F0", "#1E293B"),
        "speech": ("#F0FDF4", "#DCFCE7", "#86EFAC", "#14532D", "#DCFCE7"),
        "rect": ("#F9FAFB", "#F3F4F6", "#D1D5DB", "#374151", "#F3F4F6"),
        "parallelogram": ("#FFF1F2", "#FFE4E6", "#FCA5A5", "#991B1B", "#FFE4E6"),
    }

    def _kind_palette(self, kind: str) -> tuple[str, str, str, str, str]:
        return self._KIND_PALETTE.get(kind, self._KIND_PALETTE["rounded_rect"])

    def render(self, spec: dict[str, Any]) -> str:
        """Render a diagram spec to SVG string."""
        errors = validate_spec(spec)
        if errors:
            raise ValueError(f"Invalid diagram spec: {'; '.join(errors)}")

        # Dispatch to dedicated renderers based on template_type
        tt = spec.get("template_type", "architecture")
        if tt == "sequence":
            return self.render_sequence(spec)
        if tt == "comparison":
            return self.render_comparison(spec)
        if tt == "timeline":
            return self.render_timeline(spec)
        if tt in ("mind-map", "mind_map"):
            return self.render_mind_map(spec)
        if tt in ("er-diagram", "er_diagram"):
            return self.render_er_diagram(spec)
        if tt in ("class-diagram", "class_diagram", "class"):
            return self.render_class_diagram(spec)
        if tt in ("use-case", "use_case"):
            return self.render_use_case(spec)
        # state-machine, flowchart, data-flow, agent, memory, network-topology all
        # use the architecture renderer (nodes + arrows + containers)

        width = spec.get("width", 1400)
        height = spec.get("height", 900)
        title = spec.get("title", "")
        subtitle = spec.get("subtitle", "")
        nodes = spec.get("nodes", [])
        arrows = spec.get("arrows", [])
        containers = spec.get("containers", [])
        legend = spec.get("legend", [])
        legend_position = spec.get("legend_position", "bottom-right")

        # Build node lookup and rects
        self._node_rects = {}
        for node in nodes:
            nid = node["id"]
            x = node.get("x", 0)
            y = node.get("y", 0)
            w = node.get("width", 200)
            h = node.get("height", 80)
            self._node_rects[nid] = Rect(x, y, w, h)

        # Style defaults
        bg_color = self.style.get("background_color", spec.get("background_color", "#ffffff"))
        text_color = self.style.get("text_color", "#1f2937")
        font_family = self.style.get("font_family", "system-ui, -apple-system, sans-serif")
        node_fill = self.style.get("node_fill", "#f9fafb")
        node_stroke = self.style.get("node_stroke", "#e5e7eb")
        corner_radius = self.style.get("corner_radius", 8)
        border_width = self.style.get("border_width", 1.5)

        # Flow type colors
        flow_colors = self.style.get(
            "flow_colors",
            {
                "control": "#6366f1",
                "data": "#3b82f6",
                "read": "#10b981",
                "write": "#f59e0b",
                "feedback": "#8b5cf6",
                "async": "#ec4899",
                "embed": "#7c3aed",
                "default": "#9ca3af",
            },
        )

        parts: list[str] = []

        # SVG header
        parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" '
            f'font-family="{escape(font_family)}">'
        )

        # Defs: gradients, filters, markers
        parts.append("<defs>")

        # Node drop shadow
        parts.append(
            '<filter id="shadow" x="-15%" y="-15%" width="140%" height="140%">'
            '<feDropShadow dx="0" dy="3" stdDeviation="6" flood-color="#000" flood-opacity="0.10"/>'
            "</filter>"
        )
        # Stronger shadow for containers
        parts.append(
            '<filter id="shadow-lg" x="-15%" y="-15%" width="140%" height="140%">'
            '<feDropShadow dx="0" dy="4" stdDeviation="10" flood-color="#000" flood-opacity="0.08"/>'
            "</filter>"
        )

        # Per-kind gradient defs
        for kind, (g_start, g_end, _stroke, _text, _ibg) in self._KIND_PALETTE.items():
            parts.append(
                f'<linearGradient id="grad-{kind}" x1="0" y1="0" x2="0" y2="1">'
                f'<stop offset="0%" stop-color="{g_start}"/>'
                f'<stop offset="100%" stop-color="{g_end}"/>'
                f"</linearGradient>"
            )

        # Arrow markers — larger, cleaner
        for flow_type, color in flow_colors.items():
            parts.append(
                f'<marker id="arrow-{flow_type}" viewBox="0 0 12 8" refX="11" refY="4" '
                f'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
                f'<path d="M0,0.5 L10,4 L0,7.5 Z" fill="{color}"/>'
                f"</marker>"
            )
        parts.append("</defs>")

        # Background
        parts.append(_svg_rect(0, 0, width, height, fill=bg_color, stroke="none", stroke_width=0))

        # Title and subtitle
        title_offset = 0
        if title:
            title_size = self.style.get("title_size", 26)
            parts.append(
                _svg_text(
                    width / 2,
                    42,
                    title,
                    font_size=title_size,
                    fill=text_color,
                    font_family=font_family,
                    font_weight="700",
                )
            )
            title_offset = 30
        if subtitle:
            parts.append(
                _svg_text(
                    width / 2,
                    42 + title_offset,
                    subtitle,
                    font_size=14,
                    fill=self.style.get("subtitle_color", "#6b7280"),
                    font_family=font_family,
                )
            )

        # Containers
        for container in containers:
            cx = container.get("x", 0)
            cy = container.get("y", 0)
            cw = container.get("width", 400)
            ch = container.get("height", 200)
            cfill = container.get("fill", self.style.get("container_fill", "#F8FAFC"))
            cstroke = container.get("stroke", self.style.get("container_stroke", "#E2E8F0"))
            cdash = self.style.get("container_stroke_dash", "")
            clabel = container.get("label", "")
            csubtitle = container.get("subtitle", "")
            clabel_color = container.get("label_color", self.style.get("container_label_color", "#6B7280"))
            clabel_size = self.style.get("container_label_size", 12)
            clabel_weight = self.style.get("container_label_weight", "600")
            uppercase = self.style.get("container_label_uppercase", False)

            # Container body
            crx = self.style.get("corner_radius", 8)
            dash_attr = f' stroke-dasharray="{cdash}"' if cdash else ""
            parts.append(
                f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" '
                f'rx="{crx}" fill="{cfill}" stroke="{cstroke}" stroke-width="1.5"{dash_attr}/>'
            )

            # Container label (top-left, no header strip)
            if clabel:
                display_label = clabel.upper() if uppercase else clabel
                parts.append(
                    _svg_text(
                        cx + 16,
                        cy + 20,
                        display_label,
                        font_size=clabel_size,
                        fill=clabel_color,
                        font_family=font_family,
                        font_weight=clabel_weight,
                        anchor="start",
                        dominant_baseline="central",
                    )
                )
            if csubtitle:
                parts.append(
                    _svg_text(
                        cx + 16,
                        cy + (38 if clabel else 20),
                        csubtitle,
                        font_size=11,
                        fill="#94a3b8",
                        font_family=font_family,
                        anchor="start",
                    )
                )

        # Arrows (edges)
        for arrow in arrows:
            src_id = arrow.get("source") or arrow.get("from")
            tgt_id = arrow.get("target") or arrow.get("to")
            if not src_id or not tgt_id:
                continue
            src_rect = self._node_rects.get(src_id)
            tgt_rect = self._node_rects.get(tgt_id)
            if not src_rect or not tgt_rect:
                continue

            flow = arrow.get("flow", "default")
            color = flow_colors.get(flow, flow_colors["default"])
            label = arrow.get("label", "")
            src_port = arrow.get("source_port", "")
            tgt_port = arrow.get("target_port", "")
            is_async = flow == "async"
            is_bidirectional = arrow.get("bidirectional", False)

            # Auto-detect ports if not specified
            if not src_port or not tgt_port:
                src_port, tgt_port = self._auto_ports(src_rect, tgt_rect)

            p1 = src_rect.port(src_port)
            p2 = tgt_rect.port(tgt_port)

            # Orthogonal (L-shaped) path — cleaner for architecture diagrams
            path_d = self._route_edge(p1, p2, src_port, tgt_port)
            dash = "8,5" if is_async else ""

            # Draw a subtle ghost line for emphasis on data flows
            if flow == "data":
                parts.append(
                    _svg_path(path_d, stroke=color, stroke_width=border_width + 2, fill="none", dash=dash).replace(
                        f'stroke-width="{border_width + 2}"', f'stroke-width="{border_width + 2}" opacity="0.15"'
                    )
                )

            parts.append(
                _svg_path(
                    path_d,
                    stroke=color,
                    stroke_width=border_width + 0.5,
                    marker_end=f"arrow-{flow}",
                    dash=dash,
                )
            )
            if is_bidirectional:
                parts.append(
                    _svg_path(
                        path_d,
                        stroke=color,
                        stroke_width=border_width + 0.5,
                        marker_end=f"arrow-{flow}",
                        dash=dash,
                    ).replace(
                        f'marker-end="url(#arrow-{flow})"',
                        f'marker-start="url(#arrow-{flow})" marker-end="url(#arrow-{flow})"',
                    )
                )

            # Arrow label
            if label:
                mid_x = (p1.x + p2.x) / 2
                mid_y = (p1.y + p2.y) / 2
                label_bg_w = len(label) * 7 + 20
                label_bg_h = 22
                parts.append(
                    _svg_rect(
                        mid_x - label_bg_w / 2,
                        mid_y - label_bg_h / 2,
                        label_bg_w,
                        label_bg_h,
                        rx=11,
                        fill=bg_color,
                        stroke=color,
                        stroke_width=1,
                        opacity=0.95,
                    )
                )
                parts.append(
                    _svg_text(
                        mid_x,
                        mid_y,
                        label,
                        font_size=11,
                        fill=self.style.get("label_color", "#6b7280"),
                        font_family=font_family,
                    )
                )

        # Nodes
        for node in nodes:
            nid = node["id"]
            rect = self._node_rects[nid]
            kind = node.get("kind", "rounded_rect")
            nlabel = node.get("label", nid)
            icon_name = node.get("icon", "")
            type_label = node.get("type_label", "")

            # Resolve color palette (per-kind unless overridden)
            pal_start, pal_end, pal_stroke, pal_text, pal_ibg = self._kind_palette(kind)
            use_gradients = self.style.get("use_node_gradients", True)
            nfill = node.get("fill") or (f"url(#grad-{kind})" if use_gradients else node_fill)
            nstroke = node.get("stroke") or (pal_stroke if use_gradients else node_stroke)
            node_text_color = pal_text if use_gradients else text_color

            # Render shape
            node_svg = self._render_node_shape(kind, rect, nfill, nstroke, 2.0, corner_radius, True)
            parts.append(node_svg)

            # Icon
            has_icon = False
            if icon_name:
                try:
                    from src.services.diagrams.icons import get_icon_svg

                    icon_size = 28
                    icon_x = rect.cx - icon_size / 2
                    icon_y = rect.y + 10
                    icon_svg = get_icon_svg(icon_name, icon_x, icon_y, icon_size)
                    if icon_svg:
                        parts.append(icon_svg)
                        has_icon = True
                except ImportError:
                    pass

            # Label positioning
            label_size = self.style.get("text_size", 14)
            type_label_size = self.style.get("type_label_size", 11)
            type_label_color = self.style.get("type_label_color", "#9ca3af")

            if has_icon:
                # icon at top, type_label then main label below icon
                type_label_y = rect.y + rect.height - (label_size + type_label_size + 6) if type_label else None
                text_y = rect.y + rect.height - label_size - 8
            else:
                if type_label:
                    # type_label ABOVE main label, centered vertically together
                    block_h = type_label_size + 4 + label_size
                    type_label_y = rect.cy - block_h / 2 + type_label_size / 2
                    text_y = type_label_y + type_label_size + 6
                else:
                    type_label_y = None
                    text_y = rect.cy

            # Type label (small uppercase, above main label)
            if type_label and type_label_y is not None:
                parts.append(
                    _svg_text(
                        rect.cx,
                        type_label_y,
                        type_label.upper(),
                        font_size=type_label_size,
                        fill=type_label_color,
                        font_family=font_family,
                        font_weight="500",
                        dominant_baseline="central",
                    )
                )

            # Wrap long labels
            label_lines = self._wrap_label(nlabel, int(rect.width / 8))
            if len(label_lines) == 1:
                parts.append(
                    _svg_text(
                        rect.cx,
                        text_y,
                        label_lines[0],
                        font_size=label_size,
                        fill=node_text_color,
                        font_family=font_family,
                        font_weight="700",
                    )
                )
            else:
                line_h = label_size + 3
                total_h = line_h * len(label_lines)
                start_y = text_y - total_h / 2 + label_size / 2
                for i, line in enumerate(label_lines):
                    parts.append(
                        _svg_text(
                            rect.cx,
                            start_y + i * line_h,
                            line,
                            font_size=label_size,
                            fill=node_text_color,
                            font_family=font_family,
                            font_weight="700",
                        )
                    )

        # Legend
        if legend:
            parts.append(
                self._render_legend(legend, legend_position, width, height, flow_colors, font_family, text_color)
            )

        parts.append("</svg>")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Dedicated renderers for non-architecture diagram types
    # ------------------------------------------------------------------

    def render_comparison(self, spec: dict[str, Any]) -> str:
        """Render a comparison / feature-matrix table."""
        title = spec.get("title", "")
        subtitle = spec.get("subtitle", "")
        columns = spec.get("columns", [])  # str or {"label": str, "color": str}
        rows = spec.get("rows", [])  # {"label": str, "values": [...]}

        font_family = self.style.get("font_family", "system-ui, sans-serif")
        bg_color = self.style.get("background_color", "#FFFFFF")
        text_color = self.style.get("text_color", "#1f2937")
        node_stroke = self.style.get("node_stroke", "#E5E7EB")
        corner_radius = self.style.get("corner_radius", 8)

        ROW_LABEL_W = 200
        COL_W = 160
        ROW_H = 44
        HEADER_H = 52
        MARGIN_X = 60

        n_cols = len(columns)
        n_rows = len(rows)

        title_offset = 28 if title else 0
        if subtitle:
            title_offset += 22
        table_top = 42 + title_offset + 14
        table_width = ROW_LABEL_W + n_cols * COL_W
        table_height = HEADER_H + n_rows * ROW_H

        canvas_width = max(600, MARGIN_X * 2 + table_width)
        canvas_height = table_top + table_height + 60
        table_left = (canvas_width - table_width) / 2

        col_colors = ["#3B82F6", "#10B981", "#8B5CF6", "#F59E0B", "#EC4899", "#14B8A6", "#F97316", "#EF4444"]

        parts: list[str] = []
        parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {canvas_width} {canvas_height:.0f}" '
            f'width="{canvas_width}" height="{canvas_height:.0f}" '
            f'font-family="{escape(font_family)}">'
        )
        parts.append("<defs>")
        parts.append(
            '<filter id="cmp-shadow" x="-5%" y="-5%" width="115%" height="115%">'
            '<feDropShadow dx="0" dy="2" stdDeviation="6" flood-color="#000" flood-opacity="0.08"/>'
            "</filter>"
        )
        parts.append("</defs>")
        parts.append(
            f'<rect x="0" y="0" width="{canvas_width}" height="{canvas_height:.0f}" fill="{bg_color}" stroke="none"/>'
        )

        ty = 40
        if title:
            parts.append(
                _svg_text(
                    canvas_width / 2,
                    ty,
                    title,
                    font_size=self.style.get("title_size", 22),
                    fill=text_color,
                    font_family=font_family,
                    font_weight="700",
                )
            )
            ty += 28
        if subtitle:
            parts.append(
                _svg_text(
                    canvas_width / 2,
                    ty,
                    subtitle,
                    font_size=13,
                    fill=self.style.get("subtitle_color", "#6b7280"),
                    font_family=font_family,
                )
            )

        # Table shadow + outline
        parts.append(
            f'<rect x="{table_left:.1f}" y="{table_top:.1f}" width="{table_width}" height="{table_height}" '
            f'rx="{corner_radius}" fill="{bg_color}" stroke="{node_stroke}" stroke-width="1.5" filter="url(#cmp-shadow)"/>'
        )

        # Top-left empty header cell
        header_bg = self.style.get("container_fill", "#F8FAFC")
        parts.append(
            f'<rect x="{table_left:.1f}" y="{table_top:.1f}" width="{ROW_LABEL_W}" height="{HEADER_H}" '
            f'rx="{corner_radius}" fill="{header_bg}" stroke="{node_stroke}" stroke-width="0.5"/>'
        )
        # Fix rounded corner on right side of label header
        parts.append(
            f'<rect x="{table_left + corner_radius:.1f}" y="{table_top:.1f}" '
            f'width="{ROW_LABEL_W - corner_radius:.1f}" height="{HEADER_H}" '
            f'fill="{header_bg}" stroke="none"/>'
        )

        # Column headers
        for ci, col in enumerate(columns):
            col_label = col if isinstance(col, str) else col.get("label", str(ci))
            col_color = (col.get("color") if isinstance(col, dict) else None) or col_colors[ci % len(col_colors)]
            cx = table_left + ROW_LABEL_W + ci * COL_W
            parts.append(
                f'<rect x="{cx:.1f}" y="{table_top:.1f}" width="{COL_W}" height="{HEADER_H}" '
                f'fill="{col_color}" stroke="{node_stroke}" stroke-width="0.5"/>'
            )
            parts.append(
                _svg_text(
                    cx + COL_W / 2,
                    table_top + HEADER_H / 2,
                    col_label,
                    font_size=13,
                    fill="#FFFFFF",
                    font_family=font_family,
                    font_weight="700",
                )
            )

        # Data rows
        for ri, row in enumerate(rows):
            row_label = row.get("label", "") if isinstance(row, dict) else str(row)
            values = row.get("values", []) if isinstance(row, dict) else []
            row_y = table_top + HEADER_H + ri * ROW_H
            row_bg = "#FFFFFF" if ri % 2 == 0 else self.style.get("container_fill", "#F8FAFC")

            parts.append(
                f'<rect x="{table_left:.1f}" y="{row_y:.1f}" width="{ROW_LABEL_W}" height="{ROW_H}" '
                f'fill="{row_bg}" stroke="{node_stroke}" stroke-width="0.5"/>'
            )
            parts.append(
                _svg_text(
                    table_left + 16,
                    row_y + ROW_H / 2,
                    row_label,
                    font_size=13,
                    fill=text_color,
                    font_family=font_family,
                    font_weight="500",
                    anchor="start",
                )
            )

            for ci, val in enumerate(values[:n_cols]):
                vx = table_left + ROW_LABEL_W + ci * COL_W
                parts.append(
                    f'<rect x="{vx:.1f}" y="{row_y:.1f}" width="{COL_W}" height="{ROW_H}" '
                    f'fill="{row_bg}" stroke="{node_stroke}" stroke-width="0.5"/>'
                )
                val_str = str(val)
                val_color = text_color
                if val_str in ("✓", "✔", "Yes", "yes", "true", "True"):
                    val_color = "#10B981"
                    val_str = "✓"
                elif val_str in ("✗", "✘", "No", "no", "false", "False", "—", "-"):
                    val_color = "#EF4444"
                    val_str = "✗"
                parts.append(
                    _svg_text(
                        vx + COL_W / 2,
                        row_y + ROW_H / 2,
                        val_str,
                        font_size=13,
                        fill=val_color,
                        font_family=font_family,
                        font_weight="600" if val_str in ("✓", "✗") else "normal",
                    )
                )

        # Grid lines
        for ri in range(1, n_rows + 1):
            dy = table_top + HEADER_H + ri * ROW_H
            if dy < table_top + table_height:
                parts.append(
                    f'<line x1="{table_left:.1f}" y1="{dy:.1f}" x2="{table_left + table_width:.1f}" y2="{dy:.1f}" '
                    f'stroke="{node_stroke}" stroke-width="0.5"/>'
                )
        vx0 = table_left + ROW_LABEL_W
        parts.append(
            f'<line x1="{vx0:.1f}" y1="{table_top:.1f}" x2="{vx0:.1f}" y2="{table_top + table_height:.1f}" '
            f'stroke="{node_stroke}" stroke-width="1.5"/>'
        )
        for ci in range(1, n_cols):
            vx = table_left + ROW_LABEL_W + ci * COL_W
            parts.append(
                f'<line x1="{vx:.1f}" y1="{table_top:.1f}" x2="{vx:.1f}" y2="{table_top + table_height:.1f}" '
                f'stroke="{node_stroke}" stroke-width="0.5"/>'
            )

        parts.append("</svg>")
        return "\n".join(parts)

    def render_timeline(self, spec: dict[str, Any]) -> str:
        """Render a Gantt-style timeline / roadmap."""
        title = spec.get("title", "")
        subtitle = spec.get("subtitle", "")
        periods = spec.get("periods", [])  # ["Q1","Q2","Q3","Q4"] or ["Week 1", ...]
        tracks = spec.get("tracks", [])  # [{"label":..., "start":0, "end":2, "color":...}]
        milestones = spec.get("milestones", [])  # [{"label":..., "at":2.5, "color":"#EF4444"}]

        font_family = self.style.get("font_family", "system-ui, sans-serif")
        bg_color = self.style.get("background_color", "#FFFFFF")
        text_color = self.style.get("text_color", "#1f2937")
        node_stroke = self.style.get("node_stroke", "#E5E7EB")
        grid_color = self.style.get("container_stroke", "#E5E7EB")

        LABEL_W = 180
        PERIOD_W = 140
        TRACK_H = 48
        AXIS_H = 44
        BAR_H = 28
        BAR_R = 6
        MARGIN_X = 60

        n_periods = max(len(periods), 1)
        n_tracks = len(tracks)

        title_offset = 38 if title else 0
        if subtitle:
            title_offset += 22
        axis_y = 42 + title_offset
        content_top = axis_y + AXIS_H

        chart_width = LABEL_W + n_periods * PERIOD_W
        canvas_width = max(700, MARGIN_X * 2 + chart_width)
        chart_left = (canvas_width - chart_width) / 2
        canvas_height = content_top + n_tracks * TRACK_H + 80

        track_colors = ["#3B82F6", "#10B981", "#8B5CF6", "#F59E0B", "#EC4899", "#14B8A6", "#F97316", "#EF4444"]

        parts: list[str] = []
        parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {canvas_width} {canvas_height:.0f}" '
            f'width="{canvas_width}" height="{canvas_height:.0f}" '
            f'font-family="{escape(font_family)}">'
        )
        parts.append("<defs>")
        parts.append(
            '<filter id="tl-shadow" x="-5%" y="-5%" width="115%" height="115%">'
            '<feDropShadow dx="0" dy="1" stdDeviation="3" flood-color="#000" flood-opacity="0.12"/>'
            "</filter>"
        )
        parts.append("</defs>")
        parts.append(
            f'<rect x="0" y="0" width="{canvas_width}" height="{canvas_height:.0f}" fill="{bg_color}" stroke="none"/>'
        )

        ty = 38
        if title:
            parts.append(
                _svg_text(
                    canvas_width / 2,
                    ty,
                    title,
                    font_size=self.style.get("title_size", 22),
                    fill=text_color,
                    font_family=font_family,
                    font_weight="700",
                )
            )
            ty += 28
        if subtitle:
            parts.append(
                _svg_text(
                    canvas_width / 2,
                    ty,
                    subtitle,
                    font_size=13,
                    fill=self.style.get("subtitle_color", "#6b7280"),
                    font_family=font_family,
                )
            )

        period_area_x = chart_left + LABEL_W
        header_bg = self.style.get("container_fill", "#F8FAFC")

        # Period headers
        for pi, period in enumerate(periods):
            px = period_area_x + pi * PERIOD_W
            parts.append(
                f'<rect x="{px:.1f}" y="{axis_y:.1f}" width="{PERIOD_W}" height="{AXIS_H}" '
                f'fill="{header_bg}" stroke="{node_stroke}" stroke-width="0.5"/>'
            )
            parts.append(
                _svg_text(
                    px + PERIOD_W / 2,
                    axis_y + AXIS_H / 2,
                    str(period),
                    font_size=12,
                    fill=text_color,
                    font_family=font_family,
                    font_weight="600",
                )
            )

        # Vertical grid lines (drawn first behind rows)
        for pi in range(n_periods + 1):
            gx = period_area_x + pi * PERIOD_W
            parts.append(
                f'<line x1="{gx:.1f}" y1="{content_top:.1f}" x2="{gx:.1f}" y2="{content_top + n_tracks * TRACK_H:.1f}" '
                f'stroke="{grid_color}" stroke-width="0.5"/>'
            )

        # Track rows
        for ti, track in enumerate(tracks):
            track_y = content_top + ti * TRACK_H
            row_bg = "#FFFFFF" if ti % 2 == 0 else self.style.get("container_fill", "#F8FAFC")

            parts.append(
                f'<rect x="{chart_left:.1f}" y="{track_y:.1f}" width="{chart_width}" height="{TRACK_H}" '
                f'fill="{row_bg}" stroke="{node_stroke}" stroke-width="0.5"/>'
            )
            label = track.get("label", f"Task {ti + 1}")
            parts.append(
                _svg_text(
                    chart_left + LABEL_W - 12,
                    track_y + TRACK_H / 2,
                    label,
                    font_size=13,
                    fill=text_color,
                    font_family=font_family,
                    font_weight="500",
                    anchor="end",
                )
            )

            start = float(track.get("start", 0))
            end = float(track.get("end", 1))
            color = track.get("color") or track_colors[ti % len(track_colors)]
            bar_x = period_area_x + start * PERIOD_W
            bar_w = max(4.0, (end - start) * PERIOD_W)
            bar_y = track_y + (TRACK_H - BAR_H) / 2

            parts.append(
                f'<rect x="{bar_x:.1f}" y="{bar_y:.1f}" width="{bar_w:.1f}" height="{BAR_H}" '
                f'rx="{BAR_R}" fill="{color}" filter="url(#tl-shadow)"/>'
            )
            if bar_w > 60:
                r, g, b = _hex_to_rgb(color)
                bar_text = "#FFFFFF" if (0.299 * r + 0.587 * g + 0.114 * b) < 160 else "#1f2937"
                parts.append(
                    _svg_text(
                        bar_x + bar_w / 2,
                        bar_y + BAR_H / 2,
                        label,
                        font_size=11,
                        fill=bar_text,
                        font_family=font_family,
                        font_weight="600",
                    )
                )

        # Row separator lines
        parts.append(
            f'<line x1="{chart_left:.1f}" y1="{content_top:.1f}" x2="{chart_left + chart_width:.1f}" y2="{content_top:.1f}" '
            f'stroke="{node_stroke}" stroke-width="1"/>'
        )

        # Milestones
        for ms in milestones:
            ms_at = float(ms.get("at", 0))
            ms_label = ms.get("label", "")
            ms_color = ms.get("color") or "#EF4444"
            ms_x = period_area_x + ms_at * PERIOD_W
            d_size = 9
            ms_y = content_top - 8

            parts.append(
                f'<polygon points="{ms_x:.1f},{ms_y - d_size:.1f} {ms_x + d_size:.1f},{ms_y:.1f} '
                f'{ms_x:.1f},{ms_y + d_size:.1f} {ms_x - d_size:.1f},{ms_y:.1f}" '
                f'fill="{ms_color}" stroke="#FFFFFF" stroke-width="2"/>'
            )
            parts.append(
                f'<line x1="{ms_x:.1f}" y1="{ms_y + d_size:.1f}" '
                f'x2="{ms_x:.1f}" y2="{content_top + n_tracks * TRACK_H:.1f}" '
                f'stroke="{ms_color}" stroke-width="1.5" stroke-dasharray="4,3"/>'
            )
            if ms_label:
                parts.append(
                    _svg_text(
                        ms_x,
                        ms_y - d_size - 5,
                        ms_label,
                        font_size=11,
                        fill=ms_color,
                        font_family=font_family,
                        font_weight="600",
                    )
                )

        parts.append("</svg>")
        return "\n".join(parts)

    def render_mind_map(self, spec: dict[str, Any]) -> str:
        """Render a radial mind map."""
        title = spec.get("title", "")
        center_label = spec.get("center", "Topic")
        branches = spec.get("branches", [])

        font_family = self.style.get("font_family", "system-ui, sans-serif")
        bg_color = self.style.get("background_color", "#FFFFFF")
        text_color = self.style.get("text_color", "#1f2937")

        CENTER_R = 60
        BRANCH_DIST = 200
        LEAF_DIST = 130
        BRANCH_W = 120
        BRANCH_H = 42
        LEAF_W = 100
        LEAF_H = 32

        n_branches = max(len(branches), 1)
        canvas_w = 960
        title_h = 50 if title else 0
        canvas_h = 760 + title_h

        cx = canvas_w / 2
        cy = canvas_h / 2 + title_h / 4

        branch_colors = ["#3B82F6", "#10B981", "#8B5CF6", "#F59E0B", "#EC4899", "#14B8A6", "#F97316", "#EF4444"]

        parts: list[str] = []
        parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {canvas_w} {canvas_h}" '
            f'width="{canvas_w}" height="{canvas_h}" '
            f'font-family="{escape(font_family)}">'
        )
        parts.append("<defs>")
        parts.append(
            '<filter id="mm-shadow" x="-15%" y="-15%" width="140%" height="140%">'
            '<feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#000" flood-opacity="0.12"/>'
            "</filter>"
        )
        parts.append("</defs>")
        parts.append(f'<rect x="0" y="0" width="{canvas_w}" height="{canvas_h}" fill="{bg_color}" stroke="none"/>')

        if title:
            parts.append(
                _svg_text(
                    canvas_w / 2,
                    36,
                    title,
                    font_size=self.style.get("title_size", 22),
                    fill=text_color,
                    font_family=font_family,
                    font_weight="700",
                )
            )

        # Draw branch connectors + leaves first (behind center)
        for bi, branch in enumerate(branches):
            angle = (2 * math.pi * bi / n_branches) - math.pi / 2
            color = branch.get("color") or branch_colors[bi % len(branch_colors)]
            branch_label = branch.get("label", "")
            children = branch.get("children", [])

            bx = cx + BRANCH_DIST * math.cos(angle)
            by = cy + BRANCH_DIST * math.sin(angle)

            # Center → branch line
            parts.append(
                f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
                f'stroke="{color}" stroke-width="3" opacity="0.5"/>'
            )

            # Leaf nodes
            n_ch = len(children)
            for ci_idx, child in enumerate(children):
                if n_ch == 1:
                    leaf_angle = angle
                else:
                    spread = math.pi / 3.5
                    leaf_angle = angle - spread / 2 + spread * ci_idx / (n_ch - 1)

                lx = bx + LEAF_DIST * math.cos(leaf_angle)
                ly = by + LEAF_DIST * math.sin(leaf_angle)

                parts.append(
                    f'<line x1="{bx:.1f}" y1="{by:.1f}" x2="{lx:.1f}" y2="{ly:.1f}" '
                    f'stroke="{color}" stroke-width="1.5" opacity="0.4"/>'
                )
                r, g, b_val = _hex_to_rgb(color)
                leaf_fill = f"rgba({r},{g},{b_val},0.10)"
                parts.append(
                    f'<rect x="{lx - LEAF_W / 2:.1f}" y="{ly - LEAF_H / 2:.1f}" '
                    f'width="{LEAF_W}" height="{LEAF_H}" rx="16" '
                    f'fill="{leaf_fill}" stroke="{color}" stroke-width="1.5"/>'
                )
                child_label = child if isinstance(child, str) else child.get("label", str(child))
                parts.append(
                    _svg_text(
                        lx, ly, child_label, font_size=11, fill=text_color, font_family=font_family, font_weight="500"
                    )
                )

            # Branch node
            r_c, g_c, b_c = _hex_to_rgb(color)
            luma = 0.299 * r_c + 0.587 * g_c + 0.114 * b_c
            branch_text_color = "#FFFFFF" if luma < 160 else "#1f2937"
            parts.append(
                f'<rect x="{bx - BRANCH_W / 2:.1f}" y="{by - BRANCH_H / 2:.1f}" '
                f'width="{BRANCH_W}" height="{BRANCH_H}" rx="21" '
                f'fill="{color}" stroke="none" filter="url(#mm-shadow)"/>'
            )
            parts.append(
                _svg_text(
                    bx,
                    by,
                    branch_label,
                    font_size=13,
                    fill=branch_text_color,
                    font_family=font_family,
                    font_weight="700",
                )
            )

        # Center node (on top)
        node_fill = self.style.get("node_fill", "#FFFFFF")
        node_stroke = self.style.get("node_stroke", "#D1D5DB")
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{CENTER_R}" '
            f'fill="{node_fill}" stroke="{node_stroke}" stroke-width="2.5" filter="url(#mm-shadow)"/>'
        )
        center_lines = self._wrap_label(center_label, 12)
        line_h = 16
        start_y = cy - (len(center_lines) - 1) * line_h / 2
        for li, line in enumerate(center_lines):
            parts.append(
                _svg_text(
                    cx,
                    start_y + li * line_h,
                    line,
                    font_size=14,
                    fill=text_color,
                    font_family=font_family,
                    font_weight="700",
                )
            )

        parts.append("</svg>")
        return "\n".join(parts)

    def render_er_diagram(self, spec: dict[str, Any]) -> str:
        """Render an Entity-Relationship (ER) diagram."""
        title = spec.get("title", "")
        entities = spec.get("entities", [])
        relationships = spec.get("relationships", [])

        font_family = self.style.get("font_family", "system-ui, sans-serif")
        bg_color = self.style.get("background_color", "#FFFFFF")
        text_color = self.style.get("text_color", "#1f2937")
        node_fill = self.style.get("node_fill", "#FFFFFF")
        node_stroke = self.style.get("node_stroke", "#D1D5DB")
        corner_radius = self.style.get("corner_radius", 6)

        ENT_W = 210
        HEADER_H = 40
        ATTR_H = 28
        MARGIN_X = 60

        # Compute per-entity height
        ent_meta: dict[str, dict] = {}
        for ent in entities:
            n_attrs = len(ent.get("attributes", []))
            ent_meta[ent["id"]] = {"h": HEADER_H + max(1, n_attrs) * ATTR_H}

        # Auto-layout if positions missing
        if entities and not entities[0].get("x"):
            n = len(entities)
            cols = min(3, max(1, n))
            max_h = max((ent_meta[e["id"]]["h"] for e in entities), default=120)
            title_h = 50 if title else 20
            for i, ent in enumerate(entities):
                ent["x"] = MARGIN_X + (i % cols) * (ENT_W + 140)
                ent["y"] = title_h + MARGIN_X + (i // cols) * (max_h + 80)

        max_x = max((e.get("x", 0) + ENT_W for e in entities), default=700)
        max_y = max((e.get("y", 0) + ent_meta[e["id"]]["h"] for e in entities), default=400)
        canvas_width = max(700, max_x + MARGIN_X)
        canvas_height = max(500, max_y + 80)

        rel_color = self.style.get("flow_colors", {}).get("control", "#6366f1")

        parts: list[str] = []
        parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {canvas_width} {canvas_height}" '
            f'width="{canvas_width}" height="{canvas_height}" '
            f'font-family="{escape(font_family)}">'
        )
        parts.append("<defs>")
        parts.append(
            '<filter id="er-shadow" x="-5%" y="-5%" width="115%" height="115%">'
            '<feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#000" flood-opacity="0.10"/>'
            "</filter>"
        )
        parts.append(
            f'<marker id="er-arrow" viewBox="0 0 10 6" refX="9" refY="3" '
            f'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
            f'<path d="M0,0.5 L9,3 L0,5.5 Z" fill="{rel_color}"/>'
            f"</marker>"
        )
        parts.append("</defs>")
        parts.append(
            f'<rect x="0" y="0" width="{canvas_width}" height="{canvas_height}" fill="{bg_color}" stroke="none"/>'
        )

        if title:
            parts.append(
                _svg_text(
                    canvas_width / 2,
                    40,
                    title,
                    font_size=self.style.get("title_size", 22),
                    fill=text_color,
                    font_family=font_family,
                    font_weight="700",
                )
            )

        # Build rects for routing
        ent_rects: dict[str, Rect] = {}
        for ent in entities:
            ent_rects[ent["id"]] = Rect(ent.get("x", 0), ent.get("y", 0), ENT_W, ent_meta[ent["id"]]["h"])

        # Relationships (drawn behind entities)
        for rel in relationships:
            r1 = ent_rects.get(rel.get("from", ""))
            r2 = ent_rects.get(rel.get("to", ""))
            if not r1 or not r2:
                continue
            sp, tp = self._auto_ports(r1, r2)
            p1, p2 = r1.port(sp), r2.port(tp)
            path_d = self._route_edge(p1, p2, sp, tp)
            parts.append(
                f'<path d="{path_d}" stroke="{rel_color}" stroke-width="1.5" fill="none" marker-end="url(#er-arrow)"/>'
            )
            label = rel.get("label", "")
            from_card = rel.get("from_card", "1")
            to_card = rel.get("to_card", "N")
            mid_x, mid_y = (p1.x + p2.x) / 2, (p1.y + p2.y) / 2
            if label:
                parts.append(
                    _svg_text(
                        mid_x,
                        mid_y - 10,
                        label,
                        font_size=11,
                        fill=rel_color,
                        font_family=font_family,
                        font_weight="600",
                    )
                )
            parts.append(
                _svg_text(
                    p1.x + (10 if sp == "right" else -10),
                    p1.y - 8,
                    from_card,
                    font_size=11,
                    fill=text_color,
                    font_family=font_family,
                )
            )
            parts.append(
                _svg_text(
                    p2.x + (10 if tp == "left" else -10),
                    p2.y - 8,
                    to_card,
                    font_size=11,
                    fill=text_color,
                    font_family=font_family,
                )
            )

        # Entities
        for ent in entities:
            x, y = ent.get("x", 0), ent.get("y", 0)
            h = ent_meta[ent["id"]]["h"]
            label = ent.get("label", ent["id"])
            attributes = ent.get("attributes", [])
            hdr_color = ent.get("color", "#3B82F6")

            parts.append(
                f'<rect x="{x}" y="{y}" width="{ENT_W}" height="{h}" rx="{corner_radius}" '
                f'fill="{node_fill}" stroke="{node_stroke}" stroke-width="1.5" filter="url(#er-shadow)"/>'
            )
            # Header
            parts.append(
                f'<rect x="{x}" y="{y}" width="{ENT_W}" height="{HEADER_H}" rx="{corner_radius}" '
                f'fill="{hdr_color}" stroke="none"/>'
            )
            parts.append(
                f'<rect x="{x}" y="{y + HEADER_H - corner_radius}" width="{ENT_W}" height="{corner_radius}" '
                f'fill="{hdr_color}" stroke="none"/>'
            )
            parts.append(
                _svg_text(
                    x + ENT_W / 2,
                    y + HEADER_H / 2,
                    label,
                    font_size=14,
                    fill="#FFFFFF",
                    font_family=font_family,
                    font_weight="700",
                )
            )

            # Attributes
            for ai, attr in enumerate(attributes):
                ay = y + HEADER_H + ai * ATTR_H
                parts.append(
                    f'<line x1="{x}" y1="{ay}" x2="{x + ENT_W}" y2="{ay}" stroke="{node_stroke}" stroke-width="0.5"/>'
                )
                attr_name = attr.get("name", str(attr)) if isinstance(attr, dict) else str(attr)
                attr_type = attr.get("type", "") if isinstance(attr, dict) else ""
                is_pk = attr.get("pk", False) if isinstance(attr, dict) else False
                is_fk = attr.get("fk", False) if isinstance(attr, dict) else False
                display = f"{attr_name}: {attr_type}" if attr_type else attr_name
                if is_pk:
                    display = f"PK  {display}"
                elif is_fk:
                    display = f"FK  {display}"
                attr_color = "#B45309" if is_pk else ("#6366F1" if is_fk else text_color)
                parts.append(
                    _svg_text(
                        x + 10,
                        ay + ATTR_H / 2,
                        display,
                        font_size=12,
                        fill=attr_color,
                        font_family=font_family,
                        font_weight="600" if is_pk else "normal",
                        anchor="start",
                    )
                )

        parts.append("</svg>")
        return "\n".join(parts)

    def render_class_diagram(self, spec: dict[str, Any]) -> str:
        """Render a UML class diagram."""
        title = spec.get("title", "")
        classes = spec.get("classes", [])
        relationships = spec.get("relationships", [])

        font_family = self.style.get("font_family", "system-ui, sans-serif")
        bg_color = self.style.get("background_color", "#FFFFFF")
        text_color = self.style.get("text_color", "#1f2937")
        node_fill = self.style.get("node_fill", "#FFFFFF")
        node_stroke = self.style.get("node_stroke", "#D1D5DB")
        corner_radius = self.style.get("corner_radius", 4)

        CLASS_W = 210
        HEADER_H = 44
        SECTION_H = 24
        MIN_SECTION_H = 26
        MARGIN_X = 60

        cls_meta: dict[str, dict] = {}
        for cls in classes:
            attrs_h = max(MIN_SECTION_H, len(cls.get("attributes", [])) * SECTION_H)
            meths_h = max(MIN_SECTION_H, len(cls.get("methods", [])) * SECTION_H)
            cls_meta[cls["id"]] = {"h": HEADER_H + attrs_h + meths_h, "attrs_h": attrs_h}

        # Auto-layout
        if classes and not classes[0].get("x"):
            n = len(classes)
            cols = min(3, max(1, n))
            title_h = 50 if title else 20
            max_h = max((cls_meta[c["id"]]["h"] for c in classes), default=120)
            for i, cls in enumerate(classes):
                cls["x"] = MARGIN_X + (i % cols) * (CLASS_W + 130)
                cls["y"] = title_h + MARGIN_X + (i // cols) * (max_h + 80)

        max_x = max((c.get("x", 0) + CLASS_W for c in classes), default=700)
        max_y = max((c.get("y", 0) + cls_meta[c["id"]]["h"] for c in classes), default=500)
        canvas_width = max(700, max_x + MARGIN_X)
        canvas_height = max(500, max_y + 80)

        rel_styles: dict[str, tuple[str, bool, bool]] = {
            # type → (color, dashed, hollow_arrowhead)
            "extends": ("#8B5CF6", False, True),
            "implements": ("#6366F1", True, True),
            "association": ("#3B82F6", False, False),
            "aggregation": ("#10B981", False, False),
            "composition": ("#F59E0B", False, False),
            "dependency": ("#9CA3AF", True, False),
        }

        parts: list[str] = []
        parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {canvas_width} {canvas_height}" '
            f'width="{canvas_width}" height="{canvas_height}" '
            f'font-family="{escape(font_family)}">'
        )
        parts.append("<defs>")
        for rel_type, (rc, _dashed, hollow) in rel_styles.items():
            mp = "M0,1 L8,4.5 L0,8" if hollow else "M0,0.5 L9,4.5 L0,8.5 Z"
            mf = "none" if hollow else rc
            parts.append(
                f'<marker id="cls-{rel_type}" viewBox="0 0 10 10" refX="9" refY="4.5" '
                f'markerWidth="9" markerHeight="9" orient="auto-start-reverse">'
                f'<path d="{mp}" fill="{mf}" stroke="{rc}" stroke-width="1"/>'
                f"</marker>"
            )
        parts.append(
            '<filter id="cls-shadow" x="-5%" y="-5%" width="115%" height="115%">'
            '<feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#000" flood-opacity="0.10"/>'
            "</filter>"
        )
        parts.append("</defs>")
        parts.append(
            f'<rect x="0" y="0" width="{canvas_width}" height="{canvas_height}" fill="{bg_color}" stroke="none"/>'
        )

        if title:
            parts.append(
                _svg_text(
                    canvas_width / 2,
                    38,
                    title,
                    font_size=self.style.get("title_size", 22),
                    fill=text_color,
                    font_family=font_family,
                    font_weight="700",
                )
            )

        cls_rects: dict[str, Rect] = {}
        for cls in classes:
            cls_rects[cls["id"]] = Rect(cls.get("x", 0), cls.get("y", 0), CLASS_W, cls_meta[cls["id"]]["h"])

        # Relationships
        for rel in relationships:
            r1 = cls_rects.get(rel.get("from", ""))
            r2 = cls_rects.get(rel.get("to", ""))
            if not r1 or not r2:
                continue
            rel_type = rel.get("type", "association")
            rc, is_dashed, _hollow = rel_styles.get(rel_type, ("#9CA3AF", False, False))
            sp, tp = self._auto_ports(r1, r2)
            p1, p2 = r1.port(sp), r2.port(tp)
            path_d = self._route_edge(p1, p2, sp, tp)
            dash_attr = ' stroke-dasharray="8,5"' if is_dashed else ""
            parts.append(
                f'<path d="{path_d}" stroke="{rc}" stroke-width="1.5" fill="none"'
                f'{dash_attr} marker-end="url(#cls-{rel_type})"/>'
            )
            label = rel.get("label", "")
            if label:
                parts.append(
                    _svg_text(
                        (p1.x + p2.x) / 2 + 8,
                        (p1.y + p2.y) / 2 - 8,
                        label,
                        font_size=11,
                        fill=rc,
                        font_family=font_family,
                    )
                )

        # Classes
        header_fill = self.style.get("container_fill", "#EFF6FF")
        for cls in classes:
            x, y = cls.get("x", 0), cls.get("y", 0)
            h = cls_meta[cls["id"]]["h"]
            attrs_h = cls_meta[cls["id"]]["attrs_h"]
            name = cls.get("name", cls["id"])
            attributes = cls.get("attributes", [])
            methods = cls.get("methods", [])
            is_abstract = cls.get("abstract", False)
            is_interface = cls.get("interface", False)
            stereotype = "«interface»" if is_interface else ("«abstract»" if is_abstract else "")

            # Box
            parts.append(
                f'<rect x="{x}" y="{y}" width="{CLASS_W}" height="{h}" rx="{corner_radius}" '
                f'fill="{node_fill}" stroke="{node_stroke}" stroke-width="1.5" filter="url(#cls-shadow)"/>'
            )
            # Header fill
            parts.append(
                f'<rect x="{x}" y="{y}" width="{CLASS_W}" height="{HEADER_H}" rx="{corner_radius}" '
                f'fill="{header_fill}" stroke="none"/>'
            )
            parts.append(
                f'<rect x="{x}" y="{y + HEADER_H - corner_radius}" width="{CLASS_W}" height="{corner_radius}" '
                f'fill="{header_fill}" stroke="none"/>'
            )
            if stereotype:
                parts.append(
                    _svg_text(
                        x + CLASS_W / 2, y + 14, stereotype, font_size=10, fill="#6B7280", font_family=font_family
                    )
                )
                parts.append(
                    _svg_text(
                        x + CLASS_W / 2,
                        y + 30,
                        name,
                        font_size=13,
                        fill=text_color,
                        font_family=font_family,
                        font_weight="700",
                    )
                )
            else:
                parts.append(
                    _svg_text(
                        x + CLASS_W / 2,
                        y + HEADER_H / 2,
                        name,
                        font_size=14,
                        fill=text_color,
                        font_family=font_family,
                        font_weight="700",
                    )
                )

            # Attribute section
            attr_y = y + HEADER_H
            parts.append(
                f'<line x1="{x}" y1="{attr_y}" x2="{x + CLASS_W}" y2="{attr_y}" '
                f'stroke="{node_stroke}" stroke-width="1"/>'
            )
            for ai, attr in enumerate(attributes):
                parts.append(
                    _svg_text(
                        x + 10,
                        attr_y + SECTION_H / 2 + ai * SECTION_H,
                        str(attr),
                        font_size=12,
                        fill=text_color,
                        font_family=font_family,
                        anchor="start",
                    )
                )

            # Methods section
            meth_y = y + HEADER_H + attrs_h
            parts.append(
                f'<line x1="{x}" y1="{meth_y}" x2="{x + CLASS_W}" y2="{meth_y}" '
                f'stroke="{node_stroke}" stroke-width="1"/>'
            )
            for mi, meth in enumerate(methods):
                parts.append(
                    _svg_text(
                        x + 10,
                        meth_y + SECTION_H / 2 + mi * SECTION_H,
                        str(meth),
                        font_size=12,
                        fill=text_color,
                        font_family=font_family,
                        anchor="start",
                    )
                )

        parts.append("</svg>")
        return "\n".join(parts)

    def render_use_case(self, spec: dict[str, Any]) -> str:
        """Render a UML use case diagram."""
        title = spec.get("title", "")
        system_label = spec.get("system", "System")
        actors = spec.get("actors", [])
        use_cases = spec.get("use_cases", [])
        relationships = spec.get("relationships", [])

        font_family = self.style.get("font_family", "system-ui, sans-serif")
        bg_color = self.style.get("background_color", "#FFFFFF")
        text_color = self.style.get("text_color", "#1f2937")

        UC_RX = 85  # half-width of ellipse
        UC_RY = 30  # half-height of ellipse
        UC_V_GAP = 70  # vertical gap between use cases
        UC_H_GAP = 220  # horizontal gap between use case columns
        ACTOR_MARGIN = 100  # horizontal margin for actor columns
        SYS_PAD_X = 50
        SYS_PAD_Y = 50

        n_uc = len(use_cases)
        uc_cols = min(2, max(1, n_uc))
        uc_rows = math.ceil(n_uc / uc_cols)

        sys_inner_w = uc_cols * UC_H_GAP
        sys_inner_h = uc_rows * (UC_RY * 2 + UC_V_GAP) + UC_V_GAP

        title_h = 50 if title else 20
        sys_top = title_h + 40
        left_actors = [a for a in actors if a.get("side", "left") == "left"]
        right_actors = [a for a in actors if a.get("side", "right") == "right"]
        sys_left = ACTOR_MARGIN + (60 if left_actors else 0)

        canvas_width = sys_left + sys_inner_w + SYS_PAD_X * 2 + (ACTOR_MARGIN + 60 if right_actors else 0) + 40
        canvas_height = sys_top + sys_inner_h + SYS_PAD_Y * 2 + 60
        sys_w = sys_inner_w + SYS_PAD_X * 2
        sys_h = sys_inner_h + SYS_PAD_Y * 2

        rel_color = self.style.get("flow_colors", {}).get("control", "#6366f1")

        parts: list[str] = []
        parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {canvas_width} {canvas_height}" '
            f'width="{canvas_width}" height="{canvas_height}" '
            f'font-family="{escape(font_family)}">'
        )
        parts.append("<defs>")
        parts.append(
            f'<marker id="uc-arrow" viewBox="0 0 10 6" refX="9" refY="3" '
            f'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
            f'<path d="M0,0.5 L9,3 L0,5.5 Z" fill="{rel_color}"/>'
            f"</marker>"
        )
        parts.append("</defs>")
        parts.append(
            f'<rect x="0" y="0" width="{canvas_width}" height="{canvas_height}" fill="{bg_color}" stroke="none"/>'
        )

        if title:
            parts.append(
                _svg_text(
                    canvas_width / 2,
                    36,
                    title,
                    font_size=self.style.get("title_size", 22),
                    fill=text_color,
                    font_family=font_family,
                    font_weight="700",
                )
            )

        # System boundary
        sys_stroke = self.style.get("container_stroke", "#D1D5DB")
        sys_fill = self.style.get("container_fill", "#F8FAFC")
        parts.append(
            f'<rect x="{sys_left}" y="{sys_top}" width="{sys_w}" height="{sys_h}" '
            f'rx="8" fill="{sys_fill}" stroke="{sys_stroke}" stroke-width="1.5" stroke-dasharray="8,4"/>'
        )
        parts.append(
            _svg_text(
                sys_left + 14,
                sys_top + 18,
                system_label,
                font_size=13,
                fill=self.style.get("container_label_color", "#6B7280"),
                font_family=font_family,
                font_weight="600",
                anchor="start",
            )
        )

        # Use case positions
        uc_positions: dict[str, tuple[float, float]] = {}
        for ui, uc in enumerate(use_cases):
            col = ui % uc_cols
            row = ui // uc_cols
            ucx = sys_left + SYS_PAD_X + col * UC_H_GAP + UC_H_GAP / 2
            ucy = sys_top + SYS_PAD_Y + UC_V_GAP / 2 + row * (UC_RY * 2 + UC_V_GAP) + UC_RY
            uc_positions[uc["id"]] = (ucx, ucy)

        # Actor positions
        actor_positions: dict[str, tuple[float, float]] = {}
        for ai, actor in enumerate(left_actors):
            spc = sys_h / (len(left_actors) + 1)
            actor_positions[actor["id"]] = (sys_left - ACTOR_MARGIN / 2 - 10, sys_top + spc * (ai + 1))
        for ai, actor in enumerate(right_actors):
            spc = sys_h / (len(right_actors) + 1)
            actor_positions[actor["id"]] = (sys_left + sys_w + ACTOR_MARGIN / 2 + 10, sys_top + spc * (ai + 1))

        # Relationships
        for rel in relationships:
            if "actor" in rel and "use_case" in rel:
                ap = actor_positions.get(rel["actor"])
                up = uc_positions.get(rel["use_case"])
                if ap and up:
                    parts.append(
                        f'<line x1="{ap[0]:.1f}" y1="{ap[1]:.1f}" x2="{up[0]:.1f}" y2="{up[1]:.1f}" '
                        f'stroke="{rel_color}" stroke-width="1.5"/>'
                    )
            elif "from" in rel and "to" in rel:
                from_p = uc_positions.get(rel["from"])
                to_p = uc_positions.get(rel["to"])
                if from_p and to_p:
                    rel_type = rel.get("type", "include")
                    mid_x = (from_p[0] + to_p[0]) / 2
                    mid_y = (from_p[1] + to_p[1]) / 2
                    parts.append(
                        f'<line x1="{from_p[0]:.1f}" y1="{from_p[1]:.1f}" '
                        f'x2="{to_p[0]:.1f}" y2="{to_p[1]:.1f}" '
                        f'stroke="{rel_color}" stroke-width="1.5" stroke-dasharray="6,4" '
                        f'marker-end="url(#uc-arrow)"/>'
                    )
                    parts.append(
                        _svg_text(
                            mid_x, mid_y - 8, f"«{rel_type}»", font_size=10, fill=rel_color, font_family=font_family
                        )
                    )

        # Use cases (ellipses)
        uc_fill = self.style.get("node_fill", "#FFFFFF")
        uc_stroke = self.style.get("node_stroke", "#D1D5DB")
        for uc in use_cases:
            ucx, ucy = uc_positions[uc["id"]]
            label = uc.get("label", uc["id"])
            parts.append(
                f'<ellipse cx="{ucx:.1f}" cy="{ucy:.1f}" rx="{UC_RX}" ry="{UC_RY}" '
                f'fill="{uc_fill}" stroke="{uc_stroke}" stroke-width="1.5"/>'
            )
            uc_lines = self._wrap_label(label, 16)
            for li, ln in enumerate(uc_lines[:2]):
                parts.append(
                    _svg_text(
                        ucx,
                        ucy + (li - (len(uc_lines) - 1) / 2) * 15,
                        ln,
                        font_size=12,
                        fill=text_color,
                        font_family=font_family,
                        font_weight="500",
                    )
                )

        # Actors (stick figures)
        for actor in actors:
            ap = actor_positions.get(actor["id"])
            if not ap:
                continue
            ax, ay = ap
            label = actor.get("label", actor["id"])
            head_r = 11
            body_top = ay - head_r - 2
            # Head
            parts.append(
                f'<circle cx="{ax:.1f}" cy="{body_top:.1f}" r="{head_r}" '
                f'fill="{self.style.get("node_fill", "#F3F4F6")}" stroke="{text_color}" stroke-width="1.5"/>'
            )
            # Body
            parts.append(
                f'<line x1="{ax:.1f}" y1="{body_top + head_r:.1f}" x2="{ax:.1f}" y2="{body_top + head_r + 28:.1f}" '
                f'stroke="{text_color}" stroke-width="1.5"/>'
            )
            # Arms
            parts.append(
                f'<line x1="{ax - 17:.1f}" y1="{body_top + head_r + 10:.1f}" x2="{ax + 17:.1f}" y2="{body_top + head_r + 10:.1f}" '
                f'stroke="{text_color}" stroke-width="1.5"/>'
            )
            # Legs
            parts.append(
                f'<line x1="{ax:.1f}" y1="{body_top + head_r + 28:.1f}" x2="{ax - 13:.1f}" y2="{body_top + head_r + 50:.1f}" '
                f'stroke="{text_color}" stroke-width="1.5"/>'
            )
            parts.append(
                f'<line x1="{ax:.1f}" y1="{body_top + head_r + 28:.1f}" x2="{ax + 13:.1f}" y2="{body_top + head_r + 50:.1f}" '
                f'stroke="{text_color}" stroke-width="1.5"/>'
            )
            # Label
            parts.append(
                _svg_text(ax, ay + 46, label, font_size=12, fill=text_color, font_family=font_family, font_weight="600")
            )

        parts.append("</svg>")
        return "\n".join(parts)

    def render_sequence(self, spec: dict[str, Any]) -> str:
        """Render a sequence diagram from participants + messages spec."""
        participants = spec.get("participants", [])
        messages = spec.get("messages", [])
        title = spec.get("title", "")
        subtitle = spec.get("subtitle", "")

        font_family = self.style.get("font_family", "system-ui, -apple-system, sans-serif")
        bg_color = self.style.get("background_color", "#FFFFFF")
        text_color = self.style.get("text_color", "#1f2937")
        node_fill = self.style.get("node_fill", "#6366F1")
        node_stroke = self.style.get("node_stroke", "#D1D5DB")
        corner_radius = self.style.get("corner_radius", 8)
        flow_colors = self.style.get(
            "flow_colors",
            {
                "control": "#6366f1",
                "data": "#3b82f6",
                "read": "#10b981",
                "write": "#f59e0b",
                "feedback": "#8b5cf6",
                "async": "#ec4899",
                "embed": "#7c3aed",
                "default": "#9ca3af",
            },
        )
        arrow_color = flow_colors.get("control", "#6366f1")
        reply_color = flow_colors.get("data", "#3b82f6")
        async_color = flow_colors.get("async", "#ec4899")

        # Layout constants
        PARTICIPANT_W = 150
        PARTICIPANT_H = 54
        COL_SPACING = 200  # center-to-center
        MARGIN_X = 80
        NOTE_AREA = 180  # extra right margin when notes are present
        MSG_SPACING = 68  # vertical gap between messages

        n = len(participants)
        has_notes = any(m.get("note") for m in messages)

        # Canvas width
        total_span = max(0, n - 1) * COL_SPACING
        canvas_width = MARGIN_X * 2 + total_span + PARTICIPANT_W
        if has_notes:
            canvas_width += NOTE_AREA

        # Y positions
        title_y = 42
        title_offset = 0
        if title:
            title_offset += 28
        if subtitle:
            title_offset += 20
        participant_top = title_y + title_offset + 14

        lifeline_start_y = participant_top + PARTICIPANT_H
        msg_start_y = lifeline_start_y + 48
        lifeline_end_y = msg_start_y + len(messages) * MSG_SPACING + 40
        canvas_height = lifeline_end_y + 50

        # Participant center X positions (evenly distributed)
        if n == 1:
            p_centers = [canvas_width / 2]
        else:
            left_cx = (canvas_width - (has_notes * NOTE_AREA // 2)) / 2 - total_span / 2
            p_centers = [left_cx + i * COL_SPACING for i in range(n)]

        p_index = {p["id"]: i for i, p in enumerate(participants)}

        parts: list[str] = []
        parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {canvas_width} {canvas_height:.0f}" '
            f'width="{canvas_width}" height="{canvas_height:.0f}" '
            f'font-family="{escape(font_family)}">'
        )

        # Defs
        parts.append("<defs>")
        parts.append(
            '<filter id="seq-shadow" x="-15%" y="-15%" width="140%" height="140%">'
            '<feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#000" flood-opacity="0.10"/>'
            "</filter>"
        )
        for marker_id, color in [("seq-sync", arrow_color), ("seq-reply", reply_color), ("seq-async", async_color)]:
            parts.append(
                f'<marker id="{marker_id}" viewBox="0 0 10 6" refX="9" refY="3" '
                f'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
                f'<path d="M0,0.5 L9,3 L0,5.5 Z" fill="{color}"/>'
                f"</marker>"
            )
        parts.append("</defs>")

        # Background
        parts.append(
            f'<rect x="0" y="0" width="{canvas_width}" height="{canvas_height:.0f}" fill="{bg_color}" stroke="none"/>'
        )

        # Title + subtitle
        if title:
            title_size = self.style.get("title_size", 24)
            parts.append(
                _svg_text(
                    canvas_width / 2,
                    title_y,
                    title,
                    font_size=title_size,
                    fill=text_color,
                    font_family=font_family,
                    font_weight="700",
                )
            )
        if subtitle:
            sub_y = title_y + (28 if title else 0)
            parts.append(
                _svg_text(
                    canvas_width / 2,
                    sub_y,
                    subtitle,
                    font_size=13,
                    fill=self.style.get("subtitle_color", "#6b7280"),
                    font_family=font_family,
                )
            )

        # Participant boxes
        for i, p in enumerate(participants):
            cx = p_centers[i]
            px = cx - PARTICIPANT_W / 2
            py = participant_top
            color = p.get("color") or node_fill
            label = p.get("label", p["id"])

            # Use white text on dark backgrounds
            r, g, b = _hex_to_rgb(color)
            luma = 0.299 * r + 0.587 * g + 0.114 * b
            label_color = "#FFFFFF" if luma < 160 else text_color

            parts.append(
                f'<rect x="{px:.1f}" y="{py}" width="{PARTICIPANT_W}" height="{PARTICIPANT_H}" '
                f'rx="{corner_radius}" fill="{color}" stroke="{node_stroke}" '
                f'stroke-width="1.5" filter="url(#seq-shadow)"/>'
            )
            parts.append(
                _svg_text(
                    cx,
                    py + PARTICIPANT_H / 2,
                    label,
                    font_size=13,
                    fill=label_color,
                    font_family=font_family,
                    font_weight="700",
                )
            )

        # Lifelines
        lifeline_color = self.style.get("container_stroke", "#D1D5DB")
        for i in range(n):
            cx = p_centers[i]
            parts.append(
                _svg_line(cx, lifeline_start_y, cx, lifeline_end_y, stroke=lifeline_color, stroke_width=1.5, dash="8,5")
            )

        # Messages
        for m_idx, msg in enumerate(messages):
            from_id = msg.get("from", "")
            to_id = msg.get("to", "")
            label = msg.get("label", "")
            msg_type = msg.get("type", "sync")
            note = msg.get("note", "")

            from_i = p_index.get(from_id, -1)
            to_i = p_index.get(to_id, -1)
            if from_i < 0 or to_i < 0:
                continue

            y = msg_start_y + m_idx * MSG_SPACING
            x1 = p_centers[from_i]
            x2 = p_centers[to_i]

            # Self-message: small loop
            is_self = from_i == to_i
            is_reply = msg_type == "reply"
            is_async_msg = msg_type in ("async", "create")

            if is_reply:
                line_color = reply_color
                marker_id = "seq-reply"
                dash = "8,5"
            elif is_async_msg:
                line_color = async_color
                marker_id = "seq-async"
                dash = "6,4"
            else:
                line_color = arrow_color
                marker_id = "seq-sync"
                dash = ""

            if is_self:
                # Small right-side loop
                loop_h = 30
                lx = x1 + PARTICIPANT_W / 2
                dash_svg = f' stroke-dasharray="{dash}"' if dash else ""
                parts.append(
                    f'<path d="M{x1:.1f},{y:.1f} L{lx:.1f},{y:.1f} L{lx:.1f},{y + loop_h:.1f} L{x1:.1f},{y + loop_h:.1f}" '
                    f'stroke="{line_color}" stroke-width="1.5" fill="none"'
                    f'{dash_svg} marker-end="url(#{marker_id})"/>'
                )
                if label:
                    # Multi-line label handling
                    label_lines = [ln.strip() for ln in label.replace("\\n", "\n").split("\n")]
                    label_x = lx + 8
                    for li, ln in enumerate(label_lines[:3]):
                        parts.append(
                            _svg_text(
                                label_x,
                                y + li * 14 - 4,
                                ln,
                                font_size=11,
                                fill=text_color,
                                font_family=font_family,
                                anchor="start",
                            )
                        )
            else:
                # Horizontal arrow
                # Offset endpoints so they don't overlap the lifeline dash
                offset = 2
                ax1 = x1 + (offset if x2 > x1 else -offset)
                ax2 = x2 - (offset if x2 > x1 else -offset)

                parts.append(
                    _svg_line(ax1, y, ax2, y, stroke=line_color, stroke_width=1.5, marker_end=marker_id, dash=dash)
                )

                # Label — split on \n and render multiple lines above the arrow
                if label:
                    label_lines = [ln.strip() for ln in label.replace("\\n", "\n").split("\n")]
                    label_x = (ax1 + ax2) / 2
                    n_lines = len(label_lines)
                    # Stack lines above the arrow line
                    base_y = y - 8 - (n_lines - 1) * 14
                    for li, ln in enumerate(label_lines[:4]):
                        is_first = li == 0
                        parts.append(
                            _svg_text(
                                label_x,
                                base_y + li * 14,
                                ln,
                                font_size=11 if n_lines > 1 else 12,
                                fill=text_color,
                                font_family=font_family,
                                font_weight="600" if is_first else "normal",
                            )
                        )

            # Note box (right margin)
            if note and has_notes:
                note_x = max(p_centers) + PARTICIPANT_W / 2 + 16
                note_w = NOTE_AREA - 30
                note_fill = self.style.get("container_fill", "#FFFBEB")
                note_stroke_c = self.style.get("container_stroke", "#FCD34D")
                note_lines = [nl.strip() for nl in note.replace("\\n", "\n").split("\n")]
                note_h = max(28, 16 + len(note_lines) * 14)
                parts.append(
                    f'<rect x="{note_x:.1f}" y="{y - note_h / 2:.1f}" width="{note_w}" height="{note_h}" '
                    f'rx="4" fill="{note_fill}" stroke="{note_stroke_c}" stroke-width="1"/>'
                )
                for ni, nl in enumerate(note_lines[:3]):
                    parts.append(
                        _svg_text(
                            note_x + note_w / 2,
                            y - (len(note_lines) - 1) * 7 + ni * 14,
                            nl,
                            font_size=10,
                            fill="#374151",
                            font_family=font_family,
                        )
                    )

        # Bottom participant boxes (repeat headers for long diagrams)
        if len(messages) >= 8:
            for i, p in enumerate(participants):
                cx = p_centers[i]
                px = cx - PARTICIPANT_W / 2
                py = lifeline_end_y
                color = p.get("color") or node_fill
                label = p.get("label", p["id"])
                r, g, b = _hex_to_rgb(color)
                luma = 0.299 * r + 0.587 * g + 0.114 * b
                label_color = "#FFFFFF" if luma < 160 else text_color
                parts.append(
                    f'<rect x="{px:.1f}" y="{py:.1f}" width="{PARTICIPANT_W}" height="{PARTICIPANT_H}" '
                    f'rx="{corner_radius}" fill="{color}" stroke="{node_stroke}" stroke-width="1.5"/>'
                )
                parts.append(
                    _svg_text(
                        cx,
                        py + PARTICIPANT_H / 2,
                        label,
                        font_size=13,
                        fill=label_color,
                        font_family=font_family,
                        font_weight="700",
                    )
                )

        parts.append("</svg>")
        return "\n".join(parts)

    def _auto_ports(self, src: Rect, tgt: Rect) -> tuple[str, str]:
        """Auto-detect best connection ports based on relative position.

        For tiered/layered architecture diagrams, cross-tier arrows (significant dy)
        always use vertical ports so the flow reads top-to-bottom.
        Same-tier horizontal connections use left/right ports.
        """
        dx = tgt.cx - src.cx
        dy = tgt.cy - src.cy

        # Cross-tier: target is meaningfully below or above → always vertical
        if dy > 60:
            return "bottom", "top"
        if dy < -60:
            return "top", "bottom"

        # Same-tier: prefer horizontal when wider than tall offset
        if abs(dx) > abs(dy):
            return ("right", "left") if dx > 0 else ("left", "right")
        else:
            return ("bottom", "top") if dy > 0 else ("top", "bottom")

    def _route_edge(self, p1: Point, p2: Point, src_port: str, tgt_port: str) -> str:
        """Generate orthogonal path between two points."""
        if src_port in ("top", "bottom"):
            mid_y = (p1.y + p2.y) / 2
            return f"M{p1.x},{p1.y} L{p1.x},{mid_y} L{p2.x},{mid_y} L{p2.x},{p2.y}"
        else:
            mid_x = (p1.x + p2.x) / 2
            return f"M{p1.x},{p1.y} L{mid_x},{p1.y} L{mid_x},{p2.y} L{p2.x},{p2.y}"

    def _route_bezier(self, p1: Point, p2: Point, src_port: str, tgt_port: str) -> str:
        """Generate smooth cubic bezier path between two points."""
        dx = abs(p2.x - p1.x)
        dy = abs(p2.y - p1.y)
        tension = max(60, min(dx, dy) * 0.6)

        if src_port == "bottom":
            c1x, c1y = p1.x, p1.y + tension
        elif src_port == "top":
            c1x, c1y = p1.x, p1.y - tension
        elif src_port == "right":
            c1x, c1y = p1.x + tension, p1.y
        else:
            c1x, c1y = p1.x - tension, p1.y

        if tgt_port == "top":
            c2x, c2y = p2.x, p2.y - tension
        elif tgt_port == "bottom":
            c2x, c2y = p2.x, p2.y + tension
        elif tgt_port == "left":
            c2x, c2y = p2.x - tension, p2.y
        else:
            c2x, c2y = p2.x + tension, p2.y

        return f"M{p1.x:.1f},{p1.y:.1f} C{c1x:.1f},{c1y:.1f} {c2x:.1f},{c2y:.1f} {p2.x:.1f},{p2.y:.1f}"

    @staticmethod
    def _wrap_label(label: str, max_chars: int = 20) -> list[str]:
        """Wrap a long label into multiple lines."""
        if len(label) <= max_chars:
            return [label]
        words = label.split()
        lines: list[str] = []
        current = ""
        for word in words:
            if not current:
                current = word
            elif len(current) + 1 + len(word) <= max_chars:
                current += " " + word
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [label]

    def _render_node_shape(
        self,
        kind: str,
        rect: Rect,
        fill: str,
        stroke: str,
        stroke_width: float,
        corner_radius: float,
        has_shadow: bool,
    ) -> str:
        """Render a node shape based on its kind with professional styling."""
        filter_attr = ' filter="url(#shadow)"' if has_shadow else ""
        rx = 12  # consistent modern radius

        if kind in ("rect", "rounded_rect", "double_rect"):
            r = 0 if kind == "rect" else rx
            outer = (
                f'<rect x="{rect.x}" y="{rect.y}" width="{rect.width}" height="{rect.height}" '
                f'rx="{r}" fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{stroke_width}"{filter_attr}/>'
            )
            if kind == "double_rect":
                inset = 5
                inner = (
                    f'<rect x="{rect.x + inset}" y="{rect.y + inset}" '
                    f'width="{rect.width - inset * 2}" height="{rect.height - inset * 2}" '
                    f'rx="{max(r - 3, 0)}" fill="none" stroke="{stroke}" '
                    f'stroke-width="1.2"/>'
                )
                return outer + "\n" + inner
            return outer

        elif kind == "hexagon":
            cx, cy = rect.cx, rect.cy
            indent = rect.width * 0.18
            points = (
                f"{rect.x + indent:.1f},{rect.y} {rect.x + rect.width - indent:.1f},{rect.y} "
                f"{rect.x + rect.width},{cy:.1f} {rect.x + rect.width - indent:.1f},{rect.y + rect.height} "
                f"{rect.x + indent:.1f},{rect.y + rect.height} {rect.x},{cy:.1f}"
            )
            return (
                f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{stroke_width}"{filter_attr}/>'
            )

        elif kind == "cylinder":
            ry = max(10, int(rect.height * 0.15))
            body_y = rect.y + ry
            body_h = rect.height - ry * 2
            # Shadow base
            svg = (
                f'<rect x="{rect.x}" y="{body_y}" width="{rect.width}" height="{body_h + ry}" '
                f'fill="{fill}" stroke="none"{filter_attr}/>'
            )
            # Body
            svg += (
                f'\n<rect x="{rect.x}" y="{body_y}" width="{rect.width}" height="{body_h}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" stroke-left="true"/>'
            )
            # Top ellipse (lid)
            svg += (
                f'\n<ellipse cx="{rect.cx}" cy="{rect.y + ry}" rx="{rect.width / 2}" ry="{ry}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
            )
            # Bottom ellipse
            svg += (
                f'\n<ellipse cx="{rect.cx}" cy="{rect.y + rect.height - ry}" '
                f'rx="{rect.width / 2}" ry="{ry}" fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{stroke_width}"/>'
            )
            # Side lines
            svg += (
                f'\n<line x1="{rect.x}" y1="{body_y}" x2="{rect.x}" '
                f'y2="{rect.y + rect.height - ry}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
                f'\n<line x1="{rect.x + rect.width}" y1="{body_y}" '
                f'x2="{rect.x + rect.width}" y2="{rect.y + rect.height - ry}" '
                f'stroke="{stroke}" stroke-width="{stroke_width}"/>'
            )
            # Cover inner artifact
            svg += (
                f'\n<rect x="{rect.x + stroke_width}" y="{body_y}" '
                f'width="{rect.width - stroke_width * 2}" height="{body_h - 1}" '
                f'fill="{fill}" stroke="none"/>'
            )
            return svg

        elif kind == "diamond":
            cx, cy = rect.cx, rect.cy
            # Slightly wider diamond for readability
            hw = rect.width * 0.55
            hh = rect.height * 0.55
            points = f"{cx:.1f},{cy - hh:.1f} {cx + hw:.1f},{cy:.1f} {cx:.1f},{cy + hh:.1f} {cx - hw:.1f},{cy:.1f}"
            return (
                f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{stroke_width}"{filter_attr}/>'
            )

        elif kind == "circle":
            r = min(rect.width, rect.height) / 2
            return (
                f'<circle cx="{rect.cx}" cy="{rect.cy}" r="{r}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{filter_attr}/>'
            )

        elif kind == "gear":
            # Gear shape rendered as a circle with notches
            r = min(rect.width, rect.height) / 2 - 2
            teeth = 8
            inner_r = r * 0.7
            outer_r = r
            cx, cy = rect.cx, rect.cy
            d: list[str] = []
            for i in range(teeth * 2):
                angle = (i * math.pi) / teeth
                radius = outer_r if i % 2 == 0 else inner_r
                px = cx + radius * math.cos(angle - math.pi / 2)
                py = cy + radius * math.sin(angle - math.pi / 2)
                cmd = "M" if i == 0 else "L"
                d.append(f"{cmd}{px:.1f},{py:.1f}")
            d.append("Z")
            path = " ".join(d)
            return f'<path d="{path}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{filter_attr}/>'

        elif kind == "document":
            x, y, w, h = rect.x, rect.y, rect.width, rect.height
            wave = h * 0.1
            d = (
                f"M{x},{y} L{x + w},{y} L{x + w},{y + h - wave} "
                f"Q{x + w * 0.75},{y + h + wave} {x + w * 0.5},{y + h - wave} "
                f"Q{x + w * 0.25},{y + h - wave * 3} {x},{y + h - wave} Z"
            )
            return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{filter_attr}/>'

        elif kind == "folder":
            x, y, w, h = rect.x, rect.y, rect.width, rect.height
            tab_w = w * 0.35
            tab_h = h * 0.15
            d = (
                f"M{x},{y + tab_h} L{x},{y} L{x + tab_w},{y} "
                f"L{x + tab_w + 10},{y + tab_h} L{x + w},{y + tab_h} "
                f"L{x + w},{y + h} L{x},{y + h} Z"
            )
            return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{filter_attr}/>'

        elif kind == "terminal":
            r = rect.height / 2
            return (
                f'<rect x="{rect.x}" y="{rect.y}" width="{rect.width}" height="{rect.height}" '
                f'rx="{r}" fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{stroke_width}"{filter_attr}/>'
            )

        elif kind == "speech":
            x, y, w, h = rect.x, rect.y, rect.width, rect.height
            tail = h * 0.2
            body_h = h - tail
            d = (
                f"M{x + corner_radius},{y} L{x + w - corner_radius},{y} "
                f"Q{x + w},{y} {x + w},{y + corner_radius} "
                f"L{x + w},{y + body_h - corner_radius} "
                f"Q{x + w},{y + body_h} {x + w - corner_radius},{y + body_h} "
                f"L{x + w * 0.3},{y + body_h} L{x + w * 0.15},{y + h} "
                f"L{x + w * 0.2},{y + body_h} L{x + corner_radius},{y + body_h} "
                f"Q{x},{y + body_h} {x},{y + body_h - corner_radius} "
                f"L{x},{y + corner_radius} Q{x},{y} {x + corner_radius},{y} Z"
            )
            return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{filter_attr}/>'

        elif kind == "parallelogram":
            # Slanted rect — used for I/O steps in flowcharts, data artifacts
            skew = rect.width * 0.15
            d = (
                f"M{rect.x + skew:.1f},{rect.y:.1f} "
                f"L{rect.x + rect.width:.1f},{rect.y:.1f} "
                f"L{rect.x + rect.width - skew:.1f},{rect.y + rect.height:.1f} "
                f"L{rect.x:.1f},{rect.y + rect.height:.1f} Z"
            )
            return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{filter_attr}/>'

        # Default fallback: rounded rect
        return (
            f'<rect x="{rect.x}" y="{rect.y}" width="{rect.width}" height="{rect.height}" '
            f'rx="{corner_radius}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{stroke_width}"{filter_attr}/>'
        )

    def _render_legend(
        self,
        legend: list[dict],
        position: str,
        width: float,
        height: float,
        flow_colors: dict,
        font_family: str,
        text_color: str,
    ) -> str:
        """Render flow type legend."""
        if not legend:
            return ""

        legend_bg = self.style.get("legend_bg", "#ffffff")
        legend_border = self.style.get("legend_border", "#e5e7eb")
        entry_height = 20
        padding = 12
        legend_w = 180
        legend_h = len(legend) * entry_height + padding * 2 + 20  # +20 for title

        # Position
        if "right" in position:
            lx = width - legend_w - 20
        else:
            lx = 20
        if "bottom" in position:
            ly = height - legend_h - 20
        else:
            ly = 20

        parts: list[str] = []
        parts.append(_svg_rect(lx, ly, legend_w, legend_h, rx=8, fill=legend_bg, stroke=legend_border, opacity=0.95))
        parts.append(
            _svg_text(
                lx + padding,
                ly + padding + 6,
                "Legend",
                font_size=12,
                fill=text_color,
                font_family=font_family,
                font_weight="600",
                anchor="start",
            )
        )

        for i, entry in enumerate(legend):
            ey = ly + padding + 26 + i * entry_height
            flow = entry.get("flow", "default")
            color = flow_colors.get(flow, flow_colors.get("default", "#9ca3af"))
            label = entry.get("label", flow)

            # Color line
            parts.append(
                f'<line x1="{lx + padding}" y1="{ey}" '
                f'x2="{lx + padding + 24}" y2="{ey}" '
                f'stroke="{color}" stroke-width="2"/>'
            )
            # Arrow head
            parts.append(
                f'<polygon points="{lx + padding + 20},{ey - 3} '
                f'{lx + padding + 26},{ey} {lx + padding + 20},{ey + 3}" '
                f'fill="{color}"/>'
            )
            # Label
            parts.append(
                _svg_text(
                    lx + padding + 32,
                    ey,
                    label,
                    font_size=11,
                    fill=text_color,
                    font_family=font_family,
                    anchor="start",
                )
            )

        return "\n".join(parts)
