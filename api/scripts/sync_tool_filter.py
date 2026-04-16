#!/usr/bin/env python3
"""
Sync Tool Filter Script

Automatically generates TOOL_KEYWORDS mapping by scanning all registered tools.
This ensures the tool filter stays in sync with actual tool registrations.

Usage:
    python scripts/sync_tool_filter.py [--dry-run] [--output FILE]

Options:
    --dry-run    Print the generated keywords without updating the file
    --output     Write to a specific file instead of updating tool_filter.py
"""

import argparse
import logging
import re
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Base directory
BASE_DIR = Path(__file__).parent.parent
TOOL_REGISTRATIONS_DIR = BASE_DIR / "src" / "services" / "agents" / "tool_registrations"
ADK_TOOLS_FILE = BASE_DIR / "src" / "services" / "agents" / "adk_tools.py"
TOOL_FILTER_FILE = BASE_DIR / "src" / "services" / "agents" / "tool_filter.py"

# Additional keywords to add for specific tool patterns
PATTERN_KEYWORDS = {
    # Communication patterns
    "send": ["send", "post", "notify", "tell"],
    "message": ["message", "msg", "chat"],
    "email": ["email", "mail", "inbox"],
    "dm": ["dm", "direct message", "private"],
    # CRUD patterns
    "create": ["create", "new", "add", "make"],
    "read": ["read", "get", "fetch", "view", "show"],
    "update": ["update", "edit", "modify", "change"],
    "delete": ["delete", "remove", "cancel"],
    "list": ["list", "all", "show all", "get all"],
    "search": ["search", "find", "query", "look for"],
    # Service-specific patterns
    "slack": ["slack", "channel", "workspace"],
    "gmail": ["gmail", "google mail", "email"],
    "calendar": ["calendar", "meeting", "event", "schedule"],
    "drive": ["drive", "google drive", "file", "document"],
    "zoom": ["zoom", "video call", "meeting"],
    "jira": ["jira", "ticket", "issue", "sprint"],
    "github": ["github", "repo", "repository", "pr", "pull request"],
    "gitlab": ["gitlab", "repo", "repository", "mr", "merge request"],
    "clickup": ["clickup", "task", "todo"],
    "twitter": ["twitter", "x", "tweet", "social"],
    "linkedin": ["linkedin", "professional", "social"],
    "telegram": ["telegram", "tg", "chat"],
    "youtube": ["youtube", "video", "watch"],
    "browser": ["browser", "web", "page", "click", "navigate"],
    "git": ["git", "commit", "branch", "push", "pull"],
    "database": ["database", "db", "sql", "query", "table"],
    "chart": ["chart", "graph", "visualize", "plot"],
    "file": ["file", "document", "read", "write"],
    "s3": ["s3", "aws", "bucket", "storage"],
    "elasticsearch": ["elasticsearch", "elastic", "es", "logs"],
    "docker": ["docker", "container", "logs"],
    "recall": ["recall", "meeting", "recording", "transcript"],
    "schedule": ["schedule", "scheduler", "cron", "recurring", "daily", "weekly", "reminder"],
    "followup": ["followup", "follow up", "reminder", "task"],
    "hackernews": ["hackernews", "hacker news", "hn", "news", "tech news"],
    "spawn": ["spawn", "delegate", "sub-task", "child"],
    "screenshot": ["screenshot", "capture", "image"],
}

# Time-related keywords for scheduler tools
TIME_KEYWORDS = [
    "daily",
    "weekly",
    "hourly",
    "monthly",
    "morning",
    "evening",
    "night",
    "every day",
    "every week",
    "every hour",
    "7 am",
    "8 am",
    "9 am",
    "10 am",
    "at",
    "on",
    "every",
]


def extract_tools_from_registry_file(filepath: Path) -> list[dict]:
    """Extract tool registrations from a registry file."""
    tools = []

    try:
        content = filepath.read_text()

        # Find all registry.register_tool calls with their parameters
        # Pattern matches: registry.register_tool(name="...", description="...", ...)
        pattern = r'registry\.register_tool\s*\(\s*name\s*=\s*["\']([^"\']+)["\']'
        desc_pattern = r'description\s*=\s*["\']([^"\']+)["\']'

        # Find all tool registrations
        for match in re.finditer(pattern, content):
            tool_name = match.group(1)

            # Try to find the description nearby (within 500 chars)
            start_pos = match.start()
            end_pos = min(start_pos + 1000, len(content))
            snippet = content[start_pos:end_pos]

            desc_match = re.search(desc_pattern, snippet)
            description = desc_match.group(1) if desc_match else ""

            tools.append({"name": tool_name, "description": description, "source": filepath.name})

    except Exception as e:
        logger.warning(f"Error parsing {filepath}: {e}")

    return tools


