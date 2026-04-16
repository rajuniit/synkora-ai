"""
Tutorial Generation Tools for Synkora Agents.

Based on the pocketflow workflow for generating beginner-friendly tutorials
from codebases. Implements: Fetch → Identify Abstractions → Analyze Relationships
→ Order Chapters → Write Chapters → Combine Tutorial.
"""

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def _get_workspace_path(config: dict[str, Any] | None) -> str | None:
    """Get the workspace path from config or RuntimeContext (including Celery task fallback)."""
    from src.services.agents.workspace_manager import get_workspace_path_from_config

    return get_workspace_path_from_config(config)


def _validate_path_in_workspace(path: str, workspace_path: str | None) -> tuple[bool, str | None]:
    """Validate that a path is within the workspace directory."""
    if not workspace_path:
        return False, "No workspace path configured. File operations require a valid workspace."

    try:
        real_path = os.path.realpath(path)
        real_workspace = os.path.realpath(workspace_path)
        real_path = real_path.removeprefix("/private")
        real_workspace = real_workspace.removeprefix("/private")

        if not (real_path.startswith(real_workspace + os.sep) or real_path == real_workspace):
            return False, f"Path '{path}' is outside the workspace directory"

        return True, None
    except Exception as e:
        return False, f"Error validating path: {str(e)}"


# Language extensions mapping
LANGUAGE_EXTENSIONS = {
    "python": [".py", ".pyx", ".pyi"],
    "javascript": [".js", ".jsx", ".mjs"],
    "typescript": [".ts", ".tsx"],
    "java": [".java"],
    "go": [".go"],
    "rust": [".rs"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".hpp", ".cc", ".cxx", ".hxx"],
    "csharp": [".cs"],
    "ruby": [".rb"],
    "php": [".php"],
    "swift": [".swift"],
    "kotlin": [".kt", ".kts"],
}

# Default patterns
DEFAULT_INCLUDE_PATTERNS = ["*.py", "*.js", "*.ts", "*.java", "*.go", "*.rs", "*.md"]
DEFAULT_EXCLUDE_PATTERNS = [
    "node_modules/*",
    "venv/*",
    ".venv/*",
    "__pycache__/*",
    ".git/*",
    "dist/*",
    "build/*",
    "*.min.js",
    "*.bundle.js",
]


def _detect_language(file_path: str) -> str | None:
    """Detect programming language from file extension."""
    ext = Path(file_path).suffix.lower()
    for language, extensions in LANGUAGE_EXTENSIONS.items():
        if ext in extensions:
            return language
    return None


