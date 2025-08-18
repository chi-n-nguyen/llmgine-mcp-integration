# MCP Integration for LLMgine

## Overview

This document describes the integration of the Model Context Protocol (MCP) system with LLMgine. The integration provides enhanced tool management capabilities while maintaining backward compatibility with existing LLMgine applications.

## Architecture

The MCP integration consists of several key components:

```
┌─────────────────────────────────────────────────────────────────┐
│                        LLMgine Engine                           │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐  │
│  │ ToolChatEngine  │    │ MessageBus      │    │ UI/CLI      │  │
│  │                 │    │                 │    │             │  │
│  │ - Chat Logic    │    │ - Commands      │    │ - Interface │  │
│  │ - Tool Calls    │    │ - Events        │    │ - Results   │  │
│  └─────────┬───────┘    └─────────┬───────┘    └─────────────┘  │
└───────────┬┼─────────────────────┼┼─────────────────────────────┘
            ││                     ││
            ▼▼                     ▼▼
┌─────────────────────────────────────────────────────────────────┐
│                   Enhanced Tool Manager                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐  │
│  │   Local Tools   │    │  MCP Integration │    │ Tool Adapter│  │
│  │                 │    │                 │    │             │  │
│  │ - Functions     │    │ - Server Mgmt   │    │ - Schema    │  │
│  │ - Schemas       │    │ - Tool Discovery│    │ - Execution │  │
│  └─────────────────┘    └─────────┬───────┘    └─────────────┘  │
└───────────────────────────────────┬┼─────────────────────────────┘
                                    ││
                                    ▼▼
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Ecosystem                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐  │
│  │   Calculator    │    │     Weather     │    │   Custom    │  │
│  │                 │    │                 │    │             │  │
│  │ - Math Ops      │    │ - Current       │    │ - Domain    │  │
│  │ - Formulas      │    │ - Forecast      │    │ - Specific  │  │
│  └─────────────────┘    └─────────────────┘    └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Enhanced Tool Manager

The `EnhancedToolManager` extends the original LLMgine `ToolManager` with MCP capabilities:

- **Backward Compatibility**: Maintains the same interface as the original ToolManager
- **Local Tools**: Continues to support direct function registration
- **MCP Tools**: Adds support for external MCP servers
- **Unified Interface**: Provides seamless execution of both local and MCP tools

### 2. MCP Manager

The `MCPManager` handles multiple MCP server connections:

- **Server Management**: Start, stop, and monitor MCP servers
- **Tool Discovery**: Automatically discover available tools from servers
- **Load Balancing**: Distribute tool calls across available servers
- **Health Monitoring**: Check server health and handle failures

### 3. Tool Adapter

The `LLMgineToolAdapter` bridges MCP and LLMgine formats:

- **Schema Conversion**: Convert MCP tool schemas to OpenAI format
- **Result Processing**: Format MCP results for LLMgine consumption
- **Error Handling**: Provide consistent error reporting

## Usage

### Basic Setup

```python
from llmgine.llm.tools.enhanced_tool_manager import EnhancedToolManager
from llmgine.llm.context.memory import SimpleChatHistory

# Create enhanced tool manager
chat_history = SimpleChatHistory()
tool_manager = EnhancedToolManager(chat_history)

# Initialize MCP system
await tool_manager.initialize_mcp()

# Register local tools (same as before)
def get_weather(city: str) -> str:
    return f"Weather in {city}: Sunny, 72°F"

tool_manager.register_tool(get_weather)

# Add MCP servers
await tool_manager.add_mcp_server(
    name="calculator",
    command="python",
    args=["mcps/demo_calculator.py"],
    env={}
)
```

### Using with Enhanced Engine

```python
from programs.engines.mcp_enhanced_tool_chat_engine import MCPEnhancedToolChatEngine

# Create engine with MCP support
engine = MCPEnhancedToolChatEngine(
    model="gpt-4o-mini",
    enable_mcp=True
)

# Initialize
await engine.initialize()

# Use normally - MCP tools are automatically available
result = await engine.handle_command(
    MCPToolChatEngineCommand(prompt="Calculate 15 * 23")
)
```

### Factory Function

```python
from llmgine.llm.tools.enhanced_tool_manager import (
    create_enhanced_tool_manager_with_servers,
    MCPServerConfig,
    get_default_mcp_servers
)

# Create with default servers
servers = get_default_mcp_servers()

# Add custom server
servers.append(MCPServerConfig(
    name="weather",
    command="python",
    args=["weather_server.py"],
    env={"API_KEY": "your_key"}
))

# Create manager
tool_manager = await create_enhanced_tool_manager_with_servers(
    chat_history=chat_history,
    mcp_servers=servers
)
```

## MCP Server Development

### Creating an MCP Server

Here's an example of a simple MCP server:

```python
#!/usr/bin/env python3
"""
Example MCP Server for LLMgine Integration
"""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult

# Create server
app = Server("example-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="example_tool",
            description="An example tool",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Message to process"}
                },
                "required": ["message"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    """Handle tool calls."""
    if name == "example_tool":
        message = arguments.get("message", "")
        result = f"Processed: {message}"
        return CallToolResult(
            content=[TextContent(type="text", text=result)]
        )
    
    return CallToolResult(
        content=[TextContent(type="text", text=f"Unknown tool: {name}")],
        isError=True
    )

async def main():
    """Run the server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

### Server Configuration

Configure servers using `MCPServerConfig`:

```python
from llmgine.llm.tools.enhanced_tool_manager import MCPServerConfig

config = MCPServerConfig(
    name="my_server",           # Unique server name
    command="python",           # Command to run server
    args=["my_server.py"],      # Server script arguments
    env={"API_KEY": "secret"}   # Environment variables
)
```

## Migration from Original ToolManager

The enhanced tool manager is designed to be a drop-in replacement:

### Before (Original ToolManager)

```python
from llmgine.llm.tools.tool_manager import ToolManager

tool_manager = ToolManager(chat_history)
tool_manager.register_tool(my_function)

# Execute tools
result = await tool_manager.execute_tool_call(tool_call)
```

### After (Enhanced ToolManager)

```python
from llmgine.llm.tools.enhanced_tool_manager import EnhancedToolManager

tool_manager = EnhancedToolManager(chat_history)
await tool_manager.initialize_mcp()  # Only new requirement

tool_manager.register_tool(my_function)  # Same as before

# Add MCP capabilities
await tool_manager.add_mcp_server("calculator", "python", ["calc.py"])

# Execute tools (same interface)
result = await tool_manager.execute_tool_call(tool_call)
```

## Tool Execution Flow

1. **Tool Call Received**: Engine receives tool call from LLM
2. **Tool Resolution**: Enhanced ToolManager determines if tool is local or MCP
3. **Local Execution**: If local, execute directly (same as original)
4. **MCP Execution**: If MCP, route through MCP manager to appropriate server
5. **Result Processing**: Format result consistently regardless of source
6. **Response**: Return formatted result to engine

## Monitoring and Debugging

### Tool Information

```python
# Get all available tools
tools_info = await tool_manager.list_all_tools()

print(f"Local tools: {tools_info['local_tools']}")
print(f"MCP tools: {len(tools_info['mcp_tools'])}")
print(f"MCP servers: {tools_info['mcp_servers']}")
```

### Server Health

```python
# Check server health
health_status = await tool_manager.get_mcp_server_status()

for server_name, is_healthy in health_status.items():
    status = "✅ Healthy" if is_healthy else "❌ Unhealthy"
    print(f"{server_name}: {status}")
```

### Tool Type Detection

```python
# Check tool type
if tool_manager.is_local_tool("my_function"):
    print("This is a local tool")

if tool_manager.is_mcp_tool("calculator_add"):
    print("This is an MCP tool")
```

## Error Handling

The integration provides robust error handling:

- **Connection Failures**: Graceful handling of MCP server disconnections
- **Tool Errors**: Consistent error formatting for both local and MCP tools
- **Timeout Handling**: Configurable timeouts for MCP operations
- **Fallback Mechanisms**: Continue operation even if some servers are unavailable

## Performance Considerations

- **Connection Pooling**: MCP connections are reused across tool calls
- **Lazy Loading**: MCP servers are only started when needed
- **Caching**: Tool schemas and discovery results are cached
- **Async Operations**: All operations are fully asynchronous

## Testing

Run the integration tests:

```bash
# Run all MCP integration tests
pytest tests/integration/test_mcp_integration.py -v

# Run specific test class
pytest tests/integration/test_mcp_integration.py::TestEnhancedToolManager -v
```

## Examples

See the following files for complete examples:

- `programs/engines/mcp_enhanced_tool_chat_engine.py` - Enhanced chat engine with MCP
- `mcps/demo_calculator.py` - Example MCP server
- `tests/integration/test_mcp_integration.py` - Integration tests

## Troubleshooting

### Common Issues

1. **MCP Server Won't Start**
   - Check that the server script exists and is executable
   - Verify Python environment and dependencies
   - Check server logs for error messages

2. **Tools Not Discovered**
   - Ensure server implements `list_tools()` correctly
   - Check that tools are returned in proper MCP format
   - Verify server connection is established

3. **Tool Execution Fails**
   - Check tool argument format matches schema
   - Verify server implements `call_tool()` correctly
   - Review error messages in tool results

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('any_mcp').setLevel(logging.DEBUG)
logging.getLogger('llmgine.llm.tools.enhanced_tool_manager').setLevel(logging.DEBUG)
```

## Contributing

When adding new MCP servers or extending the integration:

1. Follow the MCP specification for server implementation
2. Add comprehensive tests for new functionality
3. Update documentation with examples
4. Ensure backward compatibility with existing code

## Future Enhancements

Planned improvements include:

- **Server Discovery**: Automatic discovery of available MCP servers
- **Load Balancing**: Intelligent distribution of tool calls
- **Caching**: Advanced caching of tool results
- **Monitoring**: Enhanced monitoring and metrics collection
- **Configuration**: YAML/JSON configuration file support
