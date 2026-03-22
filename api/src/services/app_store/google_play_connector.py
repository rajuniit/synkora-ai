"""Google Play Store connector for fetching app reviews using crawl4ai."""

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.app_review import AppReview
from src.models.app_store_source import AppStoreSource
from src.services.app_store.review_sync_service import ReviewSyncService

logger = logging.getLogger(__name__)


class GooglePlayConnector:
    """
    Connector for fetching reviews from Google Play Store using crawl4ai.

    Uses crawl4ai with Playwright to scrape reviews from the web interface.
    """

    def __init__(self, app_store_source: AppStoreSource, db: AsyncSession):
        """
        Initialize the Google Play connector.

        Args:
            app_store_source: AppStoreSource model instance
            db: Database session
        """
        self.app_store_source = app_store_source
        self.db = db
        self.app_id = app_store_source.app_id
        self.config = app_store_source.config or {}

    def _build_review_url(self, lang: str = "en", country: str = "us") -> str:
        """Build the Google Play Store review URL."""
        return f"https://play.google.com/store/apps/details?id={self.app_id}&hl={lang}&gl={country}&showAllReviews=true"

    def _parse_reviews_from_html(self, html: str) -> list[dict[str, Any]]:
        """
        Parse reviews from Google Play Store HTML.

        Args:
            html: HTML content from the page

        Returns:
            List of review dictionaries
        """
        reviews = []

        try:
            # Save HTML to file for debugging
            import os
            import tempfile

            temp_dir = tempfile.gettempdir()
            html_file = os.path.join(temp_dir, f"google_play_{self.app_id}.html")
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(html)
            logger.info(f"Saved HTML to {html_file} for debugging (length: {len(html)} chars)")

            # Extract review data from the page
            # Google Play uses structured data in script tags
            script_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
            scripts = re.findall(script_pattern, html, re.DOTALL)

            for script in scripts:
                try:
                    data = json.loads(script)
                    if isinstance(data, dict) and data.get("@type") == "Review":
                        review = self._extract_review_from_structured_data(data)
                        if review:
                            reviews.append(review)
                except json.JSONDecodeError:
                    continue

            # If no structured data found, try parsing from HTML elements
            if not reviews:
                reviews = self._parse_reviews_from_elements(html)

        except Exception as e:
            logger.error(f"Error parsing reviews from HTML: {str(e)}")

        return reviews

    def _extract_review_from_structured_data(self, data: dict) -> dict[str, Any] | None:
        """Extract review information from structured data."""
        try:
            review = {
                "reviewId": data.get("identifier", ""),
                "userName": data.get("author", {}).get("name", "Anonymous"),
                "score": int(data.get("reviewRating", {}).get("ratingValue", 0)),
                "content": data.get("reviewBody", ""),
                "at": datetime.fromisoformat(data.get("datePublished", "").replace("Z", "+00:00")),
                "thumbsUpCount": 0,
                "reviewCreatedVersion": None,
                "replyContent": None,
                "repliedAt": None,
            }

            # Extract reply if exists
            if "interactionStatistic" in data:
                for stat in data.get("interactionStatistic", []):
                    if stat.get("interactionType") == "http://schema.org/LikeAction":
                        review["thumbsUpCount"] = int(stat.get("userInteractionCount", 0))

            return review
        except Exception as e:
            logger.error(f"Error extracting review from structured data: {str(e)}")
            return None

    def _parse_reviews_from_elements(self, html: str) -> list[dict[str, Any]]:
        """
        Parse reviews from HTML elements using BeautifulSoup.

        Google Play uses a specific HTML structure for reviews.
        This method extracts reviews from the page's HTML.
        """
        reviews = []

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Save HTML for debugging
            logger.debug(f"HTML length: {len(html)} characters")

            # Google Play review structure: Reviews are in <div class="EGFGHd"> containers
            review_containers = soup.find_all("div", class_="EGFGHd")

            logger.info(f"Found {len(review_containers)} review containers with class 'EGFGHd'")

            for idx, container in enumerate(review_containers[:200]):  # Limit to 200 reviews
                try:
                    review = self._extract_review_from_container(container)
                    if review and review.get("content") and len(review["content"]) > 20:
                        # Validate it's not just metadata
                        if not review["content"].startswith(("people found", "Rated", "stars")):
                            reviews.append(review)
                            logger.debug(f"Extracted review {idx + 1}: {review['content'][:100]}...")
                except Exception as e:
                    logger.debug(f"Error extracting review from container {idx}: {e}")
                    continue

            logger.info(f"Successfully parsed {len(reviews)} valid reviews from HTML")

        except Exception as e:
            logger.error(f"Error parsing reviews from HTML: {e}", exc_info=True)

        return reviews

    def _extract_review_from_container(self, container) -> dict[str, Any] | None:
        """Extract review data from a BeautifulSoup container element."""
        try:
            # Extract review ID from data-review-id attribute in header
            header = container.find("header", class_="c1bOId")
            review_id = ""
            if header:
                review_id = header.get("data-review-id", "")

            if not review_id:
                # Generate a unique ID
                review_id = f"review_{hash(str(container)[:100])}"

            # Extract author name from X5PpBb class
            author_name = "Anonymous"
            author_elem = container.find("div", class_="X5PpBb")
            if author_elem:
                author_name = author_elem.get_text(strip=True)

            # Extract rating from aria-label in iXRFPc class
            rating = 0
            rating_container = container.find("div", class_="iXRFPc")
            if rating_container:
                aria_label = rating_container.get("aria-label", "")
                rating_match = re.search(r"Rated (\d+) star", aria_label)
                if rating_match:
                    rating = int(rating_match.group(1))

            # Extract review content from h3YV2d class
            content = ""
            content_elem = container.find("div", class_="h3YV2d")
            if content_elem:
                content = content_elem.get_text(strip=True)

            # Skip if no valid content
            if not content or len(content) < 20:
                return None

            # Extract date from bp9Aid class
            review_date = datetime.now(UTC)
            date_elem = container.find("span", class_="bp9Aid")
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                try:
                    from dateutil import parser

                    review_date = parser.parse(date_text)
                except:
                    # If parsing fails, use current date
                    pass

            # Extract thumbs up count from AJTPZc class
            thumbs_up = 0
            helpful_elem = container.find("div", class_="AJTPZc")
            if helpful_elem:
                helpful_text = helpful_elem.get_text(strip=True)
                thumbs_match = re.search(r"(\d+)\s+people found this", helpful_text)
                if thumbs_match:
                    thumbs_up = int(thumbs_match.group(1))

            # Extract developer response from ocpBU class
            response_text = None
            response_date = None
            response_container = container.find("div", class_="ocpBU")
            if response_container:
                # Get response text from ras4vb class
                response_elem = response_container.find("div", class_="ras4vb")
                if response_elem:
                    response_text = response_elem.get_text(strip=True)

                # Get response date from I9Jtec class
                response_date_elem = response_container.find("div", class_="I9Jtec")
                if response_date_elem:
                    try:
                        from dateutil import parser

                        response_date = parser.parse(response_date_elem.get_text(strip=True))
                    except:
                        response_date = datetime.now(UTC)

            logger.debug(
                f"Extracted review - Author: {author_name}, Rating: {rating}, Content length: {len(content)}, Thumbs up: {thumbs_up}"
            )

            return {
                "reviewId": review_id,
                "userName": author_name,
                "score": rating if rating > 0 else 3,
                "content": content,
                "at": review_date,
                "thumbsUpCount": thumbs_up,
                "reviewCreatedVersion": None,
                "replyContent": response_text,
                "repliedAt": response_date,
            }

        except Exception as e:
            logger.debug(f"Error extracting review from container: {e}", exc_info=True)
            return None

    async def fetch_reviews(self, count: int = 200, continuation_token: str | None = None) -> dict[str, Any]:
        """
        Fetch reviews from Google Play Store using crawl4ai.

        Args:
            count: Number of reviews to fetch (target, actual may vary)
            continuation_token: Token for pagination (not used in current implementation)

        Returns:
            Dictionary with reviews and continuation token:
                {
                    "reviews": List[Dict],
                    "continuation_token": str or None
                }
        """
        try:
            logger.info(f"Fetching reviews for app {self.app_id} from Google Play using crawl4ai")

            # Get configuration
            lang = self.config.get("language", "en")
            country = self.config.get("country", "us")

            # Build URL
            url = self._build_review_url(lang, country)

            # Fetch page with crawl4ai
            async with AsyncWebCrawler(verbose=True) as crawler:
                result = await crawler.arun(
                    url=url,
                    # Wait for page to load
                    wait_for="css:body",
                    # Click "See all reviews" button and scroll in modal
                    js_code="""
                    async function loadReviews() {
                        console.log('▶️ Starting to load reviews...');

                        const sleep = (ms) => new Promise(r => setTimeout(r, ms));

                        // Wait for the page to render
                        await sleep(4000);

                        // Try clicking "See all reviews"
                        let seeAllBtn = Array.from(document.querySelectorAll('button, div[role="button"]'))
                            .find(el => /see all|all reviews|reviews/i.test(el.textContent));
                        if (seeAllBtn) {
                            seeAllBtn.click();
                            console.log('✅ Clicked "See all reviews"');
                            await sleep(3000);
                        } else {
                            console.warn('⚠️ Could not find "See all reviews" button, fallback to scrolling page');
                        }

                        // Wait for modal to appear
                        let modal = null;
                        for (let i = 0; i < 10; i++) {
                            modal = document.querySelector('div[role="dialog"] div[style*="overflow"]');
                            if (modal) break;
                            await sleep(1000);
                        }

                        if (!modal) {
                            console.warn('⚠️ No modal found, scrolling main page instead');
                            for (let i = 0; i < 20; i++) {
                                window.scrollTo(0, document.body.scrollHeight);
                                await sleep(2000);
                            }
                            return;
                        }

                        console.log('✅ Found reviews modal, starting scroll inside modal...');

                        let lastHeight = 0;
                        let sameScrolls = 0;
                        const maxScrolls = 60; // try 60 scroll cycles (enough for hundreds of reviews)

                        for (let i = 0; i < maxScrolls; i++) {
                            modal.scrollTo(0, modal.scrollHeight);
                            await sleep(2000);

                            const newHeight = modal.scrollHeight;
                            if (newHeight === lastHeight) {
                                sameScrolls++;
                                if (sameScrolls >= 3) {
                                    console.log('🛑 Reached end of modal content');
                                    break;
                                }
                            } else {
                                sameScrolls = 0;
                                lastHeight = newHeight;
                            }
                            console.log(`↕️ Scroll ${i + 1}/${maxScrolls}, height: ${newHeight}`);
                        }

                        console.log('✅ Finished loading reviews');
                    }

                    await loadReviews();
                    """,
                    # Extract text and HTML
                    bypass_cache=True,
                    # Increase timeout for loading all reviews
                    page_timeout=120000,  # 120 seconds (2 minutes)
                )

                if not result.success:
                    raise Exception(f"Failed to fetch page: {result.error_message}")

                # Parse reviews from HTML
                reviews = self._parse_reviews_from_html(result.html)

                logger.info(f"Fetched {len(reviews)} reviews from Google Play")

                return {
                    "reviews": reviews[:count],  # Limit to requested count
                    "continuation_token": None,  # Pagination not implemented yet
                }

        except Exception as e:
            logger.error(f"Error fetching Google Play reviews: {str(e)}")
            raise

    async def sync_reviews(self, batch_size: int = 200) -> dict[str, Any]:
        """
        Sync reviews from Google Play Store.

        Args:
            batch_size: Number of reviews to fetch per batch

        Returns:
            Sync result dictionary:
                {
                    "success": bool,
                    "reviews_fetched": int,
                    "reviews_saved": int,
                    "reviews_updated": int,
                    "errors": List[str]
                }
        """
        started_at = datetime.now(UTC)
        errors = []
        reviews_fetched = 0
        reviews_saved = 0
        reviews_updated = 0

        try:
            # Fetch reviews
            result = await self.fetch_reviews(count=batch_size)
            raw_reviews = result["reviews"]
            reviews_fetched = len(raw_reviews)

            # Process each review
            for raw_review in raw_reviews:
                try:
                    # Check if review already exists
                    review_id = raw_review["reviewId"]
                    if not review_id:
                        continue

                    db_result = await self.db.execute(
                        select(AppReview).filter(
                            AppReview.app_store_source_id == self.app_store_source.id, AppReview.review_id == review_id
                        )
                    )
                    existing_review = db_result.scalar_one_or_none()

                    if existing_review:
                        # Update existing review
                        existing_review.rating = raw_review["score"]
                        existing_review.content = raw_review["content"]
                        existing_review.review_date = raw_review["at"]
                        existing_review.thumbs_up_count = raw_review.get("thumbsUpCount", 0)

                        # Update response if exists
                        reply = raw_review.get("replyContent")
                        if reply:
                            existing_review.has_response = True
                            existing_review.response_text = reply
                            existing_review.response_date = raw_review.get("repliedAt")

                        reviews_updated += 1
                    else:
                        # Create new review
                        review = AppReview(
                            app_store_source_id=self.app_store_source.id,
                            review_id=review_id,
                            author_name=raw_review.get("userName", "Anonymous"),
                            rating=raw_review["score"],
                            content=raw_review["content"],
                            language=self.config.get("language", "en"),
                            country=self.config.get("country", "us"),
                            app_version=raw_review.get("reviewCreatedVersion"),
                            review_date=raw_review["at"],
                            thumbs_up_count=raw_review.get("thumbsUpCount", 0),
                            has_response=bool(raw_review.get("replyContent")),
                            response_text=raw_review.get("replyContent"),
                            response_date=raw_review.get("repliedAt"),
                        )
                        self.db.add(review)
                        reviews_saved += 1

                except Exception as e:
                    error_msg = f"Error processing review {raw_review.get('reviewId')}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            # Commit changes
            await self.db.commit()

            # Sync to knowledge base if configured
            kb_sync_result = None
            if self.app_store_source.knowledge_base_id and (reviews_saved > 0 or reviews_updated > 0):
                try:
                    logger.info(
                        f"Syncing {reviews_saved + reviews_updated} reviews to knowledge base "
                        f"{self.app_store_source.knowledge_base_id}"
                    )

                    # Get all reviews that were just saved/updated
                    review_ids = [r["reviewId"] for r in raw_reviews if r.get("reviewId")]
                    db_result = await self.db.execute(
                        select(AppReview).filter(
                            AppReview.app_store_source_id == self.app_store_source.id,
                            AppReview.review_id.in_(review_ids),
                        )
                    )
                    reviews_to_sync = list(db_result.scalars().all())

                    # Sync to knowledge base
                    sync_service = ReviewSyncService(self.db)
                    kb_sync_result = await sync_service.sync_reviews_to_kb(self.app_store_source, reviews_to_sync)

                    if kb_sync_result.get("success"):
                        logger.info(
                            f"Knowledge base sync completed: "
                            f"{kb_sync_result['reviews_synced']} reviews synced, "
                            f"{kb_sync_result['reviews_embedded']} embedded, "
                            f"{kb_sync_result['total_chunks']} chunks generated"
                        )
                    else:
                        error_msg = f"Knowledge base sync failed: {kb_sync_result.get('error')}"
                        logger.error(error_msg)
                        errors.append(error_msg)

                except Exception as e:
                    error_msg = f"Error syncing to knowledge base: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)

            # Update app store source
            self.app_store_source.last_sync_at = datetime.now(UTC)
            self.app_store_source.next_sync_at = self._calculate_next_sync()
            self.app_store_source.total_reviews_collected = (
                self.app_store_source.total_reviews_collected or 0
            ) + reviews_saved
            self.app_store_source.status = "active"
            await self.db.commit()

            logger.info(f"Sync completed: {reviews_fetched} fetched, {reviews_saved} saved, {reviews_updated} updated")

            result = {
                "success": True,
                "reviews_fetched": reviews_fetched,
                "reviews_saved": reviews_saved,
                "reviews_updated": reviews_updated,
                "errors": errors,
                "started_at": started_at,
                "completed_at": datetime.now(UTC),
            }

            # Add KB sync results if available
            if kb_sync_result:
                result["kb_sync"] = kb_sync_result

            return result

        except Exception as e:
            error_msg = f"Sync failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

            # Update app store source with error
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
        """Calculate next sync time based on sync frequency."""
        from datetime import timedelta

        frequency = self.app_store_source.sync_frequency or "daily"
        now = datetime.now(UTC)

        if frequency == "hourly":
            return now + timedelta(hours=1)
        elif frequency == "daily":
            return now + timedelta(days=1)
        elif frequency == "weekly":
            return now + timedelta(weeks=1)
        elif frequency == "monthly":
            return now + timedelta(days=30)
        else:
            return now + timedelta(days=1)  # Default to daily

    async def test_connection(self) -> dict[str, Any]:
        """
        Test connection to Google Play Store.

        Returns:
            Dictionary with test results:
                {
                    "success": bool,
                    "message": str,
                    "reviews_available": bool (if successful)
                }
        """
        try:
            # Try to fetch just a few reviews to test connection
            result = await self.fetch_reviews(count=5)

            return {
                "success": True,
                "message": "Successfully connected to Google Play Store",
                "reviews_available": len(result["reviews"]) > 0,
            }

        except Exception as e:
            return {"success": False, "message": f"Failed to connect: {str(e)}"}

    async def get_review_count(self) -> int:
        """
        Get total number of reviews stored for this app.

        Returns:
            Total review count
        """
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count())
            .select_from(AppReview)
            .filter(AppReview.app_store_source_id == self.app_store_source.id)
        )
        return result.scalar_one()
