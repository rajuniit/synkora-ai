"""
Notion data source connector.

Syncs pages and database rows from Notion workspaces.
Uses the Notion REST API v1 (Bearer token auth).

Required config fields (data_source.config):
  database_ids  — list[str], specific database IDs to sync (empty = all accessible)
  page_ids      — list[str], specific top-level page IDs to include
  include_children — bool (default true): recursively fetch child pages
  max_page_size — int (default 100, max 100)

Auth:
  access_token_encrypted — OAuth integration token OR
  config.internal_token_encrypted — Internal integration token (simpler for self-hosted)
"""

import logging
from datetime import datetime
from typing import Any

import httpx

from src.models.data_source import DataSource
from src.services.agents.security import decrypt_value

from .base_connector import BaseConnector

logger = logging.getLogger(__name__)

_BASE = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"


class NotionConnector(BaseConnector):
    """Connector for Notion pages and databases."""

    def __init__(self, data_source: DataSource, db: Any):
        super().__init__(data_source, db)
        self._token: str = ""

    def get_required_config_fields(self) -> list[str]:
        return []  # token is enough

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Notion-Version": _NOTION_VERSION,
            "Content-Type": "application/json",
        }

    async def connect(self) -> bool:
        try:
            self._token = await self._get_token()
            async with httpx.AsyncClient(headers=self._headers(), timeout=15) as client:
                resp = await client.get(f"{_BASE}/users/me")
                resp.raise_for_status()
                user = resp.json()
                logger.info("Connected to Notion as: %s", user.get("name", user.get("id")))
            return True
        except Exception as exc:
            logger.error("Notion connect failed: %s", exc)
            return False

    async def disconnect(self) -> None:
        self._token = ""

    async def test_connection(self) -> dict[str, Any]:
        try:
            connected = await self.connect()
            if not connected:
                return {"success": False, "message": "Failed to connect", "details": {}}
            async with httpx.AsyncClient(headers=self._headers(), timeout=15) as client:
                resp = await client.get(f"{_BASE}/users/me")
                user = resp.json()
            await self.disconnect()
            return {
                "success": True,
                "message": "Connection successful",
                "details": {"user": user.get("name"), "type": user.get("type")},
            }
        except Exception as exc:
            return {"success": False, "message": str(exc), "details": {}}

    async def get_document_count(self) -> int:
        pages = await self._search_all_pages(since=None)
        return len(pages)

    async def fetch_documents(
        self, since: datetime | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        cfg = self.data_source.config
        include_children = cfg.get("include_children", True)
        documents: list[dict[str, Any]] = []

        # 1. Specific database IDs
        for db_id in cfg.get("database_ids") or []:
            rows = await self._query_database(db_id, since)
            documents.extend(rows)

        # 2. Search for all accessible pages (or specific page_ids)
        page_ids = cfg.get("page_ids") or []
        if page_ids:
            pages = [await self._get_page(pid) for pid in page_ids]
        else:
            pages = await self._search_all_pages(since)

        for page in pages:
            if not page:
                continue
            doc = await self._page_to_document(page, include_children)
            if doc:
                documents.append(doc)

            if limit and len(documents) >= limit:
                return documents[:limit]

        logger.info("Notion fetched %d documents", len(documents))
        return documents

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_token(self) -> str:
        if self.data_source.access_token_encrypted:
            return decrypt_value(self.data_source.access_token_encrypted)
        cfg = self.data_source.config
        token = cfg.get("internal_token_encrypted") or cfg.get("internal_token")
        if token:
            return decrypt_value(token) if token.startswith("gAAAAA") else token
        raise ValueError("No Notion token configured")

    async def _search_all_pages(self, since: datetime | None) -> list[dict]:
        """Use Notion search API to find all accessible pages."""
        pages: list[dict] = []
        cursor: str | None = None
        page_size = self.data_source.config.get("max_page_size", 100)

        body: dict[str, Any] = {"filter": {"value": "page", "property": "object"}, "page_size": page_size}
        if since:
            # Notion search doesn't support date filtering natively — filter post-fetch
            pass

        while True:
            if cursor:
                body["start_cursor"] = cursor
            try:
                async with httpx.AsyncClient(headers=self._headers(), timeout=30) as client:
                    resp = await client.post(f"{_BASE}/search", json=body)
                    resp.raise_for_status()
                    data = resp.json()
            except Exception as exc:
                logger.warning("Notion search failed: %s", exc)
                break

            results = data.get("results", [])
            for page in results:
                if since:
                    last_edited = page.get("last_edited_time", "")
                    if last_edited and last_edited < since.isoformat():
                        continue
                pages.append(page)

            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")

        return pages

    async def _get_page(self, page_id: str) -> dict | None:
        try:
            async with httpx.AsyncClient(headers=self._headers(), timeout=15) as client:
                resp = await client.get(f"{_BASE}/pages/{page_id}")
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.warning("Notion get_page(%s) failed: %s", page_id, exc)
            return None

    async def _get_page_content(self, page_id: str) -> str:
        """Fetch block children and extract plain text."""
        texts: list[str] = []
        cursor: str | None = None
        while True:
            params: dict[str, Any] = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
            try:
                async with httpx.AsyncClient(headers=self._headers(), timeout=15) as client:
                    resp = await client.get(f"{_BASE}/blocks/{page_id}/children", params=params)
                    resp.raise_for_status()
                    data = resp.json()
            except Exception:
                break
            for block in data.get("results", []):
                text = self._extract_block_text(block)
                if text:
                    texts.append(text)
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
        return "\n".join(texts)

    def _extract_block_text(self, block: dict) -> str:
        block_type = block.get("type", "")
        block_data = block.get(block_type, {})
        rich_texts = block_data.get("rich_text") or block_data.get("text") or []
        return "".join(rt.get("plain_text", "") for rt in rich_texts)

    async def _page_to_document(self, page: dict, include_children: bool) -> dict[str, Any] | None:
        page_id = page.get("id", "")
        props = page.get("properties") or {}

        # Extract title from various property types
        title = ""
        for prop in props.values():
            if prop.get("type") == "title":
                rich_texts = prop.get("title") or []
                title = "".join(rt.get("plain_text", "") for rt in rich_texts)
                break

        content = title
        if include_children:
            body = await self._get_page_content(page_id)
            if body:
                content = f"{title}\n\n{body}".strip()

        if not content:
            return None

        url = page.get("url", "")
        return {
            "id": f"notion_page_{page_id}",
            "external_id": page_id,
            "title": title or page_id,
            "content": content,
            "content_type": "markdown",
            "external_url": url,
            "metadata": {
                "source": "notion",
                "type": "page",
                "page_id": page_id,
                "archived": page.get("archived", False),
            },
            "source_created_at": page.get("created_time"),
            "source_updated_at": page.get("last_edited_time"),
        }

    async def _query_database(self, database_id: str, since: datetime | None) -> list[dict[str, Any]]:
        """Query a Notion database for all rows."""
        rows: list[dict[str, Any]] = []
        cursor: str | None = None
        body: dict[str, Any] = {"page_size": 100}
        if since:
            body["filter"] = {"timestamp": "last_edited_time", "last_edited_time": {"on_or_after": since.isoformat()}}

        while True:
            if cursor:
                body["start_cursor"] = cursor
            try:
                async with httpx.AsyncClient(headers=self._headers(), timeout=30) as client:
                    resp = await client.post(f"{_BASE}/databases/{database_id}/query", json=body)
                    resp.raise_for_status()
                    data = resp.json()
            except Exception as exc:
                logger.warning("Notion database query failed (%s): %s", database_id, exc)
                break

            for page in data.get("results", []):
                doc = await self._page_to_document(page, include_children=True)
                if doc:
                    doc["metadata"]["database_id"] = database_id
                    doc["metadata"]["type"] = "database_row"
                    rows.append(doc)

            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")

        return rows
