"""
Conversation Memory Service.

Unified service for managing conversation memory across all tiers:
- Short-term: Recent messages (sliding window)
- Medium-term: Conversation summaries (persisted to DB + cached)
- Long-term: RAG retrieval from knowledge bases

This service ensures memory persistence and efficient retrieval.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ConversationMemoryConfig:
    """Configuration for conversation memory management."""

    # Summarization thresholds (lowered for better context retention)
    SUMMARIZE_AFTER_MESSAGES = 10  # Summarize after 10 messages (was 30)
    SUMMARIZE_AFTER_TOKENS = 15000  # Or after 15k tokens (was 50k)

    # Summary settings
    SUMMARY_MAX_TOKENS = 1500  # Max tokens for summary
    KEEP_RECENT_MESSAGES = 8  # Keep last 8 messages detailed (was 10)

    # Cache settings
    CACHE_TTL_SECONDS = 7200  # 2 hours (was 30 minutes)
    MAX_CACHED_MESSAGES = 50

    # Incremental summarization
    INCREMENTAL_SUMMARY_THRESHOLD = 5  # Re-summarize after 5 new messages


class ConversationMemoryService:
    """
    Unified service for conversation memory management.

    Handles:
    - Loading conversation history from DB
    - Managing summaries (persist to DB, cache to Redis)
    - Smart summarization triggers
    - Merging external context (Slack threads, etc.)
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.config = ConversationMemoryConfig()

    async def get_conversation_context(
        self,
        conversation_id: str | UUID,
        include_summary: bool = True,
        max_messages: int = 30,
        external_context: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """
        Get full conversation context for LLM.

        This is the main entry point for getting conversation memory.

        Args:
            conversation_id: Conversation ID
            include_summary: Whether to include/generate summary
            max_messages: Maximum messages to return
            external_context: External context (e.g., Slack thread history)

        Returns:
            Dictionary with:
            - messages: List of message dicts
            - summary: Conversation summary (if available)
            - needs_summarization: Whether summarization is recommended
            - total_messages: Total message count
            - estimated_tokens: Estimated token count
        """
        from src.models.conversation import Conversation
        from src.services.cache.conversation_cache_service import get_conversation_cache

        conv_id = str(conversation_id)
        cache_service = get_conversation_cache()

        # Get conversation from DB
        conversation = await self.db.get(
            Conversation, UUID(conv_id) if isinstance(conversation_id, str) else conversation_id
        )
        if not conversation:
            logger.warning(f"Conversation {conv_id} not found")
            return {
                "messages": external_context or [],
                "summary": None,
                "needs_summarization": False,
                "total_messages": len(external_context) if external_context else 0,
                "estimated_tokens": 0,
            }

        # Try to get messages from cache first
        cached_messages = await cache_service.get_conversation_history(conv_id, limit=max_messages)

        if cached_messages:
            messages = cached_messages
            logger.info(f"Cache HIT: {len(messages)} messages for conversation {conv_id}")
        else:
            # Load from database
            messages = await self._load_messages_from_db(conversation, max_messages)
            logger.info(f"Loaded {len(messages)} messages from DB for conversation {conv_id}")

            # Cache for next time
            if messages:
                await cache_service.set_conversation_history(conv_id, messages, ttl=self.config.CACHE_TTL_SECONDS)

        # Merge with external context if provided (e.g., Slack thread)
        if external_context:
            messages = self._merge_contexts(messages, external_context)
            logger.info(f"Merged with external context: {len(messages)} total messages")

        # Get or load summary
        summary = None
        if include_summary:
            summary = await self._get_summary(conversation, conv_id, cache_service)

        # Calculate if summarization is needed
        estimated_tokens = self._estimate_tokens(messages)
        needs_summarization = self._should_summarize(
            message_count=len(messages),
            token_count=estimated_tokens,
            existing_summary=summary,
            summary_message_count=conversation.summary_message_count or 0,
            current_message_count=conversation.message_count or 0,
        )

        return {
            "messages": messages,
            "summary": summary,
            "needs_summarization": needs_summarization,
            "total_messages": conversation.message_count or len(messages),
            "estimated_tokens": estimated_tokens,
        }

    async def save_summary(
        self,
        conversation_id: str | UUID,
        summary: str,
        message_count: int,
        token_count: int = 0,
    ) -> bool:
        """
        Save conversation summary to both DB and cache.

        Args:
            conversation_id: Conversation ID
            summary: Generated summary text
            message_count: Number of messages when summary was generated
            token_count: Estimated token count

        Returns:
            True if saved successfully
        """
        from src.models.conversation import Conversation
        from src.services.cache.conversation_cache_service import get_conversation_cache

        conv_id = str(conversation_id)

        try:
            # Save to database (persistent storage)
            conversation = await self.db.get(
                Conversation, UUID(conv_id) if isinstance(conversation_id, str) else conversation_id
            )

            if conversation:
                conversation.context_summary = summary
                conversation.summary_updated_at = datetime.now(UTC)
                conversation.summary_message_count = message_count
                conversation.total_tokens_estimated = token_count
                await self.db.commit()
                logger.info(f"Saved summary to DB for conversation {conv_id}")

            # Also cache for fast retrieval
            cache_service = get_conversation_cache()
            await cache_service.set_conversation_summary(conv_id, summary, ttl=self.config.CACHE_TTL_SECONDS)

            return True

        except Exception as e:
            logger.error(f"Error saving summary for conversation {conv_id}: {e}")
            await self.db.rollback()
            return False

    async def append_message(
        self,
        conversation_id: str | UUID,
        role: str,
        content: str,
    ) -> bool:
        """
        Append a message to the conversation cache.

        Args:
            conversation_id: Conversation ID
            role: Message role ('user' or 'assistant')
            content: Message content

        Returns:
            True if appended successfully
        """
        from src.services.cache.conversation_cache_service import get_conversation_cache

        cache_service = get_conversation_cache()
        return await cache_service.append_message(str(conversation_id), {"role": role, "content": content})

    async def invalidate_cache(self, conversation_id: str | UUID) -> None:
        """Invalidate conversation cache."""
        from src.services.cache.conversation_cache_service import get_conversation_cache

        cache_service = get_conversation_cache()
        await cache_service.invalidate(str(conversation_id))

    async def _load_messages_from_db(self, conversation: Any, limit: int) -> list[dict[str, str]]:
        """Load messages from database."""
        from src.models.message import Message, MessageRole

        result = await self.db.execute(
            select(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        messages = list(result.scalars().all())

        return [
            {
                "role": "user" if msg.role == MessageRole.USER else "assistant",
                "content": msg.content or "",
            }
            for msg in messages
        ]

    async def _get_summary(
        self,
        conversation: Any,
        conv_id: str,
        cache_service: Any,
    ) -> str | None:
        """Get summary from cache or DB."""
        # Try cache first
        cached_summary = await cache_service.get_conversation_summary(conv_id)
        if cached_summary:
            logger.info(f"Summary cache HIT for conversation {conv_id}")
            return cached_summary

        # Fall back to database
        if conversation.context_summary:
            logger.info(f"Summary loaded from DB for conversation {conv_id}")
            # Re-cache it
            await cache_service.set_conversation_summary(
                conv_id, conversation.context_summary, ttl=self.config.CACHE_TTL_SECONDS
            )
            return conversation.context_summary

        return None

    def _merge_contexts(
        self,
        db_messages: list[dict[str, str]],
        external_context: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """
        Merge database messages with external context.

        External context (like Slack thread) takes precedence as it's
        the authoritative source for that channel.
        """
        # If external context has more messages, use it
        if len(external_context) > len(db_messages):
            return external_context

        # Otherwise use DB messages (they may have more history)
        return db_messages

    def _should_summarize(
        self,
        message_count: int,
        token_count: int,
        existing_summary: str | None,
        summary_message_count: int,
        current_message_count: int,
    ) -> bool:
        """Determine if summarization is needed."""
        # If no summary exists and we have enough messages
        if not existing_summary:
            return (
                message_count >= self.config.SUMMARIZE_AFTER_MESSAGES
                or token_count >= self.config.SUMMARIZE_AFTER_TOKENS
            )

        # If summary exists, check if we need to update it
        messages_since_summary = current_message_count - summary_message_count
        return messages_since_summary >= self.config.INCREMENTAL_SUMMARY_THRESHOLD

    def _estimate_tokens(self, messages: list[dict[str, str]]) -> int:
        """Estimate token count for messages."""
        try:
            from src.services.agents.token_counter import TokenCounter

            return TokenCounter.count_messages_tokens(messages)
        except Exception:
            total_chars = sum(len(msg.get("content", "")) for msg in messages)
            return total_chars // 4


class MemorySummarizer:
    """
    Handles conversation summarization with smart incremental updates.
    """

    def __init__(self, llm_client: Any, config: ConversationMemoryConfig | None = None):
        self.llm_client = llm_client
        self.config = config or ConversationMemoryConfig()

    async def summarize_if_needed(
        self,
        messages: list[dict[str, str]],
        existing_summary: str | None = None,
        force: bool = False,
    ) -> tuple[list[dict[str, str]], str | None]:
        """
        Summarize messages if needed, return (recent_messages, summary).

        Args:
            messages: Full message history
            existing_summary: Existing summary to build upon
            force: Force summarization even if thresholds not met

        Returns:
            Tuple of (messages_to_keep, updated_summary)
        """
        # Check if summarization is needed
        if not force:
            total_tokens = self._estimate_tokens(messages)
            should_summarize = (
                len(messages) >= self.config.SUMMARIZE_AFTER_MESSAGES
                or total_tokens >= self.config.SUMMARIZE_AFTER_TOKENS
            )

            if not should_summarize:
                return messages, existing_summary

        # Split messages: older ones to summarize, recent ones to keep
        keep_recent = self.config.KEEP_RECENT_MESSAGES
        if len(messages) <= keep_recent:
            return messages, existing_summary

        messages_to_summarize = messages[:-keep_recent]
        recent_messages = messages[-keep_recent:]

        logger.info(f"Summarizing {len(messages_to_summarize)} messages, keeping {len(recent_messages)} recent")

        # Generate summary
        new_summary = await self._generate_summary(messages_to_summarize, existing_summary)

        return recent_messages, new_summary

    async def _generate_summary(
        self,
        messages: list[dict[str, str]],
        existing_summary: str | None = None,
    ) -> str:
        """Generate summary using LLM."""
        try:
            from src.services.agents.context_summarizer import ContextSummarizer

            summarizer = ContextSummarizer(self.llm_client)

            # Include existing summary for continuity
            context = ""
            if existing_summary:
                context = f"Previous conversation summary:\n{existing_summary}\n\nNew messages to incorporate:\n"

            summary = await summarizer.summarize_messages(
                messages=messages,
                summary_type="incremental" if existing_summary else "conversation",
                max_tokens=self.config.SUMMARY_MAX_TOKENS,
                context=context,
            )

            logger.info(f"Generated summary: {len(summary)} chars")
            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return self._simple_summary(messages, existing_summary)

    def _simple_summary(
        self,
        messages: list[dict[str, str]],
        existing_summary: str | None = None,
    ) -> str:
        """Simple fallback summary without LLM."""
        parts = []

        if existing_summary:
            parts.append(f"Previous context: {existing_summary[:500]}")

        # Extract key user messages
        user_messages = [m for m in messages if m.get("role") == "user"]
        if user_messages:
            key_points = [m.get("content", "")[:200] for m in user_messages[-5:]]
            parts.append("Recent user requests: " + "; ".join(key_points))

        return " | ".join(parts)

    def _estimate_tokens(self, messages: list[dict[str, str]]) -> int:
        """Estimate token count."""
        try:
            from src.services.agents.token_counter import TokenCounter

            return TokenCounter.count_messages_tokens(messages)
        except Exception:
            total_chars = sum(len(msg.get("content", "")) for msg in messages)
            return total_chars // 4


# Global instance getter
_memory_service_instances: dict[int, ConversationMemoryService] = {}


def get_conversation_memory_service(db: AsyncSession) -> ConversationMemoryService:
    """Get or create ConversationMemoryService instance for a DB session."""
    session_id = id(db)
    if session_id not in _memory_service_instances:
        _memory_service_instances[session_id] = ConversationMemoryService(db)
    return _memory_service_instances[session_id]
