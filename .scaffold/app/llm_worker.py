"""
LLM streaming worker — runs provider.stream() on a daemon thread.

Emits Qt signals as tokens arrive, safely crossing from the worker
thread to the main thread via Qt's auto-connection mechanism.
Same threading pattern as bridge_client.py.
"""

import threading

from PySide6.QtCore import QObject, Signal


class LLMWorker(QObject):
    """
    Runs an LLM provider's stream() call on a daemon thread.

    Usage:
        worker = LLMWorker(provider, context)
        worker.token_received.connect(card.append_token)
        worker.finished.connect(card.on_llm_done)
        worker.error_occurred.connect(card.on_llm_error)
        worker.start()
    """

    token_received = Signal(str)    # one text chunk
    finished = Signal()             # stream completed cleanly
    error_occurred = Signal(str)    # error message string

    def __init__(self, provider, context, parent=None):
        super().__init__(parent)
        self._provider = provider
        self._context = context
        self._thread: threading.Thread | None = None
        self._cancelled = False

    def start(self):
        """Spawn the worker thread."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self):
        """Request cancellation (best-effort)."""
        self._cancelled = True

    def _run(self):
        try:
            for token in self._provider.stream(self._context):
                if self._cancelled:
                    break
                self.token_received.emit(token)
            if not self._cancelled:
                self.finished.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc))
