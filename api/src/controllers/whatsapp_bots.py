"""WhatsApp Bot API endpoints."""

import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..core.database import get_async_db
from ..helpers.streaming_helpers import generate_sse_event
from ..middleware.auth_middleware import get_current_account, get_current_tenant_id
from ..models import Account
from ..models.agent import Agent
from ..models.whatsapp_bot import WhatsAppBot
from ..services.agents.security import encrypt_value
from ..services.whatsapp import WhatsAppWebhookService, WhatsAppWebService

logger = logging.getLogger(__name__)

whatsapp_router = APIRouter()


# Request/Response Models
class CreateWhatsAppBotRequest(BaseModel):
    """Request model for creating a WhatsApp bot."""

    agent_id: str = Field(..., description="UUID of the agent")
    bot_name: str = Field(..., description="Human-readable name for the bot")
    phone_number_id: str = Field(..., description="WhatsApp phone number ID")
    business_account_id: str = Field(..., description="WhatsApp Business Account ID")
    access_token: str = Field(..., description="WhatsApp API access token")
    verify_token: str = Field(..., description="Webhook verification token")
    webhook_url: str | None = Field(None, description="Webhook URL")


class UpdateWhatsAppBotRequest(BaseModel):
    """Request model for updating a WhatsApp bot."""

    bot_name: str | None = None
    access_token: str | None = None
    verify_token: str | None = None
    webhook_url: str | None = None
    is_active: bool | None = None


class WhatsAppBotResponse(BaseModel):
    """Response model for WhatsApp bot operations."""

    success: bool
    message: str
    data: dict = Field(default_factory=dict)


@whatsapp_router.post("/whatsapp-bots", response_model=WhatsAppBotResponse, status_code=status.HTTP_201_CREATED)
async def create_whatsapp_bot(
    request: CreateWhatsAppBotRequest,
    current_account: Account = Depends(get_current_account),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new WhatsApp bot for an agent."""
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
        encrypted_token = encrypt_value(request.access_token)

        # Create WhatsApp bot
        bot = WhatsAppBot(
            agent_id=agent_uuid,
            tenant_id=agent.tenant_id,
            bot_name=request.bot_name,
            phone_number_id=request.phone_number_id,
            whatsapp_business_account_id=request.business_account_id,
            access_token=encrypted_token,
            verify_token=request.verify_token,
            webhook_url=request.webhook_url,
            is_active=True,
            created_by=current_account.id,
        )

        db.add(bot)
        await db.commit()
        await db.refresh(bot)

        return WhatsAppBotResponse(
            success=True,
            message=f"WhatsApp bot '{request.bot_name}' created successfully",
            data={
                "bot_id": str(bot.id),
                "bot_name": bot.bot_name,
                "agent_id": str(bot.agent_id),
                "agent_name": agent.agent_name,
                "phone_number_id": bot.phone_number_id,
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
        logger.error(f"Failed to create WhatsApp bot: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create WhatsApp bot")


@whatsapp_router.get("/whatsapp-bots", response_model=WhatsAppBotResponse)
async def list_whatsapp_bots(
    agent_id: str | None = None,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """List all WhatsApp bots, optionally filtered by agent."""
    try:
        if agent_id:
            agent_uuid = uuid.UUID(agent_id)
            result = await db.execute(
                select(WhatsAppBot)
                .options(joinedload(WhatsAppBot.agent))
                .filter(WhatsAppBot.agent_id == agent_uuid, WhatsAppBot.tenant_id == tenant_id)
            )
            bots = result.scalars().all()
        else:
            result = await db.execute(
                select(WhatsAppBot).options(joinedload(WhatsAppBot.agent)).filter(WhatsAppBot.tenant_id == tenant_id)
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
                    "connection_type": bot.connection_type,
                    "linked_phone_number": bot.linked_phone_number,
                    "phone_number_id": bot.phone_number_id,
                    "is_active": bot.is_active,
                    "last_message_at": bot.last_message_at.isoformat() if bot.last_message_at else None,
                    "created_at": bot.created_at.isoformat(),
                }
            )

        return WhatsAppBotResponse(
            success=True, message=f"Found {len(bots_list)} WhatsApp bots", data={"bots": bots_list}
        )

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent ID format")
    except Exception as e:
        logger.error(f"Failed to list WhatsApp bots: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list WhatsApp bots")


@whatsapp_router.get("/whatsapp-bots/{bot_id}", response_model=WhatsAppBotResponse)
async def get_whatsapp_bot(
    bot_id: str, tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_async_db)
):
    """Get details of a specific WhatsApp bot."""
    try:
        bot_uuid = uuid.UUID(bot_id)
        # Eager load agent to prevent N+1 query
        result = await db.execute(
            select(WhatsAppBot)
            .options(joinedload(WhatsAppBot.agent))
            .filter(WhatsAppBot.id == bot_uuid, WhatsAppBot.tenant_id == tenant_id)
        )
        bot = result.scalar_one_or_none()

        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"WhatsApp bot with ID '{bot_id}' not found"
            )

        return WhatsAppBotResponse(
            success=True,
            message="WhatsApp bot details retrieved",
            data={
                "bot_id": str(bot.id),
                "bot_name": bot.bot_name,
                "agent_id": str(bot.agent_id),
                "agent_name": bot.agent.agent_name,
                "connection_type": bot.connection_type,
                "linked_phone_number": bot.linked_phone_number,
                "phone_number_id": bot.phone_number_id,
                "business_account_id": bot.whatsapp_business_account_id,
                "webhook_url": bot.webhook_url,
                "verify_token": bot.verify_token,
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
        logger.error(f"Failed to get WhatsApp bot: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get WhatsApp bot details"
        )


@whatsapp_router.put("/whatsapp-bots/{bot_id}", response_model=WhatsAppBotResponse)
async def update_whatsapp_bot(
    bot_id: str,
    request: UpdateWhatsAppBotRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Update a WhatsApp bot's configuration."""
    try:
        bot_uuid = uuid.UUID(bot_id)
        result = await db.execute(
            select(WhatsAppBot).filter(WhatsAppBot.id == bot_uuid, WhatsAppBot.tenant_id == tenant_id)
        )
        bot = result.scalar_one_or_none()

        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"WhatsApp bot with ID '{bot_id}' not found"
            )

        # Update fields
        if request.bot_name is not None:
            bot.bot_name = request.bot_name
        if request.access_token is not None:
            bot.access_token = encrypt_value(request.access_token)
        if request.verify_token is not None:
            bot.verify_token = request.verify_token
        if request.webhook_url is not None:
            bot.webhook_url = request.webhook_url
        if request.is_active is not None:
            bot.is_active = request.is_active

        await db.commit()
        await db.refresh(bot)

        return WhatsAppBotResponse(
            success=True,
            message=f"WhatsApp bot '{bot.bot_name}' updated successfully",
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
        logger.error(f"Failed to update WhatsApp bot: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update WhatsApp bot")


@whatsapp_router.delete("/whatsapp-bots/{bot_id}", response_model=WhatsAppBotResponse)
async def delete_whatsapp_bot(
    bot_id: str, tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_async_db)
):
    """Delete a WhatsApp bot."""
    try:
        bot_uuid = uuid.UUID(bot_id)
        result = await db.execute(
            select(WhatsAppBot).filter(WhatsAppBot.id == bot_uuid, WhatsAppBot.tenant_id == tenant_id)
        )
        bot = result.scalar_one_or_none()

        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"WhatsApp bot with ID '{bot_id}' not found"
            )

        bot_name = bot.bot_name
        await db.delete(bot)
        await db.commit()

        return WhatsAppBotResponse(success=True, message=f"WhatsApp bot '{bot_name}' deleted successfully")

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot ID format")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete WhatsApp bot: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete WhatsApp bot")


# ---------------------------------------------------------------------------
# Device-Link unlink endpoint
# ---------------------------------------------------------------------------


@whatsapp_router.post("/whatsapp-bots/{bot_id}/unlink", response_model=WhatsAppBotResponse)
async def unlink_whatsapp_device(
    bot_id: str, tenant_id: uuid.UUID = Depends(get_current_tenant_id), db: AsyncSession = Depends(get_async_db)
):
    """Unlink a device-link WhatsApp bot (clears session, stops the worker connection)."""
    try:
        bot_uuid = uuid.UUID(bot_id)
        result = await db.execute(
            select(WhatsAppBot).filter(WhatsAppBot.id == bot_uuid, WhatsAppBot.tenant_id == tenant_id)
        )
        bot = result.scalar_one_or_none()

        if not bot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WhatsApp bot not found")

        if bot.connection_type != "device_link":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only device_link bots can be unlinked")

        # Stop the bot in the worker pool
        try:
            from ..config.redis import get_redis
            from ..services.bot_worker.bot_deployment_service import BotDeploymentService

            redis_client = get_redis()
            deployment = BotDeploymentService(db, redis_client)
            await deployment.deactivate_whatsapp_bot(bot_uuid)
        except Exception as e:
            logger.warning(f"Could not deactivate bot in worker pool: {e}")

        # Clear session data and linked phone
        bot.session_data = None
        bot.linked_phone_number = None
        bot.is_active = False
        bot.connection_status = "disconnected"
        await db.commit()

        return WhatsAppBotResponse(success=True, message=f"WhatsApp bot '{bot.bot_name}' unlinked successfully")

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot ID format")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to unlink WhatsApp bot: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to unlink WhatsApp bot")


# ---------------------------------------------------------------------------
# QR Device-Link endpoints
# ---------------------------------------------------------------------------


class StartQRSessionRequest(BaseModel):
    """Request body for starting a QR device-link session."""

    agent_id: str = Field(..., description="UUID of the agent to attach the bot to")
    bot_name: str = Field(..., description="Human-readable name for the bot")


class SaveQRBotRequest(BaseModel):
    """Request body for persisting a connected device-link bot."""

    agent_id: str = Field(..., description="UUID of the agent")
    bot_name: str = Field(..., description="Human-readable name for the bot")


