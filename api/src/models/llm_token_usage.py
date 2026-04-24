"""
LLM Token Usage model.

Tracks per-call LLM token consumption and estimated cost for analytics,
billing accuracy, and cost-optimization reporting.

No FK constraints — this table must survive agent/conversation deletion.
"""

from sqlalchemy import Column, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import BaseModel


class LLMTokenUsage(BaseModel):
    """Per-call LLM token and cost record."""

    __tablename__ = "llm_token_usages"

    tenant_id = Column(UUID(as_uuid=True), nullable=False, comment="Tenant ID")
    agent_id = Column(UUID(as_uuid=True), nullable=True, comment="Agent ID (no FK — survives deletion)")
    conversation_id = Column(UUID(as_uuid=True), nullable=True, comment="Conversation ID (no FK)")

    provider = Column(String(50), nullable=False, comment="LLM provider (openai, anthropic, google...)")
    model_name = Column(String(255), nullable=False, comment="Model name as used in the API call")

    # Token counts
    input_tokens = Column(Integer, nullable=False, server_default="0", comment="Prompt tokens billed at full rate")
    output_tokens = Column(Integer, nullable=False, server_default="0", comment="Completion tokens")

    # Anthropic prompt-caching tokens (different billing rates)
    cache_read_tokens = Column(Integer, nullable=True, comment="Anthropic cache_read_input_tokens (10% of input rate)")
    cache_creation_tokens = Column(
        Integer, nullable=True, comment="Anthropic cache_creation_input_tokens (125% of input rate)"
    )

    # OpenAI automatic caching
    cached_input_tokens = Column(Integer, nullable=True, comment="OpenAI prompt_tokens_details.cached_tokens (50% off)")

    estimated_cost_usd = Column(Numeric(12, 8), nullable=True, comment="Estimated USD cost for this call")

    optimization_flags = Column(
        JSONB,
        nullable=True,
        comment=("Optimization metadata: {prompt_cache_hit, response_cache_hit, routing_mode, batch_id, batch_status}"),
    )

    __table_args__ = (
        # Analytics time-range queries (e.g. cost last 7 days)
        Index("ix_llm_usage_tenant_created", "tenant_id", "created_at"),
        # Per-agent drill-down
        Index("ix_llm_usage_tenant_agent_created", "tenant_id", "agent_id", "created_at"),
        # Per-model breakdown
        Index("ix_llm_usage_tenant_model", "tenant_id", "model_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<LLMTokenUsage(id={self.id}, model={self.model_name}, "
            f"in={self.input_tokens}, out={self.output_tokens}, "
            f"cost=${self.estimated_cost_usd})>"
        )
