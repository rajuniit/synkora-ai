"""
Pydantic schemas for agent LLM configurations.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentLLMConfigBase(BaseModel):
    """Base schema for agent LLM configuration."""

    name: str = Field(..., description="Display name for the LLM config")
    provider: str = Field(..., description="LLM provider (google, openai, anthropic, litellm)")
    model_name: str = Field(..., description="Model name")
    api_base: str | None = Field(None, description="API base URL for LiteLLM")
    temperature: float | None = Field(0.7, description="Temperature setting")
    max_tokens: int | None = Field(None, description="Maximum tokens")
    top_p: float | None = Field(None, description="Top P setting")
    additional_params: dict | None = Field(default_factory=dict, description="Additional parameters")
    is_default: bool = Field(False, description="Whether this is the default config")
    display_order: int = Field(0, description="Display order")
    enabled: bool = Field(True, description="Whether this config is enabled")


class AgentLLMConfigCreate(AgentLLMConfigBase):
    """Schema for creating an agent LLM configuration."""

    api_key: str = Field(..., description="API key for the LLM provider")


class AgentLLMConfigUpdate(BaseModel):
    """Schema for updating an agent LLM configuration."""

    name: str | None = Field(None, description="Display name for the LLM config")
    provider: str | None = Field(None, description="LLM provider")
    model_name: str | None = Field(None, description="Model name")
    api_key: str | None = Field(None, description="API key for the LLM provider")
    api_base: str | None = Field(None, description="API base URL for LiteLLM")
    temperature: float | None = Field(None, description="Temperature setting")
    max_tokens: int | None = Field(None, description="Maximum tokens")
    top_p: float | None = Field(None, description="Top P setting")
    additional_params: dict | None = Field(None, description="Additional parameters")
    is_default: bool | None = Field(None, description="Whether this is the default config")
    display_order: int | None = Field(None, description="Display order")
    enabled: bool | None = Field(None, description="Whether this config is enabled")


class AgentLLMConfigResponse(AgentLLMConfigBase):
    """Schema for agent LLM configuration response."""

    id: UUID
    agent_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentLLMConfigReorder(BaseModel):
    """Schema for reordering LLM configurations."""

    config_orders: list[dict] = Field(
        ...,
        description="List of config IDs and their new display orders",
        json_schema_extra={"example": [{"id": "uuid-here", "display_order": 0}]},
    )
