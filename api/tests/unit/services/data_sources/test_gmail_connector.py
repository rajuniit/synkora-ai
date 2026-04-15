import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.data_source import DataSource
from src.services.data_sources.gmail_connector import GmailConnector


class TestGmailConnector:
    @pytest.fixture
    def mock_db_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_data_source(self):
        ds = MagicMock(spec=DataSource)
        ds.access_token_encrypted = "encrypted_token"
        ds.config = {"labels": ["INBOX"], "senders": ["test@example.com"]}
        ds.tenant_id = "tenant-123"
        ds.id = "ds-123"
        return ds

    @pytest.fixture
    def connector(self, mock_data_source, mock_db_session):
        return GmailConnector(mock_data_source, mock_db_session)

    @pytest.mark.asyncio
    async def test_connect_no_token(self, connector):
        connector.data_source.access_token_encrypted = None
        result = await connector.connect()
        assert result is False

    @pytest.mark.asyncio
    async def test_connect_success(self, connector):
        with (
            patch("src.services.agents.security.decrypt_value") as mock_decrypt,
            patch("src.services.data_sources.gmail_connector.Credentials") as mock_creds,
            patch("src.services.data_sources.gmail_connector.build") as mock_build,
        ):
            mock_decrypt.return_value = json.dumps(
                {"access_token": "token", "refresh_token": "refresh", "client_id": "id", "client_secret": "secret"}
            )

            mock_creds_instance = mock_creds.return_value
            mock_creds_instance.expired = False

            result = await connector.connect()

            assert result is True
            assert connector.service is not None
            mock_build.assert_called_with("gmail", "v1", credentials=mock_creds_instance)

    @pytest.mark.asyncio
    async def test_connect_refresh_token(self, connector, mock_db_session):
        with (
            patch("src.services.agents.security.decrypt_value") as mock_decrypt,
            patch("src.services.agents.security.encrypt_value") as mock_encrypt,
            patch("src.services.data_sources.gmail_connector.Credentials") as mock_creds,
            patch("src.services.data_sources.gmail_connector.build"),
        ):
            mock_decrypt.return_value = json.dumps({"access_token": "old_token", "refresh_token": "refresh"})

            mock_creds_instance = mock_creds.return_value
            mock_creds_instance.expired = True
            mock_creds_instance.refresh_token = "refresh"
            mock_creds_instance.token = "new_token"

            result = await connector.connect()

            assert result is True
            mock_creds_instance.refresh.assert_called_once()
            mock_encrypt.assert_called_once()
            mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, connector):
        connector.service = MagicMock()
        await connector.disconnect()
        assert connector.service is None

    @pytest.mark.asyncio
    async def test_test_connection_success(self, connector):
        connector.service = MagicMock()
        mock_users = connector.service.users.return_value
        mock_users.getProfile.return_value.execute.return_value = {
            "emailAddress": "test@example.com",
            "messagesTotal": 100,
        }

        result = await connector.test_connection()

        assert result["success"] is True
        assert result["details"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_fetch_documents_not_connected(self, connector):
        connector.service = None
        with pytest.raises(ConnectionError):
            await connector.fetch_documents()

    @pytest.mark.asyncio
    async def test_fetch_documents_success(self, connector):
        connector.service = MagicMock()
        mock_users = connector.service.users.return_value

        # Mock list response
        mock_users.messages.return_value.list.return_value.execute.return_value = {"messages": [{"id": "msg1"}]}

        # Mock get message response
        mock_users.messages.return_value.get.return_value.execute.return_value = {
            "id": "msg1",
            "internalDate": "1600000000000",
            "payload": {
                "headers": [{"name": "Subject", "value": "Test Email"}, {"name": "From", "value": "sender@test.com"}],
                "body": {"data": ""},
            },
        }

        with patch.object(connector, "_get_message_body", return_value="Email body"):
            docs = await connector.fetch_documents(limit=1)

            assert len(docs) == 1
            assert docs[0]["id"] == "msg1"
            assert docs[0]["text"] == "Email body"
            assert docs[0]["metadata"]["subject"] == "Test Email"

    def test_get_message_body_simple(self, connector):
        import base64

        body_content = "Hello World"
        encoded = base64.urlsafe_b64encode(body_content.encode()).decode()

        payload = {"body": {"data": encoded}}

        result = connector._get_message_body(payload)
        assert result == body_content

    def test_get_message_body_multipart(self, connector):
        import base64

        body_content = "Hello Multipart"
        encoded = base64.urlsafe_b64encode(body_content.encode()).decode()

        payload = {"parts": [{"mimeType": "text/plain", "body": {"data": encoded}}]}

        result = connector._get_message_body(payload)
        assert result == body_content

    @pytest.mark.asyncio
    async def test_store_email_to_s3_and_db(self, connector):
        email_data = {
            "id": "msg1",
            "text": "Body",
            "metadata": {"timestamp": "2023-01-01T12:00:00", "from": "sender", "to": "recipient", "subject": "Subject"},
        }

        raw_message = {"payload": {"headers": []}}

        with (
            patch("src.services.data_sources.gmail_connector.S3StorageService") as MockS3,
            patch("src.services.data_sources.gmail_connector.Document") as MockDoc,
        ):
            s3_instance = MockS3.return_value
            s3_instance.generate_key.return_value = "key"
            s3_instance.upload_file.return_value = {"bucket": "bucket", "key": "key", "url": "url"}

            doc_instance = MockDoc.return_value
            doc_instance.id = "doc-id"

            result = await connector._store_email_to_s3_and_db(email_data, raw_message)

            assert result == doc_instance
            s3_instance.upload_file.assert_called_once()
            connector.db.add.assert_called_once()
            connector.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_document_count(self, connector):
        connector.service = MagicMock()
        mock_users = connector.service.users.return_value
        mock_users.getProfile.return_value.execute.return_value = {"messagesTotal": 42}

        count = await connector.get_document_count()
        assert count == 42
