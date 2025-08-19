"""
MCP Manager Implementation

This module provides the main MCPManager class for managing multiple MCP clients
and providing a unified interface for tool execution.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from mcp.types import CallToolResult, Tool

from any_mcp.core.client import MCPClient

logger = logging.getLogger(__name__)


class MCPManager:
    """
    Manager for multiple MCP clients and unified tool execution.
    
    This manager provides:
    - Multiple MCP server management
    - Unified tool discovery and execution
    - Load balancing and failover
    - Resource cleanup and lifecycle management
    """
    
    def __init__(self):
        self.active_clients: Dict[str, MCPClient] = {}
        self._server_configs: Dict[str, Dict[str, Any]] = {}
        
    async def start_mcp(
        self, 
        name: str, 
        command: str, 
        args: List[str], 
        env: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Start an MCP server and create a client connection.
        
        Args:
            name: Unique name for the MCP server
            command: Command to run the server
            args: Arguments for the server command
            env: Environment variables for the server
            
        Returns:
            True if server started successfully
        """
        if name in self.active_clients:
            logger.warning(f"MCP server {name} is already running")
            return True
        
        try:
            # Store server configuration
            self._server_configs[name] = {
                "command": command,
                "args": args,
                "env": env or {}
            }
            
            # Create and connect client
            client = MCPClient(name)
            success = await client.connect(command, args, env)
            
            if success:
                self.active_clients[name] = client
                logger.info(f"Started MCP server: {name}")
                return True
            else:
                logger.error(f"Failed to start MCP server: {name}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting MCP server {name}: {e}")
            return False
    
    async def stop_mcp(self, name: str) -> bool:
        """
        Stop an MCP server and disconnect client.
        
        Args:
            name: Name of the MCP server to stop
            
        Returns:
            True if server stopped successfully
        """
        if name not in self.active_clients:
            logger.warning(f"MCP server {name} is not running")
            return True
        
        try:
            client = self.active_clients[name]
            await client.disconnect()
            
            del self.active_clients[name]
            if name in self._server_configs:
                del self._server_configs[name]
            
            logger.info(f"Stopped MCP server: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping MCP server {name}: {e}")
            return False
    
    async def list_all_tools(self) -> Dict[str, List[Tool]]:
        """
        List all tools from all active MCP servers.
        
        Returns:
            Dictionary mapping server names to their tools
        """
        all_tools = {}
        
        for server_name, client in self.active_clients.items():
            try:
                tools = await client.list_tools()
                all_tools[server_name] = tools
                logger.debug(f"Listed {len(tools)} tools from {server_name}")
            except Exception as e:
                logger.error(f"Failed to list tools from {server_name}: {e}")
                all_tools[server_name] = []
        
        return all_tools
    
    async def call_mcp(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Optional[CallToolResult]:
        """
        Call a tool on a specific MCP server.
        
        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            Tool execution result
        """
        if server_name not in self.active_clients:
            raise ValueError(f"MCP server {server_name} is not active")
        
        client = self.active_clients[server_name]
        return await client.call_tool(tool_name, arguments)
    
    async def find_tool(self, tool_name: str) -> Optional[tuple[str, Tool]]:
        """
        Find a tool by name across all active servers.
        
        Args:
            tool_name: Name of the tool to find
            
        Returns:
            Tuple of (server_name, tool) if found, None otherwise
        """
        for server_name, client in self.active_clients.items():
            try:
                tool = await client.get_tool(tool_name)
                if tool:
                    return (server_name, tool)
            except Exception as e:
                logger.error(f"Error searching for tool {tool_name} in {server_name}: {e}")
        
        return None
    
    async def call_any_mcp(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[CallToolResult]:
        """
        Call a tool on any server that has it.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            Tool execution result
        """
        result = await self.find_tool(tool_name)
        if not result:
            raise ValueError(f"Tool {tool_name} not found in any active MCP server")
        
        server_name, tool = result
        return await self.call_mcp(server_name, tool_name, arguments)
    
    def get_active_servers(self) -> List[str]:
        """Get list of active server names."""
        return list(self.active_clients.keys())
    
    def is_server_active(self, name: str) -> bool:
        """Check if a server is active."""
        return name in self.active_clients and self.active_clients[name].is_connected()
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all active servers.
        
        Returns:
            Dictionary mapping server names to their health status
        """
        health_status = {}
        
        for server_name, client in self.active_clients.items():
            try:
                # Try to list tools as a health check
                await client.list_tools()
                health_status[server_name] = True
            except Exception as e:
                logger.warning(f"Health check failed for {server_name}: {e}")
                health_status[server_name] = False
        
        return health_status
    
    async def restart_server(self, name: str) -> bool:
        """
        Restart an MCP server.
        
        Args:
            name: Name of the server to restart
            
        Returns:
            True if restart was successful
        """
        if name not in self._server_configs:
            logger.error(f"No configuration found for server {name}")
            return False
        
        config = self._server_configs[name]
        
        # Stop the server
        await self.stop_mcp(name)
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Start the server again
        return await self.start_mcp(
            name,
            config["command"],
            config["args"],
            config["env"]
        )
    
    async def cleanup(self):
        """Clean up all resources and disconnect from all servers."""
        logger.info("Cleaning up MCP manager...")
        
        # Disconnect from all servers
        for server_name in list(self.active_clients.keys()):
            await self.stop_mcp(server_name)
        
        self.active_clients.clear()
        self._server_configs.clear()
        
        logger.info("MCP manager cleanup completed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
    
    def __repr__(self):
        active_count = len(self.active_clients)
        server_names = list(self.active_clients.keys())
        return f"MCPManager(active_servers={active_count}, servers={server_names})"

