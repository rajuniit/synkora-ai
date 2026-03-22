"""Apple App Store connector for fetching app reviews using crawl4ai."""

import hashlib
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from crawl4ai import AsyncWebCrawler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.app_review import AppReview
from src.models.app_store_source import AppStoreSource
from src.services.app_store.review_sync_service import ReviewSyncService

logger = logging.getLogger(__name__)


class AppleAppStoreConnector:
    """
    Connector for fetching reviews from Apple App Store using crawl4ai.

    Uses crawl4ai with Playwright to scrape reviews from the web interface.
    """

    def __init__(self, app_store_source: AppStoreSource, db: AsyncSession):
        """
        Initialize the Apple App Store connector.

        Args:
            app_store_source: AppStoreSource model instance
            db: Database session
        """
        self.app_store_source = app_store_source
        self.db = db
        self.app_id = app_store_source.app_id
        self.app_name = app_store_source.app_name
        self.config = app_store_source.config or {}

    def _build_review_url(self, country: str = "us") -> str:
        """Build the Apple App Store review URL."""
        return f"https://apps.apple.com/{country}/app/id{self.app_id}"

    def _generate_review_id(self, review_data: dict[str, Any]) -> str:
        """
        Generate a unique review ID from review data.

        Apple doesn't provide unique IDs, so we create one from content hash.
        """
        # Create a unique string from review data
        unique_str = (
            f"{review_data.get('author', '')}_{review_data.get('date', '')}_{review_data.get('content', '')[:100]}"
        )
        # Generate hash
        return hashlib.md5(unique_str.encode()).hexdigest()

    def _parse_reviews_from_html(self, html: str) -> list[dict[str, Any]]:
        """
        Parse reviews from Apple App Store HTML.

        Args:
            html: HTML content from the page

        Returns:
            List of review dictionaries
        """
        reviews = []

        try:
            # Extract review data from the page
            # Apple uses structured data in script tags
            script_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
            scripts = re.findall(script_pattern, html, re.DOTALL)

            for script in scripts:
                try:
                    data = json.loads(script)
                    if isinstance(data, dict) and data.get("@type") == "Review":
                        review = self._extract_review_from_structured_data(data)
                        if review:
                            reviews.append(review)
                    elif isinstance(data, list):
                        # Sometimes reviews are in an array
                        for item in data:
                            if isinstance(item, dict) and item.get("@type") == "Review":
                                review = self._extract_review_from_structured_data(item)
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
            author = data.get("author", {})
            if isinstance(author, dict):
                author_name = author.get("name", "Anonymous")
            else:
                author_name = str(author) if author else "Anonymous"

            review_body = data.get("reviewBody", "")
            review_date_str = data.get("datePublished", "")

            # Parse date
            try:
                if review_date_str:
                    review_date = datetime.fromisoformat(review_date_str.replace("Z", "+00:00"))
                else:
                    review_date = datetime.now(UTC)
            except:
                review_date = datetime.now(UTC)

            review_data = {
                "author": author_name,
                "rating": int(data.get("reviewRating", {}).get("ratingValue", 0)),
                "title": data.get("name", ""),
                "content": review_body,
                "date": review_date,
                "version": None,
                "developerResponse": None,
            }

            # Generate unique ID
            review_data["reviewId"] = self._generate_review_id(review_data)

            return review_data
        except Exception as e:
            logger.error(f"Error extracting review from structured data: {str(e)}")
            return None

    def _parse_reviews_from_elements(self, html: str) -> list[dict[str, Any]]:
        """
        Parse reviews from HTML elements.

        Uses BeautifulSoup to parse the HTML and extract review data.
        """
        reviews = []

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Find all review elements
            # Apple uses div elements with specific classes for reviews
            review_elements = soup.find_all("div", class_="we-customer-review")

            logger.info(f"Found {len(review_elements)} review elements in HTML")

            for review_elem in review_elements:
                try:
                    # Extract author name
                    author_elem = review_elem.find("span", class_="we-customer-review__user")
                    author = author_elem.text.strip() if author_elem else "Anonymous"

                    # Extract rating
                    rating_elem = review_elem.find("figure", class_="we-star-rating")
                    rating = 0
                    if rating_elem and "aria-label" in rating_elem.attrs:
                        # Extract rating from aria-label like "5 out of 5"
                        rating_text = rating_elem["aria-label"]
                        rating_match = re.search(r"(\d+)", rating_text)
                        if rating_match:
                            rating = int(rating_match.group(1))

                    # Extract title
                    title_elem = review_elem.find("h3", class_="we-customer-review__title")
                    title = title_elem.text.strip() if title_elem else ""

                    # Extract content
                    content_elem = review_elem.find("p", class_="we-customer-review__body")
                    content = content_elem.text.strip() if content_elem else ""

                    # Extract date
                    date_elem = review_elem.find("time")
                    review_date = datetime.now(UTC)
                    if date_elem and "datetime" in date_elem.attrs:
                        try:
                            review_date = datetime.fromisoformat(date_elem["datetime"].replace("Z", "+00:00"))
                        except:
                            pass

                    # Extract version if available
                    version_elem = review_elem.find("span", class_="we-customer-review__version")
                    version = version_elem.text.strip() if version_elem else None

                    # Extract developer response if exists
                    response_elem = review_elem.find("div", class_="we-customer-review__response")
                    developer_response = None
                    if response_elem:
                        response_body = response_elem.find("p", class_="we-customer-review__response-body")
                        response_date_elem = response_elem.find("time")
                        if response_body:
                            developer_response = {"body": response_body.text.strip(), "modified": None}
                            if response_date_elem and "datetime" in response_date_elem.attrs:
                                try:
                                    developer_response["modified"] = datetime.fromisoformat(
                                        response_date_elem["datetime"].replace("Z", "+00:00")
                                    )
                                except:
                                    pass

                    review_data = {
                        "author": author,
                        "rating": rating,
                        "title": title,
                        "content": content,
                        "date": review_date,
                        "version": version,
                        "developerResponse": developer_response,
                    }

                    # Generate unique ID
                    review_data["reviewId"] = self._generate_review_id(review_data)

                    reviews.append(review_data)

                except Exception as e:
                    logger.error(f"Error parsing individual review: {str(e)}")
                    continue

            logger.info(f"Successfully parsed {len(reviews)} reviews from HTML")

        except ImportError:
            logger.error("BeautifulSoup not installed. Cannot parse HTML reviews.")
        except Exception as e:
            logger.error(f"Error parsing reviews from HTML: {str(e)}")

        return reviews

    async def fetch_reviews(self, count: int = 200) -> list[dict[str, Any]]:
        """
        Fetch reviews from Apple App Store using crawl4ai.

        Args:
            count: Number of reviews to fetch (target, actual may vary)

        Returns:
            List of review dictionaries
        """
        try:
            logger.info(
                f"Fetching reviews for app {self.app_name} (ID: {self.app_id}) from Apple App Store using crawl4ai"
            )

            # Get configuration
            country = self.config.get("country", "my")

            # Build URL
            url = self._build_review_url(country)

            # Fetch page with crawl4ai
            async with AsyncWebCrawler(verbose=True) as crawler:
                result = await crawler.arun(
                    url=url,
                    # Extract text and HTML
                    bypass_cache=True,
                )

                if not result.success:
                    raise Exception(f"Failed to fetch page: {result.error_message}")

                # Save HTML to file for debugging
                import os

                debug_dir = "/tmp/apple_store_debug"
                os.makedirs(debug_dir, exist_ok=True)
                html_file = f"{debug_dir}/apple_store_{self.app_id}.html"
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(result.html)
                logger.info(f"Saved HTML to {html_file} for debugging")

                # Parse reviews from HTML
                reviews = self._parse_reviews_from_html(result.html)

                logger.info(f"Fetched {len(reviews)} reviews from Apple App Store")

                return reviews[:count]  # Limit to requested count

        except Exception as e:
            logger.error(f"Error fetching Apple App Store reviews: {str(e)}")
            raise

    async def sync_reviews(self, batch_size: int = 200) -> dict[str, Any]:
        """
        Sync reviews from Apple App Store.

        Args:
            batch_size: Number of reviews to fetch

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
            raw_reviews = await self.fetch_reviews(count=batch_size)
            reviews_fetched = len(raw_reviews)

            # Process each review
            for raw_review in raw_reviews:
                try:
                    # Get review ID
                    review_id = raw_review.get("reviewId")
                    if not review_id:
                        continue

                    # Check if review already exists
                    result = await self.db.execute(
                        select(AppReview).filter(
                            AppReview.app_store_source_id == self.app_store_source.id, AppReview.review_id == review_id
                        )
                    )
                    existing_review = result.scalar_one_or_none()

                    if existing_review:
                        # Update existing review
                        existing_review.rating = raw_review.get("rating", 0)
                        existing_review.title = raw_review.get("title", "")
                        existing_review.content = raw_review.get("content", "")
                        existing_review.review_date = raw_review.get("date")

                        # Update response if exists
                        reply = raw_review.get("developerResponse")
                        if reply:
                            existing_review.has_response = True
                            existing_review.response_text = reply.get("body", "")
                            existing_review.response_date = reply.get("modified")

                        reviews_updated += 1
                    else:
                        # Create new review
                        review = AppReview(
                            app_store_source_id=self.app_store_source.id,
                            review_id=review_id,
                            author_name=raw_review.get("author", "Anonymous"),
                            rating=raw_review.get("rating", 0),
                            title=raw_review.get("title", ""),
                            content=raw_review.get("content", ""),
                            language=self.config.get("language", "en"),
                            country=self.config.get("country", "us"),
                            app_version=raw_review.get("version"),
                            review_date=raw_review.get("date"),
                            has_response=bool(raw_review.get("developerResponse")),
                            response_text=raw_review.get("developerResponse", {}).get("body")
                            if raw_review.get("developerResponse")
                            else None,
                            response_date=raw_review.get("developerResponse", {}).get("modified")
                            if raw_review.get("developerResponse")
                            else None,
                        )
                        self.db.add(review)
                        reviews_saved += 1

                except Exception as e:
                    error_msg = f"Error processing review: {str(e)}"
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
                    review_ids = [r.get("reviewId") for r in raw_reviews if r.get("reviewId")]
                    result = await self.db.execute(
                        select(AppReview).filter(
                            AppReview.app_store_source_id == self.app_store_source.id,
                            AppReview.review_id.in_(review_ids),
                        )
                    )
                    reviews_to_sync = list(result.scalars().all())

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
        Test connection to Apple App Store.

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
            reviews = await self.fetch_reviews(count=5)

            return {
                "success": True,
                "message": "Successfully connected to Apple App Store",
                "reviews_available": len(reviews) > 0,
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
