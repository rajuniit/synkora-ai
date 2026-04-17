"""
Database Tools for Synkora Agents.

Provides internal database query capabilities for PostgreSQL and Elasticsearch,
as well as chart generation from query results.
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.chart import Chart
from src.models.database_connection import DatabaseConnection
from src.services.charts import ChartService
from src.services.database import ElasticsearchConnector, PostgreSQLConnector, SQLiteConnector

logger = logging.getLogger(__name__)


async def internal_query_database(
    connection_id: str, query: str, tenant_id: str, db_session: AsyncSession, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Execute a query on a configured database connection.

    This internal tool allows agents to query PostgreSQL or Elasticsearch databases
    that have been configured by the user. It handles connection management,
    query execution, and result formatting.

    Args:
        connection_id: UUID of the database connection to use
        query: Natural language query or SQL/DSL query string
        tenant_id: Tenant ID for authorization
        db_session: Database session for fetching connection details
        config: Optional configuration dictionary

    Returns:
        Dictionary containing:
        - success: Whether the query succeeded
        - data: Query results (list of rows/documents)
        - row_count: Number of rows/documents returned
        - columns: Column names (for SQL queries)
        - query_executed: The actual query that was executed
        - connection_name: Name of the database connection used
        - database_type: Type of database (postgresql, elasticsearch)
        - error: Error message (if any)
    """
    try:
        # Fetch database connection
        stmt = select(DatabaseConnection).where(
            DatabaseConnection.id == UUID(str(connection_id)), DatabaseConnection.tenant_id == UUID(str(tenant_id))
        )
        result = await db_session.execute(stmt)
        connection = result.scalar_one_or_none()

        if not connection:
            return {"success": False, "error": f"Database connection not found: {connection_id}"}

        # Check connection status
        if connection.status != "active":
            return {"success": False, "error": f"Database connection is not active. Status: {connection.status}"}

        # Execute query based on database type
        if connection.database_type == "POSTGRESQL":
            return await _execute_postgresql_query(connection, query)
        elif connection.database_type == "ELASTICSEARCH":
            return await _execute_elasticsearch_query(connection, query)
        elif connection.database_type == "SQLITE":
            return await _execute_sqlite_query(connection, query)
        else:
            return {"success": False, "error": f"Unsupported database type: {connection.database_type}"}

    except Exception as e:
        logger.warning(f"Error executing database query: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to execute query: {str(e)}"}


async def _execute_postgresql_query(connection: DatabaseConnection, query: str) -> dict[str, Any]:
    """Execute a PostgreSQL query."""
    try:
        connector = PostgreSQLConnector(connection)
        connected = await connector.connect()

        if not connected:
            return {
                "success": False,
                "error": "Failed to connect to PostgreSQL database. Check connection credentials and network access.",
                "connection_name": connection.name,
                "database_type": "postgresql",
            }

        try:
            # Execute the query
            result = await connector.execute_query(query)

            return {
                "success": True,
                "data": result.get("rows", []),
                "row_count": result.get("row_count", 0),
                "columns": result.get("columns", []),
                "query_executed": result.get("query", query),
                "connection_name": connection.name,
                "database_type": "postgresql",
            }
        finally:
            await connector.disconnect()

    except Exception as e:
        logger.warning(f"PostgreSQL query error: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"PostgreSQL query failed: {str(e)}",
            "connection_name": connection.name,
            "database_type": "postgresql",
        }


