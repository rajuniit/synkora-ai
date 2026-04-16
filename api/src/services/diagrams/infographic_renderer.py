"""
Infographic Renderer — modern, bold, data-driven SVG reports.

Theming is fully open. Pass:
  - A preset name string:   "aurora" | "midnight" | "carbon" | "sunset" | "emerald"
  - A full custom dict:     {"bg": "#fff", "palette": ["#f00", "#0f0"], ...}
  - A partial override:     {"preset": "midnight", "palette": ["#custom1", "#custom2"]}

All keys are optional — missing ones fall back to the "aurora" defaults.

Input schema
------------
{
  "title":    str,
  "subtitle": str,           # optional
  "date":     str,           # optional — pill badge in header
  "theme":    str | dict,    # see above
  "width":    int,           # optional, default 900
  "sections": [
    {"type": "kpi_row",         "items": [{"label", "value", "change"?, "trend"?: "up"|"down"}]},
    {"type": "bar_chart",       "title": str, "data": [{"label", "value", "color"?}]},
    {"type": "donut",           "title": str, "data": [{"label", "value", "color"?}]},
    {"type": "stories",         "title": str, "items": [{"headline", "body", "channel"?, "author"?}]},
    {"type": "heatmap",         "title": str, "data": [[24 ints] x 7], "row_labels"?: [str x 7]},
    {"type": "divider",         "label"?: str},
    {"type": "text",            "content": str},
    # AntV-parity section types:
    {"type": "process_flow",    "title"?: str, "items": [{"title", "body"?}]},
    {"type": "circular_flow",   "title"?: str, "items": [{"title", "body"?}]},
    {"type": "staircase",       "title"?: str, "items": [{"label", "value"?}]},
    {"type": "pyramid",         "title"?: str, "items": [{"label", "body"?}]},
    {"type": "snake_path",      "title"?: str, "items": [{"label"}]},
    {"type": "bubble_chain",    "title"?: str, "items": [{"label", "value"}]},
    {"type": "timeline",        "title"?: str, "items": [{"label", "date"?, "body"?}]},
    {"type": "venn",            "title"?: str, "items": [{"label", "items"?: [str]}], "center_label"?: str},
    {"type": "comparison",      "title"?: str, "left": {"label", "items": [str]}, "right": {"label", "items": [str]}},
    {"type": "swot",            "title"?: str, "quadrants": [{"label", "items": [str]}]},
    {"type": "matrix_2x2",      "title"?: str, "cells": [{"label", "body"}], "x_label"?: str, "y_label"?: str},
    {"type": "quadrant_circle", "title"?: str, "quadrants": [{"label", "value"?}], "center_label"?: str},
    {"type": "card_grid",       "title"?: str, "items": [{"title", "body"}], "cols"?: int},
    {"type": "pill_list",       "title"?: str, "items": [{"label", "sub"?}]},
    {"type": "wheel",           "title"?: str, "data": [{"label", "value"?, "color"?}], "equal"?: bool, "center_label"?: str},
  ]
}
"""

from __future__ import annotations

import math
from xml.sax.saxutils import escape as _xml_escape

# ---------------------------------------------------------------------------
# Theme presets
# ---------------------------------------------------------------------------

_BASE: dict = {
    "bg":           "#08070E",
    "header_from":  "#1A0533",
    "header_to":    "#0F0A1E",
    "card_bg":      "#100E1A",
    "card_border":  "#2D2550",
    "text":         "#F2EFFF",
    "muted":        "#6E6A85",
    "palette":      ["#8B5CF6", "#06B6D4", "#10B981", "#F59E0B", "#EF4444", "#EC4899"],
    "trend_up":     "#10B981",
    "trend_down":   "#EF4444",
    "font":         "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    "radius":       14,
    "bar_h":        28,
}

PRESETS: dict[str, dict] = {
    "aurora": {
        **_BASE,
        # deep violet/purple with cyan and green
    },
    "midnight": {
        **_BASE,
        "bg":          "#050912",
        "header_from": "#081830",
        "header_to":   "#050912",
        "card_bg":     "#0C1525",
        "card_border": "#172B4A",
        "text":        "#E5F0FF",
        "muted":       "#4E6A8C",
        "palette":     ["#06B6D4", "#3B82F6", "#8B5CF6", "#10B981", "#F59E0B", "#EF4444"],
        "trend_up":    "#10B981",
        "trend_down":  "#EF4444",
    },
    "carbon": {
        **_BASE,
        "bg":          "#0B0B0D",
        "header_from": "#1C1C22",
        "header_to":   "#0B0B0D",
        "card_bg":     "#131316",
        "card_border": "#26262E",
        "text":        "#F5F5F7",
        "muted":       "#68687A",
        "palette":     ["#F97316", "#3B82F6", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6"],
        "trend_up":    "#10B981",
        "trend_down":  "#EF4444",
    },
    "sunset": {
        **_BASE,
        "bg":          "#0F0A06",
        "header_from": "#2C1206",
        "header_to":   "#0F0A06",
        "card_bg":     "#1C1008",
        "card_border": "#3A2016",
        "text":        "#FFF0E8",
        "muted":       "#8A6A58",
        "palette":     ["#F97316", "#EF4444", "#F59E0B", "#EC4899", "#8B5CF6", "#06B6D4"],
        "trend_up":    "#F59E0B",
        "trend_down":  "#EF4444",
    },
    "emerald": {
        **_BASE,
        "bg":          "#050F09",
        "header_from": "#091E12",
        "header_to":   "#050F09",
        "card_bg":     "#0A1810",
        "card_border": "#163024",
        "text":        "#E8FFF4",
        "muted":       "#4A7A60",
        "palette":     ["#10B981", "#06B6D4", "#3B82F6", "#84CC16", "#8B5CF6", "#F59E0B"],
        "trend_up":    "#10B981",
        "trend_down":  "#EF4444",
    },
}

DEFAULT_PRESET = "aurora"

# Layout constants
_PAD_H = 32
_PAD_V = 28
_GAP   = 14
_SEC_GAP = 36


def resolve_theme(theme_input: str | dict | None) -> dict:
    """
    Resolve theme input to a complete theme dict.

    Accepts:
    - str: preset name  →  use that preset
    - dict with "preset" key  →  start from preset, override with remaining keys
    - dict without "preset"   →  start from default preset, override with provided keys
    - None / unknown           →  return default preset
    """
    base = {**PRESETS[DEFAULT_PRESET]}

    if isinstance(theme_input, str):
        preset = PRESETS.get(theme_input, PRESETS[DEFAULT_PRESET])
        return {**base, **preset}

    if isinstance(theme_input, dict):
        preset_name = theme_input.get("preset", DEFAULT_PRESET)
        preset = PRESETS.get(preset_name, PRESETS[DEFAULT_PRESET])
        merged = {**base, **preset}
        overrides = {k: v for k, v in theme_input.items() if k != "preset"}
        merged.update(overrides)
        return merged

    return base


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _lighten(color: str, factor: float = 0.35) -> str:
    """Mix a #RRGGBB color toward white. Returns original on parse failure."""
    try:
        h = color.lstrip("#")
        if len(h) != 6:
            return color
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return color


def _alpha(color: str, opacity: float) -> str:
    """Return an rgba(...) string from a hex color and opacity."""
    try:
        h = color.lstrip("#")
        if len(h) != 6:
            return color
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{opacity:.2f})"
    except Exception:
        return color


# ---------------------------------------------------------------------------
# SVG primitive helpers
# ---------------------------------------------------------------------------

def _e(s: object) -> str:
    return _xml_escape(str(s))


def _attrs(**kw: object) -> str:
    parts = []
    for k, v in kw.items():
        if v is None:
            continue
        # Attribute values sit inside "…" — escape & < > and "
        safe = _xml_escape(str(v), {'"': "&quot;"})
        parts.append(f'{k.replace("_", "-")}="{safe}"')
    return " ".join(parts)


def _rect(x: float, y: float, w: float, h: float, rx: float = 0, **kw: object) -> str:
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx:.1f}" {_attrs(**kw)}/>'


def _text(x: float, y: float, content: str, **kw: object) -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" {_attrs(**kw)}>{_e(content)}</text>'


def _line(x1: float, y1: float, x2: float, y2: float, **kw: object) -> str:
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {_attrs(**kw)}/>'


def _path(d: str, **kw: object) -> str:
    return f'<path d="{d}" {_attrs(**kw)}/>'


