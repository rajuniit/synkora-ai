"""
Parallel workflow executor for ADK-style agents.

Executes sub-agents concurrently.
"""

import asyncio
import logging
from typing import Any

from .base_executor import BaseWorkflowExecutor

logger = logging.getLogger(__name__)


class ParallelExecutor(BaseWorkflowExecutor):
    """
    Executes sub-agents in parallel (concurrently).

    All sub-agents are executed at the same time, and the workflow
    waits for all to complete before finishing.

    Example configuration:
    {
        "wait_for_all": true,  # Wait for all agents to complete
        "timeout_seconds": 300  # Overall timeout for all executions
    }
    """

    async def execute(self, initial_input: str, user_id: str, **kwargs) -> dict[str, Any]:
        """
        Execute sub-agents in parallel.

        Args:
            initial_input: Initial user input
            user_id: User ID for the execution
            **kwargs: Additional execution parameters

        Returns:
            Dict containing the final state and execution results
        """
        logger.info(f"Starting parallel workflow: {self.agent.agent_name}")

        # Initialize state
        self.initialize_state(initial_input)

        # Get workflow config
        workflow_config = self.agent.workflow_config or {}
        wait_for_all = workflow_config.get("wait_for_all", True)
        timeout_seconds = workflow_config.get("timeout_seconds", 300)

        # Create tasks for all sub-agents
        tasks = []
        for sub_agent in self.sub_agents:
            task = self._execute_sub_agent_with_logging(sub_agent, user_id, **kwargs)
            tasks.append(task)

        logger.info(f"Executing {len(tasks)} sub-agents in parallel")

        try:
            if wait_for_all:
                # Wait for all tasks to complete
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True), timeout=timeout_seconds
                )
            else:
                # Return as soon as first task completes
                done, pending = await asyncio.wait(tasks, timeout=timeout_seconds, return_when=asyncio.FIRST_COMPLETED)

                # Cancel pending tasks
                for task in pending:
                    task.cancel()

                results = [task.result() for task in done]

            # Process results
            success_count = 0
            failure_count = 0

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Sub-agent {i} failed with exception: {str(result)}")
                    failure_count += 1
                elif result is None:
                    logger.warning(f"Sub-agent {i} returned None")
                    failure_count += 1
                else:
                    success_count += 1

            self.state["parallel_execution"] = {
                "total_agents": len(self.sub_agents),
                "success_count": success_count,
                "failure_count": failure_count,
                "wait_for_all": wait_for_all,
            }

        except TimeoutError:
            logger.error(f"Parallel execution timed out after {timeout_seconds} seconds")
            self.state["error"] = f"Execution timed out after {timeout_seconds} seconds"
            self.state["timeout"] = True

        # Get final result
        result = self.get_final_result()

        logger.info(f"Parallel workflow completed: {self.agent.agent_name}, status: {result['status']}")

        return result

    async def _execute_sub_agent_with_logging(self, sub_agent, user_id: str, **kwargs):
        """
        Wrapper to execute sub-agent with proper logging.

        This ensures each parallel execution is properly tracked.
        """
        try:
            return await self.execute_sub_agent(sub_agent, user_id, **kwargs)
        except Exception as e:
            logger.error(f"Parallel sub-agent execution failed: {sub_agent.sub_agent.agent_name}, error: {str(e)}")
            return None
