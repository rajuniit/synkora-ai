"""
Tests for pr_review_tools.py - PR Review Tools

Tests the PR review functionality including getting PR details,
diff, posting reviews, and security analysis.
"""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestInternalGetPrDetails:
    """Tests for internal_get_pr_details function."""

    @pytest.mark.asyncio
    async def test_gets_pr_details_successfully(self):
        from src.services.agents.internal_tools.pr_review_tools import internal_get_pr_details

        mock_pr_data = {
            "number": 123,
            "title": "Test PR",
            "body": "Description",
            "state": "open",
            "user": {"login": "testuser"},
            "base": {"ref": "main"},
            "head": {"ref": "feature-branch"},
            "merged": False,
            "mergeable": True,
            "html_url": "https://github.com/testowner/testrepo/pull/123",
            "labels": [{"name": "bug"}],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
        }
        mock_files_data = [
            {
                "filename": "test.py",
                "status": "modified",
                "additions": 10,
                "deletions": 5,
                "changes": 15,
                "patch": "+new line",
                "blob_url": "https://github.com/blob/test.py",
            }
        ]
        mock_commits_data = [
            {
                "sha": "abc123",
                "commit": {
                    "message": "Test commit",
                    "author": {"name": "Test User", "date": "2024-01-01T00:00:00Z"},
                },
            }
        ]
        mock_reviews_data = [
            {
                "id": 1,
                "user": {"login": "reviewer"},
                "state": "APPROVED",
                "submitted_at": "2024-01-02T00:00:00Z",
                "body": "LGTM",
            }
        ]

        with (
            patch(
                "src.services.agents.internal_tools.github_auth_helper.get_github_token_from_context",
                new_callable=AsyncMock,
                return_value="test-token",
            ),
            patch(
                "src.services.agents.internal_tools.pr_review_tools._make_github_request",
                new_callable=AsyncMock,
            ) as mock_request,
        ):
            mock_request.side_effect = [
                mock_pr_data,
                mock_files_data,
                mock_commits_data,
                mock_reviews_data,
            ]

            result = await internal_get_pr_details(
                owner="testowner",
                repo="testrepo",
                pr_number=123,
                config={},
                runtime_context=MagicMock(),
            )

            assert result["success"] is True
            assert result["pr"]["number"] == 123
            assert result["pr"]["title"] == "Test PR"
            assert len(result["files"]) == 1
            assert mock_request.call_count == 4

    @pytest.mark.asyncio
    async def test_returns_error_on_token_failure(self):
        from src.services.agents.internal_tools.pr_review_tools import internal_get_pr_details

        with patch(
            "src.services.agents.internal_tools.github_auth_helper.get_github_token_from_context",
            new_callable=AsyncMock,
            side_effect=ValueError("No GitHub token available"),
        ):
            result = await internal_get_pr_details(
                owner="testowner",
                repo="testrepo",
                pr_number=123,
                config={},
                runtime_context=MagicMock(),
            )

            assert result["success"] is False
            assert "error" in result


class TestInternalGetPrDiff:
    """Tests for internal_get_pr_diff function."""

    @pytest.mark.asyncio
    async def test_gets_pr_diff_successfully(self):
        from src.services.agents.internal_tools.pr_review_tools import internal_get_pr_diff

        mock_diff = """diff --git a/test.py b/test.py
index 1234567..abcdefg 100644
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
+# New line
 def test():
     pass
"""

        with (
            patch(
                "src.services.agents.internal_tools.github_auth_helper.get_github_token_from_context",
                new_callable=AsyncMock,
                return_value="test-token",
            ),
            patch("httpx.AsyncClient") as mock_client,
        ):
            mock_response = MagicMock()
            mock_response.text = mock_diff
            mock_response.raise_for_status = MagicMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance

            result = await internal_get_pr_diff(
                owner="testowner",
                repo="testrepo",
                pr_number=123,
                config={},
                runtime_context=MagicMock(),
            )

            assert result["success"] is True
            assert result["diff"] == mock_diff


