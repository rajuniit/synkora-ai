"""
MCP Server Model

Database model for storing Model Context Protocol (MCP) server configurations.
MCP servers extend agent capabilities by providing additional tools and resources.
"""

from sqlalchemy import JSON, Column, String, Text
from sqlalchemy.orm import relationship

from src.models.base import BaseModel, StatusMixin, TenantMixin


class MCPServer(BaseModel, StatusMixin, TenantMixin):
    """
    MCP Server model for storing server configurations.

    MCP (Model Context Protocol) servers provide additional tools and resources
    that can be used by AI agents to extend their capabilities.

    Attributes:
        name: Human-readable name for the MCP server
        url: Server URL/endpoint
        description: Detailed description of server capabilities
        server_type: Type of MCP server (http, websocket, etc.)
        auth_type: Authentication method (none, api_key, oauth, etc.)
        auth_config: Authentication configuration (encrypted)
        capabilities: JSON object describing server capabilities
        metadata: Additional metadata about the server
        status: Server status (active, inactive, error)
        tenant_id: Tenant identifier for multi-tenancy
    """

    __tablename__ = "mcp_servers"

    name = Column(String(255), nullable=False, index=True, comment="MCP server name")

    url = Column(String(500), nullable=True, comment="MCP server URL/endpoint (required for http transport)")

    description = Column(Text, nullable=True, comment="Server description and capabilities")

    transport_type = Column(String(20), nullable=False, default="http", comment="Transport type: http, stdio")

    command = Column(String(500), nullable=True, comment="Command to run for stdio transport (e.g., 'npx', 'python')")

    args = Column(
        JSON, nullable=True, comment="Command arguments as array (e.g., ['-y', '@modelcontextprotocol/server-github'])"
    )

    env_vars = Column(JSON, nullable=True, comment="Environment variables for stdio process")

    server_type = Column(String(50), nullable=False, default="http", comment="Server type (http, websocket, grpc)")

    auth_type = Column(
        String(50), nullable=False, default="none", comment="Authentication type (none, api_key, oauth, bearer)"
    )

    auth_config = Column(JSON, nullable=True, comment="Authentication configuration (encrypted)")

    headers = Column(JSON, nullable=True, comment="Custom HTTP headers to include in requests")

    capabilities = Column(JSON, nullable=True, comment="Server capabilities and available tools")

    server_metadata = Column(JSON, nullable=True, comment="Additional server metadata")

    # Relationships
    agents = relationship("AgentMCPServer", back_populates="mcp_server", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        """String representation of MCP server."""
        return f"<MCPServer(id={self.id}, name='{self.name}', url='{self.url}')>"

    def to_dict(self, exclude: set[str] | None = None) -> dict:
        """
        Convert to dictionary, excluding sensitive auth data by default.

        Args:
            exclude: Additional fields to exclude

        Returns:
            Dictionary representation of the server
        """
        exclude = exclude or set()
        # Always exclude sensitive auth config unless explicitly requested
        if "auth_config" not in exclude:
            exclude.add("auth_config")

        return super().to_dict(exclude=exclude)

    def to_dict_with_auth(self) -> dict:
        """
        Convert to dictionary including authentication config.
        Use with caution - only for authorized operations.

        Returns:
            Full dictionary including auth config
        """
        return super().to_dict(exclude=set())
