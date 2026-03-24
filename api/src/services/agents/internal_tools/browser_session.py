"""
Browser Session — stub module.

Browser sessions are now managed server-side by the synkora-scraper microservice.
This module is kept for import compatibility but no longer manages Playwright directly.
"""


def to_ai_friendly_error(error: Exception, context: str) -> str:
    """Convert errors to AI-friendly messages."""
    return str(error)


class BrowserSession:
    """
    Stub — all browser session state lives in synkora-scraper.
    Kept so callers that reference BrowserSession continue to import cleanly.
    Actual operations delegate to ScraperServiceClient.
    """

    @classmethod
    async def get_or_create(cls, session_id: str = "default"):
        """Return the session_id; the scraper manages state server-side."""
        return session_id

    @classmethod
    async def close_session(cls, session_id: str = "default") -> dict:
        from src.core.scraper_client import get_scraper_client

        return await get_scraper_client().browser_close_session(session_id=session_id)
