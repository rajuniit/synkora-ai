"""
Agent API endpoints with Advanced Security Protection.

Provides REST API endpoints for managing and executing Google Agent SDK agents.
CRITICAL: All chat interactions are protected with prompt injection scanning.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.controllers.agents.models import AgentResponse, ChatRequest
from src.core.database import get_async_db
from src.helpers.chat_helpers import validate_conversation_id
from src.helpers.streaming_helpers import generate_security_block_stream
from src.middleware.auth_middleware import get_current_account, get_current_tenant_id
from src.models.tenant import Account
from src.services.agents.agent_loader_service import AgentLoaderService
from src.services.agents.agent_manager import AgentManager
from src.services.agents.chat_service import ChatService
from src.services.agents.chat_stream_service import ChatStreamService
from src.services.security.advanced_prompt_scanner import advanced_prompt_scanner

logger = logging.getLogger(__name__)

# Create router
agents_chat_router = APIRouter()

# Global service instances
agent_manager = AgentManager()
agent_loader = AgentLoaderService(agent_manager)
chat_service = ChatService()
chat_stream_service = ChatStreamService(
    agent_loader=agent_loader,
    chat_service=chat_service,
)


# Endpoints
@agents_chat_router.post("/chat/upload-attachment", response_model=AgentResponse)
async def upload_chat_attachment(
    file: UploadFile = File(...),
    conversation_id: str = Form(...),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Upload a file attachment for chat.

    Args:
        file: File to upload
        conversation_id: Conversation ID
        tenant_id: Tenant ID
        db: Async database session

    Returns:
        Attachment metadata
    """
    try:
        from src.models.agent import Agent
        from src.models.conversation import Conversation
        from src.services.chat import AttachmentService

        # Validate conversation ID using helper
        conversation_uuid = validate_conversation_id(conversation_id)
        if not conversation_uuid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation ID format")

        # Verify conversation exists
        result = await db.execute(select(Conversation).filter(Conversation.id == conversation_uuid))
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Conversation with ID '{conversation_id}' not found"
            )

        # SECURITY: Verify the conversation belongs to current tenant (prevents IDOR)
        # Must verify via agent since conversations don't have direct tenant_id
        if not conversation.agent_id:
            # SECURITY: Reject conversations without an agent - cannot verify tenant ownership
            logger.warning(f"IDOR attempt: Conversation {conversation_id} has no agent_id for tenant verification")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Conversation with ID '{conversation_id}' not found"
            )

        # Verify agent belongs to current tenant
        agent_result = await db.execute(
            select(Agent).filter(Agent.id == conversation.agent_id, Agent.tenant_id == tenant_id)
        )
        agent = agent_result.scalar_one_or_none()
        if not agent:
            logger.warning(
                f"IDOR attempt: Tenant {tenant_id} tried to access conversation {conversation_id} "
                f"belonging to agent {conversation.agent_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Conversation with ID '{conversation_id}' not found"
            )

        # Initialize attachment service
        attachment_service = AttachmentService()

        # Read file content
        file_content = await file.read()

        # Upload attachment
        attachment = await attachment_service.upload_attachment(
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type,
            tenant_id=tenant_id,
            conversation_id=conversation_uuid,
        )

        return AgentResponse(
            success=True, message=f"File '{file.filename}' uploaded successfully", data={"attachment": attachment}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload chat attachment: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload attachment")


@agents_chat_router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_async_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_account: Account = Depends(get_current_account),
):
    """
    Chat with an agent using Server-Sent Events streaming with prompt injection protection.

    Args:
        request: Chat request
        http_request: FastAPI request object for security context
        db: Async database session
        tenant_id: Tenant ID from auth

    Returns:
        StreamingResponse with SSE or security block
    """
    # CRITICAL: Scan message for prompt injection before processing
    client_ip = http_request.client.host if http_request.client else "unknown"
    user_agent = http_request.headers.get("User-Agent", "unknown")

    scan_result = advanced_prompt_scanner.scan_comprehensive(
        text=request.message, user_id=f"tenant_{tenant_id}", ip_address=client_ip, context="agent_chat_stream"
    )

    # Block if threat detected
    if not scan_result["is_safe"]:
        # Log security violation
        logger.error(
            f"SECURITY VIOLATION: Prompt injection blocked in agent chat stream. "
            f"Agent: {request.agent_name}, Tenant: {tenant_id}, "
            f"Risk Score: {scan_result['risk_score']}, "
            f"Threat Level: {scan_result['threat_level']}, "
            f"IP: {client_ip}, User-Agent: {user_agent[:100]}"
        )

        return StreamingResponse(
            generate_security_block_stream(
                details={
                    "threat_level": scan_result["threat_level"],
                    "risk_score": scan_result["risk_score"],
                    "detections": len(scan_result["detections"]),
                }
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Security-Status": "blocked",
                "X-Threat-Level": scan_result["threat_level"],
                "X-Risk-Score": str(scan_result["risk_score"]),
            },
        )

    # Message is safe - proceed with normal chat flow

    # HITL: Check if this chat message is an approval reply for a pending action
    try:
        import json as _json_mod

        from src.config.redis import get_redis_async
        from src.services.human_approval_service import HumanApprovalService

        _redis = get_redis_async()
        _conv_id = request.conversation_id or ""
        _hitl_key = f"hitl:chat:{request.agent_name}:{_conv_id}"
        _approval_id_str = await _redis.get(_hitl_key)
        if _approval_id_str:
            _approval_svc = HumanApprovalService(db)
            _decision = _approval_svc.parse_reply(request.message)
            if _decision != "unclear":
                _result = await _approval_svc.handle_reply(uuid.UUID(_approval_id_str), request.message, db)
                if _result == "approved":
                    _reply = "Great! Proceeding with the action now."
                elif _result in ("rejected", "feedback"):
                    _reply = (
                        "Understood. Action cancelled."
                        if _result == "rejected"
                        else "Got it! I'll revise and ask again shortly."
                    )
                elif _result == "expired":
                    _reply = "This approval request has expired. The next scheduled run will ask again."
                else:
                    _reply = "Action status updated."

                await _redis.delete(_hitl_key)

                async def _approval_stream():
                    yield f"data: {_json_mod.dumps({'type': 'chunk', 'content': _reply})}\n\n"
                    yield 'data: {"type":"done"}\n\n'

                return StreamingResponse(
                    _approval_stream(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                    },
                )
            # else: unclear — fall through to normal agent handling
    except Exception as _hitl_err:
        logger.warning(f"HITL chat intercept error: {_hitl_err}")

    # BILLING: Validate billing requirements before processing chat
    try:
        from sqlalchemy import or_

        from src.helpers.chat_helpers import validate_conversation_id
        from src.models.agent import Agent
        from src.services.billing import ChatBillingService

        # Get agent to determine model for credit cost calculation
        agent_result = await db.execute(
            select(Agent).filter(
                Agent.agent_name == request.agent_name,
                or_(Agent.tenant_id == tenant_id, Agent.is_public.is_(True)),
            )
        )
        db_agent = agent_result.scalar_one_or_none()

        if db_agent:
            # Get model from agent's llm_configs relationship
            llm_config = None
            if request.llm_config_id:
                # Find specific config by ID
                try:
                    llm_config_uuid = uuid.UUID(request.llm_config_id)
                    llm_config = next(
                        (c for c in db_agent.llm_configs if c.id == llm_config_uuid and c.enabled),
                        None,
                    )
                except ValueError:
                    pass
            else:
                # Find default config
                llm_config = next(
                    (c for c in db_agent.llm_configs if c.is_default and c.enabled),
                    None,
                )

            if not llm_config or not llm_config.model_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "No LLM configuration",
                        "message": "This agent has no LLM configuration. Please configure an LLM model for the agent.",
                        "error_code": "NO_LLM_CONFIG",
                    },
                )

            # Parse conversation_id if provided
            conversation_uuid = None
            if request.conversation_id:
                conversation_uuid = validate_conversation_id(request.conversation_id)

            # Validate all billing requirements
            billing_service = ChatBillingService(db)
            billing_result = await billing_service.validate_chat_request(
                tenant_id=tenant_id,
                model_name=llm_config.model_name,
                conversation_id=conversation_uuid,
            )

            if not billing_result.is_valid:
                logger.warning(
                    f"Billing validation failed for chat: tenant={tenant_id}, "
                    f"error_code={billing_result.error.error_code}"
                )
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "error": billing_result.error.error_code.value,
                        "message": billing_result.error.message,
                        "error_code": billing_result.error.error_code.value,
                        **(billing_result.error.details or {}),
                    },
                )
    except HTTPException:
        raise
    except Exception as e:
        # Log but don't block chat if billing validation fails (fail open for non-critical errors)
        logger.error(f"Billing validation failed, allowing chat to proceed: {e}")

    # SECURITY: Pass tenant_id to verify conversation ownership
    return StreamingResponse(
        chat_stream_service.stream_agent_response(
            request.agent_name,
            request.message,
            request.conversation_history,
            request.conversation_id,
            request.attachments,
            request.llm_config_id,
            db,
            user_id=str(current_account.id),
            tenant_id=tenant_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Security-Status": "validated",
            "X-Risk-Score": str(scan_result["risk_score"]),
            "X-Scan-ID": f"CHAT_SC_{uuid.uuid4().hex[:8]}",
            "X-Layers-Triggered": str(scan_result["layers_triggered"]),
        },
    )
