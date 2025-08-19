"""
Simplified tool management for litellm.
Handles tool registration, schema generation, and execution.
Now supports both local tools and MCP tools.
"""

import asyncio
import inspect
import json
import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from llmgine.llm import AsyncOrSyncToolFunction
from llmgine.llm.tools.toolCall import ToolCall

if TYPE_CHECKING:
    from llmgine.llm.context.memory import SimpleChatHistory

logger = logging.getLogger(__name__)


class ToolManager:
    """Simplified tool manager for litellm. Now supports both local and MCP tools."""
    
    def __init__(self, chat_history: Optional["SimpleChatHistory"] = None):
        """Initialize tool manager."""
        self.chat_history = chat_history
        self.tools: Dict[str, Callable] = {}
        self.tool_schemas: List[Dict[str, Any]] = []
        self.mcp_clients: Dict[str, Any] = {}  # Store MCP clients by name
    
    def register_tool(self, func: AsyncOrSyncToolFunction) -> None:
        """Register a function as a tool."""
        name = func.__name__
        self.tools[name] = func
        
        # Generate OpenAI-format schema
        schema = self._generate_tool_schema(func)
        self.tool_schemas.append(schema)
    
    def _generate_tool_schema(self, func: Callable) -> Dict[str, Any]:
        """Generate OpenAI-format tool schema from function."""
        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or f"Function {func.__name__}"
        
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            # Determine type
            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                annotation = param.annotation
                # Handle basic types
                if annotation == int:
                    param_type = "integer"
                elif annotation == float:
                    param_type = "number"
                elif annotation == bool:
                    param_type = "boolean"
                elif annotation in (list, List):
                    param_type = "array"
                elif annotation in (dict, Dict):
                    param_type = "object"
                # Handle Optional and generic types
                elif hasattr(annotation, '__origin__'):
                    origin = annotation.__origin__
                    if origin == list or origin is list:
                        param_type = "array"
                    elif origin == dict or origin is dict:
                        param_type = "object"
                    # Handle Union types (Optional is Union[X, None])
                    else:
                        # Try to import Union from typing to check properly
                        from typing import Union, get_origin, get_args
                        if get_origin(annotation) is Union:
                            # Get the first non-None type from Union args
                            args = get_args(annotation)
                            for arg in args:
                                if arg is not type(None):
                                    if arg == list or get_origin(arg) == list:
                                        param_type = "array"
                                        break
                                    elif arg == dict or get_origin(arg) == dict:
                                        param_type = "object"
                                        break
                                    elif arg == int:
                                        param_type = "integer"
                                        break
                                    elif arg == float:
                                        param_type = "number"
                                        break
                                    elif arg == bool:
                                        param_type = "boolean"
                                        break
                                    elif arg == str:
                                        param_type = "string"
                                        break
            
            # Extract description from docstring if available
            param_desc = f"{param_name} parameter"
            # Simple docstring parsing for parameter descriptions
            if doc and f":param {param_name}:" in doc:
                start = doc.find(f":param {param_name}:") + len(f":param {param_name}:")
                end = doc.find("\n", start)
                if end != -1:
                    param_desc = doc[start:end].strip()
            
            properties[param_name] = {
                "type": param_type,
                "description": param_desc
            }
            
            # Check if required (no default value)
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
        
        return {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": doc.split('\n')[0] if '\n' in doc else doc,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
    
    def parse_tools_to_list(self) -> List[Dict[str, Any]]:
        """Get all tools in OpenAI format for litellm."""
        return self.tool_schemas if self.tool_schemas else None
    
    async def execute_tool_calls(self, tool_calls: List[ToolCall]) -> List[Any]:
        """Execute multiple tool calls."""
        results = []
        for tool_call in tool_calls:
            result = await self.execute_tool_call(tool_call)
            results.append(result)
        return results
    
    async def execute_tool_call(self, tool_call: ToolCall) -> Any:
        """Execute a single tool call."""
        if tool_call.name not in self.tools:
            return f"Error: Tool '{tool_call.name}' not found"
        
        func = self.tools[tool_call.name]
        
        try:
            # Parse arguments
            if isinstance(tool_call.arguments, str):
                if tool_call.arguments.strip() == "":
                    args = {}
                else:
                    args = json.loads(tool_call.arguments)
            else:
                args = tool_call.arguments
            
            # Handle empty/None arguments
            if not args:
                args = {}
            
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(**args)
            else:
                result = func(**args)
            
            return result
        except Exception as e:
            return f"Error executing {tool_call.name}: {str(e)}"
    
    def chat_history_to_messages(self) -> List[Dict[str, Any]]:
        """Get messages from chat history for litellm."""
        if self.chat_history:
            return self.chat_history.get_messages()
        return []
    
    async def register_mcp_server(self, server_name: str, command: str, args: List[str], 
                                 env: Optional[Dict[str, str]] = None) -> bool:
        """Register an MCP server and all its tools.
        
        Args:
            server_name: Name for the MCP server
            command: Command to run the server
            args: Arguments for the server
            env: Environment variables
            
        Returns:
            True if server started and tools registered successfully
        """
        try:
            # Import here to avoid circular imports
            from llmgine.llm.tools.mcp_client import SimpleMCPClient
            from llmgine.llm.tools.mcp_adapter import MCPToolAdapter
            
            # Create and start MCP client
            client = SimpleMCPClient(server_name)
            success = await client.start(command, args, env)
            
            if not success:
                logger.error(f"Failed to start MCP server: {server_name}")
                return False
            
            # Store client
            self.mcp_clients[server_name] = client
            
            # Create adapter
            adapter = MCPToolAdapter(client)
            
            # Register all tools from the MCP server
            tools = client.get_tools()
            for mcp_tool in tools:
                # Convert to OpenAI schema
                schema = adapter.convert_mcp_tool_to_schema(mcp_tool)
                self.tool_schemas.append(schema)
                
                # Create wrapper function
                wrapper_func = adapter.create_mcp_tool_function(mcp_tool.name)
                self.tools[mcp_tool.name] = wrapper_func
                
                logger.info(f"Registered MCP tool: {mcp_tool.name}")
            
            logger.info(f"Successfully registered MCP server {server_name} with {len(tools)} tools")
            return True
            
        except Exception as e:
            logger.error(f"Error registering MCP server {server_name}: {e}")
            return False
    
    async def cleanup_mcp_servers(self):
        """Cleanup all MCP servers."""
        for server_name, client in self.mcp_clients.items():
            try:
                await client.stop()
                logger.info(f"Stopped MCP server: {server_name}")
            except Exception as e:
                logger.error(f"Error stopping MCP server {server_name}: {e}")
        
        self.mcp_clients.clear()

    # Backwards compatibility - these can be removed if not needed
    async def register_tool_async(self, func: AsyncOrSyncToolFunction) -> None:
        """Register tool async - for backwards compatibility."""
        self.register_tool(func)