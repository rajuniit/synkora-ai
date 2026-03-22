"""
Base agent class for Google Agent SDK integration.

Provides the foundation for all agent implementations.
"""

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.services.agents.config import AgentConfig, AgentStatus
from src.services.agents.llm_client import MultiProviderLLMClient
from src.services.observability.langfuse_service import LangfuseService
from src.services.performance.llm_client_pool import get_llm_client_pool

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agents using Google Agent SDK.

    This class provides common functionality for agent lifecycle management,
    execution, and monitoring.
    """

    def __init__(self, config: AgentConfig, observability_config: dict[str, Any] | None = None):
        """
        Initialize the agent.

        Args:
            config: Agent configuration
            observability_config: Optional observability configuration
        """
        self.config = config
        self.agent_id = str(uuid4())
        self.status = AgentStatus.IDLE
        self.created_at = datetime.now(UTC)
        self.last_run_at: datetime | None = None
        self.execution_count = 0
        self.error_count = 0
        self.llm_client: MultiProviderLLMClient | None = None
        self._history: list[dict[str, Any]] = []
        self.observability_config = observability_config or {}
        self.langfuse_service = LangfuseService.for_agent(observability_config)
        self.current_trace_id: str | None = None  # Store current trace ID for nested operations

        logger.info(f"Initialized agent: {self.config.name} (ID: {self.agent_id})")

    def initialize_client(self, api_key: str | None = None) -> None:
        """
        Initialize the multi-provider LLM client.

        Uses the LLM client pool to reuse connections and reduce overhead.

        Args:
            api_key: Optional API key override
        """
        try:
            key = api_key or self.config.llm_config.api_key
            if not key:
                raise ValueError("API key is required to initialize the client")

            # Update config with API key
            if api_key:
                self.config.llm_config.api_key = api_key

            # Get client from pool (reuses existing clients for same provider/model)
            pool = get_llm_client_pool()
            self.llm_client = pool.get_client(
                provider=self.config.llm_config.provider,
                api_key=key,
                model=self.config.llm_config.model_name,
                api_base=self.config.llm_config.api_base,
                temperature=self.config.llm_config.temperature,
                max_tokens=self.config.llm_config.max_tokens,
                top_p=self.config.llm_config.top_p,
                additional_params=self.config.llm_config.additional_params,
                observability_config=self.observability_config,
            )

            logger.info(
                f"Client initialized for agent: {self.config.name} "
                f"(provider: {self.config.llm_config.provider}, "
                f"model: {self.config.llm_config.model_name})"
            )
        except Exception as e:
            logger.error(f"Failed to initialize client: {e}")
            raise

    @abstractmethod
    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the agent with given input.

        Args:
            input_data: Input data for the agent

        Returns:
            Execution result
        """
        pass

    async def run(
        self, input_data: dict[str, Any], user_id: str | None = None, session_id: str | None = None
    ) -> dict[str, Any]:
        """
        Run the agent with error handling and status management.

        Args:
            input_data: Input data for the agent
            user_id: Optional user ID for tracing
            session_id: Optional session ID for tracing

        Returns:
            Execution result with metadata
        """
        self.status = AgentStatus.RUNNING
        self.last_run_at = datetime.now(UTC)
        self.execution_count += 1

        start_time = datetime.now(UTC)
        trace_id = None

        # Initialize Langfuse trace if enabled
        if self.langfuse_service.should_trace(self.observability_config):
            try:
                trace_id = self.langfuse_service.create_trace(
                    name=f"agent_execution_{self.config.name}",
                    user_id=user_id,
                    session_id=session_id,
                    metadata={
                        "agent_id": self.agent_id,
                        "agent_name": self.config.name,
                        "agent_type": self.config.agent_type,
                        "input": input_data,
                    },
                )
                # Store trace_id for nested operations (function calling, RAG, etc.)
                self.current_trace_id = trace_id
                logger.debug(f"Created Langfuse trace: {trace_id}")
            except Exception as e:
                logger.warning(f"Failed to create Langfuse trace: {e}")

        try:
            logger.info(f"Running agent: {self.config.name}")

            # Execute the agent
            result = await self.execute(input_data)

            # Update status
            self.status = AgentStatus.COMPLETED
            execution_time = (datetime.now(UTC) - start_time).total_seconds()

            # Clear trace_id after execution
            self.current_trace_id = None

            # Add to history
            self._add_to_history(input_data, result, "success", execution_time)

            # Update Langfuse trace with success
            if trace_id:
                try:
                    self.langfuse_service.update_trace(
                        trace_id=trace_id,
                        output=result,
                        metadata={
                            "status": "success",
                            "execution_time": execution_time,
                        },
                    )
                    # Flush to ensure trace is sent to Langfuse
                    self.langfuse_service.flush()
                    logger.info(f"✅ Flushed Langfuse trace: {trace_id}")
                except Exception as e:
                    logger.warning(f"Failed to update Langfuse trace: {e}")

            logger.info(f"Agent {self.config.name} completed successfully in {execution_time:.2f}s")

            return {
                "agent_id": self.agent_id,
                "agent_name": self.config.name,
                "status": "success",
                "result": result,
                "execution_time": execution_time,
                "timestamp": datetime.now(UTC).isoformat(),
                "trace_id": trace_id,
            }

        except Exception as e:
            self.status = AgentStatus.FAILED
            self.error_count += 1
            execution_time = (datetime.now(UTC) - start_time).total_seconds()

            # Clear trace_id after execution
            self.current_trace_id = None

            # Add to history
            self._add_to_history(input_data, None, "error", execution_time, str(e))

            # Update Langfuse trace with error
            if trace_id:
                try:
                    self.langfuse_service.update_trace(
                        trace_id=trace_id,
                        output={"error": str(e)},
                        metadata={
                            "status": "error",
                            "execution_time": execution_time,
                            "error": str(e),
                        },
                    )
                    # Flush to ensure trace is sent to Langfuse
                    self.langfuse_service.flush()
                    logger.info(f"✅ Flushed Langfuse trace: {trace_id}")
                except Exception as ex:
                    logger.warning(f"Failed to update Langfuse trace: {ex}")

            logger.error(f"Agent {self.config.name} failed: {e}", exc_info=True)

            return {
                "agent_id": self.agent_id,
                "agent_name": self.config.name,
                "status": "error",
                "error": str(e),
                "execution_time": execution_time,
                "timestamp": datetime.now(UTC).isoformat(),
                "trace_id": trace_id,
            }

    def _add_to_history(
        self,
        input_data: dict[str, Any],
        result: dict[str, Any] | None,
        status: str,
        execution_time: float,
        error: str | None = None,
    ) -> None:
        """
        Add execution to history.

        Args:
            input_data: Input data
            result: Execution result
            status: Execution status
            execution_time: Execution time in seconds
            error: Error message if failed
        """
        if self.config.memory_enabled:
            self._history.append(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "input": input_data,
                    "result": result,
                    "status": status,
                    "execution_time": execution_time,
                    "error": error,
                }
            )

            # Keep only last 100 entries
            if len(self._history) > 100:
                self._history = self._history[-100:]

    def get_history(self, limit: int | None = None) -> list[dict[str, Any]]:
        """
        Get execution history.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of history entries
        """
        if limit:
            return self._history[-limit:]
        return self._history

    def clear_history(self) -> None:
        """Clear execution history."""
        self._history = []
        logger.info(f"Cleared history for agent: {self.config.name}")

    def get_stats(self) -> dict[str, Any]:
        """
        Get agent statistics.

        Returns:
            Dictionary of statistics
        """
        return {
            "agent_id": self.agent_id,
            "agent_name": self.config.name,
            "agent_type": self.config.agent_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "success_rate": (
                (self.execution_count - self.error_count) / self.execution_count * 100
                if self.execution_count > 0
                else 0
            ),
            "history_size": len(self._history),
        }

    def reset(self) -> None:
        """Reset agent state."""
        self.status = AgentStatus.IDLE
        self.execution_count = 0
        self.error_count = 0
        self.clear_history()
        logger.info(f"Reset agent: {self.config.name}")

    def __repr__(self) -> str:
        """String representation."""
        return f"<{self.__class__.__name__} name={self.config.name} id={self.agent_id} status={self.status.value}>"
