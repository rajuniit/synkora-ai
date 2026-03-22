"""Microsoft Teams Bot API endpoints."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..core.database import get_async_db
from ..middleware.auth_middleware import get_current_tenant_id
from ..models.agent import Agent
from ..models.teams_bot import TeamsBot
from ..services.agents.security import encrypt_value
from ..services.teams import TeamsWebhookService

logger = logging.getLogger(__name__)

teams_router = APIRouter()


# Request/Response Models
class CreateTeamsBotRequest(BaseModel):
    """Request model for creating a Teams bot."""

    agent_id: str = Field(..., description="UUID of the agent")
    bot_name: str = Field(..., description="Human-readable name for the bot")
    app_id: str = Field(..., description="Microsoft App ID")
    app_password: str = Field(..., description="Microsoft App Password")
    bot_id: str = Field(..., description="Teams Bot ID")
    webhook_url: str | None = Field(None, description="Webhook URL")
    welcome_message: str | None = Field(None, description="Message sent when bot joins")


class UpdateTeamsBotRequest(BaseModel):
    """Request model for updating a Teams bot."""

    bot_name: str | None = None
    app_password: str | None = None
    webhook_url: str | None = None
    welcome_message: str | None = None
    is_active: bool | None = None


class TeamsBotResponse(BaseModel):
    """Response model for Teams bot operations."""

    success: bool
    message: str
    data: dict = Field(default_factory=dict)


@teams_router.post("/teams-bots", response_model=TeamsBotResponse, status_code=status.HTTP_201_CREATED)
async def create_teams_bot(
    request: CreateTeamsBotRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new Teams bot for an agent."""
    try:
        agent_uuid = uuid.UUID(request.agent_id)

        # Verify agent exists and belongs to tenant
        result = await db.execute(select(Agent).filter(Agent.id == agent_uuid, Agent.tenant_id == tenant_id))
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent with ID '{request.agent_id}' not found"
            )

        # Encrypt sensitive data
        encrypted_password = encrypt_value(request.app_password)

        # Create Teams bot
        bot = TeamsBot(
            agent_id=agent_uuid,
            tenant_id=agent.tenant_id,
            bot_name=request.bot_name,
            app_id=request.app_id,
            app_password=encrypted_password,
            bot_id=request.bot_id,
            webhook_url=request.webhook_url,
            welcome_message=request.welcome_message,
            is_active=True,
        )

        db.add(bot)
        await db.commit()
        await db.refresh(bot)

        return TeamsBotResponse(
            success=True,
            message=f"Teams bot '{request.bot_name}' created successfully",
            data={
                "bot_id": str(bot.id),
                "bot_name": bot.bot_name,
                "agent_id": str(bot.agent_id),
                "agent_name": agent.agent_name,
                "app_id": bot.app_id,
                "teams_bot_id": bot.bot_id,
                "webhook_url": bot.webhook_url,
                "is_active": bot.is_active,
                "created_at": bot.created_at.isoformat(),
            },
        )

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent ID format")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create Teams bot: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create Teams bot")


