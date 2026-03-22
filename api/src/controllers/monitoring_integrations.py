"""Monitoring Integration API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_tenant_id
from src.models.monitoring_integration import MonitoringIntegration, MonitoringProvider
from src.schemas.load_testing import (
    CreateMonitoringIntegrationRequest,
    MonitoringIntegrationListResponse,
    MonitoringIntegrationResponse,
    TestConnectionResponse,
    UpdateMonitoringIntegrationRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.post("", response_model=MonitoringIntegrationResponse, status_code=201)
async def create_monitoring_integration(
    request: CreateMonitoringIntegrationRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new monitoring integration."""
    try:
        # Validate provider
        try:
            provider = MonitoringProvider(request.provider)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {request.provider}")

        # Validate config against schema
        config_schema = MonitoringIntegration.get_config_schema(provider)
        for required_field in config_schema.get("required", []):
            if required_field not in request.config:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {required_field}",
                )

        # Create integration
        integration = MonitoringIntegration(
            tenant_id=tenant_id,
            name=request.name,
            provider=provider,
            export_settings=request.export_settings,
            is_active=True,
        )

        # Encrypt and store config
        integration.set_config(request.config)

        db.add(integration)
        await db.commit()
        await db.refresh(integration)

        logger.info(f"Created monitoring integration: {integration.name} (ID: {integration.id})")

        return _integration_to_response(integration)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating monitoring integration: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=MonitoringIntegrationListResponse)
async def list_monitoring_integrations(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """List all monitoring integrations."""
    try:
        result = await db.execute(
            select(MonitoringIntegration)
            .filter(MonitoringIntegration.tenant_id == tenant_id)
            .order_by(MonitoringIntegration.created_at.desc())
        )
        integrations = result.scalars().all()

        return MonitoringIntegrationListResponse(
            items=[_integration_to_response(i) for i in integrations],
            total=len(integrations),
        )

    except Exception as e:
        logger.error(f"Error listing monitoring integrations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{integration_id}", response_model=MonitoringIntegrationResponse)
async def get_monitoring_integration(
    integration_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Get a specific monitoring integration."""
    try:
        integration = await _get_integration(db, integration_id, tenant_id)
        return _integration_to_response(integration)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting monitoring integration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{integration_id}", response_model=MonitoringIntegrationResponse)
async def update_monitoring_integration(
    integration_id: UUID,
    request: UpdateMonitoringIntegrationRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Update a monitoring integration."""
    try:
        integration = await _get_integration(db, integration_id, tenant_id)

        if request.name is not None:
            integration.name = request.name
        if request.config is not None:
            integration.set_config(request.config)
        if request.export_settings is not None:
            integration.export_settings = request.export_settings
        if request.is_active is not None:
            integration.is_active = request.is_active

        await db.commit()
        await db.refresh(integration)

        logger.info(f"Updated monitoring integration: {integration.name} (ID: {integration.id})")

        return _integration_to_response(integration)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating monitoring integration: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{integration_id}", status_code=204)
async def delete_monitoring_integration(
    integration_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete a monitoring integration."""
    try:
        integration = await _get_integration(db, integration_id, tenant_id)

        await db.delete(integration)
        await db.commit()

        logger.info(f"Deleted monitoring integration: {integration.name} (ID: {integration.id})")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting monitoring integration: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{integration_id}/test", response_model=TestConnectionResponse)
async def test_monitoring_connection(
    integration_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Test connection to a monitoring platform."""
    try:
        integration = await _get_integration(db, integration_id, tenant_id)
        config = integration.get_config()

        # Test connection based on provider
        provider = integration.provider
        success = False
        message = ""
        details = {}

        if provider == MonitoringProvider.DATADOG:
            success, message, details = await _test_datadog(config)
        elif provider == MonitoringProvider.OPENTELEMETRY:
            success, message, details = await _test_otlp(config)
        elif provider == MonitoringProvider.GRAFANA_CLOUD:
            success, message, details = await _test_grafana_cloud(config)
        elif provider == MonitoringProvider.PROMETHEUS:
            success, message, details = await _test_prometheus(config)
        elif provider == MonitoringProvider.WEBHOOK:
            success, message, details = await _test_webhook(config)
        elif provider == MonitoringProvider.SLACK:
            success, message, details = await _test_slack(config)
        elif provider == MonitoringProvider.PAGERDUTY:
            success, message, details = await _test_pagerduty(config)
        else:
            message = f"Testing not supported for provider: {provider.value}"

        # Update sync status
        integration.sync_status = "success" if success else "failed"
        integration.sync_error = None if success else message
        await db.commit()

        return TestConnectionResponse(
            success=success,
            message=message,
            details=details if details else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing monitoring connection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers/schema")
async def get_provider_schemas():
    """Get configuration schemas for all providers."""
    schemas = {}
    for provider in MonitoringProvider:
        schemas[provider.value] = MonitoringIntegration.get_config_schema(provider)
    return schemas


# ============================================================================
# Connection Test Functions
# ============================================================================


async def _test_datadog(config: dict) -> tuple[bool, str, dict]:
    """Test DataDog connection."""
    import asyncio

    import requests

    try:
        api_key = config.get("api_key")
        app_key = config.get("app_key")
        site = config.get("site", "datadoghq.com")

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(
                f"https://api.{site}/api/v1/validate",
                headers={
                    "DD-API-KEY": api_key,
                    "DD-APPLICATION-KEY": app_key,
                },
                timeout=10,
            ),
        )

        if response.status_code == 200:
            return True, "Connection successful", {"valid": True}
        else:
            return False, f"Connection failed: {response.text}", {}

    except Exception as e:
        return False, f"Connection error: {str(e)}", {}


async def _test_otlp(config: dict) -> tuple[bool, str, dict]:
    """Test OTLP endpoint connection."""
    import asyncio

    import requests

    try:
        endpoint = config.get("endpoint")
        headers = config.get("headers", {})

        # Simple health check
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: requests.options(endpoint, headers=headers, timeout=10))

        if response.status_code < 500:
            return True, "Endpoint reachable", {"status_code": response.status_code}
        else:
            return False, f"Endpoint error: {response.status_code}", {}

    except Exception as e:
        return False, f"Connection error: {str(e)}", {}


async def _test_grafana_cloud(config: dict) -> tuple[bool, str, dict]:
    """Test Grafana Cloud connection."""
    import asyncio

    import requests

    try:
        prometheus_url = config.get("prometheus_url")
        username = config.get("username")
        api_key = config.get("api_key")

        # Test Prometheus remote write endpoint
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(
                f"{prometheus_url}/api/v1/query?query=up",
                auth=(username, api_key),
                timeout=10,
            ),
        )

        if response.status_code == 200:
            return True, "Connection successful", {"status": "active"}
        else:
            return False, f"Connection failed: {response.status_code}", {}

    except Exception as e:
        return False, f"Connection error: {str(e)}", {}


async def _test_prometheus(config: dict) -> tuple[bool, str, dict]:
    """Test Prometheus Pushgateway connection."""
    import asyncio

    import requests

    try:
        pushgateway_url = config.get("pushgateway_url")
        basic_auth = config.get("basic_auth")

        auth = None
        if basic_auth:
            auth = (basic_auth.get("username"), basic_auth.get("password"))

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(
                f"{pushgateway_url}/metrics",
                auth=auth,
                timeout=10,
            ),
        )

        if response.status_code == 200:
            return True, "Pushgateway reachable", {}
        else:
            return False, f"Connection failed: {response.status_code}", {}

    except Exception as e:
        return False, f"Connection error: {str(e)}", {}


