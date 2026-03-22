"""
External tools implementations.

This module contains implementations for external API integrations like
GitHub, YouTube, and Zoom.

Note: Gmail tools are now in internal_tools/gmail_tools.py with full OAuth support.
"""

from .github_tools import *
from .web_tools import *
from .youtube_tools import *
from .zoom_tools import *

__all__ = [
    # GitHub tools
    "github_search_repos",
    "github_get_repo",
    "github_list_issues",
    "github_create_issue",
    "github_list_pull_requests",
    "github_get_user",
    "github_list_my_repos",
    "github_composite",
    # YouTube tools
    "youtube_search",
    "youtube_get_video_info",
    # Web tools
    "web_search",
    "web_crawl",
]
