"""
mcp/resources.py — Resource descriptors and registry.

Maps scaffold state into discoverable MCP resources with URI addressing.
URI scheme: scaffold://category/name

Categories:
  scaffold://routes/{name}      Route entries from .route files
  scaffold://headers/{name}     Module declarations from .h files
  scaffold://skills/{name?}     Skill manifests (or full registry)
  scaffold://tables/{name}      Raw table data
  scaffold://hot_context        Session narrative
  scaffold://queue              Task queue status
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


SCHEME = "scaffold"


@dataclass
class ResourceDescriptor:
    """Metadata for a single MCP resource."""
    uri: str = ""
    name: str = ""
    description: str = ""
    mime_type: str = "application/json"

    def to_dict(self) -> dict:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


@dataclass
class Resource:
    """A resolved resource with content."""
    descriptor: ResourceDescriptor = field(default_factory=ResourceDescriptor)
    content: Any = None           # str or dict
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "uri": self.descriptor.uri,
            "mimeType": self.descriptor.mime_type,
            "text": self.content if isinstance(self.content, str) else None,
            "data": self.content if isinstance(self.content, dict) else None,
        }


def _parse_uri(uri: str) -> tuple[str, str]:
    """Parse scaffold://category/name into (category, name)."""
    prefix = f"{SCHEME}://"
    if not uri.startswith(prefix):
        return ("", "")
    rest = uri[len(prefix):]
    parts = rest.split("/", 1)
    category = parts[0] if parts else ""
    name = parts[1] if len(parts) > 1 else ""
    return (category, name)