def _circle(cx: float, cy: float, r: float, **kw: object) -> str:
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" {_attrs(**kw)}/>'


def _wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


# ---------------------------------------------------------------------------
# Donut arc math
# ---------------------------------------------------------------------------

def _donut_segment(
    cx: float, cy: float,
    r_out: float, r_in: float,
    start_deg: float, end_deg: float,
) -> str:
    s = math.radians(start_deg - 90)
    e = math.radians(end_deg - 90)
    ox1, oy1 = cx + r_out * math.cos(s), cy + r_out * math.sin(s)
    ox2, oy2 = cx + r_out * math.cos(e), cy + r_out * math.sin(e)
    ix1, iy1 = cx + r_in * math.cos(e), cy + r_in * math.sin(e)
    ix2, iy2 = cx + r_in * math.cos(s), cy + r_in * math.sin(s)
    large = 1 if (end_deg - start_deg) > 180 else 0
    return (
        f"M {ox1:.2f} {oy1:.2f} "
        f"A {r_out} {r_out} 0 {large} 1 {ox2:.2f} {oy2:.2f} "
        f"L {ix1:.2f} {iy1:.2f} "
        f"A {r_in} {r_in} 0 {large} 0 {ix2:.2f} {iy2:.2f} Z"
    )


# ---------------------------------------------------------------------------
# Global SVG defs (gradients, filters, patterns) — generated once per render
# ---------------------------------------------------------------------------