async def _execute_elasticsearch_query(connection: DatabaseConnection, query: str) -> dict[str, Any]:
    """Execute an Elasticsearch query."""
    try:
        connector = ElasticsearchConnector(connection)
        connected = await connector.connect()

        if not connected:
            return {
                "success": False,
                "error": "Failed to connect to Elasticsearch. Check connection credentials and network access.",
                "connection_name": connection.name,
                "database_type": "elasticsearch",
            }

        try:
            # Parse query as JSON if it looks like DSL
            import json

            try:
                query_dsl = json.loads(query)
                # Assume it's a search query
                result = await connector.search(
                    index=query_dsl.get("index", "_all"),
                    query=query_dsl.get("query", {}),
                    size=query_dsl.get("size", 10),
                )
            except json.JSONDecodeError:
                # Treat as natural language query - would need query builder
                return {
                    "success": False,
                    "error": "Natural language queries for Elasticsearch not yet implemented. Please provide DSL query as JSON.",
                    "connection_name": connection.name,
                    "database_type": "elasticsearch",
                }

            return {
                "success": True,
                "data": result.get("hits", []),
                "row_count": len(result.get("hits", [])),
                "total_hits": result.get("total", 0),
                "query_executed": query,
                "connection_name": connection.name,
                "database_type": "elasticsearch",
            }
        finally:
            await connector.disconnect()

    except Exception as e:
        logger.warning(f"Elasticsearch query error: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Elasticsearch query failed: {str(e)}",
            "connection_name": connection.name,
            "database_type": "elasticsearch",
        }


