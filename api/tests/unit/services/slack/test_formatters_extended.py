"""
Additional edge-case tests for Slack formatters.

The base test_formatters.py covers happy-path scenarios.
These tests cover boundaries, edge inputs, and specific behaviours
that the existing file does not exercise.
"""

import pytest

from src.services.slack.formatters import (
    SLACK_MAX_BLOCKS,
    SLACK_MAX_TEXT_LENGTH,
    chunk_blocks,
    clean_table_cell,
    convert_markdown_table_to_slack_blocks,
    create_slack_blocks,
    format_text_for_slack,
)

# ---------------------------------------------------------------------------
# format_text_for_slack — edge cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFormatTextForSlackMentions:
    def test_slack_user_id_wrapped_in_angle_brackets(self):
        result = format_text_for_slack("Hey @UABC123 can you help?")
        assert "<@UABC123>" in result

    def test_slack_workspace_user_id_wrapped(self):
        result = format_text_for_slack("Ping @WABC123 please")
        assert "<@WABC123>" in result

    def test_already_wrapped_mention_not_double_wrapped(self):
        result = format_text_for_slack("Hey <@UABC123> already wrapped")
        assert "<@UABC123>" in result
        assert "<<@" not in result

    def test_regular_email_not_converted(self):
        result = format_text_for_slack("Email user@example.com for help")
        assert "<@" not in result or "example.com" not in result


@pytest.mark.unit
class TestFormatTextForSlackCodePreservation:
    def test_inline_code_not_modified(self):
        result = format_text_for_slack("Use `**not bold**` here")
        assert "`**not bold**`" in result

    def test_fenced_code_block_not_modified(self):
        code = "```python\n**not_bold** = 1\n```"
        result = format_text_for_slack(f"before {code} after")
        assert code in result

    def test_bold_outside_code_still_converted(self):
        result = format_text_for_slack("**bold** and `code` and **more bold**")
        assert "*bold*" in result
        assert "*more bold*" in result
        assert "`code`" in result

    def test_empty_string_returns_empty(self):
        assert format_text_for_slack("") == ""


@pytest.mark.unit
class TestFormatTextForSlackAllSyntax:
    def test_all_header_levels_converted_to_bold(self):
        for level in range(1, 7):
            text = f"{'#' * level} Heading {level}"
            result = format_text_for_slack(text)
            assert f"*Heading {level}*" in result

    def test_double_underscore_bold(self):
        result = format_text_for_slack("__bold text__")
        assert "*bold text*" in result

    def test_numbered_list_converted_to_bullet(self):
        result = format_text_for_slack("1. First\n2. Second")
        assert "• First" in result
        assert "• Second" in result

    def test_dash_list_converted_to_bullet(self):
        result = format_text_for_slack("- Item A\n- Item B")
        assert "• Item A" in result
        assert "• Item B" in result

    def test_link_converted_to_slack_format(self):
        result = format_text_for_slack("[click here](https://example.com)")
        assert "<https://example.com|click here>" in result

    def test_no_stray_double_stars_remain(self):
        result = format_text_for_slack("**bold** and more **text**")
        assert "**" not in result


# ---------------------------------------------------------------------------
# clean_table_cell — edge cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCleanTableCell:
    def test_strips_backticks(self):
        assert clean_table_cell("`code`") == "code"

    def test_strips_underscores(self):
        assert clean_table_cell("_italic_") == "italic"

    def test_strips_asterisks(self):
        assert clean_table_cell("*bold*") == "bold"

    def test_link_text_extracted(self):
        assert clean_table_cell("[label](http://example.com)") == "label"

    def test_plain_text_unchanged(self):
        assert clean_table_cell("just text") == "just text"

    def test_whitespace_stripped(self):
        assert clean_table_cell("   hello   ") == "hello"

    def test_empty_string_stays_empty(self):
        assert clean_table_cell("") == ""

    def test_mixed_markers_all_removed(self):
        result = clean_table_cell("**`bold code`**")
        assert result == "bold code"


