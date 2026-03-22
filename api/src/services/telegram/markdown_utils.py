"""
Markdown to Telegram HTML converter.

Telegram's HTML mode supports: <b>, <i>, <u>, <s>, <code>, <pre>,
<a href="...">, <blockquote>, <pre><code class="language-xxx">.
Tables are not supported by Telegram — converted to <pre> blocks.
"""

import html
import re

# Telegram's per-message character limit
MAX_MESSAGE_LENGTH = 4096


def md_to_telegram_html(text: str) -> str:
    """
    Convert markdown text to Telegram-compatible HTML.

    Handles: fenced code blocks, tables (as pre), headings, blockquotes,
    unordered/ordered lists, horizontal rules, bold, italic, strikethrough,
    inline code, links, and images (as links).
    """
    if not text:
        return ""

    lines = text.split("\n")
    blocks: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # ── Fenced code block ─────────────────────────────────────────────
        fm = re.match(r"^```(\w*)\s*$", line)
        if fm:
            lang = fm.group(1)
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not re.match(r"^```\s*$", lines[i]):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            code_content = html.escape("\n".join(code_lines))
            if lang:
                blocks.append(f'<pre><code class="language-{html.escape(lang)}">{code_content}</code></pre>')
            else:
                blocks.append(f"<pre>{code_content}</pre>")
            continue

        # ── Table ─────────────────────────────────────────────────────────
        if "|" in line and i + 1 < len(lines) and re.match(r"^\|?[\s:\-|]+\|", lines[i + 1]):
            headers = _parse_cells(line)
            i += 2  # skip header + separator row
            rows: list[list[str]] = []
            while i < len(lines) and "|" in lines[i]:
                rows.append(_parse_cells(lines[i]))
                i += 1
            blocks.append(_table_to_pre(headers, rows))
            continue

        # ── Heading ───────────────────────────────────────────────────────
        hm = re.match(r"^(#{1,6})\s+(.+)$", line)
        if hm:
            content = _inline_to_html(hm.group(2))
            blocks.append(f"<b>{content}</b>")
            i += 1
            continue

        # ── Blockquote ────────────────────────────────────────────────────
        if re.match(r"^>\s?", line):
            bq_lines: list[str] = []
            while i < len(lines) and re.match(r"^>\s?", lines[i]):
                bq_lines.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            inner = "\n".join(_inline_to_html(line_text) for line_text in bq_lines)
            blocks.append(f"<blockquote>{inner}</blockquote>")
            continue

        # ── Unordered list ────────────────────────────────────────────────
        if re.match(r"^[-*+]\s+", line):
            items: list[str] = []
            while i < len(lines) and re.match(r"^[-*+]\s+", lines[i]):
                content = _inline_to_html(re.sub(r"^[-*+]\s+", "", lines[i]))
                items.append(f"• {content}")
                i += 1
            blocks.append("\n".join(items))
            continue

        # ── Ordered list ──────────────────────────────────────────────────
        if re.match(r"^\d+\.\s+", line):
            items = []
            num = 1
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i]):
                content = _inline_to_html(re.sub(r"^\d+\.\s+", "", lines[i]))
                items.append(f"{num}. {content}")
                i += 1
                num += 1
            blocks.append("\n".join(items))
            continue

        # ── Horizontal rule ───────────────────────────────────────────────
        if re.match(r"^[-*_]{3,}\s*$", line.strip()):
            blocks.append("──────────────────")
            i += 1
            continue

        # ── Blank line ────────────────────────────────────────────────────
        if line.strip() == "":
            blocks.append("")
            i += 1
            continue

        # ── Paragraph ─────────────────────────────────────────────────────
        p_lines: list[str] = []
        while (
            i < len(lines)
            and lines[i].strip() != ""
            and not re.match(r"^#{1,6}\s", lines[i])
            and not re.match(r"^[-*+]\s+", lines[i])
            and not re.match(r"^\d+\.\s+", lines[i])
            and not re.match(r"^>\s?", lines[i])
            and not re.match(r"^```", lines[i])
            and not re.match(r"^[-*_]{3,}\s*$", lines[i].strip())
            and "|" not in lines[i]
        ):
            p_lines.append(lines[i])
            i += 1
        if p_lines:
            blocks.append(" ".join(_inline_to_html(line_text) for line_text in p_lines))

    # Join blocks; collapse runs of blank lines to a single blank
    result_lines: list[str] = []
    prev_blank = False
    for block in blocks:
        if block == "":
            if not prev_blank:
                result_lines.append("")
            prev_blank = True
        else:
            result_lines.append(block)
            prev_blank = False

    return "\n".join(result_lines).strip()