def _build_defs(t: dict, width: int) -> str:
    palette = t["palette"]
    r = t.get("radius", 14)
    parts: list[str] = ["<defs>"]

    # Header gradient
    parts.append(
        f'<linearGradient id="g_hdr" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0%" stop-color="{t["header_from"]}"/>'
        f'<stop offset="100%" stop-color="{t["header_to"]}"/>'
        f'</linearGradient>'
    )

    # Dot pattern — subtle texture for header
    parts.append(
        '<pattern id="g_dots" x="0" y="0" width="22" height="22" patternUnits="userSpaceOnUse">'
        '<circle cx="1.5" cy="1.5" r="1" fill="rgba(255,255,255,0.035)"/>'
        '</pattern>'
    )

    # Card shadow filter
    parts.append(
        '<filter id="g_shadow" x="-4%" y="-4%" width="108%" height="120%">'
        '<feDropShadow dx="0" dy="3" stdDeviation="7" flood-color="#000000" flood-opacity="0.45"/>'
        '</filter>'
    )

    # Bar gradient per palette slot (left = full colour, right = lightened)
    for i, color in enumerate(palette[:8]):
        light = _lighten(color, 0.28)
        parts.append(
            f'<linearGradient id="g_bar_{i}" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0%" stop-color="{color}"/>'
            f'<stop offset="100%" stop-color="{light}"/>'
            f'</linearGradient>'
        )

    # Heatmap cell gradient (vertical, adds depth)
    parts.append(
        f'<linearGradient id="g_cell" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{palette[0]}"/>'
        f'<stop offset="100%" stop-color="{_lighten(palette[0], 0.2)}"/>'
        f'</linearGradient>'
    )

    parts.append("</defs>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Component renderers — each returns (svg_fragment: str, height: float)
# ---------------------------------------------------------------------------

def _render_header(spec: dict, width: int, t: dict) -> tuple[str, float]:
    h      = 148.0
    title  = spec.get("title", "Report")
    sub    = spec.get("subtitle", "")
    date   = spec.get("date", "")
    r      = t.get("radius", 14)
    color0 = t["palette"][0]

    parts: list[str] = [
        # Gradient background
        _rect(0, 0, width, h, rx=0, fill="url(#g_hdr)"),
        # Dot texture overlay
        _rect(0, 0, width, h, rx=0, fill="url(#g_dots)"),
        # Left accent stripe — gradient
        f'<rect x="0" y="0" width="5" height="{h:.0f}" '
        f'fill="{color0}"/>',
        # Decorative circle — top right
        f'<circle cx="{width - 40:.0f}" cy="30" r="80" '
        f'fill="{color0}" opacity="0.04"/>',
        f'<circle cx="{width - 40:.0f}" cy="30" r="55" '
        f'fill="{color0}" opacity="0.04"/>',
        # Title
        _text(_PAD_H + 20, 65, title,
              fill=t["text"], font_size="32", font_weight="800",
              font_family=t["font"], letter_spacing="-0.5"),
    ]

    if sub:
        parts.append(
            _text(_PAD_H + 20, 91, sub,
                  fill=t["muted"], font_size="14", font_weight="400",
                  font_family=t["font"])
        )

    if date:
        badge_w = len(date) * 7.8 + 24
        bx = width - _PAD_H - badge_w
        parts += [
            _rect(bx, 22, badge_w, 26, rx=13,
                  fill=color0, opacity="0.18"),
            _rect(bx, 22, badge_w, 26, rx=13,
                  fill="none", stroke=color0, stroke_width="1", opacity="0.4"),
            _text(bx + badge_w / 2, 39, date,
                  fill=color0, font_size="11", font_weight="700",
                  font_family=t["font"], text_anchor="middle",
                  letter_spacing="0.4"),
        ]

    # Bottom rule
    parts.append(
        _line(0, h - 1, width, h - 1,
              stroke=color0, stroke_width="1", opacity="0.25")
    )

    return "\n".join(parts), h


def _section_title(label: str, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    h      = 42.0
    color0 = t["palette"][0]
    parts  = [
        # Left accent pip
        _rect(x, y + 5, 3, 22, rx=1.5, fill=color0),
        _text(x + 14, y + 22, label.upper(),
              fill=t["muted"], font_size="11", font_weight="700",
              letter_spacing="2", font_family=t["font"]),
        _line(x, y + h - 2, x + width, y + h - 2,
              stroke=t["card_border"], stroke_width="1"),
    ]
    return "\n".join(parts), h


def _render_kpi_row(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    items  = section.get("items", [])
    n      = max(len(items), 1)
    card_w = (width - _GAP * (n - 1)) / n
    card_h = 116.0
    r      = t.get("radius", 14)
    parts: list[str] = []

    for i, item in enumerate(items):
        cx     = x + i * (card_w + _GAP)
        label  = item.get("label", "")
        value  = str(item.get("value", "—"))
        change = item.get("change", "")
        trend  = item.get("trend", "")
        color  = t["palette"][i % len(t["palette"])]

        # Shadow + base card
        parts += [
            _rect(cx, y, card_w, card_h, rx=r,
                  fill=t["card_bg"], filter="url(#g_shadow)"),
            # Subtle colour wash — top half only, fades
            _rect(cx, y, card_w, card_h * 0.55, rx=r,
                  fill=color, opacity="0.07"),
            # Mask bottom of wash with a card-coloured rect
            _rect(cx, y + card_h * 0.4, card_w, card_h * 0.2,
                  fill=t["card_bg"], opacity="0.85"),
            # Card border in accent colour
            _rect(cx, y, card_w, card_h, rx=r,
                  fill="none", stroke=color, stroke_width="1", opacity="0.35"),
            # Top accent bar
            _rect(cx + r, y, card_w - r * 2, 3, rx=1.5, fill=color),
        ]

        # Big value — in accent colour, bold
        parts.append(
            _text(cx + 20, y + 62, value,
                  fill=color, font_size="38", font_weight="800",
                  font_family=t["font"])
        )
        # Label
        parts.append(
            _text(cx + 20, y + 84, label,
                  fill=t["muted"], font_size="11", font_weight="500",
                  font_family=t["font"], letter_spacing="0.3")
        )

        # Change badge — pill in top-right corner
        if change:
            trend_color = (
                t["trend_up"]   if trend == "up"   else
                t["trend_down"] if trend == "down" else
                t["muted"]
            )
            arrow = "▲ " if trend == "up" else "▼ " if trend == "down" else ""
            badge_label = f"{arrow}{change}"
            bw = len(badge_label) * 7 + 18
            bx = cx + card_w - bw - 14
            by = y + 14
            parts += [
                _rect(bx, by, bw, 20, rx=10,
                      fill=trend_color, opacity="0.15"),
                _text(bx + bw / 2, by + 13, badge_label,
                      fill=trend_color, font_size="10", font_weight="700",
                      font_family=t["font"], text_anchor="middle"),
            ]

    return "\n".join(parts), card_h


def _render_bar_chart(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    title  = section.get("title", "")
    data   = section.get("data", [])
    parts: list[str] = []
    cur_y  = y

    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 10

    if not data:
        return "", 0.0

    max_val  = max((d.get("value", 0) for d in data), default=1) or 1
    label_w  = 155.0
    val_w    = 52.0
    bar_area = width - label_w - val_w
    bh       = float(t.get("bar_h", 28))
    row_h    = bh + 18.0
    r        = bh / 2

    for i, item in enumerate(data):
        label  = item.get("label", "")
        value  = item.get("value", 0)
        pct    = value / max_val
        fill_w = max(pct * bar_area, 4.0)
        ry     = cur_y + i * row_h
        slot   = i % len(t["palette"])
        color  = item.get("color") or t["palette"][slot]

        parts += [
            # Row label
            _text(x, ry + bh - 7, label,
                  fill=t["text"], font_size="13", font_weight="500",
                  font_family=t["font"]),
            # Track
            _rect(x + label_w, ry, bar_area, bh, rx=r,
                  fill=t["card_border"]),
            # Filled bar — gradient
            _rect(x + label_w, ry, fill_w, bh, rx=r,
                  fill=f"url(#g_bar_{slot})"),
        ]

        # Percentage label inside bar if wide enough, otherwise after
        pct_str = f"{round(pct * 100)}%"
        if fill_w > 44:
            parts.append(
                _text(x + label_w + fill_w - 12, ry + bh - 8, pct_str,
                      fill="rgba(255,255,255,0.75)", font_size="10", font_weight="700",
                      font_family=t["font"], text_anchor="end")
            )
        else:
            parts.append(
                _text(x + label_w + fill_w + 8, ry + bh - 8, pct_str,
                      fill=t["muted"], font_size="10",
                      font_family=t["font"])
            )

        # Raw value
        parts.append(
            _text(x + label_w + bar_area + 10, ry + bh - 7, str(value),
                  fill=t["text"], font_size="12", font_weight="600",
                  font_family=t["font"])
        )

    return "\n".join(parts), (cur_y - y) + len(data) * row_h


def _render_donut(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    title  = section.get("title", "")
    data   = section.get("data", [])
    parts: list[str] = []
    cur_y  = y

    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 10

    if not data:
        return "", 0.0

    total  = sum(d.get("value", 0) for d in data) or 1
    r_out  = 75.0
    r_in   = 50.0   # thinner ring = more modern
    chart_d = r_out * 2 + 20
    dcx    = x + r_out + 10
    dcy    = cur_y + r_out + 10

    # Background track circle
    parts.append(_circle(dcx, dcy, r_out, fill="none",
                         stroke=t["card_border"], stroke_width="1"))

    # Segments
    angle = 0.0
    for i, item in enumerate(data):
        val   = item.get("value", 0)
        color = item.get("color") or t["palette"][i % len(t["palette"])]
        sweep = (val / total) * 360
        if sweep < 1:
            angle += sweep
            continue
        d = _donut_segment(dcx, dcy, r_out, r_in, angle, angle + sweep)
        parts.append(_path(d, fill=color))
        angle += sweep

    # Centre — total value in accent colour
    parts += [
        _text(dcx, dcy - 8, str(total),
              fill=t["palette"][0], font_size="24", font_weight="800",
              font_family=t["font"], text_anchor="middle"),
        _text(dcx, dcy + 13, "TOTAL",
              fill=t["muted"], font_size="9", font_weight="700",
              font_family=t["font"], text_anchor="middle", letter_spacing="1.5"),
    ]

    # Legend — right of donut, vertically centred
    lx   = x + chart_d + 28
    lrh  = 38.0
    n    = len(data)
    loff = max(0.0, (chart_d - n * lrh) / 2)
    ly   = cur_y + 10 + loff

    for i, item in enumerate(data):
        label = item.get("label", "")
        val   = item.get("value", 0)
        color = item.get("color") or t["palette"][i % len(t["palette"])]
        pct   = round(val / total * 100)
        iy    = ly + i * lrh

        # Colour indicator
        parts.append(_rect(lx, iy + 3, 14, 14, rx=3, fill=color))
        parts.append(
            _text(lx + 22, iy + 13, label,
                  fill=t["text"], font_size="13", font_weight="500",
                  font_family=t["font"])
        )
        parts.append(
            _text(lx + 22, iy + 27,
                  f"{val:,}  ·  {pct}%",
                  fill=t["muted"], font_size="11",
                  font_family=t["font"])
        )

    total_h = (cur_y - y) + max(chart_d, n * lrh) + 20
    return "\n".join(parts), total_h


def _render_stories(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    title  = section.get("title", "")
    items  = section.get("items", [])
    parts: list[str] = []
    cur_y  = y
    r      = t.get("radius", 14)

    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 8

    body_chars = int((width - 64) / 7.0)

    for i, story in enumerate(items):
        headline   = story.get("headline", "")
        body       = story.get("body", "")
        channel    = story.get("channel", "")
        author     = story.get("author", "")
        color      = t["palette"][i % len(t["palette"])]
        body_lines = _wrap_text(body, body_chars)
        card_h     = 46.0 + len(body_lines) * 20 + 30

        parts += [
            # Card shadow + bg
            _rect(x, cur_y, width, card_h, rx=r,
                  fill=t["card_bg"], filter="url(#g_shadow)"),
            # Colour tint on left
            _rect(x, cur_y, width * 0.35, card_h, rx=r,
                  fill=color, opacity="0.04"),
            # Mask right edge of tint bleed
            _rect(x + width * 0.35 - 8, cur_y, 12, card_h,
                  fill=t["card_bg"]),
            # Card border
            _rect(x, cur_y, width, card_h, rx=r,
                  fill="none", stroke=t["card_border"], stroke_width="1"),
            # Left accent stripe
            _rect(x, cur_y, 4, card_h, rx=2, fill=color),
            # Number bubble
            _circle(x + 28, cur_y + 26, 13, fill=color, opacity="0.18"),
            _text(x + 28, cur_y + 31, str(i + 1),
                  fill=color, font_size="12", font_weight="800",
                  font_family=t["font"], text_anchor="middle"),
            # Headline — in accent colour for boldness
            _text(x + 52, cur_y + 30, headline,
                  fill=color, font_size="14", font_weight="700",
                  font_family=t["font"]),
        ]

        # Body lines
        for li, line in enumerate(body_lines):
            parts.append(
                _text(x + 52, cur_y + 50 + li * 20, line,
                      fill=t["muted"], font_size="12",
                      font_family=t["font"])
            )

        # Meta (channel · author)
        meta_parts = []
        if channel:
            meta_parts.append(channel)
        if author:
            meta_parts.append(f"by {author}")
        if meta_parts:
            meta_y = cur_y + card_h - 11
            meta_str = "  ·  ".join(meta_parts)
            # pill background
            pw = len(meta_str) * 6.8 + 16
            parts += [
                _rect(x + 50, meta_y - 12, pw, 16, rx=8,
                      fill=color, opacity="0.12"),
                _text(x + 58, meta_y, meta_str,
                      fill=color, font_size="10", font_weight="600",
                      font_family=t["font"], opacity="0.85"),
            ]

        cur_y += card_h + 12

    return "\n".join(parts), cur_y - y


def _render_heatmap(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    title      = section.get("title", "")
    data       = section.get("data", [])
    row_labels = section.get("row_labels",
                             ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    parts: list[str] = []
    cur_y = y

    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 14

    if not data:
        return "", 0.0

    label_w  = 36.0
    cell_gap = 3
    cell_sz  = max(10, int((width - label_w - cell_gap * 23) / 24))
    row_h    = cell_sz + cell_gap
    color    = t["palette"][0]

    flat    = [v for row in data for v in row]
    max_val = max(flat) if flat else 1
    if max_val == 0:
        max_val = 1

    # Hour axis
    for hr in [0, 3, 6, 9, 12, 15, 18, 21, 23]:
        hx = x + label_w + hr * (cell_sz + cell_gap) + cell_sz / 2
        parts.append(
            _text(hx, cur_y - 5, str(hr),
                  fill=t["muted"], font_size="9",
                  font_family=t["font"], text_anchor="middle")
        )

    for ri, row in enumerate(data[:7]):
        ry  = cur_y + ri * row_h
        day = row_labels[ri] if ri < len(row_labels) else ""

        parts.append(
            _text(x, ry + cell_sz - 2, day,
                  fill=t["muted"], font_size="9", font_family=t["font"])
        )

        for ci, val in enumerate(row[:24]):
            opacity = max(0.06, val / max_val)
            cx2 = x + label_w + ci * (cell_sz + cell_gap)
            # Background cell
            parts.append(_rect(cx2, ry, cell_sz, cell_sz, rx=2,
                               fill=t["card_border"]))
            # Active cell using gradient
            parts.append(_rect(cx2, ry, cell_sz, cell_sz, rx=2,
                               fill="url(#g_cell)", opacity=f"{opacity:.2f}"))

    total_h = (cur_y - y) + 7 * row_h + 10
    return "\n".join(parts), total_h


def _render_divider(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    label = section.get("label", "")
    h     = 36.0
    mid   = y + h / 2

    if label:
        half_lw = len(label) * 3.8 + 14
        cx = x + width / 2
        color0 = t["palette"][0]
        parts = [
            _line(x, mid, cx - half_lw - 10, mid,
                  stroke=t["card_border"], stroke_width="1"),
            _rect(cx - half_lw - 2, mid - 10, (half_lw + 2) * 2, 20, rx=10,
                  fill=t["card_bg"]),
            _text(cx, mid + 4, label,
                  fill=color0, font_size="11", font_weight="600",
                  font_family=t["font"], text_anchor="middle",
                  letter_spacing="0.5"),
            _line(cx + half_lw + 10, mid, x + width, mid,
                  stroke=t["card_border"], stroke_width="1"),
        ]
    else:
        parts = [
            _line(x, mid, x + width, mid,
                  stroke=t["card_border"], stroke_width="1", opacity="0.6"),
        ]

    return "\n".join(parts), h


def _render_text_block(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    content = section.get("content", "")
    chars   = int(width / 7.4)
    lines   = _wrap_text(content, chars)
    lh      = 22.0
    r       = t.get("radius", 14)
    card_h  = len(lines) * lh + 32

    parts = [
        _rect(x, y, width, card_h, rx=r,
              fill=t["card_bg"], stroke=t["card_border"], stroke_width="1"),
        _rect(x, y, 4, card_h, rx=2, fill=t["palette"][0]),
    ]
    for i, line in enumerate(lines):
        parts.append(
            _text(x + 18, y + 20 + i * lh, line,
                  fill=t["muted"], font_size="13", font_family=t["font"])
        )
    return "\n".join(parts), card_h + 4


# ---------------------------------------------------------------------------
# AntV-parity section renderers
# ---------------------------------------------------------------------------

def _render_process_flow(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    """Numbered step cards connected by arrows (horizontal, wraps to next row)."""
    items  = section.get("items", [])
    title  = section.get("title", "")
    n      = len(items)
    if not n:
        return "", 0.0

    parts: list[str] = []
    cur_y = y
    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 10

    max_per_row = min(n, 4)
    arrow_w     = 26.0
    gap         = 10.0
    card_w      = (width - (max_per_row - 1) * (arrow_w + gap)) / max_per_row
    card_h      = 124.0
    r           = t.get("radius", 10)
    start_y     = cur_y

    for i, item in enumerate(items):
        col = i % max_per_row
        row = i // max_per_row
        cx2 = x + col * (card_w + arrow_w + gap)
        cy2 = start_y + row * (card_h + 40)
        color = t["palette"][i % len(t["palette"])]

        # Card
        parts += [
            _rect(cx2, cy2, card_w, card_h, rx=r,
                  fill=t["card_bg"], filter="url(#g_shadow)"),
            _rect(cx2, cy2, card_w, card_h, rx=r,
                  fill="none", stroke=t["card_border"], stroke_width="1"),
            _rect(cx2 + r, cy2, card_w - r * 2, 3, rx=1.5, fill=color),
        ]
        # Number circle
        parts += [
            _circle(cx2 + card_w / 2, cy2 + 32, 18, fill=color, opacity="0.18"),
            _circle(cx2 + card_w / 2, cy2 + 32, 18, fill="none", stroke=color, stroke_width="1.5"),
            _text(cx2 + card_w / 2, cy2 + 37, str(i + 1),
                  fill=color, font_size="14", font_weight="800",
                  font_family=t["font"], text_anchor="middle"),
        ]
        # Title + body
        title_txt = item.get("title", "")
        body_txt  = item.get("body", "")
        parts.append(_text(cx2 + card_w / 2, cy2 + 64, title_txt,
                           fill=t["text"], font_size="12", font_weight="700",
                           font_family=t["font"], text_anchor="middle"))
        for li, line in enumerate(_wrap_text(body_txt, int(card_w / 6.6))[:2]):
            parts.append(_text(cx2 + card_w / 2, cy2 + 82 + li * 18, line,
                               fill=t["muted"], font_size="10",
                               font_family=t["font"], text_anchor="middle"))

        # Arrow to next item on same row
        if col < max_per_row - 1 and i < n - 1:
            ax = cx2 + card_w + gap
            ay = cy2 + card_h / 2
            aend = ax + arrow_w - 2
            parts += [
                _line(ax, ay, aend, ay, stroke=t["muted"],
                      stroke_width="1.5", opacity="0.45"),
                _path(f"M {aend:.0f} {ay:.0f} L {aend-8:.0f} {ay-5:.0f} L {aend-8:.0f} {ay+5:.0f} Z",
                      fill=t["muted"], opacity="0.45"),
            ]

    rows    = (n - 1) // max_per_row + 1
    total_h = rows * card_h + (rows - 1) * 40 + (cur_y - y) + 8
    return "\n".join(parts), total_h


def _render_circular_flow(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    """Items arranged around a circle with dashed curved arrows."""
    items  = section.get("items", [])
    title  = section.get("title", "")
    n      = len(items)
    if n < 2:
        return "", 0.0

    parts: list[str] = []
    cur_y = y
    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 10

    h        = min(float(width), 360.0)
    r_orbit  = h * 0.32
    node_r   = 34.0
    cx_c     = x + width / 2
    cy_c     = cur_y + h / 2

    # Center accent
    parts += [
        _circle(cx_c, cy_c, 26, fill=t["palette"][0], opacity="0.12"),
        _circle(cx_c, cy_c, 26, fill="none", stroke=t["palette"][0],
                stroke_width="1", opacity="0.5"),
    ]
    center_label = section.get("center_label", "")
    if center_label:
        parts.append(_text(cx_c, cy_c + 5, center_label,
                           fill=t["palette"][0], font_size="10", font_weight="700",
                           font_family=t["font"], text_anchor="middle"))

    positions: list[tuple[float, float]] = []
    for i in range(n):
        angle = math.radians(-90 + 360 * i / n)
        positions.append((cx_c + r_orbit * math.cos(angle),
                          cy_c + r_orbit * math.sin(angle)))

    # Dashed arrows between consecutive nodes
    for i in range(n):
        x1, y1 = positions[i]
        x2, y2 = positions[(i + 1) % n]
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        qx = cx_c + (mx - cx_c) * 0.38
        qy = cy_c + (my - cy_c) * 0.38
        color = t["palette"][i % len(t["palette"])]
        parts.append(_path(f"M {x1:.1f} {y1:.1f} Q {qx:.1f} {qy:.1f} {x2:.1f} {y2:.1f}",
                           fill="none", stroke=color, stroke_width="1.5",
                           opacity="0.35", stroke_dasharray="5 3"))

    # Nodes
    for i, item in enumerate(items):
        nx, ny   = positions[i]
        color    = t["palette"][i % len(t["palette"])]
        lbl      = item.get("title", "")
        parts += [
            _circle(nx, ny, node_r, fill=t["card_bg"], filter="url(#g_shadow)"),
            _circle(nx, ny, node_r, fill=color, opacity="0.18"),
            _circle(nx, ny, node_r, fill="none", stroke=color, stroke_width="1.5"),
            _text(nx, ny - 5, str(i + 1), fill=color, font_size="15",
                  font_weight="800", font_family=t["font"], text_anchor="middle"),
        ]
        # Label positioned outside the orbit
        angle     = math.radians(-90 + 360 * i / n)
        push      = node_r + 18
        lx        = nx + push * math.cos(angle)
        ly        = ny + push * math.sin(angle)
        anchor    = "middle"
        if lx < cx_c - 30:
            anchor = "end"
        elif lx > cx_c + 30:
            anchor = "start"
        parts.append(_text(lx, ly + 4, lbl, fill=t["text"], font_size="11",
                           font_weight="600", font_family=t["font"],
                           text_anchor=anchor))

    return "\n".join(parts), h + 10


def _render_staircase(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    """Ascending color steps — bottom-aligned, each step taller than the last."""
    items  = section.get("items", [])
    title  = section.get("title", "")
    n      = len(items)
    if not n:
        return "", 0.0

    parts: list[str] = []
    cur_y = y
    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 10

    max_h  = 210.0
    base_y = cur_y + max_h
    gap    = 4.0
    step_w = (width - (n - 1) * gap) / n
    r      = 6

    for i, item in enumerate(items):
        label  = item.get("label", "")
        value  = item.get("value")
        color  = t["palette"][i % len(t["palette"])]
        slot   = i % len(t["palette"])
        step_h = max_h * (i + 1) / n
        sx     = x + i * (step_w + gap)
        sy     = base_y - step_h

        # Full gradient fill
        parts.append(_rect(sx, sy, step_w, step_h, rx=r,
                           fill=f"url(#g_bar_{slot})"))
        # Cancel bottom rounding (keep top rounded only)
        parts.append(_rect(sx, sy + step_h - r, step_w, r,
                           fill=color))

        # Step number at top
        parts.append(_text(sx + step_w / 2, sy + 22, str(i + 1),
                           fill="rgba(255,255,255,0.9)", font_size="16",
                           font_weight="800", font_family=t["font"],
                           text_anchor="middle"))
        if value is not None:
            parts.append(_text(sx + step_w / 2, sy + 42, str(value),
                               fill="rgba(255,255,255,0.85)", font_size="13",
                               font_weight="700", font_family=t["font"],
                               text_anchor="middle"))
        # Label at base of step
        chars = max(4, int(step_w / 6.5))
        wrapped = _wrap_text(label, chars)
        for li, line in enumerate(reversed(wrapped)):
            parts.append(_text(sx + step_w / 2,
                               base_y - 8 - li * 14, line,
                               fill="rgba(255,255,255,0.85)", font_size="10",
                               font_weight="600", font_family=t["font"],
                               text_anchor="middle"))

    return "\n".join(parts), max_h + (cur_y - y) + 10


def _render_pyramid(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    """Layered trapezoid pyramid — narrow top, wide bottom."""
    items  = section.get("items", [])
    title  = section.get("title", "")
    n      = len(items)
    if not n:
        return "", 0.0

    parts: list[str] = []
    cur_y = y
    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 10

    layer_h    = 46.0
    gap        = 3.0
    pyr_w      = width * 0.48
    cx_c       = x + pyr_w / 2 + _PAD_H * 0.5
    label_x    = x + pyr_w + 28

    for i, item in enumerate(items):
        label  = item.get("label", "")
        body   = item.get("body", "")
        slot   = i % len(t["palette"])
        color  = t["palette"][slot]

        frac_top = (i + 0.3) / n
        frac_bot = (i + 1.0) / n
        half_top = pyr_w * 0.5 * frac_top
        half_bot = pyr_w * 0.5 * min(frac_bot, 1.0)
        ty       = cur_y + i * (layer_h + gap)
        by       = ty + layer_h

        d = (f"M {cx_c - half_top:.1f} {ty:.1f} "
             f"L {cx_c + half_top:.1f} {ty:.1f} "
             f"L {cx_c + half_bot:.1f} {by:.1f} "
             f"L {cx_c - half_bot:.1f} {by:.1f} Z")
        parts.append(_path(d, fill=f"url(#g_bar_{slot})"))

        # Level number centred in layer
        parts.append(_text(cx_c, ty + layer_h / 2 + 5, str(i + 1),
                           fill="rgba(255,255,255,0.9)", font_size="14",
                           font_weight="800", font_family=t["font"],
                           text_anchor="middle"))

        # Label right side with dashed connector
        mid_y  = ty + layer_h / 2
        con_x  = cx_c + half_top + 6
        parts += [
            _line(con_x, mid_y, label_x - 4, mid_y,
                  stroke=t["muted"], stroke_width="1",
                  stroke_dasharray="3 3", opacity="0.5"),
            _text(label_x, mid_y + 4, label, fill=color,
                  font_size="13", font_weight="700",
                  font_family=t["font"]),
        ]
        if body:
            parts.append(_text(label_x, mid_y + 18, body,
                               fill=t["muted"], font_size="10",
                               font_family=t["font"]))

    total_h = n * (layer_h + gap) + (cur_y - y)
    return "\n".join(parts), total_h + 10


def _render_snake_path(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    """Serpentine numbered path — odd rows reverse direction."""
    items  = section.get("items", [])
    title  = section.get("title", "")
    n      = len(items)
    if not n:
        return "", 0.0

    parts: list[str] = []
    cur_y = y
    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 10

    cols    = min(n, 4)
    node_r  = 28.0
    node_gap = (width - cols * node_r * 2) / max(cols - 1, 1)
    row_h   = node_r * 2 + 52.0

    def _node_pos(idx: int) -> tuple[float, float]:
        col = idx % cols
        row = idx // cols
        if row % 2 == 1:
            col = cols - 1 - col
        nx = x + col * (node_r * 2 + node_gap) + node_r
        ny = cur_y + row * row_h + node_r
        return nx, ny

    for i, item in enumerate(items):
        nx, ny = _node_pos(i)
        color  = t["palette"][i % len(t["palette"])]
        label  = item.get("label", "")

        parts += [
            _circle(nx, ny, node_r, fill=t["card_bg"], filter="url(#g_shadow)"),
            _circle(nx, ny, node_r, fill=color, opacity="0.18"),
            _circle(nx, ny, node_r, fill="none", stroke=color, stroke_width="2"),
            _text(nx, ny + 6, str(i + 1), fill=color, font_size="16",
                  font_weight="800", font_family=t["font"], text_anchor="middle"),
        ]
        for li, line in enumerate(_wrap_text(label, int(node_r * 2 / 5.5))):
            parts.append(_text(nx, ny + node_r + 16 + li * 13, line,
                               fill=t["text"], font_size="10", font_weight="500",
                               font_family=t["font"], text_anchor="middle"))

        # Connector to next
        if i < n - 1:
            nnx, nny = _node_pos(i + 1)
            col_cur  = i % cols
            row_cur  = i // cols
            row_nxt  = (i + 1) // cols
            if row_nxt == row_cur:
                # Same row — simple horizontal
                parts.append(_line(nx + node_r, ny, nnx - node_r, nny,
                                   stroke=color, stroke_width="1.5", opacity="0.3"))
            else:
                # Wrap — arc down then across
                parts.append(_line(nx, ny + node_r, nnx, nny - node_r,
                                   stroke=color, stroke_width="1.5", opacity="0.25",
                                   stroke_dasharray="4 3"))

    rows    = (n - 1) // cols + 1
    return "\n".join(parts), rows * row_h + (cur_y - y) + 10


def _render_bubble_chain(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    """Horizontally connected circles sized by value."""
    items  = section.get("items", [])
    title  = section.get("title", "")
    n      = len(items)
    if not n:
        return "", 0.0

    parts: list[str] = []
    cur_y = y
    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 10

    max_val = max((item.get("value", 1) for item in items), default=1) or 1
    min_r   = 18.0
    max_r   = 52.0
    radii   = [min_r + (item.get("value", 0) / max_val) * (max_r - min_r)
               for item in items]

    connector = 16.0
    total_w   = sum(r * 2 for r in radii) + (n - 1) * connector
    scale     = min(1.0, width / total_w) if total_w > width else 1.0
    radii     = [r * scale for r in radii]
    conn_s    = connector * scale

    max_r_val = max(radii, default=max_r)
    cy_center = cur_y + max_r_val + 20
    offset_x  = x + (width - sum(r * 2 for r in radii) - (n - 1) * conn_s) / 2

    cur_x = offset_x
    for i, item in enumerate(items):
        rv     = radii[i]
        label  = item.get("label", "")
        value  = item.get("value", "")
        color  = t["palette"][i % len(t["palette"])]
        bx     = cur_x + rv

        if i < n - 1:
            nrv    = radii[i + 1]
            next_x = bx + rv + conn_s + nrv
            parts.append(_line(bx + rv, cy_center, next_x - nrv, cy_center,
                               stroke=t["muted"], stroke_width="1", opacity="0.3"))

        parts += [
            _circle(bx, cy_center, rv, fill=color, opacity="0.15"),
            _circle(bx, cy_center, rv, fill="none", stroke=color, stroke_width="2"),
            _text(bx, cy_center - 4, str(value),
                  fill=color, font_size=f"{max(9, int(rv * 0.42))}",
                  font_weight="800", font_family=t["font"], text_anchor="middle"),
            _text(bx, cy_center + max_r_val + 16, label,
                  fill=t["text"], font_size="11", font_weight="500",
                  font_family=t["font"], text_anchor="middle"),
        ]
        cur_x += rv * 2 + conn_s

    return "\n".join(parts), max_r_val * 2 + 50 + (cur_y - y)


def _render_timeline(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    """Horizontal timeline with alternating above/below event labels."""
    items  = section.get("items", [])
    title  = section.get("title", "")
    n      = len(items)
    if not n:
        return "", 0.0

    parts: list[str] = []
    cur_y = y
    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 10

    above_h = 72.0
    below_h = 72.0
    line_y  = cur_y + above_h

    # Timeline rail
    parts.append(_rect(x, line_y - 2, width, 4, rx=2, fill=t["card_border"]))

    for i, item in enumerate(items):
        label    = item.get("label", "")
        date_txt = item.get("date", "")
        body     = item.get("body", "")
        color    = t["palette"][i % len(t["palette"])]
        px       = x + (i + 0.5) * width / n

        parts += [
            _circle(px, line_y, 6, fill=color),
            _circle(px, line_y, 11, fill=color, opacity="0.2"),
        ]

        if i % 2 == 0:
            # Above
            parts += [
                _line(px, line_y - 7, px, line_y - 18,
                      stroke=color, stroke_width="1", opacity="0.4"),
                _text(px, line_y - 24, label, fill=t["text"], font_size="12",
                      font_weight="700", font_family=t["font"], text_anchor="middle"),
            ]
            if date_txt:
                parts.append(_text(px, line_y - 38, date_txt, fill=color,
                                   font_size="10", font_weight="600",
                                   font_family=t["font"], text_anchor="middle"))
            if body:
                parts.append(_text(px, line_y - 52, body, fill=t["muted"],
                                   font_size="10", font_family=t["font"],
                                   text_anchor="middle"))
        else:
            # Below
            parts += [
                _line(px, line_y + 7, px, line_y + 18,
                      stroke=color, stroke_width="1", opacity="0.4"),
                _text(px, line_y + 30, label, fill=t["text"], font_size="12",
                      font_weight="700", font_family=t["font"], text_anchor="middle"),
            ]
            if date_txt:
                parts.append(_text(px, line_y + 44, date_txt, fill=color,
                                   font_size="10", font_weight="600",
                                   font_family=t["font"], text_anchor="middle"))
            if body:
                parts.append(_text(px, line_y + 58, body, fill=t["muted"],
                                   font_size="10", font_family=t["font"],
                                   text_anchor="middle"))

    return "\n".join(parts), above_h + below_h + (cur_y - y) + 10


def _render_venn(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    """2–3 overlapping Venn circles with optional intersection label."""
    items        = section.get("items", [])
    center_label = section.get("center_label", "")
    title        = section.get("title", "")
    n            = min(len(items), 3)
    if n < 2:
        return "", 0.0

    parts: list[str] = []
    cur_y = y
    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 10

    h      = 240.0
    r_circ = h * 0.36
    cx_c   = x + width / 2
    cy_c   = cur_y + h / 2
    offset = r_circ * 0.48

    if n == 2:
        centers: list[tuple[float, float]] = [
            (cx_c - offset, cy_c),
            (cx_c + offset, cy_c),
        ]
    else:
        centers = [
            (cx_c, cy_c - offset),
            (cx_c - offset * 0.88, cy_c + offset * 0.52),
            (cx_c + offset * 0.88, cy_c + offset * 0.52),
        ]

    for i in range(n):
        ccx, ccy = centers[i]
        color    = t["palette"][i % len(t["palette"])]
        parts += [
            _circle(ccx, ccy, r_circ, fill=color, opacity="0.12"),
            _circle(ccx, ccy, r_circ, fill="none", stroke=color,
                    stroke_width="2", opacity="0.65"),
        ]
        # Label positioned toward outer edge
        dx   = ccx - cx_c
        dy   = ccy - cy_c
        norm = math.sqrt(dx * dx + dy * dy) or 1
        lx   = ccx + (dx / norm) * r_circ * 0.52
        ly   = ccy + (dy / norm) * r_circ * 0.52

        item     = items[i]
        lbl      = item.get("label", "")
        sub_list = item.get("items", [])
        anchor   = "middle"
        if dx < -10:
            anchor = "end"
        elif dx > 10:
            anchor = "start"

        parts.append(_text(lx, ly, lbl, fill=color, font_size="13",
                           font_weight="700", font_family=t["font"],
                           text_anchor=anchor))
        for si, sub in enumerate(sub_list[:3]):
            parts.append(_text(lx, ly + 15 + si * 13, sub, fill=t["muted"],
                               font_size="10", font_family=t["font"],
                               text_anchor=anchor))

    if center_label:
        parts.append(_text(cx_c, cy_c + 5, center_label, fill=t["text"],
                           font_size="12", font_weight="700",
                           font_family=t["font"], text_anchor="middle"))

    return "\n".join(parts), h + (cur_y - y) + 10


def _render_comparison(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    """Two-column VS comparison with labelled item lists."""
    left   = section.get("left",  {"label": "Option A", "items": []})
    right  = section.get("right", {"label": "Option B", "items": []})
    title  = section.get("title", "")

    parts: list[str] = []
    cur_y = y
    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 10

    vs_w      = 64.0
    col_w     = (width - vs_w) / 2
    r         = t.get("radius", 14)
    l_items   = left.get("items", [])
    r_items   = right.get("items", [])
    max_items = max(len(l_items), len(r_items), 1)
    card_h    = max_items * 34 + 58

    # Left card
    c0 = t["palette"][0]
    parts += [
        _rect(x, cur_y, col_w, card_h, rx=r, fill=t["card_bg"],
              stroke=c0, stroke_width="1.5", filter="url(#g_shadow)"),
        _rect(x, cur_y, col_w, 46, rx=r, fill=c0, opacity="0.2"),
        _rect(x, cur_y + 46 - r, col_w, r, fill=c0, opacity="0.2"),
        _text(x + col_w / 2, cur_y + 30, left.get("label", ""),
              fill=c0, font_size="16", font_weight="800",
              font_family=t["font"], text_anchor="middle"),
    ]
    for ii, it in enumerate(l_items):
        parts.append(_text(x + 16, cur_y + 60 + ii * 34, f"• {it}",
                           fill=t["text"], font_size="12", font_family=t["font"]))

    # VS badge center
    vsx = x + col_w + vs_w / 2
    vsy = cur_y + card_h / 2
    parts += [
        _circle(vsx, vsy, 24, fill=t["card_bg"]),
        _circle(vsx, vsy, 24, fill="none", stroke=t["muted"], stroke_width="1"),
        _text(vsx, vsy + 5, "VS", fill=t["muted"], font_size="13",
              font_weight="800", font_family=t["font"], text_anchor="middle"),
    ]

    # Right card
    c1  = t["palette"][1 % len(t["palette"])]
    rx2 = x + col_w + vs_w
    parts += [
        _rect(rx2, cur_y, col_w, card_h, rx=r, fill=t["card_bg"],
              stroke=c1, stroke_width="1.5", filter="url(#g_shadow)"),
        _rect(rx2, cur_y, col_w, 46, rx=r, fill=c1, opacity="0.2"),
        _rect(rx2, cur_y + 46 - r, col_w, r, fill=c1, opacity="0.2"),
        _text(rx2 + col_w / 2, cur_y + 30, right.get("label", ""),
              fill=c1, font_size="16", font_weight="800",
              font_family=t["font"], text_anchor="middle"),
    ]
    for ii, it in enumerate(r_items):
        parts.append(_text(rx2 + 16, cur_y + 60 + ii * 34, f"• {it}",
                           fill=t["text"], font_size="12", font_family=t["font"]))

    return "\n".join(parts), card_h + (cur_y - y) + 10


def _render_swot(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    """S/W/O/T 2×2 analysis grid with coloured headers."""
    quadrants = section.get("quadrants", [
        {"label": "Strengths",    "items": []},
        {"label": "Weaknesses",   "items": []},
        {"label": "Opportunities","items": []},
        {"label": "Threats",      "items": []},
    ])
    title = section.get("title", "")

    parts: list[str] = []
    cur_y = y
    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 10

    letters   = ["S", "W", "O", "T"]
    gap       = 8.0
    cell_w    = (width - gap) / 2
    max_items = max((len(q.get("items", [])) for q in quadrants[:4]), default=3)
    cell_h    = max_items * 22 + 62
    r         = t.get("radius", 10)

    for i, q in enumerate(quadrants[:4]):
        col   = i % 2
        row   = i // 2
        qx    = x + col * (cell_w + gap)
        qy    = cur_y + row * (cell_h + gap)
        color = t["palette"][i % len(t["palette"])]
        lbl   = q.get("label", letters[i])
        items = q.get("items", [])

        parts += [
            _rect(qx, qy, cell_w, cell_h, rx=r, fill=t["card_bg"],
                  stroke=t["card_border"], stroke_width="1"),
            _rect(qx, qy, cell_w, 48, rx=r, fill=color, opacity="0.22"),
            _rect(qx, qy + 48 - r, cell_w, r, fill=color, opacity="0.22"),
            # Big initial letter
            _text(qx + 18, qy + 34, letters[i], fill=color, font_size="22",
                  font_weight="900", font_family=t["font"]),
            # Label next to letter
            _text(qx + 44, qy + 34, lbl, fill=color, font_size="13",
                  font_weight="700", font_family=t["font"]),
        ]
        for ii, it in enumerate(items[:max_items]):
            parts.append(_text(qx + 14, qy + 62 + ii * 22, f"• {it}",
                               fill=t["text"], font_size="11",
                               font_family=t["font"]))

    return "\n".join(parts), 2 * cell_h + gap + (cur_y - y) + 10


def _render_matrix_2x2(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    """Generic 2×2 colour-coded grid with optional axis labels."""
    cells   = section.get("cells", [
        {"label": "", "body": ""},
        {"label": "", "body": ""},
        {"label": "", "body": ""},
        {"label": "", "body": ""},
    ])
    x_label = section.get("x_label", "")
    y_label = section.get("y_label", "")
    title   = section.get("title", "")

    parts: list[str] = []
    cur_y = y
    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 10

    margin  = 26.0
    gap     = 8.0
    cell_w  = (width - gap - margin) / 2
    chars   = int(cell_w / 6.5)
    max_lines = max((len(_wrap_text(c.get("body", ""), chars)) for c in cells[:4]), default=2)
    cell_h  = max_lines * 18 + 58
    r       = t.get("radius", 10)

    # X-axis label (top)
    if x_label:
        parts.append(_text(x + margin + width / 2 - margin / 2, cur_y - 6,
                           x_label, fill=t["muted"], font_size="10",
                           font_weight="600", font_family=t["font"],
                           text_anchor="middle", letter_spacing="1"))

    # Y-axis label (rotated, left side)
    if y_label:
        yx = x + 10
        yy = cur_y + cell_h + gap / 2
        parts.append(
            f'<text x="{yx:.0f}" y="{yy:.0f}" '
            f'fill="{t["muted"]}" font-size="10" font-weight="600" '
            f'font-family="{t["font"]}" text-anchor="middle" '
            f'transform="rotate(-90 {yx:.0f} {yy:.0f})">{_e(y_label)}</text>'
        )

    for i, cell in enumerate(cells[:4]):
        col   = i % 2
        row   = i // 2
        cx2   = x + margin + col * (cell_w + gap)
        cy2   = cur_y + row * (cell_h + gap)
        color = t["palette"][i % len(t["palette"])]
        lbl   = cell.get("label", "")
        body  = cell.get("body", "")

        parts += [
            _rect(cx2, cy2, cell_w, cell_h, rx=r, fill=color, opacity="0.1"),
            _rect(cx2, cy2, cell_w, cell_h, rx=r, fill="none",
                  stroke=color, stroke_width="1.5", opacity="0.4"),
            _rect(cx2 + r, cy2, cell_w - r * 2, 4, rx=2, fill=color),
            _text(cx2 + 14, cy2 + 28, lbl, fill=color, font_size="14",
                  font_weight="700", font_family=t["font"]),
        ]
        for li, line in enumerate(_wrap_text(body, chars)):
            parts.append(_text(cx2 + 14, cy2 + 46 + li * 18, line,
                               fill=t["muted"], font_size="11",
                               font_family=t["font"]))

    return "\n".join(parts), 2 * cell_h + gap + (cur_y - y) + 10


def _render_quadrant_circle(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    """Circle divided into 4 equal coloured sectors with labels."""
    quadrants    = section.get("quadrants", [])
    center_label = section.get("center_label", "")
    title        = section.get("title", "")

    parts: list[str] = []
    cur_y = y
    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 10

    h       = min(float(width) * 0.75, 300.0)
    r_outer = h / 2 - 10
    r_inner = r_outer * 0.24
    cx_c    = x + width / 2
    cy_c    = cur_y + h / 2

    for i in range(4):
        start_deg = i * 90 - 90
        end_deg   = start_deg + 89.5      # small gap between sectors
        color     = t["palette"][i % len(t["palette"])]
        d         = _donut_segment(cx_c, cy_c, r_outer, r_inner, start_deg, end_deg)
        parts += [
            _path(d, fill=color, opacity="0.28"),
            _path(d, fill="none", stroke=t["bg"], stroke_width="2"),
        ]

        if i < len(quadrants):
            q         = quadrants[i]
            lbl       = q.get("label", "")
            val_str   = str(q.get("value", "")) if q.get("value") is not None else ""
            mid_angle = math.radians(start_deg + 45)
            lx = cx_c + (r_inner + (r_outer - r_inner) * 0.56) * math.cos(mid_angle)
            ly = cy_c + (r_inner + (r_outer - r_inner) * 0.56) * math.sin(mid_angle)
            parts.append(_text(lx, ly - 5, lbl, fill=color, font_size="12",
                               font_weight="700", font_family=t["font"],
                               text_anchor="middle"))
            if val_str:
                parts.append(_text(lx, ly + 10, val_str, fill=t["text"],
                                   font_size="11", font_family=t["font"],
                                   text_anchor="middle"))

    # Dividing lines
    parts += [
        _line(cx_c - r_outer, cy_c, cx_c + r_outer, cy_c,
              stroke=t["bg"], stroke_width="3"),
        _line(cx_c, cy_c - r_outer, cx_c, cy_c + r_outer,
              stroke=t["bg"], stroke_width="3"),
    ]
    # Centre disc
    parts.append(_circle(cx_c, cy_c, r_inner, fill=t["card_bg"]))
    if center_label:
        parts.append(_text(cx_c, cy_c + 5, center_label, fill=t["text"],
                           font_size="11", font_weight="700",
                           font_family=t["font"], text_anchor="middle"))

    return "\n".join(parts), h + (cur_y - y) + 10


def _render_card_grid(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    """Flexible-column card grid with top accent stripe."""
    items = section.get("items", [])
    cols  = int(section.get("cols", 3))
    title = section.get("title", "")
    n     = len(items)
    if not n:
        return "", 0.0

    parts: list[str] = []
    cur_y = y
    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 10

    cols   = min(cols, n, 4)
    gap    = 12.0
    card_w = (width - (cols - 1) * gap) / cols
    r      = t.get("radius", 12)
    chars  = int(card_w / 6.5)

    max_lines = max(
        (len(_wrap_text(item.get("body", ""), chars)) for item in items),
        default=2,
    )
    card_h = max_lines * 18 + 72

    start_y = cur_y
    for i, item in enumerate(items):
        col   = i % cols
        row   = i // cols
        cx2   = x + col * (card_w + gap)
        cy2   = start_y + row * (card_h + gap)
        color = t["palette"][i % len(t["palette"])]
        lbl   = item.get("title", "")
        body  = item.get("body", "")

        parts += [
            _rect(cx2, cy2, card_w, card_h, rx=r, fill=t["card_bg"],
                  filter="url(#g_shadow)"),
            _rect(cx2, cy2, card_w, card_h, rx=r, fill="none",
                  stroke=t["card_border"], stroke_width="1"),
            # Top accent bar (sits inside the rounded corners)
            _rect(cx2 + r, cy2, card_w - r * 2, 4, rx=2, fill=color),
            # Number badge
            _circle(cx2 + 20, cy2 + 30, 13, fill=color, opacity="0.2"),
            _text(cx2 + 20, cy2 + 35, str(i + 1), fill=color, font_size="11",
                  font_weight="800", font_family=t["font"], text_anchor="middle"),
            # Card title
            _text(cx2 + 40, cy2 + 34, lbl, fill=t["text"], font_size="13",
                  font_weight="700", font_family=t["font"]),
        ]
        for li, line in enumerate(_wrap_text(body, chars)[:max_lines]):
            parts.append(_text(cx2 + 14, cy2 + 52 + li * 18, line,
                               fill=t["muted"], font_size="11",
                               font_family=t["font"]))

    rows    = (n - 1) // cols + 1
    total_h = rows * (card_h + gap) + (cur_y - y)
    return "\n".join(parts), total_h


def _render_pill_list(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    """Horizontal coloured pill steps connected by arrows."""
    items = section.get("items", [])
    title = section.get("title", "")
    n     = len(items)
    if not n:
        return "", 0.0

    parts: list[str] = []
    cur_y = y
    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 10

    arrow_w = 22.0
    pill_h  = 42.0
    pill_r  = pill_h / 2
    gap     = arrow_w
    pill_w  = (width - (n - 1) * gap) / n

    for i, item in enumerate(items):
        label = item.get("label", "")
        sub   = item.get("sub", "")
        color = t["palette"][i % len(t["palette"])]
        slot  = i % len(t["palette"])
        px    = x + i * (pill_w + gap)
        py    = cur_y

        # Pill background gradient
        parts.append(_rect(px, py, pill_w, pill_h, rx=pill_r,
                           fill=f"url(#g_bar_{slot})"))

        # Number circle on left
        parts += [
            _circle(px + pill_r, py + pill_h / 2, pill_r * 0.58,
                    fill="rgba(0,0,0,0.22)"),
            _text(px + pill_r, py + pill_h / 2 + 5, str(i + 1),
                  fill="white", font_size="12", font_weight="800",
                  font_family=t["font"], text_anchor="middle"),
        ]

        # Label (right portion of pill)
        text_x = px + pill_r + 18 + (pill_w - pill_r - 22) / 2
        parts.append(_text(text_x, py + pill_h / 2 + 5, label,
                           fill="white", font_size="11", font_weight="700",
                           font_family=t["font"], text_anchor="middle"))

        if sub:
            parts.append(_text(px + pill_w / 2, py + pill_h + 17, sub,
                               fill=t["muted"], font_size="10",
                               font_family=t["font"], text_anchor="middle"))

        # Arrow to next
        if i < n - 1:
            ax   = px + pill_w + 3
            ay   = py + pill_h / 2
            aend = ax + arrow_w - 4
            parts += [
                _line(ax, ay, aend, ay, stroke=t["muted"],
                      stroke_width="1.5", opacity="0.45"),
                _path(f"M {aend:.0f} {ay:.0f} "
                      f"L {aend-7:.0f} {ay-4:.0f} "
                      f"L {aend-7:.0f} {ay+4:.0f} Z",
                      fill=t["muted"], opacity="0.45"),
            ]

    return "\n".join(parts), pill_h + 30 + (cur_y - y)


def _render_wheel(section: dict, x: float, y: float, width: float, t: dict) -> tuple[str, float]:
    """Segmented wheel/donut — equal-size or value-proportional slices."""
    data         = section.get("data", [])
    equal        = bool(section.get("equal", False))
    center_label = section.get("center_label", "")
    title        = section.get("title", "")
    n            = len(data)
    if not n:
        return "", 0.0

    parts: list[str] = []
    cur_y = y
    if title:
        s, dh = _section_title(title, x, cur_y, width, t)
        parts.append(s)
        cur_y += dh + 10

    h       = min(float(width) * 0.72, 270.0)
    r_outer = h / 2 - 10
    r_inner = r_outer * 0.38
    cx_c    = x + width / 2
    cy_c    = cur_y + h / 2

    total = n if equal else (sum(d.get("value", 1) for d in data) or n)
    angle = 0.0

    for i, item in enumerate(data):
        val   = 1 if equal else item.get("value", 1)
        sweep = (val / total) * 360
        color = item.get("color") or t["palette"][i % len(t["palette"])]
        label = item.get("label", "")

        d = _donut_segment(cx_c, cy_c, r_outer, r_inner, angle, angle + sweep - 0.8)
        parts += [
            _path(d, fill=color, opacity="0.82"),
            _path(d, fill="none", stroke=t["bg"], stroke_width="2"),
        ]

        if sweep > 16:
            mid_a = math.radians(angle + sweep / 2 - 90)
            lx    = cx_c + (r_inner + (r_outer - r_inner) * 0.6) * math.cos(mid_a)
            ly    = cy_c + (r_inner + (r_outer - r_inner) * 0.6) * math.sin(mid_a)
            parts.append(_text(lx, ly + 4, label, fill="white", font_size="11",
                               font_weight="700", font_family=t["font"],
                               text_anchor="middle"))

        angle += sweep

    # Centre disc
    parts.append(_circle(cx_c, cy_c, r_inner, fill=t["card_bg"]))
    if center_label:
        parts.append(_text(cx_c, cy_c + 5, center_label, fill=t["text"],
                           font_size="13", font_weight="700",
                           font_family=t["font"], text_anchor="middle"))

    # Legend row below wheel
    legend_y   = cur_y + h + 12
    legend_gap = min(130.0, width / n)
    start_lx   = x + (width - n * legend_gap) / 2

    for i, item in enumerate(data):
        color = item.get("color") or t["palette"][i % len(t["palette"])]
        lbl   = item.get("label", "")
        val   = item.get("value", "")
        lx    = start_lx + i * legend_gap
        parts += [
            _rect(lx, legend_y, 12, 12, rx=2, fill=color),
            _text(lx + 16, legend_y + 10, lbl, fill=t["text"],
                  font_size="11", font_family=t["font"]),
        ]
        if val and not equal:
            parts.append(_text(lx + 16, legend_y + 22, str(val),
                               fill=t["muted"], font_size="10",
                               font_family=t["font"]))

    return "\n".join(parts), h + 50 + (cur_y - y)


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

_RENDERERS: dict = {
    "kpi_row":          _render_kpi_row,
    "bar_chart":        _render_bar_chart,
    "donut":            _render_donut,
    "stories":          _render_stories,
    "heatmap":          _render_heatmap,
    "divider":          _render_divider,
    "text":             _render_text_block,
    # AntV-parity types
    "process_flow":     _render_process_flow,
    "circular_flow":    _render_circular_flow,
    "staircase":        _render_staircase,
    "pyramid":          _render_pyramid,
    "snake_path":       _render_snake_path,
    "bubble_chain":     _render_bubble_chain,
    "timeline":         _render_timeline,
    "venn":             _render_venn,
    "comparison":       _render_comparison,
    "swot":             _render_swot,
    "matrix_2x2":       _render_matrix_2x2,
    "quadrant_circle":  _render_quadrant_circle,
    "card_grid":        _render_card_grid,
    "pill_list":        _render_pill_list,
    "wheel":            _render_wheel,
}


class InfographicRenderer:
    """
    Renders a data-driven infographic as a standalone SVG string.

    Usage::

        renderer = InfographicRenderer()
        svg = renderer.render(spec_dict)

    The ``theme`` field in the spec can be:
    - A preset name (str):  ``"aurora"`` | ``"midnight"`` | ``"carbon"`` | ``"sunset"`` | ``"emerald"``
    - A full custom dict with any subset of theme keys
    - A partial override:   ``{"preset": "midnight", "palette": ["#FF0", "#0FF"]}``
    """

    def render(self, spec: dict) -> str:
        t       = resolve_theme(spec.get("theme"))
        width   = int(spec.get("width", 900))
        cx      = float(_PAD_H)
        cw      = float(width - _PAD_H * 2)

        body_parts: list[str] = []
        cur_y = 0.0

        # Header
        header_svg, header_h = _render_header(spec, width, t)
        cur_y += header_h + _SEC_GAP

        # Sections
        for section in spec.get("sections", []):
            renderer = _RENDERERS.get(section.get("type", ""))
            if renderer is None:
                continue
            frag, consumed = renderer(section, cx, cur_y, cw, t)
            if frag:
                body_parts.append(frag)
            cur_y += consumed + _SEC_GAP

        total_h = int(cur_y + _PAD_V)

        # Build final SVG
        defs_svg = _build_defs(t, width)

        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg"'
            f' width="{width}" height="{total_h}"'
            f' viewBox="0 0 {width} {total_h}">',
            defs_svg,
            _rect(0, 0, width, total_h, fill=t["bg"]),
            header_svg,
            *body_parts,
            "</svg>",
        ]
        return "\n".join(lines)


def render_infographic(spec: dict) -> str:
    """Convenience wrapper: ``render_infographic(spec)`` → SVG string."""
    return InfographicRenderer().render(spec)
