"""
Service for managing agent LLM configurations.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_llm_config import AgentLLMConfig
from src.services.agents.security import decrypt_value, encrypt_value


class LLMConfigService:
    """Service for managing agent LLM configurations."""

    @staticmethod
    async def create_config(
        session: AsyncSession,
        agent_id: UUID,
        tenant_id: UUID,
        name: str,
        provider: str,
        model_name: str,
        api_key: str,
        api_base: str | None = None,
        temperature: float | None = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        additional_params: dict | None = None,
        is_default: bool = False,
        display_order: int = 0,
        enabled: bool = True,
        routing_rules: dict | None = None,
        routing_weight: float | None = None,
    ) -> AgentLLMConfig:
        """Create a new LLM configuration."""

        # If this is set as default, unset other defaults for this agent
        if is_default:
            await LLMConfigService._unset_default_configs(session, agent_id)

        # Encrypt the API key
        encrypted_api_key = encrypt_value(api_key)

        config = AgentLLMConfig(
            agent_id=agent_id,
            tenant_id=tenant_id,
            name=name,
            provider=provider,
            model_name=model_name,
            api_key=encrypted_api_key,
            api_base=api_base,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            additional_params=additional_params or {},
            is_default=is_default,
            display_order=display_order,
            enabled=enabled,
            routing_rules=routing_rules,
            routing_weight=routing_weight,
        )

        session.add(config)
        await session.flush()

        return config

    @staticmethod
    async def get_config(session: AsyncSession, config_id: UUID, tenant_id: UUID) -> AgentLLMConfig | None:
        """Get a specific LLM configuration."""
        result = await session.execute(
            select(AgentLLMConfig).filter(AgentLLMConfig.id == config_id, AgentLLMConfig.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_agent_configs(
        session: AsyncSession, agent_id: UUID, tenant_id: UUID, enabled_only: bool = False
    ) -> list[AgentLLMConfig]:
        """Get all LLM configurations for an agent."""
        query = select(AgentLLMConfig).filter(
            AgentLLMConfig.agent_id == agent_id, AgentLLMConfig.tenant_id == tenant_id
        )

        if enabled_only:
            query = query.filter(AgentLLMConfig.enabled)

        query = query.order_by(AgentLLMConfig.display_order, AgentLLMConfig.created_at)

        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_default_config(session: AsyncSession, agent_id: UUID, tenant_id: UUID) -> AgentLLMConfig | None:
        """Get the default LLM configuration for an agent."""
        result = await session.execute(
            select(AgentLLMConfig).filter(
                AgentLLMConfig.agent_id == agent_id,
                AgentLLMConfig.tenant_id == tenant_id,
                AgentLLMConfig.is_default,
                AgentLLMConfig.enabled,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_config(
        session: AsyncSession, config_id: UUID, tenant_id: UUID, **updates
    ) -> AgentLLMConfig | None:
        """Update an LLM configuration."""
        config = await LLMConfigService.get_config(session, config_id, tenant_id)

        if not config:
            return None

        # If setting as default, unset other defaults
        if updates.get("is_default"):
            await LLMConfigService._unset_default_configs(session, config.agent_id)

        # Encrypt API key if provided; auto-enable config when a valid key is saved
        if "api_key" in updates and updates["api_key"]:
            updates["api_key"] = encrypt_value(updates["api_key"])
            if "enabled" not in updates:
                updates["enabled"] = True

        # Update fields
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)

        await session.flush()

        return config

    @staticmethod
    async def delete_config(session: AsyncSession, config_id: UUID, tenant_id: UUID) -> bool:
        """Delete an LLM configuration."""
        config = await LLMConfigService.get_config(session, config_id, tenant_id)

        if not config:
            return False

        # Don't allow deleting the default config if it's the only one
        if config.is_default:
            configs = await LLMConfigService.get_agent_configs(session, config.agent_id, tenant_id)
            if len(configs) == 1:
                raise ValueError("Cannot delete the only LLM configuration")

            # Set another config as default
            for other_config in configs:
                if other_config.id != config_id:
                    other_config.is_default = True
                    break

        await session.delete(config)
        await session.flush()

        return True

    @staticmethod
    async def set_default_config(session: AsyncSession, config_id: UUID, tenant_id: UUID) -> AgentLLMConfig | None:
        """Set a configuration as the default."""
        config = await LLMConfigService.get_config(session, config_id, tenant_id)

        if not config:
            return None

        # Unset other defaults
        await LLMConfigService._unset_default_configs(session, config.agent_id)

        # Set this as default
        config.is_default = True
        await session.flush()

        return config

    @staticmethod
    async def reorder_configs(
        session: AsyncSession,
        agent_id: UUID,
        tenant_id: UUID,
        config_orders: list[dict],  # [{"id": UUID, "display_order": int}, ...]
    ) -> list[AgentLLMConfig]:
        """Reorder LLM configurations."""
        configs = await LLMConfigService.get_agent_configs(session, agent_id, tenant_id)
        config_map = {str(c.id): c for c in configs}

        for order_data in config_orders:
            config_id = str(order_data["id"])
            if config_id in config_map:
                config_map[config_id].display_order = order_data["display_order"]

        await session.flush()

        return await LLMConfigService.get_agent_configs(session, agent_id, tenant_id)

    @staticmethod
    def get_decrypted_api_key(config: AgentLLMConfig) -> str:
        """Get the decrypted API key from a configuration."""
        return decrypt_value(config.api_key)

    @staticmethod
    async def _unset_default_configs(session: AsyncSession, agent_id: UUID):
        """Unset all default configurations for an agent."""
        result = await session.execute(
            select(AgentLLMConfig).filter(AgentLLMConfig.agent_id == agent_id, AgentLLMConfig.is_default)
        )
        configs = list(result.scalars().all())

        for config in configs:
            config.is_default = False
