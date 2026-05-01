"""
Public (unauthenticated) endpoint for accessing shared conversations.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.services.conversation_share_service import ConversationShareService

logger = logging.getLogger(__name__)

share_public_router = APIRouter()


@share_public_router.get("/api/v1/public/share/{token}")
async def get_shared_conversation(
    token: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Return a shared conversation's messages without authentication.

    Hashes the incoming token, validates it against the store, and returns
    conversation + messages (up to 500). Returns 404 for missing, expired,
    or revoked tokens.
    """
    try:
        share = await ConversationShareService.validate_token(db, token)
        if not share:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found or expired")

        from src.models.agent import Agent
        from src.models.conversation import Conversation
        from src.models.message import Message

        # Load conversation
        conv_result = await db.execute(select(Conversation).filter(Conversation.id == share.conversation_id))
        conversation = conv_result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

        # Load messages (cap at 500)
        msg_result = await db.execute(
            select(Message)
            .filter(Message.conversation_id == share.conversation_id)
            .order_by(Message.created_at.asc())
            .limit(500)
        )
        messages = msg_result.scalars().all()

        # Load agent info for display
        agent_info: dict = {}
        if conversation.agent_id:
            agent_result = await db.execute(select(Agent).filter(Agent.id == conversation.agent_id))
            agent = agent_result.scalar_one_or_none()
            if agent:
                if str(agent.tenant_id) != str(share.tenant_id):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found or expired")
                agent_info = {
                    "name": getattr(agent, "agent_name", None),
                    "avatar": getattr(agent, "avatar", None),
                    "description": getattr(agent, "description", None),
                }

        return {
            "success": True,
            "data": {
                "conversation": conversation.to_dict(),
                "messages": [msg.to_dict() for msg in messages],
                "agent": agent_info,
                "expires_at": share.expires_at.isoformat(),
                "share_id": str(share.id),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load shared conversation: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load conversation")