# ---------------------------------------------------------------------------
# convert_markdown_table_to_slack_blocks — edge cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConvertMarkdownTableToSlackBlocks:
    def test_empty_string_returns_empty_list(self):
        assert convert_markdown_table_to_slack_blocks("") == []

    def test_no_pipe_characters_returns_empty_list(self):
        assert convert_markdown_table_to_slack_blocks("just some text\nno pipes here") == []

    def test_headers_in_bold(self):
        # 2-col table → fields block (native Slack 2-col grid); key is bold in field text
        table = "| Name | Age |\n|------|-----|\n| Alice | 30 |"
        blocks = convert_markdown_table_to_slack_blocks(table)
        assert len(blocks) == 1
        assert "fields" in blocks[0]
        field_texts = [f["text"] for f in blocks[0]["fields"]]
        assert any("*Alice*" in t for t in field_texts)

    def test_separator_row_excluded_from_data(self):
        # 2-col table → fields; separator row must not appear in any field text
        table = "| A | B |\n|---|---|\n| 1 | 2 |"
        blocks = convert_markdown_table_to_slack_blocks(table)
        assert "fields" in blocks[0]
        all_text = " ".join(f["text"] for f in blocks[0]["fields"])
        assert "---" not in all_text

    def test_data_row_present(self):
        table = "| X |\n|---|\n| val |"
        blocks = convert_markdown_table_to_slack_blocks(table)
        assert "val" in blocks[0]["text"]["text"]

    def test_row_with_fewer_cells_padded(self):
        table = "| A | B | C |\n|---|---|---|\n| 1 | 2 |"
        blocks = convert_markdown_table_to_slack_blocks(table)
        # Should not raise; row is padded with empty strings
        assert len(blocks) == 1

    def test_block_type_is_section(self):
        table = "| H |\n|---|\n| v |"
        blocks = convert_markdown_table_to_slack_blocks(table)
        assert blocks[0]["type"] == "section"
        assert blocks[0]["text"]["type"] == "mrkdwn"

    def test_headers_only_no_data_returns_empty(self):
        # A table with only a header row and separator but no data rows → nothing to render
        table = "| Only | Headers |\n|------|---------|"
        blocks = convert_markdown_table_to_slack_blocks(table)
        assert blocks == []


# ---------------------------------------------------------------------------
# chunk_blocks — edge cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestChunkBlocks:
    def test_empty_list_returns_one_empty_chunk(self):
        result = chunk_blocks([])
        assert result == [[]]

    def test_exactly_at_limit_is_one_chunk(self):
        blocks = [{"type": "section"}] * SLACK_MAX_BLOCKS
        result = chunk_blocks(blocks)
        assert len(result) == 1

    def test_one_over_limit_splits_into_two(self):
        blocks = [{"type": "section"}] * (SLACK_MAX_BLOCKS + 1)
        result = chunk_blocks(blocks)
        assert len(result) == 2
        assert len(result[0]) == SLACK_MAX_BLOCKS
        assert len(result[1]) == 1

    def test_custom_max_blocks_respected(self):
        blocks = [{"type": "section"}] * 10
        result = chunk_blocks(blocks, max_blocks=3)
        assert len(result) == 4  # 3+3+3+1
        assert all(len(c) <= 3 for c in result)

    def test_total_blocks_preserved_across_chunks(self):
        blocks = [{"type": "section"}] * 73
        chunks = chunk_blocks(blocks, max_blocks=SLACK_MAX_BLOCKS)
        total = sum(len(c) for c in chunks)
        assert total == 73

    def test_single_block_returns_one_chunk(self):
        result = chunk_blocks([{"type": "divider"}])
        assert len(result) == 1
        assert result[0] == [{"type": "divider"}]


# ---------------------------------------------------------------------------
# create_slack_blocks — edge cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateSlackBlocksEdgeCases:
    def test_empty_string_returns_empty_list(self):
        result = create_slack_blocks("")
        assert result == []

    def test_whitespace_only_returns_empty_list(self):
        result = create_slack_blocks("   \n\n   ")
        assert result == []

    def test_horizontal_rule_produces_divider(self):
        result = create_slack_blocks("Before\n\n---\n\nAfter")
        types = [b["type"] for b in result]
        assert "divider" in types

    def test_multiline_text_produces_section(self):
        result = create_slack_blocks("Line one\nLine two")
        assert any(b["type"] == "section" for b in result)

    def test_all_section_texts_are_strings(self):
        result = create_slack_blocks("Some text here")
        for block in result:
            if block.get("type") == "section":
                assert isinstance(block["text"]["text"], str)

    def test_mrkdwn_type_on_sections(self):
        result = create_slack_blocks("Hello world")
        for block in result:
            if block.get("type") == "section":
                assert block["text"]["type"] == "mrkdwn"

    def test_very_long_text_splits_into_multiple_blocks(self):
        long_text = "word " * (SLACK_MAX_TEXT_LENGTH // 4)
        result = create_slack_blocks(long_text)
        assert len(result) >= 2

    def test_each_block_text_within_limit(self):
        long_text = "a" * (SLACK_MAX_TEXT_LENGTH * 3)
        result = create_slack_blocks(long_text)
        for block in result:
            if block.get("type") == "section" and block.get("text"):
                assert len(block["text"]["text"]) <= SLACK_MAX_TEXT_LENGTH
