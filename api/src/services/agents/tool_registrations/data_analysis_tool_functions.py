"""Data Analysis Tool Functions - Implementation of data analysis tools for agents."""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def _parse_data_to_dataframe(data_str: str) -> pd.DataFrame | None:
    """
    Parse string data into a pandas DataFrame.

    Intelligently detects and parses:
    - JSON arrays
    - CSV format
    - TSV (tab-separated)
    - Other delimited formats

    Args:
        data_str: String containing data

    Returns:
        pd.DataFrame or None if parsing fails
    """
    import csv
    import io
    import json

    # Try JSON first
    try:
        json_data = json.loads(data_str)
        if isinstance(json_data, list):
            if len(json_data) > 0:
                return pd.DataFrame(json_data)
        elif isinstance(json_data, dict):
            # Single object, wrap in list
            return pd.DataFrame([json_data])
    except json.JSONDecodeError:
        pass

    # Try CSV
    try:
        # Detect delimiter (comma, semicolon, tab, pipe)
        sniffer = csv.Sniffer()
        sample = data_str[:1024]  # Use first 1KB for detection

        try:
            dialect = sniffer.sniff(sample, delimiters=",;\t|")
            delimiter = dialect.delimiter
        except csv.Error:
            # Default to comma
            delimiter = ","

        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(data_str), delimiter=delimiter)
        rows = list(csv_reader)

        if rows and len(rows) > 0:
            df = pd.DataFrame(rows)

            # Try to convert numeric strings to numbers
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col])
                except (ValueError, TypeError):
                    pass  # Keep as string

            return df
    except Exception as e:
        logger.debug(f"CSV parsing failed: {e}")

    # If all parsing fails
    logger.warning("Could not parse data string into DataFrame")
    return None


