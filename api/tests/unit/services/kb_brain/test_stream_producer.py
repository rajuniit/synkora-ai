"""
Unit tests for StreamProducer — stream key schema and push behaviour.
No real Redis required; uses AsyncMock.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.company_brain.ingestion.stream_producer import StreamProducer, _stream_key


# ---------------------------------------------------------------------------
# _stream_key
# ---------------------------------------------------------------------------

def test_stream_key_format():
    assert _stream_key(42, "slack") == "kb_ingest:42:slack"


def test_stream_key_uppercased_source_lowercased():
    assert _stream_key(1, "GITHUB") == "kb_ingest:1:github"


def test_stream_key_different_kb_ids_are_distinct():
    assert _stream_key(1, "slack") != _stream_key(2, "slack")


def test_stream_key_different_sources_are_distinct():
    assert _stream_key(1, "slack") != _stream_key(1, "github")


# ---------------------------------------------------------------------------
# Dummy documents
# ---------------------------------------------------------------------------

DOCS = [
    {"id": "slack_C01_123.456", "content": "Hello team, let's sync tomorrow.", "metadata": {"user": "U01"}},
    {"id": "slack_C01_124.000", "content": "Sounds good! I'll prepare the agenda.", "metadata": {"user": "U02"}},
]


# ---------------------------------------------------------------------------
# push — Redis streams path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_push_empty_documents_returns_zeros():
    producer = StreamProducer()
    result = await producer.push(kb_id=1, tenant_id="tid-abc", source_type="slack", documents=[])
    assert result == {"queued": 0, "skipped": 0}


@pytest.mark.asyncio
async def test_push_queues_all_docs_to_correct_stream_key():
    producer = StreamProducer()
    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(return_value=b"1-0")
    producer._redis = mock_redis

    with patch.object(producer, "_use_streams", return_value=True), \
         patch.object(producer, "_max_len", return_value=500_000):
        result = await producer.push(kb_id=5, tenant_id="tenant-xyz", source_type="slack", documents=DOCS)

    assert result["queued"] == 2
    assert result["skipped"] == 0
    assert mock_redis.xadd.call_count == 2

    # Verify the key used in every xadd call is the new KB-scoped key
    for call in mock_redis.xadd.call_args_list:
        key_arg = call.args[0]
        assert key_arg == "kb_ingest:5:slack"


@pytest.mark.asyncio
async def test_push_stream_message_contains_kb_id():
    producer = StreamProducer()
    mock_redis = AsyncMock()
    captured_payloads = []

    async def fake_xadd(key, fields, **kw):
        captured_payloads.append(fields)
        return b"1-0"

    mock_redis.xadd = fake_xadd
    producer._redis = mock_redis

    with patch.object(producer, "_use_streams", return_value=True), \
         patch.object(producer, "_max_len", return_value=500_000):
        await producer.push(kb_id=7, tenant_id="t1", source_type="github", documents=DOCS[:1])

    assert len(captured_payloads) == 1
    fields = captured_payloads[0]
    assert fields["kb_id"] == "7"
    assert fields["tenant_id"] == "t1"
    assert fields["source_type"] == "github"
    payload = json.loads(fields["payload"])
    assert payload["id"] == DOCS[0]["id"]


@pytest.mark.asyncio
async def test_push_skips_doc_on_redis_error():
    producer = StreamProducer()
    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(side_effect=[Exception("Redis down"), b"1-0"])
    producer._redis = mock_redis

    with patch.object(producer, "_use_streams", return_value=True), \
         patch.object(producer, "_max_len", return_value=500_000):
        result = await producer.push(kb_id=1, tenant_id="t1", source_type="slack", documents=DOCS)

    assert result["queued"] == 1
    assert result["skipped"] == 1


# ---------------------------------------------------------------------------
# push — Celery fallback path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_push_celery_fallback_dispatches_task():
    producer = StreamProducer()

    mock_task = MagicMock()
    mock_task.delay = MagicMock()

    with patch.object(producer, "_use_streams", return_value=False), \
         patch("src.services.company_brain.ingestion.stream_producer.StreamProducer._push_via_celery",
               new_callable=AsyncMock, return_value={"queued": 2, "skipped": 0}) as mock_celery:
        result = await producer.push(kb_id=3, tenant_id="t2", source_type="jira", documents=DOCS)

    mock_celery.assert_called_once_with(3, "t2", "jira", DOCS)
    assert result == {"queued": 2, "skipped": 0}


# ---------------------------------------------------------------------------
# stream_length
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stream_length_returns_count():
    producer = StreamProducer()
    mock_redis = AsyncMock()
    mock_redis.xlen = AsyncMock(return_value=42)
    producer._redis = mock_redis

    length = await producer.stream_length(kb_id=1, source_type="slack")
    assert length == 42
    mock_redis.xlen.assert_called_once_with("kb_ingest:1:slack")


@pytest.mark.asyncio
async def test_stream_length_returns_minus_one_on_error():
    producer = StreamProducer()
    mock_redis = AsyncMock()
    mock_redis.xlen = AsyncMock(side_effect=Exception("Redis down"))
    producer._redis = mock_redis

    length = await producer.stream_length(kb_id=1, source_type="slack")
    assert length == -1