def extract_tools_from_adk_tools(filepath: Path) -> list[dict]:
    """Extract tool registrations from adk_tools.py."""
    tools = []

    try:
        content = filepath.read_text()

        # Pattern 1: registry.register_tool(name="...")
        pattern1 = r'registry\.register_tool\s*\(\s*name\s*=\s*["\']([^"\']+)["\']'
        # Pattern 2: self.register_tool(name="...") - used in ADKToolRegistry class
        pattern2 = r'self\.register_tool\s*\(\s*name\s*=\s*["\']([^"\']+)["\']'

        desc_pattern = r'description\s*=\s*["\']([^"\']+)["\']'

        for pattern in [pattern1, pattern2]:
            for match in re.finditer(pattern, content):
                tool_name = match.group(1)

                start_pos = match.start()
                end_pos = min(start_pos + 1500, len(content))
                snippet = content[start_pos:end_pos]

                desc_match = re.search(desc_pattern, snippet)
                description = desc_match.group(1) if desc_match else ""

                tools.append({"name": tool_name, "description": description, "source": filepath.name})

    except Exception as e:
        logger.warning(f"Error parsing {filepath}: {e}")

    return tools


def generate_keywords_for_tool(tool_name: str, description: str) -> list[str]:
    """Generate relevant keywords for a tool based on its name and description."""
    keywords = set()

    # 1. Extract words from tool name (remove internal_ prefix, split on _)
    name_without_prefix = tool_name.replace("internal_", "")
    name_parts = name_without_prefix.split("_")

    # Add each meaningful word from the name
    for part in name_parts:
        if len(part) > 2:  # Skip very short words
            keywords.add(part.lower())

    # 2. Add pattern-based keywords
    name_lower = tool_name.lower()
    desc_lower = description.lower()
    combined = f"{name_lower} {desc_lower}"

    for pattern, pattern_keywords in PATTERN_KEYWORDS.items():
        if pattern in combined:
            keywords.update(pattern_keywords)

    # 3. Extract important words from description
    if description:
        # Remove common words
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "need",
            "dare",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "under",
            "again",
            "further",
            "then",
            "once",
            "here",
            "there",
            "when",
            "where",
            "why",
            "how",
            "all",
            "each",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "just",
            "use",
            "this",
            "that",
            "these",
            "those",
            "it",
            "its",
            "or",
            "and",
        }

        desc_words = re.findall(r"\b[a-z]{3,}\b", desc_lower)
        for word in desc_words:
            if word not in stop_words:
                keywords.add(word)

    # 4. Add time keywords for scheduler-related tools
    if any(x in name_lower for x in ["schedule", "cron", "recurring", "reminder"]):
        keywords.update(TIME_KEYWORDS)

    # 5. Add specific compound phrases based on tool type
    if "send" in name_lower and "message" in name_lower:
        keywords.add("send message")
    if "create" in name_lower and "issue" in name_lower:
        keywords.add("create issue")
        keywords.add("new issue")
    if "pull" in name_lower and "request" in name_lower:
        keywords.add("pull request")
        keywords.add("pr")
    if "merge" in name_lower and "request" in name_lower:
        keywords.add("merge request")
        keywords.add("mr")

    return sorted(keywords)


def scan_all_tools() -> list[dict]:
    """Scan all tool registration files and return list of tools."""
    all_tools = []

    # Scan tool_registrations directory
    if TOOL_REGISTRATIONS_DIR.exists():
        for filepath in TOOL_REGISTRATIONS_DIR.glob("*.py"):
            if filepath.name.startswith("__"):
                continue
            tools = extract_tools_from_registry_file(filepath)
            all_tools.extend(tools)
            logger.info(f"Found {len(tools)} tools in {filepath.name}")

    # Scan adk_tools.py
    if ADK_TOOLS_FILE.exists():
        tools = extract_tools_from_adk_tools(ADK_TOOLS_FILE)
        all_tools.extend(tools)
        logger.info(f"Found {len(tools)} tools in adk_tools.py")

    # Deduplicate by name
    seen = set()
    unique_tools = []
    for tool in all_tools:
        if tool["name"] not in seen:
            seen.add(tool["name"])
            unique_tools.append(tool)

    logger.info(f"\nTotal unique tools found: {len(unique_tools)}")
    return unique_tools


