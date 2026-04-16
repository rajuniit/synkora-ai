"""
Style profiles for the Synkora diagram engine.

Each style is a complete visual theme controlling colors, typography,
spacing, and flow-arrow palettes for rendered diagrams.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1 - Flat Icon
# ---------------------------------------------------------------------------
_FLAT_ICON: dict = {
    "background_color": "#FFFFFF",
    "node_fill": "#F5F5F5",
    "node_stroke": "#E0E0E0",
    "text_color": "#333333",
    "text_size": 13,
    "type_label_color": "#888888",
    "type_label_size": 10,
    "title_size": 18,
    "subtitle_color": "#999999",
    "container_fill": "#FAFAFA",
    "container_stroke": "#DDDDDD",
    "container_label_color": "#666666",
    "label_color": "#555555",
    "flow_colors": {
        "control": "#4A90D9",
        "data": "#50C878",
        "read": "#F5A623",
        "write": "#D0021B",
        "feedback": "#9B59B6",
        "async": "#95A5A6",
        "embed": "#7C3AED",
        "default": "#7F8C8D",
    },
    "use_node_gradients": False,
    "shadow_blur": 4,
    "corner_radius": 8,
    "font_family": "'Helvetica Neue', Helvetica, Arial, sans-serif",
    "border_width": 1.5,
    "legend_bg": "#FFFFFF",
    "legend_border": "#E0E0E0",
}

# ---------------------------------------------------------------------------
# 2 - Dark Terminal
# ---------------------------------------------------------------------------
_DARK_TERMINAL: dict = {
    "background_color": "#0F0F1A",
    "node_fill": "#1A1A2E",
    "node_stroke": "#2D2D44",
    "text_color": "#E0E0E0",
    "text_size": 13,
    "type_label_color": "#7F7FAA",
    "type_label_size": 10,
    "title_size": 18,
    "subtitle_color": "#6A6A8E",
    "container_fill": "#141425",
    "container_stroke": "#2A2A40",
    "container_label_color": "#9090BB",
    "label_color": "#B0B0CC",
    "flow_colors": {
        "control": "#00FF88",
        "data": "#00D4FF",
        "read": "#FFD700",
        "write": "#FF4466",
        "feedback": "#BF5FFF",
        "async": "#FF8800",
        "embed": "#BF5FFF",
        "default": "#66FFCC",
    },
    "shadow_blur": 8,
    "corner_radius": 4,
    "font_family": "'Fira Code', 'Cascadia Code', 'JetBrains Mono', monospace",
    "border_width": 1,
    "legend_bg": "#1A1A2E",
    "legend_border": "#2D2D44",
}

# ---------------------------------------------------------------------------
# 3 - Blueprint
# ---------------------------------------------------------------------------
_BLUEPRINT: dict = {
    "background_color": "#0A1628",
    "node_fill": "#0E1F3D",
    "node_stroke": "#1B3A65",
    "text_color": "#C8D8E8",
    "text_size": 12,
    "type_label_color": "#5A7EA0",
    "type_label_size": 10,
    "title_size": 18,
    "subtitle_color": "#4A6E90",
    "container_fill": "#0C1A30",
    "container_stroke": "#1A3050",
    "container_label_color": "#6B9AC4",
    "label_color": "#8BB4D8",
    "flow_colors": {
        "control": "#4DC9F6",
        "data": "#00E5FF",
        "read": "#80D8FF",
        "write": "#FF6E40",
        "feedback": "#B388FF",
        "async": "#A7FFEB",
        "embed": "#CE93D8",
        "default": "#4FC3F7",
    },
    "shadow_blur": 0,
    "corner_radius": 2,
    "font_family": "'Courier New', Courier, monospace",
    "border_width": 1,
    "legend_bg": "#0E1F3D",
    "legend_border": "#1B3A65",
}

# ---------------------------------------------------------------------------
# 4 - Notion Clean  (DEFAULT)
# ---------------------------------------------------------------------------
_NOTION_CLEAN: dict = {
    "background_color": "#FFFFFF",
    "node_fill": "#FFFFFF",
    "node_stroke": "#E3E3E3",
    "text_color": "#37352F",
    "text_size": 14,
    "type_label_color": "#9B9A97",
    "type_label_size": 11,
    "title_size": 20,
    "subtitle_color": "#9B9A97",
    "container_fill": "#F7F6F3",
    "container_stroke": "#E3E3E3",
    "container_label_color": "#787774",
    "label_color": "#37352F",
    "flow_colors": {
        "control": "#2EAADC",
        "data": "#0F7B6C",
        "read": "#D9730D",
        "write": "#E03E3E",
        "feedback": "#6940A5",
        "async": "#9B9A97",
        "embed": "#6940A5",
        "default": "#787774",
    },
    "use_node_gradients": False,
    "shadow_blur": 2,
    "corner_radius": 6,
    "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, sans-serif",
    "border_width": 1,
    "legend_bg": "#FFFFFF",
    "legend_border": "#E3E3E3",
}

# ---------------------------------------------------------------------------
# 5 - Glassmorphism
# ---------------------------------------------------------------------------
_GLASSMORPHISM: dict = {
    "background_color": "#1A1A2E",
    "node_fill": "rgba(255,255,255,0.08)",
    "node_stroke": "rgba(255,255,255,0.18)",
    "text_color": "#EEEEFF",
    "text_size": 13,
    "type_label_color": "rgba(255,255,255,0.5)",
    "type_label_size": 10,
    "title_size": 20,
    "subtitle_color": "rgba(255,255,255,0.4)",
    "container_fill": "rgba(255,255,255,0.04)",
    "container_stroke": "rgba(255,255,255,0.12)",
    "container_label_color": "rgba(255,255,255,0.6)",
    "label_color": "rgba(255,255,255,0.7)",
    "flow_colors": {
        "control": "#6C63FF",
        "data": "#00D9FF",
        "read": "#FFAB40",
        "write": "#FF5252",
        "feedback": "#E040FB",
        "async": "#69F0AE",
        "embed": "#EA80FC",
        "default": "#B0BEC5",
    },
    "shadow_blur": 16,
    "corner_radius": 16,
    "font_family": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    "border_width": 1,
    "legend_bg": "rgba(255,255,255,0.06)",
    "legend_border": "rgba(255,255,255,0.15)",
}

# ---------------------------------------------------------------------------
# 6 - Claude Official
# ---------------------------------------------------------------------------
_CLAUDE_OFFICIAL: dict = {
    "background_color": "#F8F6F3",
    "node_fill": "#FFFFFF",
    "node_stroke": "#C8BFAF",
    "text_color": "#1A1612",
    "text_size": 14,
    "type_label_color": "#9C8E7E",
    "type_label_size": 10,
    "title_size": 22,
    "subtitle_color": "#9C8E7E",
    "container_fill": "rgba(0,0,0,0)",
    "container_stroke": "#C8BFAF",
    "container_stroke_dash": "5,4",
    "container_label_color": "#7A6C5D",
    "container_label_size": 12,
    "container_label_weight": "500",
    "container_label_uppercase": False,
    "label_color": "#5C4F42",
    "use_node_gradients": False,
    "flow_colors": {
        "control": "#A0522D",
        "data": "#8B6914",
        "read": "#2E7D52",
        "write": "#C0392B",
        "feedback": "#7C3AED",
        "async": "#A0522D",
        "embed": "#7C3AED",
        "default": "#8C7E6E",
    },
    "shadow_blur": 2,
    "corner_radius": 8,
    "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif",
    "border_width": 1.5,
    "legend_bg": "#FFFFFF",
    "legend_border": "#DDD5C8",
}

# ---------------------------------------------------------------------------
# 7 - OpenAI Official
# ---------------------------------------------------------------------------
_OPENAI_OFFICIAL: dict = {
    "background_color": "#FFFFFF",
    "node_fill": "#FFFFFF",
    "node_stroke": "#D9D9E3",
    "text_color": "#202123",
    "text_size": 14,
    "type_label_color": "#8E8EA0",
    "type_label_size": 10,
    "title_size": 22,
    "subtitle_color": "#8E8EA0",
    "container_fill": "#FAFAFA",
    "container_stroke": "#C8C8D4",
    "container_stroke_dash": "6,4",
    "container_label_color": "#10A37F",
    "container_label_size": 11,
    "container_label_weight": "700",
    "container_label_uppercase": True,
    "label_color": "#353740",
    "use_node_gradients": False,
    "flow_colors": {
        "control": "#10A37F",
        "data": "#10A37F",
        "read": "#F59E0B",
        "write": "#EF4444",
        "feedback": "#4A90D9",
        "async": "#9CA3AF",
        "embed": "#7C3AED",
        "default": "#6B7280",
    },
    "shadow_blur": 3,
    "corner_radius": 10,
    "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif",
    "border_width": 1.5,
    "legend_bg": "#FFFFFF",
    "legend_border": "#D9D9E3",
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

STYLES: dict[int, dict] = {
    1: _FLAT_ICON,
    2: _DARK_TERMINAL,
    3: _BLUEPRINT,
    4: _NOTION_CLEAN,
    5: _GLASSMORPHISM,
    6: _CLAUDE_OFFICIAL,
    7: _OPENAI_OFFICIAL,
}

DEFAULT_STYLE_ID = 4


def get_style(style_id: int) -> dict:
    """Return the style profile for the given ID.

    Falls back to the default Notion Clean style (4) when the requested
    style ID is not recognised.
    """
    return STYLES.get(style_id, STYLES[DEFAULT_STYLE_ID])
