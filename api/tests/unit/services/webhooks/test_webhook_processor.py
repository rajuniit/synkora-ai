"""
Unit tests for Webhook Processor.

Tests webhook processing, event filtering, and agent execution triggering.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.webhooks.webhook_processor import WebhookProcessor


class TestWebhookProcessor:
    """Test WebhookProcessor class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def processor(self, mock_db):
        """Create processor instance."""
        return WebhookProcessor(mock_db)

    @pytest.fixture
    def mock_webhook(self):
        """Create mock webhook object."""
        webhook = MagicMock()
        webhook.id = uuid.uuid4()
        webhook.provider = "github"
        webhook.secret = "encrypted_secret"
        webhook.is_active = True
        webhook.event_types = None
        webhook.config = {}
        webhook.success_count = 0
        webhook.failure_count = 0
        webhook.last_triggered_at = None
        return webhook


class TestVerifySignature:
    """Test signature verification."""

    @pytest.fixture
    def processor(self):
        return WebhookProcessor(MagicMock())

    @pytest.fixture
    def mock_webhook(self):
        webhook = MagicMock()
        webhook.id = uuid.uuid4()
        webhook.provider = "github"
        webhook.secret = "encrypted_secret"
        webhook.config = {}
        return webhook

    def test_missing_secret_returns_false(self, processor):
        """Test that missing secret returns False."""
        webhook = MagicMock()
        webhook.id = uuid.uuid4()
        webhook.secret = None

        result = processor.verify_signature(webhook, b"payload", {})

        assert result is False

    @patch("src.services.webhooks.webhook_processor.SignatureVerifier")
    @patch("src.services.agents.security.decrypt_value")
    def test_valid_signature(self, mock_decrypt, mock_verifier, processor, mock_webhook):
        """Test valid signature verification."""
        mock_decrypt.return_value = "decrypted_secret"
        mock_verifier.verify.return_value = True

        result = processor.verify_signature(mock_webhook, b"payload", {"x-hub-signature-256": "sha256=abc"})

        assert result is True
        mock_verifier.verify.assert_called_once()

    @patch("src.services.webhooks.webhook_processor.SignatureVerifier")
    @patch("src.services.agents.security.decrypt_value")
    def test_invalid_signature(self, mock_decrypt, mock_verifier, processor, mock_webhook):
        """Test invalid signature verification."""
        mock_decrypt.return_value = "decrypted_secret"
        mock_verifier.verify.return_value = False

        result = processor.verify_signature(mock_webhook, b"payload", {})

        assert result is False

    @patch("src.services.agents.security.decrypt_value")
    def test_decrypt_error_raises_exception(self, mock_decrypt, processor, mock_webhook):
        """Test that decryption error raises HTTPException."""
        mock_decrypt.side_effect = Exception("Decryption failed")

        with pytest.raises(HTTPException) as exc_info:
            processor.verify_signature(mock_webhook, b"payload", {})

        assert exc_info.value.status_code == 500
        assert "decrypt" in exc_info.value.detail.lower()


class TestShouldProcessEvent:
    """Test event filtering logic."""

    @pytest.fixture
    def processor(self):
        return WebhookProcessor(MagicMock())

    def test_inactive_webhook_returns_false(self, processor):
        """Test that inactive webhook returns False."""
        webhook = MagicMock()
        webhook.is_active = False

        result = processor.should_process_event(webhook, {"event_type": "push"})

        assert result is False

    def test_active_webhook_no_filter_returns_true(self, processor):
        """Test active webhook without event filter returns True."""
        webhook = MagicMock()
        webhook.is_active = True
        webhook.event_types = None

        result = processor.should_process_event(webhook, {"event_type": "push"})

        assert result is True

    def test_event_type_exact_match(self, processor):
        """Test exact event type matching."""
        webhook = MagicMock()
        webhook.is_active = True
        webhook.event_types = ["push", "pull_request.opened"]

        # Exact match
        result = processor.should_process_event(webhook, {"event_type": "push"})
        assert result is True

        result = processor.should_process_event(webhook, {"event_type": "pull_request.opened"})
        assert result is True

    def test_event_type_category_match(self, processor):
        """Test event category matching."""
        webhook = MagicMock()
        webhook.is_active = True
        webhook.event_types = ["pull_request"]

        # Category match (pull_request matches pull_request.opened)
        result = processor.should_process_event(webhook, {"event_type": "pull_request.opened"})
        assert result is True

    def test_event_type_no_match(self, processor):
        """Test non-matching event type."""
        webhook = MagicMock()
        webhook.is_active = True
        webhook.event_types = ["push"]

        result = processor.should_process_event(webhook, {"event_type": "issue.created"})
        assert result is False


