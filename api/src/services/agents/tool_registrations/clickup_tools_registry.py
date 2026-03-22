"""
ClickUp Tools Registry

Registers all ClickUp-related tools with the ADK tool registry.
This modular approach keeps tool registration organized and maintainable.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_clickup_tools(registry):
    """
    Register all ClickUp tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.clickup_tools import (
        internal_add_clickup_comment,
        internal_create_clickup_task,
        internal_get_clickup_folders,
        internal_get_clickup_list_summary,
        internal_get_clickup_lists,
        internal_get_clickup_members,
        internal_get_clickup_spaces,
        internal_get_clickup_task,
        internal_get_clickup_workspace,
        internal_search_clickup_tasks,
        internal_update_clickup_task,
    )

    # ClickUp tools - create wrappers that inject runtime_context
    async def internal_get_clickup_task_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_clickup_task(
            task_id=kwargs.get("task_id"), runtime_context=runtime_context, config=config
        )

    async def internal_search_clickup_tasks_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_search_clickup_tasks(
            list_id=kwargs.get("list_id"),
            query=kwargs.get("query"),
            status=kwargs.get("status"),
            assignees=kwargs.get("assignees"),
            tags=kwargs.get("tags"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_add_clickup_comment_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_add_clickup_comment(
            task_id=kwargs.get("task_id"),
            comment_text=kwargs.get("comment_text"),
            notify_all=kwargs.get("notify_all", False),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_update_clickup_task_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_update_clickup_task(
            task_id=kwargs.get("task_id"), updates=kwargs.get("updates"), runtime_context=runtime_context, config=config
        )

    async def internal_get_clickup_workspace_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_clickup_workspace(runtime_context=runtime_context, config=config)

    async def internal_get_clickup_spaces_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_clickup_spaces(
            team_id=kwargs.get("team_id"), runtime_context=runtime_context, config=config
        )

    async def internal_get_clickup_folders_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_clickup_folders(
            space_id=kwargs.get("space_id"), runtime_context=runtime_context, config=config
        )

    async def internal_get_clickup_lists_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_clickup_lists(
            folder_id=kwargs.get("folder_id"),
            space_id=kwargs.get("space_id"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_create_clickup_task_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_create_clickup_task(
            list_id=kwargs.get("list_id"),
            name=kwargs.get("name"),
            description=kwargs.get("description"),
            status=kwargs.get("status"),
            priority=kwargs.get("priority"),
            assignees=kwargs.get("assignees"),
            tags=kwargs.get("tags"),
            due_date=kwargs.get("due_date"),
            runtime_context=runtime_context,
            config=config,
        )

    async def internal_get_clickup_members_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_clickup_members(
            team_id=kwargs.get("team_id"), runtime_context=runtime_context, config=config
        )

    async def internal_get_clickup_list_summary_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_get_clickup_list_summary(
            list_id=kwargs.get("list_id"), runtime_context=runtime_context, config=config
        )

    # Register all ClickUp tools
    registry.register_tool(
        name="internal_get_clickup_task",
        description="Get detailed information about a ClickUp task including description, status, assignees, comments, and attachments. Use this to understand the context of a reported issue or task.",
        parameters={
            "type": "object",
            "properties": {"task_id": {"type": "string", "description": "ClickUp task ID"}},
            "required": ["task_id"],
        },
        function=internal_get_clickup_task_wrapper,
    )

    registry.register_tool(
        name="internal_search_clickup_tasks",
        description="Search for ClickUp tasks in a list with optional filters for status, assignees, and tags. Use this to find related issues or tasks matching specific criteria.",
        parameters={
            "type": "object",
            "properties": {
                "list_id": {"type": "string", "description": "ClickUp list ID to search in"},
                "query": {"type": "string", "description": "Search query text (optional)"},
                "status": {"type": "array", "items": {"type": "string"}, "description": "Filter by status (optional)"},
                "assignees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by assignee user IDs (optional)",
                },
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags (optional)"},
            },
            "required": ["list_id"],
        },
        function=internal_search_clickup_tasks_wrapper,
    )

    registry.register_tool(
        name="internal_add_clickup_comment",
        description="Add a comment to a ClickUp task. Use this to provide analysis, debugging insights, or updates on issues. Be clear and actionable in your comments.",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "ClickUp task ID"},
                "comment_text": {"type": "string", "description": "Comment text to add"},
                "notify_all": {
                    "type": "boolean",
                    "description": "Whether to notify all task watchers (default: false)",
                    "default": False,
                },
            },
            "required": ["task_id", "comment_text"],
        },
        function=internal_add_clickup_comment_wrapper,
    )

    registry.register_tool(
        name="internal_update_clickup_task",
        description="Update a ClickUp task properties like name, description, status, priority, etc. Use this to update task status after debugging or to reflect current state.",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "ClickUp task ID"},
                "updates": {
                    "type": "object",
                    "description": "Dictionary of fields to update (e.g., {'status': 'in progress', 'priority': 1})",
                },
            },
            "required": ["task_id", "updates"],
        },
        function=internal_update_clickup_task_wrapper,
    )

    registry.register_tool(
        name="internal_get_clickup_workspace",
        description="Get ClickUp workspace (team) information. Use this to understand the organizational structure and available teams. Returns team IDs needed for other operations.",
        parameters={"type": "object", "properties": {}, "required": []},
        function=internal_get_clickup_workspace_wrapper,
    )

    registry.register_tool(
        name="internal_get_clickup_spaces",
        description="Get all spaces in a ClickUp workspace/team. Spaces contain folders and lists. Use this to navigate the workspace hierarchy.",
        parameters={
            "type": "object",
            "properties": {
                "team_id": {
                    "type": "string",
                    "description": "ClickUp team/workspace ID (get from internal_get_clickup_workspace)",
                },
            },
            "required": ["team_id"],
        },
        function=internal_get_clickup_spaces_wrapper,
    )

    registry.register_tool(
        name="internal_get_clickup_folders",
        description="Get all folders in a ClickUp space. Folders contain lists. Use this to find folders before getting lists.",
        parameters={
            "type": "object",
            "properties": {
                "space_id": {
                    "type": "string",
                    "description": "ClickUp space ID (get from internal_get_clickup_spaces)",
                },
            },
            "required": ["space_id"],
        },
        function=internal_get_clickup_folders_wrapper,
    )

    registry.register_tool(
        name="internal_get_clickup_lists",
        description="Get lists from a ClickUp folder or space (folderless lists). Lists contain tasks. Use this to get list IDs for creating tasks or searching.",
        parameters={
            "type": "object",
            "properties": {
                "folder_id": {"type": "string", "description": "ClickUp folder ID (for lists in a folder)"},
                "space_id": {
                    "type": "string",
                    "description": "ClickUp space ID (for folderless lists directly in a space)",
                },
            },
            "required": [],
        },
        function=internal_get_clickup_lists_wrapper,
    )

    registry.register_tool(
        name="internal_create_clickup_task",
        description="Create a new task in a ClickUp list. Use this to create new tasks, bugs, or issues.",
        parameters={
            "type": "object",
            "properties": {
                "list_id": {"type": "string", "description": "ClickUp list ID to create the task in"},
                "name": {"type": "string", "description": "Task name/title"},
                "description": {"type": "string", "description": "Task description (optional)"},
                "status": {
                    "type": "string",
                    "description": "Task status (optional, uses list default if not specified)",
                },
                "priority": {
                    "type": "integer",
                    "description": "Priority level 1-4 (1=Urgent, 2=High, 3=Normal, 4=Low) (optional)",
                },
                "assignees": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of user IDs to assign (optional)",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tag names (optional)",
                },
                "due_date": {
                    "type": "integer",
                    "description": "Due date as Unix timestamp in milliseconds (optional)",
                },
            },
            "required": ["list_id", "name"],
        },
        function=internal_create_clickup_task_wrapper,
    )

    registry.register_tool(
        name="internal_get_clickup_members",
        description="Get all members in a ClickUp workspace/team. Returns user IDs needed for assigning tasks.",
        parameters={
            "type": "object",
            "properties": {
                "team_id": {
                    "type": "string",
                    "description": "ClickUp team/workspace ID (get from internal_get_clickup_workspace)",
                },
            },
            "required": ["team_id"],
        },
        function=internal_get_clickup_members_wrapper,
    )

    registry.register_tool(
        name="internal_get_clickup_list_summary",
        description="Get a summary of a ClickUp list with task counts by status and assignee. Use this for sprint/list status reports and workload analysis.",
        parameters={
            "type": "object",
            "properties": {
                "list_id": {"type": "string", "description": "ClickUp list ID"},
            },
            "required": ["list_id"],
        },
        function=internal_get_clickup_list_summary_wrapper,
    )

    logger.info("Registered 11 ClickUp tools")