def _create_file_hash(content: str) -> str:
    """Create SHA-256 hash of file content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _get_content_for_indices(files_data: list[tuple[str, str]], indices: list[int]) -> dict[str, str]:
    """Helper to get content for specific file indices."""
    content_map = {}
    for i in indices:
        if 0 <= i < len(files_data):
            path, content = files_data[i]
            content_map[f"{i} # {path}"] = content
    return content_map


async def internal_fetch_repository_files(
    repo_path: str,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    max_file_size: int = 1048576,  # 1MB default
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Fetch and filter repository files for tutorial generation.

    This is the first step in the tutorial generation workflow.
    Scans the repository and returns a list of (path, content) tuples.
    IMPORTANT: repo_path must be within the workspace directory.

    Args:
        repo_path: Path to the cloned repository (must be within workspace)
        include_patterns: File patterns to include (e.g., ['*.py', '*.js'])
        exclude_patterns: Patterns to exclude (e.g., ['node_modules/*'])
        max_file_size: Maximum file size in bytes
        config: Configuration dictionary
        runtime_context: Runtime context

    Returns:
        Dictionary with files list and metadata
    """
    try:
        from fnmatch import fnmatch

        # Validate repo_path is within workspace
        workspace_path = _get_workspace_path(config)
        is_valid, error = _validate_path_in_workspace(repo_path, workspace_path)
        if not is_valid:
            return {"error": error}

        # Use defaults if not provided
        if include_patterns is None:
            include_patterns = DEFAULT_INCLUDE_PATTERNS
        if exclude_patterns is None:
            exclude_patterns = DEFAULT_EXCLUDE_PATTERNS

        from src.services.compute.resolver import get_compute_session_from_config

        _cs = await get_compute_session_from_config(config)

        files_list = []
        total_size = 0
        skipped_count = 0

        if _cs is not None and _cs.is_remote:
            # Remote: use find to enumerate files, then read each via compute session
            find_result = await _cs.exec_command(["find", repo_path, "-type", "f"])
            if not find_result.get("success"):
                return {"error": f"Repository path not found: {repo_path}"}
            all_files = [f for f in find_result["output"].splitlines() if f.strip()]
            for file_path in all_files:
                relative_path = os.path.relpath(file_path, repo_path)
                filename = os.path.basename(file_path)
                if any(fnmatch(relative_path, p) for p in exclude_patterns):
                    skipped_count += 1
                    continue
                if not any(fnmatch(filename, p) for p in include_patterns):
                    skipped_count += 1
                    continue
                try:
                    stat_r = await _cs.exec_command(["stat", "-c", "%s", file_path])
                    file_size = int(stat_r["output"].strip()) if stat_r.get("success") and stat_r.get("output") else 0
                    if file_size > max_file_size:
                        logger.warning(f"Skipping large file: {relative_path} ({file_size} bytes)")
                        skipped_count += 1
                        continue
                    read_r = await _cs.read_file(file_path, max_lines=50000)
                    if read_r.get("success"):
                        files_list.append((relative_path, read_r.get("content", "")))
                        total_size += file_size
                    else:
                        skipped_count += 1
                except Exception as e:
                    logger.warning(f"Error reading remote file {relative_path}: {e}")
                    skipped_count += 1
        else:
            if not os.path.exists(repo_path):
                return {"error": f"Repository path not found: {repo_path}"}

            # Walk through repository
            for root, dirs, files in os.walk(repo_path):
                dirs[:] = [
                    d
                    for d in dirs
                    if not any(
                        fnmatch(os.path.join(root, d), os.path.join(repo_path, pattern)) for pattern in exclude_patterns
                    )
                ]

                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, repo_path)

                    if any(fnmatch(relative_path, pattern) for pattern in exclude_patterns):
                        skipped_count += 1
                        continue
                    if not any(fnmatch(file, pattern) for pattern in include_patterns):
                        skipped_count += 1
                        continue

                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size > max_file_size:
                            logger.warning(f"Skipping large file: {relative_path} ({file_size} bytes)")
                            skipped_count += 1
                            continue

                        try:
                            with open(file_path, encoding="utf-8") as f:
                                content = f.read()
                        except UnicodeDecodeError:
                            with open(file_path, encoding="latin-1") as f:
                                content = f.read()

                        files_list.append((relative_path, content))
                        total_size += file_size

                    except Exception as e:
                        logger.warning(f"Error reading file {relative_path}: {e}")
                        skipped_count += 1
                        continue

        if not files_list:
            return {"error": "No files found matching the specified patterns", "skipped_count": skipped_count}

        logger.info(f"Fetched {len(files_list)} files, skipped {skipped_count}, total size: {total_size} bytes")

        return {
            "success": True,
            "files": files_list,  # List of (path, content) tuples
            "total_files": len(files_list),
            "total_size": total_size,
            "skipped_count": skipped_count,
            "repo_path": repo_path,
        }

    except Exception as e:
        logger.error(f"Error fetching repository files: {e}", exc_info=True)
        return {"error": f"Failed to fetch repository files: {str(e)}"}


