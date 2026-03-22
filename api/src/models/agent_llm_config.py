"""
Agent LLM Config Model

Database model for storing multiple LLM configurations per agent.
"""

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel, TenantMixin


class AgentLLMConfig(BaseModel, TenantMixin):
    """
    Agent LLM Configuration model for storing multiple LLM configs per agent.

    Attributes:
        agent_id: Foreign key to agent
        name: Display name for the configuration
        provider: LLM provider (google, OPENAI, anthropic, LITELLM)
        model_name: Model name
        api_key: Encrypted API key
        api_base: API base URL (for LiteLLM)
        temperature: Temperature setting
        max_tokens: Maximum tokens
        top_p: Top P setting
        additional_params: Additional parameters as JSON
        is_default: Whether this is the default configuration
        display_order: Display order for UI
        enabled: Whether this configuration is enabled
    """

    __tablename__ = "agent_llm_configs"

    agent_id = Column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True, comment="Agent ID"
    )

    name = Column(String(255), nullable=False, comment="Display name for the LLM config")

    provider = Column(String(50), nullable=False, comment="LLM provider (google, OPENAI, anthropic, LITELLM)")

    model_name = Column(String(255), nullable=False, comment="Model name")

    api_key = Column(Text, nullable=False, comment="Encrypted API key")

    api_base = Column(String(500), nullable=True, comment="API base URL for LiteLLM")

    temperature = Column(Float, nullable=True, default=0.7, comment="Temperature setting")

    max_tokens = Column(Integer, nullable=True, comment="Maximum tokens")

    top_p = Column(Float, nullable=True, comment="Top P setting")

    additional_params = Column(JSONB, nullable=True, comment="Additional parameters")

    is_default = Column(
        Boolean, nullable=False, default=False, index=True, comment="Whether this is the default config"
    )

    display_order = Column(Integer, nullable=False, default=0, comment="Display order")

    enabled = Column(Boolean, nullable=False, default=True, index=True, comment="Whether this config is enabled")

    # Relationships
    agent = relationship("Agent", back_populates="llm_configs")

    def __repr__(self) -> str:
        """String representation of agent LLM config."""
        return f"<AgentLLMConfig(id={self.id}, agent_id={self.agent_id}, name='{self.name}', provider='{self.provider}', model='{self.model_name}', is_default={self.is_default})>"

    def to_dict(self, exclude: set[str] | None = None, include_api_key: bool = False) -> dict:
        """
        Convert to dictionary, excluding sensitive data by default.

        Args:
            exclude: Additional fields to exclude
            include_api_key: Whether to include the API key (default: False)

        Returns:
            Dictionary representation of the LLM config
        """
        exclude = exclude or set()

        # Always exclude API key unless explicitly requested
        if not include_api_key:
            exclude.add("api_key")

        data = super().to_dict(exclude=exclude)
        return data

    def to_model_config_dict(self) -> dict:
        """
        Convert to ModelConfig-compatible dictionary for use with LLM client.

        Returns:
            Dictionary compatible with ModelConfig structure
        """
        return {
            "provider": self.provider,
            "model_name": self.model_name,
            "api_key": self.api_key,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "api_base": self.api_base,
            "additional_params": self.additional_params or {},
        }
