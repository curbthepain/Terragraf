"""
Message cards for the native tab chat panel.

QueryCard: shows the user's input.
ResponseCard: shows route matches, skill match, header refs, output.
LLMResponseCard: streaming LLM response card.
NoProviderCard: hint card shown when no LLM provider is configured.

All visual styling is centralized in app.theme via object names — these
classes only set object names and structure widgets.
"""

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
)


class QueryCard(QFrame):
    """Renders a user query as a styled card."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("queryCard")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        prompt = QLabel(">")
        prompt.setObjectName("status_accent_bold")
        prompt.setFixedWidth(16)

        body = QLabel(text)
        body.setWordWrap(True)

        layout.addWidget(prompt)
        layout.addWidget(body, 1)


class ResponseCard(QFrame):
    """Renders a query result as a styled card with sections."""

    def __init__(self, result, parent=None):
        super().__init__(parent)
        self.setObjectName("responseCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Skill match section
        if result.skill_match:
            name, manifest = result.skill_match
            desc = manifest.get("skill", {}).get("description", "")
            skill_label = QLabel(f"Skill: {name}")
            skill_label.setObjectName("status_green_bold")
            layout.addWidget(skill_label)
            if desc:
                desc_label = QLabel(f"  {desc}")
                desc_label.setObjectName("subtitle")
                desc_label.setWordWrap(True)
                layout.addWidget(desc_label)

        # Route matches section
        if result.route_matches:
            routes_header = QLabel(f"Routes ({len(result.route_matches)}):")
            routes_header.setObjectName("status_cyan_bold")
            layout.addWidget(routes_header)
            for rm in result.route_matches[:8]:  # Cap display at 8
                score_pct = int(rm.score * 100)
                route_line = QLabel(
                    f"  {rm.concept} -> {rm.path}  [{score_pct}%]"
                )
                layout.addWidget(route_line)

        # Header matches section
        if result.header_matches:
            hdr_header = QLabel(f"Headers ({len(result.header_matches)}):")
            hdr_header.setObjectName("status_yellow_bold")
            layout.addWidget(hdr_header)
            for hm in result.header_matches[:5]:
                tags_str = ", ".join(hm.tags[:4]) if hm.tags else ""
                hdr_line = QLabel(
                    f"  #{hm.module_name}  [{hm.source_file}]"
                    + (f"  tags: {tags_str}" if tags_str else "")
                )
                layout.addWidget(hdr_line)

        # Execution output
        if result.executed and result.output:
            out_header = QLabel("Output:")
            out_header.setObjectName("status_accent_bold")
            layout.addWidget(out_header)
            out_text = QLabel(result.output.rstrip()[:2000])
            out_text.setWordWrap(True)
            out_text.setObjectName("mono")
            layout.addWidget(out_text)

        # Error
        if result.error:
            err_label = QLabel(f"Error: {result.error}")
            err_label.setObjectName("status_red")
            err_label.setWordWrap(True)
            layout.addWidget(err_label)

        # No matches fallback
        if not result.skill_match and not result.route_matches and not result.header_matches:
            none_label = QLabel("No matches found.")
            none_label.setObjectName("dim")
            layout.addWidget(none_label)


_LLM_MAX_DISPLAY = 8000


class LLMResponseCard(QFrame):
    """
    Streaming LLM response card.

    Call append_token(text) from LLMWorker.token_received.
    Call on_llm_done() from LLMWorker.finished.
    Call on_llm_error(msg) from LLMWorker.error_occurred.
    """

    def __init__(self, query_text: str, provider_name: str = "", parent=None):
        super().__init__(parent)
        self._provider_name = provider_name
        self._full_text = ""
        self.setObjectName("llmCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Status label
        self._status_label = QLabel("LLM streaming...")
        self._status_label.setObjectName("status_cyan")
        layout.addWidget(self._status_label)

        # Streaming text area
        self._text_edit = QTextEdit()
        self._text_edit.setObjectName("llmText")
        self._text_edit.setReadOnly(True)
        self._text_edit.setPlainText("...")
        self._text_edit.setMinimumHeight(40)
        layout.addWidget(self._text_edit)

    def _restyle(self, name: str):
        """Swap object name and re-polish so the new selector applies."""
        self._text_edit.setObjectName(name)
        self._text_edit.style().unpolish(self._text_edit)
        self._text_edit.style().polish(self._text_edit)

    def append_token(self, token: str):
        """Append a streamed token. Called from main thread via Qt signal."""
        if not self._full_text:
            self._text_edit.clear()
        self._full_text += token
        # Cap display length
        display = self._full_text[-_LLM_MAX_DISPLAY:]
        self._text_edit.setPlainText(display)
        # Auto-scroll
        sb = self._text_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_llm_done(self):
        """Mark streaming complete."""
        label = f"LLM [{self._provider_name}]" if self._provider_name else "LLM"
        self._status_label.setText(label)
        self._status_label.setObjectName("status_green")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    def on_llm_error(self, error_msg: str):
        """Show error state inline."""
        self._text_edit.setPlainText(f"LLM error: {error_msg}")
        self._restyle("llmTextError")
        self._status_label.setText("error")
        self._status_label.setObjectName("status_red")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    @property
    def full_text(self) -> str:
        return self._full_text


class NoProviderCard(QFrame):
    """Static card shown when no LLM provider is configured."""

    def __init__(self, result=None, parent=None):
        super().__init__(parent)
        self.setObjectName("noProviderCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        msg = QLabel(
            "No LLM provider configured. "
            "Set ANTHROPIC_API_KEY / OPENAI_API_KEY environment variable, "
            'or add an "llm" section to .terragraf_settings.json.'
        )
        msg.setWordWrap(True)
        msg.setObjectName("status_yellow")
        layout.addWidget(msg)