async def internal_identify_abstractions(
    files_data: list[tuple[str, str]],
    project_name: str,
    max_abstractions: int = 10,
    language: str = "english",
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Identify core abstractions/concepts in the codebase using LLM.

    This is step 2 in the tutorial generation workflow.
    Analyzes the codebase and identifies 5-10 core concepts.

    Args:
        files_data: List of (path, content) tuples from fetch step
        project_name: Name of the project
        max_abstractions: Maximum number of abstractions to identify (default: 10)
        language: Language for documentation (default: "english")
        config: Configuration dictionary
        runtime_context: Runtime context with LLM client

    Returns:
        Dictionary with list of abstractions
    """
    try:
        if not runtime_context or not hasattr(runtime_context, "llm_client"):
            return {"error": "LLM client not available in runtime context"}

        if not files_data:
            return {"error": "No files data provided"}

        # Create context from files
        context = ""
        file_info = []
        for i, (path, content) in enumerate(files_data):
            entry = f"--- File Index {i}: {path} ---\n{content}\n\n"
            context += entry
            file_info.append((i, path))

        # Format file listing for prompt
        file_listing = "\n".join([f"- {idx} # {path}" for idx, path in file_info])

        # Build prompt with language support
        language_instruction = ""
        name_hint = ""
        desc_hint = ""
        if language.lower() != "english":
            language_instruction = f"IMPORTANT: Generate the `name` and `description` for each abstraction in **{language.capitalize()}** language. Do NOT use English for these fields.\n\n"
            name_hint = f" (value in {language.capitalize()})"
            desc_hint = f" (value in {language.capitalize()})"

        prompt = f"""
For the project `{project_name}`:

Codebase Context:
{context}

{language_instruction}Analyze the codebase context.
Identify the top 5-{max_abstractions} core most important abstractions to help those new to the codebase.

For each abstraction, provide:
1. A concise `name`{name_hint}.
2. A beginner-friendly `description` explaining what it is with a simple analogy, in around 100 words{desc_hint}.
3. A list of relevant `file_indices` (integers) using the format `idx # path/comment`.

List of file indices and paths present in the context:
{file_listing}

Format the output as a YAML list of dictionaries:

```yaml
- name: |
    Query Processing{name_hint}
  description: |
    Explains what the abstraction does.
    It's like a central dispatcher routing requests.{desc_hint}
  file_indices:
    - 0 # path/to/file1.py
    - 3 # path/to/related.py
- name: |
    Query Optimization{name_hint}
  description: |
    Another core concept, similar to a blueprint for objects.{desc_hint}
  file_indices:
    - 5 # path/to/another.js
# ... up to {max_abstractions} abstractions
```"""

        logger.info(f"Identifying abstractions for {project_name} using LLM...")

        response = await runtime_context.llm_client.generate_content(prompt=prompt, temperature=0.3, max_tokens=3000)

        # Parse YAML response (response is a string, not a dict)
        content = response
        yaml_match = re.search(r"```yaml\n(.*?)\n```", content, re.DOTALL)
        if not yaml_match:
            return {"error": "Could not find YAML block in LLM response"}

        yaml_str = yaml_match.group(1).strip()
        abstractions = yaml.safe_load(yaml_str)

        if not isinstance(abstractions, list):
            return {"error": "LLM output is not a list"}

        # Validate and process abstractions
        validated_abstractions = []
        for item in abstractions:
            if not isinstance(item, dict) or not all(k in item for k in ["name", "description", "file_indices"]):
                logger.warning(f"Skipping invalid abstraction: {item}")
                continue

            # Validate indices
            validated_indices = []
            for idx_entry in item["file_indices"]:
                try:
                    if isinstance(idx_entry, int):
                        idx = idx_entry
                    elif isinstance(idx_entry, str) and "#" in idx_entry:
                        idx = int(idx_entry.split("#")[0].strip())
                    else:
                        idx = int(str(idx_entry).strip())

                    if 0 <= idx < len(files_data):
                        validated_indices.append(idx)
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse index: {idx_entry}")
                    continue

            validated_abstractions.append(
                {
                    "name": item["name"].strip(),
                    "description": item["description"].strip(),
                    "files": sorted(set(validated_indices)),
                }
            )

        logger.info(f"Identified {len(validated_abstractions)} abstractions")

        return {
            "success": True,
            "abstractions": validated_abstractions,
            "total_abstractions": len(validated_abstractions),
        }

    except Exception as e:
        logger.error(f"Error identifying abstractions: {e}", exc_info=True)
        return {"error": f"Failed to identify abstractions: {str(e)}"}


async def internal_analyze_relationships(
    abstractions: list[dict[str, Any]],
    files_data: list[tuple[str, str]],
    project_name: str,
    language: str = "english",
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Analyze relationships between abstractions using LLM.

    This is step 3 in the tutorial generation workflow.
    Generates project summary and relationship diagram data.

    Args:
        abstractions: List of identified abstractions from step 2
        files_data: Original files data
        project_name: Name of the project
        language: Language for documentation
        config: Configuration dictionary
        runtime_context: Runtime context with LLM client

    Returns:
        Dictionary with summary and relationships
    """
    try:
        if not runtime_context or not hasattr(runtime_context, "llm_client"):
            return {"error": "LLM client not available in runtime context"}

        if not abstractions:
            return {"error": "No abstractions provided"}

        # Build context with abstractions and relevant files
        context = "Identified Abstractions:\n"
        abstraction_info = []
        all_relevant_indices = set()

        for i, abstr in enumerate(abstractions):
            file_indices_str = ", ".join(map(str, abstr["files"]))
            info_line = f"- Index {i}: {abstr['name']} (Relevant file indices: [{file_indices_str}])\n  Description: {abstr['description']}"
            context += info_line + "\n"
            abstraction_info.append(f"{i} # {abstr['name']}")
            all_relevant_indices.update(abstr["files"])

        # Add relevant file snippets
        context += "\nRelevant File Snippets (Referenced by Index and Path):\n"
        relevant_files_content = _get_content_for_indices(files_data, sorted(all_relevant_indices))
        file_context_str = "\n\n".join(
            f"--- File: {idx_path} ---\n{content}" for idx_path, content in relevant_files_content.items()
        )
        context += file_context_str

        # Build prompt
        language_instruction = ""
        lang_hint = ""
        if language.lower() != "english":
            language_instruction = f"IMPORTANT: Generate the `summary` and relationship `label` fields in **{language.capitalize()}** language. Do NOT use English for these fields.\n\n"
            lang_hint = f" (in {language.capitalize()})"

        prompt = f"""
Based on the following abstractions and relevant code snippets from the project `{project_name}`:

List of Abstraction Indices and Names:
{chr(10).join(abstraction_info)}

Context (Abstractions, Descriptions, Code):
{context}

{language_instruction}Please provide:
1. A high-level `summary` of the project's main purpose and functionality in a few beginner-friendly sentences{lang_hint}. Use markdown formatting with **bold** and *italic* text to highlight important concepts.
2. A list (`relationships`) describing the key interactions between these abstractions. For each relationship, specify:
    - `from_abstraction`: Index of the source abstraction (e.g., `0 # AbstractionName1`)
    - `to_abstraction`: Index of the target abstraction (e.g., `1 # AbstractionName2`)
    - `label`: A brief label for the interaction **in just a few words**{lang_hint} (e.g., "Manages", "Inherits", "Uses").
    Ideally the relationship should be backed by one abstraction calling or passing parameters to another.
    Simplify the relationship and exclude those non-important ones.

IMPORTANT: Make sure EVERY abstraction is involved in at least ONE relationship (either as source or target). Each abstraction index must appear at least once across all relationships.

Format the output as YAML:

```yaml
summary: |
  A brief, simple explanation of the project{lang_hint}.
  Can span multiple lines with **bold** and *italic* for emphasis.
relationships:
  - from_abstraction: 0 # AbstractionName1
    to_abstraction: 1 # AbstractionName2
    label: "Manages"{lang_hint}
  - from_abstraction: 2 # AbstractionName3
    to_abstraction: 0 # AbstractionName1
    label: "Provides config"{lang_hint}
  # ... other relationships
```

Now, provide the YAML output:
"""

        logger.info(f"Analyzing relationships for {project_name} using LLM...")

        response = await runtime_context.llm_client.generate_content(prompt=prompt, temperature=0.3, max_tokens=2000)

        # Parse YAML response (response is a string, not a dict)
        content = response
        yaml_match = re.search(r"```yaml\n(.*?)\n```", content, re.DOTALL)
        if not yaml_match:
            return {"error": "Could not find YAML block in LLM response"}

        yaml_str = yaml_match.group(1).strip()
        relationships_data = yaml.safe_load(yaml_str)

        if not isinstance(relationships_data, dict) or not all(
            k in relationships_data for k in ["summary", "relationships"]
        ):
            return {"error": "LLM output missing required keys"}

        # Validate relationships
        validated_relationships = []
        for rel in relationships_data["relationships"]:
            if not isinstance(rel, dict) or not all(k in rel for k in ["from_abstraction", "to_abstraction", "label"]):
                logger.warning(f"Skipping invalid relationship: {rel}")
                continue

            try:
                from_idx = int(str(rel["from_abstraction"]).split("#")[0].strip())
                to_idx = int(str(rel["to_abstraction"]).split("#")[0].strip())

                if 0 <= from_idx < len(abstractions) and 0 <= to_idx < len(abstractions):
                    validated_relationships.append({"from": from_idx, "to": to_idx, "label": rel["label"]})
            except (ValueError, TypeError):
                logger.warning(f"Could not parse relationship indices: {rel}")
                continue

        logger.info(f"Generated project summary and {len(validated_relationships)} relationships")

        return {
            "success": True,
            "summary": relationships_data["summary"],
            "relationships": validated_relationships,
            "total_relationships": len(validated_relationships),
        }

    except Exception as e:
        logger.error(f"Error analyzing relationships: {e}", exc_info=True)
        return {"error": f"Failed to analyze relationships: {str(e)}"}


async def internal_order_chapters(
    abstractions: list[dict[str, Any]],
    relationships: dict[str, Any],
    project_name: str,
    language: str = "english",
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Determine optimal chapter ordering for tutorial using LLM.

    This is step 4 in the tutorial generation workflow.
    Orders abstractions from foundational to advanced concepts.

    Args:
        abstractions: List of identified abstractions
        relationships: Relationships data with summary
        project_name: Name of the project
        language: Language for documentation
        config: Configuration dictionary
        runtime_context: Runtime context with LLM client

    Returns:
        Dictionary with ordered chapter indices
    """
    try:
        if not runtime_context or not hasattr(runtime_context, "llm_client"):
            return {"error": "LLM client not available in runtime context"}

        if not abstractions:
            return {"error": "No abstractions provided"}

        # Build abstraction listing
        abstraction_info = []
        for i, abstr in enumerate(abstractions):
            abstraction_info.append(f"- {i} # {abstr['name']}")
        abstraction_listing = "\n".join(abstraction_info)

        # Build context with summary and relationships
        context = f"Project Summary:\n{relationships.get('summary', '')}\n\n"
        context += "Relationships (Indices refer to abstractions above):\n"

        for rel in relationships.get("relationships", []):
            from_name = abstractions[rel["from"]]["name"]
            to_name = abstractions[rel["to"]]["name"]
            context += f"- From {rel['from']} ({from_name}) to {rel['to']} ({to_name}): {rel['label']}\n"

        prompt = f"""
Given the following project abstractions and their relationships for the project `{project_name}`:

Abstractions (Index # Name):
{abstraction_listing}

Context about relationships and project summary:
{context}

If you are going to make a tutorial for `{project_name}`, what is the best order to explain these abstractions, from first to last?
Ideally, first explain those that are the most important or foundational, perhaps user-facing concepts or entry points. Then move to more detailed, lower-level implementation details or supporting concepts.

Output the ordered list of abstraction indices, including the name in a comment for clarity. Use the format `idx # AbstractionName`.

```yaml
- 2 # FoundationalConcept
- 0 # CoreClassA
- 1 # CoreClassB (uses CoreClassA)
- ...
```

Now, provide the YAML output:
"""

        logger.info(f"Ordering chapters for {project_name} using LLM...")

        response = await runtime_context.llm_client.generate_content(prompt=prompt, temperature=0.3, max_tokens=1000)

        # Parse YAML response (response is a string, not a dict)
        content = response
        yaml_match = re.search(r"```yaml\n(.*?)\n```", content, re.DOTALL)
        if not yaml_match:
            return {"error": "Could not find YAML block in LLM response"}

        yaml_str = yaml_match.group(1).strip()
        ordered_indices_raw = yaml.safe_load(yaml_str)

        if not isinstance(ordered_indices_raw, list):
            return {"error": "LLM output is not a list"}

        # Validate indices
        ordered_indices = []
        seen_indices = set()

        for entry in ordered_indices_raw:
            try:
                if isinstance(entry, int):
                    idx = entry
                elif isinstance(entry, str) and "#" in entry:
                    idx = int(entry.split("#")[0].strip())
                else:
                    idx = int(str(entry).strip())

                if not (0 <= idx < len(abstractions)):
                    logger.warning(f"Invalid index {idx}, skipping")
                    continue

                if idx in seen_indices:
                    logger.warning(f"Duplicate index {idx}, skipping")
                    continue

                ordered_indices.append(idx)
                seen_indices.add(idx)

            except (ValueError, TypeError):
                logger.warning(f"Could not parse index from: {entry}")
                continue

        # Check if all abstractions are included
        if len(ordered_indices) != len(abstractions):
            missing_indices = set(range(len(abstractions))) - seen_indices
            logger.warning(f"Missing indices in ordering: {missing_indices}")
            # Add missing indices at the end
            for idx in sorted(missing_indices):
                ordered_indices.append(idx)

        logger.info(f"Determined chapter order: {ordered_indices}")

        return {"success": True, "chapter_order": ordered_indices, "total_chapters": len(ordered_indices)}

    except Exception as e:
        logger.error(f"Error ordering chapters: {e}", exc_info=True)
        return {"error": f"Failed to order chapters: {str(e)}"}


async def internal_generate_tutorial_chapter(
    chapter_number: int,
    abstraction: dict[str, Any],
    files_data: list[tuple[str, str]],
    project_name: str,
    previous_chapters_summary: str = "",
    full_chapter_listing: str = "",
    language: str = "english",
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Generate a single tutorial chapter using LLM.

    This is step 5 in the tutorial generation workflow (called multiple times).
    Creates beginner-friendly markdown content for one chapter.

    Args:
        chapter_number: Chapter number (1-indexed)
        abstraction: Abstraction details (name, description, files)
        files_data: Original files data
        project_name: Name of the project
        previous_chapters_summary: Summary of previous chapters for context
        full_chapter_listing: Complete chapter structure for linking
        language: Language for documentation
        config: Configuration dictionary
        runtime_context: Runtime context with LLM client

    Returns:
        Dictionary with generated chapter markdown
    """
    try:
        if not runtime_context or not hasattr(runtime_context, "llm_client"):
            return {"error": "LLM client not available in runtime context"}

        abstraction_name = abstraction["name"]
        abstraction_description = abstraction["description"]

        # Get related file content
        related_files_content = _get_content_for_indices(files_data, abstraction["files"])
        file_context_str = "\n\n".join(
            f"--- File: {idx_path.split('# ')[1] if '# ' in idx_path else idx_path} ---\n{content}"
            for idx_path, content in related_files_content.items()
        )

        # Build language-specific instructions
        language_instruction = ""
        if language.lower() != "english":
            lang_cap = language.capitalize()
            language_instruction = f"IMPORTANT: Write this ENTIRE tutorial chapter in **{lang_cap}**. DO NOT use English anywhere except in code syntax.\n\n"

        prompt = f"""
{language_instruction}Write a very beginner-friendly tutorial chapter (in Markdown format) for the project `{project_name}` about the concept: "{abstraction_name}". This is Chapter {chapter_number}.

Concept Details:
- Name: {abstraction_name}
- Description:
{abstraction_description}

Complete Tutorial Structure:
{full_chapter_listing if full_chapter_listing else "This is a standalone chapter."}

Context from previous chapters:
{previous_chapters_summary if previous_chapters_summary else "This is the first chapter."}

Relevant Code Snippets:
{file_context_str if file_context_str else "No specific code snippets provided for this abstraction."}

Instructions for the chapter:
- Start with a clear heading: `# Chapter {chapter_number}: {abstraction_name}`

- Begin with high-level motivation explaining what problem this abstraction solves. Start with a concrete use case example.

- If complex, break down into key concepts and explain each one-by-one in a beginner-friendly way.

- Explain how to use this abstraction with example inputs and outputs.

- Keep code blocks BELOW 10 lines! Break longer code into smaller pieces. Use comments to skip non-important details.

- Describe internal implementation with a non-code walkthrough of what happens step-by-step.

- Use a simple mermaid sequenceDiagram with at most 5 participants for clarity.

- When referring to other core abstractions, use proper Markdown links: [Chapter Title](filename.md)

- Use mermaid diagrams (```mermaid``` format) to illustrate complex concepts.

- Use analogies and examples throughout to help beginners understand.

- End with a brief conclusion summarizing what was learned.

- Keep the tone welcoming and easy for newcomers to understand.

Now, provide the Markdown content for this chapter:
"""

        logger.info(f"Writing chapter {chapter_number}: {abstraction_name} using LLM...")

        response = await runtime_context.llm_client.generate_content(prompt=prompt, temperature=0.4, max_tokens=2500)

        # Response is a string, not a dict
        chapter_content = response

        # Ensure proper heading
        actual_heading = f"# Chapter {chapter_number}: {abstraction_name}"
        if not chapter_content.strip().startswith(f"# Chapter {chapter_number}"):
            lines = chapter_content.strip().split("\n")
            if lines and lines[0].strip().startswith("#"):
                lines[0] = actual_heading
                chapter_content = "\n".join(lines)
            else:
                chapter_content = f"{actual_heading}\n\n{chapter_content}"

        logger.info(f"Successfully generated chapter {chapter_number}")

        return {
            "success": True,
            "chapter_number": chapter_number,
            "chapter_content": chapter_content,
            "abstraction_name": abstraction_name,
        }

    except Exception as e:
        logger.error(f"Error generating chapter {chapter_number}: {e}", exc_info=True)
        return {"error": f"Failed to generate chapter: {str(e)}"}


async def internal_combine_tutorial(
    chapters: list[str],
    abstractions: list[dict[str, Any]],
    chapter_order: list[int],
    relationships: dict[str, Any],
    project_name: str,
    repository_url: str | None = None,
    output_path: str | None = None,
    config: dict[str, Any] | None = None,
    runtime_context: Any = None,
) -> dict[str, Any]:
    """
    Combine tutorial chapters into final output with index and mermaid diagram.

    This is the final step (step 6) in the tutorial generation workflow.
    Creates index.md and individual chapter files.
    IMPORTANT: output_path must be within the workspace directory.

    Args:
        chapters: List of generated chapter markdown content
        abstractions: List of all abstractions
        chapter_order: Ordered list of chapter indices
        relationships: Relationships data with summary
        project_name: Name of the project
        repository_url: URL of the source repository
        output_path: Path to write tutorial files (must be within workspace directory)
        config: Configuration dictionary
        runtime_context: Runtime context

    Returns:
        Dictionary with tutorial content and file information
    """
    try:
        # Validate output_path is within workspace if provided
        if output_path:
            workspace_path = _get_workspace_path(config)
            is_valid, error = _validate_path_in_workspace(output_path, workspace_path)
            if not is_valid:
                return {"error": error}

        # Generate Mermaid diagram
        mermaid_lines = ["flowchart TD"]

        # Add nodes
        for i, abstr in enumerate(abstractions):
            node_id = f"A{i}"
            sanitized_name = abstr["name"].replace('"', "")
            mermaid_lines.append(f'    {node_id}["{sanitized_name}"]')

        # Add edges
        for rel in relationships.get("relationships", []):
            from_node_id = f"A{rel['from']}"
            to_node_id = f"A{rel['to']}"
            edge_label = rel["label"].replace('"', "").replace("\n", " ")
            if len(edge_label) > 30:
                edge_label = edge_label[:27] + "..."
            mermaid_lines.append(f'    {from_node_id} -- "{edge_label}" --> {to_node_id}')

        mermaid_diagram = "\n".join(mermaid_lines)

        # Build index.md content
        index_content = f"# Tutorial: {project_name}\n\n"
        index_content += f"{relationships.get('summary', '')}\n\n"

        if repository_url:
            index_content += f"**Source Repository:** [{repository_url}]({repository_url})\n\n"

        # Add Mermaid diagram
        index_content += "```mermaid\n"
        index_content += mermaid_diagram + "\n"
        index_content += "```\n\n"

        index_content += "## Chapters\n\n"

        # Generate chapter files data
        chapter_files = []
        for i, abstraction_index in enumerate(chapter_order):
            if 0 <= abstraction_index < len(abstractions) and i < len(chapters):
                abstraction_name = abstractions[abstraction_index]["name"]
                safe_name = "".join(c if c.isalnum() else "_" for c in abstraction_name).lower()
                filename = f"{i + 1:02d}_{safe_name}.md"

                index_content += f"{i + 1}. [{abstraction_name}]({filename})\n"

                # Add attribution to chapter
                chapter_content = chapters[i]
                if not chapter_content.endswith("\n\n"):
                    chapter_content += "\n\n"
                chapter_content += "---\n\nGenerated by Synkora AI Documentation Agent"

                chapter_files.append({"filename": filename, "content": chapter_content})

        # Add attribution to index
        index_content += "\n\n---\n\nGenerated by Synkora AI Documentation Agent"

        # Write files if output path provided
        if output_path:
            from .git_helpers import async_makedirs, async_write_file

            await async_makedirs(output_path, config)

            index_filepath = os.path.join(output_path, "index.md")
            await async_write_file(index_filepath, index_content, config)
            logger.info(f"Wrote {index_filepath}")

            for chapter_info in chapter_files:
                chapter_filepath = os.path.join(output_path, chapter_info["filename"])
                await async_write_file(chapter_filepath, chapter_info["content"], config)
                logger.info(f"Wrote {chapter_filepath}")

        logger.info(f"Tutorial generation complete! {len(chapter_files)} chapters created.")

        return {
            "success": True,
            "index_content": index_content,
            "chapter_files": chapter_files,
            "total_chapters": len(chapter_files),
            "output_path": output_path,
            "mermaid_diagram": mermaid_diagram,
        }

    except Exception as e:
        logger.error(f"Error combining tutorial: {e}", exc_info=True)
        return {"error": f"Failed to combine tutorial: {str(e)}"}
