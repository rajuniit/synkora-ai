"""
Database-related Celery tasks for scheduled task execution.
"""

import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select

from src.celery_app import celery_app
from src.core.database import get_db
from src.models.database_connection import DatabaseConnection, DatabaseConnectionType
from src.services.database import ElasticsearchConnector, PostgreSQLConnector

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.execute_database_query")
def execute_database_query(connection_id: str, query: str, task_id: str = None) -> dict[str, Any]:
    """
    Execute a database query for a scheduled task.

    Args:
        connection_id: UUID of the database connection
        query: SQL/query string to execute
        task_id: Optional task ID for logging

    Returns:
        Dict containing query results or error information
    """
    db = next(get_db())

    try:
        # Get database connection
        stmt = select(DatabaseConnection).where(DatabaseConnection.id == UUID(connection_id))
        result = db.execute(stmt)
        connection = result.scalar_one_or_none()

        if not connection:
            raise ValueError(f"Database connection {connection_id} not found")

        # Create appropriate connector
        if connection.database_type == DatabaseConnectionType.POSTGRESQL:
            connector = PostgreSQLConnector(connection)
        elif connection.database_type == DatabaseConnectionType.ELASTICSEARCH:
            connector = ElasticsearchConnector(connection)
        else:
            raise ValueError(f"Unsupported database type: {connection.database_type}")

        # All connectors are async — run in a fresh event loop (Celery workers are sync)
        async def _run():
            await connector.connect()
            try:
                results = await connector.execute_query(query)
                logger.info(f"Query executed successfully for task {task_id}")
                return {"success": True, "data": results, "row_count": len(results) if isinstance(results, list) else 0}
            finally:
                await connector.disconnect()

        return asyncio.run(_run())

    except Exception as e:
        logger.error(f"Error executing query for task {task_id}: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e), "data": None, "row_count": 0}
    finally:
        db.close()
