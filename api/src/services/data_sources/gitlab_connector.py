"""
GitLab Data Source Connector.

Handles syncing data from GitLab projects, issues, merge requests, and code files.
Supports self-hosted GitLab instances.
"""

import base64
import logging
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.data_source import DataSource
from src.services.agents.security import decrypt_value

from .base_connector import BaseConnector

logger = logging.getLogger(__name__)


class GitLabConnector(BaseConnector):
    """Connector for GitLab data sources with self-hosted support."""

    def __init__(self, data_source: DataSource, db: AsyncSession):
        """
        Initialize GitLab connector.

        Args:
            data_source: DataSource model instance
            db: Async database session
        """
        super().__init__(data_source, db)
        # Support self-hosted GitLab via config
        gitlab_url = (
            data_source.config.get("base_url", "https://gitlab.com") if data_source.config else "https://gitlab.com"
        )
        self.base_url = f"{gitlab_url.rstrip('/')}/api/v4"

    async def _get_access_token(self) -> str:
        """Get decrypted access token from data source or linked OAuth app."""
        # First try to get token directly from data source
        if self.data_source.access_token_encrypted:
            return decrypt_value(self.data_source.access_token_encrypted)

        # Fall back to OAuth app if linked
        if self.data_source.oauth_app_id and self.data_source.oauth_app:
            oauth_app = self.data_source.oauth_app

            # Determine which authentication method to use based on auth_method
            if oauth_app.auth_method == "api_token":
                # Use API token (PAT)
                if not oauth_app.api_token:
                    raise ValueError(
                        "No API token configured. Please add a GitLab Personal Access Token to this OAuth app."
                    )
                return decrypt_value(oauth_app.api_token)
            else:
                # Use OAuth token
                if not oauth_app.access_token:
                    raise ValueError(
                        "No OAuth access token available. Please complete OAuth flow first or use API token method."
                    )
                return decrypt_value(oauth_app.access_token)

        raise ValueError("No access token configured for GitLab data source")

    def _get_auth_method(self) -> str:
        """Determine auth method (api_token or oauth)."""
        if self.data_source.oauth_app_id and self.data_source.oauth_app:
            return self.data_source.oauth_app.auth_method or "oauth"
        return "oauth"

    async def _make_request(
        self, method: str, endpoint: str, params: dict[str, Any] | None = None, json_data: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[Any]:
        """
        Make authenticated request to GitLab API.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            json_data: JSON body data

        Returns:
            Response data
        """
        token = await self._get_access_token()
        auth_method = self._get_auth_method()

        # GitLab uses different auth headers for PAT vs OAuth
        if auth_method == "api_token":
            headers = {"PRIVATE-TOKEN": token}
        else:
            headers = {"Authorization": f"Bearer {token}"}

        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method, url=url, headers=headers, params=params, json=json_data, timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def connect(self) -> bool:
        """Establish connection to GitLab (test API access)."""
        try:
            await self._get_access_token()
            # Test connection by getting user info
            await self._make_request("GET", "/user")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to GitLab: {e}")
            return False

    async def disconnect(self) -> None:
        """Close connection to GitLab."""
        # No persistent connection to close
        pass

    async def fetch_documents(self, since: datetime | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        """
        Fetch documents from GitLab.

        Args:
            since: Fetch documents modified since this timestamp
            limit: Maximum number of documents to fetch

        Returns:
            List of documents
        """
        documents = []
        config = self.data_source.config or {}
        projects = config.get("projects", [])

        # Handle case where projects is a single string instead of a list
        if isinstance(projects, str):
            projects = [projects]

        sync_issues = config.get("sync_issues", True)
        sync_merge_requests = config.get("sync_merge_requests", True)
        sync_code = config.get("sync_code", False)

        for project in projects:
            # Handle both string format "namespace/project" and object format
            if isinstance(project, str):
                project_path = project
            elif isinstance(project, dict):
                project_path = project.get("path") or f"{project.get('namespace')}/{project.get('name')}"
            else:
                logger.warning(f"Invalid project config: {project}")
                continue

            if not project_path:
                logger.warning(f"Invalid project config: {project}")
                continue

            logger.info(f"Syncing GitLab project: {project_path}")

            # URL encode the project path for API calls
            encoded_path = project_path.replace("/", "%2F")

            # Fetch README
            readme_docs = await self._sync_readme(encoded_path, project_path)
            documents.extend(readme_docs)

            # Fetch issues if enabled
            if sync_issues:
                issue_docs = await self._sync_issues(encoded_path, project_path)
                documents.extend(issue_docs)

            # Fetch merge requests if enabled
            if sync_merge_requests:
                mr_docs = await self._sync_merge_requests(encoded_path, project_path)
                documents.extend(mr_docs)

            # Fetch code files if enabled
            if sync_code and isinstance(project, dict):
                code_docs = await self._sync_code_files(encoded_path, project_path, project.get("paths", []))
                documents.extend(code_docs)

            if limit and len(documents) >= limit:
                break

        return documents[:limit] if limit else documents

    async def get_document_count(self) -> int:
        """Get total number of documents."""
        # Approximate count based on projects
        config = self.data_source.config or {}
        projects = config.get("projects", [])
        # Rough estimate: README + 100 issues + 50 MRs per project
        return len(projects) * 151

    def get_required_config_fields(self) -> list[str]:
        """Get required configuration fields."""
        return ["projects"]

    async def _create_document(self, title: str, content: str, metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Create a document dict for processing.

        Args:
            title: Document title
            content: Document content
            metadata: Document metadata

        Returns:
            Document dictionary
        """
        return {
            "id": f"{metadata.get('project', 'unknown')}_{metadata.get('type', 'doc')}_{hash(title)}",
            "text": content,
            "metadata": {"title": title, "source": "gitlab", **metadata},
        }

    async def _sync_readme(self, encoded_path: str, project_path: str) -> list[dict[str, Any]]:
        """Sync project README."""
        try:
            # Try common README filenames
            readme_files = ["README.md", "README.rst", "README.txt", "README"]

            for readme_name in readme_files:
                try:
                    encoded_file = readme_name.replace("/", "%2F")
                    data = await self._make_request(
                        "GET", f"/projects/{encoded_path}/repository/files/{encoded_file}", params={"ref": "HEAD"}
                    )

                    # Decode base64 content
                    content = base64.b64decode(data["content"]).decode("utf-8")

                    # Create document
                    doc = await self._create_document(
                        title=f"{project_path} - README",
                        content=content,
                        metadata={
                            "type": "readme",
                            "project": project_path,
                            "path": data["file_path"],
                            "url": data.get("blob_id", ""),
                        },
                    )

                    return [doc]
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        continue  # Try next README file
                    raise

            logger.info(f"No README found for {project_path}")
            return []

        except Exception as e:
            logger.warning(f"Failed to sync README for {project_path}: {e}")
            return []

    async def _sync_issues(self, encoded_path: str, project_path: str) -> list[dict[str, Any]]:
        """Sync project issues."""
        documents = []

        try:
            # Get issues
            issues = await self._make_request(
                "GET", f"/projects/{encoded_path}/issues", params={"state": "all", "per_page": 100}
            )

            for issue in issues:
                # Build content
                content = f"# {issue['title']}\n\n"
                content += f"**State:** {issue['state']}\n"
                content += f"**Created:** {issue['created_at']}\n"
                content += f"**Author:** {issue['author']['username']}\n\n"

                if issue.get("description"):
                    content += f"{issue['description']}\n\n"

                # Add notes (comments)
                if issue.get("user_notes_count", 0) > 0:
                    try:
                        notes = await self._make_request("GET", f"/projects/{encoded_path}/issues/{issue['iid']}/notes")

                        content += "## Comments\n\n"
                        for note in notes:
                            if not note.get("system", False):  # Skip system notes
                                content += f"**{note['author']['username']}** ({note['created_at']}):\n"
                                content += f"{note['body']}\n\n"
                    except Exception as e:
                        logger.warning(f"Failed to fetch notes for issue #{issue['iid']}: {e}")

                # Create document
                doc = await self._create_document(
                    title=f"Issue #{issue['iid']}: {issue['title']}",
                    content=content,
                    metadata={
                        "type": "issue",
                        "project": project_path,
                        "issue_iid": issue["iid"],
                        "state": issue["state"],
                        "url": issue["web_url"],
                        "labels": issue.get("labels", []),
                    },
                )

                if doc:
                    documents.append(doc)

            logger.info(f"Synced {len(documents)} issues from {project_path}")

        except Exception as e:
            logger.error(f"Failed to sync issues for {project_path}: {e}")

        return documents

    async def _sync_merge_requests(self, encoded_path: str, project_path: str) -> list[dict[str, Any]]:
        """Sync project merge requests."""
        documents = []

        try:
            mrs = await self._make_request(
                "GET", f"/projects/{encoded_path}/merge_requests", params={"state": "all", "per_page": 100}
            )

            for mr in mrs:
                # Build content
                content = f"# {mr['title']}\n\n"
                content += f"**State:** {mr['state']}\n"
                content += f"**Created:** {mr['created_at']}\n"
                content += f"**Author:** {mr['author']['username']}\n"
                content += f"**Target Branch:** {mr['target_branch']} <- **Source Branch:** {mr['source_branch']}\n\n"

                if mr.get("description"):
                    content += f"{mr['description']}\n\n"

                # Create document
                doc = await self._create_document(
                    title=f"MR !{mr['iid']}: {mr['title']}",
                    content=content,
                    metadata={
                        "type": "merge_request",
                        "project": project_path,
                        "mr_iid": mr["iid"],
                        "state": mr["state"],
                        "url": mr["web_url"],
                        "target_branch": mr["target_branch"],
                        "source_branch": mr["source_branch"],
                    },
                )

                if doc:
                    documents.append(doc)

            logger.info(f"Synced {len(documents)} merge requests from {project_path}")

        except Exception as e:
            logger.error(f"Failed to sync merge requests for {project_path}: {e}")

        return documents

    async def _sync_code_files(self, encoded_path: str, project_path: str, paths: list[str]) -> list[dict[str, Any]]:
        """Sync specific code files from project."""
        documents = []

        try:
            for path in paths:
                try:
                    encoded_file = path.replace("/", "%2F")
                    data = await self._make_request(
                        "GET", f"/projects/{encoded_path}/repository/files/{encoded_file}", params={"ref": "HEAD"}
                    )

                    # Decode base64 content
                    content = base64.b64decode(data["content"]).decode("utf-8")

                    # Create document
                    doc = await self._create_document(
                        title=f"{project_path}/{path}",
                        content=content,
                        metadata={"type": "code", "project": project_path, "path": path, "size": data.get("size", 0)},
                    )

                    if doc:
                        documents.append(doc)

                except Exception as e:
                    logger.warning(f"Failed to sync file {path}: {e}")

            logger.info(f"Synced {len(documents)} code files from {project_path}")

        except Exception as e:
            logger.error(f"Failed to sync code files for {project_path}: {e}")

        return documents

    async def test_connection(self) -> dict[str, Any]:
        """
        Test GitLab connection.

        Returns:
            Connection test result
        """
        try:
            # Get authenticated user info
            user = await self._make_request("GET", "/user")

            return {
                "success": True,
                "message": f"Connected as {user['username']}",
                "user": {"username": user["username"], "name": user.get("name"), "email": user.get("email")},
            }

        except Exception as e:
            logger.error(f"GitLab connection test failed: {e}")
            return {"success": False, "error": str(e)}
