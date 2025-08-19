#!/usr/bin/env python3
import asyncio
import os
import sys

# Ensure src/ is on the import path
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from any_mcp.managers.manager import MCPManager  # type: ignore


async def main() -> int:
    print("\n=== MCP Smoke Test ===")
    print("Starting demo calculator MCP server and calling a tool...\n")

    manager = MCPManager()

    # Use current Python interpreter to run the server so imports match this venv
    command = sys.executable
    args = [os.path.join(PROJECT_ROOT, "mcps", "demo_calculator.py")]

    started = await manager.start_mcp(
        name="calculator",
        command=command,
        args=args,
        env=os.environ.copy(),
    )

    if not started:
        print("❌ Failed to start calculator MCP server")
        return 1

    print("✅ Server started\n")

    try:
        tools_by_server = await manager.list_all_tools()
        print("Discovered tools:")
        for server, tools in tools_by_server.items():
            names = [t.name for t in tools]
            print(f"- {server}: {names}")

        def result_text(call_result):
            try:
                # mcp.types.CallToolResult has .content as list of content items
                if call_result and getattr(call_result, "content", None):
                    for item in call_result.content:
                        text = getattr(item, "text", None)
                        if text:
                            return text
                return str(call_result)
            except Exception:
                return str(call_result)

        print("\nCalling tool 'add' with a=15, b=23...")
        result = await manager.call_mcp("calculator", "add", {"a": 15, "b": 23})
        print(f"Result: {result_text(result)}")

        # Also exercise call_any_mcp by name
        print("\nCalling via call_any_mcp 'multiply' with a=6, b=7...")
        result2 = await manager.call_any_mcp("multiply", {"a": 6, "b": 7})
        print(f"Result: {result_text(result2)}")

        print("\n✅ Smoke test completed successfully")
        return 0

    finally:
        await manager.cleanup()
        print("\n🧹 Cleaned up manager and stopped server")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
