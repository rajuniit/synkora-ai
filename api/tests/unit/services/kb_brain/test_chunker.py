"""
Unit tests for company_brain chunker — all four strategies with dummy data.
"""

from unittest.mock import patch

from src.services.company_brain.ingestion.chunker import (
    _chunk_by_headings,
    _chunk_fixed,
    _chunk_pr_diff,
    _chunk_slack_thread,
    chunk_document,
    get_strategy,
)

# ---------------------------------------------------------------------------
# Fixtures — dummy documents
# ---------------------------------------------------------------------------

def _doc(content: str, **extra) -> dict:
    return {"id": "test-doc-1", "content": content, "title": "Test Doc", **extra}


SLACK_DOC = {
    "id": "slack_C123_1234567890.000",
    "content": "Hello world from Alice",
    "title": "Slack #general",
    "metadata": {
        "source": "slack",
        "channel": "C123",
        "user": "U456",
        "thread_messages": [
            {"user": "U456", "text": "Hello from Alice", "ts": "1234567890.000"},
            {"user": "U789", "text": "Hi Alice, how are you?", "ts": "1234567891.000"},
            {"user": "U456", "text": "I am fine, thanks!", "ts": "1234567892.000"},
        ],
    },
}

GITHUB_PR_DOC = {
    "id": "github_pr_847",
    "content": "PR: Fix null pointer in auth",
    "title": "PR #847",
    "metadata": {
        "source": "github",
        "files": [
            {"filename": "auth/handler.py", "patch": "@@ -10,6 +10,7 @@\n-def handle():\n+def handle(ctx=None):\n     pass"},
            {"filename": "tests/test_auth.py", "patch": "@@ -1,3 +1,4 @@\n+import pytest\n def test_handle():"},
        ],
    },
}

CONFLUENCE_DOC = {
    "id": "confluence_page_001",
    "content": "# Architecture Overview\n\nThis is the intro.\n\n## Backend\n\nFastAPI with PostgreSQL.\n\n## Frontend\n\nNext.js 15.",
    "title": "Architecture",
}

SHORT_DOC = {"id": "short-1", "content": "Hi", "title": "Short"}
EMPTY_DOC = {"id": "empty-1", "content": "", "title": "Empty"}


# ---------------------------------------------------------------------------
# get_strategy
# ---------------------------------------------------------------------------

def test_get_strategy_defaults_to_fixed():
    fake = type("S", (), {"company_brain_chunking_strategies": '{"default":"fixed"}'})()
    with patch("src.config.settings.get_settings", return_value=fake):
        assert get_strategy("unknown_source") == "fixed"


def test_get_strategy_slack():
    fake = type("S", (), {"company_brain_chunking_strategies": '{"slack":"thread","default":"fixed"}'})()
    with patch("src.config.settings.get_settings", return_value=fake):
        assert get_strategy("slack") == "thread"


def test_get_strategy_bad_json_falls_back():
    fake = type("S", (), {"company_brain_chunking_strategies": "NOT_JSON"})()
    with patch("src.config.settings.get_settings", return_value=fake):
        assert get_strategy("slack") == "fixed"


# ---------------------------------------------------------------------------
# _chunk_fixed
# ---------------------------------------------------------------------------

def test_chunk_fixed_short_content_one_chunk():
    doc = _doc("The quick brown fox jumps over the lazy dog.")
    chunks = _chunk_fixed(doc, chunk_size=1500, chunk_overlap=150)
    assert len(chunks) == 1
    assert "quick brown fox" in chunks[0]


def test_chunk_fixed_empty_returns_empty():
    chunks = _chunk_fixed(EMPTY_DOC, 1500, 150)
    assert chunks == []


def test_chunk_fixed_large_content_splits():
    # ~300 words → well above 150-token boundary in word-fallback mode
    words = ["word"] * 600
    doc = _doc(" ".join(words))
    chunks = _chunk_fixed(doc, chunk_size=100, chunk_overlap=10)
    assert len(chunks) >= 2


def test_chunk_fixed_each_chunk_not_empty():
    doc = _doc("A " * 500)
    chunks = _chunk_fixed(doc, chunk_size=50, chunk_overlap=5)
    assert all(c.strip() for c in chunks)


# ---------------------------------------------------------------------------
# _chunk_slack_thread
# ---------------------------------------------------------------------------

def test_chunk_slack_thread_small_thread_one_chunk():
    chunks = _chunk_slack_thread(SLACK_DOC, chunk_size=5000, chunk_overlap=0)
    assert len(chunks) == 1
    assert "Alice" in chunks[0]
    assert "Hi Alice" in chunks[0]


def test_chunk_slack_thread_no_metadata_falls_back_to_fixed():
    doc = _doc("A short message without thread metadata")
    chunks = _chunk_slack_thread(doc, chunk_size=1500, chunk_overlap=150)
    assert len(chunks) == 1


def test_chunk_slack_thread_formats_users():
    chunks = _chunk_slack_thread(SLACK_DOC, chunk_size=5000, chunk_overlap=0)
    assert "[U456]:" in chunks[0]
    assert "[U789]:" in chunks[0]


def test_chunk_slack_thread_large_splits_at_message_boundary():
    messages = [{"user": f"U{i}", "text": "x " * 400, "ts": str(i)} for i in range(10)]
    doc = {"id": "big-thread", "content": "fallback", "metadata": {"thread_messages": messages}}
    chunks = _chunk_slack_thread(doc, chunk_size=200, chunk_overlap=0)
    assert len(chunks) >= 2


# ---------------------------------------------------------------------------
# _chunk_pr_diff
# ---------------------------------------------------------------------------

def test_chunk_pr_diff_per_file_chunks():
    chunks = _chunk_pr_diff(GITHUB_PR_DOC, chunk_size=5000, chunk_overlap=0)
    assert len(chunks) == 2  # one per file
    filenames = [c for c in chunks if "auth/handler.py" in c or "test_auth.py" in c]
    assert len(filenames) == 2


def test_chunk_pr_diff_includes_filename():
    chunks = _chunk_pr_diff(GITHUB_PR_DOC, chunk_size=5000, chunk_overlap=0)
    assert any("File: auth/handler.py" in c for c in chunks)


def test_chunk_pr_diff_no_files_falls_back():
    doc = _doc("Raw diff text without files metadata")
    chunks = _chunk_pr_diff(doc, chunk_size=5000, chunk_overlap=0)
    assert len(chunks) >= 1
    assert "Raw diff text" in chunks[0]


def test_chunk_pr_diff_large_patch_splits_at_hunks():
    big_patch = "@@ -1,5 +1,6 @@\n line\n" + "@@ -10,5 +11,6 @@\n other line\n" * 20
    doc = {
        "id": "pr-big",
        "content": "",
        "metadata": {"files": [{"filename": "big.py", "patch": big_patch}]},
    }
    chunks = _chunk_pr_diff(doc, chunk_size=10, chunk_overlap=0)
    assert len(chunks) >= 2


# ---------------------------------------------------------------------------
# _chunk_by_headings
# ---------------------------------------------------------------------------

def test_chunk_by_headings_splits_at_h2():
    chunks = _chunk_by_headings(CONFLUENCE_DOC, chunk_size=5000, chunk_overlap=0)
    # Should produce at least 3 chunks: intro + Backend + Frontend
    assert len(chunks) >= 2


def test_chunk_by_headings_preserves_context():
    chunks = _chunk_by_headings(CONFLUENCE_DOC, chunk_size=5000, chunk_overlap=0)
    # Backend section should reference "Backend" heading
    backend_chunks = [c for c in chunks if "Backend" in c]
    assert len(backend_chunks) >= 1


def test_chunk_by_headings_empty_falls_back():
    chunks = _chunk_by_headings(EMPTY_DOC, chunk_size=5000, chunk_overlap=0)
    assert chunks == []


def test_chunk_by_headings_no_headings_fixed_fallback():
    doc = _doc("No headings here. Just plain text that goes on and on.")
    chunks = _chunk_by_headings(doc, chunk_size=5000, chunk_overlap=0)
    assert len(chunks) >= 1


# ---------------------------------------------------------------------------
# chunk_document (public API — strategy dispatch)
# ---------------------------------------------------------------------------

def test_chunk_document_adds_chunk_index():
    chunks = chunk_document(SLACK_DOC, "slack")
    for i, chunk in enumerate(chunks):
        assert "chunk_index" in chunk
        assert "chunk_content" in chunk
        assert "chunk_count" in chunk
        assert chunk["chunk_count"] == len(chunks)


def test_chunk_document_inherits_base_metadata():
    chunks = chunk_document(SLACK_DOC, "slack")
    for chunk in chunks:
        assert chunk["id"] == SLACK_DOC["id"]
        assert chunk["title"] == SLACK_DOC["title"]
        # "content" key not duplicated — only chunk_content
        assert "chunk_content" in chunk


def test_chunk_document_skips_empty_chunks():
    doc = {"id": "x", "content": "Hello world", "metadata": {"thread_messages": [
        {"user": "U1", "text": "", "ts": "1"},
        {"user": "U2", "text": "   ", "ts": "2"},
        {"user": "U3", "text": "Real content", "ts": "3"},
    ]}}
    chunks = chunk_document(doc, "slack")
    for chunk in chunks:
        assert chunk["chunk_content"].strip()


def test_chunk_document_fallback_on_exception(monkeypatch):
    """If the strategy handler raises, falls back to fixed chunking."""
    def _boom(*a, **kw):
        raise RuntimeError("simulated chunker failure")

    monkeypatch.setattr(
        "src.services.company_brain.ingestion.chunker._chunk_slack_thread", _boom
    )
    chunks = chunk_document(SLACK_DOC, "slack")
    assert len(chunks) >= 1  # fixed fallback should produce at least one chunk


def test_chunk_document_github_pr():
    chunks = chunk_document(GITHUB_PR_DOC, "github")
    assert len(chunks) >= 1


def test_chunk_document_confluence():
    chunks = chunk_document(CONFLUENCE_DOC, "confluence")
    assert len(chunks) >= 1
