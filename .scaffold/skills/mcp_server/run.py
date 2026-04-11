"""
mcp_server — MCP resource server launcher (skill shim).

Thin wrapper over .scaffold/mcp/server.py so the MCP server shows up
in `terra skill list` and satisfies consistency_scan. The canonical
entry point is still `terra mcp start` (terra.py:1024); this shim
duplicates the start loop so either path works.

Usage:
    python run.py [start|status]
"""
import os
import sys
import time
from pathlib import Path

SCAFFOLD = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SCAFFOLD))


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "start"

    if action == "status":
        print("MCP Server")
        print(f"  Port: {os.environ.get('TERRA_MCP_PORT', '9878')}")
        return 0

    if action == "start":
        from app.scaffold_state import ScaffoldState
        from mcp.resources import ResourceRegistry
        from mcp.server import MCPServer

        state = ScaffoldState()
        state.load_all()
        registry = ResourceRegistry(state)
        server = MCPServer(registry, state)
        server.start()

        info = server.status()
        print(f"MCP Server started on {info['host']}:{info['port']}")
        print("  Press Ctrl+C to stop")
        try:
            while server.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            server.stop()
            print("MCP server stopped")
        return 0

    print(f"unknown action: {action}")
    print("Usage: python run.py [start|status]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
