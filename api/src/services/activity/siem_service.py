"""SIEM webhook streaming service.

Forwards audit events to an external SIEM (Security Information and Event
Management) system via HTTP webhook.  The integration is completely optional:
if SIEM_WEBHOOK_URL is not set, every call is a no-op.

Configuration (env vars)
------------------------
SIEM_WEBHOOK_URL    – destination URL for POST requests (required to enable)
SIEM_WEBHOOK_SECRET – optional HMAC-SHA256 signing secret; when set, each
                      request includes an `X-SIEM-Signature: sha256=<hex>`
                      header so the receiver can verify authenticity.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

# Module-level singleton — created once and reused so the underlying TCP
# connection pool is shared across all fire-and-forget tasks.
_siem_service: SIEMWebhookService | None = None


def get_siem_service() -> SIEMWebhookService:
    """Return (and lazily create) the module-level SIEM service singleton."""
    global _siem_service
    if _siem_service is None:
        _siem_service = SIEMWebhookService()
    return _siem_service


class SIEMWebhookService:
    """Fire-and-forget SIEM event forwarder."""

    def __init__(self) -> None:
        self._webhook_url: str | None = os.getenv("SIEM_WEBHOOK_URL")
        self._webhook_secret: str | None = os.getenv("SIEM_WEBHOOK_SECRET")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def stream_event(self, event: dict) -> None:
        """Send *event* to the configured SIEM webhook.

        This is a fire-and-forget coroutine — callers should wrap it in
        ``asyncio.create_task(...)`` so it never blocks the audit write path.
        All exceptions are swallowed; a SIEM outage must never prevent an
        audit log entry from being persisted.

        Args:
            event: Arbitrary dict that will be serialised to JSON and POSTed.
        """
        if not self._webhook_url:
            return  # SIEM not configured — silently skip

        try:
            import httpx

            payload = self._build_payload(event)
            body = json.dumps(payload, default=str)
            headers = self._build_headers(body)

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    self._webhook_url,
                    content=body,
                    headers=headers,
                )
                if response.status_code >= 400:
                    logger.warning(
                        "SIEM webhook returned HTTP %d for event_type=%s",
                        response.status_code,
                        event.get("event_type", "unknown"),
                    )
        except Exception as exc:
            # Intentionally swallowed — SIEM failure must never surface to callers.
            logger.warning("SIEM webhook delivery failed (suppressed): %s", exc)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_payload(event: dict) -> dict:
        """Normalise *event* into the canonical SIEM envelope."""
        now = datetime.now(UTC).isoformat()
        return {
            "timestamp": event.get("timestamp", now),
            "event_type": event.get("event_type", "audit"),
            "tenant_id": event.get("tenant_id"),
            "account_id": event.get("account_id"),
            "action": event.get("action"),
            "resource_type": event.get("resource_type"),
            "resource_id": event.get("resource_id"),
            "ip": event.get("ip"),
            "metadata": event.get("metadata", {}),
        }

    def _build_headers(self, body: str) -> dict[str, str]:
        """Build HTTP headers, including an HMAC signature when a secret is set."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "SynkoraSIEM/1.0",
        }
        if self._webhook_secret:
            sig = hmac.new(  # type: ignore[attr-defined]
                self._webhook_secret.encode(),
                body.encode(),
                hashlib.sha256,
            ).hexdigest()
            headers["X-SIEM-Signature"] = f"sha256={sig}"
        return headers
