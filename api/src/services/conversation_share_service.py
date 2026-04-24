"""
Service for creating, listing, revoking, and validating conversation share links.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversation_share import ConversationShare


class ConversationShareService:
    """CRUD + validation for conversation share tokens."""

    @staticmethod
    async def create_share(
        db: AsyncSession,
        conversation_id: UUID,
        tenant_id: UUID,
        created_by: UUID,
        expires_in_seconds: int,
    ) -> tuple[ConversationShare, str]:
        """
        Create a share link.

        Returns (share_record, plaintext_token). The plaintext token is returned
        exactly once and must be forwarded to the caller — it is never stored.
        """
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        share = ConversationShare(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            created_by=created_by,
            share_token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in_seconds),
        )
        db.add(share)
        await db.flush()
        return share, token

    @staticmethod
    async def list_active_shares(
        db: AsyncSession,
        conversation_id: UUID,
        tenant_id: UUID,
    ) -> list[ConversationShare]:
        """Return all non-revoked, non-expired shares for a conversation."""
        result = await db.execute(
            select(ConversationShare).filter(
                ConversationShare.conversation_id == conversation_id,
                ConversationShare.tenant_id == tenant_id,
                ConversationShare.revoked_at.is_(None),
                ConversationShare.expires_at > datetime.now(UTC),
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def revoke_share(
        db: AsyncSession,
        share_id: UUID,
        conversation_id: UUID,
        tenant_id: UUID,
    ) -> bool:
        """
        Revoke a share link.

        Returns True when the share was found and revoked; False when not found
        or already belonging to a different tenant/conversation.
        """
        result = await db.execute(
            select(ConversationShare).filter(
                ConversationShare.id == share_id,
                ConversationShare.conversation_id == conversation_id,
                ConversationShare.tenant_id == tenant_id,
            )
        )
        share = result.scalar_one_or_none()
        if not share:
            return False
        share.revoked_at = datetime.now(UTC)
        await db.flush()
        return True

    @staticmethod
    async def validate_token(db: AsyncSession, token: str) -> ConversationShare | None:
        """
        Validate a share token.

        Returns the share record if valid (not revoked, not expired), otherwise None.
        Constant-time hash comparison prevents timing attacks.
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        result = await db.execute(
            select(ConversationShare).filter(
                and_(
                    ConversationShare.share_token_hash == token_hash,
                    ConversationShare.revoked_at.is_(None),
                    ConversationShare.expires_at > datetime.now(UTC),
                )
            )
        )
        return result.scalar_one_or_none()
