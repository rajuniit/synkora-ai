"""Review sync service for app store reviews."""

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.app_review import AppReview
from src.models.app_store_source import AppStoreSource
from src.models.document import Document
from src.models.document_segment import DocumentSegment
from src.models.knowledge_base import KnowledgeBase
from src.services.knowledge_base.embedding_service import EmbeddingService
from src.services.knowledge_base.providers.vector_db_factory import VectorDBProviderFactory
from src.services.knowledge_base.text_processor import TextProcessor

logger = logging.getLogger(__name__)


class ReviewSyncService:
    """Sync app store reviews to knowledge base with embeddings."""

    def __init__(self, db: AsyncSession):
        """Initialize review sync service."""
        self.db = db
        self.text_processor = TextProcessor()
        self.embedding_service = None

    async def sync_source(self, source_id: UUID) -> dict[str, Any]:
        """
        Sync reviews for an app store source.

        Args:
            source_id: App store source ID

        Returns:
            Sync result dictionary
        """
        from src.services.app_store import get_connector

        # Get source
        result = await self.db.execute(select(AppStoreSource).filter(AppStoreSource.id == source_id))
        source = result.scalar_one_or_none()

        if not source:
            return {"success": False, "error": "App store source not found"}

        try:
            # Get connector
            connector = get_connector(source, self.db)

            # Fetch reviews
            logger.info(f"Fetching reviews for {source.app_name}...")
            fetch_result = await connector.fetch_reviews()

            # Extract reviews from result
            reviews_data = fetch_result.get("reviews", []) if isinstance(fetch_result, dict) else fetch_result

            if not reviews_data:
                logger.warning(f"No reviews fetched for {source.app_name}")
                return {"success": True, "reviews_fetched": 0, "reviews_synced": 0}

            # Save reviews to database
            reviews = []
            for idx, review_data in enumerate(reviews_data):
                # Log raw review data for debugging
                logger.info(f"Processing review {idx + 1}/{len(reviews_data)}")
                logger.debug(f"Raw review data: {json.dumps(review_data, default=str, indent=2)}")

                # Convert camelCase keys to snake_case for database model
                normalized_data = {
                    "review_id": review_data.get("reviewId", review_data.get("review_id")),
                    "author_name": review_data.get("userName", review_data.get("author_name", "Anonymous")),
                    "rating": review_data.get("score", review_data.get("rating")),
                    "content": review_data.get("content", ""),
                    "review_date": review_data.get("at", review_data.get("review_date")),
                    "thumbs_up_count": review_data.get("thumbsUpCount", review_data.get("thumbs_up_count", 0)),
                    "app_version": review_data.get("reviewCreatedVersion", review_data.get("app_version")),
                    "has_response": bool(review_data.get("replyContent") or review_data.get("response_text")),
                    "response_text": review_data.get("replyContent", review_data.get("response_text")),
                    "response_date": review_data.get("repliedAt", review_data.get("response_date")),
                    "language": review_data.get("language"),
                    "country": review_data.get("country"),
                    "title": review_data.get("title"),
                }

                # Log normalized data
                logger.info(
                    f"Normalized review data - ID: {normalized_data['review_id']}, "
                    f"Author: {normalized_data['author_name']}, "
                    f"Rating: {normalized_data['rating']}, "
                    f"Content length: {len(normalized_data['content'])} chars"
                )

                # Check if review already exists
                existing_result = await self.db.execute(
                    select(AppReview).filter(
                        AppReview.app_store_source_id == source_id, AppReview.review_id == normalized_data["review_id"]
                    )
                )
                existing_review = existing_result.scalar_one_or_none()

                if existing_review:
                    # Update existing review
                    for key, value in normalized_data.items():
                        if value is not None and hasattr(existing_review, key):
                            setattr(existing_review, key, value)
                    review = existing_review
                else:
                    # Create new review
                    review = AppReview(
                        app_store_source_id=source_id, **{k: v for k, v in normalized_data.items() if v is not None}
                    )
                    self.db.add(review)

                reviews.append(review)

            await self.db.commit()

            # Sync to knowledge base if configured
            if source.knowledge_base_id:
                sync_result = await self.sync_reviews_to_kb(source, reviews)

                # Update source stats
                source.last_sync_at = datetime.now(UTC)
                count_result = await self.db.execute(
                    select(AppReview).filter(AppReview.app_store_source_id == source_id)
                )
                source.total_reviews_collected = len(list(count_result.scalars().all()))
                await self.db.commit()

                return {
                    "success": True,
                    "reviews_fetched": len(reviews_data),
                    "reviews_synced": sync_result.get("reviews_synced", 0),
                    "reviews_embedded": sync_result.get("reviews_embedded", 0),
                    "total_chunks": sync_result.get("total_chunks", 0),
                }
            else:
                # Update source stats
                source.last_sync_at = datetime.now(UTC)
                count_result = await self.db.execute(
                    select(AppReview).filter(AppReview.app_store_source_id == source_id)
                )
                source.total_reviews_collected = len(list(count_result.scalars().all()))
                await self.db.commit()

                return {
                    "success": True,
                    "reviews_fetched": len(reviews_data),
                    "reviews_synced": len(reviews),
                    "reviews_embedded": 0,
                    "total_chunks": 0,
                }

        except Exception as e:
            logger.error(f"Error syncing source {source_id}: {e}", exc_info=True)
            await self.db.rollback()
            return {"success": False, "error": str(e)}

    async def sync_reviews_to_kb(self, app_store_source: AppStoreSource, reviews: list[AppReview]) -> dict[str, Any]:
        """
        Sync reviews to knowledge base with embeddings.

        Args:
            app_store_source: App store source instance
            reviews: List of review instances to sync

        Returns:
            Sync result dictionary
        """
        if not app_store_source.knowledge_base_id:
            logger.warning(
                f"App store source {app_store_source.app_name} is not linked to a knowledge base. "
                "Reviews will be stored but not embedded."
            )
            return {"success": True, "reviews_synced": len(reviews), "reviews_embedded": 0, "total_chunks": 0}

        # Get knowledge base
        result = await self.db.execute(
            select(KnowledgeBase).filter(KnowledgeBase.id == app_store_source.knowledge_base_id)
        )
        kb = result.scalar_one_or_none()

        if not kb:
            logger.error(f"Knowledge base {app_store_source.knowledge_base_id} not found")
            return {"success": False, "error": "Knowledge base not found", "reviews_synced": 0}

        return await self._sync_and_embed(app_store_source, kb, reviews)

    async def _sync_and_embed(
        self, app_store_source: AppStoreSource, kb: KnowledgeBase, reviews: list[AppReview]
    ) -> dict[str, Any]:
        """Sync reviews and create embeddings."""
        try:
            # Initialize embedding service with KB's configuration
            embedding_config = kb.get_embedding_config_decrypted()
            logger.info(
                f"Initializing embedding service with provider: {kb.embedding_provider.value}, "
                f"model: {kb.embedding_model}"
            )

            self.embedding_service = EmbeddingService(
                provider=kb.embedding_provider.value, model_name=kb.embedding_model, config=embedding_config
            )

            # Initialize vector DB provider
            from src.models.knowledge_base import VectorDBProvider

            if isinstance(kb.vector_db_provider, str):
                provider_enum = VectorDBProvider(kb.vector_db_provider)
            else:
                provider_enum = kb.vector_db_provider

            vector_db_config = kb.get_vector_db_config_decrypted()

            vector_db = VectorDBProviderFactory.create(provider_type=provider_enum, config=vector_db_config)
            vector_db.connect()

            # Get collection/index name
            collection_name = (
                kb.vector_db_config.get("index_name") or kb.vector_db_config.get("collection_name") or f"kb-{kb.id}"
            )
            logger.info(f"Using collection/index name: '{collection_name}'")

            # Ensure collection exists
            if not vector_db.collection_exists(collection_name):
                dimension = self.embedding_service.get_embedding_dimension()
                vector_db.create_collection(
                    collection_name=collection_name, dimension=dimension, distance_metric="cosine"
                )
                logger.info(f"Created collection {collection_name} with dimension {dimension}")

            reviews_synced = 0
            total_chunks = 0

            logger.info(f"Starting to sync {len(reviews)} reviews...")

            for idx, review in enumerate(reviews):
                logger.info(f"Processing review {idx + 1}/{len(reviews)}: {review.review_id}")
                try:
                    # Create review text for embedding
                    review_text = self._format_review_for_embedding(review)

                    # Create document for this review
                    doc_name = f"{app_store_source.app_name} - Review by {review.author_name}"
                    if review.title:
                        doc_name += f": {review.title}"

                    # Check if document already exists
                    existing_doc_result = await self.db.execute(
                        select(Document).filter(
                            Document.knowledge_base_id == kb.id, Document.external_id == review.review_id
                        )
                    )
                    existing_doc = existing_doc_result.scalar_one_or_none()

                    if existing_doc:
                        kb_doc = existing_doc
                        kb_doc.content = review_text
                        kb_doc.doc_metadata = self._create_review_metadata(review, app_store_source)
                    else:
                        kb_doc = Document(
                            tenant_id=app_store_source.tenant_id,
                            knowledge_base_id=kb.id,
                            name=doc_name,
                            external_id=review.review_id,
                            source_type="app_review",
                            content=review_text,
                            content_type="text",
                            doc_metadata=self._create_review_metadata(review, app_store_source),
                            word_count=len(review_text.split()),
                            char_count=len(review_text),
                            upload_source="app_store",
                        )
                        self.db.add(kb_doc)

                    await self.db.flush()

                    # Chunk the review text
                    logger.info(f"Chunking review text (length: {len(review_text)} chars)...")
                    chunks = self.text_processor.chunk_text(
                        text=review_text,
                        chunk_size=kb.chunk_size,
                        chunk_overlap=kb.chunk_overlap,
                        strategy=kb.chunking_strategy,
                        min_chunk_size=kb.min_chunk_size,
                        max_chunk_size=kb.max_chunk_size,
                        chunking_config=kb.chunking_config,
                        metadata=self._create_review_metadata(review, app_store_source),
                    )
                    logger.info(f"Generated {len(chunks)} chunks")

                    if not chunks:
                        logger.warning(f"No chunks generated for review {review.review_id}")
                        continue

                    # Generate embeddings
                    chunk_texts = [chunk["text"] for chunk in chunks]
                    logger.info(f"Generating embeddings for {len(chunk_texts)} chunks...")
                    embeddings = self.embedding_service.embed_texts(chunk_texts)
                    logger.info(f"Generated {len(embeddings)} embeddings")

                    # Delete existing segments for this document
                    await self.db.execute(
                        DocumentSegment.__table__.delete().where(DocumentSegment.document_id == kb_doc.id)
                    )

                    # Prepare vectors for storage
                    vectors = []
                    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=False)):
                        chunk_text = chunk["text"]

                        # Create DocumentSegment
                        segment = DocumentSegment(
                            tenant_id=app_store_source.tenant_id,
                            dataset_id=None,
                            document_id=kb_doc.id,
                            position=i,
                            content=chunk_text,
                            word_count=len(chunk_text.split()),
                            tokens=len(chunk_text) // 4,
                            index_node_id=f"kb-{kb.id}-doc-{kb_doc.id}-seg-{i}",
                            index_node_hash=f"hash-{kb_doc.id}-{i}",
                            created_by=app_store_source.tenant_id,
                        )
                        self.db.add(segment)
                        await self.db.flush()

                        # Prepare vector metadata (exclude None values for Pinecone compatibility)
                        metadata = {
                            "knowledge_base_id": str(kb.id),
                            "document_id": str(kb_doc.id),
                            "segment_id": str(segment.id),
                            "review_id": review.review_id,
                            "app_store_source_id": str(app_store_source.id),
                            "chunk_index": i,
                            "text": chunk_text,
                            "rating": review.rating,
                            "app_name": app_store_source.app_name,
                            "store_type": app_store_source.store_type,
                        }

                        # Add optional fields if present (Pinecone doesn't accept null values)
                        if review.sentiment:
                            metadata["sentiment"] = review.sentiment
                        if review.review_date:
                            metadata["review_date"] = review.review_date.isoformat()
                        if review.language:
                            metadata["language"] = review.language
                        if review.country:
                            metadata["country"] = review.country
                        if review.app_version:
                            metadata["app_version"] = review.app_version
                        if review.topics:
                            metadata["topics"] = review.topics
                        if review.issues:
                            metadata["issues"] = review.issues

                        # Check metadata size for Pinecone
                        if kb.vector_db_provider == VectorDBProvider.PINECONE:
                            metadata_json = json.dumps(metadata)
                            metadata_size = len(metadata_json.encode("utf-8"))

                            if metadata_size > 40960:  # 40KB limit
                                logger.warning(
                                    f"Metadata exceeds Pinecone limit! "
                                    f"Size: {metadata_size} bytes ({metadata_size / 1024:.2f} KB)"
                                )

                        vectors.append({"id": segment.index_node_id, "vector": embedding, "payload": metadata})

                    # Store vectors in vector DB with KB ID as namespace
                    namespace = str(kb.id)
                    vector_ids = vector_db.add_vectors(
                        collection_name=collection_name, vectors=vectors, namespace=namespace
                    )
                    logger.info(
                        f"Stored {len(vector_ids)} vectors for review {review.review_id} in namespace {namespace}"
                    )

                    # Commit after each review
                    await self.db.commit()

                    reviews_synced += 1
                    total_chunks += len(chunk_texts)

                    logger.info(
                        f"Completed review {idx + 1}/{len(reviews)} - "
                        f"Total synced: {reviews_synced}, Total chunks: {total_chunks}"
                    )

                except Exception as e:
                    logger.error(f"Error processing review {review.review_id}: {e}", exc_info=True)
                    await self.db.rollback()
                    continue

            # Update knowledge base stats
            logger.info("Updating knowledge base stats...")
            doc_count_result = await self.db.execute(select(Document).filter(Document.knowledge_base_id == kb.id))
            kb.total_documents = len(list(doc_count_result.scalars().all()))
            kb.total_chunks += total_chunks

            await self.db.commit()
            vector_db.disconnect()

            logger.info(
                f"Synced {reviews_synced} reviews, generated {total_chunks} chunks for knowledge base {kb.name}"
            )

            return {
                "success": True,
                "reviews_synced": reviews_synced,
                "reviews_embedded": reviews_synced,
                "total_chunks": total_chunks,
            }

        except Exception as e:
            logger.error(f"Error in review sync: {e}", exc_info=True)
            await self.db.rollback()
            return {"success": False, "error": str(e), "reviews_synced": 0}

    def _format_review_for_embedding(self, review: AppReview) -> str:
        """
        Format review for embedding.

        Args:
            review: Review instance

        Returns:
            Formatted review text
        """
        parts = []

        # Add title if present
        if review.title:
            parts.append(f"Title: {review.title}")

        # Add rating
        parts.append(f"Rating: {review.rating}/5 stars")

        # Add review content
        if review.content:
            parts.append(f"Review: {review.content}")

        # Add metadata
        metadata_parts = []
        if review.author_name:
            metadata_parts.append(f"Author: {review.author_name}")
        if review.app_version:
            metadata_parts.append(f"App Version: {review.app_version}")
        if review.language:
            metadata_parts.append(f"Language: {review.language}")
        if review.country:
            metadata_parts.append(f"Country: {review.country}")
        if review.review_date:
            metadata_parts.append(f"Date: {review.review_date.strftime('%Y-%m-%d')}")

        if metadata_parts:
            parts.append("Metadata: " + ", ".join(metadata_parts))

        # Add developer response if present
        if review.has_response and review.response_text:
            parts.append(f"Developer Response: {review.response_text}")

        return "\n\n".join(parts)

    def _create_review_metadata(self, review: AppReview, app_store_source: AppStoreSource) -> dict[str, Any]:
        """
        Create metadata dictionary for review.

        Args:
            review: Review instance
            app_store_source: App store source instance

        Returns:
            Metadata dictionary
        """
        metadata = {
            "review_id": review.review_id,
            "app_store_source_id": str(app_store_source.id),
            "app_name": app_store_source.app_name,
            "app_id": app_store_source.app_id,
            "store_type": app_store_source.store_type,
            "rating": review.rating,
            "author_name": review.author_name,
            "review_date": review.review_date.isoformat() if review.review_date else None,
            "has_response": review.has_response,
        }

        # Add optional fields
        if review.title:
            metadata["title"] = review.title
        if review.language:
            metadata["language"] = review.language
        if review.country:
            metadata["country"] = review.country
        if review.app_version:
            metadata["app_version"] = review.app_version
        if review.device_type:
            metadata["device_type"] = review.device_type
        if review.sentiment:
            metadata["sentiment"] = review.sentiment
        if review.sentiment_score is not None:
            metadata["sentiment_score"] = review.sentiment_score
        if review.topics:
            metadata["topics"] = review.topics
        if review.issues:
            metadata["issues"] = review.issues
        if review.features_mentioned:
            metadata["features_mentioned"] = review.features_mentioned
        if review.response_text:
            metadata["response_text"] = review.response_text
        if review.response_date:
            metadata["response_date"] = review.response_date.isoformat()

        return metadata
