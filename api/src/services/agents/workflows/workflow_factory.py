"""
Workflow factory for creating appropriate workflow executors.
"""

import logging

from src.models.agent import Agent
from src.models.agent_sub_agent import AgentSubAgent

from .base_executor import BaseWorkflowExecutor
from .custom_executor import CustomExecutor
from .loop_executor import LoopExecutor
from .parallel_executor import ParallelExecutor
from .sequential_executor import SequentialExecutor

logger = logging.getLogger(__name__)


class WorkflowFactory:
    """
    Factory for creating workflow executors based on agent configuration.
    """

    @staticmethod
    def create_executor(agent: Agent, sub_agents: list[AgentSubAgent]) -> BaseWorkflowExecutor | None:
        """
        Create the appropriate workflow executor for the agent.

        Args:
            agent: The workflow agent
            sub_agents: List of sub-agents to execute

        Returns:
            The appropriate executor instance or None if not a workflow agent
        """
        workflow_type = agent.workflow_type

        if not workflow_type:
            logger.debug(f"Agent {agent.agent_name} is not a workflow agent")
            return None

        if not sub_agents:
            logger.warning(f"Workflow agent {agent.agent_name} has no sub-agents")
            return None

        # Create executor based on workflow type
        if workflow_type == "sequential":
            logger.info(f"Creating sequential executor for agent: {agent.agent_name}")
            return SequentialExecutor(agent, sub_agents)

        elif workflow_type == "loop":
            logger.info(f"Creating loop executor for agent: {agent.agent_name}")
            return LoopExecutor(agent, sub_agents)

        elif workflow_type == "parallel":
            logger.info(f"Creating parallel executor for agent: {agent.agent_name}")
            return ParallelExecutor(agent, sub_agents)

        elif workflow_type == "custom":
            logger.info(f"Creating custom executor for agent: {agent.agent_name}")
            return CustomExecutor(agent, sub_agents)

        else:
            logger.error(f"Unknown workflow type: {workflow_type} for agent: {agent.agent_name}")
            return None

    @staticmethod
    def get_supported_workflow_types() -> list[str]:
        """
        Get list of supported workflow types.

        Returns:
            List of supported workflow type strings
        """
        return ["sequential", "loop", "parallel", "custom"]

    @staticmethod
    def get_workflow_type_info(workflow_type: str) -> dict:
        """
        Get information about a specific workflow type.

        Args:
            workflow_type: The workflow type to get info for

        Returns:
            Dictionary with workflow type information
        """
        info = {
            "sequential": {
                "name": "Sequential",
                "description": "Execute agents one after another in order",
                "config_schema": {
                    "stop_on_error": {
                        "type": "boolean",
                        "default": True,
                        "description": "Stop execution if any agent fails",
                    }
                },
                "use_cases": ["Multi-step processes", "Data transformation pipelines", "Sequential decision making"],
            },
            "loop": {
                "name": "Loop",
                "description": "Execute agents repeatedly until a condition is met",
                "config_schema": {
                    "max_iterations": {"type": "integer", "default": 10, "description": "Maximum number of iterations"},
                    "exit_condition": {
                        "type": "string",
                        "description": "Condition to exit the loop (e.g., 'state.task_completed == true')",
                    },
                    "stop_on_error": {
                        "type": "boolean",
                        "default": True,
                        "description": "Stop execution if any agent fails",
                    },
                },
                "use_cases": ["Iterative refinement", "Until-complete tasks", "Retry logic"],
            },
            "parallel": {
                "name": "Parallel",
                "description": "Execute agents concurrently",
                "config_schema": {
                    "wait_for_all": {
                        "type": "boolean",
                        "default": True,
                        "description": "Wait for all agents to complete",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "default": 300,
                        "description": "Overall timeout for all executions",
                    },
                },
                "use_cases": [
                    "Independent parallel tasks",
                    "Concurrent data processing",
                    "Multi-source information gathering",
                ],
            },
            "custom": {
                "name": "Custom",
                "description": "Custom orchestration flow defined by nodes",
                "config_schema": {
                    "nodes": {
                        "type": "array",
                        "description": "Ordered list of nodes with type and agent names/roles/indices",
                    },
                    "stop_on_error": {
                        "type": "boolean",
                        "default": True,
                        "description": "Stop execution if a sub-agent fails",
                    },
                },
                "use_cases": [
                    "Story generation and refinement",
                    "Multi-stage critique and revision",
                    "Post-processing pipelines",
                ],
            },
        }

        return info.get(workflow_type, {})
