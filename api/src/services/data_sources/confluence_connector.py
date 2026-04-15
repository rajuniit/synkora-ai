"""
Confluence data source connector.

Syncs pages and blog posts from Confluence Cloud or Server/Data Center.
Uses Confluence REST API v2 for Cloud, v1 for Server.

Required config fields (data_source.config):
  base_url         — str, e.g. "https://yourcompany.atlassian.net/wiki" (Cloud)
                     or "https://confluence.company.com" (Server)
  space_keys       — list[str], specific space keys to sync (empty = all)
  include_blogs    — bool (default true): include blog posts
  include_children — bool (default true): recursively fetch child pages
  max_page_size    — int (default 50, Cloud max 250)
  is_cloud         — bool (default true)

Auth:
  access_token_encrypted         — OAuth 2.0 Bearer token (Cloud)
  config.api_token_encrypted     — API token (Cloud) with config.email
  config.pat_encrypted           — Personal Access Token (Server/DC)
"""

import logging
from datetime import datetime
from typing import Any

import httpx

from src.models.data_source import DataSource
from src.services.agents.security import decrypt_value

from .base_connector import BaseConnector

logger = logging.getLogger(__name__)


class ConfluenceConnector(BaseConnector):
    """Connector for Confluence pages and blog posts."""

    def __init__(self, data_source: DataSource, db: Any):
        super().__init__(data_source, db)
        self._auth: tuple[str, str] | None = None  # (email, api_token) for Cloud
        self._bearer: str | None = None  # OAuth or PAT

    def get_required_config_fields(self) -> list[str]:
        return ["base_url"]

    def _base_url(self) -> str:
        return self.data_source.config.get("base_url", "").rstrip("/")

    def _is_cloud(self) -> bool:
        return self.data_source.config.get("is_cloud", True)

    def _build_client(self) -> httpx.AsyncClient:
        if self._bearer:
            return httpx.AsyncClient(
                headers={"Authorization": f"Bearer {self._bearer}", "Accept": "application/json"},
                timeout=30,
            )
        if self._auth:
            return httpx.AsyncClient(auth=self._auth, headers={"Accept": "application/json"}, timeout=30)
        raise ValueError("No Confluence credentials configured")

    async def connect(self) -> bool:
        try:
            await self._resolve_credentials()
            async with self._build_client() as client:
                url = f"{self._base_url()}/rest/api/space"
                resp = await client.get(url, params={"limit": 1})
                resp.raise_for_status()
            logger.info("Connected to Confluence at %s", self._base_url())
            return True
        except Exception as exc:
            logger.error("Confluence connect failed: %s", exc)
            return False

    async def disconnect(self) -> None:
        self._bearer = None
        self._auth = None

    async def test_connection(self) -> dict[str, Any]:
        try:
            connected = await self.connect()
            if not connected:
                return {"success": False, "message": "Failed to connect", "details": {}}
            async with self._build_client() as client:
                resp = await client.get(f"{self._base_url()}/rest/api/space", params={"limit": 5})
                data = resp.json()
            await self.disconnect()
            spaces = [s.get("key") for s in data.get("results", [])]
            return {"success": True, "message": "Connection successful", "details": {"spaces": spaces}}
        except Exception as exc:
            return {"success": False, "message": str(exc), "details": {}}

    async def get_document_count(self) -> int:
        pages = await self._fetch_all_pages(since=None, count_only=True)
        return pages

    async def fetch_documents(self, since: datetime | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        cfg = self.data_source.config
        space_keys: list[str] = cfg.get("space_keys") or []
        include_blogs: bool = cfg.get("include_blogs", True)

        documents: list[dict[str, Any]] = []

        if space_keys:
            for key in space_keys:
                docs = await self._fetch_space(key, since, include_blogs)
                documents.extend(docs)
        else:
            # Fetch all accessible spaces first
            spaces = await self._list_spaces()
            for space in spaces:
                docs = await self._fetch_space(space["key"], since, include_blogs)
                documents.extend(docs)

            if limit and len(documents) >= limit:
                return documents[:limit]

        logger.info("Confluence fetched %d documents", len(documents))
        return documents[:limit] if limit else documents

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _resolve_credentials(self) -> None:
        ds = self.data_source
        cfg = ds.config

        # Priority 1: OAuth Bearer token
        if ds.access_token_encrypted:
            self._bearer = decrypt_value(ds.access_token_encrypted)
            return

        # Priority 2: Personal Access Token (Server/DC)
        pat = cfg.get("pat_encrypted") or cfg.get("pat")
        if pat:
            self._bearer = decrypt_value(pat) if pat.startswith("gAAAAA") else pat
            return

        # Priority 3: API token (Cloud) = email + api_token
        api_token_raw = cfg.get("api_token_encrypted") or cfg.get("api_token")
        email = cfg.get("email")
        if api_token_raw and email:
            token = decrypt_value(api_token_raw) if api_token_raw.startswith("gAAAAA") else api_token_raw
            self._auth = (email, token)
            return

        raise ValueError("No Confluence credentials configured")

    async def _list_spaces(self) -> list[dict]:
        spaces: list[dict] = []
        start = 0
        limit = self.data_source.config.get("max_page_size", 50)
        async with self._build_client() as client:
            while True:
                resp = await client.get(
                    f"{self._base_url()}/rest/api/space",
                    params={"type": "global", "start": start, "limit": limit},
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                spaces.extend(results)
                if data.get("size", 0) < limit:
                    break
                start += limit
        return spaces

    async def _fetch_space(self, space_key: str, since: datetime | None, include_blogs: bool) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        for content_type in ["page"] + (["blogpost"] if include_blogs else []):
            pages = await self._search_space_content(space_key, content_type, since)
            for page in pages:
                doc = await self._page_to_document(page)
                if doc:
                    docs.append(doc)
        return docs

    async def _search_space_content(self, space_key: str, content_type: str, since: datetime | None) -> list[dict]:
        """Use CQL to fetch content from a space."""
        cql_parts = [f"type={content_type}", f'space="{space_key}"']
        if since:
            ts = since.strftime("%Y-%m-%d %H:%M")
            cql_parts.append(f'lastModified > "{ts}"')
        cql = " AND ".join(cql_parts) + " ORDER BY lastModified DESC"

        results: list[dict] = []
        start = 0
        limit = self.data_source.config.get("max_page_size", 50)

        async with self._build_client() as client:
            while True:
                try:
                    resp = await client.get(
                        f"{self._base_url()}/rest/api/content/search",
                        params={
                            "cql": cql,
                            "start": start,
                            "limit": limit,
                            "expand": "body.storage,version,ancestors,space",
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as exc:
                    logger.warning("Confluence search failed (space=%s, type=%s): %s", space_key, content_type, exc)
                    break

                batch = data.get("results", [])
                results.extend(batch)

                if len(batch) < limit:
                    break
                start += limit

        return results

    async def _page_to_document(self, page: dict) -> dict[str, Any] | None:
        page_id = page.get("id", "")
        title = page.get("title", "") or ""
        content_type = page.get("type", "page")

        # Extract content from storage format (HTML-like)
        body_storage = page.get("body", {}).get("storage", {})
        raw_body = body_storage.get("value", "")
        content = _strip_confluence_markup(raw_body)

        if not content and not title:
            return None

        full_content = f"{title}\n\n{content}".strip() if content else title

        space = page.get("space", {})
        space_key = space.get("key", "")
        space_name = space.get("name", "")

        # Build URL
        links = page.get("_links", {})
        base = links.get("base", self._base_url())
        web_ui = links.get("webui", f"/display/{space_key}/{page_id}")
        url = f"{base}{web_ui}"

        version = page.get("version", {})
        updated_at = version.get("when")
        created_at = page.get("history", {}).get("createdDate") or updated_at

        return {
            "id": f"confluence_{content_type}_{page_id}",
            "external_id": page_id,
            "title": title or page_id,
            "content": full_content,
            "content_type": "markdown",
            "external_url": url,
            "metadata": {
                "source": "confluence",
                "type": content_type,
                "page_id": page_id,
                "space_key": space_key,
                "space_name": space_name,
                "version": version.get("number", 1),
            },
            "source_created_at": created_at,
            "source_updated_at": updated_at,
        }

    async def _fetch_all_pages(self, since: datetime | None, count_only: bool = False) -> int:
        """Count pages across all spaces (for get_document_count)."""
        total = 0
        spaces = await self._list_spaces()
        for space in spaces:
            pages = await self._search_space_content(space["key"], "page", since)
            total += len(pages)
        return total


def _strip_confluence_markup(html: str) -> str:
    """
    Very lightweight HTML/Confluence macro stripper.
    Removes tags, decodes common entities, collapses whitespace.
    For production use consider 'markdownify' or 'html2text'.
    """
    import re

    # Remove script/style blocks
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove Confluence macros
    html = re.sub(r"<ac:[^>]+>.*?</ac:[^>]+>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<ac:[^/]*/?>", "", html, flags=re.IGNORECASE)
    # Convert block tags to newlines
    html = re.sub(r"</(p|div|li|tr|h[1-6]|br)>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    # Strip remaining tags
    html = re.sub(r"<[^>]+>", "", html)
    # Decode entities
    html = (
        html.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&nbsp;", " ")
        .replace("&#39;", "'")
    )
    # Collapse whitespace
    html = re.sub(r"\n{3,}", "\n\n", html)
    html = re.sub(r" {2,}", " ", html)
    return html.strip()
