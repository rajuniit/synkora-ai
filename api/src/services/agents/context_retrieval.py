"""
RAG-style Context Retrieval Service.


Stores conversation history externally and retrieves relevant context when needed.
"""

import hashlib
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class ContextRetrieval:
    """RAG-style context retrieval using vector similarity."""

    def __init__(self, vector_db: Any | None = None, embedding_service: Any | None = None):
        """
        Initialize context retrieval service.

        Args:
            vector_db: Vector database for storing/retrieving contexts
            embedding_service: Service for generating embeddings
        """
        self.vector_db = vector_db
        self.embedding_service = embedding_service
        self.local_cache: dict[str, list[dict[str, Any]]] = {}
        logger.info("ContextRetrieval initialized")

    async def store_context(
        self, conversation_id: str, messages: list[dict[str, str]], metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Store conversation context for later retrieval.

        Args:
            conversation_id: Unique conversation identifier
            messages: Messages to store
            metadata: Additional metadata

        Returns:
            Storage ID
        """
        try:
            if not self.vector_db or not self.embedding_service:
                return self._store_locally(conversation_id, messages, metadata)

            # Generate embeddings for messages
            text_chunks = [f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in messages]

            embeddings = self.embedding_service.embed_texts(text_chunks)

            # Store in vector DB with metadata
            storage_id = hashlib.md5(f"{conversation_id}_{datetime.now().isoformat()}".encode()).hexdigest()

            for i, (text, embedding) in enumerate(zip(text_chunks, embeddings, strict=False)):
                self.vector_db.insert(
                    collection_name=f"context_{conversation_id}",
                    vector=embedding,
                    payload={
                        "text": text,
                        "message_index": i,
                        "conversation_id": conversation_id,
                        "storage_id": storage_id,
                        "timestamp": datetime.now().isoformat(),
                        **(metadata or {}),
                    },
                )

            logger.info(f"Stored {len(messages)} messages for conversation {conversation_id}")
            return storage_id

        except Exception as e:
            logger.error(f"Failed to store context: {e}")
            return self._store_locally(conversation_id, messages, metadata)

    def _store_locally(
        self, conversation_id: str, messages: list[dict[str, str]], metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Store context locally.

        Args:
            conversation_id: Conversation ID
            messages: Messages to store
            metadata: Additional metadata

        Returns:
            Storage ID
        """
        storage_id = hashlib.md5(f"{conversation_id}_{datetime.now().isoformat()}".encode()).hexdigest()

        if conversation_id not in self.local_cache:
            self.local_cache[conversation_id] = []

        self.local_cache[conversation_id].append(
            {
                "storage_id": storage_id,
                "messages": messages,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat(),
            }
        )

        logger.info(f"Stored {len(messages)} messages locally for {conversation_id}")
        return storage_id

    async def retrieve_relevant_context(
        self, conversation_id: str, query: str, top_k: int = 5, min_score: float = 0.7
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant context based on query.

        Args:
            conversation_id: Conversation ID
            query: Query to find relevant context
            top_k: Number of results to return
            min_score: Minimum similarity score

        Returns:
            List of relevant context items
        """
        try:
            if not self.vector_db or not self.embedding_service:
                return self._retrieve_locally(conversation_id, query, top_k)

            # Generate embedding for query
            query_embedding = self.embedding_service.embed_texts([query])[0]

            # Search vector DB
            results = self.vector_db.search(
                collection_name=f"context_{conversation_id}",
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=min_score,
            )

            # Format results
            relevant_contexts = []
            for result in results:
                payload = result.get("payload", {})
                relevant_contexts.append(
                    {
                        "text": payload.get("text", ""),
                        "score": result.get("score", 0),
                        "message_index": payload.get("message_index"),
                        "timestamp": payload.get("timestamp"),
                        "metadata": {
                            k: v
                            for k, v in payload.items()
                            if k not in ["text", "message_index", "conversation_id", "storage_id", "timestamp"]
                        },
                    }
                )

            logger.info(f"Retrieved {len(relevant_contexts)} relevant contexts for query: {query[:50]}...")
            return relevant_contexts

        except Exception as e:
            logger.error(f"Failed to retrieve context: {e}")
            return self._retrieve_locally(conversation_id, query, top_k)

    def _retrieve_locally(self, conversation_id: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Retrieve context from local cache.

        Args:
            conversation_id: Conversation ID
            query: Query string
            top_k: Number of results

        Returns:
            List of relevant contexts
        """
        if conversation_id not in self.local_cache:
            return []

        # Simple keyword matching
        query_lower = query.lower()
        relevant_contexts = []

        for stored_item in self.local_cache[conversation_id]:
            for i, msg in enumerate(stored_item["messages"]):
                content = msg.get("content", "").lower()
                if any(word in content for word in query_lower.split()):
                    # Simple scoring based on word matches
                    score = sum(1 for word in query_lower.split() if word in content) / len(query_lower.split())

                    relevant_contexts.append(
                        {
                            "text": f"{msg.get('role', 'user')}: {msg.get('content', '')}",
                            "score": score,
                            "message_index": i,
                            "timestamp": stored_item["timestamp"],
                            "metadata": stored_item["metadata"],
                        }
                    )

        # Sort by score and return top_k
        relevant_contexts.sort(key=lambda x: x["score"], reverse=True)
        return relevant_contexts[:top_k]

    async def get_conversation_summary(self, conversation_id: str) -> dict[str, Any] | None:
        """
        Get summary of stored conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            Summary dict or None
        """
        if conversation_id in self.local_cache:
            total_messages = sum(len(item["messages"]) for item in self.local_cache[conversation_id])

            return {
                "conversation_id": conversation_id,
                "total_messages": total_messages,
                "storage_count": len(self.local_cache[conversation_id]),
                "first_stored": self.local_cache[conversation_id][0]["timestamp"],
                "last_stored": self.local_cache[conversation_id][-1]["timestamp"],
            }

        return None

    def clear_conversation(self, conversation_id: str) -> bool:
        """
        Clear stored context for a conversation.

        Args:
            conversation_id: Conversation ID to clear

        Returns:
            True if successful
        """
        try:
            # Clear from vector DB if available
            if self.vector_db:
                self.vector_db.delete_collection(f"context_{conversation_id}")

            # Clear from local cache
            if conversation_id in self.local_cache:
                del self.local_cache[conversation_id]

            logger.info(f"Cleared context for conversation {conversation_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear conversation context: {e}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """
        Get retrieval service statistics.

        Returns:
            Dict with stats
        """
        total_conversations = len(self.local_cache)
        total_stored_items = sum(len(items) for items in self.local_cache.values())

        return {
            "total_conversations": total_conversations,
            "total_stored_items": total_stored_items,
            "has_vector_db": self.vector_db is not None,
            "has_embedding_service": self.embedding_service is not None,
            "storage_mode": "vector_db" if self.vector_db else "local_cache",
        }
