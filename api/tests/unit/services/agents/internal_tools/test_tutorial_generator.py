from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from src.services.agents.internal_tools.tutorial_generator import (
    _create_file_hash,
    _detect_language,
    internal_analyze_relationships,
    internal_combine_tutorial,
    internal_fetch_repository_files,
    internal_generate_tutorial_chapter,
    internal_identify_abstractions,
    internal_order_chapters,
)


class TestTutorialGenerator:
    """Test tutorial generator with workspace path mocking."""

    MOCK_WORKSPACE = "/tmp/synkora/workspaces/tenant1/conv1"
    MOCK_REPO_PATH = "/tmp/synkora/workspaces/tenant1/conv1/repos/repo"

    @pytest.fixture
    def mock_runtime_context(self):
        context = MagicMock()
        context.llm_client = MagicMock()
        context.llm_client.generate_content = AsyncMock()
        return context

    def test_detect_language(self):
        assert _detect_language("test.py") == "python"
        assert _detect_language("test.js") == "javascript"
        assert _detect_language("test.unknown") is None

    def test_create_file_hash(self):
        assert _create_file_hash("content") == "ed7002b439e9ac845f22357d822bac1444730fbdb6016d3ec9432297b9ec9f73"

    @pytest.mark.asyncio
    async def test_fetch_repository_files(self):
        with (
            patch(
                "src.services.agents.internal_tools.tutorial_generator._get_workspace_path",
                return_value=self.MOCK_WORKSPACE,
            ),
            patch(
                "src.services.agents.internal_tools.tutorial_generator._validate_path_in_workspace",
                return_value=(True, None),
            ),
            patch("os.walk") as mock_walk,
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=100),
            patch("builtins.open", mock_open(read_data="content")),
        ):
            mock_walk.return_value = [(self.MOCK_REPO_PATH, [], ["file.py"])]

            result = await internal_fetch_repository_files(self.MOCK_REPO_PATH)

            assert result["success"] is True
            assert len(result["files"]) == 1
            assert result["files"][0][0] == "file.py"

    @pytest.mark.asyncio
    async def test_fetch_repository_files_not_found(self):
        with (
            patch(
                "src.services.agents.internal_tools.tutorial_generator._get_workspace_path",
                return_value=self.MOCK_WORKSPACE,
            ),
            patch(
                "src.services.agents.internal_tools.tutorial_generator._validate_path_in_workspace",
                return_value=(True, None),
            ),
            patch("os.path.exists", return_value=False),
        ):
            result = await internal_fetch_repository_files(self.MOCK_REPO_PATH)
            assert "error" in result

    @pytest.mark.asyncio
    async def test_identify_abstractions(self, mock_runtime_context):
        files_data = [("file.py", "content")]
        mock_response = """```yaml
- name: Abstraction1
  description: Desc
  file_indices: [0]
```"""
        mock_runtime_context.llm_client.generate_content.return_value = mock_response

        result = await internal_identify_abstractions(files_data, "Project", runtime_context=mock_runtime_context)

        assert result["success"] is True
        assert len(result["abstractions"]) == 1
        assert result["abstractions"][0]["name"] == "Abstraction1"

    @pytest.mark.asyncio
    async def test_identify_abstractions_no_client(self):
        result = await internal_identify_abstractions([], "Project", runtime_context=None)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_analyze_relationships(self, mock_runtime_context):
        abstractions = [{"name": "A1", "description": "D1", "files": [0]}]
        files_data = [("file.py", "content")]
        mock_response = """```yaml
summary: Summary
relationships:
  - from_abstraction: 0 # A1
    to_abstraction: 0 # A1
    label: self
```"""
        mock_runtime_context.llm_client.generate_content.return_value = mock_response

        result = await internal_analyze_relationships(
            abstractions, files_data, "Project", runtime_context=mock_runtime_context
        )

        assert result["success"] is True
        assert result["summary"] == "Summary"
        assert len(result["relationships"]) == 1

    @pytest.mark.asyncio
    async def test_order_chapters(self, mock_runtime_context):
        abstractions = [{"name": "A1", "description": "D1", "files": [0]}]
        relationships = {"summary": "Sum", "relationships": []}
        mock_response = """```yaml
- 0 # A1
```"""
        mock_runtime_context.llm_client.generate_content.return_value = mock_response

        result = await internal_order_chapters(
            abstractions, relationships, "Project", runtime_context=mock_runtime_context
        )

        assert result["success"] is True
        assert result["chapter_order"] == [0]

    @pytest.mark.asyncio
    async def test_generate_tutorial_chapter(self, mock_runtime_context):
        abstraction = {"name": "A1", "description": "D1", "files": [0]}
        files_data = [("file.py", "content")]
        mock_runtime_context.llm_client.generate_content.return_value = "# Chapter 1: A1\nContent"

        result = await internal_generate_tutorial_chapter(
            1, abstraction, files_data, "Project", runtime_context=mock_runtime_context
        )

        assert result["success"] is True
        assert "Chapter 1: A1" in result["chapter_content"]

    @pytest.mark.asyncio
    async def test_combine_tutorial(self):
        output_path = f"{self.MOCK_WORKSPACE}/tutorials/out"
        chapters = ["# Chapter 1\nContent"]
        abstractions = [{"name": "A1"}]
        chapter_order = [0]
        relationships = {"summary": "Summary", "relationships": [{"from": 0, "to": 0, "label": "self"}]}

        with (
            patch(
                "src.services.agents.internal_tools.tutorial_generator._get_workspace_path",
                return_value=self.MOCK_WORKSPACE,
            ),
            patch(
                "src.services.agents.internal_tools.tutorial_generator._validate_path_in_workspace",
                return_value=(True, None),
            ),
            patch("os.makedirs"),
            patch("builtins.open", mock_open()),
        ):
            result = await internal_combine_tutorial(
                chapters, abstractions, chapter_order, relationships, "Project", output_path=output_path
            )

            assert result["success"] is True
            assert len(result["chapter_files"]) == 1
            assert "mermaid" in result["index_content"]
