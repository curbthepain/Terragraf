"""Pytest bootstrap for Terragraf.

Appends .scaffold/src/python (if it exists) to sys.path so that optional
test-only deps sourced via `terra deps sync` (onnx, onnxscript, …) are
importable during pytest runs. Uses append, not prepend — system-installed
torch / torchvision must continue to win to avoid C++-extension ABI clashes
documented in Session 18 (DepsPanel).
"""

import sys
from pathlib import Path

_SRC_PY = Path(__file__).parent / "src" / "python"
if _SRC_PY.is_dir() and str(_SRC_PY) not in sys.path:
    sys.path.append(str(_SRC_PY))
