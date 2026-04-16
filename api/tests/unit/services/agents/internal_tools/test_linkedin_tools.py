"""
Tests for linkedin_tools.py - LinkedIn Tools

Tests the LinkedIn API integration for profile, posting, sharing,
and company information.
"""

from unittest.mock import AsyncMock, patch

import pytest


class TestInternalLinkedInGetProfile:
    """Tests for internal_linkedin_get_profile function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.linkedin_tools import internal_linkedin_get_profile

        result = await internal_linkedin_get_profile(runtime_context=None)

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_gets_profile_successfully(self):
        from src.services.agents.internal_tools.linkedin_tools import internal_linkedin_get_profile

        mock_credentials = {"access_token": "test-token"}
        mock_response_data = {
            "sub": "user-123",
            "name": "John Doe",
            "given_name": "John",
            "family_name": "Doe",
            "picture": "https://example.com/photo.jpg",
            "email": "john@example.com",
            "email_verified": True,
            "locale": "en_US",
        }

        with (
            patch(
                "src.services.agents.internal_tools.linkedin_tools._get_linkedin_credentials",
                new_callable=AsyncMock,
                return_value=mock_credentials,
            ),
            patch(
                "src.services.agents.internal_tools.linkedin_tools._make_linkedin_request",
                new_callable=AsyncMock,
                return_value=mock_response_data,
            ),
        ):
            result = await internal_linkedin_get_profile(runtime_context={"agent_id": "test"})

            assert result["success"] is True
            assert result["profile"]["id"] == "user-123"
            assert result["profile"]["name"] == "John Doe"


class TestInternalLinkedInPostText:
    """Tests for internal_linkedin_post_text function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.linkedin_tools import internal_linkedin_post_text

        result = await internal_linkedin_post_text(
            text="Hello LinkedIn!",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_text(self):
        from src.services.agents.internal_tools.linkedin_tools import internal_linkedin_post_text

        result = await internal_linkedin_post_text(
            text="",
            runtime_context={"agent_id": "test"},
        )

        assert result["success"] is False
        assert "Post text is required" in result["error"]

    @pytest.mark.asyncio
    async def test_validates_character_limit(self):
        from src.services.agents.internal_tools.linkedin_tools import internal_linkedin_post_text

        long_text = "x" * 3001

        result = await internal_linkedin_post_text(
            text=long_text,
            runtime_context={"agent_id": "test"},
        )

        assert result["success"] is False
        assert "3000 characters" in result["error"]

    @pytest.mark.asyncio
    async def test_posts_text_successfully(self):
        from src.services.agents.internal_tools.linkedin_tools import internal_linkedin_post_text

        mock_credentials = {"access_token": "test-token"}
        mock_profile_response = {
            "sub": "user-123",
            "name": "John Doe",
        }
        mock_post_response = {
            "success": True,
            "id": "post-456",
        }

        with (
            patch(
                "src.services.agents.internal_tools.linkedin_tools._get_linkedin_credentials",
                new_callable=AsyncMock,
                return_value=mock_credentials,
            ),
            patch(
                "src.services.agents.internal_tools.linkedin_tools._make_linkedin_request",
                new_callable=AsyncMock,
                side_effect=[mock_profile_response, mock_post_response],
            ),
        ):
            result = await internal_linkedin_post_text(
                text="Hello LinkedIn!",
                visibility="PUBLIC",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["post"]["id"] == "post-456"


class TestInternalLinkedInShareUrl:
    """Tests for internal_linkedin_share_url function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.linkedin_tools import internal_linkedin_share_url

        result = await internal_linkedin_share_url(
            url="https://example.com",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_url(self):
        from src.services.agents.internal_tools.linkedin_tools import internal_linkedin_share_url

        result = await internal_linkedin_share_url(
            url="",
            runtime_context={"agent_id": "test"},
        )

        assert result["success"] is False
        assert "URL is required" in result["error"]

    @pytest.mark.asyncio
    async def test_shares_url_successfully(self):
        from src.services.agents.internal_tools.linkedin_tools import internal_linkedin_share_url

        mock_credentials = {"access_token": "test-token"}
        mock_profile_response = {
            "sub": "user-123",
            "name": "John Doe",
        }
        mock_share_response = {
            "success": True,
            "id": "share-789",
        }

        with (
            patch(
                "src.services.agents.internal_tools.linkedin_tools._get_linkedin_credentials",
                new_callable=AsyncMock,
                return_value=mock_credentials,
            ),
            patch(
                "src.services.agents.internal_tools.linkedin_tools._make_linkedin_request",
                new_callable=AsyncMock,
                side_effect=[mock_profile_response, mock_share_response],
            ),
        ):
            result = await internal_linkedin_share_url(
                url="https://example.com/article",
                text="Check out this article!",
                title="Great Article",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["share"]["id"] == "share-789"


class TestInternalLinkedInGetCompanyInfo:
    """Tests for internal_linkedin_get_company_info function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.linkedin_tools import internal_linkedin_get_company_info

        result = await internal_linkedin_get_company_info(
            company_id="12345",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_company_id(self):
        from src.services.agents.internal_tools.linkedin_tools import internal_linkedin_get_company_info

        result = await internal_linkedin_get_company_info(
            company_id="",
            runtime_context={"agent_id": "test"},
        )

        assert result["success"] is False
        assert "Company ID is required" in result["error"]

    @pytest.mark.asyncio
    async def test_gets_company_info_successfully(self):
        from src.services.agents.internal_tools.linkedin_tools import internal_linkedin_get_company_info

        mock_credentials = {"access_token": "test-token"}
        mock_response = {
            "id": "12345",
            "localizedName": "Acme Corp",
            "localizedDescription": "We make great products",
            "websiteUrl": "https://acme.com",
        }

        with (
            patch(
                "src.services.agents.internal_tools.linkedin_tools._get_linkedin_credentials",
                new_callable=AsyncMock,
                return_value=mock_credentials,
            ),
            patch(
                "src.services.agents.internal_tools.linkedin_tools._make_linkedin_request",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
        ):
            result = await internal_linkedin_get_company_info(
                company_id="12345",
                runtime_context={"agent_id": "test"},
            )

            assert result["success"] is True
            assert result["company"]["name"] == "Acme Corp"


class TestInternalLinkedInGetPosts:
    """Tests for internal_linkedin_get_posts function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.linkedin_tools import internal_linkedin_get_posts

        result = await internal_linkedin_get_posts(runtime_context=None)

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]


class TestInternalLinkedInPostWithImage:
    """Tests for internal_linkedin_post_with_image function."""

    @pytest.mark.asyncio
    async def test_requires_runtime_context(self):
        from src.services.agents.internal_tools.linkedin_tools import internal_linkedin_post_with_image

        result = await internal_linkedin_post_with_image(
            text="Check out this image!",
            image_url="https://example.com/image.jpg",
            runtime_context=None,
        )

        assert result["success"] is False
        assert "Runtime context is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_text(self):
        from src.services.agents.internal_tools.linkedin_tools import internal_linkedin_post_with_image

        result = await internal_linkedin_post_with_image(
            text="",
            image_url="https://example.com/image.jpg",
            runtime_context={"agent_id": "test"},
        )

        assert result["success"] is False
        assert "Post text is required" in result["error"]

    @pytest.mark.asyncio
    async def test_requires_image_url(self):
        from src.services.agents.internal_tools.linkedin_tools import internal_linkedin_post_with_image

        result = await internal_linkedin_post_with_image(
            text="Check out this image!",
            image_url="",
            runtime_context={"agent_id": "test"},
        )

        assert result["success"] is False
        assert "At least one image URL is required" in result["error"]
