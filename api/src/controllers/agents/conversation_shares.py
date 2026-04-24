"""
Authenticated endpoints for managing conversation share links.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_account, get_current_tenant_id
from src.models.conversation import Conversation
from src.models.tenant import Account
from src.services.conversation_share_service import ConversationShareService

logger = logging.getLogger(__name__)

conversation_shares_router = APIRouter()


class CreateShareRequest(BaseModel):
    expires_in_seconds: int = Field(..., gt=0, le=604800, description="TTL in seconds (max 7 days)")


async def _get_owned_conversation(
    conversation_id: str,
    current_account: Account,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> Conversation:
    """Load conversation and verify ownership."""
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation ID")

    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conv_uuid,
            Conversation.account_id == current_account.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


@conversation_shares_router.post(
    "/conversations/{conversation_id}/shares",
    status_code=status.HTTP_201_CREATED,
)
async def create_share(
    conversation_id: str,
    request: CreateShareRequest,
    current_account: Account = Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a time-limited share link for a conversation."""
    try:
        conversation = await _get_owned_conversation(conversation_id, current_account, tenant_id, db)

        from src.utils.config_helper import get_app_base_url

        share, token = await ConversationShareService.create_share(
            db=db,
            conversation_id=conversation.id,
            tenant_id=tenant_id,
            created_by=current_account.id,
            expires_in_seconds=request.expires_in_seconds,
        )
        await db.commit()
        await db.refresh(share)

        base_url = await get_app_base_url(db, tenant_id)
        share_url = f"{base_url.rstrip('/')}/share/{token}"

        return {
            "success": True,
            "data": {
                **share.to_dict(),
                "share_url": share_url,
                "token": token,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create share: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create share link")


@conversation_shares_router.get("/conversations/{conversation_id}/shares")
async def list_shares(
    conversation_id: str,
    current_account: Account = Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """List active share links for a conversation."""
    try:
        conversation = await _get_owned_conversation(conversation_id, current_account, tenant_id, db)

        shares = await ConversationShareService.list_active_shares(
            db=db,
            conversation_id=conversation.id,
            tenant_id=tenant_id,
        )
        return {
            "success": True,
            "data": {"shares": [s.to_dict() for s in shares]},
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list shares: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list share links")


@conversation_shares_router.delete(
    "/conversations/{conversation_id}/shares/{share_id}",
    status_code=status.HTTP_200_OK,
)
async def revoke_share(
    conversation_id: str,
    share_id: str,
    current_account: Account = Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Revoke an active share link."""
    try:
        try:
            share_uuid = uuid.UUID(share_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid share ID format")

        conversation = await _get_owned_conversation(conversation_id, current_account, tenant_id, db)

        revoked = await ConversationShareService.revoke_share(
            db=db,
            share_id=share_uuid,
            conversation_id=conversation.id,
            tenant_id=tenant_id,
        )
        if not revoked:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")

        await db.commit()
        return {"success": True, "message": "Share link revoked"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to revoke share: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to revoke share link")