@whatsapp_router.post("/whatsapp-bots/qr/start", response_model=WhatsAppBotResponse, status_code=status.HTTP_200_OK)
async def start_qr_session(
    request: StartQRSessionRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Start a WhatsApp Web QR linking session and return a session_id."""
    try:
        agent_uuid = uuid.UUID(request.agent_id)

        # Verify agent belongs to tenant
        result = await db.execute(select(Agent).filter(Agent.id == agent_uuid, Agent.tenant_id == tenant_id))
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent with ID '{request.agent_id}' not found"
            )

        session_id = str(uuid.uuid4())
        await WhatsAppWebService.start_session(session_id)

        return WhatsAppBotResponse(
            success=True,
            message="QR session started",
            data={"session_id": session_id},
        )

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent ID format")
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start QR session: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start QR session")


@whatsapp_router.get("/whatsapp-bots/qr/{session_id}/stream")
async def stream_qr_session(session_id: str):
    """SSE stream that pushes QR code updates and connection status for a device-link session."""

    async def _event_generator():
        last_qr: str | None = None
        timeout = 300  # 5-minute maximum linking window
        elapsed = 0
        interval = 2

        try:
            while elapsed < timeout:
                current_status = WhatsAppWebService.get_status(session_id)

                if current_status == "not_found":
                    yield await generate_sse_event("error", {"message": "Session not found or expired"})
                    return

                if current_status in ("qr_ready", "pending"):
                    qr_data = WhatsAppWebService.get_qr_data(session_id)
                    if qr_data and qr_data != last_qr:
                        last_qr = qr_data
                        yield await generate_sse_event("qr", {"qr_data": qr_data})

                elif current_status == "scanning":
                    yield await generate_sse_event("status", {"status": "scanning"})

                elif current_status == "connected":
                    phone_number = WhatsAppWebService.get_phone_number(session_id)
                    yield await generate_sse_event("connected", {"phone_number": phone_number})
                    return

                elif current_status == "disconnected":
                    yield await generate_sse_event("error", {"message": "Session disconnected"})
                    return

                await asyncio.sleep(interval)
                elapsed += interval

            # Timeout reached
            yield await generate_sse_event("error", {"message": "QR linking timed out. Please try again."})

        except asyncio.CancelledError:
            # Client disconnected — clean up
            await WhatsAppWebService.stop_session(session_id)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@whatsapp_router.post(
    "/whatsapp-bots/qr/{session_id}/save", response_model=WhatsAppBotResponse, status_code=status.HTTP_201_CREATED
)
async def save_qr_bot(
    session_id: str,
    request: SaveQRBotRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Persist a successfully-connected device-link bot to the database."""
    try:
        current_status = WhatsAppWebService.get_status(session_id)
        if current_status != "connected":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Session is not connected (current status: {current_status})",
            )

        agent_uuid = uuid.UUID(request.agent_id)
        result = await db.execute(select(Agent).filter(Agent.id == agent_uuid, Agent.tenant_id == tenant_id))
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent with ID '{request.agent_id}' not found"
            )

        phone_number = WhatsAppWebService.get_phone_number(session_id)
        raw_session_data = WhatsAppWebService.get_session_data(session_id)
        encrypted_session = encrypt_value(raw_session_data) if raw_session_data else None

        bot = WhatsAppBot(
            agent_id=agent_uuid,
            tenant_id=tenant_id,
            bot_name=request.bot_name,
            connection_type="device_link",
            linked_phone_number=phone_number,
            session_data=encrypted_session,
            is_active=True,
            connection_status="connected",
        )

        db.add(bot)
        await db.commit()
        await db.refresh(bot)

        # Session data is now persisted; clean up QR session memory
        await WhatsAppWebService.stop_session(session_id)

        # Activate bot through the worker pool so it starts receiving messages
        try:
            from ..config.redis import get_redis
            from ..services.bot_worker.bot_deployment_service import BotDeploymentService

            redis_client = get_redis()
            deployment = BotDeploymentService(db, redis_client)
            await deployment.activate_whatsapp_bot(bot.id)
        except Exception as e:
            logger.warning(f"Could not activate bot in worker pool (bot saved, will activate on worker restart): {e}")

        return WhatsAppBotResponse(
            success=True,
            message=f"WhatsApp bot '{request.bot_name}' linked successfully",
            data={
                "bot_id": str(bot.id),
                "bot_name": bot.bot_name,
                "agent_id": str(bot.agent_id),
                "agent_name": agent.agent_name,
                "connection_type": bot.connection_type,
                "linked_phone_number": bot.linked_phone_number,
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
        logger.error(f"Failed to save QR bot: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save WhatsApp bot")


@whatsapp_router.delete("/whatsapp-bots/qr/{session_id}", response_model=WhatsAppBotResponse)
async def cancel_qr_session(session_id: str, _tenant_id: uuid.UUID = Depends(get_current_tenant_id)):
    """Cancel an in-progress QR linking session."""
    await WhatsAppWebService.stop_session(session_id)
    return WhatsAppBotResponse(success=True, message="QR session cancelled")


# Webhook endpoints
@whatsapp_router.get("/whatsapp-bots/{bot_id}/webhook")
async def verify_whatsapp_webhook(
    bot_id: str,
    hub_mode: str = None,
    hub_verify_token: str = None,
    hub_challenge: str = None,
    request: Request = None,
    db: AsyncSession = Depends(get_async_db),
):
    """Verify WhatsApp webhook (called by WhatsApp)."""
    try:
        # Extract query params if not provided
        if not hub_mode:
            hub_mode = request.query_params.get("hub.mode")
        if not hub_verify_token:
            hub_verify_token = request.query_params.get("hub.verify_token")
        if not hub_challenge:
            hub_challenge = request.query_params.get("hub.challenge")

        bot_uuid = uuid.UUID(bot_id)
        service = WhatsAppWebhookService(db)

        challenge = await service.verify_webhook(
            mode=hub_mode, token=hub_verify_token, challenge=hub_challenge, bot_id=bot_uuid
        )

        if challenge:
            return int(challenge)

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Webhook verification failed")

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot ID format")
    except Exception as e:
        logger.error(f"Webhook verification error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Webhook verification failed")


@whatsapp_router.post("/whatsapp-bots/{bot_id}/webhook")
async def handle_whatsapp_webhook(bot_id: str, payload: dict, db: AsyncSession = Depends(get_async_db)):
    """Handle incoming WhatsApp webhook (called by WhatsApp)."""
    try:
        bot_uuid = uuid.UUID(bot_id)
        service = WhatsAppWebhookService(db)

        await service.handle_webhook(bot_uuid, payload)

        return {"status": "ok"}

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot ID format")
    except Exception as e:
        logger.error(f"Webhook handling error: {e}", exc_info=True)
        # Return 200 to WhatsApp even on error to prevent retries
        return {"status": "error"}
