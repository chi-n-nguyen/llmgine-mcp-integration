"""
Tool Adapter for llmgine Integration

This module provides conversion between MCP tools and llmgine tools,
enabling seamless tool registration and execution across both systems.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List

from mcp.types import Tool as MCPTool, CallToolResult

# any-mcp imports
from any_mcp.managers.manager import MCPManager

logger = logging.getLogger(__name__)


class LLMgineToolAdapter:
    """
    Adapter for converting between MCP tools and llmgine tools.
    
    This adapter handles:
    - Converting MCP tool schemas to llmgine-compatible formats
    - Converting MCP tool results to appropriate formats
    - Maintaining compatibility between both tool systems
    """
    
    def __init__(self, mcp_manager: MCPManager):
        self.mcp_manager = mcp_manager
        
    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools from MCP servers in llmgine-compatible format.
        
        Returns:
            List of tool information dictionaries
        """
        tools = []
        
        try:
            all_server_tools = await self.mcp_manager.list_all_tools()
            
            for server_name, server_tools in all_server_tools.items():
                for tool in server_tools:
                    tool_info = {
                        "mcp_name": server_name,
                        "tool_name": tool.name,
                        "description": tool.description or f"Tool {tool.name} from {server_name}",
                        "input_schema": tool.inputSchema,
                        "available": True
                    }
                    tools.append(tool_info)
                    
        except Exception as e:
            logger.error(f"Failed to list available tools: {e}")
        
        return tools
    
    def convert_mcp_tool_to_openai_schema(self, mcp_tool: MCPTool, server_name: str) -> Dict[str, Any]:
        """
        Convert an MCP tool to OpenAI function calling schema.
        
        Args:
            mcp_tool: The MCP tool to convert
            server_name: Name of the MCP server
            
        Returns:
            OpenAI-compatible tool schema
        """
        return {
            "type": "function",
            "function": {
                "name": f"{server_name}_{mcp_tool.name}",
                "description": mcp_tool.description or f"Tool {mcp_tool.name} from {server_name}",
                "parameters": mcp_tool.inputSchema or {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    
    async def get_all_openai_schemas(self) -> List[Dict[str, Any]]:
        """
        Get all MCP tools as OpenAI-compatible schemas.
        
        Returns:
            List of OpenAI-compatible tool schemas
        """
        schemas = []
        
        try:
            all_server_tools = await self.mcp_manager.list_all_tools()
            
            for server_name, server_tools in all_server_tools.items():
                for tool in server_tools:
                    schema = self.convert_mcp_tool_to_openai_schema(tool, server_name)
                    schemas.append(schema)
                    
        except Exception as e:
            logger.error(f"Failed to get OpenAI schemas: {e}")
        
        return schemas
    
    def parse_tool_name(self, full_tool_name: str) -> tuple[str, str]:
        """
        Parse a full tool name into server name and tool name.
        
        Args:
            full_tool_name: Full tool name (e.g., "calculator_add")
            
        Returns:
            Tuple of (server_name, tool_name)
        """
        if "_" in full_tool_name:
            parts = full_tool_name.split("_", 1)
            return parts[0], parts[1]
        else:
            # If no underscore, assume it's just the tool name and try to find it
            return "", full_tool_name
    
    async def execute_tool(
        self, 
        full_tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool through the MCP system.
        
        Args:
            full_tool_name: Full tool name (e.g., "calculator_add")
            arguments: Tool arguments
            
        Returns:
            Execution result dictionary
        """
        try:
            server_name, tool_name = self.parse_tool_name(full_tool_name)
            
            if server_name:
                # Execute on specific server
                result = await self.mcp_manager.call_mcp(server_name, tool_name, arguments)
            else:
                # Try to find and execute on any server
                result = await self.mcp_manager.call_any_mcp(tool_name, arguments)
            
            return self._format_tool_result(result, server_name, tool_name)
            
        except Exception as e:
            logger.error(f"Failed to execute tool {full_tool_name}: {e}")
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }
    
    def _format_tool_result(self, result: CallToolResult, server_name: str, tool_name: str) -> Dict[str, Any]:
        """
        Format MCP tool result for llmgine consumption.
        
        Args:
            result: MCP tool result
            server_name: Name of the MCP server
            tool_name: Name of the tool
            
        Returns:
            Formatted result dictionary
        """
        try:
            if result and result.content:
                # Extract content from result
                content_list = []
                for item in result.content:
                    if hasattr(item, 'text'):
                        content_list.append(item.text)
                    else:
                        content_list.append(str(item))
                
                formatted_result = "\n".join(content_list) if content_list else "No result"
                
                return {
                    "success": not (result.isError if hasattr(result, 'isError') else False),
                    "result": formatted_result,
                    "server_name": server_name,
                    "tool_name": tool_name
                }
            else:
                return {
                    "success": True,
                    "result": "Tool executed successfully (no content returned)",
                    "server_name": server_name,
                    "tool_name": tool_name
                }
                
        except Exception as e:
            logger.error(f"Failed to format tool result: {e}")
            return {
                "success": False,
                "result": None,
                "error": f"Failed to format result: {e}",
                "server_name": server_name,
                "tool_name": tool_name
            }
    
    async def get_tool_info(self, server_name: str, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific tool.
        
        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool
            
        Returns:
            Tool information dictionary if found
        """
        try:
            if server_name not in self.mcp_manager.active_clients:
                return None
            
            client = self.mcp_manager.active_clients[server_name]
            tool = await client.get_tool(tool_name)
            
            if tool:
                return {
                    "mcp_name": server_name,
                    "tool_name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                    "available": True
                }
            
        except Exception as e:
            logger.error(f"Failed to get tool info for {server_name}:{tool_name}: {e}")
        
        return None

