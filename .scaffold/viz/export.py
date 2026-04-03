"""
.scaffold/viz/export.py
Figure export utilities — PNG, SVG, raw buffer.

Provides:
  - save_figure      — save matplotlib figure to file (PNG/SVG/PDF)
  - figure_to_buffer — render figure to in-memory bytes buffer
"""

import io


def save_figure(fig, path, dpi=150, transparent=False):
    """
    Save a matplotlib figure to disk.
    Supports: .png, .svg, .pdf, .jpg based on file extension.
    """
    fig.savefig(path, dpi=dpi, transparent=transparent, bbox_inches="tight")


def figure_to_buffer(fig, format="png", dpi=150) -> bytes:
    """
    Render a matplotlib figure to an in-memory bytes buffer.
    Useful for embedding in web responses or passing to PIL.

    format: "png", "svg", "pdf", "raw"
    Returns bytes.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format=format, dpi=dpi, bbox_inches="tight")
    buf.seek(0)
    return buf.read()
