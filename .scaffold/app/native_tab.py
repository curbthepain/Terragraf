"""
Native tab — chat panel with QueryEngine integration.

Users type queries like "analyze signal" or "fft" and the engine
resolves them through routes, headers, and skills. Results are
displayed as styled message cards.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .widgets.context_panel import ContextPanel
from .widgets.message_card import QueryCard, ResponseCard, LLMResponseCard, NoProviderCard
from query.engine import QueryEngine
from llm.factory import make_provider
from llm.base import LLMContext


class NativeTab(QWidget):
    """
    Chat-style panel for structured query dispatch.

    Layout:
        [Scrollable message area] | [Context panel]
        [Input bar + Send button                   ]
    """

    query_submitted = Signal(str)

    def __init__(self, session, scaffold_state, parent=None):
        super().__init__(parent)
        self.session = session
        self._engine = QueryEngine(scaffold_state)
        self._llm_provider = make_provider()
        self._active_worker = None

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Main area: messages + context panel ──────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Message scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: {theme.BG_PRIMARY}; }}"
        )

        self._messages_widget = QWidget()
        self._messages_layout = QVBoxLayout(self._messages_widget)
        self._messages_layout.setContentsMargins(12, 12, 12, 12)
        self._messages_layout.setSpacing(6)
        self._messages_layout.addStretch()  # Push messages to top
        self._scroll.setWidget(self._messages_widget)

        # Context panel
        self._context_panel = ContextPanel()

        splitter.addWidget(self._scroll)
        splitter.addWidget(self._context_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

        root.addWidget(splitter, 1)

        # ── Input bar ────────────────────────────────────────────────
        input_row = QWidget()
        input_row.setStyleSheet(
            f"background: {theme.BG_SECONDARY};"
            f" border-top: 1px solid {theme.BORDER};"
        )
        input_layout = QHBoxLayout(input_row)
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a query... (e.g. analyze signal, fft, solve math)")
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: {theme.BG_INPUT};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {theme.BORDER_FOCUS};
            }}
        """)
        self._input.returnPressed.connect(self._on_submit)

        self._send_btn = QPushButton("Send")
        self._send_btn.setFixedWidth(60)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {theme.ACCENT};
                color: {theme.BG_PRIMARY};
                border: none;
                border-radius: 4px;
                padding: 6px 0;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: #5ab0ff;
            }}
        """)
        self._send_btn.clicked.connect(self._on_submit)

        input_layout.addWidget(self._input, 1)
        input_layout.addWidget(self._send_btn)

        root.addWidget(input_row)

    # ── Query handling ───────────────────────────────────────────────

    def _on_submit(self):
        text = self._input.text().strip()
        if not text:
            return

        self._input.clear()
        self.query_submitted.emit(text)

        # Add query card
        self._add_card(QueryCard(text))

        # Run engine
        result = self._engine.query(text, self.session)

        # Decide: normal response vs LLM fallback
        if self._engine.needs_llm_fallback(result) and self._llm_provider is not None:
            self._start_llm_stream(text, result)
        elif self._engine.needs_llm_fallback(result):
            self._add_card(NoProviderCard(result))
        else:
            self._add_card(ResponseCard(result))

        # Update context panel
        self._context_panel.refresh(self.session)

    def _start_llm_stream(self, query_text: str, result):
        """Launch a background LLM stream and wire it to a response card."""
        from .llm_worker import LLMWorker

        ctx = LLMContext(
            query=query_text,
            route_matches=result.route_matches,
            header_matches=result.header_matches,
            best_score=self._engine.best_score(result),
        )

        provider_name = type(self._llm_provider).__name__
        card = LLMResponseCard(query_text, provider_name=provider_name)
        self._add_card(card)

        self._active_worker = LLMWorker(self._llm_provider, ctx)
        self._active_worker.token_received.connect(card.append_token)
        self._active_worker.finished.connect(card.on_llm_done)
        self._active_worker.error_occurred.connect(card.on_llm_error)
        self._active_worker.start()

        # Track in session
        if hasattr(self.session, "llm_responses"):
            self.session.llm_responses.append({
                "query": query_text,
                "provider": provider_name,
            })

    def _add_card(self, card):
        """Insert a card before the stretch at the bottom."""
        count = self._messages_layout.count()
        self._messages_layout.insertWidget(count - 1, card)

        # Auto-scroll to bottom
        self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        )
