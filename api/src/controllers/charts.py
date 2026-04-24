"""Chart controller for managing chart operations."""

import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_db
from ..middleware.auth_middleware import get_current_account, get_current_tenant_id
from ..models import Chart
from ..models.agent import Agent

router = APIRouter(prefix="/charts", tags=["charts"])

# Patterns that indicate XSS payloads in string values
_XSS_PATTERN = re.compile(
    r"<script|onerror\s*=|onload\s*=|javascript\s*:|<iframe|<object|<embed|<img[^>]+on\w+\s*=",
    re.IGNORECASE,
)


def _check_xss(value: object, path: str = "") -> None:
    """Recursively walk a dict/list structure and reject XSS payloads."""
    if isinstance(value, str):
        if _XSS_PATTERN.search(value):
            raise ValueError(f"Potentially unsafe content detected in field '{path}'")
    elif isinstance(value, dict):
        for k, v in value.items():
            _check_xss(v, f"{path}.{k}" if path else k)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _check_xss(item, f"{path}[{i}]")


class ChartCreate(BaseModel):
    """Schema for creating a chart."""

    agent_id: UUID
    conversation_id: UUID | None = None
    message_id: UUID | None = None
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    chart_type: str = Field(..., min_length=1, max_length=50)
    library: str = Field(..., min_length=1, max_length=50)
    config: dict
    data: dict
    query: str | None = None

    @field_validator("title", "description", mode="before")
    @classmethod
    def validate_text_fields(cls, v: object) -> object:
        if isinstance(v, str) and _XSS_PATTERN.search(v):
            raise ValueError("Potentially unsafe content detected")
        return v

    @field_validator("config", "data", mode="after")
    @classmethod
    def validate_no_xss(cls, v: object) -> object:
        _check_xss(v)
        return v


class ChartUpdate(BaseModel):
    """Schema for updating a chart."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    config: dict | None = None
    data: dict | None = None

    @field_validator("title", "description", mode="before")
    @classmethod
    def validate_text_fields(cls, v: object) -> object:
        if isinstance(v, str) and _XSS_PATTERN.search(v):
            raise ValueError("Potentially unsafe content detected")
        return v

    @field_validator("config", "data", mode="after")
    @classmethod
    def validate_no_xss(cls, v: object) -> object:
        if v is not None:
            _check_xss(v)
        return v


class ChartResponse(BaseModel):
    """Schema for chart response."""

    id: UUID
    tenant_id: UUID
    agent_id: UUID
    conversation_id: UUID | None
    message_id: UUID | None
    title: str
    description: str | None
    chart_type: str
    library: str
    config: dict
    data: dict
    query: str | None
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


def _chart_to_response(chart: Chart) -> ChartResponse:
    return ChartResponse(
        id=chart.id,
        tenant_id=chart.tenant_id,
        agent_id=chart.agent_id,
        conversation_id=chart.conversation_id,
        message_id=chart.message_id,
        title=chart.title,
        description=chart.description,
        chart_type=chart.chart_type,
        library=chart.library,
        config=chart.config,
        data=chart.data,
        query=chart.query,
        created_at=chart.created_at.isoformat(),
        updated_at=chart.updated_at.isoformat(),
    )


@router.post("", response_model=ChartResponse, status_code=status.HTTP_201_CREATED)
async def create_chart(
    chart_data: ChartCreate,
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Create a new chart."""
    # SECURITY: Verify the agent belongs to the current tenant (cross-tenant AuthZ check)
    agent_result = await db.execute(
        select(Agent).where(Agent.id == chart_data.agent_id, Agent.tenant_id == tenant_id)
    )
    if agent_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    chart = Chart(
        tenant_id=tenant_id,
        agent_id=chart_data.agent_id,
        conversation_id=chart_data.conversation_id,
        message_id=chart_data.message_id,
        title=chart_data.title,
        description=chart_data.description,
        chart_type=chart_data.chart_type,
        library=chart_data.library,
        config=chart_data.config,
        data=chart_data.data,
        query=chart_data.query,
    )

    db.add(chart)
    await db.commit()
    await db.refresh(chart)

    return _chart_to_response(chart)


@router.get("", response_model=list[ChartResponse])
async def list_charts(
    agent_id: UUID | None = None,
    conversation_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """List charts for the current tenant with pagination."""
    query = select(Chart).where(Chart.tenant_id == tenant_id)

    if agent_id:
        query = query.where(Chart.agent_id == agent_id)
    if conversation_id:
        query = query.where(Chart.conversation_id == conversation_id)

    query = query.order_by(Chart.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    charts = result.scalars().all()

    return [_chart_to_response(chart) for chart in charts]


@router.get("/{chart_id}", response_model=ChartResponse)
async def get_chart(
    chart_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Get a specific chart by ID."""
    result = await db.execute(select(Chart).where(Chart.id == chart_id, Chart.tenant_id == tenant_id))
    chart = result.scalar_one_or_none()

    if not chart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found")

    return _chart_to_response(chart)


@router.patch("/{chart_id}", response_model=ChartResponse)
async def update_chart(
    chart_id: UUID,
    chart_data: ChartUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Update a chart."""
    result = await db.execute(select(Chart).where(Chart.id == chart_id, Chart.tenant_id == tenant_id))
    chart = result.scalar_one_or_none()

    if not chart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found")

    if chart_data.title is not None:
        chart.title = chart_data.title
    if chart_data.description is not None:
        chart.description = chart_data.description
    if chart_data.config is not None:
        chart.config = chart_data.config
    if chart_data.data is not None:
        chart.data = chart_data.data

    await db.commit()
    await db.refresh(chart)

    return _chart_to_response(chart)


@router.delete("/{chart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chart(
    chart_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Delete a chart."""
    result = await db.execute(select(Chart).where(Chart.id == chart_id, Chart.tenant_id == tenant_id))
    chart = result.scalar_one_or_none()

    if not chart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found")

    await db.delete(chart)
    await db.commit()
