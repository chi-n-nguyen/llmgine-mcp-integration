"""
MCP Tool Manager for LLMgine

This module replaces LLMgine's traditional tool manager with any-mcp's MCP tool manager.
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

from any_mcp.managers.manager import MCPManager


@dataclass
class MCPTool:
	"""Represents an MCP tool that can be called by LLMgine"""
	name: str
	description: str
	input_schema: Dict[str, Any]
	server_name: str


class MCPToolManager:
	"""
	Manages MCP tools for LLMgine, replacing the traditional tool manager.
	"""
	
	def __init__(self):
		self.mcp_manager: Optional[MCPManager] = None
		self.tools: Dict[str, MCPTool] = {}
		self._initialized = False
	
	async def initialize(self):
		"""Initialize the MCP manager and discover available tools"""
		if self._initialized:
			return
			
		try:
			self.mcp_manager = MCPManager()
			await self.mcp_manager.start()
			await self._discover_tools()
			self._initialized = True
			
		except Exception as e:
			raise RuntimeError(f"Failed to initialize MCP Tool Manager: {e}")
	
	async def _discover_tools(self):
		"""Discover all available tools from MCP servers"""
		if not self.mcp_manager:
			return
			
		mcp_servers = await self.mcp_manager.list_mcps()
		
		for server_name, server_info in mcp_servers.items():
			if server_info.get('status') == 'running':
				try:
					tools = await self.mcp_manager.list_mcp_tools(server_name)
					
					for tool_name, tool_info in tools.items():
						mcp_tool = MCPTool(
							name=tool_name,
							description=tool_info.get('description', ''),
							input_schema=tool_info.get('inputSchema', {}),
							server_name=server_name
						)
						
						llmgine_tool_name = f"{server_name}.{tool_name}"
						self.tools[llmgine_tool_name] = mcp_tool
						
				except Exception as e:
					print(f"Warning: Could not discover tools from {server_name}: {e}")
	
	async def get_tool(self, tool_name: str) -> Optional[MCPTool]:
		"""Get a tool by name"""
		if not self._initialized:
			await self.initialize()
		return self.tools.get(tool_name)
	
	async def list_tools(self) -> List[MCPTool]:
		"""List all available tools"""
		if not self._initialized:
			await self.initialize()
		return list(self.tools.values())
	
	async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
		"""Call an MCP tool with the given arguments"""
		tool = await self.get_tool(tool_name)
		if not tool:
			raise ValueError(f"Tool '{tool_name}' not found")
		
		try:
			result = await self.mcp_manager.call_mcp(
				tool.server_name,
				tool.name,
				arguments
			)
			return result
			
		except Exception as e:
			raise RuntimeError(f"Failed to call tool '{tool_name}': {e}")
	
	async def shutdown(self):
		"""Shutdown the MCP manager"""
		if self.mcp_manager:
			await self.mcp_manager.stop()
			self._initialized = False


# LLMgine compatibility layer - this replaces the existing tool manager
class LLMgineMCPToolManager:
	"""
	Compatibility layer that makes MCPToolManager work with LLMgine's existing
	tool system architecture.
	"""
	
	def __init__(self):
		self.mcp_manager = MCPToolManager()
	
	async def register_tool(self, tool_func: Callable) -> str:
		"""
		Compatibility method - in MCP mode, tools are discovered, not registered.
		"""
		tool_name = tool_func.__name__
		print(f"Warning: Tool registration not supported in MCP mode. Tool '{tool_name}' will not be available.")
		return tool_name
	
	async def get_available_tools(self) -> List[Dict[str, Any]]:
		"""Get list of available tools in LLMgine-compatible format"""
		tools = await self.mcp_manager.list_tools()
		
		llmgine_tools = []
		for tool in tools:
			llmgine_tools.append({
				"name": tool.name,
				"description": tool.description,
				"parameters": tool.input_schema,
				"type": "mcp"
			})
		
		return llmgine_tools
	
	async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
		"""Execute a tool call"""
		return await self.mcp_manager.call_tool(tool_name, arguments)
	
	async def initialize(self):
		"""Initialize the MCP tool manager"""
		await self.mcp_manager.initialize()
	
	async def shutdown(self):
		"""Shutdown the MCP tool manager"""
		await self.mcp_manager.shutdown()
