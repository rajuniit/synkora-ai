"""
Agent Loader Service.

Handles loading agents from cache/database and managing LLM configurations.
"""

import logging
import time
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent import Agent
from src.services.agents.agent_manager import AgentManager
from src.services.agents.config import AgentConfig, ModelConfig, ToolConfig
from src.services.agents.implementations import ClaudeCodeAgent, CodeAgent, LLMAgent, ResearchAgent
from src.services.agents.llm_provider_presets import get_model_preset
from src.services.agents.routing.intent_classifier import classify_query
from src.services.agents.routing.model_router import RoutingDecision, get_router
from src.services.agents.security import decrypt_value
from src.services.cache import get_agent_cache

logger = logging.getLogger(__name__)


class AgentLoadResult:
    """Result of agent loading operation."""

    def __init__(
        self,
        db_agent: Agent | None = None,
        agent: Any | None = None,
        cache_hit: bool = False,
        loading_time: float = 0.0,
        error: str | None = None,
        is_workflow: bool = False,
        fallback_config_ids: list[str] | None = None,
        routing_decision: Any | None = None,
    ):
        self.db_agent = db_agent
        self.agent = agent
        self.cache_hit = cache_hit
        self.loading_time = loading_time
        self.error = error
        self.is_workflow = is_workflow
        self.fallback_config_ids: list[str] = fallback_config_ids or []
        self.routing_decision = routing_decision