async def internal_list_database_connections(
    tenant_id: str, db_session: AsyncSession, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    List all database connections available to the agent.

    This tool allows agents to discover what database connections are configured
    and available for querying.

    Args:
        tenant_id: Tenant ID for authorization
        db_session: Database session for fetching connections
        config: Optional configuration dictionary

    Returns:
        Dictionary containing:
        - success: Whether the operation succeeded
        - connections: List of available connections with details
        - count: Number of connections
        - error: Error message (if any)
    """
    try:
        # Fetch all active database connections for tenant
        stmt = select(DatabaseConnection).where(
            DatabaseConnection.tenant_id == UUID(str(tenant_id)), DatabaseConnection.status == "active"
        )
        result = await db_session.execute(stmt)
        connections = list(result.scalars().all())

        # Format connection details
        connection_list = []
        for conn in connections:
            connection_list.append(
                {
                    "id": str(conn.id),
                    "name": conn.name,
                    "type": conn.database_type,
                    "host": conn.host,
                    "port": conn.port,
                    "database": conn.database_name,
                    "database_path": conn.database_path,
                    "description": f"{conn.database_type.upper()} database"
                    + (
                        f" at {conn.host}:{conn.port}/{conn.database_name}"
                        if conn.host
                        else f" at {conn.database_path}"
                        if conn.database_path
                        else ""
                    ),
                }
            )

        return {"success": True, "connections": connection_list, "count": len(connection_list)}

    except Exception as e:
        logger.warning(f"Error listing database connections: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to list connections: {str(e)}"}


async def internal_get_database_schema(
    connection_id: str, tenant_id: str, db_session: AsyncSession, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Get schema information for a database connection.

    This tool allows agents to understand the structure of a database,
    including tables, columns, and data types.

    Args:
        connection_id: UUID of the database connection
        tenant_id: Tenant ID for authorization
        db_session: Database session for fetching connection details
        config: Optional configuration dictionary

    Returns:
        Dictionary containing:
        - success: Whether the operation succeeded
        - schema: Schema information (tables, indices, etc.)
        - connection_name: Name of the database connection
        - database_type: Type of database
        - error: Error message (if any)
    """
    try:
        # Fetch database connection
        stmt = select(DatabaseConnection).where(
            DatabaseConnection.id == UUID(str(connection_id)), DatabaseConnection.tenant_id == UUID(str(tenant_id))
        )
        result = await db_session.execute(stmt)
        connection = result.scalar_one_or_none()

        if not connection:
            return {"success": False, "error": f"Database connection not found: {connection_id}"}

        # Get schema based on database type
        if connection.database_type == "POSTGRESQL":
            return await _get_postgresql_schema(connection)
        elif connection.database_type == "ELASTICSEARCH":
            return await _get_elasticsearch_schema(connection)
        elif connection.database_type == "SQLITE":
            return await _get_sqlite_schema(connection)
        else:
            return {"success": False, "error": f"Unsupported database type: {connection.database_type}"}

    except Exception as e:
        logger.warning(f"Error getting database schema: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to get schema: {str(e)}"}


async def _get_postgresql_schema(connection: DatabaseConnection) -> dict[str, Any]:
    """Get PostgreSQL schema information."""
    try:
        connector = PostgreSQLConnector(connection)
        await connector.connect()

        try:
            tables = await connector.get_tables()

            # Get detailed info for each table
            schema_info = []
            for table in tables[:20]:  # Limit to first 20 tables
                table_info = await connector.get_table_info(table)
                schema_info.append(table_info)

            return {
                "success": True,
                "schema": {"tables": schema_info, "total_tables": len(tables)},
                "connection_name": connection.name,
                "database_type": "postgresql",
            }
        finally:
            await connector.disconnect()

    except Exception as e:
        logger.warning(f"PostgreSQL schema error: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to get PostgreSQL schema: {str(e)}",
            "connection_name": connection.name,
            "database_type": "postgresql",
        }


async def _get_elasticsearch_schema(connection: DatabaseConnection) -> dict[str, Any]:
    """Get Elasticsearch schema information."""
    try:
        connector = ElasticsearchConnector(connection)
        await connector.connect()

        try:
            indices = await connector.list_indices()

            # Get mappings for each index
            schema_info = []
            for index in indices[:20]:  # Limit to first 20 indices
                mapping = await connector.get_mapping(index)
                schema_info.append({"index": index, "mapping": mapping})

            return {
                "success": True,
                "schema": {"indices": schema_info, "total_indices": len(indices)},
                "connection_name": connection.name,
                "database_type": "elasticsearch",
            }
        finally:
            await connector.disconnect()

    except Exception as e:
        logger.warning(f"Elasticsearch schema error: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to get Elasticsearch schema: {str(e)}",
            "connection_name": connection.name,
            "database_type": "elasticsearch",
        }


async def _execute_sqlite_query(connection: DatabaseConnection, query: str) -> dict[str, Any]:
    """Execute a SQLite query."""
    try:
        connector = SQLiteConnector(database_path=connection.database_path)
        await connector.connect()

        try:
            # Execute the query
            result = await connector.execute_query(query)

            return {
                "success": True,
                "data": result.get("rows", []),
                "row_count": result.get("row_count", 0),
                "columns": result.get("columns", []),
                "query_executed": result.get("query", query),
                "connection_name": connection.name,
                "database_type": "sqlite",
            }
        finally:
            await connector.disconnect()

    except Exception as e:
        logger.warning(f"SQLite query error: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"SQLite query failed: {str(e)}",
            "connection_name": connection.name,
            "database_type": "sqlite",
        }


async def _get_sqlite_schema(connection: DatabaseConnection) -> dict[str, Any]:
    """Get SQLite schema information."""
    try:
        connector = SQLiteConnector(database_path=connection.database_path)
        await connector.connect()

        try:
            schema_result = await connector.get_schema()

            if not schema_result.get("success"):
                return {
                    "success": False,
                    "error": schema_result.get("error", "Failed to get schema"),
                    "connection_name": connection.name,
                    "database_type": "sqlite",
                }

            tables = schema_result.get("tables", [])

            return {
                "success": True,
                "schema": {
                    "tables": tables[:20],  # Limit to first 20 tables
                    "total_tables": len(tables),
                },
                "connection_name": connection.name,
                "database_type": "sqlite",
            }
        finally:
            await connector.disconnect()

    except Exception as e:
        logger.warning(f"SQLite schema error: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to get SQLite schema: {str(e)}",
            "connection_name": connection.name,
            "database_type": "sqlite",
        }


async def internal_generate_chart(
    query_result: dict[str, Any],
    chart_type: str | None,
    title: str,
    agent_id: str,
    tenant_id: str,
    db_session: AsyncSession,
    conversation_id: str | None = None,
    message_id: str | None = None,
    description: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate a chart from database query results.

    This tool allows agents to create visualizations from data they've queried.
    The chart configuration is generated automatically based on the data structure,
    or can be customized using the config parameter.

    Args:
        query_result: Result from internal_query_database containing data
        chart_type: Type of chart (line, bar, pie, scatter, etc.) or None for auto-detection
        title: Chart title
        agent_id: Agent ID creating the chart
        tenant_id: Tenant ID for authorization
        db_session: Database session
        conversation_id: Optional conversation ID to link chart to
        message_id: Optional message ID to link chart to
        description: Optional chart description
        config: Optional custom chart configuration

    Returns:
        Dictionary containing:
        - success: Whether chart generation succeeded
        - chart_id: ID of the created chart
        - chart_config: Generated chart configuration
        - chart_data: Formatted chart data
        - error: Error message (if any)
    """
    try:
        # Normalize query_result — the LLM may pass data in several shapes:
        #   1. A plain list of rows (e.g. from micromobility tool results aggregated by LLM)
        #   2. A flat dict of key→value pairs (e.g. {"total_reports": 276, "pending": 216})
        #   3. The standard {"success": True, "data": [...]} format from internal_query_database
        if isinstance(query_result, list):
            query_result = {"success": True, "data": query_result, "row_count": len(query_result)}
        elif isinstance(query_result, dict) and "data" not in query_result:
            # Flat dict — convert each key/value into a row suitable for charting
            rows = [{"label": k, "value": v} for k, v in query_result.items() if isinstance(v, (int, float))]
            query_result = {"success": True, "data": rows, "row_count": len(rows)}

        # Clean query_result to remove any non-serializable objects
        # This prevents Session objects or other non-JSON-serializable data from being stored
        clean_query_result = {
            "success": query_result.get("success"),
            "data": query_result.get("data"),
            "row_count": query_result.get("row_count"),
            "columns": query_result.get("columns"),
            "query_executed": query_result.get("query_executed"),
            "connection_name": query_result.get("connection_name"),
            "database_type": query_result.get("database_type"),
        }

        # Extract data from query result
        # The LLM may pass query results with or without a "success" key
        data = clean_query_result.get("data", [])

        # If data is a paginated API response (e.g. micromobility list_trips returns
        # {"count": N, "next": ..., "results": [...]}), extract the actual rows.
        if isinstance(data, dict) and "results" in data:
            data = data["results"]

        # Validate that we have data to work with
        if not data:
            error_msg = clean_query_result.get("error", "No data available to generate chart")
            logger.warning(f"Chart generation failed: {error_msg}")
            return {"success": False, "error": error_msg}

        logger.info(f"Generating chart with {len(data)} data points")

        # Determine chart type if not specified
        if not chart_type:
            chart_type = "bar"  # Default to bar chart

        # Initialize chart service with db_session
        chart_service = ChartService(db_session)

        # Generate chart data structure (doesn't need db)
        chart_data = chart_service.generate_chart_from_query_result(query_result=data, chart_type=chart_type)

        # Generate chart configuration (doesn't need db)
        library = "chartjs"  # Default library
        chart_config = chart_service._generate_chart_config(chart_type=chart_type, data=chart_data, library=library)

        # Merge with custom config if provided, but exclude runtime context
        if config:
            # Filter out non-serializable keys like _runtime_context
            clean_config = {k: v for k, v in config.items() if k != "_runtime_context" and not k.startswith("_")}
            if clean_config:
                chart_config.update(clean_config)

        # Create chart in database using a fresh session to avoid conflicts
        # when multiple charts are saved concurrently from parallel tool calls
        from src.core.database import get_async_session_factory

        chart_id: str | None = None
        session_factory = get_async_session_factory()
        async with session_factory() as new_session:
            async with new_session.begin():
                chart = Chart(
                    tenant_id=UUID(str(tenant_id)),
                    agent_id=UUID(str(agent_id)),
                    conversation_id=UUID(str(conversation_id)) if conversation_id else None,
                    message_id=UUID(str(message_id)) if message_id else None,
                    title=title,
                    description=description
                    or f"Chart generated from {clean_query_result.get('connection_name', 'database')} query",
                    chart_type=chart_type,
                    library=library,
                    config=chart_config,
                    data=chart_data,
                    query=clean_query_result.get("query_executed"),
                )
                new_session.add(chart)
            await new_session.refresh(chart)
            chart_id = str(chart.id)
            chart_type_saved = chart.chart_type
            chart_library = chart.library
            chart_config_saved = chart.config
            chart_data_saved = chart.data

        return {
            "success": True,
            "chart_id": chart_id,
            "chart_type": chart_type_saved,
            "library": chart_library,
            "chart_config": chart_config_saved,
            "chart_data": chart_data_saved,
            "message": f"Chart '{title}' created successfully",
        }

    except Exception as e:
        logger.warning(f"Error generating chart: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to generate chart: {str(e)}"}


async def internal_query_and_chart(
    connection_id: str,
    query: str,
    chart_title: str,
    tenant_id: str,
    agent_id: str,
    db_session: AsyncSession,
    chart_type: str | None = None,
    conversation_id: str | None = None,
    message_id: str | None = None,
    chart_description: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Execute a database query and automatically generate a chart from the results.

    This is a convenience tool that combines query execution and chart generation
    in a single step. It's useful when you know you want to visualize the query results.

    Args:
        connection_id: UUID of the database connection to use
        query: SQL or DSL query string
        chart_title: Title for the generated chart
        tenant_id: Tenant ID for authorization
        agent_id: Agent ID creating the chart
        db_session: Database session
        chart_type: Optional chart type (auto-detected if not provided)
        conversation_id: Optional conversation ID
        message_id: Optional message ID
        chart_description: Optional chart description
        config: Optional custom chart configuration

    Returns:
        Dictionary containing:
        - success: Whether the operation succeeded
        - query_result: Results from the database query
        - chart: Chart generation result
        - error: Error message (if any)
    """
    try:
        # Execute the query
        query_result = await internal_query_database(
            connection_id=connection_id, query=query, tenant_id=tenant_id, db_session=db_session
        )

        if not query_result.get("success"):
            return {
                "success": False,
                "error": f"Query failed: {query_result.get('error')}",
                "query_result": query_result,
            }

        # Create a clean query_result without any non-serializable objects
        clean_query_result = {
            "success": query_result.get("success"),
            "data": query_result.get("data"),
            "row_count": query_result.get("row_count"),
            "columns": query_result.get("columns"),
            "query_executed": query_result.get("query_executed"),
            "connection_name": query_result.get("connection_name"),
            "database_type": query_result.get("database_type"),
        }

        # Generate chart from results
        chart_result = await internal_generate_chart(
            query_result=clean_query_result,
            chart_type=chart_type,
            title=chart_title,
            agent_id=agent_id,
            tenant_id=tenant_id,
            db_session=db_session,
            conversation_id=conversation_id,
            message_id=message_id,
            description=chart_description,
            config=config,
        )

        return {
            "success": chart_result.get("success", False),
            "query_result": {
                "row_count": query_result.get("row_count"),
                "columns": query_result.get("columns"),
                "connection_name": query_result.get("connection_name"),
            },
            "chart": chart_result,
            "message": f"Query executed and chart '{chart_title}' generated successfully"
            if chart_result.get("success")
            else None,
            "error": chart_result.get("error") if not chart_result.get("success") else None,
        }

    except Exception as e:
        logger.warning(f"Error in query_and_chart: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to execute query and generate chart: {str(e)}"}
