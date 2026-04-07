"""
render_3d — 3D visualization pipeline.

Renders surfaces, volumes, node graphs, and point clouds using viz.3d modules.

Usage:
    python run.py surface <expr> [--range -5:5] [--output out.png]
    python run.py volume <data_file> [--output out.png]
    python run.py nodes <graph_json> [--layout force] [--output out.png]
    python run.py points <csv_file> [--output out.png]
    python run.py demo                  # Render all demo scenes
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

SCAFFOLD = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SCAFFOLD))

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def cmd_surface(args):
    from viz._3d.mesh import generate_surface, render_surface
    from viz.export import save_figure

    expr = args.expression
    rng = args.range.split(":") if args.range else ["-5", "5"]
    lo, hi = float(rng[0]), float(rng[1])

    print(f"  {CYAN}Surface{RESET} f(x,y) = {expr}")
    print(f"  range: [{lo}, {hi}]")

    x = np.linspace(lo, hi, 100)
    y = np.linspace(lo, hi, 100)
    X, Y = np.meshgrid(x, y)
    Z = eval(expr, {"x": X, "y": Y, "np": np, "sin": np.sin, "cos": np.cos,
                     "exp": np.exp, "sqrt": np.sqrt, "abs": np.abs})

    fig = render_surface(X, Y, Z)
    if args.output:
        save_figure(fig, args.output)
        print(f"  {GREEN}Saved{RESET} {args.output}")
    else:
        import matplotlib.pyplot as plt
        plt.show()
    return 0


def cmd_volume(args):
    from viz._3d.volume import VolumeRenderer, render_slices
    from viz.export import save_figure

    data_path = Path(args.data_file)
    if data_path.suffix == ".npy":
        volume = np.load(str(data_path))
    else:
        print(f"  {RED}Unsupported format: {data_path.suffix}. Use .npy{RESET}")
        return 1

    print(f"  {CYAN}Volume{RESET} {volume.shape}")
    fig = render_slices(volume)
    if args.output:
        save_figure(fig, args.output)
        print(f"  {GREEN}Saved{RESET} {args.output}")
    else:
        import matplotlib.pyplot as plt
        plt.show()
    return 0


def cmd_nodes(args):
    from viz._3d.nodes import NodeGraph, render_node_graph
    from viz.export import save_figure

    graph_path = Path(args.graph_file)
    data = json.loads(graph_path.read_text())

    graph = NodeGraph()
    for node in data.get("nodes", []):
        graph.add_node(node["id"], label=node.get("label", ""),
                       group=node.get("group", 0))
    for edge in data.get("edges", []):
        graph.add_edge(edge["from"], edge["to"],
                       weight=edge.get("weight", 1.0))

    graph.layout_spring()
    print(f"  {CYAN}Node Graph{RESET} {len(data.get('nodes', []))} nodes, {len(data.get('edges', []))} edges")

    fig = render_node_graph(graph)
    if args.output:
        save_figure(fig, args.output)
        print(f"  {GREEN}Saved{RESET} {args.output}")
    else:
        import matplotlib.pyplot as plt
        plt.show()
    return 0


def cmd_points(args):
    from viz._3d.mesh import render_point_cloud, generate_point_cloud
    from viz.export import save_figure

    data = np.loadtxt(args.csv_file, delimiter=",")
    if data.shape[1] < 3:
        print(f"  {RED}Need at least 3 columns (x, y, z){RESET}")
        return 1

    cloud = generate_point_cloud(data[:, :3])
    print(f"  {CYAN}Point Cloud{RESET} {data.shape[0]} points")

    fig = render_point_cloud(cloud)
    if args.output:
        save_figure(fig, args.output)
        print(f"  {GREEN}Saved{RESET} {args.output}")
    else:
        import matplotlib.pyplot as plt
        plt.show()
    return 0


def cmd_demo():
    """Render demo scenes to show capabilities."""
    from viz._3d.mesh import generate_surface, render_surface
    from viz.export import save_figure

    print(f"{BOLD}3D Render Demo{RESET}")
    print()

    # Surface demo
    x = np.linspace(-3, 3, 80)
    y = np.linspace(-3, 3, 80)
    X, Y = np.meshgrid(x, y)
    Z = np.sin(np.sqrt(X**2 + Y**2))
    fig = render_surface(X, Y, Z)
    save_figure(fig, "demo_surface.png")
    print(f"  {GREEN}Saved{RESET} demo_surface.png (ripple surface)")

    return 0


def cli():
    parser = argparse.ArgumentParser(description="3D visualization pipeline")
    sub = parser.add_subparsers(dest="command")

    s = sub.add_parser("surface", help="Render mathematical surface")
    s.add_argument("expression", help="Math expression in x,y (e.g., 'np.sin(x)*np.cos(y)')")
    s.add_argument("--range", default="-5:5", help="Range as lo:hi")
    s.add_argument("--output", "-o", help="Output PNG path")

    v = sub.add_parser("volume", help="Render volume slices")
    v.add_argument("data_file", help="Volume data (.npy)")
    v.add_argument("--output", "-o", help="Output PNG path")

    n = sub.add_parser("nodes", help="Render node graph")
    n.add_argument("graph_file", help="Graph JSON file")
    n.add_argument("--layout", default="force", help="Layout algorithm")
    n.add_argument("--output", "-o", help="Output PNG path")

    p = sub.add_parser("points", help="Render point cloud")
    p.add_argument("csv_file", help="Points CSV (x,y,z columns)")
    p.add_argument("--output", "-o", help="Output PNG path")

    sub.add_parser("demo", help="Render demo scenes")

    args = parser.parse_args()

    commands = {
        "surface": cmd_surface,
        "volume": cmd_volume,
        "nodes": cmd_nodes,
        "points": cmd_points,
        "demo": cmd_demo,
    }

    if args.command in commands:
        return commands[args.command](args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(cli())