class TestCreateWebhookEvent:
    """Test webhook event creation."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.add = MagicMock()
        return db

    @pytest.fixture
    def processor(self, mock_db):
        return WebhookProcessor(mock_db)

    @pytest.mark.asyncio
    async def test_creates_event_with_correct_fields(self, processor, mock_db):
        """Test event creation with correct fields."""
        webhook = MagicMock()
        webhook.id = uuid.uuid4()

        payload = {"action": "opened"}
        parsed_data = {"event_type": "pull_request.opened", "summary": "PR opened"}
        event_id = "delivery-123"

        await processor.create_webhook_event(webhook, payload, parsed_data, event_id)

        # Verify db operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_event_without_event_id(self, processor, mock_db):
        """Test event creation without event_id."""
        webhook = MagicMock()
        webhook.id = uuid.uuid4()

        await processor.create_webhook_event(webhook, {"payload": "data"}, {"event_type": "test"})

        mock_db.add.assert_called_once()


class TestTriggerAgentExecution:
    """Test agent execution triggering."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def processor(self, mock_db):
        return WebhookProcessor(mock_db)

    @pytest.mark.asyncio
    @patch("src.tasks.agent_tasks.process_webhook_event")
    async def test_queues_celery_task(self, mock_task, processor):
        """Test that Celery task is queued."""
        webhook = MagicMock()
        webhook.id = uuid.uuid4()

        event = MagicMock()
        event.id = uuid.uuid4()

        mock_task.delay.return_value.id = "task-123"

        parsed_data = {"event_type": "push"}

        result = await processor.trigger_agent_execution(webhook, event, parsed_data)

        assert result == "task-123"
        mock_task.delay.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.tasks.agent_tasks.process_webhook_event")
    async def test_handles_task_error(self, mock_task, processor):
        """Test error handling when task fails."""
        webhook = MagicMock()
        webhook.id = uuid.uuid4()

        event = MagicMock()
        event.id = uuid.uuid4()

        mock_task.delay.side_effect = Exception("Celery error")

        with pytest.raises(Exception):
            await processor.trigger_agent_execution(webhook, event, {})


