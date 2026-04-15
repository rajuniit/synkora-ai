"""Unit tests for TextProcessor."""

from unittest.mock import MagicMock, patch

import pytest

from src.services.knowledge_base.text_processor import TextProcessor


@pytest.fixture
def processor():
    return TextProcessor()


@pytest.mark.unit
class TestCleanText:
    def test_collapses_extra_whitespace(self, processor):
        result = processor.clean_text("hello   world")
        assert result == "hello world"

    def test_strips_leading_trailing_whitespace(self, processor):
        result = processor.clean_text("  hello world  ")
        assert result == "hello world"

    def test_removes_special_characters(self, processor):
        result = processor.clean_text("hello@world#test$")
        assert "@" not in result
        assert "#" not in result
        assert "$" not in result

    def test_preserves_basic_punctuation(self, processor):
        text = "Hello, world! How are you? I'm fine; (yes) it's great."
        result = processor.clean_text(text)
        assert "," in result
        assert "!" in result
        assert "?" in result
        assert ";" in result

    def test_empty_string_returns_empty(self, processor):
        assert processor.clean_text("") == ""

    def test_newline_collapsed_to_space(self, processor):
        result = processor.clean_text("line1\nline2")
        assert "\n" not in result
        assert result == "line1 line2"


@pytest.mark.unit
class TestTruncateText:
    def test_short_text_unchanged(self, processor):
        text = "short text"
        assert processor.truncate_text(text, 100) == text

    def test_exactly_max_length_unchanged(self, processor):
        text = "12345"
        assert processor.truncate_text(text, 5) == text

    def test_truncates_long_text(self, processor):
        text = "a" * 200
        result = processor.truncate_text(text, 50)
        assert len(result) == 50

    def test_appends_suffix(self, processor):
        text = "a" * 100
        result = processor.truncate_text(text, 20)
        assert result.endswith("...")

    def test_custom_suffix(self, processor):
        text = "a" * 100
        result = processor.truncate_text(text, 20, suffix=" [more]")
        assert result.endswith(" [more]")

    def test_empty_string_unchanged(self, processor):
        assert processor.truncate_text("", 10) == ""


@pytest.mark.unit
class TestRemoveCodeBlocks:
    def test_removes_fenced_code_block(self, processor):
        text = "Before\n```python\nprint('hi')\n```\nAfter"
        result = processor.remove_code_blocks(text)
        assert "```" not in result
        assert "print('hi')" not in result
        assert "Before" in result
        assert "After" in result

    def test_removes_inline_code(self, processor):
        text = "Use `pip install foo` to install"
        result = processor.remove_code_blocks(text)
        assert "`pip install foo`" not in result
        assert "Use" in result

    def test_multiple_code_blocks_removed(self, processor):
        text = "```js\nalert(1)\n``` then ```py\nprint(2)\n```"
        result = processor.remove_code_blocks(text)
        assert "alert" not in result
        assert "print" not in result

    def test_no_code_blocks_unchanged(self, processor):
        text = "Just plain text."
        assert processor.remove_code_blocks(text) == "Just plain text."

    def test_empty_string_returns_empty(self, processor):
        assert processor.remove_code_blocks("") == ""


@pytest.mark.unit
class TestExtractMetadataFromText:
    def test_extracts_title_from_first_line(self, processor):
        text = "My Document Title\nThis is the body."
        meta = processor.extract_metadata_from_text(text)
        assert meta.get("title") == "My Document Title"

    def test_long_first_line_not_used_as_title(self, processor):
        # First line > 100 chars should not be used as title
        text = ("x" * 101) + "\nBody text"
        meta = processor.extract_metadata_from_text(text)
        assert "title" not in meta

    def test_extracts_iso_dates(self, processor):
        text = "Published on 2024-01-15 and updated 2024-03-20."
        meta = processor.extract_metadata_from_text(text)
        assert "dates" in meta
        assert "2024-01-15" in meta["dates"]
        assert "2024-03-20" in meta["dates"]

    def test_extracts_slash_dates(self, processor):
        text = "Invoice dated 1/15/2024."
        meta = processor.extract_metadata_from_text(text)
        assert "dates" in meta
        assert "1/15/2024" in meta["dates"]

    def test_extracts_urls(self, processor):
        text = "Visit https://example.com and http://test.org for more."
        meta = processor.extract_metadata_from_text(text)
        assert "urls" in meta
        assert any("example.com" in u for u in meta["urls"])

    def test_no_dates_no_key(self, processor):
        meta = processor.extract_metadata_from_text("No dates here")
        assert "dates" not in meta

    def test_no_urls_no_key(self, processor):
        meta = processor.extract_metadata_from_text("No URLs here")
        assert "urls" not in meta


