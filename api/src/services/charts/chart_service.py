"""Chart service for generating chart configurations from data."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.chart import Chart


class ChartService:
    """Service for generating and managing charts."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_chart(
        self,
        tenant_id: UUID,
        title: str,
        chart_type: str,
        data: dict[str, Any],
        agent_id: UUID | None = None,
        conversation_id: UUID | None = None,
        message_id: UUID | None = None,
        description: str | None = None,
        query: str | None = None,
        library: str = "chartjs",
    ) -> Chart:
        """Create a new chart."""
        # Generate chart configuration based on type and library
        config = self._generate_chart_config(chart_type, data, library)

        chart = Chart(
            tenant_id=tenant_id,
            agent_id=agent_id,
            conversation_id=conversation_id,
            message_id=message_id,
            title=title,
            description=description,
            chart_type=chart_type,
            library=library,
            config=config,
            data=data,
            query=query,
        )

        self.db.add(chart)
        await self.db.commit()
        await self.db.refresh(chart)

        return chart

    async def get_chart(self, chart_id: UUID, tenant_id: UUID) -> Chart | None:
        """Get a chart by ID."""
        result = await self.db.execute(select(Chart).where(Chart.id == chart_id, Chart.tenant_id == tenant_id))
        return result.scalar_one_or_none()

    async def list_charts(
        self,
        tenant_id: UUID,
        agent_id: UUID | None = None,
        conversation_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Chart]:
        """List charts with optional filters."""
        query = select(Chart).where(Chart.tenant_id == tenant_id)

        if agent_id:
            query = query.where(Chart.agent_id == agent_id)
        if conversation_id:
            query = query.where(Chart.conversation_id == conversation_id)

        query = query.order_by(Chart.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_chart(self, chart_id: UUID, tenant_id: UUID) -> bool:
        """Delete a chart."""
        chart = await self.get_chart(chart_id, tenant_id)
        if not chart:
            return False

        await self.db.delete(chart)
        await self.db.commit()
        return True

    def _generate_chart_config(self, chart_type: str, data: dict[str, Any], library: str) -> dict[str, Any]:
        """Generate chart configuration based on type and library."""
        if library == "chartjs":
            return self._generate_chartjs_config(chart_type, data)
        elif library == "plotly":
            return self._generate_plotly_config(chart_type, data)
        else:
            raise ValueError(f"Unsupported chart library: {library}")

    def _generate_chartjs_config(self, chart_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Generate Chart.js configuration."""
        # Extract labels and datasets from data
        labels = data.get("labels", [])
        datasets = data.get("datasets", [])

        # Base configuration
        config = {
            "type": chart_type,
            "data": {"labels": labels, "datasets": datasets},
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "plugins": {"legend": {"display": True, "position": "top"}, "tooltip": {"enabled": True}},
            },
        }

        # Add type-specific options
        if chart_type in ["bar", "line"]:
            config["options"]["scales"] = {"y": {"beginAtZero": True}}

        return config

    def _generate_plotly_config(self, chart_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Generate Plotly configuration."""
        # Extract data
        x_data = data.get("x", [])
        y_data = data.get("y", [])

        # Map chart types to Plotly types
        plotly_type_map = {"bar": "bar", "line": "scatter", "pie": "pie", "scatter": "scatter"}

        plotly_type = plotly_type_map.get(chart_type, "scatter")

        # Base configuration
        config = {
            "data": [
                {
                    "type": plotly_type,
                    "x": x_data,
                    "y": y_data,
                    "mode": "lines+markers" if plotly_type == "scatter" else None,
                }
            ],
            "layout": {"autosize": True, "margin": {"l": 50, "r": 50, "t": 50, "b": 50}},
        }

        return config

    def generate_chart_from_query_result(
        self,
        query_result: list[dict[str, Any]],
        chart_type: str = "bar",
        x_column: str | None = None,
        y_column: str | None = None,
    ) -> dict[str, Any]:
        """Generate chart data from database query result."""
        if not query_result:
            return {"labels": [], "datasets": []}

        # Auto-detect columns if not specified
        if not x_column or not y_column:
            columns = list(query_result[0].keys())
            if len(columns) >= 2:
                x_column = columns[0]
                y_column = columns[1]
            else:
                raise ValueError("Query result must have at least 2 columns")

        # Extract data
        labels = [str(row.get(x_column, "")) for row in query_result]
        values = [float(row.get(y_column, 0)) for row in query_result]

        # Generate chart data
        chart_data = {
            "labels": labels,
            "datasets": [
                {
                    "label": y_column,
                    "data": values,
                    "backgroundColor": self._generate_colors(len(values)),
                    "borderColor": self._generate_colors(len(values), alpha=1.0),
                    "borderWidth": 1,
                }
            ],
        }

        return chart_data

    def _generate_colors(self, count: int, alpha: float = 0.6) -> list[str]:
        """Generate a list of colors for chart datasets."""
        base_colors = [
            (54, 162, 235),  # Blue
            (255, 99, 132),  # Red
            (255, 206, 86),  # Yellow
            (75, 192, 192),  # Green
            (153, 102, 255),  # Purple
            (255, 159, 64),  # Orange
            (199, 199, 199),  # Grey
            (83, 102, 255),  # Indigo
            (255, 99, 255),  # Pink
            (99, 255, 132),  # Light Green
        ]

        colors = []
        for i in range(count):
            r, g, b = base_colors[i % len(base_colors)]
            colors.append(f"rgba({r}, {g}, {b}, {alpha})")

        return colors
