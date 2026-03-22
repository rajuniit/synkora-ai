"""
Review Analysis Service.

Provides analysis functions for app store reviews that can be used by
any agent or called directly from API endpoints.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.app_review import AppReview
from src.models.app_store_source import AppStoreSource
from src.services.agents.config import ModelConfig
from src.services.agents.llm_client import MultiProviderLLMClient
from src.services.performance.llm_client_pool import get_llm_client_pool

logger = logging.getLogger(__name__)


class ReviewAnalysisService:
    """
    Service for analyzing app store reviews.

    This service provides analysis functions that can be used by agents
    or called directly from API endpoints.
    """

    def __init__(self, db_session: AsyncSession, llm_client: MultiProviderLLMClient | None = None):
        """
        Initialize the review analysis service.

        Args:
            db_session: Database session
            llm_client: Optional LLM client (will be created if not provided)
        """
        self.db_session = db_session
        self.llm_client = llm_client

        # Default analysis configuration
        self.analysis_config = {
            "sentiment_categories": ["positive", "negative", "neutral", "mixed"],
            "topic_categories": [
                "ui_ux",
                "performance",
                "features",
                "bugs",
                "crashes",
                "pricing",
                "customer_support",
                "updates",
                "compatibility",
            ],
            "issue_severity_levels": ["critical", "high", "medium", "low"],
        }

    def initialize_llm_client(self, llm_config: ModelConfig) -> None:
        """
        Initialize the LLM client with configuration.

        Uses the LLM client pool to reuse connections and reduce overhead.

        Args:
            llm_config: LLM configuration
        """
        pool = get_llm_client_pool()
        self.llm_client = pool.get_client(
            provider=llm_config.provider,
            api_key=llm_config.api_key,
            model=llm_config.model_name,
            api_base=llm_config.api_base,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
            top_p=llm_config.top_p,
            additional_params=llm_config.additional_params,
        )
        logger.info(f"LLM client initialized from pool: {llm_config.provider}/{llm_config.model_name}")

    async def analyze_review(self, review_id: UUID) -> dict[str, Any]:
        """
        Analyze a single review for sentiment, topics, and issues.

        Args:
            review_id: UUID of the review to analyze

        Returns:
            Analysis results with sentiment, topics, issues, and features
        """
        if not self.llm_client:
            raise RuntimeError("LLM client not initialized. Call initialize_llm_client() first.")

        # Fetch review from database
        stmt = select(AppReview).where(AppReview.id == review_id)
        result = await self.db_session.execute(stmt)
        review = result.scalar_one_or_none()

        if not review:
            raise ValueError(f"Review not found: {review_id}")

        logger.info(f"Analyzing review {review_id} (rating: {review.rating})")

        # Build analysis prompt
        prompt = self._build_review_analysis_prompt(review)

        # Generate analysis using LLM
        response = await self.llm_client.generate_content(
            prompt=prompt,
            temperature=0.3,  # Lower temperature for more consistent analysis
            max_tokens=1000,
        )

        # Parse the response
        analysis = self._parse_analysis_response(response)

        # Update review in database
        review.sentiment = analysis.get("sentiment")
        review.sentiment_score = analysis.get("sentiment_score")
        review.topics = analysis.get("topics")
        review.issues = analysis.get("issues")
        review.features_mentioned = analysis.get("features_mentioned")

        await self.db_session.commit()

        logger.info(
            f"Review {review_id} analyzed: sentiment={analysis.get('sentiment')}, "
            f"topics={len(analysis.get('topics', []))}, "
            f"issues={len(analysis.get('issues', []))}"
        )

        return {
            "review_id": str(review_id),
            "rating": review.rating,
            "analysis": analysis,
            "updated_at": datetime.now(UTC).isoformat(),
        }

    async def analyze_batch(
        self, app_store_source_id: UUID, limit: int = 100, only_unanalyzed: bool = True
    ) -> dict[str, Any]:
        """
        Analyze multiple reviews in batch.

        Args:
            app_store_source_id: UUID of the app store source
            limit: Maximum number of reviews to analyze
            only_unanalyzed: Only analyze reviews without existing analysis

        Returns:
            Batch analysis results
        """
        # Fetch reviews
        stmt = select(AppReview).where(AppReview.app_store_source_id == app_store_source_id)

        if only_unanalyzed:
            stmt = stmt.where(AppReview.sentiment.is_(None))

        stmt = stmt.limit(limit)

        result = await self.db_session.execute(stmt)
        reviews = list(result.scalars().all())

        if not reviews:
            return {"total_reviews": 0, "analyzed_count": 0, "message": "No reviews found for analysis"}

        logger.info(f"Analyzing batch of {len(reviews)} reviews")

        # Analyze each review
        analyzed_count = 0
        failed_count = 0

        for review in reviews:
            try:
                await self.analyze_review(review.id)
                analyzed_count += 1
            except Exception as e:
                logger.error(f"Failed to analyze review {review.id}: {e}")
                failed_count += 1

        return {
            "total_reviews": len(reviews),
            "analyzed_count": analyzed_count,
            "failed_count": failed_count,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def generate_insights(self, app_store_source_id: UUID, limit: int = 500) -> dict[str, Any]:
        """
        Generate high-level insights from analyzed reviews.

        Args:
            app_store_source_id: UUID of the app store source
            limit: Maximum number of reviews to include in analysis

        Returns:
            Insights including trends, top issues, and recommendations
        """
        if not self.llm_client:
            raise RuntimeError("LLM client not initialized. Call initialize_llm_client() first.")

        # Fetch app store source
        stmt = select(AppStoreSource).where(AppStoreSource.id == app_store_source_id)
        result = await self.db_session.execute(stmt)
        source = result.scalar_one_or_none()

        if not source:
            raise ValueError(f"App store source not found: {app_store_source_id}")

        # Fetch analyzed reviews
        stmt = (
            select(AppReview)
            .where(AppReview.app_store_source_id == app_store_source_id, AppReview.sentiment.isnot(None))
            .order_by(AppReview.review_date.desc())
            .limit(limit)
        )

        result = await self.db_session.execute(stmt)
        reviews = list(result.scalars().all())

        if not reviews:
            return {"app_name": source.app_name, "message": "No analyzed reviews available for insights"}

        logger.info(f"Generating insights for {source.app_name} from {len(reviews)} reviews")

        # Calculate statistics
        insights = self.calculate_statistics(reviews)

        # Generate AI-powered insights summary
        prompt = self._build_insights_prompt(source, reviews, insights)

        summary = await self.llm_client.generate_content(
            prompt=prompt,
            temperature=0.5,
            max_tokens=1500,
        )

        return {
            "app_name": source.app_name,
            "store_type": source.store_type,
            "total_reviews_analyzed": len(reviews),
            "statistics": insights,
            "ai_summary": summary,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def calculate_statistics(self, reviews: list[AppReview]) -> dict[str, Any]:
        """
        Calculate statistical insights from a list of reviews.

        Args:
            reviews: List of AppReview objects

        Returns:
            Dictionary of statistics
        """
        total = len(reviews)
        if total == 0:
            return {}

        # Rating distribution
        rating_dist = dict.fromkeys(range(1, 6), 0)
        for review in reviews:
            rating_dist[review.rating] = rating_dist.get(review.rating, 0) + 1

        # Sentiment distribution
        sentiment_dist = {}
        for review in reviews:
            if review.sentiment:
                sentiment_dist[review.sentiment] = sentiment_dist.get(review.sentiment, 0) + 1

        # Topic frequency
        topic_freq = {}
        for review in reviews:
            if review.topics:
                for topic in review.topics:
                    topic_freq[topic] = topic_freq.get(topic, 0) + 1

        # Issue frequency
        issue_freq = {}
        for review in reviews:
            if review.issues:
                for issue in review.issues:
                    desc = issue.get("description", "Unknown")
                    issue_freq[desc] = issue_freq.get(desc, 0) + 1

        # Feature mentions
        feature_freq = {}
        for review in reviews:
            if review.features_mentioned:
                for feature in review.features_mentioned:
                    feature_freq[feature] = feature_freq.get(feature, 0) + 1

        # Calculate average rating
        avg_rating = sum(r.rating for r in reviews) / total

        # Sort and get top items
        top_topics = sorted(topic_freq.items(), key=lambda x: x[1], reverse=True)
        top_issues = sorted(issue_freq.items(), key=lambda x: x[1], reverse=True)
        top_features = sorted(feature_freq.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_reviews": total,
            "average_rating": avg_rating,
            "rating_distribution": rating_dist,
            "sentiment_distribution": sentiment_dist,
            "top_topics": [{"topic": t, "count": c} for t, c in top_topics[:10]],
            "top_issues": [{"issue": i, "count": c} for i, c in top_issues[:10]],
            "top_features": [{"feature": f, "count": c} for f, c in top_features[:10]],
        }

    def _build_review_analysis_prompt(self, review: AppReview) -> str:
        """Build prompt for analyzing a single review."""
        prompt = f"""Analyze the following app store review and provide a structured analysis.