class TestInternalPostPrReview:
    """Tests for internal_post_pr_review function."""

    @pytest.mark.asyncio
    async def test_posts_comment_review_successfully(self):
        from src.services.agents.internal_tools.pr_review_tools import internal_post_pr_review

        mock_response = {
            "id": 12345,
            "state": "COMMENTED",
            "html_url": "https://github.com/testowner/testrepo/pull/123#pullrequestreview-12345",
            "submitted_at": "2024-01-02T00:00:00Z",
        }

        with (
            patch(
                "src.services.agents.internal_tools.github_auth_helper.get_github_token_from_context",
                new_callable=AsyncMock,
                return_value="test-token",
            ),
            patch(
                "src.services.agents.internal_tools.pr_review_tools._make_github_request",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
        ):
            result = await internal_post_pr_review(
                owner="testowner",
                repo="testrepo",
                pr_number=123,
                review_body="Test review comment",
                review_event="COMMENT",
                review_comments=None,
                config={},
                runtime_context=MagicMock(),
            )

            assert result["success"] is True
            assert result["review_id"] == 12345
            assert result["state"] == "COMMENTED"

    @pytest.mark.asyncio
    async def test_posts_approve_review_successfully(self):
        from src.services.agents.internal_tools.pr_review_tools import internal_post_pr_review

        mock_response = {
            "id": 12346,
            "state": "APPROVED",
            "html_url": "https://github.com/testowner/testrepo/pull/123#pullrequestreview-12346",
            "submitted_at": "2024-01-02T00:00:00Z",
        }

        with (
            patch(
                "src.services.agents.internal_tools.github_auth_helper.get_github_token_from_context",
                new_callable=AsyncMock,
                return_value="test-token",
            ),
            patch(
                "src.services.agents.internal_tools.pr_review_tools._make_github_request",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
        ):
            result = await internal_post_pr_review(
                owner="testowner",
                repo="testrepo",
                pr_number=123,
                review_body="LGTM!",
                review_event="APPROVE",
                review_comments=None,
                config={},
                runtime_context=MagicMock(),
            )

            assert result["success"] is True
            assert result["state"] == "APPROVED"

    @pytest.mark.asyncio
    async def test_posts_request_changes_review_successfully(self):
        from src.services.agents.internal_tools.pr_review_tools import internal_post_pr_review

        mock_response = {
            "id": 12347,
            "state": "CHANGES_REQUESTED",
            "html_url": "https://github.com/testowner/testrepo/pull/123#pullrequestreview-12347",
            "submitted_at": "2024-01-02T00:00:00Z",
        }

        with (
            patch(
                "src.services.agents.internal_tools.github_auth_helper.get_github_token_from_context",
                new_callable=AsyncMock,
                return_value="test-token",
            ),
            patch(
                "src.services.agents.internal_tools.pr_review_tools._make_github_request",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
        ):
            result = await internal_post_pr_review(
                owner="testowner",
                repo="testrepo",
                pr_number=123,
                review_body="Please fix these issues",
                review_event="REQUEST_CHANGES",
                review_comments=None,
                config={},
                runtime_context=MagicMock(),
            )

            assert result["success"] is True
            assert result["state"] == "CHANGES_REQUESTED"

    @pytest.mark.asyncio
    async def test_rejects_invalid_review_event(self):
        from src.services.agents.internal_tools.pr_review_tools import internal_post_pr_review

        with patch(
            "src.services.agents.internal_tools.github_auth_helper.get_github_token_from_context",
            new_callable=AsyncMock,
            return_value="test-token",
        ):
            result = await internal_post_pr_review(
                owner="testowner",
                repo="testrepo",
                pr_number=123,
                review_body="Test",
                review_event="INVALID_EVENT",
                review_comments=None,
                config={},
                runtime_context=MagicMock(),
            )

            assert result["success"] is False
            assert "error" in result


class TestInternalAnalyzePrSecurity:
    """Tests for internal_analyze_pr_security function."""

    @pytest.mark.asyncio
    async def test_detects_sql_injection(self):
        from src.services.agents.internal_tools.pr_review_tools import internal_analyze_pr_security

        mock_pr_details = {
            "success": True,
            "files": [
                {
                    "filename": "app.py",
                    "patch": '+query = "SELECT * FROM users WHERE id = " + user_id\n+cursor.execute(query)',
                }
            ],
        }

        with patch(
            "src.services.agents.internal_tools.pr_review_tools.internal_get_pr_details",
            new_callable=AsyncMock,
            return_value=mock_pr_details,
        ):
            result = await internal_analyze_pr_security(
                owner="testowner",
                repo="testrepo",
                pr_number=123,
                config={},
                runtime_context=MagicMock(),
            )

            assert result["success"] is True
            assert "findings" in result
            sql_findings = [f for f in result["findings"] if f["category"] == "sql_injection"]
            assert len(sql_findings) > 0

    @pytest.mark.asyncio
    async def test_detects_xss(self):
        from src.services.agents.internal_tools.pr_review_tools import internal_analyze_pr_security

        mock_pr_details = {
            "success": True,
            "files": [
                {
                    "filename": "component.js",
                    "patch": "+element.innerHTML = userInput;\n+<div dangerouslySetInnerHTML={{__html: data}} />",
                }
            ],
        }

        with patch(
            "src.services.agents.internal_tools.pr_review_tools.internal_get_pr_details",
            new_callable=AsyncMock,
            return_value=mock_pr_details,
        ):
            result = await internal_analyze_pr_security(
                owner="testowner",
                repo="testrepo",
                pr_number=123,
                config={},
                runtime_context=MagicMock(),
            )

            assert result["success"] is True
            xss_findings = [f for f in result["findings"] if f["category"] == "xss"]
            assert len(xss_findings) > 0

    @pytest.mark.asyncio
    async def test_detects_hardcoded_secrets(self):
        from src.services.agents.internal_tools.pr_review_tools import internal_analyze_pr_security

        mock_pr_details = {
            "success": True,
            "files": [
                {
                    "filename": "config.py",
                    "patch": '+password = "supersecret123"\n+api_key = "sk-12345"',
                }
            ],
        }

        with patch(
            "src.services.agents.internal_tools.pr_review_tools.internal_get_pr_details",
            new_callable=AsyncMock,
            return_value=mock_pr_details,
        ):
            result = await internal_analyze_pr_security(
                owner="testowner",
                repo="testrepo",
                pr_number=123,
                config={},
                runtime_context=MagicMock(),
            )

            assert result["success"] is True
            secret_findings = [f for f in result["findings"] if f["category"] == "secrets"]
            assert len(secret_findings) > 0

    @pytest.mark.asyncio
    async def test_detects_command_injection(self):
        from src.services.agents.internal_tools.pr_review_tools import internal_analyze_pr_security

        mock_pr_details = {
            "success": True,
            "files": [
                {
                    "filename": "utils.py",
                    "patch": "+os.system(user_input)\n+eval(code)",
                }
            ],
        }

        with patch(
            "src.services.agents.internal_tools.pr_review_tools.internal_get_pr_details",
            new_callable=AsyncMock,
            return_value=mock_pr_details,
        ):
            result = await internal_analyze_pr_security(
                owner="testowner",
                repo="testrepo",
                pr_number=123,
                config={},
                runtime_context=MagicMock(),
            )

            assert result["success"] is True
            cmd_findings = [f for f in result["findings"] if f["category"] == "command_injection"]
            assert len(cmd_findings) > 0

    @pytest.mark.asyncio
    async def test_detects_deserialization(self):
        from src.services.agents.internal_tools.pr_review_tools import internal_analyze_pr_security

        mock_pr_details = {
            "success": True,
            "files": [
                {
                    "filename": "data.py",
                    "patch": "+pickle.loads(data)\n+yaml.load(content)",
                }
            ],
        }

        with patch(
            "src.services.agents.internal_tools.pr_review_tools.internal_get_pr_details",
            new_callable=AsyncMock,
            return_value=mock_pr_details,
        ):
            result = await internal_analyze_pr_security(
                owner="testowner",
                repo="testrepo",
                pr_number=123,
                config={},
                runtime_context=MagicMock(),
            )

            assert result["success"] is True
            deser_findings = [f for f in result["findings"] if f["category"] == "deserialization"]
            assert len(deser_findings) > 0

    @pytest.mark.asyncio
    async def test_returns_empty_for_clean_code(self):
        from src.services.agents.internal_tools.pr_review_tools import internal_analyze_pr_security

        mock_pr_details = {
            "success": True,
            "files": [
                {
                    "filename": "safe.py",
                    "patch": "+def add(a, b):\n+    return a + b",
                }
            ],
        }

        with patch(
            "src.services.agents.internal_tools.pr_review_tools.internal_get_pr_details",
            new_callable=AsyncMock,
            return_value=mock_pr_details,
        ):
            result = await internal_analyze_pr_security(
                owner="testowner",
                repo="testrepo",
                pr_number=123,
                config={},
                runtime_context=MagicMock(),
            )

            assert result["success"] is True
            assert len(result["findings"]) == 0
            assert result["summary"]["risk_score"] == 0

    @pytest.mark.asyncio
    async def test_risk_score_capped_at_100(self):
        from src.services.agents.internal_tools.pr_review_tools import internal_analyze_pr_security

        mock_pr_details = {
            "success": True,
            "files": [
                {
                    "filename": "vulnerable.py",
                    "patch": (
                        '+query = "SELECT * FROM users WHERE id = " + id\n'
                        "+cursor.execute(query)\n"
                        "+os.system(cmd)\n"
                        "+eval(code)\n"
                        "+exec(data)\n"
                        '+password = "secret"\n'
                        '+api_key = "key123"\n'
                        '+secret = "mysecret"\n'
                        '+token = "tok123"\n'
                        "+pickle.loads(data)\n"
                        "+element.innerHTML = x\n"
                    ),
                }
            ],
        }

        with patch(
            "src.services.agents.internal_tools.pr_review_tools.internal_get_pr_details",
            new_callable=AsyncMock,
            return_value=mock_pr_details,
        ):
            result = await internal_analyze_pr_security(
                owner="testowner",
                repo="testrepo",
                pr_number=123,
                config={},
                runtime_context=MagicMock(),
            )

            assert result["success"] is True
            assert result["summary"]["risk_score"] <= 100


class TestInternalGetFileContent:
    """Tests for internal_get_file_content function."""

    @pytest.mark.asyncio
    async def test_gets_file_content_successfully(self):
        from src.services.agents.internal_tools.pr_review_tools import internal_get_file_content

        file_content = "def hello():\n    print('Hello, World!')"
        encoded_content = base64.b64encode(file_content.encode()).decode()

        mock_response = {
            "name": "test.py",
            "path": "src/test.py",
            "sha": "abc123",
            "size": len(file_content),
            "encoding": "base64",
            "content": encoded_content,
            "html_url": "https://github.com/testowner/testrepo/blob/main/src/test.py",
        }

        with (
            patch(
                "src.services.agents.internal_tools.github_auth_helper.get_github_token_from_context",
                new_callable=AsyncMock,
                return_value="test-token",
            ),
            patch(
                "src.services.agents.internal_tools.pr_review_tools._make_github_request",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
        ):
            result = await internal_get_file_content(
                owner="testowner",
                repo="testrepo",
                path="src/test.py",
                ref="main",
                config={},
                runtime_context=MagicMock(),
            )

            assert result["success"] is True
            assert result["content"] == file_content
            assert result["path"] == "src/test.py"

    @pytest.mark.asyncio
    async def test_returns_error_on_token_failure(self):
        from src.services.agents.internal_tools.pr_review_tools import internal_get_file_content

        with patch(
            "src.services.agents.internal_tools.github_auth_helper.get_github_token_from_context",
            new_callable=AsyncMock,
            side_effect=ValueError("No GitHub token available"),
        ):
            result = await internal_get_file_content(
                owner="testowner",
                repo="testrepo",
                path="src/test.py",
                ref="main",
                config={},
                runtime_context=MagicMock(),
            )

            assert result["success"] is False
            assert "error" in result
