"""Slack message formatting utilities."""

import logging
import re
import uuid

logger = logging.getLogger(__name__)

SLACK_MAX_TEXT_LENGTH = 3000
SLACK_MAX_BLOCKS = 50

# Auto-inject emojis for common status / value words in table cells.
# Checked against the lowercased cell value — first match wins.
_STATUS_EMOJI: list[tuple[str, str]] = [
    ("locked", ":lock:"),
    ("unlocked", ":unlock:"),
    ("connected", ":large_green_circle:"),
    ("disconnected", ":red_circle:"),
    ("active", ":large_green_circle:"),
    ("inactive", ":white_circle:"),
    ("completed", ":white_check_mark:"),
    ("failed", ":x:"),
    ("pending", ":hourglass_flowing_sand:"),
    ("in progress", ":arrows_counterclockwise:"),
    ("good", ":star:"),
    ("excellent", ":star2:"),
    ("poor", ":thumbsdown:"),
    ("100%", ":battery:"),
    ("success", ":white_check_mark:"),
    ("error", ":x:"),
    ("warning", ":warning:"),
]


def _apply_emoji_status(text: str) -> str:
    """Prepend a relevant emoji when a cell value matches a known status word."""
    lower = text.strip().lower()
    for keyword, emoji in _STATUS_EMOJI:
        if lower == keyword or lower.startswith(keyword):
            return f"{emoji} {text}"
    return text


def format_text_for_slack(text: str) -> str:
    """Convert markdown text to Slack mrkdwn format.

    Used as the plain-text fallback for Block Kit messages and for
    direct Slack tool calls (slack_tools.py).
    """
    logger.debug("Converting markdown to Slack format")

    # --- Protect code blocks from subsequent transformations ---
    code_map: dict[str, str] = {}

    def _extract_code(match: re.Match) -> str:
        token = f"CODEBLOCK_{uuid.uuid4().hex}"
        code_map[token] = match.group(0)
        return token

    text = re.sub(r"(```[\s\S]+?```|`[^`\n]+?`)", _extract_code, text)

    # --- Clean HTML artifacts the LLM sometimes emits ---
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?p\s*/?>", "\n", text, flags=re.IGNORECASE)

    # --- Convert @USER_ID → Slack mention ---
    text = re.sub(r"(?<!<)@([UW][A-Z0-9]+)(?!>)", r"<@\1>", text)

    # --- Headers → bold (H1/H2 get header blocks in create_slack_blocks) ---
    text = re.sub(r"^\s*#{1,6}\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)

    # --- Bold ---
    text = re.sub(r"\*\*([^*]+)\*\*", r"*\1*", text)
    text = re.sub(r"__(.+?)__", r"*\1*", text)

    # --- Lists (nested first, then top-level) ---
    text = re.sub(r"^\s{2,}(?:[-*]|\d+[.)])\s+", "  • ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s+-\s+(.*)$", r"  • \1", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "• ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s+•", "  •", text, flags=re.MULTILINE)

    # --- Links: [text](url) → <url|text> ---
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<\2|\1>", text)

    # --- Clean up stray double-stars ---
    text = text.replace("**", "*")

    # --- Restore code blocks ---
    for token, original in code_map.items():
        text = text.replace(token, original)

    logger.debug("Markdown conversion complete")
    return text


def clean_table_cell(text: str) -> str:
    """Sanitise a markdown table cell value for display in Slack."""
    # HTML line breaks → space (common LLM table artifact)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    # Strip broken image references like ![Profile Picture] or ![alt](non-http-url)
    text = re.sub(r"!\[([^\]]*)\](?:\([^)]*\))?", r"\1", text)
    # Strip markdown bold / italic / code markers
    text = re.sub(r"[*_`]", "", text)
    # Collapse markdown links to their display text
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    return text.strip()


def convert_markdown_table_to_slack_blocks(markdown_table: str) -> list:
    """Convert a markdown table to Slack Block Kit blocks.

    2-column (key | value) tables are rendered using section *fields* — Slack's
    native two-column grid, which looks far better than pipe-separated plain text.

    Multi-column tables fall back to a monospaced-style text block with a bold
    header row and unicode box-drawing separators.
    """
    lines = [line.strip() for line in markdown_table.strip().split("\n")]

    headers: list[str] = []
    data: list[list[str]] = []

    for line in lines:
        if "|" not in line:
            continue

        cells = [c.strip() for c in line.split("|")]
        if line.startswith("|") and cells:
            cells.pop(0)
        if line.endswith("|") and cells:
            cells.pop()

        # Separator row (---|---) → skip
        if cells and all(re.match(r"^[-:\s]+$", c) for c in cells if c):
            continue

        clean_cells = [clean_table_cell(c) for c in cells]
        if not any(clean_cells):
            continue

        if not headers:
            headers = clean_cells
        else:
            if len(clean_cells) < len(headers):
                clean_cells += [""] * (len(headers) - len(clean_cells))
            data.append(clean_cells[: len(headers)])

    if not headers or not data:
        return []

    blocks: list[dict] = []

    if len(headers) == 2:
        # ── Key-value table → section fields (native Slack 2-col grid) ──────
        fields = []
        for row in data:
            key = row[0] if row else ""
            val = _apply_emoji_status(row[1] if len(row) > 1 else "")
            if key:
                # Truncate very long values so they don't overflow a field
                if len(val) > 300:
                    val = val[:297] + "…"
                fields.append({"type": "mrkdwn", "text": f"*{key}*\n{val}"})

        # Slack allows max 10 fields per section block
        for i in range(0, len(fields), 10):
            chunk = fields[i : i + 10]
            blocks.append({"type": "section", "fields": chunk})
            if i + 10 < len(fields):
                blocks.append({"type": "divider"})

    else:
        # ── Multi-column table → formatted text block ─────────────────────
        col_widths = [len(h) for h in headers]
        for row in data:
            for j, cell in enumerate(row):
                if j < len(col_widths):
                    col_widths[j] = max(col_widths[j], len(cell))

        def _fmt_row(cells: list[str], bold: bool = False) -> str:
            parts = []
            for j, cell in enumerate(cells):
                w = col_widths[j] if j < len(col_widths) else len(cell)
                padded = cell.ljust(w)
                parts.append(f"*{padded}*" if bold else padded)
            return " │ ".join(parts)

        separator = "─" * min(sum(col_widths) + 3 * (len(headers) - 1), 80)
        header_line = _fmt_row(headers, bold=True)
        current_lines = [header_line, separator]

        for row in data:
            row_line = _fmt_row(row)
            candidate = "\n".join(current_lines + [row_line])
            if len(candidate) > SLACK_MAX_TEXT_LENGTH:
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(current_lines)}})
                blocks.append({"type": "divider"})
                current_lines = [header_line, separator, row_line]
            else:
                current_lines.append(row_line)

        if current_lines:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(current_lines)}})

    return blocks


def _image_block(alt: str, url: str) -> dict:
    return {"type": "image", "image_url": url, "alt_text": alt or "image"}


def create_slack_blocks(text: str) -> list:
    """Parse raw LLM markdown and produce Slack Block Kit blocks.

    Improvements over plain text:
    - 2-col markdown tables → section fields (native Slack grid)
    - Multi-col tables      → bold header + unicode separator rows
    - H1/H2 headings        → header blocks (larger, prominent title)
    - H3-H6 headings        → bold section text
    - ![alt](url) images    → inline image blocks (actually displayed)
    - <br> tags             → newlines (not literal HTML)
    - Status values         → auto-prefixed with relevant emoji
    """
    blocks: list[dict] = []

    # ── Pre-pass: extract markdown images so they survive table splitting ───
    # NOTE: <br> is intentionally NOT replaced here — doing so before table splitting
    # would break multi-value cells like "Name <br> Email: x". clean_table_cell()
    # replaces <br> with a space inside tables; format_text_for_slack() replaces
    # it with \n in regular text sections. Both run after the table split below.
    # Replace ![alt](url) with a sentinel; we'll emit image blocks for each.
    _img_sentinel = "SLACK_IMG_"
    _img_map: dict[str, tuple[str, str]] = {}

    def _extract_image(m: re.Match) -> str:
        key = f"{_img_sentinel}{uuid.uuid4().hex}"
        _img_map[key] = (m.group(1), m.group(2))
        return f"\n\n{key}\n\n"  # isolated paragraph so it becomes its own section

    text = re.sub(r"!\[([^\]]*)\]\((https?://[^)\s]+)\)", _extract_image, text)

    # ── Split on markdown tables ─────────────────────────────────────────────
    # Matches both pipe-surrounded (|col|col|) and bare (col | col) table styles.
    # Requires: header row with |, then a separator line (---|--- or |---|---|), then data rows.
    table_pattern = (
        r"((?:^|\n)"
        r"[^\n]*\|[^\n]*\n"  # header row — any line containing |
        r"[ \t]*\|?[ \t]*[-:]+[-| \t:]*\n"  # separator — ---|--- or |---|---|
        r"(?:[^\n]*\|[^\n]*\s*(?:\n|$))+"  # 1+ data rows
        r")"
    )
    parts = re.split(table_pattern, text, flags=re.MULTILINE)

    for part in parts:
        if not part.strip():
            continue

        # ── Is this chunk a table? ───────────────────────────────────────────
        lines = part.strip().split("\n")
        is_table = (
            len(lines) >= 3 and "|" in lines[0] and re.match(r"^[ \t]*\|?[ \t]*[-:]+[-| \t:]*$", lines[1].strip())
        )

        if is_table:
            table_blocks = convert_markdown_table_to_slack_blocks(part)
            blocks.extend(table_blocks)
            if table_blocks:
                blocks.append({"type": "divider"})
            continue

        # ── Non-table: replace HR markers, split into paragraphs ────────────
        part = re.sub(r"\n\s*([-*]{3,})\s*\n", "\n\n<HR_DIVIDER>\n\n", part)
        sections = re.split(r"(?:\r\n|\n){2,}", part)

        for section in sections:
            stripped = section.strip()
            if not stripped:
                continue

            # Divider
            if stripped == "<HR_DIVIDER>":
                blocks.append({"type": "divider"})
                continue

            # ── Image sentinel ───────────────────────────────────────────────
            if stripped in _img_map:
                alt, url = _img_map[stripped]
                blocks.append(_image_block(alt, url))
                continue

            # ── Heading block (H1/H2 → header block; H3-H6 → bold text) ────
            heading_match = re.match(r"^\s*(#{1,6})\s+(.+)$", stripped)
            if heading_match:
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                # Strip any inline markdown from the heading text
                heading_text = re.sub(r"\*\*?([^*]+)\*\*?", r"\1", heading_text)
                if level <= 2 and len(heading_text) <= 150:
                    blocks.append(
                        {
                            "type": "header",
                            "text": {"type": "plain_text", "text": heading_text, "emoji": True},
                        }
                    )
                else:
                    blocks.append(
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": f"*{heading_text}*"},
                        }
                    )
                continue

            # ── Regular text section ─────────────────────────────────────────
            formatted = format_text_for_slack(section)

            if len(formatted) > SLACK_MAX_TEXT_LENGTH:
                chunks = re.split(r"([.!?]\s+|\n)", formatted)
                current = ""
                for chunk in chunks:
                    if len(current) + len(chunk) > SLACK_MAX_TEXT_LENGTH:
                        if current:
                            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": current.strip()}})
                        current = chunk
                        while len(current) > SLACK_MAX_TEXT_LENGTH:
                            blocks.append(
                                {
                                    "type": "section",
                                    "text": {"type": "mrkdwn", "text": current[:SLACK_MAX_TEXT_LENGTH]},
                                }
                            )
                            current = current[SLACK_MAX_TEXT_LENGTH:]
                    else:
                        current += chunk
                if current:
                    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": current.strip()}})
            else:
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": formatted}})

    return blocks


def chunk_blocks(blocks: list, max_blocks: int = SLACK_MAX_BLOCKS) -> list:
    """Split a block list into chunks that fit within Slack's 50-block limit."""
    if len(blocks) <= max_blocks:
        return [blocks]

    chunks: list[list] = []
    current: list = []
    for block in blocks:
        current.append(block)
        if len(current) >= max_blocks:
            chunks.append(current)
            current = []

    if current:
        chunks.append(current)

    return chunks
