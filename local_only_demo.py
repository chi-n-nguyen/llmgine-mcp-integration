#!/usr/bin/env python3
"""
Local Tools Only Demo - Show How Fast and Reliable Local Tools Are

This demonstrates the existing ToolManager working perfectly with local Python functions.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from llmgine.llm.tools.tool_manager import ToolManager
from llmgine.llm.tools.toolCall import ToolCall


# Local tools - these work perfectly!
def fast_math(x: int, y: int) -> int:
    """Fast local math operation."""
    return x * y + 42


def string_processor(text: str, operation: str = "uppercase") -> str:
    """Process strings locally."""
    if operation == "uppercase":
        return text.upper()
    elif operation == "lowercase":
        return text.lower()
    elif operation == "reverse":
        return text[::-1]
    else:
        return f"Unknown operation: {operation}"


def data_validator(data: dict) -> str:
    """Validate data locally."""
    if "name" not in data:
        return "❌ Missing 'name' field"
    if "age" not in data:
        return "❌ Missing 'age' field"
    if data["age"] < 0:
        return "❌ Age cannot be negative"
    return f"✅ Valid data: {data['name']} is {data['age']} years old"


async def main():
    print("🔵 LOCAL TOOLS DEMO - Fast & Reliable!")
    print("=" * 50)
    print("This shows the existing ToolManager working perfectly!")
    print()
    
    # Create tool manager
    tool_manager = ToolManager()
    
    # Register local tools
    print("📝 REGISTERING LOCAL TOOLS...")
    tool_manager.register_tool(fast_math)
    tool_manager.register_tool(string_processor)
    tool_manager.register_tool(data_validator)
    print(f"✅ Registered {len(tool_manager.tools)} local tools")
    print()
    
    # Show what we have
    print("🛠️  AVAILABLE LOCAL TOOLS:")
    for i, tool_name in enumerate(tool_manager.tools.keys(), 1):
        print(f"  {i}. {tool_name}")
    
    print()
    print("🧪 TESTING LOCAL TOOLS:")
    print()
    
    # Test fast math
    result = await tool_manager.execute_tool_call(
        ToolCall(id="1", name="fast_math", arguments={"x": 10, "y": 5})
    )
    print(f"🔢 fast_math(10, 5) = {result}")
    
    # Test string processing
    result = await tool_manager.execute_tool_call(
        ToolCall(id="2", name="string_processor", arguments={"text": "Hello World", "operation": "uppercase"})
    )
    print(f"📝 string_processor('Hello World', 'uppercase') = {result}")
    
    result = await tool_manager.execute_tool_call(
        ToolCall(id="3", name="string_processor", arguments={"text": "Hello World", "operation": "reverse"})
    )
    print(f"📝 string_processor('Hello World', 'reverse') = {result}")
    
    # Test data validation
    result = await tool_manager.execute_tool_call(
        ToolCall(id="4", name="data_validator", arguments={"name": "Alice", "age": 25})
    )
    print(f"✅ data_validator({{'name': 'Alice', 'age': 25}}) = {result}")
    
    result = await tool_manager.execute_tool_call(
        ToolCall(id="5", name="data_validator", arguments={"name": "Bob"})
    )
    print(f"✅ data_validator({{'name': 'Bob'}}) = {result}")
    
    # Test multiple tool calls
    print("\n🔄 TESTING MULTIPLE TOOL CALLS:")
    tool_calls = [
        ToolCall(id="6", name="fast_math", arguments={"x": 2, "y": 3}),
        ToolCall(id="7", name="string_processor", arguments={"text": "test", "operation": "uppercase"}),
        ToolCall(id="8", name="data_validator", arguments={"name": "Test", "age": 30}),
    ]
    
    results = await tool_manager.execute_tool_calls(tool_calls)
    for i, (call, result) in enumerate(zip(tool_calls, results)):
        print(f"  {call.name}: {result}")
    
    print()
    print("🎯 WHY LOCAL TOOLS ARE GREAT:")
    print("  ✅ Instant execution (no subprocess overhead)")
    print("  ✅ Reliable (no network/stdio failures)")
    print("  ✅ Easy debugging (stack traces point to your code)")
    print("  ✅ Type safety (Python type hints work)")
    print("  ✅ Fast iteration (edit function, test immediately)")
    print()
    print("💡 This is why we keep the existing ToolManager!")
    print("   MCP tools are just an ADDITION, not a replacement.")


if __name__ == "__main__":
    asyncio.run(main())