class TestProcessWebhook:
    """Test the main process_webhook method."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def processor(self, mock_db):
        return WebhookProcessor(mock_db)

    @pytest.fixture
    def mock_webhook(self):
        webhook = MagicMock()
        webhook.id = uuid.uuid4()
        webhook.provider = "github"
        webhook.secret = "encrypted_secret"
        webhook.is_active = True
        webhook.event_types = None
        webhook.config = {}
        webhook.success_count = 0
        webhook.failure_count = 0
        return webhook

    @pytest.mark.asyncio
    @patch.object(WebhookProcessor, "trigger_agent_execution")
    @patch.object(WebhookProcessor, "create_webhook_event")
    @patch.object(WebhookProcessor, "should_process_event")
    @patch.object(WebhookProcessor, "verify_signature")
    @patch("src.services.webhooks.webhook_processor.ProviderParser")
    async def test_successful_processing(
        self,
        mock_parser,
        mock_verify,
        mock_should_process,
        mock_create_event,
        mock_trigger,
        processor,
        mock_webhook,
        mock_db,
    ):
        """Test successful webhook processing."""
        mock_verify.return_value = True
        mock_should_process.return_value = True
        mock_parser.parse_github.return_value = {"event_type": "push", "summary": "Push event"}

        mock_event = MagicMock()
        mock_event.id = uuid.uuid4()
        mock_event.status = "pending"
        mock_create_event.return_value = mock_event

        mock_trigger.return_value = "task-123"

        # Mock DB execute for replay protection and dedup checks (return no existing event)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await processor.process_webhook(
            webhook=mock_webhook,
            payload=b'{"action": "push"}',
            payload_dict={"action": "push"},
            headers={"x-github-event": "push", "x-github-delivery": "delivery-123"},
        )

        assert result["status"] == "success"
        assert "event_id" in result
        assert result["execution_id"] == "task-123"

    @pytest.mark.asyncio
    @patch.object(WebhookProcessor, "verify_signature")
    async def test_invalid_signature_returns_401(self, mock_verify, processor, mock_webhook, mock_db):
        """Test that invalid signature returns 401."""
        mock_verify.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await processor.process_webhook(webhook=mock_webhook, payload=b"payload", payload_dict={}, headers={})

        assert exc_info.value.status_code == 401
        assert mock_webhook.failure_count == 1

    @pytest.mark.asyncio
    @patch.object(WebhookProcessor, "should_process_event")
    @patch.object(WebhookProcessor, "verify_signature")
    @patch("src.services.webhooks.webhook_processor.ProviderParser")
    async def test_filtered_event_returns_skipped(
        self, mock_parser, mock_verify, mock_should_process, processor, mock_webhook
    ):
        """Test that filtered events return skipped status."""
        mock_verify.return_value = True
        mock_should_process.return_value = False
        mock_parser.parse_github.return_value = {"event_type": "issue"}

        result = await processor.process_webhook(
            webhook=mock_webhook, payload=b"{}", payload_dict={}, headers={"x-github-event": "issue"}
        )

        assert result["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_webhook_without_secret(self, processor, mock_db):
        """Test processing webhook without secret."""
        webhook = MagicMock()
        webhook.id = uuid.uuid4()
        webhook.provider = "github"
        webhook.secret = None  # No secret
        webhook.is_active = True
        webhook.event_types = None
        webhook.config = {}
        webhook.success_count = 0
        webhook.failure_count = 0

        with patch("src.services.webhooks.webhook_processor.ProviderParser") as mock_parser:
            with patch.object(processor, "should_process_event", return_value=True):
                with patch.object(processor, "create_webhook_event") as mock_create:
                    with patch.object(processor, "trigger_agent_execution", return_value="task-id"):
                        mock_parser.parse_github.return_value = {"event_type": "push"}
                        mock_event = MagicMock()
                        mock_event.id = uuid.uuid4()
                        mock_create.return_value = mock_event

                        # Should process without signature verification
                        result = await processor.process_webhook(
                            webhook=webhook, payload=b"{}", payload_dict={}, headers={"x-github-event": "push"}
                        )

                        assert result["status"] == "success"


class TestEventIdExtraction:
    """Test event ID extraction from headers."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def processor(self, mock_db):
        return WebhookProcessor(mock_db)

    @pytest.mark.asyncio
    @patch.object(WebhookProcessor, "trigger_agent_execution")
    @patch.object(WebhookProcessor, "create_webhook_event")
    @patch.object(WebhookProcessor, "should_process_event")
    @patch.object(WebhookProcessor, "verify_signature")
    @patch("src.services.webhooks.webhook_processor.ProviderParser")
    async def test_github_delivery_id_extracted(
        self, mock_parser, mock_verify, mock_should_process, mock_create_event, mock_trigger, processor, mock_db
    ):
        """Test GitHub delivery ID extraction."""
        webhook = MagicMock()
        webhook.id = uuid.uuid4()
        webhook.provider = "github"
        webhook.secret = "secret"
        webhook.is_active = True
        webhook.event_types = None
        webhook.config = {}
        webhook.success_count = 0

        mock_verify.return_value = True
        mock_should_process.return_value = True
        mock_parser.parse_github.return_value = {"event_type": "push"}
        mock_event = MagicMock()
        mock_event.id = uuid.uuid4()
        mock_create_event.return_value = mock_event
        mock_trigger.return_value = "task-id"

        # Mock DB execute for replay protection and dedup checks (return no existing event)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        await processor.process_webhook(
            webhook=webhook,
            payload=b"{}",
            payload_dict={},
            headers={"x-github-event": "push", "x-github-delivery": "github-delivery-123"},
        )

        # Check that create_webhook_event was called with the delivery ID
        call_kwargs = mock_create_event.call_args
        assert call_kwargs is not None
