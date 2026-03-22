"""
Tutorial Generator Tools Registry

Registers all tutorial generation-related tools with the ADK tool registry.
This modular approach keeps tool registration organized and maintainable.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_tutorial_tools(registry):
    """
    Register all tutorial generation tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.tutorial_generator import (
        internal_analyze_relationships,
        internal_combine_tutorial,
        internal_fetch_repository_files,
        internal_generate_tutorial_chapter,
        internal_identify_abstractions,
        internal_order_chapters,
    )

    # Tutorial generator tools - wrapper to inject runtime_context
    async def internal_fetch_repository_files_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_fetch_repository_files(
            repo_path=kwargs.get("repo_path"),
            include_patterns=kwargs.get("include_patterns"),
            exclude_patterns=kwargs.get("exclude_patterns"),
            max_file_size=kwargs.get("max_file_size", 1048576),
            config=config,
            runtime_context=runtime_context,
        )

    async def internal_identify_abstractions_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_identify_abstractions(
            files_data=kwargs.get("files_data"),
            project_name=kwargs.get("project_name"),
            max_abstractions=kwargs.get("max_abstractions", 10),
            language=kwargs.get("language", "english"),
            config=config,
            runtime_context=runtime_context,
        )

    async def internal_analyze_relationships_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_analyze_relationships(
            abstractions=kwargs.get("abstractions"),
            files_data=kwargs.get("files_data"),
            project_name=kwargs.get("project_name"),
            language=kwargs.get("language", "english"),
            config=config,
            runtime_context=runtime_context,
        )

    async def internal_order_chapters_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_order_chapters(
            abstractions=kwargs.get("abstractions"),
            relationships=kwargs.get("relationships"),
            project_name=kwargs.get("project_name"),
            language=kwargs.get("language", "english"),
            config=config,
            runtime_context=runtime_context,
        )

    async def internal_generate_tutorial_chapter_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_generate_tutorial_chapter(
            chapter_number=kwargs.get("chapter_number"),
            abstraction=kwargs.get("abstraction"),
            files_data=kwargs.get("files_data"),
            project_name=kwargs.get("project_name"),
            previous_chapters_summary=kwargs.get("previous_chapters_summary", ""),
            full_chapter_listing=kwargs.get("full_chapter_listing", ""),
            language=kwargs.get("language", "english"),
            config=config,
            runtime_context=runtime_context,
        )

    async def internal_combine_tutorial_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_combine_tutorial(
            chapters=kwargs.get("chapters"),
            abstractions=kwargs.get("abstractions"),
            chapter_order=kwargs.get("chapter_order"),
            relationships=kwargs.get("relationships"),
            project_name=kwargs.get("project_name"),
            repository_url=kwargs.get("repository_url"),
            output_path=kwargs.get("output_path"),
            config=config,
            runtime_context=runtime_context,
        )

    registry.register_tool(
        name="internal_fetch_repository_files",
        description="Fetch and filter repository files for tutorial generation. Scans the repository and returns a list of (path, content) tuples. This is step 1 of the tutorial generation workflow.",
        parameters={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the cloned repository"},
                "include_patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File patterns to include (e.g., ['*.py', '*.js']). Default: common code files",
                },
                "exclude_patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Patterns to exclude (e.g., ['node_modules/*']). Default: common exclusions",
                },
                "max_file_size": {
                    "type": "integer",
                    "description": "Maximum file size in bytes (default: 1048576 = 1MB)",
                },
            },
            "required": ["repo_path"],
        },
        function=internal_fetch_repository_files_wrapper,
    )

    registry.register_tool(
        name="internal_identify_abstractions",
        description="Identify 5-10 core abstractions/concepts in the codebase using LLM analysis. This is step 2 of the tutorial generation workflow. Takes the files_data from step 1.",
        parameters={
            "type": "object",
            "properties": {
                "files_data": {
                    "type": "array",
                    "description": "List of (path, content) tuples from internal_fetch_repository_files",
                },
                "project_name": {"type": "string", "description": "Name of the project"},
                "max_abstractions": {
                    "type": "integer",
                    "description": "Maximum number of abstractions to identify (default: 10)",
                },
                "language": {"type": "string", "description": "Language for documentation (default: 'english')"},
            },
            "required": ["files_data", "project_name"],
        },
        function=internal_identify_abstractions_wrapper,
    )

    registry.register_tool(
        name="internal_analyze_relationships",
        description="Analyze relationships between identified abstractions using LLM. Generates project summary and relationship diagram data. This is step 3 of the tutorial generation workflow.",
        parameters={
            "type": "object",
            "properties": {
                "abstractions": {
                    "type": "array",
                    "description": "List of abstractions from internal_identify_abstractions",
                },
                "files_data": {"type": "array", "description": "Original files data from step 1"},
                "project_name": {"type": "string", "description": "Name of the project"},
                "language": {"type": "string", "description": "Language for documentation (default: 'english')"},
            },
            "required": ["abstractions", "files_data", "project_name"],
        },
        function=internal_analyze_relationships_wrapper,
    )

    registry.register_tool(
        name="internal_order_chapters",
        description="Determine optimal chapter ordering for tutorial from foundational to advanced concepts. This is step 4 of the tutorial generation workflow.",
        parameters={
            "type": "object",
            "properties": {
                "abstractions": {"type": "array", "description": "List of identified abstractions"},
                "relationships": {
                    "type": "object",
                    "description": "Relationships data from internal_analyze_relationships",
                },
                "project_name": {"type": "string", "description": "Name of the project"},
                "language": {"type": "string", "description": "Language for documentation (default: 'english')"},
            },
            "required": ["abstractions", "relationships", "project_name"],
        },
        function=internal_order_chapters_wrapper,
    )

    registry.register_tool(
        name="internal_generate_tutorial_chapter",
        description="Generate a single beginner-friendly tutorial chapter using LLM. This is step 5 (called multiple times for each chapter). Creates markdown content with code examples, diagrams, and explanations.",
        parameters={
            "type": "object",
            "properties": {
                "chapter_number": {"type": "integer", "description": "Chapter number (1-indexed)"},
                "abstraction": {"type": "object", "description": "Abstraction details (name, description, files)"},
                "files_data": {"type": "array", "description": "Original files data"},
                "project_name": {"type": "string", "description": "Name of the project"},
                "previous_chapters_summary": {
                    "type": "string",
                    "description": "Summary of previous chapters for context (optional)",
                },
                "full_chapter_listing": {
                    "type": "string",
                    "description": "Complete chapter structure for linking (optional)",
                },
                "language": {"type": "string", "description": "Language for documentation (default: 'english')"},
            },
            "required": ["chapter_number", "abstraction", "files_data", "project_name"],
        },
        function=internal_generate_tutorial_chapter_wrapper,
    )

    registry.register_tool(
        name="internal_combine_tutorial",
        description="Combine tutorial chapters into final output with index and mermaid diagram. This is the final step (step 6). Creates index.md and individual chapter files in a temporary directory. Returns the output_path which can then be uploaded to S3 using internal_s3_upload_directory.",
        parameters={
            "type": "object",
            "properties": {
                "chapters": {"type": "array", "description": "List of generated chapter markdown content"},
                "abstractions": {"type": "array", "description": "List of all abstractions"},
                "chapter_order": {"type": "array", "description": "Ordered list of chapter indices"},
                "relationships": {"type": "object", "description": "Relationships data with summary"},
                "project_name": {"type": "string", "description": "Name of the project"},
                "repository_url": {"type": "string", "description": "URL of the source repository (optional)"},
                "output_path": {
                    "type": "string",
                    "description": "Path to write tutorial files (optional, creates temp directory if not provided)",
                },
            },
            "required": ["chapters", "abstractions", "chapter_order", "relationships", "project_name"],
        },
        function=internal_combine_tutorial_wrapper,
    )

    logger.info("Registered 6 tutorial generation tools")
