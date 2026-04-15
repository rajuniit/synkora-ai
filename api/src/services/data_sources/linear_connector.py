"""
Linear data source connector.

Syncs issues, projects, and cycles from Linear workspaces.
Uses the Linear GraphQL API.

Required config fields (data_source.config):
  team_ids   — list[str], specific team IDs to sync (empty = all)
  include_archived — bool (default false)
  max_page_size — int (default 50, max 250)

Auth:
  access_token_encrypted        — OAuth access token OR
  config.api_key_encrypted      — Personal API key
"""

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from src.models.data_source import DataSource
from src.services.agents.security import decrypt_value

from .base_connector import BaseConnector

logger = logging.getLogger(__name__)

_GRAPHQL_URL = "https://api.linear.app/graphql"


class LinearConnector(BaseConnector):
    """Connector for Linear issues and projects."""

    def __init__(self, data_source: DataSource, db: Any):
        super().__init__(data_source, db)
        self._token: str = ""

    def get_required_config_fields(self) -> list[str]:
        return []

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._token,
            "Content-Type": "application/json",
        }

    async def connect(self) -> bool:
        try:
            self._token = await self._get_token()
            async with httpx.AsyncClient(headers=self._headers(), timeout=15) as client:
                resp = await client.post(_GRAPHQL_URL, json={"query": "{ viewer { id name } }"})
                resp.raise_for_status()
                data = resp.json()
                viewer = data.get("data", {}).get("viewer", {})
                logger.info("Connected to Linear as: %s", viewer.get("name", viewer.get("id")))
            return True
        except Exception as exc:
            logger.error("Linear connect failed: %s", exc)
            return False

    async def disconnect(self) -> None:
        self._token = ""

    async def test_connection(self) -> dict[str, Any]:
        try:
            connected = await self.connect()
            if not connected:
                return {"success": False, "message": "Failed to connect", "details": {}}
            async with httpx.AsyncClient(headers=self._headers(), timeout=15) as client:
                resp = await client.post(_GRAPHQL_URL, json={"query": "{ viewer { id name email } }"})
                viewer = resp.json().get("data", {}).get("viewer", {})
            await self.disconnect()
            return {
                "success": True,
                "message": "Connection successful",
                "details": {"name": viewer.get("name"), "email": viewer.get("email")},
            }
        except Exception as exc:
            return {"success": False, "message": str(exc), "details": {}}

    async def get_document_count(self) -> int:
        issues = await self._fetch_issues(since=None, count_only=True)
        return issues

    async def fetch_documents(
        self, since: datetime | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        cfg = self.data_source.config
        team_ids: list[str] = cfg.get("team_ids") or []

        documents: list[dict[str, Any]] = []

        if team_ids:
            for tid in team_ids:
                issues = await self._fetch_team_issues(tid, since)
                documents.extend(issues)
        else:
            # Fetch from all teams
            teams = await self._list_teams()
            for team in teams:
                issues = await self._fetch_team_issues(team["id"], since)
                documents.extend(issues)

        logger.info("Linear fetched %d documents", len(documents))
        return documents[:limit] if limit else documents

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_token(self) -> str:
        if self.data_source.access_token_encrypted:
            return decrypt_value(self.data_source.access_token_encrypted)
        cfg = self.data_source.config
        key = cfg.get("api_key_encrypted") or cfg.get("api_key")
        if key:
            return decrypt_value(key) if key.startswith("gAAAAA") else key
        raise ValueError("No Linear token configured")

    async def _gql(self, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL query and return the data dict."""
        body: dict[str, Any] = {"query": query}
        if variables:
            body["variables"] = variables
        async with httpx.AsyncClient(headers=self._headers(), timeout=30) as client:
            resp = await client.post(_GRAPHQL_URL, json=body)
            resp.raise_for_status()
            result = resp.json()
        errors = result.get("errors")
        if errors:
            raise RuntimeError(f"Linear GraphQL errors: {errors}")
        return result.get("data", {})

    async def _list_teams(self) -> list[dict]:
        query = """
        query {
          teams {
            nodes { id name key }
          }
        }
        """
        data = await self._gql(query)
        return data.get("teams", {}).get("nodes", [])

    async def _fetch_team_issues(self, team_id: str, since: datetime | None) -> list[dict[str, Any]]:
        """Paginate through all issues for a team."""
        cfg = self.data_source.config
        include_archived = cfg.get("include_archived", False)
        page_size = min(cfg.get("max_page_size", 50), 250)

        filter_clause = f'teamId: {{ eq: "{team_id}" }}'
        if since:
            ts = since.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            filter_clause += f', updatedAt: {{ gte: "{ts}" }}'

        query = """
        query($filter: IssueFilter, $first: Int, $after: String) {
          issues(filter: $filter, first: $first, after: $after, orderBy: updatedAt) {
            nodes {
              id
              identifier
              title
              description
              state { name type }
              priority
              priorityLabel
              assignee { id name email }
              creator { id name email }
              team { id name key }
              project { id name }
              cycle { id name number }
              labels { nodes { id name color } }
              parent { id identifier title }
              url
              createdAt
              updatedAt
              archivedAt
              completedAt
              canceledAt
              comments {
                nodes {
                  id
                  body
                  user { name email }
                  createdAt
                }
              }
            }
            pageInfo { hasNextPage endCursor }
          }
        }
        """

        issues: list[dict[str, Any]] = []
        cursor: str | None = None

        while True:
            variables: dict[str, Any] = {
                "filter": {"teamId": {"eq": team_id}},
                "first": page_size,
            }
            if since:
                variables["filter"]["updatedAt"] = {"gte": since.strftime("%Y-%m-%dT%H:%M:%S.000Z")}
            if not include_archived:
                variables["filter"]["archivedAt"] = {"null": True}
            if cursor:
                variables["after"] = cursor

            try:
                data = await self._gql(query, variables)
            except Exception as exc:
                logger.warning("Linear issues fetch failed (team=%s): %s", team_id, exc)
                break

            nodes = data.get("issues", {}).get("nodes", [])
            for node in nodes:
                doc = self._issue_to_document(node)
                if doc:
                    issues.append(doc)

            page_info = data.get("issues", {}).get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")

        return issues

    def _issue_to_document(self, issue: dict) -> dict[str, Any] | None:
        issue_id = issue.get("id", "")
        identifier = issue.get("identifier", "")  # e.g. "ENG-42"
        title = issue.get("title", "") or ""
        description = issue.get("description", "") or ""

        # Build content with structured context
        parts = [f"# {identifier}: {title}"]

        state = issue.get("state", {}) or {}
        if state.get("name"):
            parts.append(f"Status: {state['name']}")

        if issue.get("priorityLabel"):
            parts.append(f"Priority: {issue['priorityLabel']}")

        assignee = issue.get("assignee") or {}
        if assignee.get("name"):
            parts.append(f"Assignee: {assignee['name']} ({assignee.get('email', '')})")

        project = issue.get("project") or {}
        if project.get("name"):
            parts.append(f"Project: {project['name']}")

        labels = [lb["name"] for lb in (issue.get("labels") or {}).get("nodes", []) if lb.get("name")]
        if labels:
            parts.append(f"Labels: {', '.join(labels)}")

        if description:
            parts.append(f"\n{description}")

        # Append comments
        comments = (issue.get("comments") or {}).get("nodes", [])
        if comments:
            parts.append("\n## Comments")
            for c in comments:
                user = (c.get("user") or {}).get("name", "unknown")
                parts.append(f"**{user}** ({c.get('createdAt', '')[:10]}): {c.get('body', '')}")

        content = "\n".join(parts).strip()
        if not content:
            return None

        team = issue.get("team") or {}
        creator = issue.get("creator") or {}

        return {
            "id": f"linear_issue_{issue_id}",
            "external_id": issue_id,
            "title": f"{identifier}: {title}" if identifier else title,
            "content": content,
            "content_type": "markdown",
            "external_url": issue.get("url", ""),
            "metadata": {
                "source": "linear",
                "type": "issue",
                "issue_id": issue_id,
                "identifier": identifier,
                "status": state.get("name", ""),
                "state_type": state.get("type", ""),
                "priority": issue.get("priority", 0),
                "team_id": team.get("id", ""),
                "team_key": team.get("key", ""),
                "project_id": (issue.get("project") or {}).get("id", ""),
                "assignee_email": assignee.get("email", ""),
                "creator_email": creator.get("email", ""),
                "labels": labels,
            },
            "source_created_at": issue.get("createdAt"),
            "source_updated_at": issue.get("updatedAt"),
        }

    async def _fetch_issues(self, since: datetime | None, count_only: bool = False) -> int:
        teams = await self._list_teams()
        total = 0
        for team in teams:
            issues = await self._fetch_team_issues(team["id"], since)
            total += len(issues)
        return total
