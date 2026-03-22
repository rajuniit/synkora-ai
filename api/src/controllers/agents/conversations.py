"""
Agent API endpoints.

Provides REST API endpoints for managing and executing Google Agent SDK agents.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.controllers.agents.models import AgentResponse, CreateConversationRequest
from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_account, get_current_tenant_id
from src.models.agent import Agent
from src.models.tenant import Account
from src.services.agents.agent_manager import AgentManager

logger = logging.getLogger(__name__)

# Create router
agents_conversations_router = APIRouter()

# Global agent manager instance
agent_manager = AgentManager()


# Conversation Management Endpoints


@agents_conversations_router.post("/conversations", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: CreateConversationRequest,
    current_account: Account = Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a new conversation for an agent.

    Args:
        request: Conversation creation request
        current_account: Current authenticated user
        tenant_id: Tenant ID from JWT token
        db: Database session

    Returns:
        Created conversation details
    """
    try:
        from sqlalchemy import or_

        from src.services.billing import ChatBillingService
        from src.services.conversation_service import ConversationService

        # Convert agent_id to UUID
        try:
            agent_uuid = uuid.UUID(request.agent_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent ID format")

        # BILLING: Validate billing requirements for conversation creation
        billing_service = ChatBillingService(db)
        billing_result = await billing_service.validate_conversation_creation(tenant_id, current_account.id)
        if not billing_result.is_valid:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": billing_result.error.error_code.value,
                    "message": billing_result.error.message,
                    "error_code": billing_result.error.error_code.value,
                    **(billing_result.error.details or {}),
                },
            )

        # SECURITY: Single OR query to prevent timing attacks
        # Checks: (agent belongs to tenant) OR (agent is public)
        result = await db.execute(
            select(Agent).filter(Agent.id == agent_uuid, or_(Agent.tenant_id == tenant_id, Agent.is_public.is_(True)))
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent with ID '{request.agent_id}' not found"
            )

        # Create conversation with current user's account_id
        conversation = await ConversationService.create_conversation(
            db=db,
            app_id=tenant_id,  # Using tenant ID as app_id
            agent_id=agent_uuid,
            session_id=request.session_id,
            name=request.name,
            account_id=current_account.id,  # Associate with current user
        )

        return AgentResponse(success=True, message="Conversation created successfully", data=conversation.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create conversation: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create conversation")


@agents_conversations_router.get("/{agent_id}/conversations", response_model=AgentResponse)
async def list_agent_conversations(
    agent_id: str,
    limit: int = 50,
    current_account: Account = Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """
    List all conversations for an agent.

    Args:
        agent_id: UUID of the agent
        limit: Maximum number of conversations to return
        current_account: Current authenticated user
        tenant_id: Tenant ID from JWT token
        db: Database session

    Returns:
        List of conversations
    """
    try:
        from sqlalchemy import or_

        # Convert agent_id to UUID
        try:
            agent_uuid = uuid.UUID(agent_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent ID format")

        # SECURITY: Single OR query to prevent timing attacks
        # Checks: (agent belongs to tenant) OR (agent is public)
        result = await db.execute(
            select(Agent).filter(Agent.id == agent_uuid, or_(Agent.tenant_id == tenant_id, Agent.is_public.is_(True)))
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent with ID '{agent_id}' not found")

        # Get conversations - SECURITY: Only get conversations for the current USER (account_id)
        from src.models.conversation import Conversation

        result = await db.execute(
            select(Conversation)
            .filter(
                Conversation.agent_id == agent_uuid,
                Conversation.account_id == current_account.id,  # Only show current user's conversations
            )
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        conversations = result.scalars().all()

        conversations_list = [conv.to_dict() for conv in conversations]

        return AgentResponse(
            success=True,
            message=f"Found {len(conversations_list)} conversations",
            data={"conversations": conversations_list},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list conversations: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list conversations")


@agents_conversations_router.get("/conversations/{conversation_id}", response_model=AgentResponse)
async def get_conversation(
    conversation_id: str,
    include_messages: bool = False,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get a specific conversation.

    Args:
        conversation_id: UUID of the conversation
        include_messages: Whether to include messages
        current_account: Current authenticated user
        db: Database session

    Returns:
        Conversation details
    """
    try:
        from src.models.conversation import Conversation
        from src.services.conversation_service import ConversationService

        # Convert conversation_id to UUID
        try:
            conversation_uuid = uuid.UUID(conversation_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation ID format")

        # SECURITY: Get conversation and verify it belongs to current USER (account_id)
        result = await db.execute(
            select(Conversation).filter(
                Conversation.id == conversation_uuid,
                Conversation.account_id
                == current_account.id,  # SECURITY: Only allow access to user's own conversations
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Conversation with ID '{conversation_id}' not found"
            )

        # Get full conversation with messages if needed
        conversation = await ConversationService.get_conversation(
            db=db, conversation_id=conversation_uuid, include_messages=include_messages
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Conversation with ID '{conversation_id}' not found"
            )

        return AgentResponse(
            success=True,
            message="Conversation retrieved successfully",
            data=conversation.to_dict(include_messages=include_messages),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get conversation")


class UpdateConversationRequest(BaseModel):
    """Request model for updating a conversation."""

    name: str | None = Field(None, description="New conversation name")
    summary: str | None = Field(None, description="Conversation summary")


@agents_conversations_router.put("/conversations/{conversation_id}", response_model=AgentResponse)
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Update a conversation.

    Args:
        conversation_id: UUID of the conversation
        request: Update request
        current_account: Current authenticated user
        db: Database session

    Returns:
        Updated conversation details
    """
    try:
        from src.models.conversation import Conversation
        from src.services.conversation_service import ConversationService

        # Convert conversation_id to UUID
        try:
            conversation_uuid = uuid.UUID(conversation_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation ID format")

        # SECURITY: Verify conversation belongs to current USER (account_id)
        result = await db.execute(
            select(Conversation).filter(
                Conversation.id == conversation_uuid,
                Conversation.account_id == current_account.id,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Conversation with ID '{conversation_id}' not found"
            )

        # Update conversation
        conversation = await ConversationService.update_conversation(
            db=db, conversation_id=conversation_uuid, name=request.name, summary=request.summary
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Conversation with ID '{conversation_id}' not found"
            )

        return AgentResponse(success=True, message="Conversation updated successfully", data=conversation.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update conversation: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update conversation")


@agents_conversations_router.delete("/conversations/{conversation_id}", response_model=AgentResponse)
async def delete_conversation(
    conversation_id: str,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Delete a conversation.

    Args:
        conversation_id: UUID of the conversation
        current_account: Current authenticated user
        db: Database session

    Returns:
        Deletion confirmation
    """
    try:
        from src.models.conversation import Conversation
        from src.services.conversation_service import ConversationService

        # Convert conversation_id to UUID
        try:
            conversation_uuid = uuid.UUID(conversation_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation ID format")

        # SECURITY: Verify conversation belongs to current USER (account_id)
        result = await db.execute(
            select(Conversation).filter(
                Conversation.id == conversation_uuid,
                Conversation.account_id == current_account.id,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Conversation with ID '{conversation_id}' not found"
            )

        # Delete conversation
        deleted = await ConversationService.delete_conversation(
            db=db, conversation_id=conversation_uuid, soft_delete=True
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Conversation with ID '{conversation_id}' not found"
            )

        return AgentResponse(success=True, message="Conversation deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete conversation")


@agents_conversations_router.get("/conversations/{conversation_id}/messages", response_model=AgentResponse)
async def get_conversation_messages(
    conversation_id: str,
    limit: int | None = None,
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get messages for a conversation.

    Args:
        conversation_id: UUID of the conversation
        limit: Maximum number of messages to return
        current_account: Current authenticated user
        db: Database session

    Returns:
        List of messages
    """
    try:
        from src.models.conversation import Conversation
        from src.services.conversation_service import ConversationService

        # Convert conversation_id to UUID
        try:
            conversation_uuid = uuid.UUID(conversation_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation ID format")

        # SECURITY: Verify conversation belongs to current USER (account_id)
        result = await db.execute(
            select(Conversation).filter(
                Conversation.id == conversation_uuid,
                Conversation.account_id
                == current_account.id,  # SECURITY: Only allow access to user's own conversations
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Conversation with ID '{conversation_id}' not found"
            )

        # Get messages
        messages = await ConversationService.get_conversation_messages(
            db=db, conversation_id=conversation_uuid, limit=limit
        )

        messages_list = [msg.to_dict() for msg in messages]

        return AgentResponse(
            success=True, message=f"Found {len(messages_list)} messages", data={"messages": messages_list}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation messages: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get messages")
