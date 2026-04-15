"""
ClickUp data source connector.

Syncs tasks, comments, and subtasks from ClickUp spaces / folders / lists.
Uses the ClickUp REST API v2 with a personal API token or OAuth token.

Required config fields (data_source.config):
  space_ids    — list[str], ClickUp space IDs to sync (empty = all spaces in team)
  list_ids     — list[str], specific list IDs (alternative to space_ids)
  team_id      — str, ClickUp team (workspace) ID
  include_comments  — bool (default true)
  include_subtasks  — bool (default true)
  max_per_page      — int (default 100)

Auth:
  access_token_encrypted — OAuth token  OR
  config.api_token_encrypted — Personal API token (recommended for automation)
"""

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from src.models.data_source import DataSource
from src.services.agents.security import decrypt_value

from .base_connector import BaseConnector

logger = logging.getLogger(__name__)

_BASE = "https://api.clickup.com/api/v2"


class ClickUpConnector(BaseConnector):
    """Connector for ClickUp tasks, comments, and subtasks."""

    def __init__(self, data_source: DataSource, db: Any):
        super().__init__(data_source, db)
        self._token: str = ""

    # ------------------------------------------------------------------
    # BaseConnector interface
    # ------------------------------------------------------------------

    def get_required_config_fields(self) -> list[str]:
        return ["team_id"]

    async def connect(self) -> bool:
        try:
            self._token = await self._get_token()
            async with httpx.AsyncClient(headers=self._headers(), timeout=15) as client:
                resp = await client.get(f"{_BASE}/user")
                resp.raise_for_status()
                user = resp.json().get("user", {})
                logger.info("Connected to ClickUp as: %s", user.get("username"))
            return True
        except Exception as exc:
            logger.error("ClickUp connect failed: %s", exc)
            return False

    async def disconnect(self) -> None:
        self._token = ""

    async def test_connection(self) -> dict[str, Any]:
        try:
            connected = await self.connect()
            if not connected:
                return {"success": False, "message": "Failed to connect", "details": {}}
            async with httpx.AsyncClient(headers=self._headers(), timeout=15) as client:
                resp = await client.get(f"{_BASE}/user")
                user = resp.json().get("user", {})
            await self.disconnect()
            return {
                "success": True,
                "message": "Connection successful",
                "details": {"username": user.get("username"), "email": user.get("email")},
            }
        except Exception as exc:
            return {"success": False, "message": str(exc), "details": {}}

    async def get_document_count(self) -> int:
        """Approximate count — ClickUp doesn't expose a single count endpoint."""
        lists = await self._get_all_lists()
        total = 0
        for lst in lists[:10]:  # sample first 10 lists
            try:
                async with httpx.AsyncClient(headers=self._headers(), timeout=15) as client:
                    resp = await client.get(
                        f"{_BASE}/list/{lst['id']}/task",
                        params={"subtasks": "true", "page": 0},
                    )
                    data = resp.json()
                    total += len(data.get("tasks", []))
            except Exception:
                pass
        return total

    async def fetch_documents(
        self, since: datetime | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        include_comments = self.data_source.config.get("include_comments", True)
        include_subtasks = self.data_source.config.get("include_subtasks", True)
        documents: list[dict[str, Any]] = []

        lists = await self._get_all_lists()
        for lst in lists:
            tasks = await self._fetch_list_tasks(lst["id"], since, include_subtasks)
            for task in tasks:
                doc = self._task_to_document(task)
                documents.append(doc)

                if include_comments:
                    comments = await self._fetch_task_comments(task["id"])
                    documents.extend(comments)

                if limit and len(documents) >= limit:
                    return documents[:limit]

        logger.info("ClickUp fetched %d documents", len(documents))
        return documents

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_token(self) -> str:
        if self.data_source.access_token_encrypted:
            return decrypt_value(self.data_source.access_token_encrypted)

        cfg = self.data_source.config
        api_token = cfg.get("api_token_encrypted") or cfg.get("api_token")
        if api_token:
            return decrypt_value(api_token) if api_token.startswith("gAAAAA") else api_token

        raise ValueError("No ClickUp auth configured (need access_token or api_token)")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": self._token, "Content-Type": "application/json"}

    async def _get_all_lists(self) -> list[dict[str, Any]]:
        """Return all lists from the configured spaces, list_ids, or entire team."""
        cfg = self.data_source.config
        team_id = cfg.get("team_id", "")
        explicit_list_ids: list[str] = cfg.get("list_ids") or []
        space_ids: list[str] = cfg.get("space_ids") or []

        if explicit_list_ids:
            return [{"id": lid} for lid in explicit_list_ids]

        if not space_ids and team_id:
            # Fetch all spaces for the team
            space_ids = await self._get_space_ids(team_id)

        all_lists: list[dict[str, Any]] = []
        for sid in space_ids:
            all_lists.extend(await self._get_lists_in_space(sid))

        return all_lists

    async def _get_space_ids(self, team_id: str) -> list[str]:
        try:
            async with httpx.AsyncClient(headers=self._headers(), timeout=15) as client:
                resp = await client.get(f"{_BASE}/team/{team_id}/space", params={"archived": False})
                resp.raise_for_status()
                spaces = resp.json().get("spaces", [])
                return [s["id"] for s in spaces]
        except Exception as exc:
            logger.warning("ClickUp get_space_ids failed: %s", exc)
            return []

    async def _get_lists_in_space(self, space_id: str) -> list[dict[str, Any]]:
        try:
            all_lists: list[dict] = []
            async with httpx.AsyncClient(headers=self._headers(), timeout=15) as client:
                # Get lists directly in space (no folder)
                resp = await client.get(f"{_BASE}/space/{space_id}/list", params={"archived": False})
                resp.raise_for_status()
                all_lists.extend(resp.json().get("lists", []))
                # Get folders then their lists
                resp2 = await client.get(f"{_BASE}/space/{space_id}/folder", params={"archived": False})
                resp2.raise_for_status()
                for folder in resp2.json().get("folders", []):
                    for lst in folder.get("lists", []):
                        all_lists.append(lst)
            return all_lists
        except Exception as exc:
            logger.warning("ClickUp get_lists_in_space(%s) failed: %s", space_id, exc)
            return []

    async def _fetch_list_tasks(
        self, list_id: str, since: datetime | None, include_subtasks: bool
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "subtasks": str(include_subtasks).lower(),
            "page": 0,
            "order_by": "updated",
            "reverse": True,
        }
        if since:
            # ClickUp uses Unix milliseconds
            params["date_updated_gt"] = int(since.timestamp() * 1000)

        tasks: list[dict] = []
        page_size = self.data_source.config.get("max_per_page", 100)

        while True:
            try:
                async with httpx.AsyncClient(headers=self._headers(), timeout=30) as client:
                    resp = await client.get(f"{_BASE}/list/{list_id}/task", params=params)
                    resp.raise_for_status()
                    page_tasks = resp.json().get("tasks", [])
            except Exception as exc:
                logger.warning("ClickUp task fetch failed for list %s: %s", list_id, exc)
                break

            tasks.extend(page_tasks)
            if len(page_tasks) < page_size:
                break
            params["page"] += 1

        return tasks

    async def _fetch_task_comments(self, task_id: str) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(headers=self._headers(), timeout=15) as client:
                resp = await client.get(f"{_BASE}/task/{task_id}/comment")
                resp.raise_for_status()
                comments = resp.json().get("comments", [])
        except Exception:
            return []

        docs = []
        for c in comments:
            text = c.get("comment_text") or ""
            if not text.strip():
                continue
            docs.append({
                "id": f"clickup_comment_{c['id']}",
                "external_id": str(c["id"]),
                "title": f"Comment on task {task_id}",
                "content": text,
                "content_type": "text",
                "metadata": {
                    "source": "clickup",
                    "type": "comment",
                    "task_id": task_id,
                    "author": (c.get("user") or {}).get("username"),
                    "author_email": (c.get("user") or {}).get("email"),
                },
                "source_created_at": _ms_to_iso(c.get("date")),
            })
        return docs

    def _task_to_document(self, task: dict[str, Any]) -> dict[str, Any]:
        name = task.get("name", "")
        description = task.get("description") or ""
        content = f"{name}\n\n{description}".strip() if description else name

        assignees = [a.get("username", "") for a in (task.get("assignees") or [])]
        tags = [t.get("name", "") for t in (task.get("tags") or [])]

        return {
            "id": f"clickup_task_{task['id']}",
            "external_id": task["id"],
            "title": name,
            "content": content,
            "content_type": "text",
            "external_url": task.get("url"),
            "metadata": {
                "source": "clickup",
                "type": "task",
                "task_id": task["id"],
                "status": (task.get("status") or {}).get("status"),
                "priority": (task.get("priority") or {}).get("priority"),
                "list": (task.get("list") or {}).get("name"),
                "space": (task.get("space") or {}).get("name"),
                "assignees": assignees,
                "tags": tags,
                "creator": (task.get("creator") or {}).get("username"),
            },
            "source_created_at": _ms_to_iso(task.get("date_created")),
            "source_updated_at": _ms_to_iso(task.get("date_updated")),
        }


def _ms_to_iso(ms: Any) -> str | None:
    """Convert Unix milliseconds (as str or int) to ISO-8601 string."""
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=UTC).isoformat()
    except Exception:
        return None
