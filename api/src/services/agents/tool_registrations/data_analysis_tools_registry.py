"""Data Analysis Tools Registry - Registers data analysis tools with the ADK tool registry."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_data_analysis_tools(registry: Any):
    """
    Register data analysis tools with the ADK tool registry.

    These tools allow agents to query various data sources (Datadog, Databricks, Docker),
    analyze uploaded files, generate statistics, and export reports in multiple formats.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.tool_registrations.data_analysis_tool_functions import (
        analyze_data_statistics,
        export_data_report,
        query_databricks,
        query_datadog_metrics,
        query_docker_logs,
    )
    from src.services.agents.tool_registrations.generate_chart_from_csv import (
        generate_chart_from_data,
    )

    # Register Datadog metrics query tool
    registry.register_tool(
        name="query_datadog_metrics",
        description="Query metrics from Datadog monitoring platform. Use this to fetch system metrics, application performance data, or custom metrics. Returns time-series data for analysis.",
        parameters={
            "type": "object",
            "properties": {
                "data_source_id": {"type": "integer", "description": "The ID of the Datadog data source to query"},
                "query": {"type": "string", "description": "The Datadog metric query (e.g., 'avg:system.cpu.user{*}')"},
                "from_time": {
                    "type": "string",
                    "description": "Start time in ISO format (e.g., '2024-01-01T00:00:00Z')",
                },
                "to_time": {"type": "string", "description": "End time in ISO format (e.g., '2024-01-31T23:59:59Z')"},
            },
            "required": ["data_source_id", "query", "from_time", "to_time"],
        },
        function=query_datadog_metrics,
    )

    # Register Databricks SQL query tool
    registry.register_tool(
        name="query_databricks",
        description="Execute SQL queries on Databricks data lakehouse. Use this to analyze large datasets, run complex queries, or aggregate data. Returns query results with rows and columns.",
        parameters={
            "type": "object",
            "properties": {
                "data_source_id": {"type": "integer", "description": "The ID of the Databricks data source to query"},
                "query": {
                    "type": "string",
                    "description": "SQL query to execute (e.g., 'SELECT * FROM users LIMIT 100')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of rows to return (default: 1000)",
                    "default": 1000,
                },
            },
            "required": ["data_source_id", "query"],
        },
        function=query_databricks,
    )

    # Register Docker logs query tool
    registry.register_tool(
        name="query_docker_logs",
        description="Fetch logs from Docker containers. Use this to analyze application logs, debug issues, or monitor container activity. Returns log lines with timestamps.",
        parameters={
            "type": "object",
            "properties": {
                "data_source_id": {"type": "integer", "description": "The ID of the Docker data source to query"},
                "container_id": {
                    "type": "string",
                    "description": "Docker container ID to fetch logs from (optional if container_name is provided)",
                },
                "container_name": {
                    "type": "string",
                    "description": "Docker container name (alternative to container_id)",
                },
                "since": {"type": "string", "description": "Only return logs since this time in ISO format (optional)"},
                "tail": {
                    "type": "integer",
                    "description": "Number of lines from the end of the logs to show (default: 1000)",
                    "default": 1000,
                },
            },
            "required": ["data_source_id"],
        },
        function=query_docker_logs,
    )

    # Register data statistics calculator tool
    registry.register_tool(
        name="analyze_data_statistics",
        description="Calculate comprehensive statistics for a dataset. Accepts data in multiple formats (CSV text, JSON string, or query results). Automatically detects format and parses. Returns summary statistics (mean, median, std dev), distributions, missing values, and data types. Use this to understand data patterns and uploaded file contents.",
        parameters={
            "type": "object",
            "properties": {
                "data": {
                    "type": "string",
                    "description": "Data as a string (CSV content, JSON array string, or any delimited text format - will be auto-detected and parsed)",
                },
                "columns": {
                    "type": "array",
                    "description": "Specific columns to analyze (optional, analyzes all if not specified)",
                    "items": {"type": "string"},
                },
            },
            "required": ["data"],
        },
        function=analyze_data_statistics,
    )

    # Register report export tool
    registry.register_tool(
        name="export_data_report",
        description="Export analysis results or data to a file. Supports CSV, Excel (.xlsx), JSON, and HTML formats. Returns download URL for the exported file. Use this to save and share analysis results.",
        parameters={
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "description": "Array of data objects to export",
                    "items": {"type": "object"},
                },
                "format": {
                    "type": "string",
                    "enum": ["csv", "excel", "json", "html"],
                    "description": "Export format (csv, excel, json, or html)",
                },
                "filename": {
                    "type": "string",
                    "description": "Name for the exported file without extension (optional, auto-generated if not provided)",
                },
                "title": {
                    "type": "string",
                    "description": "Title for the report (used in HTML/Excel headers, optional)",
                },
            },
            "required": ["data", "format"],
        },
        function=export_data_report,
    )

    # Register chart generation tool for CSV/JSON data (different from internal_generate_chart
    # which takes DB query results — this one takes raw CSV/JSON strings from uploaded files)
    registry.register_tool(
        name="generate_chart_from_data",
        description="Generate Chart.js visualization from CSV or JSON string data. Use this for uploaded files or raw data strings. For database query results, use internal_generate_chart instead. Supports bar, line, pie, doughnut, and scatter charts.",
        parameters={
            "type": "object",
            "properties": {
                "data": {
                    "type": "string",
                    "description": "CSV text or JSON array string containing the data to visualize",
                },
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "doughnut", "scatter"],
                    "description": "Type of chart to generate",
                },
                "title": {"type": "string", "description": "Chart title"},
                "x_column": {
                    "type": "string",
                    "description": "Column name for X-axis (required for bar, line, scatter charts)",
                },
                "y_column": {
                    "type": "string",
                    "description": "Column name for Y-axis (required for bar, line, scatter charts)",
                },
                "description": {"type": "string", "description": "Optional chart description"},
            },
            "required": ["data", "chart_type", "title"],
        },
        function=generate_chart_from_data,
    )

    logger.info("Registered 6 data analysis tools")
