"""Google Play Store connector — delegates scraping to the scraper microservice."""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.app_review import AppReview
from src.models.app_store_source import AppStoreSource
from src.services.app_store.review_sync_service import ReviewSyncService

logger = logging.getLogger(__name__)


class GooglePlayConnector:
    """
    Connector for fetching reviews from Google Play Store.

    Scraping is delegated to the synkora-scraper microservice so that
    crawl4ai/playwright are not bundled in the API image.
    """

    def __init__(self, app_store_source: AppStoreSource, db: AsyncSession):
        self.app_store_source = app_store_source
        self.db = db
        self.app_id = app_store_source.app_id
        self.config = app_store_source.config or {}

    async def fetch_reviews(self, count: int = 200, continuation_token: str | None = None) -> dict[str, Any]:
        """Fetch reviews via the scraper microservice."""
        from src.core.scraper_client import get_scraper_client

        logger.info(f"Fetching Google Play reviews for {self.app_id} via scraper service")
        lang = self.config.get("language", "en")
        country = self.config.get("country", "us")

        client = get_scraper_client()
        reviews = await client.scrape_google_play(app_id=self.app_id, country=country, lang=lang, count=count)

        logger.info(f"Fetched {len(reviews)} reviews from scraper service")
        return {"reviews": reviews, "continuation_token": None}

    async def sync_reviews(self, batch_size: int = 200) -> dict[str, Any]:
        """Sync reviews from Google Play Store."""
        started_at = datetime.now(UTC)
        errors = []
        reviews_fetched = 0
        reviews_saved = 0
        reviews_updated = 0

        try:
            result = await self.fetch_reviews(count=batch_size)
            raw_reviews = result["reviews"]
            reviews_fetched = len(raw_reviews)

            for raw_review in raw_reviews:
                try:
                    review_id = raw_review.get("reviewId", "")
                    if not review_id:
                        continue

                    db_result = await self.db.execute(
                        select(AppReview).filter(
                            AppReview.app_store_source_id == self.app_store_source.id,
                            AppReview.review_id == review_id,
                        )
                    )
                    existing_review = db_result.scalar_one_or_none()

                    # Parse date — scraper returns ISO string or datetime
                    at_val = raw_review.get("at")
                    if isinstance(at_val, str):
                        try:
                            at_val = datetime.fromisoformat(at_val.replace("Z", "+00:00"))
                        except Exception:
                            at_val = datetime.now(UTC)

                    if existing_review:
                        existing_review.rating = raw_review.get("score", 0)
                        existing_review.content = raw_review.get("content", "")
                        existing_review.review_date = at_val
                        existing_review.thumbs_up_count = raw_review.get("thumbsUpCount", 0)
                        reply = raw_review.get("replyContent")
                        if reply:
                            existing_review.has_response = True
                            existing_review.response_text = reply
                            existing_review.response_date = raw_review.get("repliedAt")
                        reviews_updated += 1
                    else:
                        review = AppReview(
                            app_store_source_id=self.app_store_source.id,
                            review_id=review_id,
                            author_name=raw_review.get("userName", "Anonymous"),
                            rating=raw_review.get("score", 0),
                            content=raw_review.get("content", ""),
                            language=self.config.get("language", "en"),
                            country=self.config.get("country", "us"),
                            app_version=raw_review.get("reviewCreatedVersion"),
                            review_date=at_val,
                            thumbs_up_count=raw_review.get("thumbsUpCount", 0),
                            has_response=bool(raw_review.get("replyContent")),
                            response_text=raw_review.get("replyContent"),
                            response_date=raw_review.get("repliedAt"),
                        )
                        self.db.add(review)
                        reviews_saved += 1

                except Exception as e:
                    error_msg = f"Error processing review {raw_review.get('reviewId')}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            await self.db.commit()

            kb_sync_result = None
            if self.app_store_source.knowledge_base_id and (reviews_saved > 0 or reviews_updated > 0):
                try:
                    review_ids = [r.get("reviewId") for r in raw_reviews if r.get("reviewId")]
                    db_result = await self.db.execute(
                        select(AppReview).filter(
                            AppReview.app_store_source_id == self.app_store_source.id,
                            AppReview.review_id.in_(review_ids),
                        )
                    )
                    reviews_to_sync = list(db_result.scalars().all())
                    sync_service = ReviewSyncService(self.db)
                    kb_sync_result = await sync_service.sync_reviews_to_kb(self.app_store_source, reviews_to_sync)
                except Exception as e:
                    error_msg = f"Error syncing to knowledge base: {e}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)

            self.app_store_source.last_sync_at = datetime.now(UTC)
            self.app_store_source.next_sync_at = self._calculate_next_sync()
            self.app_store_source.total_reviews_collected = (
                self.app_store_source.total_reviews_collected or 0
            ) + reviews_saved
            self.app_store_source.status = "active"
            await self.db.commit()

            result = {
                "success": True,
                "reviews_fetched": reviews_fetched,
                "reviews_saved": reviews_saved,
                "reviews_updated": reviews_updated,
                "errors": errors,
                "started_at": started_at,
                "completed_at": datetime.now(UTC),
            }
            if kb_sync_result:
                result["kb_sync"] = kb_sync_result
            return result

        except Exception as e:
            error_msg = f"Sync failed: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            self.app_store_source.status = "error"
            await self.db.commit()
            return {
                "success": False,
                "reviews_fetched": reviews_fetched,
                "reviews_saved": reviews_saved,
                "reviews_updated": reviews_updated,
                "errors": errors,
                "started_at": started_at,
                "completed_at": datetime.now(UTC),
            }

    def _calculate_next_sync(self) -> datetime:
        from datetime import timedelta

        frequency = self.app_store_source.sync_frequency or "daily"
        now = datetime.now(UTC)
        match frequency:
            case "hourly":
                return now + timedelta(hours=1)
            case "weekly":
                return now + timedelta(weeks=1)
            case "monthly":
                return now + timedelta(days=30)
            case _:
                return now + timedelta(days=1)

    async def test_connection(self) -> dict[str, Any]:
        try:
            result = await self.fetch_reviews(count=5)
            return {
                "success": True,
                "message": "Successfully connected to Google Play Store",
                "reviews_available": len(result["reviews"]) > 0,
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to connect: {e}"}

    async def get_review_count(self) -> int:
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count())
            .select_from(AppReview)
            .filter(AppReview.app_store_source_id == self.app_store_source.id)
        )
        return result.scalar_one()