class ResourceRegistry:
    """
    Indexes all scaffold resources. Backed by a ScaffoldState instance.

    Usage:
        registry = ResourceRegistry(scaffold_state)
        descriptors = registry.list_resources()
        resource = registry.read_resource("scaffold://routes/structure")
    """

    def __init__(self, scaffold_state):
        self._state = scaffold_state

    def list_resources(self) -> list[ResourceDescriptor]:
        """Enumerate all available resources from current scaffold state."""
        descriptors = []

        # Routes
        for filename in self._state.routes:
            name = filename.replace(".route", "")
            descriptors.append(ResourceDescriptor(
                uri=f"{SCHEME}://routes/{name}",
                name=f"routes/{name}",
                description=f"Route mappings from {filename}",
            ))

        # Headers
        for filename in self._state.headers:
            name = filename.replace(".h", "")
            descriptors.append(ResourceDescriptor(
                uri=f"{SCHEME}://headers/{name}",
                name=f"headers/{name}",
                description=f"Module declarations from {filename}",
            ))

        # Skills (aggregate)
        descriptors.append(ResourceDescriptor(
            uri=f"{SCHEME}://skills",
            name="skills",
            description="All registered skills",
        ))

        # Individual skills
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from skills.runner import list_skills
            for skill_name, manifest in list_skills():
                desc = manifest.get("skill", {}).get("description", "")
                descriptors.append(ResourceDescriptor(
                    uri=f"{SCHEME}://skills/{skill_name}",
                    name=f"skills/{skill_name}",
                    description=desc,
                ))
        except Exception:
            pass

        # Tables
        for filename in self._state.tables:
            name = filename.replace(".table", "")
            descriptors.append(ResourceDescriptor(
                uri=f"{SCHEME}://tables/{name}",
                name=f"tables/{name}",
                description=f"Table data from {filename}",
                mime_type="text/plain",
            ))

        # HOT_CONTEXT
        descriptors.append(ResourceDescriptor(
            uri=f"{SCHEME}://hot_context",
            name="hot_context",
            description="Session narrative (HOT_CONTEXT.md)",
            mime_type="text/markdown",
        ))

        # Queue
        descriptors.append(ResourceDescriptor(
            uri=f"{SCHEME}://queue",
            name="queue",
            description="Task queue status",
        ))

        return descriptors

    def read_resource(self, uri: str) -> Optional[Resource]:
        """Resolve a URI and return resource content. None if not found."""
        category, name = _parse_uri(uri)
        if not category:
            return None

        reader = {
            "routes": self._read_routes,
            "headers": self._read_headers,
            "skills": self._read_skills,
            "tables": self._read_tables,
            "hot_context": self._read_hot_context,
            "queue": self._read_queue,
        }.get(category)

        if reader is None:
            return None
        return reader(name, uri)

    # ── Readers ──────────────────────────────────────────────────────

    def _read_routes(self, name: str, uri: str) -> Optional[Resource]:
        filename = f"{name}.route"
        entries = self._state.routes.get(filename)
        if entries is None:
            return None
        content = [
            {"concept": e.concept, "path": e.path, "description": e.description}
            for e in entries
        ]
        return Resource(
            descriptor=ResourceDescriptor(uri=uri, name=f"routes/{name}",
                                          description=f"Routes from {filename}"),
            content={"routes": content},
        )

    def _read_headers(self, name: str, uri: str) -> Optional[Resource]:
        filename = f"{name}.h"
        data = self._state.headers.get(filename)
        if data is None:
            return None
        modules = []
        for m in data.get("modules", []):
            modules.append({
                "name": m.get("name", ""),
                "path": m.get("path", ""),
                "exports": m.get("exports", []),
                "depends": m.get("depends", []),
                "desc": m.get("desc", ""),
            })
        return Resource(
            descriptor=ResourceDescriptor(uri=uri, name=f"headers/{name}",
                                          description=f"Modules from {filename}"),
            content={"modules": modules},
        )

    def _read_skills(self, name: str, uri: str) -> Optional[Resource]:
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from skills.runner import list_skills
        except Exception:
            return None

        if not name:
            # All skills
            skills = []
            for skill_name, manifest in list_skills():
                info = manifest.get("skill", {})
                triggers = manifest.get("triggers", {})
                skills.append({
                    "name": skill_name,
                    "type": info.get("type", ""),
                    "description": info.get("description", ""),
                    "version": info.get("version", ""),
                    "intents": triggers.get("intents", []),
                    "commands": triggers.get("commands", []),
                })
            return Resource(
                descriptor=ResourceDescriptor(uri=uri, name="skills",
                                              description="All registered skills"),
                content={"skills": skills},
            )
        else:
            # Single skill
            for skill_name, manifest in list_skills():
                if skill_name == name:
                    info = manifest.get("skill", {})
                    triggers = manifest.get("triggers", {})
                    return Resource(
                        descriptor=ResourceDescriptor(
                            uri=uri, name=f"skills/{name}",
                            description=info.get("description", "")),
                        content={
                            "name": name,
                            "type": info.get("type", ""),
                            "description": info.get("description", ""),
                            "version": info.get("version", ""),
                            "entry": info.get("entry", ""),
                            "intents": triggers.get("intents", []),
                            "commands": triggers.get("commands", []),
                        },
                    )
            return None

    def _read_tables(self, name: str, uri: str) -> Optional[Resource]:
        filename = f"{name}.table"
        text = self._state.tables.get(filename)
        if text is None:
            return None
        return Resource(
            descriptor=ResourceDescriptor(uri=uri, name=f"tables/{name}",
                                          description=f"Table from {filename}",
                                          mime_type="text/plain"),
            content=text,
        )

    def _read_hot_context(self, name: str, uri: str) -> Optional[Resource]:
        return Resource(
            descriptor=ResourceDescriptor(uri=uri, name="hot_context",
                                          description="Session narrative",
                                          mime_type="text/markdown"),
            content=self._state.hot_context,
        )

    def _read_queue(self, name: str, uri: str) -> Optional[Resource]:
        return Resource(
            descriptor=ResourceDescriptor(uri=uri, name="queue",
                                          description="Task queue status"),
            content=self._state.queue_status,
        )
