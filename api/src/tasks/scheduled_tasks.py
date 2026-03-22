"""
Scheduled tasks for executing database queries and generating charts
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from src.celery_app import celery_app
from src.core.database import get_db
from src.models.database_connection import DatabaseConnection, DatabaseConnectionType
from src.models.scheduled_task import ScheduledTask, TaskExecution, TaskStatus
from src.services.charts import ChartService
from src.services.database import ElasticsearchConnector, PostgreSQLConnector
from src.tasks.followup_reminder_task import execute_followup_reminder

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="tasks.execute_scheduled_task")
def execute_scheduled_task(self, task_id: str) -> dict[str, Any]:
    """
    Execute a scheduled task

    Args:
        task_id: ID of the scheduled task to execute (UUID as string)

    Returns:
        Dict containing execution results
    """
    db: Session = next(get_db())

    try:
        # Get the scheduled task
        task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
        if not task:
            raise ValueError(f"Scheduled task {task_id} not found")

        if not task.is_active:
            logger.info(f"Task {task_id} is not active, skipping execution")
            return {"status": "skipped", "reason": "Task is not active"}

        # Create execution record
        execution = TaskExecution(task_id=task_id, status=TaskStatus.RUNNING, started_at=datetime.now(UTC))
        db.add(execution)
        db.commit()

        try:
            # Handle followup reminder tasks
            if task.task_type == "followup_reminder":
                # Get agent_id from task config
                agent_id = task.config.get("agent_id")
                if not agent_id:
                    raise ValueError("agent_id not found in task config")

                result = execute_followup_reminder(
                    task_id=str(task.id), tenant_id=str(task.tenant_id), agent_id=str(agent_id), task_config=task.config
                )

                # Update execution status
                if result.get("success"):
                    execution.status = TaskStatus.SUCCESS
                    execution.result = result

                    # Check if task should be disabled
                    if result.get("should_disable_task"):
                        task.is_active = False
                else:
                    execution.status = TaskStatus.FAILED
                    execution.error_message = result.get("error", "Unknown error")

                execution.completed_at = datetime.now(UTC)
                task.last_run_at = datetime.now(UTC)

                db.commit()

                logger.info(f"Successfully executed followup reminder task {task_id}")
                return result

            # Handle generic agent tasks (no database connection required)
            if task.task_type == "agent_task":
                # Get agent_id and prompt from task config
                agent_id = task.config.get("agent_id")
                task_prompt = task.config.get("prompt") or task.config.get("task_description") or task.description

                if not agent_id:
                    logger.error(f"agent_id not found in task config for task {task_id} — deactivating task")
                    task.is_active = False
                    execution.status = TaskStatus.FAILED
                    execution.error_message = "agent_id not found in task config — task deactivated"
                    execution.completed_at = datetime.now(UTC)
                    task.last_run_at = datetime.now(UTC)
                    db.commit()
                    return {"status": "failed", "reason": "agent_id not found in task config — task deactivated"}

                if not task_prompt:
                    raise ValueError("prompt or task_description not found in task config")

                # Import required services
                from src.models.agent import Agent
                from src.services.agents.agent_loader_service import AgentLoaderService
                from src.services.agents.agent_manager import AgentManager
                from src.services.agents.chat_service import ChatService
                from src.services.agents.chat_stream_service import ChatStreamService

                # Load agent from DB — scope to task's tenant to prevent cross-tenant access
                agent = (
                    db.query(Agent)
                    .filter(Agent.id == agent_id, Agent.tenant_id == task.tenant_id)
                    .first()
                )
                if not agent:
                    logger.error(f"Agent {agent_id} not found for task {task_id} (tenant {task.tenant_id}) — deactivating task")
                    task.is_active = False
                    execution.status = TaskStatus.FAILED
                    execution.error_message = f"Agent {agent_id} not found — task deactivated"
                    execution.completed_at = datetime.now(UTC)
                    task.last_run_at = datetime.now(UTC)
                    db.commit()
                    return {"status": "failed", "reason": f"Agent {agent_id} not found — task deactivated"}

                logger.info(f"🚀 Executing scheduled agent task '{task.name}' with agent '{agent.agent_name}'")

                # Get task creator's email (for tasks that need to send emails to the user)
                creator_email = None
                if task.created_by:
                    from src.models.tenant import Account

                    creator = db.query(Account).filter(Account.id == task.created_by).first()
                    if creator:
                        creator_email = creator.email

                # Create chat stream service
                agent_manager = AgentManager()
                agent_loader = AgentLoaderService(agent_manager)
                chat_service = ChatService()
                chat_stream_service = ChatStreamService(
                    agent_loader=agent_loader,
                    chat_service=chat_service,
                )

                # Build task config context (exclude internal fields like agent_id, prompt)
                # Also replace any [EMAIL_REDACTED] placeholders with the actual creator email
                config_context = ""
                context_items: dict = {}
                if task.config:
                    context_items = {
                        k: v for k, v in task.config.items() if k not in ("agent_id", "prompt", "task_description")
                    }
                    # Replace redacted email placeholders with actual creator email
                    if creator_email:
                        for key, value in context_items.items():
                            if isinstance(value, str) and "[EMAIL_REDACTED]" in value:
                                context_items[key] = creator_email
                            elif value == "[EMAIL_REDACTED]":
                                context_items[key] = creator_email

                    if context_items:
                        import json as json_module

                        config_context = (
                            f"\n\n## Task Configuration\n```json\n{json_module.dumps(context_items, indent=2)}\n```"
                        )

                # Add creator email to context if available (as fallback)
                creator_context = ""
                if creator_email:
                    creator_context = f"\n\n## Task Creator\nThis task was created by: {creator_email}\nIf you need to send emails or notifications, use this email address."

                # Build the prompt with context
                full_prompt = f"""## Scheduled Task: {task.name}
{config_context}
{creator_context}

{task_prompt}

This is an automated scheduled task. Complete it thoroughly and provide your findings."""

                # Collect response chunks
                response_chunks = []

                async def process_agent():
                    """Stream agent response and collect chunks."""
                    import json as json_module

                    from src.core.database import create_celery_async_session, reset_async_engine

                    reset_async_engine()

                    # Pass task_config in shared_state for tools to resolve redacted values
                    task_shared_state = {
                        "task_config": context_items if context_items else {},
                        "captured_email": {},
                    }

                    async_session_factory = create_celery_async_session()
                    async with async_session_factory() as async_db:
                        async for sse_event in chat_stream_service.stream_agent_response(
                            agent_name=agent.agent_name,
                            message=full_prompt,
                            conversation_history=None,
                            conversation_id=None,
                            attachments=None,
                            llm_config_id=None,
                            db=async_db,
                            shared_state=task_shared_state,
                        ):
                            # Parse SSE events
                            if sse_event.startswith("data: "):
                                try:
                                    event_data = json_module.loads(sse_event[6:])
                                    if event_data.get("type") == "chunk":
                                        response_chunks.append(event_data.get("content", ""))
                                except json_module.JSONDecodeError:
                                    pass

                # Execute async agent call
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(process_agent())
                loop.close()

                response_text = "".join(response_chunks)

                # Dispatch to agent subscribers
                if agent_id and agent.allow_subscriptions:
                    from src.config.settings import settings
                    from src.models.agent_subscription import AgentSubscription
                    from src.tasks.email_tasks import send_email_task

                    subs = (
                        db.query(AgentSubscription)
                        .filter(
                            AgentSubscription.agent_id == agent_id,
                            AgentSubscription.is_active == True,  # noqa: E712
                        )
                        .limit(1000)
                        .all()
                    )
                    if subs:
                        base_url = settings.webhook_base_url or f"http://{settings.api_host}:{settings.api_port}"
                        task_date = datetime.now(UTC).strftime("%B %d, %Y")

                        # Use the actual email the agent sent; fall back to response_text if agent didn't send one
                        captured = task_shared_state.get("captured_email", {})
                        if captured.get("html_body"):
                            email_subject = captured.get("subject") or f"[{task.name}] {task_date}"
                            raw_content_html = captured["html_body"]
                        else:
                            import markdown as md_lib

                            email_subject = f"[{task.name}] {task_date}"
                            raw_content_html = md_lib.markdown(
                                response_text,
                                extensions=["tables", "fenced_code", "nl2br"],
                            )

                        for sub in subs:
                            unsubscribe_url = f"{base_url}/unsubscribe?token={sub.unsubscribe_token}"
                            unsubscribe_footer = (
                                f'<p style="font-size:11px;color:#9ca3af;text-align:center;margin:16px 0 0">'
                                f"You're receiving this because you subscribed to <strong>{task.name}</strong> reports."
                                f'&nbsp;<a href="{unsubscribe_url}" style="color:#9ca3af">Unsubscribe</a></p>'
                            )
                            send_email_task.delay(
                                tenant_id=str(task.tenant_id),
                                to_email=sub.email,
                                subject=email_subject,
                                html_body=raw_content_html + unsubscribe_footer,
                            )
                        logger.info(f"Dispatched report to {len(subs)} subscriber(s) for agent {agent_id}")

                result = {
                    "status": "success",
                    "task_id": str(task.id),
                    "task_name": task.name,
                    "agent_name": agent.agent_name,
                    "executed_at": datetime.now(UTC).isoformat(),
                    "response_preview": response_text[:500] if response_text else None,
                    "has_response": bool(response_text),
                }

                # Execute webhook callback if configured
                callback_url = task.config.get("callback_url")
                callback_data = task.config.get("callback_data", {})
                if callback_url:
                    try:
                        import httpx

                        from src.services.agents.internal_tools.web_tools import _is_url_safe

                        is_safe, ssrf_error = _is_url_safe(callback_url)
                        if not is_safe:
                            logger.warning(f"Callback URL blocked for task {task_id}: {ssrf_error}")
                            result["callback_error"] = f"Callback URL blocked: {ssrf_error}"
                        else:
                            with httpx.Client(timeout=30.0, follow_redirects=False) as client:
                                response = client.post(
                                    callback_url,
                                    json={
                                        "task_id": str(task.id),
                                        "task_name": task.name,
                                        "tenant_id": str(task.tenant_id),
                                        "executed_at": datetime.now(UTC).isoformat(),
                                        "agent_response": response_text,
                                        **callback_data,
                                    },
                                )
                                result["callback_status"] = response.status_code
                                result["callback_response"] = response.text[:500] if response.text else None
                    except Exception as callback_error:
                        logger.warning(f"Callback failed for task {task_id}: {str(callback_error)}")
                        result["callback_error"] = str(callback_error)

                execution.status = TaskStatus.SUCCESS
                execution.result = result
                execution.completed_at = datetime.now(UTC)
                execution.execution_time_seconds = (execution.completed_at - execution.started_at).total_seconds()
                task.last_run_at = datetime.now(UTC)

                db.commit()

                if response_text:
                    logger.info(
                        f"✅ Successfully executed agent task {task_id}: {task.name} - Response: {response_text[:100]}..."
                    )
                else:
                    logger.info(f"🔧 Agent task {task_id} completed (agent used tools, no text response)")

                return result

            # Handle database query tasks
            # Ensure we have a database connection for non-followup tasks
            if not task.database_connection_id:
                raise ValueError(f"database_connection_id is required for task type {task.task_type}")

            # Get the database connection — scope to task's tenant to prevent cross-tenant access
            connection = (
                db.query(DatabaseConnection)
                .filter(
                    DatabaseConnection.id == task.database_connection_id,
                    DatabaseConnection.tenant_id == task.tenant_id,
                )
                .first()
            )

            if not connection:
                raise ValueError(f"Database connection {task.database_connection_id} not found")

            # Create appropriate connector based on type
            if connection.type == DatabaseConnectionType.POSTGRESQL:
                connector = PostgreSQLConnector(connection)
            elif connection.type == DatabaseConnectionType.ELASTICSEARCH:
                connector = ElasticsearchConnector(connection)
            else:
                raise ValueError(f"Unsupported database type: {connection.type}")

            # Execute the query using asyncio
            async def execute_async():
                await connector.connect()
                result = await connector.execute_query(task.query)
                await connector.disconnect()
                return result

            query_result = asyncio.run(execute_async())

            # Calculate rows affected
            rows_affected = len(query_result.get("rows", []))

            # Generate chart if configured (chart config is in task.config)
            chart_data = None
            chart_config = task.config.get("chart_config") if task.config else None
            if chart_config:
                chart_service = ChartService(db)
                chart_data = chart_service.generate_chart(data=query_result.get("rows", []), chart_config=chart_config)

            # Store results in the JSONB result column
            execution.result = {
                "query_result": query_result,
                "rows_affected": rows_affected,
                "chart_data": chart_data,
            }

            # Update execution status
            execution.status = TaskStatus.SUCCESS
            execution.completed_at = datetime.now(UTC)
            execution.execution_time_seconds = (execution.completed_at - execution.started_at).total_seconds()

            # Update task last run
            task.last_run_at = datetime.now(UTC)

            db.commit()

            logger.info(f"Successfully executed task {task_id}")

            return {
                "status": "success",
                "execution_id": str(execution.id),
                "rows_affected": rows_affected,
                "has_chart": chart_data is not None,
            }

        except Exception as e:
            # Update execution with error
            execution.status = TaskStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now(UTC)

            # Update task last run
            task.last_run_at = datetime.now(UTC)

            db.commit()

            logger.error(f"Failed to execute task {task_id}: {str(e)}")
            raise

    except Exception as e:
        logger.error(f"Error executing scheduled task {task_id}: {str(e)}")
        raise
    finally:
        db.close()


# Number of scheduled tasks to load per batch during the due-check sweep.
# Keeps peak memory bounded regardless of total active task count.
_CHECK_BATCH_SIZE = 500


@celery_app.task(name="tasks.check_scheduled_tasks")
def check_scheduled_tasks() -> dict[str, Any]:
    """
    Check for due scheduled tasks and queue them for execution.
    This task runs every minute via Celery Beat.

    Processes tasks in batches of _CHECK_BATCH_SIZE (ordered by id for stable
    pagination) so memory usage stays constant even with 10k+ active tasks.

    Returns:
        Dict containing results of the check
    """
    db: Session = next(get_db())

    try:
        now = datetime.now(UTC)
        queued_count = 0
        total_due = 0
        offset = 0

        while True:
            # Fetch one page of active tasks ordered by a stable PK column so
            # OFFSET pagination is consistent across loop iterations.
            tasks = (
                db.query(ScheduledTask)
                .filter(ScheduledTask.is_active == True)  # noqa: E712
                .order_by(ScheduledTask.id)
                .limit(_CHECK_BATCH_SIZE)
                .offset(offset)
                .all()
            )

            if not tasks:
                break

            for task in tasks:
                try:
                    if _is_task_due_sync(task, now):
                        total_due += 1
                        execute_scheduled_task.delay(str(task.id))
                        # Update last_run_at immediately to prevent a second
                        # beat tick from re-queuing the same task this minute.
                        task.last_run_at = datetime.now(UTC)
                        queued_count += 1
                        logger.info(f"Queued scheduled task {task.id} ({task.name}) for execution")
                except Exception as e:
                    logger.error(f"Error processing task {task.id}: {str(e)}")

            # Commit after each batch so the last_run_at updates are durable
            # before we move on — avoids a large pending write set.
            db.commit()

            if len(tasks) < _CHECK_BATCH_SIZE:
                # Last (partial) page — no more rows to fetch.
                break

            offset += _CHECK_BATCH_SIZE

        logger.info(f"Checked scheduled tasks: {total_due} due, {queued_count} queued")

        return {
            "status": "success",
            "due_tasks": total_due,
            "queued_tasks": queued_count,
        }
    except Exception as e:
        logger.error(f"Error checking scheduled tasks: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def _is_task_due_sync(task: ScheduledTask, now: datetime) -> bool:
    """
    Check if a task is due to run based on interval or cron scheduling.
    Synchronous version for celery tasks.
    """
    from croniter import croniter

    # Make now timezone-aware if not already
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    # Make last_run_at timezone-aware for comparison
    last_run = task.last_run_at
    if last_run and last_run.tzinfo is None:
        last_run = last_run.replace(tzinfo=UTC)

    # If task has a cron schedule
    if task.cron_expression:
        try:
            # If task has never run, it's due
            if last_run is None:
                return True

            # Compute next scheduled run AFTER last_run (same logic as SchedulerService._is_cron_task_due)
            cron = croniter(task.cron_expression, last_run)
            next_scheduled = cron.get_next(datetime)
            if next_scheduled.tzinfo is None:
                next_scheduled = next_scheduled.replace(tzinfo=UTC)

            return next_scheduled <= now
        except Exception as e:
            logger.error(f"Error parsing cron schedule '{task.cron_expression}': {e}")
            return False

    # If task has an interval (in seconds)
    if task.interval_seconds and task.interval_seconds > 0:
        if last_run is None:
            return True
        elapsed = (now - last_run).total_seconds()
        return elapsed >= task.interval_seconds

    return False


@celery_app.task(name="tasks.cleanup_old_executions")
def cleanup_old_executions(days: int = 30) -> dict[str, Any]:
    """
    Clean up old task executions

    Args:
        days: Number of days to keep executions

    Returns:
        Dict containing cleanup results
    """
    db: Session = next(get_db())

    try:
        from datetime import timedelta

        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        # Delete old executions
        deleted_count = db.query(TaskExecution).filter(TaskExecution.completed_at < cutoff_date).delete()

        db.commit()

        logger.info(f"Cleaned up {deleted_count} old task executions")

        return {"status": "success", "deleted_count": deleted_count}

    except Exception as e:
        logger.error(f"Error cleaning up old executions: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()