async def query_datadog_metrics(
    data_source_id: int, query: str, from_time: str, to_time: str, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Query metrics from Datadog monitoring platform.

    Args:
        data_source_id: The ID of the Datadog data source
        query: Datadog metric query (e.g., 'avg:system.cpu.user{*}')
        from_time: Start time in ISO format
        to_time: End time in ISO format
        config: Configuration with runtime context

    Returns:
        Query results with metrics data
    """
    try:
        from src.services.data_analysis_service import DataAnalysisService

        # Extract runtime context
        config = config or {}
        runtime_context = config.get("_runtime_context")

        if not runtime_context:
            return {"success": False, "error": "Runtime context not available"}

        db_session = (
            runtime_context.db_session if hasattr(runtime_context, "db_session") else runtime_context.get("db_session")
        )

        if not db_session:
            return {"success": False, "error": "Database session not available"}

        # Create service and query
        service = DataAnalysisService(db_session)
        result = await service.query_data_source(
            data_source_id=data_source_id,
            query_params={"query_type": "metrics", "query": query, "from_time": from_time, "to_time": to_time},
        )

        return result

    except Exception as e:
        logger.error(f"Datadog query error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def query_databricks(
    data_source_id: int, query: str, limit: int = 1000, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Execute SQL queries on Databricks data lakehouse.

    Args:
        data_source_id: The ID of the Databricks data source
        query: SQL query to execute
        limit: Maximum number of rows to return
        config: Configuration with runtime context

    Returns:
        Query results with rows and columns
    """
    try:
        from src.services.data_analysis_service import DataAnalysisService

        # Extract runtime context
        config = config or {}
        runtime_context = config.get("_runtime_context")

        if not runtime_context:
            return {"success": False, "error": "Runtime context not available"}

        db_session = (
            runtime_context.db_session if hasattr(runtime_context, "db_session") else runtime_context.get("db_session")
        )

        if not db_session:
            return {"success": False, "error": "Database session not available"}

        # Create service and query
        service = DataAnalysisService(db_session)
        result = await service.query_data_source(
            data_source_id=data_source_id, query_params={"query": query, "limit": limit}
        )

        return result

    except Exception as e:
        logger.error(f"Databricks query error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def query_docker_logs(
    data_source_id: int,
    container_id: str | None = None,
    container_name: str | None = None,
    since: str | None = None,
    tail: int = 1000,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Fetch logs from Docker containers.

    Args:
        data_source_id: The ID of the Docker data source
        container_id: Docker container ID (optional if container_name provided)
        container_name: Docker container name (optional if container_id provided)
        since: Only return logs since this time (ISO format, optional)
        tail: Number of lines from end of logs to show
        config: Configuration with runtime context

    Returns:
        Log lines with timestamps
    """
    try:
        from src.services.data_analysis_service import DataAnalysisService

        # Extract runtime context
        config = config or {}
        runtime_context = config.get("_runtime_context")

        if not runtime_context:
            return {"success": False, "error": "Runtime context not available"}

        db_session = (
            runtime_context.db_session if hasattr(runtime_context, "db_session") else runtime_context.get("db_session")
        )

        if not db_session:
            return {"success": False, "error": "Database session not available"}

        # Build query parameters
        query_params: dict[str, Any] = {"tail": tail}
        if container_id:
            query_params["container_id"] = container_id
        if container_name:
            query_params["container_name"] = container_name
        if since:
            query_params["since"] = since

        # Create service and query
        service = DataAnalysisService(db_session)
        result = await service.query_data_source(data_source_id=data_source_id, query_params=query_params)

        return result

    except Exception as e:
        logger.error(f"Docker logs query error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def analyze_data_statistics(
    data: str, columns: list[str] | None = None, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Calculate comprehensive statistics for a dataset.

    Args:
        data: Data as string (CSV, JSON, or other text format - will be auto-detected)
        columns: Specific columns to analyze (optional)
        config: Configuration with runtime context

    Returns:
        Statistics including mean, median, std dev, distributions, etc.
    """
    try:
        if not data or not isinstance(data, str):
            return {"success": False, "error": "Data must be provided as a string"}

        # Parse the string data into a structured format
        df = _parse_data_to_dataframe(data.strip())

        if df is None or df.empty:
            return {"success": False, "error": "Could not parse data or data is empty"}

        # Filter columns if specified
        if columns:
            missing_cols = [col for col in columns if col not in df.columns]
            if missing_cols:
                return {"success": False, "error": f"Columns not found in data: {', '.join(missing_cols)}"}
            df = df[columns]

        # Calculate statistics
        stats = {
            "success": True,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "data_types": df.dtypes.astype(str).to_dict(),
            "missing_values": df.isnull().sum().to_dict(),
            "missing_percentage": (df.isnull().sum() / len(df) * 100).to_dict(),
            "numeric_stats": {},
            "categorical_stats": {},
        }

        # Get numeric column statistics
        numeric_cols = df.select_dtypes(include=["number"]).columns
        for col in numeric_cols:
            col_data = df[col].dropna()
            if len(col_data) > 0:
                stats["numeric_stats"][col] = {
                    "count": int(col_data.count()),
                    "mean": float(col_data.mean()),
                    "median": float(col_data.median()),
                    "std": float(col_data.std()) if len(col_data) > 1 else 0.0,
                    "min": float(col_data.min()),
                    "max": float(col_data.max()),
                    "quartiles": {
                        "q25": float(col_data.quantile(0.25)),
                        "q50": float(col_data.quantile(0.50)),
                        "q75": float(col_data.quantile(0.75)),
                    },
                }

        # Get categorical column statistics
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns
        for col in categorical_cols:
            col_data = df[col].dropna()
            if len(col_data) > 0:
                value_counts = col_data.value_counts().head(10)
                stats["categorical_stats"][col] = {
                    "unique_count": int(col_data.nunique()),
                    "top_values": {str(k): int(v) for k, v in value_counts.items()},
                    "most_common": str(col_data.mode()[0]) if len(col_data.mode()) > 0 else None,
                }

        # Build visual chart configs for automatic chart rendering
        charts = []

        # Box plot for all numeric columns (Plotly)
        numeric_cols_list = list(numeric_cols)
        if numeric_cols_list:
            box_traces = [{"type": "box", "y": df[col].dropna().tolist(), "name": col} for col in numeric_cols_list[:8]]
            charts.append(
                {
                    "chart_type": "box",
                    "library": "plotly",
                    "title": "Numeric Column Distributions",
                    "description": "Box plots showing spread, median, and outliers for each numeric column",
                    "data": {"data": box_traces, "layout": {"showlegend": False}},
                    "table_data": df.head(50).astype(object).where(df.head(50).notna(), None).to_dict(orient="records"),
                }
            )

        # Bar chart: top values for first categorical column (if any, Recharts)
        if categorical_cols.size > 0:
            first_cat = categorical_cols[0]
            vc = df[first_cat].dropna().value_counts().head(10)
            if len(vc) > 0:
                charts.append(
                    {
                        "chart_type": "bar",
                        "library": "chartjs",
                        "title": f"Top Values: {first_cat}",
                        "description": f"Frequency distribution of {first_cat}",
                        "data": {
                            "labels": [str(k) for k in vc.index],
                            "datasets": [
                                {
                                    "label": "Count",
                                    "data": [int(v) for v in vc.values],
                                    "backgroundColor": "rgba(99, 102, 241, 0.6)",
                                    "borderColor": "rgba(99, 102, 241, 1)",
                                    "borderWidth": 1,
                                }
                            ],
                        },
                    }
                )

        # Missing value chart (if any nulls exist)
        missing = df.isnull().sum()
        missing = missing[missing > 0]
        if len(missing) > 0:
            charts.append(
                {
                    "chart_type": "bar",
                    "library": "chartjs",
                    "title": "Missing Values by Column",
                    "description": "Number of null/missing values per column",
                    "data": {
                        "labels": [str(k) for k in missing.index],
                        "datasets": [
                            {
                                "label": "Missing count",
                                "data": [int(v) for v in missing.values],
                                "backgroundColor": "rgba(239, 68, 68, 0.6)",
                                "borderColor": "rgba(239, 68, 68, 1)",
                                "borderWidth": 1,
                            }
                        ],
                    },
                }
            )

        stats["charts"] = charts
        return stats

    except Exception as e:
        logger.error(f"Data statistics error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def export_data_report(
    data: list[dict[str, Any]],
    format: str,
    filename: str | None = None,
    title: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Export analysis results or data to a file.

    Args:
        data: Array of data objects to export
        format: Export format (csv, excel, json, html)
        filename: Name for the file without extension (optional)
        title: Title for the report (optional)
        config: Configuration with runtime context

    Returns:
        Export result with download URL
    """
    try:
        import time

        from src.services.report_export_service import ReportExportService

        # Extract runtime context
        config = config or {}
        runtime_context = config.get("_runtime_context")

        if not runtime_context:
            return {"success": False, "error": "Runtime context not available"}

        db_session = (
            runtime_context.db_session if hasattr(runtime_context, "db_session") else runtime_context.get("db_session")
        )
        tenant_id = (
            runtime_context.tenant_id if hasattr(runtime_context, "tenant_id") else runtime_context.get("tenant_id")
        )

        if not db_session:
            return {"success": False, "error": "Database session not available"}

        if not tenant_id:
            return {"success": False, "error": "Tenant ID not available"}

        # Generate filename if not provided
        if not filename:
            filename = f"report_{int(time.time())}"

        # Create service and export
        service = ReportExportService(db_session)
        result = await service.export_report(
            data=data, format=format, filename=filename, title=title, tenant_id=str(tenant_id)
        )

        return result

    except Exception as e:
        logger.error(f"Report export error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
