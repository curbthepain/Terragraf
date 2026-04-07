"""
.scaffold/mcp — MCP resource server.

Exposes scaffold data (routes, headers, skills, tables, HOT_CONTEXT, queue)
as discoverable resources over TCP. External tools (Claude Code, Cursor)
connect as clients.

Protocol: JSON-RPC 2.0 over length-prefixed TCP (port 9878).
Wire format reused from instances/transport.py.
"""

from .resources import ResourceDescriptor, Resource, ResourceRegistry
from .tools import SkillToolAdapter
from .server import MCPServer

__all__ = [
    "ResourceDescriptor",
    "Resource",
    "ResourceRegistry",
    "SkillToolAdapter",
    "MCPServer",
]
