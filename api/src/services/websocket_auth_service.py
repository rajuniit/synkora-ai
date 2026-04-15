"""
WebSocket authorization service for room access control.

This service provides authorization checks for WebSocket room operations,
ensuring users can only access conversations they are authorized to view.
"""

import logging
import re
from uuid import UUID

from sqlalchemy import select

from src.core.database import get_async_session_factory
from src.models.agent import Agent
from src.models.conversation import Conversation

logger = logging.getLogger(__name__)


# Room ID patterns for different room types
CONVERSATION_ROOM_PATTERN = re.compile(r"^conversation:([a-f0-9-]+)$")
AGENT_ROOM_PATTERN = re.compile(r"^agent:([a-f0-9-]+)$")
TENANT_ROOM_PATTERN = re.compile(r"^tenant:([a-f0-9-]+)$")


async def authorize_room_access(
    room_id: str,
    user_id: UUID,
    tenant_id: UUID,
) -> bool:
    """
    Check if a user is authorized to access a WebSocket room.

    This is the main authorization callback used by the ConnectionManager.
    It handles different room types:
    - conversation:{id} - User must own the conversation or have tenant access
    - agent:{id} - User must belong to the agent's tenant
    - tenant:{id} - User must belong to that tenant

    Args:
        room_id: The room identifier (format: type:uuid)
        user_id: The user attempting to access the room
        tenant_id: The tenant the user belongs to

    Returns:
        True if access is authorized, False otherwise
    """
    # Check conversation rooms
    conversation_match = CONVERSATION_ROOM_PATTERN.match(room_id)
    if conversation_match:
        conversation_id = conversation_match.group(1)
        return await _authorize_conversation_access(conversation_id, user_id, tenant_id)

    # Check agent rooms
    agent_match = AGENT_ROOM_PATTERN.match(room_id)
    if agent_match:
        agent_id = agent_match.group(1)
        return await _authorize_agent_access(agent_id, tenant_id)

    # Check tenant rooms - user must belong to that tenant
    tenant_match = TENANT_ROOM_PATTERN.match(room_id)
    if tenant_match:
        room_tenant_id = tenant_match.group(1)
        return str(tenant_id) == room_tenant_id

    # Unknown room type - deny by default for security
    logger.warning(f"Unknown room type for room_id={room_id}, denying access for user={user_id}")
    return False


async def _authorize_conversation_access(
    conversation_id: str,
    user_id: UUID,
    tenant_id: UUID,
) -> bool:
    """
    Check if a user can access a conversation room.

    Authorization rules:
    1. User owns the conversation (account_id matches)
    2. OR the conversation belongs to an agent in the user's tenant
    3. OR the agent is public (is_public=True)

    Args:
        conversation_id: The conversation UUID
        user_id: The user attempting access
        tenant_id: The user's tenant

    Returns:
        True if authorized, False otherwise
    """
    try:
        conversation_uuid = UUID(conversation_id)
    except ValueError:
        logger.warning(f"Invalid conversation UUID: {conversation_id}")
        return False

    async with get_async_session_factory()() as db:
        try:
            # Get conversation with agent relationship
            stmt = select(Conversation).filter(Conversation.id == conversation_uuid)
            result = await db.execute(stmt)
            conversation = result.scalar_one_or_none()

            if not conversation:
                logger.debug(f"Conversation not found: {conversation_id}")
                return False

            # Rule 1: User owns the conversation
            if conversation.account_id == user_id:
                return True

            # Rule 2 & 3: Check agent tenant or public status
            if conversation.agent_id:
                stmt = select(Agent).filter(Agent.id == conversation.agent_id)
                result = await db.execute(stmt)
                agent = result.scalar_one_or_none()

                if agent:
                    # User belongs to agent's tenant
                    if agent.tenant_id == tenant_id:
                        return True

                    # Agent is public
                    if agent.is_public:
                        return True

            logger.debug(f"User {user_id} not authorized for conversation {conversation_id}")
            return False

        except Exception as e:
            logger.error(f"Error checking conversation authorization: {e}")
            return False


async def _authorize_agent_access(
    agent_id: str,
    tenant_id: UUID,
) -> bool:
    """
    Check if a user can access an agent room.

    Authorization rules:
    1. Agent belongs to user's tenant
    2. OR agent is public

    Args:
        agent_id: The agent UUID
        tenant_id: The user's tenant

    Returns:
        True if authorized, False otherwise
    """
    try:
        agent_uuid = UUID(agent_id)
    except ValueError:
        logger.warning(f"Invalid agent UUID: {agent_id}")
        return False

    async with get_async_session_factory()() as db:
        try:
            stmt = select(Agent).filter(Agent.id == agent_uuid)
            result = await db.execute(stmt)
            agent = result.scalar_one_or_none()

            if not agent:
                logger.debug(f"Agent not found: {agent_id}")
                return False

            # User belongs to agent's tenant
            if agent.tenant_id == tenant_id:
                return True

            # Agent is public
            if agent.is_public:
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking agent authorization: {e}")
            return False


def setup_websocket_authorization() -> None:
    """
    Configure the WebSocket connection manager with authorization.

    This should be called during application startup to enable
    room access authorization checks.
    """
    from src.core.websocket import connection_manager

    connection_manager.set_room_authorization_callback(authorize_room_access)
    logger.info("WebSocket room authorization configured")
