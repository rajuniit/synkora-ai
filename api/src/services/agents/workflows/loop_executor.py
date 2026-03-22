"""
Loop workflow executor for ADK-style agents.

Executes sub-agents repeatedly until a condition is met.
"""

import logging
from typing import Any

from .base_executor import BaseWorkflowExecutor

logger = logging.getLogger(__name__)


class LoopExecutor(BaseWorkflowExecutor):
    """
    Executes sub-agents in a loop until a condition is met.

    The loop can be controlled by:
    - Maximum iterations
    - Exit condition
    - Error handling

    Example configuration:
    {
        "max_iterations": 5,
        "exit_condition": "state.task_completed == true",
        "stop_on_error": true
    }
    """

    async def execute(self, initial_input: str, user_id: str, **kwargs) -> dict[str, Any]:
        """
        Execute sub-agents in a loop.

        Args:
            initial_input: Initial user input
            user_id: User ID for the execution
            **kwargs: Additional execution parameters

        Returns:
            Dict containing the final state and execution results
        """
        logger.info(f"Starting loop workflow: {self.agent.agent_name}")

        # Initialize state
        self.initialize_state(initial_input)

        # Get workflow config
        workflow_config = self.agent.workflow_config or {}
        max_iterations = workflow_config.get("max_iterations", 10)
        exit_condition = workflow_config.get("exit_condition")
        stop_on_error = workflow_config.get("stop_on_error", True)

        iteration = 0

        # Loop until condition is met or max iterations reached
        while iteration < max_iterations:
            iteration += 1
            self.state["iteration"] = iteration

            logger.info(f"Loop iteration {iteration}/{max_iterations}")

            # Execute each sub-agent in the loop
            for sub_agent in self.sub_agents:
                logger.info(f"Executing sub-agent: {sub_agent.sub_agent.agent_name} (iteration {iteration})")

                # Execute the sub-agent
                output = await self.execute_sub_agent(sub_agent, user_id, **kwargs)

                # Check if execution failed and we should stop
                if output is None and stop_on_error:
                    logger.warning(f"Sub-agent execution failed, stopping workflow: {sub_agent.sub_agent.agent_name}")
                    self.state["stopped_at"] = sub_agent.sub_agent.agent_name
                    self.state["stopped_at_iteration"] = iteration
                    break

            # Check if we should stop due to error
            if self.state.get("error") and stop_on_error:
                logger.warning("Error detected, stopping loop")
                break

            # Check exit condition
            if exit_condition and self.evaluate_condition(exit_condition):
                logger.info(f"Exit condition met: {exit_condition}")
                self.state["exit_reason"] = "condition_met"
                break
        else:
            # Max iterations reached
            logger.info(f"Max iterations reached: {max_iterations}")
            self.state["exit_reason"] = "max_iterations"

        # Store final iteration count
        self.state["total_iterations"] = iteration

        # Get final result
        result = self.get_final_result()

        logger.info(
            f"Loop workflow completed: {self.agent.agent_name}, iterations: {iteration}, status: {result['status']}"
        )

        return result
