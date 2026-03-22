"""
Custom workflow executor for ADK-style agents.

Provides opinionated orchestration flows that combine sequential, loop,
and post-processing stages.
"""

import asyncio
import logging
from typing import Any

from src.models.agent_sub_agent import AgentSubAgent

from .base_executor import BaseWorkflowExecutor

logger = logging.getLogger(__name__)


class CustomExecutor(BaseWorkflowExecutor):
    """
    Executes custom, multi-stage workflows.

    Flow is defined by workflow_config.nodes, for example:
    {
      "nodes": [
        {"type": "agent", "agents": ["story_generator"]},
        {"type": "loop", "agents": ["critic", "reviser"], "iterations": 2},
        {"type": "sequential", "agents": ["grammar_check", "tone_check"]}
      ],
      "stop_on_error": true
    }
    """

    async def execute(self, initial_input: str, user_id: str, **kwargs) -> dict[str, Any]:
        logger.info(f"Starting custom workflow: {self.agent.agent_name}")

        self.initialize_state(initial_input)

        workflow_config = self.agent.workflow_config or {}
        nodes = workflow_config.get("nodes") or workflow_config.get("stages")
        stop_on_error = workflow_config.get("stop_on_error", True)

        if not isinstance(nodes, list) or not nodes:
            error_msg = "Custom workflow requires a non-empty 'nodes' list in workflow_config."
            logger.error(error_msg)
            self.state["error"] = error_msg
            return self.get_final_result()

        output = None

        for stage_index, stage in enumerate(nodes, start=1):
            stage_type = (stage or {}).get("type", "sequential")
            stage_agents = self._resolve_sub_agents(stage)

            if not stage_agents:
                logger.warning(f"Custom workflow stage {stage_index} has no sub-agents")
                continue

            logger.info(f"Executing custom stage {stage_index}: {stage_type} ({len(stage_agents)} agents)")

            if stage_type in {"agent", "sequential"}:
                for sub_agent in stage_agents:
                    # Store previous output for next agent to use
                    if output:
                        self.state["previous_output"] = output
                        self.state["last_agent_output"] = output

                    output = await self.execute_sub_agent(sub_agent, user_id, **kwargs)
                    if output is None and stop_on_error:
                        self.state["stopped_at"] = sub_agent.sub_agent.agent_name
                        return self.get_final_result()

            elif stage_type == "loop":
                iterations = int(stage.get("iterations", 1))
                for iteration in range(iterations):
                    self.state["iteration"] = iteration + 1
                    for sub_agent in stage_agents:
                        # Store previous output for next agent to use
                        if output:
                            self.state["previous_output"] = output
                            self.state["last_agent_output"] = output

                        output = await self.execute_sub_agent(sub_agent, user_id, **kwargs)
                        if output is None and stop_on_error:
                            self.state["stopped_at"] = sub_agent.sub_agent.agent_name
                            return self.get_final_result()

            elif stage_type == "parallel":
                tasks = [self.execute_sub_agent(sub_agent, user_id, **kwargs) for sub_agent in stage_agents]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for sub_agent, result in zip(stage_agents, results, strict=False):
                    if isinstance(result, Exception):
                        logger.error(f"Custom parallel stage error for {sub_agent.sub_agent.agent_name}: {result}")
                        if stop_on_error:
                            self.state["error"] = str(result)
                            self.state["stopped_at"] = sub_agent.sub_agent.agent_name
                            return self.get_final_result()
                    elif result is None and stop_on_error:
                        self.state["stopped_at"] = sub_agent.sub_agent.agent_name
                        return self.get_final_result()
                    else:
                        output = result or output

            else:
                logger.error(f"Unknown custom stage type: {stage_type}")
                if stop_on_error:
                    self.state["error"] = f"Unknown stage type: {stage_type}"
                    return self.get_final_result()

        if output:
            self.state["final_response"] = output

        result = self.get_final_result()
        logger.info(f"Custom workflow completed: {self.agent.agent_name}, status: {result['status']}")
        return result

    def _resolve_sub_agents(self, stage: dict[str, Any] | None) -> list[AgentSubAgent]:
        if not stage:
            return self.sub_agents

        agent_refs = stage.get("agents") or stage.get("roles") or []
        indices = stage.get("indices") or []

        if agent_refs:
            resolved = []
            for ref in agent_refs:
                for sub_agent in self.sub_agents:
                    config = sub_agent.execution_config or {}
                    role = config.get("role")
                    if ref in {role, sub_agent.sub_agent.agent_name}:
                        resolved.append(sub_agent)
                        break
            return resolved

        if indices:
            resolved = []
            for index in indices:
                if isinstance(index, int) and 0 <= index < len(self.sub_agents):
                    resolved.append(self.sub_agents[index])
            return resolved

        return self.sub_agents
