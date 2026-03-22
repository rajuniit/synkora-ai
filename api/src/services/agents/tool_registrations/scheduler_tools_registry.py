"""
Scheduler Tools Registry

Registers scheduler management tools with the ADK tool registry.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_scheduler_tools(registry):
    """
    Register all scheduler management tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.scheduler_tools import (
        internal_create_cron_scheduled_task,
        internal_create_scheduled_task,
        internal_delete_scheduled_task,
        internal_list_scheduled_tasks,
        internal_toggle_scheduled_task,
    )

    async def _extract_emails_from_message(runtime_context) -> list[str]:
        """Extract email addresses from the user's original message."""
        import re

        from sqlalchemy import select

        if not runtime_context or not runtime_context.message_id:
            logger.info("[scheduler] No message_id in runtime_context")
            return []
        try:
            from src.models.message import Message

            logger.info(f"[scheduler] Looking up message_id: {runtime_context.message_id}")
            result = await runtime_context.db_session.execute(
                select(Message).filter(Message.id == runtime_context.message_id)
            )
            message = result.scalar_one_or_none()
            if message and message.content:
                logger.info(f"[scheduler] Found message content: {message.content[:200]}...")
                # Extract all email addresses from the message
                email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
                emails = re.findall(email_pattern, message.content)
                logger.info(f"[scheduler] Extracted emails from message: {emails}")
                return emails
            else:
                logger.info("[scheduler] Message not found or empty content")
        except Exception as e:
            logger.warning(f"[scheduler] Failed to extract emails from message: {e}")
        return []

    def _fix_redacted_values(task_config: dict, emails: list[str]) -> dict:
        """Replace [EMAIL_REDACTED] placeholders with actual emails from user message."""
        logger.info(f"[scheduler] task_config BEFORE fix: {task_config}")
        logger.info(f"[scheduler] Available emails to substitute: {emails}")

        if not emails:
            logger.info("[scheduler] No emails to substitute, returning unchanged")
            return task_config

        email_index = 0
        for key, value in task_config.items():
            if isinstance(value, str) and "[EMAIL_REDACTED]" in value:
                if email_index < len(emails):
                    logger.info(f"[scheduler] Replacing {key}: '{value}' -> '{emails[email_index]}'")
                    task_config[key] = emails[email_index]
                    email_index += 1
            elif value == "[EMAIL_REDACTED]" and email_index < len(emails):
                logger.info(f"[scheduler] Replacing {key}: '{value}' -> '{emails[email_index]}'")
                task_config[key] = emails[email_index]
                email_index += 1

        logger.info(f"[scheduler] task_config AFTER fix: {task_config}")
        return task_config

    # Scheduler tools - create wrappers that inject runtime_context
    async def internal_create_scheduled_task_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        account_id = str(runtime_context.user_id) if runtime_context and runtime_context.user_id else None

        # Build task config - agent_id auto-injected, everything else comes from agent
        task_config = kwargs.get("task_config", {})
        if runtime_context and runtime_context.agent_id:
            task_config["agent_id"] = str(runtime_context.agent_id)
        if kwargs.get("prompt"):
            task_config["prompt"] = kwargs.get("prompt")

        emails = await _extract_emails_from_message(runtime_context)
        task_config = _fix_redacted_values(task_config, emails)

        return await internal_create_scheduled_task(
            db=runtime_context.db_session if runtime_context else None,
            tenant_id=str(runtime_context.tenant_id) if runtime_context else None,
            name=kwargs.get("name"),
            task_type=kwargs.get("task_type"),
            interval_seconds=kwargs.get("interval_seconds"),
            config=task_config,
            description=kwargs.get("description"),
            is_active=kwargs.get("is_active", True),
            account_id=account_id,
        )

    async def _get_tenant_timezone(runtime_context) -> str:
        """Fetch the tenant's configured timezone from the database."""
        if not runtime_context or not runtime_context.tenant_id:
            return "UTC"
        try:
            from sqlalchemy import select

            from src.models.tenant import Tenant

            result = await runtime_context.db_session.execute(
                select(Tenant.timezone).filter(Tenant.id == runtime_context.tenant_id)
            )
            tz = result.scalar_one_or_none()
            return tz if tz else "UTC"
        except Exception as e:
            logger.warning(f"[scheduler] Failed to fetch tenant timezone: {e}")
            return "UTC"

    def _convert_cron_to_utc(cron_expression: str, user_timezone: str) -> str:
        """
        Convert a cron expression written in the user's local timezone to UTC.
        Only converts simple cases (specific hour:minute integers, no wildcards).
        Returns the original expression unchanged if conversion is not safe.
        """
        if not user_timezone or user_timezone in ("UTC", "utc"):
            return cron_expression

        parts = cron_expression.strip().split()
        if len(parts) != 5:
            return cron_expression

        minute_part, hour_part, dom, month, dow = parts

        # Only convert when both minute and hour are plain integers
        if not minute_part.isdigit() or not hour_part.isdigit():
            logger.info(f"[scheduler] Skipping cron timezone conversion for complex expression: {cron_expression}")
            return cron_expression

        try:
            from datetime import datetime as dt
            from zoneinfo import ZoneInfo

            tz = ZoneInfo(user_timezone)
            utc_tz = ZoneInfo("UTC")

            # Build a reference local datetime at the cron's hour/minute
            local_ref = dt.now(tz).replace(hour=int(hour_part), minute=int(minute_part), second=0, microsecond=0)
            utc_ref = local_ref.astimezone(utc_tz)

            utc_minute = utc_ref.minute
            utc_hour = utc_ref.hour

            # Handle day rollover for day-of-week patterns
            if dow != "*" and utc_ref.date() != local_ref.date():
                day_diff = (utc_ref.date() - local_ref.date()).days
                new_dow_parts = []
                for part in dow.split(","):
                    if part.isdigit():
                        new_dow_parts.append(str((int(part) + day_diff) % 7))
                    else:
                        new_dow_parts.append(part)
                dow = ",".join(new_dow_parts)

            converted = f"{utc_minute} {utc_hour} {dom} {month} {dow}"
            logger.info(f"[scheduler] Converted cron '{cron_expression}' from {user_timezone} to UTC: '{converted}'")
            return converted

        except Exception as e:
            logger.warning(f"[scheduler] Cron timezone conversion failed: {e}, using original expression")
            return cron_expression

    async def internal_create_cron_scheduled_task_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        account_id = str(runtime_context.user_id) if runtime_context and runtime_context.user_id else None

        # Build task config - agent_id auto-injected, everything else comes from agent
        task_config = kwargs.get("task_config", {})
        if runtime_context and runtime_context.agent_id:
            task_config["agent_id"] = str(runtime_context.agent_id)
        if kwargs.get("prompt"):
            task_config["prompt"] = kwargs.get("prompt")

        emails = await _extract_emails_from_message(runtime_context)
        task_config = _fix_redacted_values(task_config, emails)

        # Resolve timezone: agent-provided in task_config > tenant setting > UTC
        user_timezone = task_config.pop("timezone", None)
        if not user_timezone:
            user_timezone = await _get_tenant_timezone(runtime_context)
            logger.info(f"[scheduler] Using tenant timezone: {user_timezone}")

        # Convert cron expression from user's timezone to UTC
        cron_expression = kwargs.get("cron_expression", "")
        utc_cron = _convert_cron_to_utc(cron_expression, user_timezone)

        # Store original timezone and cron in config for display/debugging
        task_config["user_timezone"] = user_timezone
        task_config["original_cron"] = cron_expression

        return await internal_create_cron_scheduled_task(
            db=runtime_context.db_session if runtime_context else None,
            tenant_id=str(runtime_context.tenant_id) if runtime_context else None,
            name=kwargs.get("name"),
            task_type=kwargs.get("task_type", "agent_task"),
            cron_expression=utc_cron,
            config=task_config,
            description=kwargs.get("description"),
            is_active=kwargs.get("is_active", True),
            account_id=account_id,
        )

    async def internal_list_scheduled_tasks_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_list_scheduled_tasks(
            db=runtime_context.db_session if runtime_context else None,
            tenant_id=str(runtime_context.tenant_id) if runtime_context else None,
        )

    async def internal_delete_scheduled_task_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_delete_scheduled_task(
            db=runtime_context.db_session if runtime_context else None, task_id=kwargs.get("task_id")
        )

    async def internal_toggle_scheduled_task_wrapper(config: dict[str, Any] | None = None, **kwargs):
        runtime_context = config.get("_runtime_context") if config else None
        return await internal_toggle_scheduled_task(
            db=runtime_context.db_session if runtime_context else None, task_id=kwargs.get("task_id")
        )

    # Register scheduler tools
    registry.register_tool(
        name="internal_create_scheduled_task",
        description=(
            "Create a scheduled task that runs at regular intervals. "
            "The current agent will execute the prompt when the task runs. "
            "Use this for recurring automations like hourly checks or daily reports."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the scheduled task"},
                "task_type": {
                    "type": "string",
                    "description": "Type of task. Use 'agent_task' for tasks that this agent should execute.",
                    "default": "agent_task",
                },
                "interval_seconds": {
                    "type": "integer",
                    "description": "Interval in seconds between task executions. Minimum 60 seconds. Examples: 60 (every 1 minute), 300 (every 5 minutes), 3600 (every hour), 86400 (every day)",
                },
                "prompt": {
                    "type": "string",
                    "description": "The instructions/prompt for the agent to execute when this scheduled task runs. Be specific about what the agent should do.",
                },
                "task_config": {
                    "type": "object",
                    "description": "Store any data needed when the task runs. IMPORTANT: Use actual values provided by the user (real email addresses, real folder IDs, etc.) - do NOT use placeholders like [EMAIL_REDACTED]. This config will be passed to the agent when the task executes.",
                    "default": {},
                },
                "description": {
                    "type": "string",
                    "description": "Optional human-readable description of what the task does",
                },
                "is_active": {"type": "boolean", "description": "Whether the task should be active", "default": True},
            },
            "required": ["name", "interval_seconds", "prompt"],
        },
        function=internal_create_scheduled_task_wrapper,
    )

    registry.register_tool(
        name="internal_create_cron_scheduled_task",
        description=(
            "Create a scheduled task that runs at specific times using cron expressions. "
            "Use this for tasks that need to run at exact times like '7 AM daily' or 'every Monday at 9 AM'. "
            "The current agent will execute the prompt when the task runs.\n\n"
            "TIMEZONE RULES (IMPORTANT):\n"
            "1. Always write the cron expression in the USER'S LOCAL TIME, not UTC. "
            "The system will automatically convert it to UTC.\n"
            "2. You MUST include a 'timezone' field in task_config with a valid IANA timezone name "
            "(e.g., 'America/New_York', 'Asia/Kolkata', 'Europe/London', 'Asia/Tokyo').\n"
            "3. If the user has NOT mentioned their timezone in this conversation, "
            "ASK them before calling this tool: 'What timezone are you in? "
            "(e.g., America/New_York, Asia/Kolkata, Europe/London)'\n"
            "4. Never assume UTC unless the user explicitly says so."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the scheduled task"},
                "cron_expression": {
                    "type": "string",
                    "description": (
                        "Cron expression in the USER'S LOCAL TIME (not UTC — the system converts automatically). "
                        "Format: 'minute hour day-of-month month day-of-week'. "
                        "Examples: '0 7 * * *' (daily at 7 AM local), '0 9 * * 1-5' (weekdays at 9 AM local), "
                        "'30 8 * * *' (daily at 8:30 AM local), '0 0 * * 0' (Sundays at midnight local)"
                    ),
                },
                "prompt": {
                    "type": "string",
                    "description": "The instructions/prompt for the agent to execute when this scheduled task runs. Be specific about what the agent should do.",
                },
                "task_config": {
                    "type": "object",
                    "description": (
                        "Store any data needed when the task runs. "
                        "MUST include 'timezone' with the user's IANA timezone (e.g., 'Asia/Kolkata'). "
                        "IMPORTANT: Use actual values provided by the user (real email addresses, etc.) "
                        "- do NOT use placeholders like [EMAIL_REDACTED]."
                    ),
                    "default": {},
                },
                "description": {
                    "type": "string",
                    "description": "Optional human-readable description of what the task does",
                },
                "is_active": {"type": "boolean", "description": "Whether the task should be active", "default": True},
            },
            "required": ["name", "cron_expression", "prompt"],
        },
        function=internal_create_cron_scheduled_task_wrapper,
    )

    registry.register_tool(
        name="internal_list_scheduled_tasks",
        description="List all scheduled tasks. Use this to see what tasks are currently scheduled and their status.",
        parameters={"type": "object", "properties": {}, "required": []},
        function=internal_list_scheduled_tasks_wrapper,
    )

    registry.register_tool(
        name="internal_delete_scheduled_task",
        description="Delete a scheduled task. Use this to remove tasks that are no longer needed.",
        parameters={
            "type": "object",
            "properties": {"task_id": {"type": "string", "description": "UUID of the task to delete"}},
            "required": ["task_id"],
        },
        function=internal_delete_scheduled_task_wrapper,
    )

    registry.register_tool(
        name="internal_toggle_scheduled_task",
        description="Toggle a scheduled task's active status. Use this to temporarily pause or resume a task.",
        parameters={
            "type": "object",
            "properties": {"task_id": {"type": "string", "description": "UUID of the task to toggle"}},
            "required": ["task_id"],
        },
        function=internal_toggle_scheduled_task_wrapper,
    )

    logger.info("Registered 5 scheduler management tools")
