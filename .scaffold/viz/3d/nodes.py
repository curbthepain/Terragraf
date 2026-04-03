"""
.scaffold/viz/3d/nodes.py
3D node graph generator — dependency graphs, data flow, neural net architecture.

Provides:
  - NodeGraph          — build a graph of nodes and edges
  - render_node_graph  — render to matplotlib 3D scatter/line plot
"""

import numpy as np
from typing import Dict, List, Optional, Tuple


class NodeGraph:
    """
    3D node graph for visualizing relationships.
    Nodes have positions, labels, and optional metadata.
    Edges connect nodes with optional weights.
    """

    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self.edges: List[Tuple[str, str, float]] = []

    def add_node(self, name: str, position: Optional[np.ndarray] = None,
                 label: Optional[str] = None, group: int = 0):
        """Add a node. If no position given, it will be computed by layout."""
        self.nodes[name] = {
            "position": position,
            "label": label or name,
            "group": group,
        }

    def add_edge(self, source: str, target: str, weight: float = 1.0):
        """Add a directed edge between two nodes."""
        self.edges.append((source, target, weight))

    def layout_spring(self, iterations=50, k=1.0):
        """
        Spring layout — force-directed positioning in 3D.
        Nodes repel each other, edges act as springs.
        """
        node_names = list(self.nodes.keys())
        n = len(node_names)
        positions = np.random.randn(n, 3)

        # Assign existing positions
        for i, name in enumerate(node_names):
            if self.nodes[name]["position"] is not None:
                positions[i] = self.nodes[name]["position"]

        idx = {name: i for i, name in enumerate(node_names)}

        for _ in range(iterations):
            forces = np.zeros((n, 3))

            # Repulsion between all pairs
            for i in range(n):
                for j in range(i + 1, n):
                    diff = positions[i] - positions[j]
                    dist = max(np.linalg.norm(diff), 0.01)
                    force = k * diff / (dist ** 2)
                    forces[i] += force
                    forces[j] -= force

            # Attraction along edges
            for src, tgt, weight in self.edges:
                if src in idx and tgt in idx:
                    i, j = idx[src], idx[tgt]
                    diff = positions[j] - positions[i]
                    dist = np.linalg.norm(diff)
                    force = weight * diff * dist / k
                    forces[i] += force
                    forces[j] -= force

            positions += forces * 0.01

        # Write back
        for i, name in enumerate(node_names):
            self.nodes[name]["position"] = positions[i]

    def layout_networkx(self):
        """Use NetworkX for 3D spring layout (requires networkx)."""
        import networkx as nx

        G = nx.DiGraph()
        for name in self.nodes:
            G.add_node(name)
        for src, tgt, weight in self.edges:
            G.add_edge(src, tgt, weight=weight)

        pos_2d = nx.spring_layout(G, dim=3)
        for name, pos in pos_2d.items():
            self.nodes[name]["position"] = np.array(pos)

    def get_positions(self) -> np.ndarray:
        """Get all node positions as (n, 3) array."""
        return np.array([self.nodes[n]["position"] for n in self.nodes])


def render_node_graph(graph: NodeGraph, figsize=(10, 8), title="Node Graph"):
    """
    Render a NodeGraph as a matplotlib 3D plot.
    Returns a matplotlib Figure.
    """
    import matplotlib.pyplot as plt

    if any(graph.nodes[n]["position"] is None for n in graph.nodes):
        graph.layout_spring()

    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection="3d")

    # Draw edges
    node_names = list(graph.nodes.keys())
    idx = {name: i for i, name in enumerate(node_names)}
    positions = graph.get_positions()

    for src, tgt, weight in graph.edges:
        if src in idx and tgt in idx:
            p1 = positions[idx[src]]
            p2 = positions[idx[tgt]]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]],
                    "gray", alpha=0.5, linewidth=0.5 + weight)

    # Draw nodes colored by group
    groups = [graph.nodes[n]["group"] for n in node_names]
    scatter = ax.scatter(
        positions[:, 0], positions[:, 1], positions[:, 2],
        c=groups, cmap="tab10", s=100, edgecolors="black", linewidth=0.5
    )

    # Labels
    for i, name in enumerate(node_names):
        label = graph.nodes[name]["label"]
        ax.text(positions[i, 0], positions[i, 1], positions[i, 2],
                f"  {label}", fontsize=7)

    ax.set_title(title)
    fig.tight_layout()
    return fig
