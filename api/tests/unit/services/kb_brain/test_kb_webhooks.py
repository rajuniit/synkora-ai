"""
Unit tests for kb_webhooks.py — Slack Events API webhook handler.
Tests HMAC verification, timestamp validation, event routing, and document conversion.
"""

import hashlib
import hmac
import json
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.controllers.kb_webhooks import (
    _extract_signing_secret,
    _slack_event_to_document,
    _verify_signature,
    _verify_timestamp,
    public_router,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SIGNING_SECRET = "test-signing-secret-abc123"
TENANT_ID = str(uuid.uuid4())
KB_ID = 42


def _make_signature(body: bytes, timestamp: str, secret: str = SIGNING_SECRET) -> str:
    sig_base = f"v0:{timestamp}:{body.decode()}".encode()
    return "v0=" + hmac.new(secret.encode(), sig_base, hashlib.sha256).hexdigest()  # type: ignore[attr-defined]


def _make_slack_event(
    event_type: str = "message",
    text: str = "Hello world",
    user: str = "U123",
    channel: str = "C456",
    ts: str = "1234567890.000",
    bot_id: str | None = None,
) -> dict:
    event: dict = {
        "type": "event_callback",
        "team_id": "T001",
        "event": {
            "type": event_type,
            "text": text,
            "user": user,
            "channel": channel,
            "ts": ts,
        },
    }
    if bot_id:
        event["event"]["bot_id"] = bot_id
    return event


# ---------------------------------------------------------------------------
# _verify_timestamp
# ---------------------------------------------------------------------------


def test_verify_timestamp_recent_passes():
    ts = str(int(time.time()))
    _verify_timestamp(ts)  # Should not raise


def test_verify_timestamp_missing_raises():
    with pytest.raises(HTTPException) as exc_info:
        _verify_timestamp(None)
    assert exc_info.value.status_code == 400


def test_verify_timestamp_non_integer_raises():
    with pytest.raises(HTTPException) as exc_info:
        _verify_timestamp("not-a-number")
    assert exc_info.value.status_code == 400


def test_verify_timestamp_too_old_raises():
    old_ts = str(int(time.time()) - 400)  # 400 seconds ago (> 300 threshold)
    with pytest.raises(HTTPException) as exc_info:
        _verify_timestamp(old_ts)
    assert exc_info.value.status_code == 400


def test_verify_timestamp_future_within_tolerance_passes():
    # 10 seconds in the future — well within the ±300s tolerance
    future_ts = str(int(time.time()) + 10)
    _verify_timestamp(future_ts)  # Should not raise


# ---------------------------------------------------------------------------
# _verify_signature
# ---------------------------------------------------------------------------


def test_verify_signature_valid():
    body = b'{"type":"event_callback"}'
    ts = str(int(time.time()))
    sig = _make_signature(body, ts)
    _verify_signature(body, ts, sig, SIGNING_SECRET)  # Should not raise


def test_verify_signature_invalid_secret_raises():
    body = b'{"type":"event_callback"}'
    ts = str(int(time.time()))
    valid_sig = _make_signature(body, ts)
    with pytest.raises(HTTPException) as exc_info:
        _verify_signature(body, ts, valid_sig, "wrong-secret")
    assert exc_info.value.status_code == 401


def test_verify_signature_tampered_body_raises():
    body = b'{"type":"event_callback"}'
    ts = str(int(time.time()))
    sig = _make_signature(body, ts)
    tampered_body = b'{"type":"event_callback","evil":true}'
    with pytest.raises(HTTPException) as exc_info:
        _verify_signature(tampered_body, ts, sig, SIGNING_SECRET)
    assert exc_info.value.status_code == 401


def test_verify_signature_missing_signature_raises():
    body = b'{"type":"event_callback"}'
    ts = str(int(time.time()))
    with pytest.raises(HTTPException) as exc_info:
        _verify_signature(body, ts, None, SIGNING_SECRET)
    assert exc_info.value.status_code == 401


def test_verify_signature_missing_timestamp_raises():
    body = b'{"type":"event_callback"}'
    sig = "v0=abc"
    with pytest.raises(HTTPException) as exc_info:
        _verify_signature(body, None, sig, SIGNING_SECRET)
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# _slack_event_to_document
# ---------------------------------------------------------------------------


def test_slack_event_to_document_basic():
    body = {"team_id": "T001"}
    event = {"type": "message", "text": "Deploy complete!", "user": "U1", "channel": "C-deploy", "ts": "1234567890.000"}
    doc = _slack_event_to_document(body, event, TENANT_ID)
    assert doc is not None
    assert doc["content"] == "Deploy complete!"
    assert doc["metadata"]["user"] == "U1"
    assert doc["metadata"]["channel"] == "C-deploy"
    assert doc["metadata"]["team"] == "T001"
    assert doc["metadata"]["tenant_id"] == TENANT_ID


def test_slack_event_to_document_empty_text_returns_none():
    body = {"team_id": "T001"}
    event = {"type": "message", "text": "", "user": "U1", "channel": "C1", "ts": "123"}
    assert _slack_event_to_document(body, event, TENANT_ID) is None


def test_slack_event_to_document_whitespace_only_returns_none():
    body = {}
    event = {"type": "message", "text": "   \n  ", "user": "U1", "channel": "C1", "ts": "123"}
    assert _slack_event_to_document(body, event, TENANT_ID) is None


def test_slack_event_to_document_thread_ts_grouping():
    body = {}
    event = {
        "type": "message",
        "text": "Reply in thread",
        "user": "U2",
        "channel": "C1",
        "ts": "1234567891.000",
        "thread_ts": "1234567890.000",
    }
    doc = _slack_event_to_document(body, event, TENANT_ID)
    # doc_id uses thread_ts for grouping
    assert "1234567890.000" in doc["id"]
    assert doc["metadata"]["thread_ts"] == "1234567890.000"


def test_slack_event_to_document_external_id_unique_per_message():
    body = {}
    event1 = {"type": "message", "text": "Msg 1", "user": "U1", "channel": "C1", "ts": "100"}
    event2 = {"type": "message", "text": "Msg 2", "user": "U1", "channel": "C1", "ts": "200"}
    doc1 = _slack_event_to_document(body, event1, TENANT_ID)
    doc2 = _slack_event_to_document(body, event2, TENANT_ID)
    assert doc1["external_id"] != doc2["external_id"]


# ---------------------------------------------------------------------------
# _extract_signing_secret
# ---------------------------------------------------------------------------


def test_extract_signing_secret_plain():
    ds = MagicMock()
    ds.config = {"signing_secret": "plaintext-secret"}
    result = _extract_signing_secret(ds)
    assert result == "plaintext-secret"


def test_extract_signing_secret_missing_raises():
    ds = MagicMock()
    ds.config = {}
    with pytest.raises(HTTPException) as exc_info:
        _extract_signing_secret(ds)
    assert exc_info.value.status_code == 500


def test_extract_signing_secret_none_config_raises():
    ds = MagicMock()
    ds.config = None
    with pytest.raises(HTTPException) as exc_info:
        _extract_signing_secret(ds)
    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# HTTP endpoint integration via TestClient
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    _app = FastAPI()
    _app.include_router(public_router)
    return _app


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


def _make_headers(body: bytes, ts: str | None = None, secret: str = SIGNING_SECRET) -> dict:
    ts = ts or str(int(time.time()))
    return {
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature": _make_signature(body, ts, secret),
        "Content-Type": "application/json",
    }


def test_slack_endpoint_url_verification(client):
    body = json.dumps(
        {"type": "url_verification", "challenge": "3eZbrw1aBm2rZgRNFdxV2595E9CY3gmdALWMmHkvFXO7tYXAYM8P"}
    ).encode()
    headers = _make_headers(body)

    with patch("src.controllers.kb_webhooks._get_slack_data_source", new_callable=AsyncMock) as mock_ds:
        ds = MagicMock()
        ds.config = {"signing_secret": SIGNING_SECRET}
        ds.tenant_id = uuid.UUID(TENANT_ID)
        mock_ds.return_value = ds

        response = client.post(f"/api/webhooks/kb/{KB_ID}/slack", content=body, headers=headers)

    assert response.status_code == 200
    assert response.json()["challenge"] == "3eZbrw1aBm2rZgRNFdxV2595E9CY3gmdALWMmHkvFXO7tYXAYM8P"


def test_slack_endpoint_event_queued(client):
    event_body = _make_slack_event(text="Hello team, deploy is done!")
    body = json.dumps(event_body).encode()
    headers = _make_headers(body)

    with (
        patch("src.controllers.kb_webhooks._get_slack_data_source", new_callable=AsyncMock) as mock_ds,
        patch("src.controllers.kb_webhooks._producer") as mock_producer,
    ):
        ds = MagicMock()
        ds.config = {"signing_secret": SIGNING_SECRET}
        ds.tenant_id = uuid.UUID(TENANT_ID)
        mock_ds.return_value = ds
        mock_producer.push = AsyncMock(return_value={"queued": 1, "skipped": 0})

        response = client.post(f"/api/webhooks/kb/{KB_ID}/slack", content=body, headers=headers)

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    mock_producer.push.assert_called_once()
    call_kwargs = mock_producer.push.call_args.kwargs
    assert call_kwargs["kb_id"] == KB_ID
    assert call_kwargs["source_type"] == "slack"


def test_slack_endpoint_bot_message_not_queued(client):
    event_body = _make_slack_event(text="I am a bot", bot_id="B123")
    body = json.dumps(event_body).encode()
    headers = _make_headers(body)

    with (
        patch("src.controllers.kb_webhooks._get_slack_data_source", new_callable=AsyncMock) as mock_ds,
        patch("src.controllers.kb_webhooks._producer") as mock_producer,
    ):
        ds = MagicMock()
        ds.config = {"signing_secret": SIGNING_SECRET}
        ds.tenant_id = uuid.UUID(TENANT_ID)
        mock_ds.return_value = ds
        mock_producer.push = AsyncMock()

        response = client.post(f"/api/webhooks/kb/{KB_ID}/slack", content=body, headers=headers)

    assert response.status_code == 200
    mock_producer.push.assert_not_called()


def test_slack_endpoint_invalid_signature_rejected(client):
    body = b'{"type":"event_callback","event":{"type":"message"}}'
    headers = {
        "X-Slack-Request-Timestamp": str(int(time.time())),
        "X-Slack-Signature": "v0=badhash",
        "Content-Type": "application/json",
    }

    with patch("src.controllers.kb_webhooks._get_slack_data_source", new_callable=AsyncMock) as mock_ds:
        ds = MagicMock()
        ds.config = {"signing_secret": SIGNING_SECRET}
        ds.tenant_id = uuid.UUID(TENANT_ID)
        mock_ds.return_value = ds

        response = client.post(f"/api/webhooks/kb/{KB_ID}/slack", content=body, headers=headers)

    assert response.status_code == 401


def test_slack_endpoint_old_timestamp_rejected(client):
    body = b'{"type":"event_callback"}'
    old_ts = str(int(time.time()) - 400)
    headers = {
        "X-Slack-Request-Timestamp": old_ts,
        "X-Slack-Signature": _make_signature(body, old_ts),
        "Content-Type": "application/json",
    }

    response = client.post(f"/api/webhooks/kb/{KB_ID}/slack", content=body, headers=headers)
    assert response.status_code == 400


def test_slack_endpoint_no_active_ds_returns_404(client):
    body = b'{"type":"event_callback"}'
    headers = _make_headers(body)

    with patch("src.controllers.kb_webhooks._get_slack_data_source", new_callable=AsyncMock) as mock_ds:
        from fastapi import HTTPException

        mock_ds.side_effect = HTTPException(status_code=404, detail="Slack data source not found")

        response = client.post(f"/api/webhooks/kb/{KB_ID}/slack", content=body, headers=headers)

    assert response.status_code == 404
