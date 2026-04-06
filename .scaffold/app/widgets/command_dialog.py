"""CommandDialog — base class for terra command form dialogs.

Subclasses declare a list of FieldSpec entries and implement ``run(values)``.
The base class builds a QFormLayout, captures stdout/stderr from the run,
and shows the result in a read-only output area.

Path normalization: every ``file``/``dir`` field value is rewritten through
``str(Path(v).resolve())`` before ``run()`` is called, so dialogs never have
to worry about Windows/POSIX drift.

Threaded execution: subclasses may set ``_run_async = True`` to dispatch
``run()`` on a QThread. The Run button disables and a Cancel button appears.
TrainDialog uses this; everything else stays synchronous.
"""

from __future__ import annotations

import contextlib
import io
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QCheckBox,
    QPlainTextEdit,
    QPushButton,
    QFileDialog,
    QWidget,
)

from .. import theme


@dataclass
class FieldSpec:
    """Declarative form field."""
    name: str
    label: str
    kind: str = "text"   # text|number|float|choice|checkbox|file|dir|multiline
    default: Any = None
    choices: list[str] = field(default_factory=list)
    placeholder: str = ""
    minimum: float = 0.0
    maximum: float = 1_000_000.0
    step: float = 1.0
    file_filter: str = "All files (*.*)"
    help: str = ""


class _CommandWorker(QThread):
    finished_with_output = Signal(str, bool)
    chunk = Signal(str)

    def __init__(self, fn: Callable[[dict], str], values: dict, parent=None):
        super().__init__(parent)
        self._fn = fn
        self._values = values

    def run(self):
        try:
            out = self._fn(self._values) or ""
            self.finished_with_output.emit(str(out), False)
        except Exception:
            self.finished_with_output.emit(traceback.format_exc(), True)


