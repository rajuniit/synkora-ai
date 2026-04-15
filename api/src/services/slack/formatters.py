"""Slack message formatting utilities."""

import logging
import re
import uuid

logger = logging.getLogger(__name__)

# Slack limits
SLACK_MAX_TEXT_LENGTH = 3000
SLACK_MAX_BLOCKS = 50


def format_text_for_slack(text: str) -> str:
    """Format markdown text for Slack's mrkdwn format.

    Converts common markdown formatting to Slack's format:
    - **bold** -> *bold*
    - _italic_ -> _italic_
    - # Headers -> *Headers*
    - [link](url) -> <url|link>
    - Lists with bullet points

    Args:
        text: Raw markdown text to convert

    Returns:
        Text formatted for Slack's mrkdwn format
    """
    logger.debug("Converting markdown to Slack format")

    # Step 1: Protect code blocks with UUID placeholders
    code_map = {}

    def extract_code_to_token(match: re.Match) -> str:
        token = f"CODEBLOCK_{uuid.uuid4().hex}"
        code_map[token] = match.group(0)
        return token

    # Extract both fenced code blocks and inline code
    text = re.sub(r"(```[\s\S]+?```|`[^`\n]+?`)", extract_code_to_token, text)

    # Step 2: Convert markdown formatting

    # Convert @USER_ID patterns to Slack mentions <@USER_ID>
    # Matches @U followed by alphanumeric (Slack user IDs) or @W (workspace user IDs)
    # Only convert if not already in angle brackets
    text = re.sub(r"(?<!<)@([UW][A-Z0-9]+)(?!>)", r"<@\1>", text)

    # Headers -> Bold
    text = re.sub(r"^\s*#{1,6}\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)

    # Bold: **text** -> *text*
    text = re.sub(r"\*\*([^*]+)\*\*", r"*\1*", text)
    text = re.sub(r"__(.+?)__", r"*\1*", text)

    # Italic: Keep _text_ as is (Slack uses underscores for italic)
    # Don't convert single asterisks - in Slack *text* means bold, not italic

    # Nested lists (2+ spaces)
    # Use a non-capturing group for the bullet marker
    text = re.sub(r"^\s{2,}(?:[-*]|\d+[.)])\s+", "  • ", text, flags=re.MULTILINE)

    # Also handle the Subitem pattern specifically if above fails
    # We need to handle indented dashes that might not be caught by above regex
    text = re.sub(r"^\s+-\s+(.*)$", r"  • \1", text, flags=re.MULTILINE)

    # Lists
    text = re.sub(r"^\s*\d+\.\s+", "• ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.MULTILINE)

    # Normalize indentation for sub-items
    text = re.sub(r"^\s+•", "  •", text, flags=re.MULTILINE)

    # Links: [text](url) -> <url|text>
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<\2|\1>", text)

    # Clean up double stars
    text = text.replace("**", "*")

    # Step 3: Restore code blocks
    for token, original_code in code_map.items():
        text = text.replace(token, original_code)

    logger.debug("Markdown conversion complete")
    return text


def clean_table_cell(text: str) -> str:
    """Clean markdown from table cells for display.

    Args:
        text: Raw cell content with potential markdown

    Returns:
        Cleaned text suitable for Slack
    """
    # Remove bold/italic/code markers
    text = re.sub(r"[*_`]", "", text)
    # Remove links [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    return text.strip()


def convert_markdown_table_to_slack_blocks(markdown_table: str) -> list:
    """Convert markdown table to Slack blocks (simplified version).

    Since Slack's table block support is limited, this converts tables
    to formatted text blocks.

    Args:
        markdown_table: Markdown table string

    Returns:
        List of Slack blocks
    """
    lines = [line.strip() for line in markdown_table.strip().split("\n")]

    headers = []
    data = []

    for line in lines:
        if "|" not in line:
            continue

        cells = [c.strip() for c in line.split("|")]

        # Handle edge pipes
        if line.startswith("|") and cells:
            cells.pop(0)
        if line.endswith("|") and cells:
            cells.pop()

        # Check if separator line
        if all(re.match(r"^[-:\s]+$", c) for c in cells):
            continue

        clean_cells = [clean_table_cell(c) for c in cells]

        if not clean_cells:
            continue

        if not headers:
            headers = clean_cells
        else:
            if len(clean_cells) < len(headers):
                clean_cells += [""] * (len(headers) - len(clean_cells))
            data.append(clean_cells[: len(headers)])

    if not headers:
        return []

    # Format as text block with headers in bold
    table_text = []
    table_text.append("*" + " | ".join(headers) + "*")
    table_text.append("—" * (len(" | ".join(headers))))

    for row in data:
        table_text.append(" | ".join(row))

    return [{"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(table_text)}}]


def create_slack_blocks(text: str) -> list:
    """Parse text and create Slack Block Kit blocks.

    Args:
        text: Raw text with markdown formatting

    Returns:
        List of Slack Block Kit blocks
    """
    blocks = []

    # Extract tables first using regex
    # This regex looks for a block that looks like a table:
    # | ... |
    # | - |
    # | ... |
    table_pattern = r"((?:^|\n)(?:\|[^\n]+\|\s*\n)(?:\|[-:| ]+\|\s*\n)(?:\|[^\n]+\|\s*(?:\n|$))+)"

    # Split text into parts (tables and non-tables)
    # The capturing group in split ensures tables are included in the list
    parts = re.split(table_pattern, text, flags=re.MULTILINE)

    for part in parts:
        if not part.strip():
            continue

        # Check if this is a table (naively checks if it starts with pipe or has pipe in second line)
        lines = part.strip().split("\n")
        is_table = False
        if len(lines) >= 2:
            # Check first line for pipe
            if re.match(r"^\s*\|", lines[0]) or re.match(r"^\s*\|?[-:|\s]+\|?", lines[1]):
                is_table = True

        if is_table:
            table_blocks = convert_markdown_table_to_slack_blocks(part)
            blocks.extend(table_blocks)
            if table_blocks:
                blocks.append({"type": "divider"})
            continue

        # Handle horizontal rules
        text_with_markers = re.sub(r"\n\s*([-*]{3,})\s*\n", "\n\n<HR_DIVIDER>\n\n", part)

        # Split into sections
        sections = re.split(r"(?:\r\n|\n){2,}", text_with_markers)

        for section in sections:
            if not section.strip():
                continue

            if section.strip() == "<HR_DIVIDER>":
                blocks.append({"type": "divider"})
                continue

            # Format the section
            formatted_section = format_text_for_slack(section)

            # Handle long sections
            if len(formatted_section) > SLACK_MAX_TEXT_LENGTH:
                # Split into chunks
                chunks = re.split(r"([.!?]\s+|\n)", formatted_section)
                current_chunk = ""

                for chunk in chunks:
                    # Slack block text limit is 3000
                    if len(current_chunk) + len(chunk) > SLACK_MAX_TEXT_LENGTH:
                        if current_chunk:
                            blocks.append(
                                {"type": "section", "text": {"type": "mrkdwn", "text": current_chunk.strip()}}
                            )
                        current_chunk = chunk
                        # If a single chunk is still too long, we need to split it by chars
                        while len(current_chunk) > SLACK_MAX_TEXT_LENGTH:
                            blocks.append(
                                {
                                    "type": "section",
                                    "text": {"type": "mrkdwn", "text": current_chunk[:SLACK_MAX_TEXT_LENGTH]},
                                }
                            )
                            current_chunk = current_chunk[SLACK_MAX_TEXT_LENGTH:]
                    else:
                        current_chunk += chunk

                if current_chunk:
                    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": current_chunk.strip()}})
            else:
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": formatted_section}})

    return blocks


def chunk_blocks(blocks: list, max_blocks: int = SLACK_MAX_BLOCKS) -> list:
    """Split blocks into chunks if they exceed Slack's limit.

    Args:
        blocks: List of Block Kit blocks
        max_blocks: Maximum blocks per message (Slack limit is 50)

    Returns:
        List of block chunks
    """
    if len(blocks) <= max_blocks:
        return [blocks]

    chunks = []
    current_chunk = []

    for block in blocks:
        current_chunk.append(block)

        if len(current_chunk) >= max_blocks:
            chunks.append(current_chunk)
            current_chunk = []

    if current_chunk:
        chunks.append(current_chunk)

    return chunks
