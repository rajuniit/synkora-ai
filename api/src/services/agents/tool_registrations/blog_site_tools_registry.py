"""
Blog Site Tools Registry - Agentic Approach

Registers blog site tools that provide minimal scaffolding.
The AGENT generates all custom CSS, HTML, and content dynamically.

Tools:
- internal_generate_blog_site: Creates directory structure (scaffolding only)
- internal_create_github_repository: Creates GitHub repo
- internal_deploy_blog_to_github: Deploys site to GitHub
- internal_enable_github_pages: Enables GitHub Pages hosting

The agent should use internal_write_file to create custom CSS/HTML based on
user's style requirements (Medium, Minimal, Modern, Dark, etc.)
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_blog_site_tools(registry):
    """
    Register blog site scaffolding and deployment tools.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.blog_site_tools import (
        internal_create_github_repo,
        internal_deploy_to_github,
        internal_enable_github_pages,
        internal_generate_blog_site,
    )

    # =========================================================================
    # Wrapper Functions
    # =========================================================================

    async def generate_blog_site_wrapper(config: dict[str, Any] | None = None, **kwargs):
        return await internal_generate_blog_site(
            site_name=kwargs.get("site_name"),
            description=kwargs.get("description", ""),
            author_name=kwargs.get("author_name", "Author"),
            config=config,
        )

    async def create_github_repo_wrapper(config: dict[str, Any] | None = None, **kwargs):
        return await internal_create_github_repo(
            repo_name=kwargs.get("repo_name"),
            description=kwargs.get("description", ""),
            private=kwargs.get("private", False),
            config=config,
        )

    async def deploy_to_github_wrapper(config: dict[str, Any] | None = None, **kwargs):
        # Build repo URL from owner and repo name if not provided directly
        repo_url = kwargs.get("repo_url")
        if not repo_url:
            owner = kwargs.get("github_username") or kwargs.get("owner")
            repo_name = kwargs.get("repo_name")
            if owner and repo_name:
                repo_url = f"https://github.com/{owner}/{repo_name}.git"

        return await internal_deploy_to_github(
            site_path=kwargs.get("site_path"),
            repo_url=repo_url or "",
            branch=kwargs.get("branch", "main"),
            commit_message=kwargs.get("commit_message", "Deploy blog site"),
            config=config,
        )

    async def enable_github_pages_wrapper(config: dict[str, Any] | None = None, **kwargs):
        return await internal_enable_github_pages(
            repo_name=kwargs.get("repo_name"),
            owner=kwargs.get("github_username") or kwargs.get("owner"),
            branch=kwargs.get("branch", "main"),
            path=kwargs.get("path", "/"),
            config=config,
        )

    # =========================================================================
    # Register Tools
    # =========================================================================

    registry.register_tool(
        name="internal_generate_blog_site",
        description="""Create a blog site scaffolding (directory structure and placeholder files).

This tool creates ONLY the basic structure:
- index.html (minimal placeholder)
- css/style.css (empty - YOU must write the CSS)
- js/app.js (minimal)
- posts/ directory
- images/ directory

IMPORTANT: After calling this tool, YOU must use internal_write_file to:
1. Write custom CSS to css/style.css based on user's desired style
2. Update index.html with properly styled HTML
3. Create blog posts in posts/ directory
4. Create about.html and other pages

You can create ANY style the user wants:
- Medium style: Georgia font, 680px max-width, green accent
- Minimal: System fonts, whitespace, simple black/white
- Modern: Inter font, gradients, card layouts
- Dark: Dark background, light text, blue accent
- Or ANY custom style the user describes""",
        parameters={
            "type": "object",
            "properties": {
                "site_name": {"type": "string", "description": "Name of the blog site"},
                "description": {"type": "string", "description": "Tagline or description for the blog"},
                "author_name": {"type": "string", "description": "Name of the blog author"},
            },
            "required": ["site_name"],
        },
        function=generate_blog_site_wrapper,
    )

    registry.register_tool(
        name="internal_create_github_repository",
        description="""Create a new GitHub repository for the blog.

Creates an empty repository on GitHub. Use this before deploying the blog.
Requires GitHub OAuth - user must have connected their GitHub account.""",
        parameters={
            "type": "object",
            "properties": {
                "repo_name": {
                    "type": "string",
                    "description": "Repository name (will be part of URL: github.com/username/repo_name)",
                },
                "description": {"type": "string", "description": "Repository description"},
                "private": {
                    "type": "boolean",
                    "description": "Make repository private (default: false, must be public for GitHub Pages)",
                },
            },
            "required": ["repo_name"],
        },
        function=create_github_repo_wrapper,
        requires_auth="github",
    )

    registry.register_tool(
        name="internal_deploy_blog_to_github",
        description="""Deploy the blog site to GitHub.

Initializes git, commits all files, and pushes to the repository.
Requires GitHub OAuth authentication.""",
        parameters={
            "type": "object",
            "properties": {
                "site_path": {
                    "type": "string",
                    "description": "Path to the blog site directory (from internal_generate_blog_site)",
                },
                "repo_name": {"type": "string", "description": "GitHub repository name"},
                "github_username": {"type": "string", "description": "GitHub username (repository owner)"},
                "branch": {"type": "string", "description": "Branch name (default: main)"},
                "commit_message": {"type": "string", "description": "Git commit message"},
            },
            "required": ["site_path", "repo_name", "github_username"],
        },
        function=deploy_to_github_wrapper,
        requires_auth="github",
    )

    registry.register_tool(
        name="internal_enable_github_pages",
        description="""Enable GitHub Pages to make the blog publicly accessible.

After enabling, the blog will be live at: https://{username}.github.io/{repo_name}/
Note: May take a few minutes for the site to become available.
Requires GitHub OAuth authentication.""",
        parameters={
            "type": "object",
            "properties": {
                "repo_name": {"type": "string", "description": "GitHub repository name"},
                "github_username": {"type": "string", "description": "GitHub username"},
                "branch": {"type": "string", "description": "Branch to deploy (default: main)"},
            },
            "required": ["repo_name", "github_username"],
        },
        function=enable_github_pages_wrapper,
        requires_auth="github",
    )

    logger.info("Registered 4 blog site tools (scaffolding + GitHub deployment)")
