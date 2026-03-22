"""
Shared models for agent controllers.

Contains common request/response models used across multiple agent controller modules.
"""

from typing import Any

from pydantic import BaseModel, Field

from src.services.agents.config import AgentConfig, WorkflowConfig


class AgentResponse(BaseModel):
    """Response model for agent operations."""

    success: bool
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class CreateAgentRequest(BaseModel):
    """Request model for creating an agent."""

    config: AgentConfig
    agent_type: str = Field(..., description="Agent type: llm, research, code, or claude_code")
    api_key: str | None = Field(None, description="Google API key")
    is_public: bool = Field(default=False, description="Whether agent is public in marketplace")
    category: str | None = Field(None, description="Agent category for marketplace")
    tags: list[str] | None = Field(None, description="Tags for agent discovery")
    role_id: str | None = Field(None, description="Optional role template ID for role-based agents")
    human_contact_id: str | None = Field(None, description="Optional human contact ID for escalation")


class UpdateAgentRequest(BaseModel):
    """Request model for updating an agent."""

    description: str | None = Field(None, description="Agent description")
    avatar: str | None = Field(None, description="Agent avatar URL")
    system_prompt: str | None = Field(None, description="System prompt")
    llm_config: dict[str, Any] | None = Field(None, description="LLM configuration")
    tools_config: dict[str, Any] | None = Field(None, description="Tools configuration")
    observability_config: dict[str, Any] | None = Field(None, description="Observability configuration")
    suggestion_prompts: list[dict[str, Any]] | None = Field(
        None,
        description="Suggestion prompts for chat interface (array of objects with title, description, icon, prompt)",
    )
    status: str | None = Field(None, description="Agent status")
    is_public: bool | None = Field(None, description="Whether agent is public in marketplace")
    category: str | None = Field(None, description="Agent category for marketplace")
    tags: list[str] | None = Field(None, description="Tags for agent discovery")
    voice_enabled: bool | None = Field(None, description="Whether voice chat is enabled")
    voice_config: dict[str, Any] | None = Field(
        None, description="Voice configuration (STT/TTS providers, voice settings)"
    )
    agent_metadata: dict[str, Any] | None = Field(
        None, description="Agent metadata including performance_config for caching, RAG, and context files settings"
    )
    is_adk_workflow_enabled: bool | None = Field(None, description="Whether ADK workflow is enabled")
    workflow_type: str | None = Field(None, description="Workflow type (sequential, parallel, loop)")
    workflow_config: dict[str, Any] | None = Field(None, description="Workflow configuration")
    role_id: str | None = Field(None, description="Optional role template ID for role-based agents")
    human_contact_id: str | None = Field(None, description="Optional human contact ID for escalation")


class ExecuteAgentRequest(BaseModel):
    """Request model for executing an agent."""

    agent_name: str = Field(..., description="Name of the agent to execute")
    input_data: dict[str, Any] = Field(..., description="Input data for the agent")


class ExecuteWorkflowRequest(BaseModel):
    """Request model for executing a workflow."""

    workflow_config: WorkflowConfig
    input_data: dict[str, Any] = Field(..., description="Initial input data")


class ChatRequest(BaseModel):
    """Request model for chat with streaming."""

    agent_name: str = Field(..., description="Name of the agent")
    message: str = Field(..., description="User message")
    conversation_history: list[dict[str, str]] | None = Field(None, description="Conversation history")
    conversation_id: str | None = Field(None, description="Conversation ID for history")
    attachments: list[dict[str, Any]] | None = Field(None, description="File attachments metadata")
    llm_config_id: str | None = Field(None, description="Optional LLM config ID to use for this chat")


class UploadAttachmentRequest(BaseModel):
    """Request model for uploading chat attachment."""

    conversation_id: str = Field(..., description="Conversation ID")


class CreateConversationRequest(BaseModel):
    """Request model for creating a conversation."""

    agent_id: str = Field(..., description="UUID of the agent")
    name: str = Field(default="New Conversation", description="Conversation name")
    session_id: str | None = Field(None, description="Session ID for tracking")


class AttachMCPServerRequest(BaseModel):
    """Request model for attaching an MCP server to an agent."""

    mcp_server_id: str = Field(..., description="UUID of the MCP server")
    mcp_config: dict[str, Any] | None = Field(
        None, description="MCP configuration (enabled_tools, timeout, max_retries, tool_config, etc.)"
    )


class AttachKnowledgeBaseRequest(BaseModel):
    """Request model for attaching a knowledge base to an agent."""

    knowledge_base_id: int = Field(..., description="ID of the knowledge base")
    retrieval_config: dict[str, Any] | None = Field(
        None, description="Retrieval configuration (max_results, min_score, max_context_tokens, etc.)"
    )


class CloneAgentRequest(BaseModel):
    """Request model for cloning an agent."""

    new_name: str = Field(..., description="Name for the cloned agent")
    new_api_key: str | None = Field(
        None, description="New API key for LLM (if not provided, requires re-configuration)"
    )
    clone_tools: bool = Field(default=True, description="Whether to clone tool configurations")
    clone_knowledge_bases: bool = Field(
        default=False,
        description="Whether to link same knowledge bases (Note: OAuth-based data sources will require re-authorization)",
    )
    clone_sub_agents: bool = Field(default=False, description="Whether to clone sub-agent relationships")
    clone_workflows: bool = Field(default=True, description="Whether to clone workflow configurations")
