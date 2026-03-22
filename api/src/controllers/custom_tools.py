"""
Custom Tools API Controller

Handles API endpoints for managing custom tools (OpenAPI-based tools).
"""

import json
import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_tenant_id
from src.models.custom_tool import CustomTool
from src.services.agents.security import encrypt_value
from src.services.custom_tools import OpenAPIParser, ToolExecutor
from src.services.security.url_validator import validate_url_for_openapi_import

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/custom-tools", tags=["custom-tools"])


# Request/Response Models
class CreateCustomToolRequest(BaseModel):
    """Request model for creating a custom tool."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    openapi_schema: dict[str, Any] = Field(..., description="OpenAPI 3.0/3.1 schema")
    server_url: str | None = Field(None, description="Override server URL from schema")
    auth_type: str = Field(
        default="none",
        description="Authentication type: none, basic, bearer, custom",
    )
    auth_config: dict[str, Any] = Field(default_factory=dict, description="Authentication configuration")
    icon: str | None = None
    tags: list[str] | None = None
    enabled: bool = Field(default=True)


class UpdateCustomToolRequest(BaseModel):
    """Request model for updating a custom tool."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    openapi_schema: dict[str, Any] | None = None
    server_url: str | None = None
    auth_type: str | None = None
    auth_config: dict[str, Any] | None = None
    icon: str | None = None
    tags: list[str] | None = None
    enabled: bool | None = None


class ImportFromURLRequest(BaseModel):
    """Request model for importing tool from URL."""

    url: str = Field(..., description="URL to OpenAPI schema")
    name: str | None = None
    description: str | None = None
    auth_type: str = Field(default="none")
    auth_config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = Field(default=True)


class TestToolRequest(BaseModel):
    """Request model for testing a tool."""

    operation_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class ExecuteToolRequest(BaseModel):
    """Request model for executing a tool operation."""

    operation_id: str = Field(..., description="Operation ID to execute")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Operation parameters")


class CustomToolResponse(BaseModel):
    """Response model for custom tool."""

    id: str
    tenant_id: str
    name: str
    description: str | None
    server_url: str
    auth_type: str
    enabled: bool
    icon: str | None
    tags: list[str]
    operation_count: int
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class CustomToolDetailResponse(CustomToolResponse):
    """Detailed response model for custom tool."""

    openapi_schema: dict[str, Any]
    schema_info: dict[str, Any]
    operations: list[dict[str, Any]]


class OperationResponse(BaseModel):
    """Response model for tool operation."""

    operation_id: str
    method: str
    path: str
    summary: str
    description: str
    parameters: list[dict[str, Any]]
    request_body: dict[str, Any] | None
    tags: list[str]


# Endpoints
@router.post("", response_model=CustomToolResponse, status_code=201)
async def create_custom_tool(
    request: CreateCustomToolRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new custom tool."""
    try:
        # Validate OpenAPI schema by parsing it
        try:
            parser = OpenAPIParser(request.openapi_schema, request.server_url)
            schema_info = parser.get_schema_info()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid OpenAPI schema: {str(e)}")

        # Check for duplicate name
        result = await db.execute(
            select(CustomTool).filter(CustomTool.tenant_id == tenant_id, CustomTool.name == request.name)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Custom tool with name '{request.name}' already exists",
            )

        # Encrypt auth config
        encrypted_auth_config = {}
        for key, value in request.auth_config.items():
            if isinstance(value, str) and value:
                encrypted_auth_config[key] = encrypt_value(value)
            else:
                encrypted_auth_config[key] = value

        # Create custom tool
        tool = CustomTool(
            tenant_id=tenant_id,
            name=request.name,
            description=request.description,
            openapi_schema=request.openapi_schema,
            server_url=request.server_url or schema_info["server_url"],
            auth_type=request.auth_type,
            auth_config=encrypted_auth_config,
            enabled=request.enabled,
            icon=request.icon,
            tags=request.tags or [],
        )

        db.add(tool)
        await db.commit()
        await db.refresh(tool)

        logger.info(f"Created custom tool: {tool.name} (ID: {tool.id})")

        return CustomToolResponse(
            id=str(tool.id),
            tenant_id=str(tool.tenant_id),
            name=tool.name,
            description=tool.description,
            server_url=tool.server_url,
            auth_type=tool.auth_type,
            enabled=tool.enabled,
            icon=tool.icon,
            tags=tool.tags or [],
            operation_count=schema_info["operation_count"],
            created_at=tool.created_at.isoformat(),
            updated_at=tool.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating custom tool: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import-url", response_model=CustomToolResponse, status_code=201)
async def import_from_url(
    request: ImportFromURLRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Import a custom tool from a URL pointing to an OpenAPI schema."""
    try:
        # SECURITY: Validate URL to prevent SSRF attacks
        is_valid, error_message = validate_url_for_openapi_import(request.url)
        if not is_valid:
            logger.warning(f"SSRF protection blocked URL: {request.url} - {error_message}")
            raise HTTPException(status_code=400, detail=f"URL validation failed: {error_message}")

        # Fetch OpenAPI schema from URL
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(request.url)
            response.raise_for_status()

            # Try to parse as JSON
            try:
                openapi_schema = response.json()
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="URL does not return valid JSON")

        # Validate it's an OpenAPI schema
        if "openapi" not in openapi_schema and "swagger" not in openapi_schema:
            raise HTTPException(
                status_code=400,
                detail="URL does not point to a valid OpenAPI/Swagger schema",
            )

        # Parse schema to get info
        parser = OpenAPIParser(openapi_schema)
        schema_info = parser.get_schema_info()

        # Use provided name or extract from schema
        tool_name = request.name or schema_info["title"]
        tool_description = request.description or schema_info["description"]

        # Check for duplicate name
        result = await db.execute(
            select(CustomTool).filter(CustomTool.tenant_id == tenant_id, CustomTool.name == tool_name)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Custom tool with name '{tool_name}' already exists",
            )

        # Encrypt auth config
        encrypted_auth_config = {}
        for key, value in request.auth_config.items():
            if isinstance(value, str) and value:
                encrypted_auth_config[key] = encrypt_value(value)
            else:
                encrypted_auth_config[key] = value

        # Create custom tool
        tool = CustomTool(
            tenant_id=tenant_id,
            name=tool_name,
            description=tool_description,
            openapi_schema=openapi_schema,
            server_url=schema_info["server_url"],
            auth_type=request.auth_type,
            auth_config=encrypted_auth_config,
            enabled=request.enabled,
            tags=[],
        )

        db.add(tool)
        await db.commit()
        await db.refresh(tool)

        logger.info(f"Imported custom tool from URL: {tool.name} (ID: {tool.id})")

        return CustomToolResponse(
            id=str(tool.id),
            tenant_id=str(tool.tenant_id),
            name=tool.name,
            description=tool.description,
            server_url=tool.server_url,
            auth_type=tool.auth_type,
            enabled=tool.enabled,
            icon=tool.icon,
            tags=tool.tags or [],
            operation_count=schema_info["operation_count"],
            created_at=tool.created_at.isoformat(),
            updated_at=tool.updated_at.isoformat(),
        )

    except httpx.HTTPError as e:
        logger.error(f"Error fetching OpenAPI schema from URL: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch schema from URL: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing custom tool: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[CustomToolResponse])
async def list_custom_tools(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    enabled_only: bool = Query(False),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """List all custom tools for the current tenant."""
    try:
        query = select(CustomTool).filter(CustomTool.tenant_id == tenant_id)

        if enabled_only:
            query = query.filter(CustomTool.enabled)

        result = await db.execute(query.offset(skip).limit(limit))
        tools = result.scalars().all()

        return [
            CustomToolResponse(
                id=str(tool.id),
                tenant_id=str(tool.tenant_id),
                name=tool.name,
                description=tool.description,
                server_url=tool.server_url,
                auth_type=tool.auth_type,
                enabled=tool.enabled,
                icon=tool.icon,
                tags=tool.tags or [],
                operation_count=len(OpenAPIParser(tool.openapi_schema).get_available_operations()),
                created_at=tool.created_at.isoformat(),
                updated_at=tool.updated_at.isoformat(),
            )
            for tool in tools
        ]

    except Exception as e:
        logger.error(f"Error listing custom tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tool_id}", response_model=CustomToolDetailResponse)
async def get_custom_tool(
    tool_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Get a specific custom tool with full details."""
    try:
        result = await db.execute(
            select(CustomTool).filter(CustomTool.id == tool_id, CustomTool.tenant_id == tenant_id)
        )
        tool = result.scalar_one_or_none()

        if not tool:
            raise HTTPException(status_code=404, detail="Custom tool not found")

        # Parse schema
        parser = OpenAPIParser(tool.openapi_schema, tool.server_url)
        schema_info = parser.get_schema_info()
        operations = parser.get_available_operations()

        return CustomToolDetailResponse(
            id=str(tool.id),
            tenant_id=str(tool.tenant_id),
            name=tool.name,
            description=tool.description,
            server_url=tool.server_url,
            auth_type=tool.auth_type,
            enabled=tool.enabled,
            icon=tool.icon,
            tags=tool.tags or [],
            operation_count=len(operations),
            created_at=tool.created_at.isoformat(),
            updated_at=tool.updated_at.isoformat(),
            openapi_schema=tool.openapi_schema,
            schema_info=schema_info,
            operations=operations,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting custom tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{tool_id}", response_model=CustomToolResponse)
async def update_custom_tool(
    tool_id: UUID,
    request: UpdateCustomToolRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Update a custom tool."""
    try:
        result = await db.execute(
            select(CustomTool).filter(CustomTool.id == tool_id, CustomTool.tenant_id == tenant_id)
        )
        tool = result.scalar_one_or_none()

        if not tool:
            raise HTTPException(status_code=404, detail="Custom tool not found")

        # Update fields
        if request.name is not None:
            # Check for duplicate name
            result = await db.execute(
                select(CustomTool).filter(
                    CustomTool.tenant_id == tenant_id,
                    CustomTool.name == request.name,
                    CustomTool.id != tool_id,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Custom tool with name '{request.name}' already exists",
                )
            tool.name = request.name

        if request.description is not None:
            tool.description = request.description

        if request.openapi_schema is not None:
            # Validate new schema
            try:
                parser = OpenAPIParser(request.openapi_schema, request.server_url)
                parser.get_schema_info()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid OpenAPI schema: {str(e)}")
            tool.openapi_schema = request.openapi_schema

        if request.server_url is not None:
            tool.server_url = request.server_url

        if request.auth_type is not None:
            tool.auth_type = request.auth_type

        if request.auth_config is not None:
            # Encrypt auth config
            encrypted_auth_config = {}
            for key, value in request.auth_config.items():
                if isinstance(value, str) and value:
                    encrypted_auth_config[key] = encrypt_value(value)
                else:
                    encrypted_auth_config[key] = value
            tool.auth_config = encrypted_auth_config

        if request.icon is not None:
            tool.icon = request.icon

        if request.tags is not None:
            tool.tags = request.tags

        if request.enabled is not None:
            tool.enabled = request.enabled

        await db.commit()
        await db.refresh(tool)

        logger.info(f"Updated custom tool: {tool.name} (ID: {tool.id})")

        # Get operation count
        parser = OpenAPIParser(tool.openapi_schema, tool.server_url)
        operation_count = len(parser.get_available_operations())

        return CustomToolResponse(
            id=str(tool.id),
            tenant_id=str(tool.tenant_id),
            name=tool.name,
            description=tool.description,
            server_url=tool.server_url,
            auth_type=tool.auth_type,
            enabled=tool.enabled,
            icon=tool.icon,
            tags=tool.tags or [],
            operation_count=operation_count,
            created_at=tool.created_at.isoformat(),
            updated_at=tool.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating custom tool: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{tool_id}", status_code=204)
async def delete_custom_tool(
    tool_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete a custom tool."""
    try:
        result = await db.execute(
            select(CustomTool).filter(CustomTool.id == tool_id, CustomTool.tenant_id == tenant_id)
        )
        tool = result.scalar_one_or_none()

        if not tool:
            raise HTTPException(status_code=404, detail="Custom tool not found")

        await db.delete(tool)
        await db.commit()

        logger.info(f"Deleted custom tool: {tool.name} (ID: {tool.id})")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting custom tool: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tool_id}/operations", response_model=list[OperationResponse])
async def list_tool_operations(
    tool_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """List all available operations for a custom tool."""
    try:
        result = await db.execute(
            select(CustomTool).filter(CustomTool.id == tool_id, CustomTool.tenant_id == tenant_id)
        )
        tool = result.scalar_one_or_none()

        if not tool:
            raise HTTPException(status_code=404, detail="Custom tool not found")

        parser = OpenAPIParser(tool.openapi_schema, tool.server_url)
        operations = parser.get_available_operations()

        return [
            OperationResponse(
                operation_id=op["operation_id"],
                method=op["method"],
                path=op["path"],
                summary=op["summary"],
                description=op["description"],
                parameters=op["parameters"],
                request_body=op.get("request_body"),
                tags=op.get("tags", []),
            )
            for op in operations
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tool operations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{tool_id}/test")
async def test_tool(
    tool_id: UUID,
    request: TestToolRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Test a custom tool by making a test connection or executing a test operation."""
    try:
        result = await db.execute(
            select(CustomTool).filter(CustomTool.id == tool_id, CustomTool.tenant_id == tenant_id)
        )
        tool = result.scalar_one_or_none()

        if not tool:
            raise HTTPException(status_code=404, detail="Custom tool not found")

        # Create parser and executor
        parser = OpenAPIParser(tool.openapi_schema, tool.server_url)
        executor = ToolExecutor(parser=parser, auth_type=tool.auth_type, auth_config=tool.auth_config)

        # If operation_id is provided, execute that operation
        if request.operation_id:
            result = await executor.execute(request.operation_id, request.parameters)
            return {
                "success": True,
                "message": "Operation executed successfully",
                "operation_id": request.operation_id,
                "result": result,
            }
        else:
            # Otherwise, just test the connection
            result = await executor.test_connection()
            return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing custom tool: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.post("/{tool_id}/execute")
async def execute_tool_operation(
    tool_id: UUID,
    request: ExecuteToolRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Execute a specific operation of a custom tool."""
    try:
        result = await db.execute(
            select(CustomTool).filter(CustomTool.id == tool_id, CustomTool.tenant_id == tenant_id)
        )
        tool = result.scalar_one_or_none()

        if not tool:
            raise HTTPException(status_code=404, detail="Custom tool not found")

        if not tool.enabled:
            raise HTTPException(status_code=400, detail="Custom tool is disabled")

        # Create parser and executor
        parser = OpenAPIParser(tool.openapi_schema, tool.server_url)
        executor = ToolExecutor(parser=parser, auth_type=tool.auth_type, auth_config=tool.auth_config)

        # Execute the operation
        result = await executor.execute(request.operation_id, request.parameters)

        return {
            "success": True,
            "operation_id": request.operation_id,
            "result": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing tool operation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
