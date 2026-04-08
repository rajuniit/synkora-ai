"""
Widget API endpoints.

Provides REST API endpoints for managing agent widgets (embedded chat interfaces).
"""

import json
import logging
import secrets
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

# Import SessionLocal to create independent sessions for streams
from src.config.settings import get_settings
from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_tenant_id
from src.middleware.widget_auth import WidgetAuthMiddleware
from src.models.agent import Agent
from src.models.agent_widget import AgentWidget, WidgetAnalytics
from src.models.conversation import Conversation
from src.models.message import Message
from src.services.security.advanced_prompt_scanner import advanced_prompt_scanner

logger = logging.getLogger(__name__)

# Create router
widgets_router = APIRouter()


# Request/Response Models
class CreateWidgetRequest(BaseModel):
    """Request model for creating a widget."""

    agent_id: str = Field(..., description="UUID of the agent")
    widget_name: str = Field(..., description="Human-readable name for the widget")
    allowed_domains: list[str] | None = Field(
        None, description="List of domains allowed to embed this widget (null = all domains)"
    )
    theme_config: dict[str, Any] | None = Field(
        None, description="JSON configuration for widget appearance and behavior"
    )
    rate_limit: int = Field(100, description="Maximum requests per hour")


class UpdateWidgetRequest(BaseModel):
    """Request model for updating a widget."""

    widget_name: str | None = Field(None, description="Human-readable name for the widget")
    allowed_domains: list[str] | None = Field(None, description="List of domains allowed to embed this widget")
    theme_config: dict[str, Any] | None = Field(None, description="JSON configuration for widget appearance")
    rate_limit: int | None = Field(None, description="Maximum requests per hour")
    is_active: bool | None = Field(None, description="Whether the widget is active")


class WidgetResponse(BaseModel):
    """Response model for widget operations."""

    success: bool
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


def generate_api_key() -> tuple[str, str, str]:
    """Generate a secure API key. Returns (plain_key, encrypted_key, key_prefix)."""
    from src.services.agents.security import encrypt_value

    plain_key = f"widget_{secrets.token_urlsafe(32)}"
    encrypted_key = encrypt_value(plain_key)
    key_prefix = plain_key[:20]
    return plain_key, encrypted_key, key_prefix


