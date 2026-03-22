"""Smart chunking service with multiple strategies for different content types."""

import logging
import re
from typing import Any

from src.models.knowledge_base import ChunkingStrategy

logger = logging.getLogger(__name__)


class SmartChunker:
    """Smart chunking service that applies different strategies based on content type."""

    def __init__(
        self,
        strategy: ChunkingStrategy = ChunkingStrategy.FIXED,
        chunk_size: int = 1500,
        chunk_overlap: int = 150,
        min_chunk_size: int = 500,
        max_chunk_size: int = 3000,
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize smart chunker.

        Args:
            strategy: Chunking strategy to use
            chunk_size: Target chunk size
            chunk_overlap: Overlap between chunks
            min_chunk_size: Minimum chunk size
            max_chunk_size: Maximum chunk size
            config: Additional configuration options
        """
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.config = config or {}

    def chunk_text(
        self, text: str, metadata: dict[str, Any] | None = None, source_type: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Chunk text using the configured strategy.

        Args:
            text: Text to chunk
            metadata: Document metadata
            source_type: Type of source (gmail, SLACK, etc.)

        Returns:
            List of chunk dictionaries with text and metadata
        """
        if not text:
            return []

        metadata = metadata or {}

        # Select chunking method based on strategy
        if self.strategy == ChunkingStrategy.EMAIL:
            return self._chunk_email(text, metadata)
        elif self.strategy == ChunkingStrategy.SLACK:
            return self._chunk_slack(text, metadata)
        elif self.strategy == ChunkingStrategy.SEMANTIC:
            return self._chunk_semantic(text, metadata)
        elif self.strategy == ChunkingStrategy.DOCUMENT:
            return self._chunk_document(text, metadata)
        elif self.strategy == ChunkingStrategy.CODE:
            return self._chunk_code(text, metadata)
        else:
            return self._chunk_fixed(text, metadata)

    def _chunk_email(self, text: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Email-specific chunking that preserves email structure.

        Strategy:
        - Keep complete emails under threshold as single chunks
        - For longer emails, chunk by semantic sections
        - Always include header info in first chunk
        """
        email_threshold = self.config.get("email_threshold", 2000)

        # Short email - keep as single chunk
        if len(text) <= email_threshold:
            return [
                {
                    "text": text,
                    "metadata": {
                        **metadata,
                        "chunk_type": "complete_email",
                        "chunk_index": 0,
                        "total_chunks": 1,
                        "has_complete_context": True,
                    },
                }
            ]

        # Long email - chunk semantically
        chunks = []

        # Try to extract email components
        header_end = self._find_email_header_end(text)
        if header_end > 0:
            header = text[:header_end]
            body = text[header_end:]
        else:
            header = ""
            body = text

        # First chunk includes header
        if header:
            first_chunk_body = self._get_first_paragraphs(body, self.chunk_size - len(header))
            chunks.append(
                {
                    "text": (header + "\n\n" + first_chunk_body).strip(),
                    "metadata": {**metadata, "chunk_type": "email_start", "chunk_index": 0, "has_header": True},
                }
            )
            remaining_body = body[len(first_chunk_body) :]
        else:
            remaining_body = body

        # Chunk remaining body
        body_chunks = self._chunk_by_paragraphs(remaining_body, self.chunk_size)
        for i, chunk_text in enumerate(body_chunks):
            chunks.append(
                {
                    "text": chunk_text,
                    "metadata": {
                        **metadata,
                        "chunk_type": "email_body" if i < len(body_chunks) - 1 else "email_end",
                        "chunk_index": len(chunks),
                    },
                }
            )

        # Update total_chunks in all chunks
        for chunk in chunks:
            chunk["metadata"]["total_chunks"] = len(chunks)

        return chunks

    def _chunk_slack(self, text: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Slack thread-aware chunking.

        Strategy:
        - Keep threads under threshold together
        - Group messages in conversation units
        - Preserve temporal order
        """
        slack_threshold = self.config.get("slack_thread_size", 1500)

        # Short thread - keep together
        if len(text) <= slack_threshold:
            return [
                {
                    "text": text,
                    "metadata": {
                        **metadata,
                        "chunk_type": "complete_thread",
                        "chunk_index": 0,
                        "total_chunks": 1,
                        "has_complete_context": True,
                    },
                }
            ]

        # Long thread - chunk by message groups
        # Try to split by message boundaries (look for timestamps or user mentions)
        message_pattern = r"\n(?=\[\d{4}-\d{2}-\d{2}|\d{1,2}:\d{2}|@\w+)"
        messages = re.split(message_pattern, text)

        chunks = []
        current_chunk = ""

        for msg in messages:
            if len(current_chunk) + len(msg) <= self.chunk_size:
                current_chunk += msg
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = msg

        if current_chunk:
            chunks.append(current_chunk.strip())

        return [
            {
                "text": chunk_text,
                "metadata": {**metadata, "chunk_type": "slack_messages", "chunk_index": i, "total_chunks": len(chunks)},
            }
            for i, chunk_text in enumerate(chunks)
        ]

    def _chunk_semantic(self, text: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Semantic-aware chunking that respects paragraph boundaries.
        """
        chunks = self._chunk_by_paragraphs(text, self.chunk_size)

        return [
            {
                "text": chunk_text,
                "metadata": {**metadata, "chunk_type": "SEMANTIC", "chunk_index": i, "total_chunks": len(chunks)},
            }
            for i, chunk_text in enumerate(chunks)
        ]

    def _chunk_document(self, text: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Document structure-aware chunking (sections, headings).
        """
        # Try to detect sections by headings
        heading_pattern = r"\n(#{1,6}\s+.+|[A-Z][^.!?]*:)\n"
        sections = re.split(heading_pattern, text)

        chunks = []
        current_chunk = ""
        current_heading = None

        for _i, section in enumerate(sections):
            # Check if this is a heading
            is_heading = bool(re.match(heading_pattern, "\n" + section + "\n"))

            if is_heading:
                current_heading = section.strip()
            else:
                # Add heading to chunk if available
                section_text = section
                if current_heading:
                    section_text = f"{current_heading}\n\n{section}"

                if len(current_chunk) + len(section_text) <= self.chunk_size:
                    current_chunk += section_text
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = section_text

        if current_chunk:
            chunks.append(current_chunk.strip())

        return [
            {
                "text": chunk_text,
                "metadata": {
                    **metadata,
                    "chunk_type": "document_section",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            }
            for i, chunk_text in enumerate(chunks)
        ]

    def _chunk_code(self, text: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Code structure-aware chunking (functions, classes).
        """
        # Simple implementation - chunk by function/class definitions
        # This is a basic version; could be enhanced with AST parsing
        code_pattern = r"\n(def |class |function |const |let |var )"
        sections = re.split(code_pattern, text)

        chunks = []
        current_chunk = ""

        for i in range(0, len(sections), 2):
            section = sections[i]
            if i + 1 < len(sections):
                section += sections[i + 1]

            if len(current_chunk) + len(section) <= self.chunk_size:
                current_chunk += section
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = section

        if current_chunk:
            chunks.append(current_chunk.strip())

        return [
            {
                "text": chunk_text,
                "metadata": {**metadata, "chunk_type": "code_block", "chunk_index": i, "total_chunks": len(chunks)},
            }
            for i, chunk_text in enumerate(chunks)
        ]

    def _chunk_fixed(self, text: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Fixed-size chunking with overlap (default strategy).
        """
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + self.chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                sentence_end = max(
                    text.rfind(". ", start, end),
                    text.rfind("! ", start, end),
                    text.rfind("? ", start, end),
                    text.rfind("\n", start, end),
                )

                if sentence_end > start:
                    end = sentence_end + 1

            chunk_text = text[start:end].strip()
            if chunk_text and len(chunk_text) >= self.min_chunk_size:
                chunks.append(
                    {"text": chunk_text, "metadata": {**metadata, "chunk_type": "FIXED", "chunk_index": chunk_index}}
                )
                chunk_index += 1

            start = end - self.chunk_overlap if self.chunk_overlap > 0 else end

        # Update total_chunks
        for chunk in chunks:
            chunk["metadata"]["total_chunks"] = len(chunks)

        return chunks

    def _chunk_by_paragraphs(self, text: str, target_size: int) -> list[str]:
        """Chunk text by paragraphs while respecting target size."""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= target_size:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # If paragraph itself is too large, split it
                if len(para) > target_size:
                    sub_chunks = self._split_large_text(para, target_size)
                    chunks.extend(sub_chunks[:-1])
                    current_chunk = sub_chunks[-1] if sub_chunks else ""
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _split_large_text(self, text: str, target_size: int) -> list[str]:
        """Split large text into smaller chunks."""
        chunks = []
        start = 0

        while start < len(text):
            end = start + target_size

            if end < len(text):
                # Try to break at sentence boundary
                sentence_end = max(
                    text.rfind(". ", start, end),
                    text.rfind("! ", start, end),
                    text.rfind("? ", start, end),
                    text.rfind("\n", start, end),
                )

                if sentence_end > start:
                    end = sentence_end + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end

        return chunks if chunks else [text]

    def _find_email_header_end(self, text: str) -> int:
        """Find where email header ends (From, To, Subject, Date)."""
        # Look for common email header patterns
        header_patterns = [r"From:.*?\n", r"To:.*?\n", r"Subject:.*?\n", r"Date:.*?\n"]

        last_header_pos = 0
        for pattern in header_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                last_header_pos = max(last_header_pos, match.end())

        # Look for double newline after headers
        if last_header_pos > 0:
            double_newline = text.find("\n\n", last_header_pos)
            if double_newline > 0:
                return double_newline + 2

        return last_header_pos

    def _get_first_paragraphs(self, text: str, max_chars: int) -> str:
        """Get first few paragraphs up to max_chars."""
        paragraphs = text.split("\n\n")
        result = ""

        for para in paragraphs:
            if len(result) + len(para) + 2 <= max_chars:
                if result:
                    result += "\n\n" + para
                else:
                    result = para
            else:
                break

        return result if result else text[:max_chars]
