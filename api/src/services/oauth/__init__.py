"""OAuth authentication services."""

from .clickup_oauth import ClickUpOAuth
from .github_oauth import GitHubOAuth
from .gitlab_oauth import GitLabOAuth
from .gmail_oauth import GmailOAuth
from .jira_oauth import JiraOAuth
from .linkedin_oauth import LinkedInOAuth
from .oauth_app_service import OAuthAppService
from .slack_oauth import SlackOAuth
from .telegram_auth import TelegramAuth
from .twitter_oauth import TwitterOAuth

__all__ = [
    "ClickUpOAuth",
    "GitHubOAuth",
    "GitLabOAuth",
    "GmailOAuth",
    "JiraOAuth",
    "LinkedInOAuth",
    "OAuthAppService",
    "SlackOAuth",
    "TelegramAuth",
    "TwitterOAuth",
]
