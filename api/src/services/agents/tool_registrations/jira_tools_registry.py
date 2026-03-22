"""
Jira Tools Registry

Registers all Jira-related tools with the ADK tool registry.
This modular approach keeps tool registration organized and maintainable.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_jira_tools(registry):
    """
    Register all Jira tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.jira_tools import (
        internal_add_jira_comment,
        internal_close_jira_sprint,
        internal_create_jira_issue,
        internal_get_jira_boards,
        internal_get_jira_issue,
        internal_get_jira_project,
        internal_get_jira_sprints,
        internal_get_jira_users,
        internal_get_sprint_issues,
        internal_search_jira_issues,
        internal_start_jira_sprint,
        internal_transition_jira_issue,
        internal_update_jira_issue,
    )

    # Jira tools - create wrappers that inject runtime_context
    async def internal_get_jira_issue_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_jira_issue(
            issue_key=kwargs.get("issue_key"), runtime_context=runtime_context, config=config
        )

    async def internal_search_jira_issues_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_search_jira_issues(
            jql=kwargs.get("jql"),
            max_results=kwargs.get("max_results", 50),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_add_jira_comment_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_add_jira_comment(
            issue_key=kwargs.get("issue_key"),
            comment_text=kwargs.get("comment_text"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_update_jira_issue_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_update_jira_issue(
            issue_key=kwargs.get("issue_key"),
            updates=kwargs.get("updates"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_transition_jira_issue_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_transition_jira_issue(
            issue_key=kwargs.get("issue_key"),
            transition_id=kwargs.get("transition_id"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_get_jira_project_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_jira_project(
            project_key=kwargs.get("project_key"), runtime_context=runtime_context, config=config
        )

    async def internal_create_jira_issue_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_create_jira_issue(
            project_key=kwargs.get("project_key"),
            summary=kwargs.get("summary"),
            issue_type=kwargs.get("issue_type", "Task"),
            description=kwargs.get("description"),
            priority=kwargs.get("priority"),
            assignee_account_id=kwargs.get("assignee_account_id"),
            labels=kwargs.get("labels"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_get_jira_boards_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_jira_boards(
            project_key=kwargs.get("project_key"), runtime_context=runtime_context, config=config
        )

    async def internal_get_jira_sprints_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_jira_sprints(
            board_id=kwargs.get("board_id"),
            state=kwargs.get("state"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_get_sprint_issues_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_sprint_issues(
            sprint_id=kwargs.get("sprint_id"), runtime_context=runtime_context, config=config
        )

    async def internal_start_jira_sprint_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_start_jira_sprint(
            sprint_id=kwargs.get("sprint_id"),
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_close_jira_sprint_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_close_jira_sprint(
            sprint_id=kwargs.get("sprint_id"), runtime_context=runtime_context, config=config
        )

    async def internal_get_jira_users_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_jira_users(
            project_key=kwargs.get("project_key"), runtime_context=runtime_context, config=config
        )

    # Register all Jira tools
    registry.register_tool(
        name="internal_get_jira_issue",
        description="Get detailed information about a Jira issue including summary, description, status, priority, assignee, comments, and attachments. Use this to understand the context of a reported bug or task.",
        parameters={
            "type": "object",
            "properties": {"issue_key": {"type": "string", "description": "Jira issue key (e.g., 'PROJ-123')"}},
            "required": ["issue_key"],
        },
        function=internal_get_jira_issue_wrapper,
    )

    registry.register_tool(
        name="internal_search_jira_issues",
        description="Search for Jira issues using JQL (Jira Query Language). Use this to find related issues, bugs, or tasks. Example JQL: 'project = PROJ AND status = Open' or 'text ~ \"error\" AND priority = High'.",
        parameters={
            "type": "object",
            "properties": {
                "jql": {"type": "string", "description": "JQL query string (e.g., 'project = PROJ AND status = Open')"},
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 50)",
                    "default": 50,
                },
            },
            "required": ["jql"],
        },
        function=internal_search_jira_issues_wrapper,
    )

    registry.register_tool(
        name="internal_add_jira_comment",
        description="Add a comment to a Jira issue. Use this to provide debugging analysis, root cause findings, or suggested fixes. Be clear and actionable in your comments.",
        parameters={
            "type": "object",
            "properties": {
                "issue_key": {"type": "string", "description": "Jira issue key (e.g., 'PROJ-123')"},
                "comment_text": {"type": "string", "description": "Comment text to add"},
            },
            "required": ["issue_key", "comment_text"],
        },
        function=internal_add_jira_comment_wrapper,
    )

    registry.register_tool(
        name="internal_update_jira_issue",
        description="Update a Jira issue fields like summary, description, priority, assignee, etc. Use this to update issue status or details after debugging.",
        parameters={
            "type": "object",
            "properties": {
                "issue_key": {"type": "string", "description": "Jira issue key (e.g., 'PROJ-123')"},
                "updates": {
                    "type": "object",
                    "description": "Dictionary of fields to update (e.g., {'summary': 'New title', 'priority': {'name': 'High'}})",
                },
            },
            "required": ["issue_key", "updates"],
        },
        function=internal_update_jira_issue_wrapper,
    )

    registry.register_tool(
        name="internal_transition_jira_issue",
        description="Transition a Jira issue to a different status (e.g., from 'Open' to 'In Progress' or 'Resolved'). Use this to update workflow status after completing work on an issue.",
        parameters={
            "type": "object",
            "properties": {
                "issue_key": {"type": "string", "description": "Jira issue key (e.g., 'PROJ-123')"},
                "transition_id": {
                    "type": "string",
                    "description": "Transition ID (use Jira API to find available transitions for the issue)",
                },
            },
            "required": ["issue_key", "transition_id"],
        },
        function=internal_transition_jira_issue_wrapper,
    )

    registry.register_tool(
        name="internal_get_jira_project",
        description="Get Jira project information including description, lead, and available issue types. Use this to understand project structure and conventions.",
        parameters={
            "type": "object",
            "properties": {"project_key": {"type": "string", "description": "Jira project key (e.g., 'PROJ')"}},
            "required": ["project_key"],
        },
        function=internal_get_jira_project_wrapper,
    )

    registry.register_tool(
        name="internal_create_jira_issue",
        description="Create a new Jira issue. Use this to create bugs, tasks, stories, or epics in a project.",
        parameters={
            "type": "object",
            "properties": {
                "project_key": {"type": "string", "description": "Jira project key (e.g., 'PROJ')"},
                "summary": {"type": "string", "description": "Issue summary/title"},
                "issue_type": {
                    "type": "string",
                    "description": "Issue type (e.g., 'Task', 'Bug', 'Story', 'Epic')",
                    "default": "Task",
                },
                "description": {"type": "string", "description": "Issue description (optional)"},
                "priority": {"type": "string", "description": "Priority name (e.g., 'High', 'Medium', 'Low')"},
                "assignee_account_id": {"type": "string", "description": "Assignee's Atlassian account ID"},
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of labels to add to the issue",
                },
            },
            "required": ["project_key", "summary"],
        },
        function=internal_create_jira_issue_wrapper,
    )

    registry.register_tool(
        name="internal_get_jira_boards",
        description="Get Jira boards (Scrum/Kanban boards) for a project. Use this to find board IDs for sprint management.",
        parameters={
            "type": "object",
            "properties": {
                "project_key": {"type": "string", "description": "Filter boards by project key (optional)"},
            },
            "required": [],
        },
        function=internal_get_jira_boards_wrapper,
    )

    registry.register_tool(
        name="internal_get_jira_sprints",
        description="Get sprints for a Jira board. Use this to find active, future, or closed sprints.",
        parameters={
            "type": "object",
            "properties": {
                "board_id": {"type": "integer", "description": "Board ID (get from internal_get_jira_boards)"},
                "state": {
                    "type": "string",
                    "description": "Filter by sprint state: 'active', 'closed', or 'future'",
                },
            },
            "required": ["board_id"],
        },
        function=internal_get_jira_sprints_wrapper,
    )

    registry.register_tool(
        name="internal_get_sprint_issues",
        description="Get all issues in a sprint with summary statistics. Shows issues grouped by status and assignee.",
        parameters={
            "type": "object",
            "properties": {
                "sprint_id": {"type": "integer", "description": "Sprint ID (get from internal_get_jira_sprints)"},
            },
            "required": ["sprint_id"],
        },
        function=internal_get_sprint_issues_wrapper,
    )

    registry.register_tool(
        name="internal_start_jira_sprint",
        description="Start a Jira sprint. Changes sprint state from 'future' to 'active'.",
        parameters={
            "type": "object",
            "properties": {
                "sprint_id": {"type": "integer", "description": "Sprint ID to start"},
                "start_date": {"type": "string", "description": "Sprint start date (ISO format, defaults to now)"},
                "end_date": {"type": "string", "description": "Sprint end date (ISO format)"},
            },
            "required": ["sprint_id"],
        },
        function=internal_start_jira_sprint_wrapper,
    )

    registry.register_tool(
        name="internal_close_jira_sprint",
        description="Close/complete a Jira sprint. Changes sprint state from 'active' to 'closed'.",
        parameters={
            "type": "object",
            "properties": {
                "sprint_id": {"type": "integer", "description": "Sprint ID to close"},
            },
            "required": ["sprint_id"],
        },
        function=internal_close_jira_sprint_wrapper,
    )

    registry.register_tool(
        name="internal_get_jira_users",
        description="Get users who can be assigned to issues in a project. Returns account IDs needed for assigning issues.",
        parameters={
            "type": "object",
            "properties": {
                "project_key": {"type": "string", "description": "Project key to get assignable users for"},
            },
            "required": ["project_key"],
        },
        function=internal_get_jira_users_wrapper,
    )

    logger.info("Registered 13 Jira tools")
