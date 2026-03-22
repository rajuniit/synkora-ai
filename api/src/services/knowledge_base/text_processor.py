"""Text processing utilities for knowledge base operations."""

import re
from typing import Any

from src.models.knowledge_base import ChunkingStrategy
from src.services.knowledge_base.smart_chunker import SmartChunker


class TextProcessor:
    """Utility class for text processing operations."""

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 1500,
        chunk_overlap: int = 150,
        separator: str = "\n\n",
        strategy: ChunkingStrategy = ChunkingStrategy.FIXED,
        min_chunk_size: int = 500,
        max_chunk_size: int = 3000,
        chunking_config: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Split text into chunks using the configured strategy.

        Args:
            text: Text to chunk
            chunk_size: Target chunk size in characters
            chunk_overlap: Number of characters to overlap between chunks
            separator: Separator to use for splitting (default: double newline)
            strategy: Chunking strategy to use
            min_chunk_size: Minimum chunk size
            max_chunk_size: Maximum chunk size
            chunking_config: Additional configuration for chunking strategy
            metadata: Document metadata to include in chunks

        Returns:
            List of chunk dictionaries with text and metadata
        """
        if not text or chunk_size <= 0:
            return []

        # Use SmartChunker for intelligent chunking
        chunker = SmartChunker(
            strategy=strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_size=min_chunk_size,
            max_chunk_size=max_chunk_size,
            config=chunking_config or {},
        )

        return chunker.chunk_text(text, metadata=metadata)

    def _split_large_text(self, text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
        """
        Split large text that doesn't fit in a single chunk.

        Args:
            text: Text to split
            chunk_size: Maximum chunk size
            chunk_overlap: Overlap between chunks

        Returns:
            List of chunks
        """
        chunks = []
        start = 0
        max_iterations = len(text) // max(1, chunk_size - chunk_overlap) + 10  # Safety limit
        iterations = 0

        while start < len(text) and iterations < max_iterations:
            iterations += 1
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                sentence_end = max(
                    text.rfind(". ", start, end),
                    text.rfind("! ", start, end),
                    text.rfind("? ", start, end),
                    text.rfind("\n", start, end),
                )

                if sentence_end > start:
                    end = sentence_end + 1

            chunk = text[start:end].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)

            # Ensure we're making progress
            if chunk_overlap >= chunk_size:
                # Prevent infinite loop if overlap >= chunk_size
                start = end
            else:
                start = end - chunk_overlap if chunk_overlap > 0 else end

            # Safety check: if we're not making progress, break
            if start >= len(text) or (chunks and start <= len(chunks[-1])):
                break

        return chunks if chunks else [text]  # Return original text if no chunks created

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:()\-\'"]+', "", text)

        return text.strip()

    def extract_metadata_from_text(self, text: str) -> dict:
        """
        Extract metadata from text (e.g., title, date).

        Args:
            text: Text to analyze

        Returns:
            Dictionary with extracted metadata
        """
        metadata = {}

        # Extract potential title (first line if short)
        lines = text.split("\n")
        if lines and len(lines[0]) < 100:
            metadata["title"] = lines[0].strip()

        # Extract dates (simple pattern)
        date_pattern = r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{4}\b"
        dates = re.findall(date_pattern, text)
        if dates:
            metadata["dates"] = dates

        # Extract URLs
        url_pattern = r"https?://[^\s]+"
        urls = re.findall(url_pattern, text)
        if urls:
            metadata["urls"] = urls

        return metadata

    def truncate_text(self, text: str, max_length: int, suffix: str = "...") -> str:
        """
        Truncate text to maximum length.

        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix to add if truncated

        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text

        return text[: max_length - len(suffix)] + suffix

    def remove_code_blocks(self, text: str) -> str:
        """
        Remove code blocks from text.

        Args:
            text: Text containing code blocks

        Returns:
            Text without code blocks
        """
        # Remove markdown code blocks
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r"`[^`]+`", "", text)

        return text.strip()

    def extract_keywords(self, text: str, max_keywords: int = 10) -> list[str]:
        """
        Extract keywords from text (simple implementation).

        Args:
            text: Text to analyze
            max_keywords: Maximum number of keywords

        Returns:
            List of keywords
        """
        # Simple keyword extraction based on word frequency
        # Remove common stop words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
            "were",
            "been",
            "be",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
        }

        # Extract words
        words = re.findall(r"\b[a-z]{3,}\b", text.lower())

        # Filter stop words and count frequency
        word_freq = {}
        for word in words:
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency and return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:max_keywords]]