def split_html_message(html_text: str, limit: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """
    Split an HTML message into chunks that fit within Telegram's character limit.

    Splits on block boundaries (double newlines) to avoid breaking tags.
    If a single block is longer than limit, it is split at the limit boundary.
    """
    if len(html_text) <= limit:
        return [html_text]

    parts: list[str] = []
    current = ""

    for block in html_text.split("\n"):
        candidate = (current + "\n" + block).lstrip("\n") if current else block
        if len(candidate) > limit:
            if current:
                parts.append(current.strip())
            # If the block itself is too long, hard-split it
            while len(block) > limit:
                parts.append(block[:limit])
                block = block[limit:]
            current = block
        else:
            current = candidate

    if current.strip():
        parts.append(current.strip())

    return parts


# ── Internal helpers ──────────────────────────────────────────────────────────


def _parse_cells(line: str) -> list[str]:
    cells = line.split("|")
    result = []
    for j, c in enumerate(cells):
        c = c.strip()
        if j == 0 and c == "":
            continue
        if j == len(cells) - 1 and c == "":
            continue
        result.append(c)
    return result


def _table_to_pre(headers: list[str], rows: list[list[str]]) -> str:
    """Render a markdown table as a monospace <pre> block."""
    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for j, cell in enumerate(row):
            if j < len(col_widths):
                col_widths[j] = max(col_widths[j], len(cell))

    def fmt_row(cells: list[str]) -> str:
        padded = []
        for j, w in enumerate(col_widths):
            cell = cells[j] if j < len(cells) else ""
            padded.append(cell.ljust(w))
        return " | ".join(padded)

    sep = "-+-".join("-" * w for w in col_widths)
    lines = [fmt_row(headers), sep]
    for row in rows:
        lines.append(fmt_row(row))

    return "<pre>" + html.escape("\n".join(lines)) + "</pre>"


def _inline_to_html(text: str) -> str:
    """Convert inline markdown elements to Telegram HTML."""
    if not text:
        return ""

    ph: list[str] = []
    s = text

    # Protect inline code (must come first)
    def protect_code(m: re.Match) -> str:
        ph.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"\x00{len(ph) - 1}\x00"

    s = re.sub(r"`([^`\n]+)`", protect_code, s)

    # Images → link with alt text (Telegram can't embed images inline)
    def protect_image(m: re.Match) -> str:
        alt, src = m.group(1), m.group(2)
        if re.match(r"^https?://", src, re.IGNORECASE):
            ph.append(f'<a href="{html.escape(src)}">{html.escape(alt or "image")}</a>')
        else:
            ph.append(html.escape(alt or ""))
        return f"\x00{len(ph) - 1}\x00"

    s = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", protect_image, s)

    # Links (safe protocols only)
    def protect_link(m: re.Match) -> str:
        label, href = m.group(1), m.group(2)
        if not re.match(r"^(https?://|mailto:|/)", href, re.IGNORECASE):
            ph.append(html.escape(label))
        else:
            ph.append(f'<a href="{html.escape(href)}">{html.escape(label)}</a>')
        return f"\x00{len(ph) - 1}\x00"

    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", protect_link, s)

    # Escape HTML entities in remaining plain text
    s = html.escape(s)

    # Bold
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"__(.+?)__", r"<b>\1</b>", s)
    # Italic
    s = re.sub(r"\*([^*\n]+)\*", r"<i>\1</i>", s)
    s = re.sub(r"_([^_\n\s][^_\n]*)_", r"<i>\1</i>", s)
    # Strikethrough
    s = re.sub(r"~~(.+?)~~", r"<s>\1</s>", s)

    # Restore placeholders
    s = re.sub(r"\x00(\d+)\x00", lambda m: ph[int(m.group(1))], s)
    return s
