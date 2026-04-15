"""
KB real-time ingestion webhooks.

Slack sends workspace events here when a DataSource (with knowledge_base_id set)
has the Slack integration configured.  The endpoint:
  1. Validates Slack's HMAC-SHA256 signature
  2. Responds to URL verification challenges
  3. Enqueues message events to the KB Redis Stream for async processing

Route: POST /api/webhooks/kb/{kb_id}/slack

No auth middleware — Slack signs every request; we verify the signature.
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Path, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select

from src.core.database import get_async_session_factory
from src.models.data_source import DataSource, DataSourceStatus, DataSourceType
from src.services.company_brain.ingestion.stream_producer import StreamProducer

logger = logging.getLogger(__name__)

public_router = APIRouter(prefix="/api/webhooks/kb", tags=["kb-webhooks"])

_producer = StreamProducer()

# Slack event types we ingest
_INGEST_EVENTS = {
    "message",
    "message.channels",
    "message.groups",
    "message.im",
    "message.mpim",
}


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@public_router.post("/{kb_id}/slack", status_code=200)
async def slack_events_webhook(
    kb_id: int = Path(..., description="KnowledgeBase ID"),
    request: Request = None,
    x_slack_signature: str = Header(None, alias="X-Slack-Signature"),
    x_slack_request_timestamp: str = Header(None, alias="X-Slack-Request-Timestamp"),
) -> Any:
    """
    Receive Slack Events API webhooks and enqueue them into the KB ingestion stream.

    The DataSource must have `knowledge_base_id = kb_id` and an active Slack type.
    """
    raw_body = await request.body()

    # 1. Verify timestamp (prevent replay: reject if > 5 min old)
    _verify_timestamp(x_slack_request_timestamp)

    # 2. Look up the Slack data source and its signing secret
    ds = await _get_slack_data_source(kb_id)
    signing_secret = _extract_signing_secret(ds)
    tenant_id = str(ds.tenant_id)

    # 3. Verify HMAC signature
    _verify_signature(raw_body, x_slack_request_timestamp, x_slack_signature, signing_secret)

    # 4. Parse body
    try:
        body: dict = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    # 5. URL verification challenge
    if body.get("type") == "url_verification":
        return JSONResponse({"challenge": body.get("challenge", "")})

    # 6. Event callback
    if body.get("type") == "event_callback":
        event = body.get("event", {})
        event_type = event.get("type", "")

        # Ignore bot messages
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return {"ok": True}

        if event_type in _INGEST_EVENTS or event_type == "message":
            doc = _slack_event_to_document(body, event, tenant_id)
            if doc:
                try:
                    await _producer.push(
                        kb_id=kb_id,
                        tenant_id=tenant_id,
                        source_type="slack",
                        documents=[doc],
                    )
                    logger.debug(
                        "Queued Slack event ts=%s channel=%s kb_id=%d",
                        event.get("ts"),
                        event.get("channel"),
                        kb_id,
                    )
                except Exception as exc:
                    logger.error("Failed to enqueue Slack event: %s", exc)
                    # Return 200 anyway — Slack retries on non-2xx causing noise

    return {"ok": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _verify_timestamp(timestamp: str | None) -> None:
    if not timestamp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing X-Slack-Request-Timestamp")
    try:
        ts = int(timestamp)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid timestamp")
    if abs(time.time() - ts) > 300:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request timestamp too old")


def _verify_signature(
    body: bytes,
    timestamp: str | None,
    signature: str | None,
    signing_secret: str,
) -> None:
    if not signature or not timestamp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Slack signature headers")

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8', errors='replace')}".encode()
    expected = "v0=" + hmac.new(signing_secret.encode(), sig_basestring, hashlib.sha256).hexdigest()  # type: ignore[attr-defined]

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Slack signature")


async def _get_slack_data_source(kb_id: int) -> DataSource:
    """Return the active Slack DataSource linked to the given KnowledgeBase."""
    factory = get_async_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(DataSource).where(
                DataSource.knowledge_base_id == kb_id,
                DataSource.type == DataSourceType.SLACK,
                DataSource.status == DataSourceStatus.ACTIVE,
            ).limit(1)
        )
        ds = result.scalar_one_or_none()

    if not ds:
        logger.warning("No active Slack data source for kb_id=%d", kb_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slack data source not found for this knowledge base")

    return ds


def _extract_signing_secret(ds: DataSource) -> str:
    cfg = ds.config or {}
    secret_raw = cfg.get("signing_secret_encrypted") or cfg.get("signing_secret")
    if not secret_raw:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Signing secret not configured")

    from src.services.agents.security import decrypt_value
    return decrypt_value(secret_raw) if secret_raw.startswith("gAAAAA") else secret_raw


def _slack_event_to_document(body: dict, event: dict, tenant_id: str) -> dict | None:
    """Convert a Slack event payload to an ingestion document."""
    text = event.get("text", "") or ""
    ts = event.get("ts", "") or ""
    channel = event.get("channel", "") or ""
    user = event.get("user", "") or ""
    thread_ts = event.get("thread_ts") or ts

    if not text.strip():
        return None

    doc_id = f"slack_{channel}_{thread_ts}"

    return {
        "id": doc_id,
        "external_id": f"{channel}_{ts}",
        "title": f"Slack #{channel}",
        "content": text,
        "content_type": "text",
        "external_url": "",
        "metadata": {
            "source": "slack",
            "type": "message",
            "channel": channel,
            "user": user,
            "ts": ts,
            "thread_ts": thread_ts,
            "team": body.get("team_id", ""),
            "tenant_id": tenant_id,
        },
        "source_created_at": None,
        "source_updated_at": None,
    }
