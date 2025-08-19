"""
MCP Client Implementation

This module provides a robust MCP client for connecting to and interacting
with MCP (Model Context Protocol) servers.
"""

import asyncio
import json
import logging
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, Tool

logger = logging.getLogger(__name__)


class MCPClient:
    """
    A robust MCP client for connecting to MCP servers.
    
    This client handles:
    - Server connection and lifecycle management
    - Tool discovery and execution
    - Error handling and recovery
    - Resource cleanup
    """
    
    def __init__(self, server_name: str):
        self.server_name = server_name
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._connected = False
        self._tools_cache: Optional[List[Tool]] = None
        
    async def connect(self, command: str, args: List[str], env: Optional[Dict[str, str]] = None) -> bool:
        """
        Connect to an MCP server.
        
        Args:
            command: Command to run the server
            args: Arguments for the server command
            env: Environment variables for the server
            
        Returns:
            True if connection was successful
        """
        try:
            logger.info(f"Connecting to MCP server {self.server_name}...")
            
            # Create server parameters
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env or {}
            )
            
            # Connect to server
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, write = stdio_transport
            
            # Create session
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )
            
            # Initialize session
            await self.session.initialize()
            
            self._connected = True
            logger.info(f"Successfully connected to MCP server {self.server_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.server_name}: {e}")
            self._connected = False
            return False
    
    async def list_tools(self) -> List[Tool]:
        """
        List all available tools from the MCP server.
        
        Returns:
            List of available tools
        """
        if not self._connected or not self.session:
            raise RuntimeError(f"Not connected to MCP server {self.server_name}")
        
        try:
            # Use cached tools if available
            if self._tools_cache is not None:
                return self._tools_cache
            
            response = await self.session.list_tools()
            self._tools_cache = response.tools
            
            logger.debug(f"Listed {len(self._tools_cache)} tools from {self.server_name}")
            return self._tools_cache
            
        except Exception as e:
            logger.error(f"Failed to list tools from {self.server_name}: {e}")
            raise
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Optional[CallToolResult]:
        """
        Call a tool on the MCP server.
        
        Args:
            name: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            Tool execution result
        """
        if not self._connected or not self.session:
            raise RuntimeError(f"Not connected to MCP server {self.server_name}")
        
        try:
            logger.debug(f"Calling tool {name} on {self.server_name} with args: {arguments}")
            
            result = await self.session.call_tool(name, arguments)
            
            logger.debug(f"Tool {name} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Failed to call tool {name} on {self.server_name}: {e}")
            raise
    
    async def get_tool(self, name: str) -> Optional[Tool]:
        """
        Get information about a specific tool.
        
        Args:
            name: Name of the tool
            
        Returns:
            Tool information if found
        """
        tools = await self.list_tools()
        for tool in tools:
            if tool.name == name:
                return tool
        return None
    
    def is_connected(self) -> bool:
        """Check if client is connected to server."""
        return self._connected
    
    def clear_tools_cache(self):
        """Clear the tools cache to force refresh on next list_tools call."""
        self._tools_cache = None
    
    async def disconnect(self):
        """Disconnect from the MCP server and clean up resources."""
        try:
            if self._connected:
                logger.info(f"Disconnecting from MCP server {self.server_name}")
                
                await self.exit_stack.aclose()
                
                self._connected = False
                self.session = None
                self._tools_cache = None
                
                logger.info(f"Disconnected from MCP server {self.server_name}")
                
        except Exception as e:
            logger.error(f"Error disconnecting from {self.server_name}: {e}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    def __repr__(self):
        status = "connected" if self._connected else "disconnected"
        return f"MCPClient(server_name='{self.server_name}', status='{status}')"