async def _test_webhook(config: dict) -> tuple[bool, str, dict]:
    """Test webhook endpoint connection."""
    import asyncio

    import requests

    try:
        url = config.get("url")
        method = config.get("method", "POST")
        headers = config.get("headers", {})

        # Send test payload
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.request(
                method=method,
                url=url,
                headers={**headers, "Content-Type": "application/json"},
                json={"test": True, "source": "synkora"},
                timeout=10,
            ),
        )

        if response.status_code < 400:
            return True, "Webhook test successful", {"status_code": response.status_code}
        else:
            return False, f"Webhook error: {response.status_code}", {}

    except Exception as e:
        return False, f"Connection error: {str(e)}", {}


async def _test_slack(config: dict) -> tuple[bool, str, dict]:
    """Test Slack webhook connection."""
    import asyncio

    import requests

    try:
        webhook_url = config.get("webhook_url")

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                webhook_url,
                json={"text": "Synkora monitoring test - connection verified"},
                timeout=10,
            ),
        )

        if response.status_code == 200:
            return True, "Slack webhook test successful", {}
        else:
            return False, f"Slack error: {response.text}", {}

    except Exception as e:
        return False, f"Connection error: {str(e)}", {}


async def _test_pagerduty(config: dict) -> tuple[bool, str, dict]:
    """Test PagerDuty integration."""
    import asyncio

    import requests

    try:
        routing_key = config.get("routing_key")

        # Verify routing key by attempting an event submission
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                "https://events.pagerduty.com/v2/enqueue",
                json={
                    "routing_key": routing_key,
                    "event_action": "trigger",
                    "payload": {
                        "summary": "Synkora monitoring test",
                        "severity": "info",
                        "source": "synkora-test",
                    },
                },
                timeout=10,
            ),
        )

        if response.status_code == 202:
            # Acknowledge the test event
            data = response.json()
            return True, "PagerDuty test successful", {"dedup_key": data.get("dedup_key")}
        else:
            return False, f"PagerDuty error: {response.text}", {}

    except Exception as e:
        return False, f"Connection error: {str(e)}", {}


# ============================================================================
# Helper Functions
# ============================================================================


async def _get_integration(db: AsyncSession, integration_id: UUID, tenant_id: UUID) -> MonitoringIntegration:
    """Get a monitoring integration by ID with tenant verification."""
    result = await db.execute(
        select(MonitoringIntegration).filter(
            MonitoringIntegration.id == integration_id,
            MonitoringIntegration.tenant_id == tenant_id,
        )
    )
    integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(status_code=404, detail="Monitoring integration not found")

    return integration


def _integration_to_response(
    integration: MonitoringIntegration,
) -> MonitoringIntegrationResponse:
    """Convert MonitoringIntegration model to response schema."""
    return MonitoringIntegrationResponse(
        id=integration.id,
        tenant_id=integration.tenant_id,
        name=integration.name,
        provider=integration.provider.value,
        is_active=integration.is_active,
        export_settings=integration.export_settings,
        last_sync_at=integration.last_sync_at,
        sync_status=integration.sync_status,
        sync_error=integration.sync_error,
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )
