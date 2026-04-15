"""
Source-aware document chunker for Company Brain.

Strategy is resolved per source_type from the COMPANY_BRAIN_CHUNKING_STRATEGIES
JSON env var.  Adding a new strategy requires zero config changes — just add a
handler function and map it.

Available strategies:
  thread    — Slack: group all messages in a thread into one chunk (preserves context)
  diff      — GitHub PRs: split by file diff hunk blocks
  document  — Confluence / Notion: split at heading boundaries
  fixed     — Default: fixed-size with configurable overlap (tiktoken-based)
  semantic  — Future: sentence-boundary + embedding similarity grouping
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_CHUNK_SIZE = 1_500   # tokens
_DEFAULT_CHUNK_OVERLAP = 150  # tokens


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_strategy(source_type: str) -> str:
    """Return the chunking strategy name for a source_type from settings."""
    from src.config.settings import get_settings
    settings = get_settings()
    raw = getattr(settings, "company_brain_chunking_strategies",
                  '{"default":"fixed"}')
    try:
        mapping: dict[str, str] = json.loads(raw)
    except Exception:
        mapping = {"default": "fixed"}
    return mapping.get(source_type.lower(), mapping.get("default", "fixed"))


def chunk_document(
    doc: dict[str, Any],
    source_type: str,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = _DEFAULT_CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    """
    Split a raw document into indexable chunks.

    Args:
        doc:         Raw document dict with at minimum {"content": str, "id": str}
        source_type: e.g. "slack", "github", "jira"
        chunk_size:  Target token count per chunk
        chunk_overlap: Token overlap between consecutive fixed chunks

    Returns:
        List of chunk dicts.  Each inherits all metadata from the source doc
        and adds:
          chunk_index:   int (0-based)
          chunk_count:   int (total chunks for this doc)
          chunk_content: str (the text for this chunk)
    """
    strategy = get_strategy(source_type)

    handlers = {
        "thread": _chunk_slack_thread,
        "diff": _chunk_pr_diff,
        "document": _chunk_by_headings,
        "fixed": _chunk_fixed,
    }

    handler = handlers.get(strategy, _chunk_fixed)
    try:
        texts = handler(doc, chunk_size, chunk_overlap)
    except Exception as exc:
        logger.warning("Chunker '%s' failed for doc %s: %s — falling back to fixed",
                       strategy, doc.get("id"), exc)
        texts = _chunk_fixed(doc, chunk_size, chunk_overlap)

    if not texts:
        texts = [doc.get("content", "")]

    base_meta = {k: v for k, v in doc.items() if k != "content"}
    chunks = []
    for i, text in enumerate(texts):
        if not text or not text.strip():
            continue
        chunks.append({
            **base_meta,
            "chunk_index": i,
            "chunk_count": len(texts),
            "chunk_content": text.strip(),
        })
    return chunks


# ---------------------------------------------------------------------------
# Strategy implementations
# ---------------------------------------------------------------------------

def _count_tokens(text: str) -> int:
    """Approximate token count without importing tiktoken (no hard dep)."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # fallback: ~4 characters per token
        return max(1, len(text) // 4)


def _chunk_fixed(
    doc: dict[str, Any], chunk_size: int, chunk_overlap: int
) -> list[str]:
    """Split text into fixed-size overlapping chunks (token-based)."""
    text = doc.get("content", "")
    if not text:
        return []

    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(text)
        chunks = []
        start = 0
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunks.append(enc.decode(chunk_tokens))
            if end == len(tokens):
                break
            start += chunk_size - chunk_overlap
        return chunks
    except Exception:
        # Word-based fallback
        words = text.split()
        approx_words_per_chunk = chunk_size // 2  # ~2 tokens per word average
        overlap_words = chunk_overlap // 2
        chunks = []
        start = 0
        while start < len(words):
            end = min(start + approx_words_per_chunk, len(words))
            chunks.append(" ".join(words[start:end]))
            if end == len(words):
                break
            start += approx_words_per_chunk - overlap_words
        return chunks


def _chunk_slack_thread(
    doc: dict[str, Any], chunk_size: int, chunk_overlap: int
) -> list[str]:
    """
    Slack thread strategy: keep the entire thread as one chunk if it fits;
    otherwise split at message boundaries rather than mid-message.

    The doc is expected to have metadata.thread_messages: list[{"user", "text", "ts"}]
    If not present, falls back to fixed chunking.
    """
    meta = doc.get("metadata") or {}
    messages = meta.get("thread_messages")
    if not messages:
        return _chunk_fixed(doc, chunk_size, chunk_overlap)

    formatted = "\n".join(
        f"[{m.get('user', 'unknown')}]: {m.get('text', '')}"
        for m in messages
        if m.get("text")
    )

    if _count_tokens(formatted) <= chunk_size:
        return [formatted]

    # Thread is large — split at message boundaries preserving N messages per chunk
    chunks: list[str] = []
    current_lines: list[str] = []
    current_tokens = 0

    for m in messages:
        line = f"[{m.get('user', 'unknown')}]: {m.get('text', '')}"
        line_tokens = _count_tokens(line)
        if current_tokens + line_tokens > chunk_size and current_lines:
            chunks.append("\n".join(current_lines))
            current_lines = current_lines[-3:]  # keep last 3 messages for context
            current_tokens = sum(_count_tokens(l) for l in current_lines)
        current_lines.append(line)
        current_tokens += line_tokens

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks


def _chunk_pr_diff(
    doc: dict[str, Any], chunk_size: int, chunk_overlap: int
) -> list[str]:
    """
    GitHub PR / GitLab MR strategy: split at file diff boundaries.

    Expects doc["content"] to be a unified diff or the metadata to contain
    individual file diffs under metadata.files[].patch.
    """
    meta = doc.get("metadata") or {}
    files = meta.get("files")

    if files:
        chunks: list[str] = []
        for f in files:
            filename = f.get("filename", "")
            patch = f.get("patch", "")
            if not patch:
                continue
            header = f"File: {filename}\n"
            block = header + patch
            if _count_tokens(block) <= chunk_size:
                chunks.append(block)
            else:
                # Large diff: split at hunk boundaries (@@ ... @@)
                hunks = re.split(r"(?=^@@)", patch, flags=re.MULTILINE)
                for hunk in hunks:
                    if hunk.strip():
                        chunks.append(header + hunk)
        if chunks:
            return chunks

    # Fallback: treat as fixed text
    return _chunk_fixed(doc, chunk_size, chunk_overlap)


def _chunk_by_headings(
    doc: dict[str, Any], chunk_size: int, chunk_overlap: int
) -> list[str]:
    """
    Document strategy (Confluence / Notion): split at Markdown heading boundaries.

    Keeps heading hierarchy context by prepending ancestor headings to each chunk.
    """
    text = doc.get("content", "")
    if not text:
        return []

    # Split at headings (# ## ### etc.)
    sections = re.split(r"(?=^#{1,6}\s)", text, flags=re.MULTILINE)

    chunks: list[str] = []
    ancestors: list[str] = []

    for section in sections:
        if not section.strip():
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+)", section)
        if heading_match:
            level = len(heading_match.group(1))
            ancestors = ancestors[: level - 1]
            ancestors.append(heading_match.group(0).split("\n")[0])

        context_prefix = "\n".join(ancestors[:-1]) + "\n" if len(ancestors) > 1 else ""
        full_section = context_prefix + section

        if _count_tokens(full_section) <= chunk_size:
            chunks.append(full_section)
        else:
            # Section itself is too long — apply fixed chunking to it
            sub_doc = {"content": full_section}
            chunks.extend(_chunk_fixed(sub_doc, chunk_size, chunk_overlap))

    return chunks if chunks else _chunk_fixed(doc, chunk_size, chunk_overlap)
