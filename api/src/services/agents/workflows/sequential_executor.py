"""
Sequential workflow executor for ADK-style agents.

Executes sub-agents one after another in order.
"""

import logging
from typing import Any

from .base_executor import BaseWorkflowExecutor

logger = logging.getLogger(__name__)


class SequentialExecutor(BaseWorkflowExecutor):
    """
    Executes sub-agents sequentially in order.

    Each agent is executed in sequence, with the output of one
    agent potentially being used as input for the next agent.

    Example configuration:
    {
        "stop_on_error": true  # Stop execution if any agent fails
    }
    """

    async def execute(self, initial_input: str, user_id: str, **kwargs) -> dict[str, Any]:
        """
        Execute sub-agents sequentially.

        Args:
            initial_input: Initial user input
            user_id: User ID for the execution
            **kwargs: Additional execution parameters

        Returns:
            Dict containing the final state and execution results
        """
        logger.info(f"Starting sequential workflow: {self.agent.agent_name}")

        # Initialize state
        self.initialize_state(initial_input)

        # Get workflow config
        workflow_config = self.agent.workflow_config or {}
        stop_on_error = workflow_config.get("stop_on_error", True)

        # Execute each sub-agent in order
        for sub_agent in self.sub_agents:
            logger.info(f"Executing sub-agent: {sub_agent.sub_agent.agent_name}")

            # Execute the sub-agent
            output = await self.execute_sub_agent(sub_agent, user_id, **kwargs)

            # Check if execution failed and we should stop
            if output is None and stop_on_error:
                logger.warning(f"Sub-agent execution failed, stopping workflow: {sub_agent.sub_agent.agent_name}")
                self.state["stopped_at"] = sub_agent.sub_agent.agent_name
                break

        # Get final result
        result = self.get_final_result()

        logger.info(f"Sequential workflow completed: {self.agent.agent_name}, status: {result['status']}")

        return result