Review Details:
- Rating: {review.rating}/5 stars
- Title: {review.title or "N/A"}
- Content: {review.content}
- App Version: {review.app_version or "N/A"}
- Language: {review.language or "N/A"}

Please analyze this review and provide the following in JSON format:

1. **Sentiment**: Classify as one of: {", ".join(self.analysis_config["sentiment_categories"])}
2. **Sentiment Score**: A float between -1 (very negative) and 1 (very positive)
3. **Topics**: List of relevant topics from: {", ".join(self.analysis_config["topic_categories"])}
4. **Issues**: List of specific issues mentioned (if any), each with:
   - description: Brief description of the issue
   - severity: One of {", ".join(self.analysis_config["issue_severity_levels"])}
   - category: The topic category it belongs to
5. **Features Mentioned**: List of specific features or aspects mentioned (if any)

Return ONLY valid JSON in this exact format:
{{
  "sentiment": "positive|negative|neutral|mixed",
  "sentiment_score": 0.0,
  "topics": ["topic1", "topic2"],
  "issues": [
    {{"description": "issue description", "severity": "high", "category": "bugs"}}
  ],
  "features_mentioned": ["feature1", "feature2"]
}}

Be concise and accurate. If no issues or features are mentioned, use empty arrays."""

        return prompt

    def _build_insights_prompt(
        self, source: AppStoreSource, reviews: list[AppReview], statistics: dict[str, Any]
    ) -> str:
        """Build prompt for generating insights summary."""
        # Sample recent reviews for context
        recent_reviews_sample = reviews[:10]
        reviews_text = "\n\n".join(
            [f"Rating: {r.rating}/5 - {r.title or ''}\n{r.content[:200]}..." for r in recent_reviews_sample]
        )

        prompt = f"""Generate a comprehensive insights summary for the app "{source.app_name}" based on user reviews.

