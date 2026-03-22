"""
MCP Service Package

Provides MCP client functionality for connecting to and communicating with
Model Context Protocol (MCP) servers.
"""

from .mcp_client import (
    MCPAuthenticationError,
    MCPClient,
    MCPClientError,
    MCPClientManager,
    MCPConnectionError,
    MCPToolExecutionError,
    mcp_client_manager,
)

__all__ = [
    "MCPClient",
    "MCPClientManager",
    "MCPClientError",
    "MCPConnectionError",
    "MCPAuthenticationError",
    "MCPToolExecutionError",
    "mcp_client_manager",
]
