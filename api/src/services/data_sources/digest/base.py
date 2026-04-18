"""Abstract base class for daily digest extractors."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from datetime import date as DateType
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.data_source import DataSource

logger = logging.getLogger(__name__)

# Common structured digest schema returned by all extractors after LLM processing
DIGEST_JSON_SCHEMA = """{
    "total_items": <integer>,
    "activity_level": "<low|medium|high>",
    "highlights": ["<string>", ...],
    "key_decisions": ["<string>", ...],
    "action_items": [{"task": "<string>", "owner": "<name or null>"}, ...],
    "topics": ["<string>", ...],
    "source_specific": { <source-dependent breakdown object> }
}"""


@dataclass
class RawItem:
    """A single raw item (message, email, commit, etc.) from a data source."""

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseDigestExtractor(ABC):
    """
    Abstract base for data source digest extractors.

    Each extractor fetches raw items for a target date and formats
    them into a text blob suitable for LLM processing.
    """

    @property
    @abstractmethod
    def source_type(self) -> str:
        """DataSourceType value this extractor handles, e.g. 'SLACK'."""

    @abstractmethod
    async def fetch_items(
        self,
        data_source: DataSource,
        start: datetime,
        end: datetime,
        db: AsyncSession,
    ) -> list[RawItem]:
        """
        Fetch all raw items from the data source for the given date range.

        Args:
            data_source: The DataSource model instance.
            start: Start of the range (inclusive, UTC-aware).
            end: End of the range (exclusive, UTC-aware).
            db: Async database session.

        Returns:
            List of RawItem instances.
        """

    @abstractmethod
    def build_prompt(self, items: list[RawItem], target_date: DateType) -> str:
        """
        Build the LLM prompt from the raw items.

        The prompt must instruct the LLM to return JSON matching DIGEST_JSON_SCHEMA.
        """

    def date_range(self, target_date: DateType) -> tuple[datetime, datetime]:
        """Return (start, end) UTC datetimes covering the full target date."""
        start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=UTC)
        end = start + timedelta(days=1)
        return start, end
