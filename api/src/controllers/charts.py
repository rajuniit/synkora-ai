"""Chart controller for managing chart operations."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_db
from ..middleware.auth_middleware import get_current_account, get_current_tenant_id
from ..models import Chart

router = APIRouter(prefix="/charts", tags=["charts"])


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


class ChartUpdate(BaseModel):
    """Schema for updating a chart."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    config: dict | None = None
    data: dict | None = None


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


@router.post("", response_model=ChartResponse, status_code=status.HTTP_201_CREATED)
async def create_chart(
    chart_data: ChartCreate,
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Create a new chart."""
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


@router.get("", response_model=list[ChartResponse])
async def list_charts(
    agent_id: UUID | None = None,
    conversation_id: UUID | None = None,
    db: AsyncSession = Depends(get_async_db),
    current_account=Depends(get_current_account),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """List all charts for the current tenant."""
    query = select(Chart).where(Chart.tenant_id == tenant_id)

    if agent_id:
        query = query.where(Chart.agent_id == agent_id)
    if conversation_id:
        query = query.where(Chart.conversation_id == conversation_id)

    query = query.order_by(Chart.created_at.desc())

    result = await db.execute(query)
    charts = result.scalars().all()

    return [
        ChartResponse(
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
        for chart in charts
    ]


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

    # Update fields
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
