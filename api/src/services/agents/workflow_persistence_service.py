"""
Workflow Persistence Service - Persistent tracking of ADK workflow executions.

Provides persistence layer for the BaseWorkflowExecutor system,
enabling workflow resume after interruption and providing audit trails.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.models.agent import Agent
from src.models.agent_sub_agent import AgentSubAgent
from src.models.workflow_execution import (
    WorkflowExecution,
    WorkflowExecutionStatus,
    WorkflowStepExecution,
    WorkflowStepStatus,
)

logger = logging.getLogger(__name__)


class WorkflowPersistenceService:
    """
    Service for persisting workflow execution state.

    Integrates with the existing ADK BaseWorkflowExecutor system
    to provide persistence without replacing the execution logic.

    Usage:
        persistence = WorkflowPersistenceService(db, tenant_id)

        # Create execution record before starting
        execution = await persistence.create_execution(
            agent=workflow_agent,
            user_id=user_id,
            initial_input=user_message
        )

        # Save each step as it executes
        await persistence.save_step_start(execution.id, sub_agent, step_index, input_data)
        await persistence.save_step_complete(execution.id, step_index, output, output_key)

        # Update state periodically
        await persistence.update_state(execution.id, state_dict, current_step)

        # Mark complete when done
        await persistence.mark_completed(execution.id, final_result)
    """

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        """
        Initialize the service.

        Args:
            db: SQLAlchemy async database session
            tenant_id: Tenant ID for multi-tenancy
        """
        self.db = db
        self.tenant_id = tenant_id

    async def create_execution(
        self,
        agent: Agent,
        user_id: str,
        initial_input: str,
        conversation_id: uuid.UUID | None = None,
        sub_agents: list[AgentSubAgent] | None = None,
    ) -> WorkflowExecution:
        """
        Create a new workflow execution record.

        Args:
            agent: The workflow agent being executed
            user_id: User who initiated the workflow
            initial_input: Initial user input
            conversation_id: Optional associated conversation
            sub_agents: List of sub-agents (to determine total_steps)

        Returns:
            The created WorkflowExecution record
        """
        total_steps = len(sub_agents) if sub_agents else 0

        execution = WorkflowExecution(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            parent_agent_id=agent.id,
            conversation_id=conversation_id,
            user_id=user_id,
            workflow_type=agent.workflow_type or "sequential",
            initial_input=initial_input,
            workflow_state={"user_input": initial_input},
            status=WorkflowExecutionStatus.PENDING,
            current_step_index=0,
            total_steps=total_steps,
            execution_log=[],
        )

        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)

        logger.info(f"Created workflow execution {execution.id} for agent {agent.agent_name}")

        return execution

    async def mark_started(self, execution_id: uuid.UUID) -> None:
        """Mark workflow as started."""
        result = await self.db.execute(select(WorkflowExecution).filter(WorkflowExecution.id == execution_id))
        execution = result.scalar_one_or_none()

        if execution:
            execution.mark_started()
            await self.db.commit()
            logger.debug(f"Workflow {execution_id} marked as started")

    async def update_state(
        self,
        execution_id: uuid.UUID,
        state: dict,
        current_step_index: int,
        execution_log: list | None = None,
    ) -> None:
        """
        Update workflow state.

        Args:
            execution_id: The execution to update
            state: Current workflow state dictionary
            current_step_index: Current step index
            execution_log: Optional updated execution log
        """
        result = await self.db.execute(select(WorkflowExecution).filter(WorkflowExecution.id == execution_id))
        execution = result.scalar_one_or_none()

        if execution:
            execution.workflow_state = state
            execution.current_step_index = current_step_index
            if execution_log is not None:
                execution.execution_log = execution_log
            await self.db.commit()
            logger.debug(f"Workflow {execution_id} state updated, step {current_step_index}")

    async def save_step_start(
        self,
        execution_id: uuid.UUID,
        sub_agent: AgentSubAgent,
        step_index: int,
        input_data: str,
    ) -> WorkflowStepExecution:
        """
        Record the start of a step execution.

        Args:
            execution_id: Parent workflow execution
            sub_agent: The sub-agent being executed
            step_index: Position in workflow
            input_data: Input provided to the agent

        Returns:
            The created step execution record
        """
        step = WorkflowStepExecution(
            id=uuid.uuid4(),
            workflow_execution_id=execution_id,
            sub_agent_id=sub_agent.sub_agent_id,
            step_index=step_index,
            agent_name=sub_agent.sub_agent.agent_name,
            input_data=input_data,
            status=WorkflowStepStatus.RUNNING,
            started_at=datetime.now(UTC).isoformat(),
        )

        self.db.add(step)
        await self.db.commit()
        await self.db.refresh(step)

        logger.debug(f"Step {step_index} started for workflow {execution_id}: {step.agent_name}")

        return step

    async def save_step_complete(
        self,
        execution_id: uuid.UUID,
        step_index: int,
        output: str | None = None,
        output_key: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """
        Record step completion.

        Args:
            execution_id: Parent workflow execution
            step_index: Position in workflow
            output: Output from the agent
            output_key: State key where output was stored
            metadata: Additional execution metadata
        """
        result = await self.db.execute(
            select(WorkflowStepExecution).filter(
                WorkflowStepExecution.workflow_execution_id == execution_id,
                WorkflowStepExecution.step_index == step_index,
            )
        )
        step = result.scalar_one_or_none()

        if step:
            step.mark_completed(output, output_key)
            if metadata:
                step.execution_metadata = metadata
            await self.db.commit()
            logger.debug(f"Step {step_index} completed for workflow {execution_id}")

    async def save_step_failed(
        self,
        execution_id: uuid.UUID,
        step_index: int,
        error: str,
    ) -> None:
        """
        Record step failure.

        Args:
            execution_id: Parent workflow execution
            step_index: Position in workflow
            error: Error message
        """
        result = await self.db.execute(
            select(WorkflowStepExecution).filter(
                WorkflowStepExecution.workflow_execution_id == execution_id,
                WorkflowStepExecution.step_index == step_index,
            )
        )
        step = result.scalar_one_or_none()

        if step:
            step.mark_failed(error)
            await self.db.commit()
            logger.debug(f"Step {step_index} failed for workflow {execution_id}: {error}")

    async def save_step_skipped(
        self,
        execution_id: uuid.UUID,
        sub_agent: AgentSubAgent,
        step_index: int,
        reason: str,
    ) -> None:
        """
        Record a skipped step.

        Args:
            execution_id: Parent workflow execution
            sub_agent: The sub-agent that was skipped
            step_index: Position in workflow
            reason: Reason for skipping
        """
        step = WorkflowStepExecution(
            id=uuid.uuid4(),
            workflow_execution_id=execution_id,
            sub_agent_id=sub_agent.sub_agent_id,
            step_index=step_index,
            agent_name=sub_agent.sub_agent.agent_name,
            status=WorkflowStepStatus.SKIPPED,
            skip_reason=reason,
            completed_at=datetime.now(UTC).isoformat(),
        )

        self.db.add(step)
        await self.db.commit()

        logger.debug(f"Step {step_index} skipped for workflow {execution_id}: {reason}")

    async def mark_completed(
        self,
        execution_id: uuid.UUID,
        final_result: dict | None = None,
    ) -> None:
        """
        Mark workflow as completed.

        Args:
            execution_id: The execution to update
            final_result: Optional final result dictionary
        """
        result = await self.db.execute(select(WorkflowExecution).filter(WorkflowExecution.id == execution_id))
        execution = result.scalar_one_or_none()

        if execution:
            execution.mark_completed(final_result)
            await self.db.commit()
            logger.info(f"Workflow {execution_id} completed successfully")

    async def mark_failed(
        self,
        execution_id: uuid.UUID,
        error: str,
    ) -> None:
        """
        Mark workflow as failed.

        Args:
            execution_id: The execution to update
            error: Error message
        """
        result = await self.db.execute(select(WorkflowExecution).filter(WorkflowExecution.id == execution_id))
        execution = result.scalar_one_or_none()

        if execution:
            execution.mark_failed(error)
            await self.db.commit()
            logger.error(f"Workflow {execution_id} failed: {error}")

    async def mark_paused(self, execution_id: uuid.UUID) -> None:
        """Mark workflow as paused (can be resumed later)."""
        result = await self.db.execute(select(WorkflowExecution).filter(WorkflowExecution.id == execution_id))
        execution = result.scalar_one_or_none()

        if execution:
            execution.mark_paused()
            await self.db.commit()
            logger.info(f"Workflow {execution_id} paused")

    async def mark_cancelled(self, execution_id: uuid.UUID) -> None:
        """Mark workflow as cancelled."""
        result = await self.db.execute(select(WorkflowExecution).filter(WorkflowExecution.id == execution_id))
        execution = result.scalar_one_or_none()

        if execution:
            execution.mark_cancelled()
            await self.db.commit()
            logger.info(f"Workflow {execution_id} cancelled")

    async def get_execution(
        self,
        execution_id: uuid.UUID,
    ) -> WorkflowExecution | None:
        """
        Get a workflow execution by ID.

        Args:
            execution_id: The execution to retrieve

        Returns:
            WorkflowExecution or None if not found
        """
        result = await self.db.execute(
            select(WorkflowExecution).filter(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_execution_with_steps(
        self,
        execution_id: uuid.UUID,
    ) -> WorkflowExecution | None:
        """
        Get a workflow execution with all steps eagerly loaded.

        Args:
            execution_id: The execution to retrieve

        Returns:
            WorkflowExecution with steps loaded, or None
        """
        result = await self.db.execute(
            select(WorkflowExecution)
            .options(joinedload(WorkflowExecution.steps))
            .filter(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.tenant_id == self.tenant_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def resume_execution(
        self,
        execution_id: uuid.UUID,
    ) -> tuple[WorkflowExecution | None, dict]:
        """
        Resume a paused or interrupted workflow.

        Args:
            execution_id: The execution to resume

        Returns:
            Tuple of (execution, restored_state) or (None, {}) if not found/not resumable
        """
        execution = await self.get_execution_with_steps(execution_id)

        if not execution:
            logger.warning(f"Workflow {execution_id} not found for resume")
            return None, {}

        if not execution.is_resumable:
            logger.warning(f"Workflow {execution_id} is not resumable (status: {execution.status})")
            return None, {}

        # Restore state from the execution
        state = execution.workflow_state or {}

        # Mark as running again
        execution.status = WorkflowExecutionStatus.RUNNING
        await self.db.commit()

        logger.info(f"Resuming workflow {execution_id} from step {execution.current_step_index}")

        return execution, state

    async def get_pending_executions(
        self,
        agent_id: uuid.UUID | None = None,
    ) -> list[WorkflowExecution]:
        """
        Get workflows that can be resumed.

        Args:
            agent_id: Optional filter by agent

        Returns:
            List of resumable workflow executions
        """
        query = select(WorkflowExecution).filter(
            WorkflowExecution.tenant_id == self.tenant_id,
            WorkflowExecution.status.in_(
                [
                    WorkflowExecutionStatus.RUNNING,
                    WorkflowExecutionStatus.PAUSED,
                ]
            ),
        )

        if agent_id:
            query = query.filter(WorkflowExecution.parent_agent_id == agent_id)

        query = query.order_by(WorkflowExecution.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_recent_executions(
        self,
        agent_id: uuid.UUID | None = None,
        limit: int = 10,
    ) -> list[WorkflowExecution]:
        """
        Get recent workflow executions.

        Args:
            agent_id: Optional filter by agent
            limit: Maximum number of results

        Returns:
            List of recent workflow executions
        """
        query = select(WorkflowExecution).filter(
            WorkflowExecution.tenant_id == self.tenant_id,
        )

        if agent_id:
            query = query.filter(WorkflowExecution.parent_agent_id == agent_id)

        query = query.order_by(WorkflowExecution.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def cleanup_old_executions(
        self,
        days_to_keep: int = 30,
    ) -> int:
        """
        Clean up old completed/failed workflow executions.

        Args:
            days_to_keep: Number of days to retain executions

        Returns:
            Number of executions deleted
        """
        from datetime import timedelta

        from sqlalchemy import delete

        cutoff = datetime.now(UTC) - timedelta(days=days_to_keep)
        cutoff_str = cutoff.isoformat()

        # Only delete terminal executions (completed, failed, cancelled)
        stmt = delete(WorkflowExecution).where(
            WorkflowExecution.tenant_id == self.tenant_id,
            WorkflowExecution.status.in_(
                [
                    WorkflowExecutionStatus.COMPLETED,
                    WorkflowExecutionStatus.FAILED,
                    WorkflowExecutionStatus.CANCELLED,
                ]
            ),
            WorkflowExecution.completed_at < cutoff_str,
        )

        result = await self.db.execute(stmt)
        await self.db.commit()

        deleted_count = result.rowcount
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old workflow executions")

        return deleted_count