class AgentLoaderService:
    """Service for loading and caching agents."""

    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager
        self.cache = get_agent_cache()

    @staticmethod
    def _get_max_tokens_with_preset_default(
        provider: str, model_name: str, configured_max_tokens: int | None
    ) -> int | None:
        """
        Get max_tokens, using preset defaults if not configured.

        This ensures that agents have appropriate max_tokens for tool calls
        that may generate large content (e.g., PDF generation, document creation).

        Args:
            provider: LLM provider (e.g., 'anthropic', 'litellm')
            model_name: Model name (e.g., 'claude-4-5-sonnet')
            configured_max_tokens: Value from agent config (may be None)

        Returns:
            max_tokens value (from config, preset, or default 16384)
        """
        if configured_max_tokens is not None:
            return configured_max_tokens

        # Try to get preset default
        # For litellm provider, try both 'litellm' and original provider presets
        model_preset = get_model_preset(provider, model_name)
        if not model_preset and provider == "litellm":
            # Try common providers for litellm models
            for fallback_provider in ["anthropic", "openai", "gemini"]:
                model_preset = get_model_preset(fallback_provider, model_name)
                if model_preset:
                    break

        if model_preset and model_preset.default_max_tokens:
            logger.info(
                f"Using preset default max_tokens: {model_preset.default_max_tokens} for {provider}/{model_name}"
            )
            return model_preset.default_max_tokens

        default_max_tokens = 16384
        logger.info(f"Using fallback max_tokens: {default_max_tokens} for {provider}/{model_name}")
        return default_max_tokens

    def _reconstruct_agent(self, cached_data: dict[str, Any]) -> Agent:
        """
        Reconstruct an Agent instance from cached data without touching the database.

        Used by the fast path when the agent is already warm in the in-process registry.
        The returned object is detached (not attached to any session), which is fine
        because all attribute access in the hot path uses scalar columns only.
        """
        from datetime import datetime

        agent_data = {k: v for k, v in cached_data.items() if k not in ["default_llm_config"]}

        # Parse datetime strings back to datetime objects
        for dt_field in ["created_at", "updated_at"]:
            if agent_data.get(dt_field) and isinstance(agent_data[dt_field], str):
                agent_data[dt_field] = datetime.fromisoformat(agent_data[dt_field])

        # Convert UUID string fields back to UUID objects
        for uuid_field in ["id", "tenant_id"]:
            if agent_data.get(uuid_field) and isinstance(agent_data[uuid_field], str):
                try:
                    agent_data[uuid_field] = uuid.UUID(agent_data[uuid_field])
                except ValueError:
                    pass

        return Agent(**agent_data)

    async def load_agent(
        self,
        agent_name: str,
        db: AsyncSession,
        llm_config_id: str | None = None,
        query: str | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> AgentLoadResult:
        """
        Load agent from cache or database, with optional intelligent model routing.

        When the agent has routing_mode != "fixed" and a query is provided, the
        router classifies the query and selects the most cost-effective LLM config.

        Args:
            agent_name: Name of the agent
            db: Database session
            llm_config_id: Explicit LLM config ID override (bypasses routing)
            query: User message (used by router for intent/complexity classification)
            conversation_history: Prior turns (used by router for complexity scoring)

        Returns:
            AgentLoadResult with loaded agent, routing decision, and fallback IDs
        """
        start_time = time.time()

        # Fast path: agent is already warm in the in-process registry AND in Redis.
        # Skip db.merge() entirely — reconstruct db_agent from Redis data as a
        # detached object (all hot-path attribute accesses are scalar columns).
        # Bypass when:
        #   - llm_config_id is set (needs fresh DB config)
        #   - query is set (routing may select a different config)
        if not llm_config_id and not query:
            in_memory_agent = self.agent_manager.registry.get(agent_name)
            if in_memory_agent and in_memory_agent.llm_client:
                cached_data = await self.cache.get_agent_config(agent_name)
                if cached_data:
                    db_agent = self._reconstruct_agent(cached_data)
                    is_workflow = bool(db_agent.workflow_type)
                    logger.info(
                        f"⚡ Fast path HIT for agent '{agent_name}' "
                        f"(registry+redis, no DB) ({time.time() - start_time:.4f}s)"
                    )
                    return AgentLoadResult(
                        db_agent=db_agent,
                        agent=in_memory_agent,
                        cache_hit=True,
                        loading_time=time.time() - start_time,
                        is_workflow=is_workflow,
                    )

        # Slow path: Redis → DB lookup
        cached_data = await self.cache.get_agent_config(agent_name)

        if cached_data:
            db_agent = await self._load_from_cache(cached_data, db)
            cache_hit = True
            logger.info(f"Cache HIT for agent '{agent_name}' ({time.time() - start_time:.3f}s)")
        else:
            db_agent = await self._load_from_database(agent_name, db)
            cache_hit = False

            if db_agent:
                await self._cache_agent(db_agent, db)
                logger.info(
                    f"Cache MISS for agent '{agent_name}', cached for next time ({time.time() - start_time:.3f}s)"
                )

        if not db_agent:
            return AgentLoadResult(
                error=f"Agent {agent_name} not found in database", loading_time=time.time() - start_time
            )

        # Check if workflow agent
        is_workflow = bool(db_agent.workflow_type)

        if is_workflow:
            logger.info(f"Detected workflow agent: {agent_name}, type: {db_agent.workflow_type}")
            return AgentLoadResult(
                db_agent=db_agent, cache_hit=cache_hit, loading_time=time.time() - start_time, is_workflow=True
            )

        # Run model routing if a query was provided and routing is non-fixed
        routing_decision = None
        effective_config_id = llm_config_id  # explicit override wins
        fallback_config_ids: list[str] = []

        agent_routing_mode = getattr(db_agent, "routing_mode", "fixed") or "fixed"

        if query and not llm_config_id and agent_routing_mode != "fixed":
            routing_decision, effective_config_id, fallback_config_ids = await self._run_routing(
                db_agent=db_agent,
                query=query,
                conversation_history=conversation_history,
                db=db,
            )

        # Load regular agent into memory
        agent = await self._load_agent_to_memory(
            agent_name=agent_name,
            db_agent=db_agent,
            cached_data=cached_data,
            llm_config_id=effective_config_id,
            db=db,
        )

        return AgentLoadResult(
            db_agent=db_agent,
            agent=agent,
            cache_hit=cache_hit,
            loading_time=time.time() - start_time,
            is_workflow=False,
            error=agent.get("error") if isinstance(agent, dict) else None,
            fallback_config_ids=fallback_config_ids,
            routing_decision=routing_decision,
        )

    async def _load_from_cache(self, cached_data: dict[str, Any], db: AsyncSession) -> Agent:
        """Load agent from cached data."""
        from datetime import datetime

        # Remove non-model fields
        agent_data = {k: v for k, v in cached_data.items() if k not in ["default_llm_config"]}

        # Parse datetime fields from ISO format strings
        for dt_field in ["created_at", "updated_at"]:
            if agent_data.get(dt_field) and isinstance(agent_data[dt_field], str):
                agent_data[dt_field] = datetime.fromisoformat(agent_data[dt_field])

        db_agent = Agent(**agent_data)
        db_agent = await db.merge(db_agent)  # Attach to session

        return db_agent

    async def _load_from_database(self, agent_name: str, db: AsyncSession) -> Agent | None:
        """Load agent from database."""
        result = await db.execute(select(Agent).filter(Agent.agent_name == agent_name))
        return result.scalar_one_or_none()

    async def _cache_agent(self, db_agent: Agent, db: AsyncSession) -> None:
        """Cache agent configuration."""
        from src.models.agent_llm_config import AgentLLMConfig

        # Load default LLM config
        llm_config_stmt = select(AgentLLMConfig).where(
            AgentLLMConfig.agent_id == db_agent.id, AgentLLMConfig.enabled, AgentLLMConfig.is_default
        )
        llm_config_result = await db.execute(llm_config_stmt)
        default_llm_config = llm_config_result.scalar_one_or_none()

        # Prepare LLM config dict
        llm_config_dict = None
        if default_llm_config:
            llm_config_dict = {
                "provider": default_llm_config.provider,
                "model_name": default_llm_config.model_name,
                "temperature": default_llm_config.temperature,
                "max_tokens": default_llm_config.max_tokens,
                "top_p": default_llm_config.top_p,
                "api_key": default_llm_config.api_key,  # Encrypted
                "api_base": default_llm_config.api_base,
                "additional_params": default_llm_config.additional_params or {},
            }

        # Cache agent data
        agent_dict = {
            "id": str(db_agent.id),
            "agent_name": db_agent.agent_name,
            "agent_type": db_agent.agent_type,
            "description": db_agent.description,
            "avatar": db_agent.avatar,
            "system_prompt": db_agent.system_prompt,
            "llm_config": db_agent.llm_config,
            "default_llm_config": llm_config_dict,
            "tools_config": db_agent.tools_config,
            "agent_metadata": db_agent.agent_metadata,
            "observability_config": db_agent.observability_config,
            "workflow_type": db_agent.workflow_type,
            "workflow_config": db_agent.workflow_config,
            "routing_mode": getattr(db_agent, "routing_mode", "fixed") or "fixed",
            "routing_config": getattr(db_agent, "routing_config", None),
            "status": db_agent.status,
            "tenant_id": str(db_agent.tenant_id),
            "created_at": db_agent.created_at.isoformat() if db_agent.created_at else None,
            "updated_at": db_agent.updated_at.isoformat() if db_agent.updated_at else None,
        }

        await self.cache.set_agent_config(agent_name=db_agent.agent_name, config=agent_dict)

    async def _load_agent_to_memory(
        self,
        agent_name: str,
        db_agent: Agent,
        cached_data: dict[str, Any] | None,
        llm_config_id: str | None,
        db: AsyncSession,
    ) -> Any:
        """Load agent into memory with LLM client."""
        # Check if already in memory
        agent = self.agent_manager.registry.get(agent_name)

        if agent and agent.llm_client:
            logger.info(f"Agent '{agent_name}' already in memory with LLM client")
            return agent

        # Remove broken agent from memory if exists
        if agent and not agent.llm_client:
            logger.warning(f"Agent '{agent_name}' in memory but LLM client not initialized, reloading...")
            try:
                await self.agent_manager.delete_agent(agent_name)
            except Exception as e:
                logger.warning(f"Failed to remove broken agent: {e}")

        # Load LLM configuration
        llm_config, api_key, error = await self._resolve_llm_config(
            db_agent=db_agent, cached_data=cached_data, llm_config_id=llm_config_id, db=db
        )

        if error:
            return {"error": error}

        # Create agent config
        tools = []
        if db_agent.tools_config and "tools" in db_agent.tools_config:
            tools = [ToolConfig(**tool) for tool in db_agent.tools_config["tools"]]

        config = AgentConfig(
            name=db_agent.agent_name,
            description=db_agent.description or "",
            system_prompt=db_agent.system_prompt or "",
            llm_config=llm_config,
            tools=tools,
        )

        # Determine agent class
        agent_class_map = {
            "llm": LLMAgent,
            "research": ResearchAgent,
            "code": CodeAgent,
            "claude_code": ClaudeCodeAgent,
        }
        agent_class = agent_class_map.get(db_agent.agent_type.lower() if db_agent.agent_type else "llm", LLMAgent)

        # Create agent
        try:
            agent = await self.agent_manager.create_agent(
                config=config,
                agent_class=agent_class,
                api_key=api_key,
                observability_config=db_agent.observability_config or {},
            )

            logger.info(f"Agent '{agent_name}' loaded into memory")
            return agent

        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            return {"error": f"Failed to create agent: {str(e)}"}

    async def _run_routing(
        self,
        db_agent: Agent,
        query: str,
        conversation_history: list[dict[str, Any]] | None,
        db: AsyncSession,
    ) -> tuple[RoutingDecision | None, str | None, list[str]]:
        """
        Classify the query and pick the best LLM config using the model router.

        Returns:
            (RoutingDecision, selected_config_id, fallback_config_ids)
        """
        from src.models.agent_llm_config import AgentLLMConfig

        try:
            # Load all enabled configs for this agent
            stmt = (
                select(AgentLLMConfig)
                .where(AgentLLMConfig.agent_id == db_agent.id, AgentLLMConfig.enabled)
                .order_by(AgentLLMConfig.display_order, AgentLLMConfig.created_at)
            )
            result = await db.execute(stmt)
            all_configs = list(result.scalars().all())

            if not all_configs:
                return None, None, []

            # Classify the query (< 1ms, zero API cost)
            classification = classify_query(query, conversation_history)

            # Run the router
            router = get_router()
            decision = router.select(
                routing_mode=getattr(db_agent, "routing_mode", "fixed") or "fixed",
                routing_config=getattr(db_agent, "routing_config", None),
                llm_configs=all_configs,
                classification=classification,
                explicit_config_id=None,
            )

            logger.info(
                f"[routing] agent={db_agent.agent_name} {decision} "
                f"intent={classification.intent} complexity={classification.complexity:.2f}"
            )

            return decision, decision.primary_config_id, decision.fallback_config_ids

        except Exception as e:
            logger.warning(f"[routing] Failed for agent '{db_agent.agent_name}', using default: {e}")
            return None, None, []

    async def _resolve_llm_config(
        self, db_agent: Agent, cached_data: dict[str, Any] | None, llm_config_id: str | None, db: AsyncSession
    ) -> tuple[ModelConfig | None, str | None, str | None]:
        """
        Resolve LLM configuration from cache or database.

        Returns:
            Tuple of (ModelConfig, api_key, error_message)
        """
        from src.models.agent_llm_config import AgentLLMConfig

        cached_llm = cached_data.get("default_llm_config") if cached_data else None

        # Use cached config if available and no specific config requested
        if cached_llm and not llm_config_id:
            logger.info(f"Using CACHED LLM config: {cached_llm.get('provider')}/{cached_llm.get('model_name')}")

            api_key = decrypt_value(cached_llm["api_key"]) if cached_llm.get("api_key") else ""

            # Apply preset defaults for max_tokens if not configured
            max_tokens = self._get_max_tokens_with_preset_default(
                cached_llm["provider"], cached_llm["model_name"], cached_llm["max_tokens"]
            )

            llm_config = ModelConfig(
                provider=cached_llm["provider"],
                model_name=cached_llm["model_name"],
                temperature=cached_llm["temperature"],
                max_tokens=max_tokens,
                top_p=cached_llm["top_p"],
                api_key=api_key,
                api_base=cached_llm.get("api_base"),
                additional_params=cached_llm.get("additional_params") or {},
            )

            return llm_config, api_key, None

        # Load from database
        default_llm_config = None

        if llm_config_id:
            try:
                llm_config_uuid = uuid.UUID(llm_config_id)
                stmt = select(AgentLLMConfig).where(
                    AgentLLMConfig.id == llm_config_uuid, AgentLLMConfig.agent_id == db_agent.id, AgentLLMConfig.enabled
                )
                result = await db.execute(stmt)
                default_llm_config = result.scalar_one_or_none()
            except (ValueError, Exception) as e:
                logger.warning(f"Invalid llm_config_id '{llm_config_id}': {e}")

        # Try default config
        if not default_llm_config:
            stmt = select(AgentLLMConfig).where(
                AgentLLMConfig.agent_id == db_agent.id, AgentLLMConfig.enabled, AgentLLMConfig.is_default
            )
            result = await db.execute(stmt)
            default_llm_config = result.scalar_one_or_none()

        # Try any enabled config
        if not default_llm_config:
            stmt = (
                select(AgentLLMConfig)
                .where(AgentLLMConfig.agent_id == db_agent.id, AgentLLMConfig.enabled)
                .order_by(AgentLLMConfig.display_order, AgentLLMConfig.created_at)
                .limit(1)
            )
            result = await db.execute(stmt)
            default_llm_config = result.scalar_one_or_none()

        if not default_llm_config:
            error_msg = f'No LLM model configured for agent "{db_agent.agent_name}". Please configure at least one LLM model in the "LLM Configuration" tab.'
            return None, None, error_msg

        # Decrypt API key
        api_key = decrypt_value(default_llm_config.api_key) if default_llm_config.api_key else ""

        if not api_key or api_key.strip() == "":
            error_msg = f'Agent "{db_agent.agent_name}" is missing LLM API key. Please configure the LLM settings.'
            return None, None, error_msg

        # Apply preset defaults for max_tokens if not configured
        max_tokens = self._get_max_tokens_with_preset_default(
            default_llm_config.provider, default_llm_config.model_name, default_llm_config.max_tokens
        )

        llm_config = ModelConfig(
            provider=default_llm_config.provider,
            model_name=default_llm_config.model_name,
            temperature=default_llm_config.temperature,
            max_tokens=max_tokens,
            top_p=default_llm_config.top_p,
            api_key=api_key,
            api_base=default_llm_config.api_base,
            additional_params=default_llm_config.additional_params or {},
        )

        logger.info(f"Loaded LLM config: {llm_config.provider}/{llm_config.model_name} (max_tokens={max_tokens})")

        return llm_config, api_key, None