@widgets_router.post("/widgets", response_model=WidgetResponse, status_code=status.HTTP_201_CREATED)
async def create_widget(
    request: CreateWidgetRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        try:
            agent_uuid = uuid.UUID(request.agent_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent ID format")

        result = await db.execute(select(Agent).filter(Agent.id == agent_uuid, Agent.tenant_id == tenant_id))
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent with ID '{request.agent_id}' not found"
            )

        plain_key, encrypted_key, key_prefix = generate_api_key()

        widget = AgentWidget(
            agent_id=agent_uuid,
            tenant_id=agent.tenant_id,
            widget_name=request.widget_name,
            api_key=encrypted_key,
            key_prefix=key_prefix,
            allowed_domains=request.allowed_domains,
            theme_config=request.theme_config or {},
            rate_limit=request.rate_limit,
            is_active=True,
        )

        db.add(widget)
        await db.commit()
        await db.refresh(widget)

        return WidgetResponse(
            success=True,
            message=f"Widget '{request.widget_name}' created successfully",
            data={
                "widget_id": str(widget.id),
                "widget_name": widget.widget_name,
                "api_key": plain_key,
                "agent_id": str(widget.agent_id),
                "agent_name": agent.agent_name,
                "allowed_domains": widget.allowed_domains,
                "theme_config": widget.theme_config,
                "rate_limit": widget.rate_limit,
                "is_active": widget.is_active,
                "created_at": widget.created_at.isoformat(),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create widget: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create widget")


@widgets_router.get("/widgets", response_model=WidgetResponse)
async def list_widgets(
    agent_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        if agent_id:
            try:
                agent_uuid = uuid.UUID(agent_id)
                result = await db.execute(select(Agent).filter(Agent.id == agent_uuid, Agent.tenant_id == tenant_id))
                agent = result.scalar_one_or_none()
                if not agent:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent with ID '{agent_id}' not found"
                    )
                stmt = (
                    select(AgentWidget)
                    .options(joinedload(AgentWidget.agent))
                    .filter(AgentWidget.agent_id == agent_uuid, AgentWidget.tenant_id == tenant_id)
                )
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid agent ID format")
        else:
            stmt = select(AgentWidget).options(joinedload(AgentWidget.agent)).filter(AgentWidget.tenant_id == tenant_id)

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Get paginated results
        result = await db.execute(stmt.limit(limit).offset(offset))
        widgets = result.scalars().unique().all()

        widgets_list = []
        for widget in widgets:
            widgets_list.append(
                {
                    "widget_id": str(widget.id),
                    "widget_name": widget.widget_name,
                    "agent_id": str(widget.agent_id),
                    "agent_name": widget.agent.agent_name,
                    "allowed_domains": widget.allowed_domains,
                    "rate_limit": widget.rate_limit,
                    "is_active": widget.is_active,
                    "created_at": widget.created_at.isoformat(),
                    "updated_at": widget.updated_at.isoformat(),
                }
            )

        return WidgetResponse(
            success=True,
            message=f"Found {len(widgets_list)} widgets",
            data={"widgets": widgets_list, "total": total_count, "limit": limit, "offset": offset},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list widgets: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list widgets")


# Widget Public Config Endpoint
@widgets_router.get("/widgets/config")
async def get_widget_config(http_request: Request, db: AsyncSession = Depends(get_async_db)):
    """
    Public endpoint to fetch widget + agent configuration.
    Authenticated via X-Widget-API-Key header.
    Returns agent name, avatar, description, suggestion prompts, and theme config
    so the embedded widget can render itself correctly without hardcoded values.
    """
    try:
        api_key = http_request.headers.get("X-Widget-API-Key")
        if not api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Widget API key is required")

        widget = await WidgetAuthMiddleware.validate_api_key(api_key, db)
        if not widget:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or inactive widget API key")

        result = await db.execute(
            select(Agent).filter(
                Agent.id == widget.agent_id,
                Agent.tenant_id == widget.tenant_id,
            )
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

        theme = widget.theme_config or {}

        return {
            "widget_id": str(widget.id),
            "widget_name": widget.widget_name,
            "agent_name": agent.agent_name,
            "agent_description": agent.description or "",
            "agent_avatar": agent.avatar or "",
            "suggestion_prompts": agent.suggestion_prompts or [],
            "theme": {
                "primary_color": theme.get("chat_primary_color") or theme.get("primaryColor") or "",
                "welcome_message": theme.get("chat_welcome_message") or "",
                "placeholder": theme.get("chat_placeholder") or "",
                "title": theme.get("chat_title") or "",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get widget config: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get widget config")


@widgets_router.get("/widgets/chat/history")
async def get_widget_chat_history(
    session_id: str, http_request: Request, limit: int = 50, db: AsyncSession = Depends(get_async_db)
):
    try:
        api_key = http_request.headers.get("X-Widget-API-Key")
        if not api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Widget API key is required")

        widget = await WidgetAuthMiddleware.validate_api_key(api_key, db)
        if not widget:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or inactive widget API key")

        # SECURITY: Verify agent belongs to the same tenant as the widget
        result = await db.execute(
            select(Agent).filter(
                Agent.id == widget.agent_id,
                Agent.tenant_id == widget.tenant_id,  # Prevent cross-tenant access
            )
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

        conversation_result = await db.execute(
            select(Conversation).filter(Conversation.agent_id == agent.id, Conversation.session_id == session_id)
        )
        conversation = conversation_result.scalar_one_or_none()

        if not conversation:
            return WidgetResponse(
                success=True, message="No chat history found", data={"session_id": session_id, "messages": []}
            )

        messages_result = await db.execute(
            select(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = messages_result.scalars().all()

        messages_list = []
        for msg in reversed(messages):
            messages_list.append({"role": msg.role, "content": msg.content, "created_at": msg.created_at.isoformat()})

        return WidgetResponse(
            success=True,
            message=f"Found {len(messages_list)} messages",
            data={"session_id": session_id, "messages": messages_list},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get chat history")


@widgets_router.get("/widgets/{widget_id}", response_model=WidgetResponse)
async def get_widget(
    widget_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        try:
            widget_uuid = uuid.UUID(widget_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid widget ID format")

        # Eager load agent to prevent N+1 query
        result = await db.execute(
            select(AgentWidget)
            .options(joinedload(AgentWidget.agent))
            .filter(AgentWidget.id == widget_uuid, AgentWidget.tenant_id == tenant_id)
        )
        widget = result.scalar_one_or_none()

        if not widget:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Widget with ID '{widget_id}' not found")

        return WidgetResponse(
            success=True,
            message="Widget details retrieved",
            data={
                "widget_id": str(widget.id),
                "widget_name": widget.widget_name,
                "api_key": widget.api_key,
                "agent_id": str(widget.agent_id),
                "agent_name": widget.agent.agent_name,
                "allowed_domains": widget.allowed_domains,
                "theme_config": widget.theme_config,
                "rate_limit": widget.rate_limit,
                "is_active": widget.is_active,
                "created_at": widget.created_at.isoformat(),
                "updated_at": widget.updated_at.isoformat(),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get widget: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get widget details")


@widgets_router.put("/widgets/{widget_id}", response_model=WidgetResponse)
async def update_widget(
    widget_id: str,
    request: UpdateWidgetRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        try:
            widget_uuid = uuid.UUID(widget_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid widget ID format")

        result = await db.execute(
            select(AgentWidget).filter(AgentWidget.id == widget_uuid, AgentWidget.tenant_id == tenant_id)
        )
        widget = result.scalar_one_or_none()

        if not widget:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Widget with ID '{widget_id}' not found")

        if request.widget_name is not None:
            widget.widget_name = request.widget_name
        if request.allowed_domains is not None:
            widget.allowed_domains = request.allowed_domains
        if request.theme_config is not None:
            widget.theme_config = request.theme_config
        if request.rate_limit is not None:
            widget.rate_limit = request.rate_limit
        if request.is_active is not None:
            widget.is_active = request.is_active

        await db.commit()
        await db.refresh(widget)

        return WidgetResponse(
            success=True,
            message=f"Widget '{widget.widget_name}' updated successfully",
            data={
                "widget_id": str(widget.id),
                "widget_name": widget.widget_name,
                "allowed_domains": widget.allowed_domains,
                "theme_config": widget.theme_config,
                "rate_limit": widget.rate_limit,
                "is_active": widget.is_active,
                "updated_at": widget.updated_at.isoformat(),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update widget: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update widget")


@widgets_router.delete("/widgets/{widget_id}", response_model=WidgetResponse)
async def delete_widget(
    widget_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        try:
            widget_uuid = uuid.UUID(widget_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid widget ID format")

        result = await db.execute(
            select(AgentWidget).filter(AgentWidget.id == widget_uuid, AgentWidget.tenant_id == tenant_id)
        )
        widget = result.scalar_one_or_none()

        if not widget:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Widget with ID '{widget_id}' not found")

        widget_name = widget.widget_name
        await db.delete(widget)
        await db.commit()

        return WidgetResponse(success=True, message=f"Widget '{widget_name}' deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete widget: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete widget")


@widgets_router.post("/widgets/{widget_id}/regenerate-key", response_model=WidgetResponse)
async def regenerate_api_key(
    widget_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        try:
            widget_uuid = uuid.UUID(widget_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid widget ID format")

        result = await db.execute(
            select(AgentWidget).filter(AgentWidget.id == widget_uuid, AgentWidget.tenant_id == tenant_id)
        )
        widget = result.scalar_one_or_none()

        if not widget:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Widget with ID '{widget_id}' not found")

        plain_key, encrypted_key, key_prefix = generate_api_key()
        widget.api_key = encrypted_key
        widget.key_prefix = key_prefix
        await db.commit()
        await db.refresh(widget)

        return WidgetResponse(
            success=True,
            message="API key regenerated successfully",
            data={"widget_id": str(widget.id), "api_key": plain_key},
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to regenerate API key: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to regenerate API key")


@widgets_router.get("/widgets/{widget_id}/embed-code", response_model=WidgetResponse)
async def get_embed_code(
    widget_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        try:
            widget_uuid = uuid.UUID(widget_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid widget ID format")

        result = await db.execute(
            select(AgentWidget).filter(AgentWidget.id == widget_uuid, AgentWidget.tenant_id == tenant_id)
        )
        widget = result.scalar_one_or_none()

        if not widget:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Widget with ID '{widget_id}' not found")

        settings = get_settings()
        widget_js_url = settings.widget_js_url
        public_api_url = settings.public_api_url

        # Decrypt API key for embed code display (keys may be stored encrypted)
        from src.services.agents.security import decrypt_value

        try:
            display_api_key = decrypt_value(widget.api_key)
        except Exception:
            display_api_key = widget.api_key  # already plain (legacy)

        embed_code = f"""<!-- Synkora Agent Widget -->
<div id="synkora-widget-{widget_id}"></div>
<script src="{widget_js_url}"></script>
<script>
  SynkoraWidget.init({{
    widgetId: '{widget_id}',
    apiKey: '{display_api_key}',
    containerId: 'synkora-widget-{widget_id}',
    apiUrl: '{public_api_url}'
  }});
</script>"""

        return WidgetResponse(
            success=True, message="Embed code generated", data={"widget_id": str(widget.id), "embed_code": embed_code}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate embed code: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate embed code")


@widgets_router.get("/widgets/{widget_id}/analytics", response_model=WidgetResponse)
async def get_widget_analytics(
    widget_id: str,
    limit: int = 100,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        try:
            widget_uuid = uuid.UUID(widget_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid widget ID format")

        result = await db.execute(
            select(AgentWidget).filter(AgentWidget.id == widget_uuid, AgentWidget.tenant_id == tenant_id)
        )
        widget = result.scalar_one_or_none()

        if not widget:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Widget with ID '{widget_id}' not found")

        analytics_result = await db.execute(
            select(WidgetAnalytics)
            .filter(WidgetAnalytics.widget_id == widget_uuid)
            .order_by(WidgetAnalytics.created_at.desc())
            .limit(limit)
        )
        analytics = analytics_result.scalars().all()

        analytics_list = []
        for record in analytics:
            analytics_list.append(
                {
                    "session_id": record.session_id,
                    "messages_count": record.messages_count,
                    "domain": record.domain,
                    "user_agent": record.user_agent,
                    "created_at": record.created_at.isoformat(),
                }
            )

        total_sessions = len({a.session_id for a in analytics})
        total_messages = sum(a.messages_count for a in analytics)
        unique_domains = len({a.domain for a in analytics if a.domain})

        return WidgetResponse(
            success=True,
            message=f"Found {len(analytics_list)} analytics records",
            data={
                "widget_id": str(widget.id),
                "widget_name": widget.widget_name,
                "analytics": analytics_list,
                "summary": {
                    "total_sessions": total_sessions,
                    "total_messages": total_messages,
                    "unique_domains": unique_domains,
                },
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get widget analytics: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get analytics")


# Widget Chat Endpoints
class WidgetChatRequest(BaseModel):
    """Request model for widget chat."""

    message: str = Field(..., description="User message")
    session_id: str | None = Field(None, description="Session ID for conversation continuity")
    conversation_id: str | None = Field(None, description="Conversation ID if continuing existing chat")


@widgets_router.post("/widgets/chat")
async def widget_chat(request: WidgetChatRequest, http_request: Request, db: AsyncSession = Depends(get_async_db)):
    """
    Send a message to the agent via widget with advanced prompt injection protection.
    """
    try:
        # Get API key from header
        api_key = http_request.headers.get("X-Widget-API-Key")
        if not api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Widget API key is required")

        # Validate API key and get widget
        widget = await WidgetAuthMiddleware.validate_api_key(api_key, db)
        if not widget:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or inactive widget API key")

        # Validate domain
        origin = http_request.headers.get("Origin") or http_request.headers.get("Referer")
        if not WidgetAuthMiddleware.validate_domain(widget, origin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Domain not allowed for this widget")

        # Check rate limit
        if not WidgetAuthMiddleware.check_rate_limit(widget):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded for this widget"
            )

        # Get agent - SECURITY: Verify agent belongs to the same tenant as the widget
        result = await db.execute(
            select(Agent).filter(
                Agent.id == widget.agent_id,
                Agent.tenant_id == widget.tenant_id,  # Prevent cross-tenant access
            )
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

        # Eager load any necessary agent data here if needed to avoid lazy loading in thread

        # Scan message
        client_ip = http_request.client.host if http_request.client else "unknown"
        http_request.headers.get("User-Agent", "unknown")

        scan_result = advanced_prompt_scanner.scan_comprehensive(
            text=request.message, user_id=f"widget_{widget.id}", ip_address=client_ip, context="widget_chat"
        )

        # Block if threat detected
        if not scan_result["is_safe"]:
            logger.warning(
                f"SECURITY: Prompt injection blocked. Widget: {widget.id}, Risk: {scan_result['risk_score']}"
            )

            async def generate_security_block():
                security_response = {
                    "type": "error",
                    "content": "Your message has been blocked due to security policy violations.",
                    "error_type": "security_violation",
                    "violation_id": f"WVI_{uuid.uuid4().hex[:8]}",
                }
                yield f"data: {json.dumps(security_response)}\n\n"

            return StreamingResponse(
                generate_security_block(), media_type="text/event-stream", headers={"X-Security-Status": "blocked"}
            )

        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())

        # Track analytics
        origin = http_request.headers.get("Origin") or http_request.headers.get("Referer")
        domain = None
        if origin:
            domain = origin.replace("http://", "").replace("https://", "").split(":")[0]

        analytics_result = await db.execute(
            select(WidgetAnalytics).filter(
                WidgetAnalytics.widget_id == widget.id, WidgetAnalytics.session_id == session_id
            )
        )
        analytics = analytics_result.scalar_one_or_none()

        if analytics:
            analytics.messages_count += 1
        else:
            analytics = WidgetAnalytics(
                widget_id=widget.id,
                session_id=session_id,
                messages_count=1,
                domain=domain,
                user_agent=http_request.headers.get("User-Agent", "unknown"),
            )
            db.add(analytics)

        try:
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to commit analytics: {e}")
            await db.rollback()

        # Import the stream services
        from src.services.agents.agent_loader_service import AgentLoaderService
        from src.services.agents.agent_manager import AgentManager
        from src.services.agents.chat_service import ChatService
        from src.services.agents.chat_stream_service import ChatStreamService
        from src.services.conversation_service import ConversationService

        # Load conversation history if conversation_id is provided
        conversation_history = None
        if request.conversation_id:
            try:
                conversation_uuid = uuid.UUID(request.conversation_id)
                conversation_history = await ConversationService.get_conversation_history_cached(
                    db=db,
                    conversation_id=conversation_uuid,
                    limit=30,  # Keep recent messages for context
                )
                logger.info(f"📝 Loaded {len(conversation_history)} messages from widget conversation history")
            except (ValueError, Exception) as e:
                logger.warning(f"Could not load conversation history: {e}")

        # Initialize the chat stream service
        agent_manager = AgentManager()
        chat_stream_service = ChatStreamService(
            agent_loader=AgentLoaderService(agent_manager), chat_service=ChatService()
        )

        # Return streaming response with loaded conversation history
        return StreamingResponse(
            chat_stream_service.stream_agent_response(
                agent.agent_name,
                request.message,
                conversation_history,  # Pass loaded history for memory
                request.conversation_id,
                None,  # attachments
                None,  # llm_config_id
                db,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Security-Status": "validated",
                "X-Risk-Score": str(scan_result["risk_score"]),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process widget chat: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process chat message")
