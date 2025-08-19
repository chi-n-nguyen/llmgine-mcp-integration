"""
any-mcp: Universal MCP (Model Context Protocol) Client System

This package provides a comprehensive system for integrating with MCP servers,
including client management, tool adapters, and integration bridges.
"""

__version__ = "0.1.0"
__author__ = "any-mcp Team"

from any_mcp.managers.manager import MCPManager
from any_mcp.core.client import MCPClient

__all__ = [
    "MCPManager",
    "MCPClient",
]

