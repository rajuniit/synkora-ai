"""
Conversation Lane - Concurrency control for agent executions.

Ensures only one agent execution per conversation at a time,
preventing race conditions in context management and state updates.

"""

import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Awaitable
from contextlib import asynccontextmanager
from typing import Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ConversationLane:
    """
    Manages per-conversation locks to ensure serialized execution.

    This prevents race conditions when multiple requests hit the same
    conversation simultaneously (e.g., user sends messages rapidly,
    or webhooks arrive concurrently).

    Usage:
        lane = ConversationLane()

        async with lane.acquire(conversation_id):
            # Only one execution per conversation at a time
            result = await process_message(...)

    Or with the helper:
        result = await lane.execute_in_lane(
            conversation_id,
            process_message(...)
        )
    """

    _instance: Optional["ConversationLane"] = None

    def __init__(self):
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._active_conversations: dict[str, float] = {}  # conversation_id -> start_time
        self._waiting_count: dict[str, int] = defaultdict(int)

    @classmethod
    def get_instance(cls) -> "ConversationLane":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @asynccontextmanager
    async def acquire(self, conversation_id: str, timeout: float | None = 300.0):
        """
        Acquire the lane for a conversation.

        Args:
            conversation_id: The conversation to lock
            timeout: Maximum time to wait for the lock (default 5 minutes)

        Raises:
            asyncio.TimeoutError: If lock cannot be acquired within timeout
        """
        if not conversation_id:
            # No conversation ID means no locking needed (e.g., new conversation)
            yield
            return

        lock = self._locks[conversation_id]
        self._waiting_count[conversation_id] += 1

        try:
            if self._waiting_count[conversation_id] > 1:
                logger.info(
                    f"Waiting for conversation lane: {conversation_id} "
                    f"(queue position: {self._waiting_count[conversation_id]})"
                )

            # Try to acquire with timeout
            if timeout:
                try:
                    await asyncio.wait_for(lock.acquire(), timeout=timeout)
                except TimeoutError:
                    logger.error(f"Timeout waiting for conversation lane: {conversation_id}")
                    raise
            else:
                await lock.acquire()

            self._active_conversations[conversation_id] = time.time()
            logger.debug(f"Acquired conversation lane: {conversation_id}")

            yield

        finally:
            self._waiting_count[conversation_id] -= 1
            if conversation_id in self._active_conversations:
                duration = time.time() - self._active_conversations[conversation_id]
                del self._active_conversations[conversation_id]
                logger.debug(f"Released conversation lane: {conversation_id} (held for {duration:.2f}s)")

            lock.release()

            # Clean up lock if no one is waiting
            if self._waiting_count[conversation_id] == 0:
                del self._locks[conversation_id]
                del self._waiting_count[conversation_id]

    async def execute_in_lane(self, conversation_id: str, coro: Awaitable[T], timeout: float | None = 300.0) -> T:
        """
        Execute a coroutine within the conversation's lane.

        Args:
            conversation_id: The conversation to lock
            coro: The coroutine to execute
            timeout: Maximum time to wait for the lock

        Returns:
            The result of the coroutine
        """
        async with self.acquire(conversation_id, timeout):
            return await coro

    def is_conversation_active(self, conversation_id: str) -> bool:
        """Check if a conversation has an active execution."""
        return conversation_id in self._active_conversations

    def get_active_duration(self, conversation_id: str) -> float | None:
        """Get how long the current execution has been running."""
        if conversation_id in self._active_conversations:
            return time.time() - self._active_conversations[conversation_id]
        return None

    def get_queue_length(self, conversation_id: str) -> int:
        """Get number of executions waiting for this conversation."""
        return self._waiting_count.get(conversation_id, 0)

    def get_stats(self) -> dict:
        """Get statistics about active lanes."""
        return {
            "active_conversations": len(self._active_conversations),
            "total_locks": len(self._locks),
            "conversations": {
                conv_id: {"duration": time.time() - start_time, "waiting": self._waiting_count.get(conv_id, 0)}
                for conv_id, start_time in self._active_conversations.items()
            },
        }


# Global instance for easy access
def get_conversation_lane() -> ConversationLane:
    """Get the global ConversationLane instance."""
    return ConversationLane.get_instance()