@teams_router.get("/teams-bots", response_model=TeamsBotResponse)
async def list_teams_bots(
    agent_id: str | None = None,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """List all Teams bots, optionally filtered by agent."""
    try:
        if agent_id:
            agent_uuid = uuid.UUID(agent_id)
            result = await db.execute(
                select(TeamsBot)
                .options(joinedload(TeamsBot.agent))
                .filter(TeamsBot.agent_id == agent_uuid, TeamsBot.tenant_id == tenant_id)
            )
            bots = result.scalars().all()
        else:
            result = await db.execute(
                select(TeamsBot).options(joinedload(TeamsBot.agent)).filter(TeamsBot.tenant_id == tenant_id)
            )
            bots = result.scalars().all()

        bots_list = []
        for bot in bots:
            bots_list.append(
                {
                    "bot_id": str(bot.id),
                    "bot_name": bot.bot_name,
                    "agent_id": str(bot.agent_id),
                    "agent_name": bot.agent.agent_name,
                    "app_id": bot.app_id,
                    "teams_bot_id": bot.bot_id,
                    "is_active": bot.is_active,
                    "last_message_at": bot.last_message_at.isoformat() if bot.last_message_at else None,
                    "created_at": bot.created_at.isoformat(),
                }
            )

        return TeamsBotResponse(success=True, message=f"Found {len(bots_list)} Teams bots", data={"bots": bots_list})

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent ID format")
    except Exception as e:
        logger.error(f"Failed to list Teams bots: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list Teams bots")


@teams_router.get("/teams-bots/{bot_id}", response_model=TeamsBotResponse)
async def get_teams_bot(
    bot_id: str, tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_async_db)
):
    """Get details of a specific Teams bot."""
    try:
        bot_uuid = uuid.UUID(bot_id)
        # Eager load agent to prevent N+1 query
        result = await db.execute(
            select(TeamsBot)
            .options(joinedload(TeamsBot.agent))
            .filter(TeamsBot.id == bot_uuid, TeamsBot.tenant_id == tenant_id)
        )
        bot = result.scalar_one_or_none()

        if not bot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Teams bot with ID '{bot_id}' not found")

        return TeamsBotResponse(
            success=True,
            message="Teams bot details retrieved",
            data={
                "bot_id": str(bot.id),
                "bot_name": bot.bot_name,
                "agent_id": str(bot.agent_id),
                "agent_name": bot.agent.agent_name,
                "app_id": bot.app_id,
                "teams_bot_id": bot.bot_id,
                "webhook_url": bot.webhook_url,
                "welcome_message": bot.welcome_message,
                "is_active": bot.is_active,
                "last_message_at": bot.last_message_at.isoformat() if bot.last_message_at else None,
                "created_at": bot.created_at.isoformat(),
                "updated_at": bot.updated_at.isoformat(),
            },
        )

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Teams bot: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get Teams bot details")


@teams_router.put("/teams-bots/{bot_id}", response_model=TeamsBotResponse)
async def update_teams_bot(
    bot_id: str,
    request: UpdateTeamsBotRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Update a Teams bot's configuration."""
    try:
        bot_uuid = uuid.UUID(bot_id)
        result = await db.execute(select(TeamsBot).filter(TeamsBot.id == bot_uuid, TeamsBot.tenant_id == tenant_id))
        bot = result.scalar_one_or_none()

        if not bot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Teams bot with ID '{bot_id}' not found")

        # Update fields
        if request.bot_name is not None:
            bot.bot_name = request.bot_name
        if request.app_password is not None:
            bot.app_password = encrypt_value(request.app_password)
        if request.webhook_url is not None:
            bot.webhook_url = request.webhook_url
        if request.welcome_message is not None:
            bot.welcome_message = request.welcome_message
        if request.is_active is not None:
            bot.is_active = request.is_active

        await db.commit()
        await db.refresh(bot)

        return TeamsBotResponse(
            success=True,
            message=f"Teams bot '{bot.bot_name}' updated successfully",
            data={
                "bot_id": str(bot.id),
                "bot_name": bot.bot_name,
                "is_active": bot.is_active,
                "updated_at": bot.updated_at.isoformat(),
            },
        )

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot ID format")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update Teams bot: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update Teams bot")


@teams_router.delete("/teams-bots/{bot_id}", response_model=TeamsBotResponse)
async def delete_teams_bot(
    bot_id: str, tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_async_db)
):
    """Delete a Teams bot."""
    try:
        bot_uuid = uuid.UUID(bot_id)
        result = await db.execute(select(TeamsBot).filter(TeamsBot.id == bot_uuid, TeamsBot.tenant_id == tenant_id))
        bot = result.scalar_one_or_none()

        if not bot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Teams bot with ID '{bot_id}' not found")

        bot_name = bot.bot_name
        await db.delete(bot)
        await db.commit()

        return TeamsBotResponse(success=True, message=f"Teams bot '{bot_name}' deleted successfully")

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot ID format")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete Teams bot: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete Teams bot")


# Webhook endpoint
@teams_router.post("/teams-bots/{bot_id}/webhook")
async def handle_teams_webhook(bot_id: str, activity: dict, db: AsyncSession = Depends(get_async_db)):
    """Handle incoming Teams activity (called by Bot Framework)."""
    try:
        bot_uuid = uuid.UUID(bot_id)
        service = TeamsWebhookService(db)

        await service.handle_activity(bot_uuid, activity)

        return {"status": "ok"}

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot ID format")
    except Exception as e:
        logger.error(f"Webhook handling error: {e}", exc_info=True)
        # Return 200 to Teams even on error to prevent retries
        return {"status": "error"}