class CommandDialog(QDialog):
    """Base class — subclasses set TITLE, FIELDS, and override run()."""

    TITLE: str = "Command"
    FIELDS: list[FieldSpec] = []
    _run_async: bool = False
    _run_streaming: bool = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.TITLE)
        self.setMinimumWidth(540)
        self.setMinimumHeight(480)

        self._widgets: dict[str, QWidget] = {}
        self._worker: _CommandWorker | None = None
        # Streaming hook — set per-run by _start_async/_run_sync. Subclasses
        # may call self._emit_chunk(line) from inside run() to push partial
        # output to the dialog as it arrives.
        self._emit_chunk: Callable[[str], None] = lambda _line: None
        self._chunks_received: int = 0
        self._build_ui()

    # ── UI construction ────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(self.TITLE)
        title.setObjectName("section_header")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(form)

        for spec in self.FIELDS:
            row = self._make_field(spec)
            label = QLabel(spec.label)
            if spec.help:
                label.setToolTip(spec.help)
            form.addRow(label, row)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self.cancel_btn)

        self.run_btn = QPushButton("Run")
        self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self._on_run_clicked)
        btn_row.addWidget(self.run_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.close_btn)

        layout.addLayout(btn_row)

        # Output area
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Output will appear here after Run.")
        layout.addWidget(self.output, 1)

    def _make_field(self, spec: FieldSpec) -> QWidget:
        kind = spec.kind
        widget: QWidget

        if kind == "text":
            widget = QLineEdit()
            if spec.default is not None:
                widget.setText(str(spec.default))
            if spec.placeholder:
                widget.setPlaceholderText(spec.placeholder)

        elif kind == "number":
            widget = QSpinBox()
            widget.setRange(int(spec.minimum), int(spec.maximum))
            widget.setSingleStep(int(spec.step))
            if spec.default is not None:
                widget.setValue(int(spec.default))

        elif kind == "float":
            widget = QDoubleSpinBox()
            widget.setRange(spec.minimum, spec.maximum)
            widget.setDecimals(6)
            widget.setSingleStep(spec.step)
            if spec.default is not None:
                widget.setValue(float(spec.default))

        elif kind == "choice":
            widget = QComboBox()
            widget.addItems(spec.choices)
            if spec.default in spec.choices:
                widget.setCurrentText(str(spec.default))

        elif kind == "checkbox":
            widget = QCheckBox()
            widget.setChecked(bool(spec.default))

        elif kind == "multiline":
            widget = QPlainTextEdit()
            widget.setFixedHeight(80)
            if spec.default is not None:
                widget.setPlainText(str(spec.default))

        elif kind in ("file", "dir"):
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            edit = QLineEdit()
            if spec.default is not None:
                edit.setText(str(spec.default))
            if spec.placeholder:
                edit.setPlaceholderText(spec.placeholder)
            browse = QPushButton("…")
            browse.setFixedWidth(36)

            def _pick(_=False, _e=edit, _kind=kind, _filter=spec.file_filter):
                if _kind == "file":
                    p, _ = QFileDialog.getOpenFileName(self, "Select file", "", _filter)
                else:
                    p = QFileDialog.getExistingDirectory(self, "Select directory", "")
                if p:
                    _e.setText(p)
            browse.clicked.connect(_pick)

            row.addWidget(edit, 1)
            row.addWidget(browse)
            container._edit = edit  # for value extraction
            widget = container
        else:
            widget = QLineEdit()

        self._widgets[spec.name] = widget
        return widget

    # ── Value collection ───────────────────────────────────────────

    def _collect_values(self) -> dict:
        values: dict = {}
        for spec in self.FIELDS:
            w = self._widgets.get(spec.name)
            if w is None:
                continue
            kind = spec.kind
            if kind == "text":
                values[spec.name] = w.text()
            elif kind == "number":
                values[spec.name] = w.value()
            elif kind == "float":
                values[spec.name] = w.value()
            elif kind == "choice":
                values[spec.name] = w.currentText()
            elif kind == "checkbox":
                values[spec.name] = w.isChecked()
            elif kind == "multiline":
                values[spec.name] = w.toPlainText()
            elif kind in ("file", "dir"):
                edit = getattr(w, "_edit", None)
                values[spec.name] = edit.text() if edit else ""
        return values

    def _normalize_values(self, values: dict) -> dict:
        """Resolve every file/dir field through Path.resolve(). Idempotent."""
        out = dict(values)
        for spec in self.FIELDS:
            if spec.kind in ("file", "dir"):
                v = out.get(spec.name, "")
                if v:
                    try:
                        out[spec.name] = str(Path(v).resolve())
                    except OSError:
                        pass  # Leave as-is
        return out

    # ── Execution ──────────────────────────────────────────────────

    def _on_run_clicked(self):
        values = self._normalize_values(self._collect_values())
        self.output.clear()
        self._chunks_received = 0

        if self._run_async:
            self._start_async(values)
        else:
            self._run_sync(values)

    def _run_sync(self, values: dict):
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Running...")
        # Sync streaming: chunks append directly to output area.
        if self._run_streaming:
            self._emit_chunk = self._append_chunk_sync
        else:
            self._emit_chunk = lambda _line: None
        try:
            out = self.run(values) or ""
            if self._run_streaming:
                # Streaming run() may also return trailing text
                if out:
                    self.output.appendPlainText(str(out))
            else:
                self.output.setPlainText(str(out))
        except Exception:
            self._show_error(traceback.format_exc())
        finally:
            self._emit_chunk = lambda _line: None
            self.run_btn.setEnabled(True)
            self.run_btn.setText("Run")

    def _append_chunk_sync(self, line: str):
        self._chunks_received += 1
        self.output.appendPlainText(line)

    def _start_async(self, values: dict):
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Running...")
        self.cancel_btn.setVisible(True)
        if self._run_streaming:
            self.output.setPlainText("")
        else:
            self.output.setPlainText("Working...")
        self._worker = _CommandWorker(self.run, values, parent=self)
        # Wire chunk signal: worker emits across the thread boundary; Qt
        # auto-marshals to the GUI thread, where _on_chunk appends.
        self._worker.chunk.connect(self._on_chunk)
        self._worker.finished_with_output.connect(self._on_async_done)
        # The dialog's _emit_chunk goes through the worker signal so calls
        # from inside run() (worker thread) reach the GUI thread safely.
        self._emit_chunk = self._worker.chunk.emit
        self._worker.start()

    def _on_chunk(self, line: str):
        self._chunks_received += 1
        self.output.appendPlainText(line)

    def _on_async_done(self, output: str, was_error: bool):
        if was_error:
            self._show_error(output)
        elif self._run_streaming:
            # Don't clobber streamed lines; only append trailing text if any
            if output and self._chunks_received == 0:
                self.output.setPlainText(output)
            elif output:
                self.output.appendPlainText(output)
        else:
            self.output.setPlainText(output)
        self._emit_chunk = lambda _line: None
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run")
        self.cancel_btn.setVisible(False)
        self._worker = None

    def _on_cancel(self):
        if self._worker is not None:
            self._worker.requestInterruption()
            self.output.appendPlainText("\n[cancel requested]")

    def _show_error(self, text: str):
        self.output.setPlainText(text)
        self.output.setStyleSheet(f"color: {theme.RED};")

    # ── Helpers for subclasses ─────────────────────────────────────

    @staticmethod
    def capture_call(fn: Callable, *args, **kwargs) -> str:
        """Run a function while capturing stdout+stderr; return the text."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            try:
                rv = fn(*args, **kwargs)
            except SystemExit:
                pass
            except Exception:
                buf.write("\n" + traceback.format_exc())
        out = buf.getvalue()
        if not out and 'rv' in locals():
            out = str(rv) if rv is not None else ""
        return out

    @staticmethod
    def run_skill(name: str, args: list[str] | None = None) -> str:
        """Convenience wrapper that calls runner.run_skill_capture and joins output."""
        import sys
        from pathlib import Path as _P
        sys.path.insert(0, str(_P(__file__).resolve().parent.parent.parent))
        from skills.runner import run_skill_capture
        rc, stdout, stderr = run_skill_capture(name, args or [])
        out = stdout
        if stderr:
            out += ("\n" if out else "") + stderr
        if rc != 0:
            out += f"\n[exit code {rc}]"
        return out

    def run_skill_streaming(self, name: str, args: list[str] | None = None) -> str:
        """Stream a skill's stdout line-by-line through self._emit_chunk.

        Companion to run_skill(): subclasses that set _run_streaming = True
        call this from their run() method instead of run_skill(). The trailing
        return value is empty on success and an exit-code marker on failure;
        all real output has already been pushed via _emit_chunk.
        """
        import sys
        from pathlib import Path as _P
        sys.path.insert(0, str(_P(__file__).resolve().parent.parent.parent))
        from skills.runner import run_skill_stream
        rc = run_skill_stream(name, args or [], on_line=self._emit_chunk)
        return f"\n[exit code {rc}]" if rc != 0 else ""

    # ── Override in subclass ───────────────────────────────────────

    def run(self, values: dict) -> str:
        """Execute the command. Return captured output as string."""
        raise NotImplementedError
