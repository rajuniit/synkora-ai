"""Data Analysis API endpoints."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.core.errors import safe_error_message
from src.middleware.auth_middleware import get_current_account, get_current_tenant_id
from src.models import Account
from src.services.data_analysis_service import DataAnalysisService
from src.services.report_export_service import ReportExportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/data-analysis", tags=["data-analysis"])


# Request/Response Models
class UploadFileResponse(BaseModel):
    """Response model for file upload."""

    success: bool
    message: str | None = None
    file_path: str | None = None
    file_name: str | None = None
    file_size: int | None = None
    file_type: str | None = None
    statistics: dict[str, Any] | None = None
    data_preview: list[dict[str, Any]] | None = None


class QueryDataSourceRequest(BaseModel):
    """Request model for querying data source."""

    data_source_id: int
    query_params: dict[str, Any] = Field(default_factory=dict)


class QueryDatabaseRequest(BaseModel):
    """Request model for querying database."""

    connection_id: str
    query: str
    limit: int | None = Field(None, gt=0, le=10000)


class ExportReportRequest(BaseModel):
    """Request model for exporting report."""

    data: list[dict[str, Any]] | dict[str, Any]
    format: str = Field(..., pattern="^(csv|excel|xlsx|json|html)$")
    filename: str | None = None
    title: str | None = None


class DataAnalysisResponse(BaseModel):
    """Response model for data analysis."""

    success: bool
    message: str | None = None
    data: Any = None
    error: str | None = None


class ReportExportResponse(BaseModel):
    """Response model for report export."""

    success: bool
    message: str | None = None
    format: str | None = None
    file_path: str | None = None
    file_name: str | None = None
    file_size: int | None = None
    download_url: str | None = None


# Endpoints
@router.post("/upload-file", response_model=UploadFileResponse)
async def upload_analysis_file(
    file: UploadFile = File(...),
    file_type: str = Query("auto", pattern="^(auto|csv|zip)$"),
    db: AsyncSession = Depends(get_async_db),
    current_account: Account = Depends(get_current_account),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> UploadFileResponse:
    """
    Upload CSV or ZIP file for data analysis.

    Args:
        file: File to upload
        file_type: Type of file (auto, csv, zip)
        db: Database session
        current_account: Authenticated user
        tenant_id: Current tenant ID

    Returns:
        Upload result with file info and data preview
    """
    try:
        # Validate file size (max 100MB)
        MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large. Maximum size is 100MB"
            )

        # Validate file type
        if not file.filename.endswith((".csv", ".zip")):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV and ZIP files are supported")

        # Process file
        service = DataAnalysisService(db, tenant_id)
        result = await service.upload_and_process_file(file, file_type)

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message", "File processing failed")
            )

        logger.info(f"File uploaded successfully: {file.filename}")

        return UploadFileResponse(
            success=True,
            message="File uploaded and processed successfully",
            file_path=result.get("file_path"),
            file_name=result.get("file_name"),
            file_size=result.get("file_size"),
            file_type=result.get("file_type"),
            statistics=result.get("statistics"),
            data_preview=result.get("data_preview"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=safe_error_message(e, "Failed to upload file", include_type=True),
        )


@router.post("/query-data-source", response_model=DataAnalysisResponse)
async def query_data_source(
    request: QueryDataSourceRequest,
    db: AsyncSession = Depends(get_async_db),
    current_account: Account = Depends(get_current_account),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> DataAnalysisResponse:
    """
    Query data from a configured data source (Datadog, Databricks, Docker).

    Args:
        request: Query request with data source ID and parameters
        db: Database session
        current_account: Authenticated user
        tenant_id: Current tenant ID

    Returns:
        Query results
    """
    try:
        service = DataAnalysisService(db, tenant_id)
        result = await service.query_data_source(request.data_source_id, request.query_params)

        if not result.get("success"):
            return DataAnalysisResponse(success=False, message=result.get("message"), error=result.get("error"))

        return DataAnalysisResponse(success=True, message="Query executed successfully", data=result)

    except Exception as e:
        logger.error(f"Error querying data source: {e}", exc_info=True)
        return DataAnalysisResponse(success=False, message=f"Query failed: {str(e)}", error=str(e))


@router.post("/query-database", response_model=DataAnalysisResponse)
async def query_database(
    request: QueryDatabaseRequest,
    db: AsyncSession = Depends(get_async_db),
    current_account: Account = Depends(get_current_account),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> DataAnalysisResponse:
    """
    Query data from a configured database connection.

    Args:
        request: Query request with connection ID and SQL query
        db: Database session
        current_account: Authenticated user
        tenant_id: Current tenant ID

    Returns:
        Query results
    """
    try:
        service = DataAnalysisService(db, tenant_id)
        result = await service.query_database_connection(UUID(request.connection_id), request.query, request.limit)

        if not result.get("success"):
            return DataAnalysisResponse(success=False, message=result.get("message"), error=result.get("error"))

        return DataAnalysisResponse(success=True, message="Query executed successfully", data=result)

    except Exception as e:
        logger.error(f"Error querying database: {e}", exc_info=True)
        return DataAnalysisResponse(success=False, message=f"Query failed: {str(e)}", error=str(e))


@router.post("/export-report", response_model=ReportExportResponse)
async def export_report(
    request: ExportReportRequest,
    db: AsyncSession = Depends(get_async_db),
    current_account: Account = Depends(get_current_account),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> ReportExportResponse:
    """
    Export analysis results to various formats (CSV, Excel, JSON, HTML, PDF).

    Args:
        request: Export request with data and format
        db: Database session
        current_account: Authenticated user
        tenant_id: Current tenant ID

    Returns:
        Export result with file info
    """
    try:
        service = ReportExportService(db, tenant_id)

        # Prepare kwargs
        kwargs = {}
        if request.title:
            kwargs["title"] = request.title

        result = await service.export_report(request.data, request.format, request.filename, **kwargs)

        if not result.get("success"):
            return ReportExportResponse(
                success=False,
                message=result.get("message"),
            )

        # Generate download URL (assuming storage service provides this)
        download_url = f"/api/v1/files/download?path={result.get('file_path')}"

        return ReportExportResponse(
            success=True,
            message="Report exported successfully",
            format=result.get("format"),
            file_path=result.get("file_path"),
            file_name=result.get("file_name"),
            file_size=result.get("file_size"),
            download_url=download_url,
        )

    except Exception as e:
        logger.error(f"Error exporting report: {e}", exc_info=True)
        return ReportExportResponse(success=False, message=f"Export failed: {str(e)}")


@router.get("/connectors", response_model=dict[str, Any])
async def list_available_connectors(current_account: Account = Depends(get_current_account)) -> dict[str, Any]:
    """
    List available data analysis connectors.

    Args:
        current_account: Authenticated user

    Returns:
        List of available connectors with their capabilities
    """
    return {
        "connectors": [
            {
                "type": "DATADOG",
                "name": "Datadog",
                "description": "Fetch metrics and logs from Datadog monitoring platform",
                "capabilities": ["metrics", "logs"],
                "config_fields": [
                    {"name": "api_key", "type": "string", "required": True, "sensitive": True},
                    {"name": "app_key", "type": "string", "required": True, "sensitive": True},
                    {"name": "site", "type": "string", "required": False, "default": "datadoghq.com"},
                ],
            },
            {
                "type": "DATABRICKS",
                "name": "Databricks",
                "description": "Execute SQL queries on Databricks data lakehouse",
                "capabilities": ["sql_query", "table_list"],
                "config_fields": [
                    {"name": "host", "type": "string", "required": True},
                    {"name": "token", "type": "string", "required": True, "sensitive": True},
                    {"name": "http_path", "type": "string", "required": True},
                    {"name": "catalog", "type": "string", "required": False, "default": "main"},
                    {"name": "schema", "type": "string", "required": False, "default": "default"},
                ],
            },
            {
                "type": "DOCKER_LOGS",
                "name": "Docker Logs",
                "description": "Fetch logs from Docker containers",
                "capabilities": ["logs", "container_list"],
                "config_fields": [
                    {"name": "host", "type": "string", "required": False, "default": "unix:///var/run/docker.sock"},
                    {"name": "container_ids", "type": "array", "required": False},
                    {"name": "container_names", "type": "array", "required": False},
                ],
            },
            {
                "type": "CSV_FILE",
                "name": "CSV File Upload",
                "description": "Upload and analyze CSV files",
                "capabilities": ["file_upload", "statistics"],
                "config_fields": [],
            },
            {
                "type": "ZIP_FILE",
                "name": "ZIP File Upload",
                "description": "Upload and analyze ZIP files containing CSV data",
                "capabilities": ["file_upload", "multi_file"],
                "config_fields": [],
            },
        ],
        "export_formats": [
            {"format": "csv", "name": "CSV", "description": "Comma-separated values"},
            {"format": "excel", "name": "Excel", "description": "Microsoft Excel spreadsheet (.xlsx)"},
            {"format": "json", "name": "JSON", "description": "JavaScript Object Notation"},
            {"format": "html", "name": "HTML", "description": "HTML table report"},
        ],
    }
