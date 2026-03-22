import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.agents.credential_resolver import CredentialResolver
from src.services.agents.runtime_context import RuntimeContext


class TestCredentialResolver:
    @pytest.fixture
    def mock_db_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def runtime_context(self, mock_db_session):
        ctx = RuntimeContext(tenant_id=uuid.uuid4(), agent_id=uuid.uuid4(), db_session=mock_db_session)
        return ctx

    @pytest.fixture
    def resolver(self, runtime_context):
        return CredentialResolver(runtime_context)

    @pytest.mark.asyncio
    async def test_get_github_client_success(self, resolver, mock_db_session):
        # Mock AgentTool
        mock_tool = MagicMock()
        mock_tool.oauth_app_id = uuid.uuid4()

        # Mock OAuthApp
        mock_oauth_app = MagicMock()
        mock_oauth_app.auth_method = "oauth"
        mock_oauth_app.access_token = "encrypted_token"

        # Setup execute mock to return different results for sequential calls
        # First call: AgentTool query
        # Second call: OAuthApp query
        mock_result_tool = MagicMock()
        mock_result_tool.scalar_one_or_none.return_value = mock_tool

        mock_result_oauth = MagicMock()
        mock_result_oauth.scalar_one_or_none.return_value = mock_oauth_app

        mock_db_session.execute = AsyncMock(side_effect=[mock_result_tool, mock_result_oauth])

        with (
            patch("src.services.agents.security.decrypt_value", return_value="decrypted_token"),
            patch("github.Github") as MockGithub,
            patch.object(resolver, "_get_user_token", return_value=None),
        ):
            client = await resolver.get_github_client("test_tool")

            assert client is not None
            MockGithub.assert_called_once_with("decrypted_token")

    @pytest.mark.asyncio
    async def test_get_github_client_no_tool(self, resolver, mock_db_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        client = await resolver.get_github_client("test_tool")
        assert client is None

    @pytest.mark.asyncio
    async def test_get_github_context(self, resolver, mock_db_session):
        # Mock AgentTool and OAuthApp
        mock_tool = MagicMock()
        mock_tool.oauth_app_id = uuid.uuid4()

        mock_oauth_app = MagicMock()
        mock_oauth_app.config = {"organization": "test-org", "default_branch": "develop"}

        # Mock DB queries using execute
        mock_result_tool = MagicMock()
        mock_result_tool.scalar_one_or_none.return_value = mock_tool

        mock_result_oauth = MagicMock()
        mock_result_oauth.scalar_one_or_none.return_value = mock_oauth_app

        mock_db_session.execute = AsyncMock(side_effect=[mock_result_tool, mock_result_oauth])

        # Mock client and user
        mock_user = MagicMock()
        mock_user.login = "test-user"
        mock_client = MagicMock()
        mock_client.get_user.return_value = mock_user

        with patch.object(resolver, "get_github_client", return_value=mock_client):
            context = await resolver.get_github_context("test_tool")

            assert context["organization"] == "test-org"
            assert context["default_branch"] == "develop"
            assert context["username"] == "test-user"

    @pytest.mark.asyncio
    async def test_get_gmail_service(self, resolver, mock_db_session):
        import json

        # Mock AgentTool with oauth_app_id
        mock_agent_tool = MagicMock()
        mock_agent_tool.oauth_app_id = uuid.uuid4()
        mock_agent_tool.enabled = True

        # Mock OAuthApp with Gmail provider and credentials
        mock_oauth_app = MagicMock()
        mock_oauth_app.id = mock_agent_tool.oauth_app_id
        mock_oauth_app.provider = "gmail"
        mock_oauth_app.is_active = True
        mock_oauth_app.app_name = "Test Gmail App"
        mock_oauth_app.client_id = "test_client_id"
        mock_oauth_app.client_secret = "encrypted_secret"
        mock_oauth_app.access_token = "encrypted_creds_json"

        # Setup mock DB queries using execute
        mock_result_tool = MagicMock()
        mock_result_tool.scalar_one_or_none.return_value = mock_agent_tool

        mock_result_oauth = MagicMock()
        mock_result_oauth.scalar_one_or_none.return_value = mock_oauth_app

        mock_db_session.execute = AsyncMock(side_effect=[mock_result_tool, mock_result_oauth])

        # Gmail credentials JSON that decrypt_value will return
        gmail_creds = json.dumps(
            {
                "access_token": "ya29.test_token",
                "refresh_token": "refresh_test",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "test_client_id",
                "client_secret": "test_secret",
            }
        )

        # Mock _get_user_token_record to return None (use app token)
        with (
            patch.object(resolver, "_get_user_token_record", return_value=None),
            patch("src.services.agents.security.decrypt_value", return_value=gmail_creds),
            patch("googleapiclient.discovery.build") as mock_build,
        ):
            mock_build.return_value = MagicMock()

            service = await resolver.get_gmail_service("test_tool")

            assert service is not None
            mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_youtube_service(self, resolver, mock_db_session):
        mock_tool = MagicMock()
        mock_tool.config = {"YOUTUBE_API_KEY": "encrypted_key"}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with (
            patch("src.services.agents.security.decrypt_value", return_value="api_key"),
            patch("googleapiclient.discovery.build") as mock_build,
        ):
            service = await resolver.get_youtube_service("test_tool")

            assert service is not None
            mock_build.assert_called_with("youtube", "v3", developerKey="api_key")

    @pytest.mark.asyncio
    async def test_get_serpapi_key(self, resolver, mock_db_session):
        mock_tool = MagicMock()
        mock_tool.config = {"SERPAPI_KEY": "encrypted_key"}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tool
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.services.agents.security.decrypt_value", return_value="real_key"):
            key = await resolver.get_serpapi_key("test_tool")
            assert key == "real_key"

    @pytest.mark.asyncio
    async def test_resolve_for_tool(self, resolver):
        with patch.object(resolver, "get_github_client", return_value="github_client") as mock_get_github:
            result = await resolver.resolve_for_tool("tool", "github")
            assert result == "github_client"
            mock_get_github.assert_called_with("tool")

    @pytest.mark.asyncio
    async def test_resolve_for_tool_unknown(self, resolver):
        result = await resolver.resolve_for_tool("tool", "unknown_type")
        assert result is None