@pytest.mark.unit
class TestExtractKeywords:
    def test_returns_list(self, processor):
        result = processor.extract_keywords("The quick brown fox jumps over the lazy dog")
        assert isinstance(result, list)

    def test_filters_stop_words(self, processor):
        text = "the quick brown fox"
        result = processor.extract_keywords(text)
        assert "the" not in result

    def test_respects_max_keywords(self, processor):
        text = "apple banana cherry date elderberry fig grape honeydew kiwi lemon mango nectarine"
        result = processor.extract_keywords(text, max_keywords=5)
        assert len(result) <= 5

    def test_short_words_excluded(self, processor):
        # Words < 3 chars should be excluded by the regex \b[a-z]{3,}\b
        text = "is it an go to do by"
        result = processor.extract_keywords(text)
        assert "is" not in result
        assert "it" not in result

    def test_returns_most_frequent_first(self, processor):
        # "apple" appears 3 times, "banana" once
        text = "apple apple apple banana"
        result = processor.extract_keywords(text, max_keywords=2)
        assert result[0] == "apple"

    def test_empty_text_returns_empty(self, processor):
        result = processor.extract_keywords("")
        assert result == []


@pytest.mark.unit
class TestSplitLargeText:
    def test_returns_non_empty_list(self, processor):
        text = "Hello world. This is a sentence. Another one here."
        chunks = processor._split_large_text(text, chunk_size=30, chunk_overlap=5)
        assert len(chunks) >= 1
        assert all(c.strip() for c in chunks)

    def test_short_text_returns_single_chunk(self, processor):
        text = "short"
        chunks = processor._split_large_text(text, chunk_size=1000, chunk_overlap=0)
        assert chunks == ["short"]

    def test_empty_text_returns_fallback(self, processor):
        # Empty text falls back to returning the original (empty) string as single item
        chunks = processor._split_large_text("   ", chunk_size=100, chunk_overlap=0)
        # Returns either empty list or list with whitespace; either way, at most 1 item
        assert len(chunks) <= 1

    def test_respects_chunk_size_upper_bound(self, processor):
        text = "word " * 200
        chunk_size = 50
        chunks = processor._split_large_text(text, chunk_size=chunk_size, chunk_overlap=0)
        for chunk in chunks:
            # Each chunk should be at most chunk_size + a small boundary tolerance
            assert len(chunk) <= chunk_size + 10

    def test_returns_list_type(self, processor):
        text = "some text here"
        result = processor._split_large_text(text, chunk_size=100, chunk_overlap=0)
        assert isinstance(result, list)


@pytest.mark.unit
class TestChunkText:
    def test_empty_text_returns_empty_list(self, processor):
        with patch("src.services.knowledge_base.text_processor.SmartChunker") as mock_chunker_cls:
            result = processor.chunk_text("", chunk_size=500)
        assert result == []

    def test_zero_chunk_size_returns_empty(self, processor):
        with patch("src.services.knowledge_base.text_processor.SmartChunker") as mock_chunker_cls:
            result = processor.chunk_text("some text", chunk_size=0)
        assert result == []

    def test_delegates_to_smart_chunker(self, processor):
        expected = [{"text": "chunk1", "index": 0}]
        with patch("src.services.knowledge_base.text_processor.SmartChunker") as mock_chunker_cls:
            mock_instance = MagicMock()
            mock_instance.chunk_text.return_value = expected
            mock_chunker_cls.return_value = mock_instance

            result = processor.chunk_text("some text", chunk_size=500)

        assert result == expected
        mock_instance.chunk_text.assert_called_once()

    def test_passes_metadata_to_chunker(self, processor):
        meta = {"source": "test.pdf"}
        with patch("src.services.knowledge_base.text_processor.SmartChunker") as mock_chunker_cls:
            mock_instance = MagicMock()
            mock_instance.chunk_text.return_value = []
            mock_chunker_cls.return_value = mock_instance

            processor.chunk_text("text", chunk_size=500, metadata=meta)

        call_kwargs = mock_instance.chunk_text.call_args
        assert call_kwargs[1]["metadata"] == meta or call_kwargs[0][1] == meta