Statistics:
- Total Reviews Analyzed: {statistics["total_reviews"]}
- Average Rating: {statistics["average_rating"]:.2f}/5
- Sentiment Distribution: {json.dumps(statistics["sentiment_distribution"])}
- Top Topics: {json.dumps(statistics["top_topics"][:5])}
- Top Issues: {json.dumps(statistics["top_issues"][:5])}

Sample Recent Reviews:
{reviews_text}

Please provide:

1. **Overall Sentiment Summary**: Brief overview of user sentiment
2. **Key Strengths**: What users love about the app (2-3 points)
3. **Main Pain Points**: Critical issues users are facing (2-3 points)
4. **Trending Topics**: What users are talking about most
5. **Actionable Recommendations**: 3-5 specific recommendations for improvement

Format your response in clear, professional language suitable for product managers and developers."""

        return prompt

    def _parse_analysis_response(self, response: str) -> dict[str, Any]:
        """Parse LLM response into structured analysis."""
        try:
            # Try to extract JSON from response
            # Handle cases where LLM adds markdown code blocks
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            analysis = json.loads(response.strip())

            # Validate and normalize
            analysis["sentiment"] = analysis.get("sentiment", "neutral").lower()
            analysis["sentiment_score"] = float(analysis.get("sentiment_score", 0.0))
            analysis["topics"] = analysis.get("topics", [])
            analysis["issues"] = analysis.get("issues", [])
            analysis["features_mentioned"] = analysis.get("features_mentioned", [])

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analysis response: {e}")
            logger.debug(f"Response was: {response}")

            # Return default analysis
            return {
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "topics": [],
                "issues": [],
                "features_mentioned": [],
            }
