"""Gmail data source connector."""

import base64
import json
import logging
from datetime import datetime
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.data_source import DataSource
from src.models.document import Document
from src.services.storage.s3_storage import S3StorageService

from .base_connector import BaseConnector

logger = logging.getLogger(__name__)


class GmailConnector(BaseConnector):
    """Connector for Gmail data."""

    def __init__(self, data_source: DataSource, db: AsyncSession):
        """
        Initialize Gmail connector.

        Args:
            data_source: DataSource model instance
            db: Async database session
        """
        super().__init__(data_source, db)
        self.service = None

    async def connect(self) -> bool:
        """Establish connection to Gmail."""
        try:
            if not self.data_source.access_token_encrypted:
                logger.error("No access token found for data source")
                return False

            from src.services.agents.security import decrypt_value

            try:
                access_token_str = decrypt_value(self.data_source.access_token_encrypted)

                if not access_token_str or access_token_str.strip() == "":
                    logger.error("Decrypted token is empty")
                    return False

                credentials_data = json.loads(access_token_str)

            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to parse credentials JSON: {e}. Raw value length: {len(access_token_str) if access_token_str else 0}"
                )
                return False

            creds = Credentials(
                token=credentials_data.get("access_token"),
                refresh_token=credentials_data.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=credentials_data.get("client_id"),
                client_secret=credentials_data.get("client_secret"),
            )

            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                credentials_data["access_token"] = creds.token
                from src.services.agents.security import encrypt_value

                self.data_source.access_token_encrypted = encrypt_value(json.dumps(credentials_data))
                await self.db.commit()

            self.service = build("gmail", "v1", credentials=creds)
            logger.info("Connected to Gmail")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Gmail: {e}", exc_info=True)
            return False

    async def disconnect(self) -> None:
        """Close connection to Gmail."""
        self.service = None
        logger.info("Disconnected from Gmail")

    async def test_connection(self) -> dict[str, Any]:
        """Test the Gmail connection."""
        try:
            if not self.service:
                connected = await self.connect()
                if not connected:
                    return {"success": False, "message": "Failed to connect to Gmail", "details": {}}

            # Get user profile
            profile = self.service.users().getProfile(userId="me").execute()

            return {
                "success": True,
                "message": "Successfully connected to Gmail",
                "details": {
                    "email": profile.get("emailAddress"),
                    "messages_total": profile.get("messagesTotal"),
                    "threads_total": profile.get("threadsTotal"),
                },
            }

        except HttpError as e:
            return {"success": False, "message": f"Gmail API error: {e.reason}", "details": {"error": str(e)}}
        except Exception as e:
            return {"success": False, "message": f"Unexpected error: {str(e)}", "details": {"error": str(e)}}

    async def fetch_documents(self, since: datetime | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        """Fetch emails from Gmail."""
        if not self.service:
            raise ConnectionError("Not connected to Gmail")

        documents = []
        config = self.data_source.config

        # Build query
        query_parts = []

        # Add labels filter
        labels = config.get("labels", [])
        if labels:
            query_parts.append(f"label:({' OR '.join(labels)})")

        # Add date filter - default to last 1 day if not specified
        if since:
            date_str = since.strftime("%Y/%m/%d")
            query_parts.append(f"after:{date_str}")
        else:
            # Default: only fetch emails from last 1 day
            from datetime import timedelta

            default_since = datetime.now() - timedelta(days=1)
            date_str = default_since.strftime("%Y/%m/%d")
            query_parts.append(f"after:{date_str}")
            logger.info(f"No 'since' date provided, defaulting to last 1 day (after {date_str})")

        # Add sender filter
        senders = config.get("senders", [])
        if senders:
            query_parts.append(f"from:({' OR '.join(senders)})")

        # Exclude spam and trash by default
        if not config.get("include_spam", False):
            query_parts.append("-in:spam")
        if not config.get("include_trash", False):
            query_parts.append("-in:trash")

        query = " ".join(query_parts) if query_parts else None

        try:
            # List messages - default limit to 50 emails per sync
            page_token = None
            default_limit = 50
            max_results = min(limit or default_limit, 500)  # Gmail API max is 500

            logger.info(f"Fetching up to {limit or default_limit} emails with query: {query}")

            while True:
                results = (
                    self.service.users()
                    .messages()
                    .list(userId="me", q=query, maxResults=max_results, pageToken=page_token)
                    .execute()
                )

                messages = results.get("messages", [])

                for msg_ref in messages:
                    # Get full message
                    message = (
                        self.service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()
                    )

                    document = await self._parse_message(message)
                    if document:
                        documents.append(document)

                    if limit and len(documents) >= limit:
                        break

                if limit and len(documents) >= limit:
                    break

                page_token = results.get("nextPageToken")
                if not page_token:
                    break

        except HttpError as e:
            logger.error(f"Error fetching emails: {e}")

        return documents

    async def _parse_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Parse Gmail message into document format."""
        try:
            headers = {h["name"]: h["value"] for h in message["payload"]["headers"]}

            # Extract body
            body = self._get_message_body(message["payload"])

            # Parse date
            timestamp = datetime.fromtimestamp(int(message["internalDate"]) / 1000).isoformat()

            return {
                "id": message["id"],
                "text": body,
                "metadata": {
                    "source": "GMAIL",
                    "subject": headers.get("Subject", ""),
                    "from": headers.get("From", ""),
                    "to": headers.get("To", ""),
                    "cc": headers.get("Cc", ""),
                    "timestamp": timestamp,
                    "labels": message.get("labelIds", []),
                    "thread_id": message.get("threadId"),
                    "snippet": message.get("snippet", ""),
                },
            }

        except Exception as e:
            logger.error(f"Error parsing message {message.get('id')}: {e}")
            return None

    def _get_message_body(self, payload: dict[str, Any]) -> str:
        """Extract message body from payload."""
        body = ""

        if "parts" in payload:
            # Multipart message
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data", "")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode("utf-8")
                        break
                elif part["mimeType"] == "text/html" and not body:
                    data = part["body"].get("data", "")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode("utf-8")
        else:
            # Simple message
            data = payload["body"].get("data", "")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8")

        return body

    async def _store_email_to_s3_and_db(
        self, email_data: dict[str, Any], raw_message: dict[str, Any]
    ) -> Document | None:
        """
        Store email to S3 and create Document record.

        Args:
            email_data: Processed email data with text and metadata
            raw_message: Raw Gmail API message response

        Returns:
            Document instance or None if failed
        """
        try:
            # Initialize S3 service
            s3 = S3StorageService()

            # Generate S3 key for email
            timestamp = datetime.fromisoformat(email_data["metadata"]["timestamp"])
            filename = f"email-{email_data['id']}.eml"
            s3_key = s3.generate_key(
                tenant_id=self.data_source.tenant_id, source_type="GMAIL", filename=filename, timestamp=timestamp
            )

            # Create .eml format content
            headers = {h["name"]: h["value"] for h in raw_message["payload"]["headers"]}
            eml_content = f"""From: {headers.get("From", "")}
To: {headers.get("To", "")}
Subject: {headers.get("Subject", "")}
Date: {headers.get("Date", "")}
Message-ID: {headers.get("Message-ID", "")}

{email_data["text"]}
"""

            # Upload email to S3
            s3_result = s3.upload_file(
                file_content=eml_content.encode("utf-8"),
                key=s3_key,
                content_type="message/rfc822",
                metadata={
                    "from": email_data["metadata"]["from"],
                    "to": email_data["metadata"]["to"],
                    "subject": email_data["metadata"]["subject"],
                    "timestamp": email_data["metadata"]["timestamp"],
                },
            )

            # Generate Gmail URL
            gmail_url = f"https://mail.google.com/mail/u/0/#inbox/{email_data['id']}"

            # Create Document record
            document = Document(
                tenant_id=self.data_source.tenant_id,
                knowledge_base_id=None,  # Will be set when added to KB
                data_source_id=self.data_source.id,
                title=email_data["metadata"]["subject"] or "No Subject",
                content=email_data["text"],
                source_type="GMAIL",
                external_id=email_data["id"],
                external_url=gmail_url,
                s3_bucket=s3_result["bucket"],
                s3_key=s3_result["key"],
                s3_url=s3_result["url"],
                file_size=len(eml_content),
                mime_type="message/rfc822",
                metadata={
                    "from": email_data["metadata"]["from"],
                    "to": email_data["metadata"]["to"],
                    "cc": email_data["metadata"].get("cc"),
                    "subject": email_data["metadata"]["subject"],
                    "timestamp": email_data["metadata"]["timestamp"],
                    "labels": email_data["metadata"].get("labels", []),
                    "thread_id": email_data["metadata"].get("thread_id"),
                    "snippet": email_data["metadata"].get("snippet"),
                },
            )

            self.db.add(document)
            await self.db.commit()
            await self.db.refresh(document)

            logger.info(f"Stored Gmail email {email_data['id']} to S3 and DB")
            return document

        except Exception as e:
            logger.error(f"Failed to store email to S3/DB: {e}")
            await self.db.rollback()
            return None

    async def _store_attachment_to_s3_and_db(
        self, attachment_data: dict[str, Any], email_id: str, parent_document_id: str
    ) -> Document | None:
        """
        Store email attachment to S3 and create Document record.

        Args:
            attachment_data: Attachment data from Gmail API
            email_id: Parent email ID
            parent_document_id: Parent document ID

        Returns:
            Document instance or None if failed
        """
        try:
            # Initialize S3 service
            s3 = S3StorageService()

            # Generate S3 key for attachment
            timestamp = datetime.now()
            filename = attachment_data.get("filename", f"attachment-{attachment_data['id']}")
            s3_key = s3.generate_key(
                tenant_id=self.data_source.tenant_id, source_type="GMAIL", filename=filename, timestamp=timestamp
            )

            # Upload attachment to S3
            s3_result = s3.upload_file(
                file_content=attachment_data["data"],
                key=s3_key,
                content_type=attachment_data.get("mimeType", "application/octet-stream"),
                metadata={"email_id": email_id, "filename": filename, "size": str(attachment_data.get("size", 0))},
            )

            # Create Document record for attachment
            document = Document(
                tenant_id=self.data_source.tenant_id,
                knowledge_base_id=None,
                data_source_id=self.data_source.id,
                title=f"Attachment: {filename}",
                content="",  # Attachments don't have text content initially
                source_type="GMAIL",
                external_id=f"{email_id}_attachment_{attachment_data['id']}",
                external_url=f"https://mail.google.com/mail/u/0/#inbox/{email_id}",
                s3_bucket=s3_result["bucket"],
                s3_key=s3_result["key"],
                s3_url=s3_result["url"],
                file_size=attachment_data.get("size", 0),
                mime_type=attachment_data.get("mimeType"),
                metadata={
                    "parent_email_id": email_id,
                    "parent_document_id": parent_document_id,
                    "filename": filename,
                    "attachment_id": attachment_data["id"],
                },
            )

            self.db.add(document)
            await self.db.commit()
            await self.db.refresh(document)

            logger.info(f"Stored attachment {filename} to S3 and DB")
            return document

        except Exception as e:
            logger.error(f"Failed to store attachment to S3/DB: {e}")
            await self.db.rollback()
            return None

    async def sync_to_knowledge_base(
        self, knowledge_base_id: str, since: datetime | None = None, limit: int | None = None
    ) -> dict[str, Any]:
        """
        Sync Gmail emails to knowledge base with S3 storage.

        Args:
            knowledge_base_id: Target knowledge base ID
            since: Only sync emails after this time
            limit: Maximum number of emails to sync

        Returns:
            Sync result with statistics
        """
        try:
            if not self.service:
                await self.connect()

            # Fetch emails
            emails = await self.fetch_documents(since=since, limit=limit)

            stored_count = 0
            failed_count = 0
            attachment_count = 0

            for email_data in emails:
                # Get full message for S3 storage
                try:
                    raw_message = (
                        self.service.users().messages().get(userId="me", id=email_data["id"], format="full").execute()
                    )

                    # Store email to S3 and create Document
                    document = await self._store_email_to_s3_and_db(email_data, raw_message)

                    if document:
                        # Associate with knowledge base
                        document.knowledge_base_id = knowledge_base_id
                        await self.db.commit()
                        stored_count += 1

                        # Handle attachments if present
                        if "parts" in raw_message["payload"]:
                            for part in raw_message["payload"]["parts"]:
                                if part.get("filename") and part["body"].get("attachmentId"):
                                    # Download attachment
                                    attachment = (
                                        self.service.users()
                                        .messages()
                                        .attachments()
                                        .get(userId="me", messageId=email_data["id"], id=part["body"]["attachmentId"])
                                        .execute()
                                    )

                                    attachment_data = {
                                        "id": part["body"]["attachmentId"],
                                        "filename": part["filename"],
                                        "mimeType": part["mimeType"],
                                        "size": part["body"].get("size", 0),
                                        "data": base64.urlsafe_b64decode(attachment["data"]),
                                    }

                                    # Store attachment
                                    att_doc = await self._store_attachment_to_s3_and_db(
                                        attachment_data, email_data["id"], str(document.id)
                                    )

                                    if att_doc:
                                        att_doc.knowledge_base_id = knowledge_base_id
                                        await self.db.commit()
                                        attachment_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    logger.error(f"Failed to process email {email_data['id']}: {e}")
                    failed_count += 1

            return {
                "success": True,
                "total_fetched": len(emails),
                "stored": stored_count,
                "attachments": attachment_count,
                "failed": failed_count,
                "message": f"Synced {stored_count} emails and {attachment_count} attachments to knowledge base",
            }

        except Exception as e:
            logger.error(f"Sync to knowledge base failed: {e}")
            return {"success": False, "error": str(e), "message": "Failed to sync emails"}

    async def get_document_count(self) -> int:
        """Get total number of emails."""
        if not self.service:
            return 0

        try:
            profile = self.service.users().getProfile(userId="me").execute()
            return profile.get("messagesTotal", 0)
        except HttpError as e:
            logger.error(f"Error getting message count: {e}")
            return 0

    def get_required_config_fields(self) -> list[str]:
        """Get required configuration fields."""
        return []  # All config is optional

    def get_oauth_url(self) -> str | None:
        """Get Gmail OAuth URL."""
        from src.services.oauth.gmail_oauth import GmailOAuth

        oauth = GmailOAuth()
        return oauth.get_authorization_url(state=f"data_source_{self.data_source.id}")

    async def handle_oauth_callback(self, code: str) -> dict[str, Any]:
        """Handle Gmail OAuth callback."""
        from src.services.oauth.gmail_oauth import GmailOAuth

        try:
            oauth = GmailOAuth()
            token_data = await oauth.exchange_code(code)

            # Store credentials
            self.data_source.credentials = {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
                "client_id": oauth.client_id,
                "client_secret": oauth.client_secret,
                "token_expiry": token_data.get("expires_in"),
            }
            self.data_source.is_connected = True
            await self.db.commit()

            return {"success": True, "message": "Successfully connected to Gmail"}

        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            return {"success": False, "message": f"Failed to complete OAuth: {str(e)}"}
