"""
Agent registry for managing agent instances.

Provides centralized agent registration, discovery, and lifecycle management.
Now includes Redis sync for horizontal scaling support.
"""

import logging
from typing import Any

from src.services.agents.base_agent import BaseAgent
from src.services.agents.config import AgentConfig

logger = logging.getLogger(__name__)


def _get_redis_registry():
    """Lazy import to avoid circular dependencies."""
    try:
        from src.services.agents.redis_registry import get_redis_registry

        return get_redis_registry()
    except Exception as e:
        logger.warning(f"Redis registry not available: {e}")
        return None


class AgentRegistry:
    """
    Registry for managing agent instances.

    Provides a centralized location for agent registration, discovery,
    and lifecycle management across the application.
    """

    def __init__(self):
        """Initialize the agent registry."""
        self._agents: dict[str, BaseAgent] = {}
        self._configs: dict[str, AgentConfig] = {}
        logger.info("Agent registry initialized")

    def register(self, agent: BaseAgent) -> None:
        """
        Register an agent instance.

        Args:
            agent: Agent instance to register

        Raises:
            ValueError: If agent with same name already exists
        """
        if agent.config.name in self._agents:
            raise ValueError(f"Agent '{agent.config.name}' is already registered")

        self._agents[agent.config.name] = agent
        self._configs[agent.config.name] = agent.config

        # PERFORMANCE: Sync to Redis for horizontal scaling
        redis_registry = _get_redis_registry()
        if redis_registry:
            try:
                # Convert config to dict for Redis storage
                config_dict = {
                    "name": agent.config.name,
                    "description": agent.config.description,
                    "system_prompt": agent.config.system_prompt,
                }
                redis_registry.register_config(
                    agent_name=agent.config.name, config=config_dict, metadata={"type": agent.__class__.__name__}
                )
            except Exception as e:
                logger.warning(f"Failed to sync agent to Redis: {e}")

        logger.info(f"Registered agent: {agent.config.name}")

    def unregister(self, agent_name: str) -> None:
        """
        Unregister an agent.

        Args:
            agent_name: Name of the agent to unregister

        Raises:
            KeyError: If agent not found
        """
        if agent_name not in self._agents:
            raise KeyError(f"Agent '{agent_name}' not found in registry")

        del self._agents[agent_name]
        del self._configs[agent_name]

        # PERFORMANCE: Sync to Redis for horizontal scaling
        redis_registry = _get_redis_registry()
        if redis_registry:
            try:
                redis_registry.unregister(agent_name)
            except Exception as e:
                logger.warning(f"Failed to unregister agent from Redis: {e}")

        logger.info(f"Unregistered agent: {agent_name}")

    def get(self, agent_name: str) -> BaseAgent | None:
        """
        Get an agent by name.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent instance or None if not found
        """
        return self._agents.get(agent_name)

    def get_config(self, agent_name: str) -> AgentConfig | None:
        """
        Get agent configuration by name.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent configuration or None if not found
        """
        return self._configs.get(agent_name)

    def list_agents(self) -> list[str]:
        """
        List all registered agent names.

        Returns:
            List of agent names
        """
        return list(self._agents.keys())

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get statistics for all registered agents.

        Returns:
            Dictionary mapping agent names to their statistics
        """
        return {name: agent.get_stats() for name, agent in self._agents.items()}

    def reset_all(self) -> None:
        """Reset all registered agents."""
        for agent in self._agents.values():
            agent.reset()
        logger.info("Reset all agents in registry")

    def clear(self) -> None:
        """Clear all agents from registry."""
        self._agents.clear()
        self._configs.clear()
        logger.info("Cleared agent registry")

    def __len__(self) -> int:
        """Get number of registered agents."""
        return len(self._agents)

    def __contains__(self, agent_name: str) -> bool:
        """Check if agent is registered."""
        return agent_name in self._agents

    def __repr__(self) -> str:
        """String representation."""
        return f"<AgentRegistry agents={len(self._agents)}>"


# Global registry instance
_global_registry: AgentRegistry | None = None


def get_registry() -> AgentRegistry:
    """
    Get the global agent registry instance.

    Returns:
        Global agent registry
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry
