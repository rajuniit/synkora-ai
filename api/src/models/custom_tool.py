"""
Custom Tool Model

Database model for storing custom tools with OpenAPI specifications.
"""

from enum import StrEnum

from sqlalchemy import Boolean, Column, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class AuthType(StrEnum):
    """Authentication types for custom tools."""

    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"
    CUSTOM = "custom"


class CustomTool(BaseModel):
    """
    CustomTool model for storing custom tools with OpenAPI specifications.

    Allows users to import tools from OpenAPI schemas and make them available
    to agents for execution.

    Attributes:
        tenant_id: Foreign key to tenants table
        name: Unique name of the custom tool
        description: Description of what the tool does
        openapi_schema: Complete OpenAPI specification (JSON)
        server_url: Base URL for API requests
        auth_type: Type of authentication (none, basic, bearer, api_key, custom)
        auth_config: Encrypted authentication configuration
        enabled: Whether the tool is currently enabled
        icon: Optional icon URL or emoji
        tags: Optional tags for categorization
    """

    __tablename__ = "custom_tools"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_custom_tool_name"),)

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID this tool belongs to",
    )

    name = Column(String(100), nullable=False, index=True, comment="Unique name of the custom tool")

    description = Column(Text, nullable=True, comment="Description of what the tool does")

    openapi_schema = Column(JSONB, nullable=False, comment="Complete OpenAPI specification")

    server_url = Column(String(500), nullable=False, comment="Base URL for API requests")

    auth_type = Column(String(20), nullable=False, default=AuthType.NONE.value, comment="Type of authentication")

    auth_config = Column(JSONB, nullable=False, default=dict, comment="Encrypted authentication configuration")

    enabled = Column(Boolean, nullable=False, default=True, index=True, comment="Whether the tool is enabled")

    icon = Column(String(200), nullable=True, comment="Optional icon URL or emoji")

    tags = Column(JSONB, nullable=True, default=list, comment="Optional tags for categorization")

    # Relationships
    tenant = relationship("Tenant", back_populates="custom_tools")

    def __repr__(self) -> str:
        """String representation of custom tool."""
        return f"<CustomTool(id={self.id}, name='{self.name}', tenant_id={self.tenant_id})>"

    def to_dict(self, include_auth: bool = False) -> dict:
        """
        Convert to dictionary.

        Args:
            include_auth: Whether to include auth_config (may contain sensitive data)

        Returns:
            Dictionary representation
        """
        data = super().to_dict()

        # Optionally exclude auth config for security
        if not include_auth:
            data.pop("auth_config", None)

        return data

    def get_operations(self) -> list[dict]:
        """
        Extract available operations from OpenAPI schema.

        Returns:
            List of operations with their details
        """
        operations = []

        if not self.openapi_schema or "paths" not in self.openapi_schema:
            return operations

        for path, path_item in self.openapi_schema.get("paths", {}).items():
            for method, operation in path_item.items():
                if method.lower() in ["get", "post", "put", "patch", "delete"]:
                    operations.append(
                        {
                            "path": path,
                            "method": method.upper(),
                            "operation_id": operation.get("operationId", f"{method}_{path}"),
                            "summary": operation.get("summary", ""),
                            "description": operation.get("description", ""),
                            "parameters": operation.get("parameters", []),
                            "request_body": operation.get("requestBody", {}),
                            "responses": operation.get("responses", {}),
                        }
                    )

        return operations
