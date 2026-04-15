"""
Jira data source connector.

Syncs issues, comments, and changelogs from a Jira Cloud or Data Center instance.
Supports both OAuth 2.0 (Jira Cloud) and API token (Data Center / personal token).

Required config fields (data_source.config):
  cloud_id      — Jira Cloud site ID (Cloud only; omit for Data Center)
  base_url      — e.g. "https://mycompany.atlassian.net" or "https://jira.internal"
  project_keys  — list[str], e.g. ["BE", "INFRA", "DATA"] (empty = all projects)
  include_comments — bool (default true)
  max_results_per_page — int (default 100)

Auth (one of):
  access_token_encrypted — OAuth 2.0 access token (recommended for Cloud)
  OR config.api_token + config.email — Basic auth for Data Center / personal token
"""

import logging
from datetime import datetime
from typing import Any

import httpx

from src.models.data_source import DataSource
from src.services.agents.security import decrypt_value

from .base_connector import BaseConnector

logger = logging.getLogger(__name__)


class JiraConnector(BaseConnector):
    """Connector for Jira Cloud and Data Center."""

    def __init__(self, data_source: DataSource, db: Any):
        super().__init__(data_source, db)
        self._headers: dict[str, str] = {}
        self._base_url: str = ""

    # ------------------------------------------------------------------
    # BaseConnector interface
    # ------------------------------------------------------------------

    def get_required_config_fields(self) -> list[str]:
        return ["base_url"]

    async def connect(self) -> bool:
        try:
            self._base_url = self.data_source.config.get("base_url", "").rstrip("/")
            if not self._base_url:
                logger.error("Jira connector: base_url not configured")
                return False

            self._headers = await self._build_headers()
            # Verify connection
            async with httpx.AsyncClient(headers=self._headers, timeout=15) as client:
                resp = await client.get(f"{self._base_url}/rest/api/3/myself")
                resp.raise_for_status()
                user = resp.json()
                logger.info("Connected to Jira as: %s", user.get("displayName"))
            return True
        except Exception as exc:
            logger.error("Jira connect failed: %s", exc)
            return False

    async def disconnect(self) -> None:
        self._headers = {}

    async def test_connection(self) -> dict[str, Any]:
        try:
            connected = await self.connect()
            if not connected:
                return {"success": False, "message": "Failed to connect", "details": {}}
            async with httpx.AsyncClient(headers=self._headers, timeout=15) as client:
                resp = await client.get(f"{self._base_url}/rest/api/3/serverInfo")
                info = resp.json()
            await self.disconnect()
            return {
                "success": True,
                "message": "Connection successful",
                "details": {
                    "version": info.get("version"),
                    "server_title": info.get("serverTitle"),
                    "deployment_type": info.get("deploymentType"),
                },
            }
        except Exception as exc:
            return {"success": False, "message": str(exc), "details": {}}

    async def get_document_count(self) -> int:
        try:
            jql = self._build_jql(since=None)
            async with httpx.AsyncClient(headers=self._headers, timeout=30) as client:
                resp = await client.get(
                    f"{self._base_url}/rest/api/3/search",
                    params={"jql": jql, "maxResults": 0},
                )
                resp.raise_for_status()
                return resp.json().get("total", 0)
        except Exception:
            return 0

    async def fetch_documents(
        self, since: datetime | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Fetch Jira issues (+ optionally comments) updated since `since`."""
        documents: list[dict[str, Any]] = []
        include_comments = self.data_source.config.get("include_comments", True)
        page_size = self.data_source.config.get("max_results_per_page", 100)
        jql = self._build_jql(since)
        start_at = 0

        while True:
            batch = await self._fetch_issue_page(jql, start_at, page_size)
            if not batch:
                break

            for issue in batch:
                doc = self._issue_to_document(issue)
                documents.append(doc)

                if include_comments:
                    comments = await self._fetch_comments(issue["id"])
                    documents.extend(comments)

            start_at += len(batch)
            if limit and len(documents) >= limit:
                documents = documents[:limit]
                break
            if len(batch) < page_size:
                break

        logger.info("Jira fetched %d documents (JQL: %s)", len(documents), jql)
        return documents

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _build_headers(self) -> dict[str, str]:
        """Return HTTP headers for Jira API auth."""
        cfg = self.data_source.config

        # OAuth 2.0 access token (Jira Cloud)
        if self.data_source.access_token_encrypted:
            token = decrypt_value(self.data_source.access_token_encrypted)
            return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # API token + email (Data Center / personal token)
        api_token = cfg.get("api_token_encrypted") or cfg.get("api_token")
        email = cfg.get("email")
        if api_token and email:
            if api_token.startswith("gAAAAA"):
                api_token = decrypt_value(api_token)
            import base64
            credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
            return {"Authorization": f"Basic {credentials}", "Content-Type": "application/json"}

        raise ValueError("No Jira auth configured (need access_token or api_token + email)")

    def _build_jql(self, since: datetime | None) -> str:
        """Build a JQL query to fetch relevant issues."""
        cfg = self.data_source.config
        project_keys: list[str] = cfg.get("project_keys") or []

        clauses: list[str] = []
        if project_keys:
            keys_str = ", ".join(f'"{k}"' for k in project_keys)
            clauses.append(f"project in ({keys_str})")
        if since:
            # JQL date format: YYYY-MM-DD HH:mm
            since_str = since.strftime("%Y-%m-%d %H:%M")
            clauses.append(f'updated >= "{since_str}"')

        clauses.append("ORDER BY updated DESC")
        return " AND ".join(clauses[:-1]) + " " + clauses[-1] if len(clauses) > 1 else clauses[-1]

    async def _fetch_issue_page(self, jql: str, start_at: int, max_results: int) -> list[dict]:
        fields = "summary,description,status,priority,assignee,reporter,created,updated,labels,comment,issuetype,project"
        try:
            async with httpx.AsyncClient(headers=self._headers, timeout=30) as client:
                resp = await client.get(
                    f"{self._base_url}/rest/api/3/search",
                    params={
                        "jql": jql,
                        "startAt": start_at,
                        "maxResults": max_results,
                        "fields": fields,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("issues", [])
        except Exception as exc:
            logger.error("Jira fetch_issue_page failed: %s", exc)
            return []

    async def _fetch_comments(self, issue_id: str) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(headers=self._headers, timeout=15) as client:
                resp = await client.get(f"{self._base_url}/rest/api/3/issue/{issue_id}/comment")
                resp.raise_for_status()
                comments = resp.json().get("comments", [])
        except Exception:
            return []

        docs = []
        for c in comments:
            body = self._extract_text(c.get("body"))
            if not body:
                continue
            docs.append({
                "id": f"jira_comment_{c['id']}",
                "external_id": f"comment_{c['id']}",
                "title": f"Comment on {issue_id}",
                "content": body,
                "content_type": "text",
                "metadata": {
                    "source": "jira",
                    "type": "comment",
                    "issue_id": issue_id,
                    "author": c.get("author", {}).get("displayName"),
                    "author_email": c.get("author", {}).get("emailAddress"),
                },
                "source_created_at": c.get("created"),
                "source_updated_at": c.get("updated"),
            })
        return docs

    def _issue_to_document(self, issue: dict[str, Any]) -> dict[str, Any]:
        fields = issue.get("fields", {})
        summary = fields.get("summary", "")
        description = self._extract_text(fields.get("description"))
        content = f"{summary}\n\n{description}".strip() if description else summary

        return {
            "id": f"jira_issue_{issue['id']}",
            "external_id": issue.get("key", issue["id"]),
            "title": summary,
            "content": content,
            "content_type": "text",
            "external_url": f"{self._base_url}/browse/{issue.get('key', '')}",
            "metadata": {
                "source": "jira",
                "type": "issue",
                "issue_key": issue.get("key"),
                "project": fields.get("project", {}).get("key"),
                "status": fields.get("status", {}).get("name"),
                "priority": fields.get("priority", {}).get("name"),
                "issue_type": fields.get("issuetype", {}).get("name"),
                "assignee": (fields.get("assignee") or {}).get("displayName"),
                "assignee_email": (fields.get("assignee") or {}).get("emailAddress"),
                "reporter": (fields.get("reporter") or {}).get("displayName"),
                "labels": fields.get("labels", []),
            },
            "source_created_at": fields.get("created"),
            "source_updated_at": fields.get("updated"),
        }

    def _extract_text(self, adf: Any) -> str:
        """Extract plain text from Atlassian Document Format (ADF) or plain string."""
        if not adf:
            return ""
        if isinstance(adf, str):
            return adf
        # ADF is a nested dict — extract all text nodes recursively
        texts: list[str] = []
        self._walk_adf(adf, texts)
        return " ".join(texts)

    def _walk_adf(self, node: Any, texts: list[str]) -> None:
        if isinstance(node, dict):
            if node.get("type") == "text":
                texts.append(node.get("text", ""))
            for child in node.get("content") or []:
                self._walk_adf(child, texts)
        elif isinstance(node, list):
            for item in node:
                self._walk_adf(item, texts)