def generate_tool_keywords_dict(tools: list[dict]) -> dict[str, list[str]]:
    """Generate the TOOL_KEYWORDS dictionary."""
    tool_keywords = {}

    for tool in tools:
        keywords = generate_keywords_for_tool(tool["name"], tool["description"])
        tool_keywords[tool["name"]] = keywords

    return tool_keywords


def format_tool_keywords_python(tool_keywords: dict[str, list[str]]) -> str:
    """Format the tool keywords dict as Python code."""
    lines = ["TOOL_KEYWORDS: dict[str, list[str]] = {"]

    # Group tools by category for readability
    categories = {}
    for tool_name, keywords in sorted(tool_keywords.items()):
        # Determine category from tool name
        parts = tool_name.replace("internal_", "").split("_")
        if len(parts) > 1:
            category = parts[0]
        else:
            category = "other"

        if category not in categories:
            categories[category] = []
        categories[category].append((tool_name, keywords))

    # Output by category
    for category in sorted(categories.keys()):
        tools = categories[category]
        lines.append(f"    # {category.title()} tools")

        for tool_name, keywords in tools:
            # Format keywords list
            if len(keywords) <= 5:
                kw_str = ", ".join(f'"{k}"' for k in keywords)
                lines.append(f'    "{tool_name}": [{kw_str}],')
            else:
                lines.append(f'    "{tool_name}": [')
                # Split into chunks of 6
                for i in range(0, len(keywords), 6):
                    chunk = keywords[i : i + 6]
                    kw_str = ", ".join(f'"{k}"' for k in chunk)
                    lines.append(f"        {kw_str},")
                lines.append("    ],")

        lines.append("")

    lines.append("}")
    return "\n".join(lines)


def update_tool_filter_file(new_keywords_code: str) -> bool:
    """Update the tool_filter.py file with new TOOL_KEYWORDS."""
    try:
        content = TOOL_FILTER_FILE.read_text()

        # Find the TOOL_KEYWORDS dict and replace it
        # Find where TOOL_KEYWORDS starts
        start_marker = "TOOL_KEYWORDS: dict[str, list[str]] = {"
        start_idx = content.find(start_marker)

        if start_idx == -1:
            logger.error("Could not find TOOL_KEYWORDS in tool_filter.py")
            return False

        # Find the matching closing brace
        brace_count = 0
        end_idx = start_idx
        in_string = False
        string_char = None

        for i, char in enumerate(content[start_idx:], start=start_idx):
            if char in "\"'":
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char and content[i - 1] != "\\":
                    in_string = False
            elif not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break

        # Replace the old dict with the new one
        new_content = content[:start_idx] + new_keywords_code + content[end_idx:]

        TOOL_FILTER_FILE.write_text(new_content)
        logger.info(f"Updated {TOOL_FILTER_FILE}")
        return True

    except Exception as e:
        logger.error(f"Error updating tool_filter.py: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Sync tool filter with registered tools")
    parser.add_argument("--dry-run", action="store_true", help="Print without updating file")
    parser.add_argument("--output", type=str, help="Write to specific file")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Scanning tool registrations...")
    logger.info("=" * 60)

    # Scan all tools
    tools = scan_all_tools()

    if not tools:
        logger.error("No tools found!")
        sys.exit(1)

    # Generate keywords
    logger.info("\nGenerating keywords for each tool...")
    tool_keywords = generate_tool_keywords_dict(tools)

    # Format as Python code
    keywords_code = format_tool_keywords_python(tool_keywords)

    if args.dry_run:
        logger.info("\n" + "=" * 60)
        logger.info("Generated TOOL_KEYWORDS (dry run):")
        logger.info("=" * 60)
        print(keywords_code)
    elif args.output:
        output_path = Path(args.output)
        output_path.write_text(keywords_code)
        logger.info(f"\nWritten to {output_path}")
    else:
        # Update the actual file
        logger.info("\nUpdating tool_filter.py...")
        if update_tool_filter_file(keywords_code):
            logger.info("\n✅ Successfully updated TOOL_KEYWORDS!")
            logger.info(f"   Total tools: {len(tool_keywords)}")
        else:
            logger.error("\n❌ Failed to update tool_filter.py")
            sys.exit(1)


if __name__ == "__main__":
    main()
