"""
Scaffold tree — QTreeWidget rendering parsed scaffold state.

Shows headers (with modules), routes (with entries), and tables as a
navigable tree. Recently-changed items are highlighted with bold + accent.
"""

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import QHeaderView, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from .. import theme


_HIGHLIGHT_MS = 5000  # How long highlights persist


class ScaffoldTree(QWidget):
    """Tree view of parsed scaffold state (headers, routes, tables)."""

    item_selected = Signal(str, str)  # (category, name) on click

    def __init__(self, parent=None):
        super().__init__(parent)
        self._highlighted: list[tuple[QTreeWidgetItem, QTimer]] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Scaffold State"])
        self._tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tree.setRootIsDecorated(True)
        self._tree.setAnimated(True)
        self._tree.itemClicked.connect(self._on_item_clicked)

        layout.addWidget(self._tree)

        # Top-level category nodes
        self._headers_node = QTreeWidgetItem(self._tree, ["Headers"])
        self._routes_node = QTreeWidgetItem(self._tree, ["Routes"])
        self._tables_node = QTreeWidgetItem(self._tree, ["Tables"])
        self._queue_node = QTreeWidgetItem(self._tree, ["Queue"])

        for node in (self._headers_node, self._routes_node,
                     self._tables_node, self._queue_node):
            font = node.font(0)
            font.setBold(True)
            node.setFont(0, font)
            node.setForeground(0, QBrush(QColor(theme.ACCENT)))
            node.setExpanded(True)

    def refresh(self, scaffold_state):
        """Rebuild tree contents from ScaffoldState."""
        self._populate_headers(scaffold_state.headers)
        self._populate_routes(scaffold_state.routes)
        self._populate_tables(scaffold_state.tables)
        self._populate_queue(scaffold_state.queue_status)

    def _populate_headers(self, headers: dict):
        self._headers_node.takeChildren()
        for fname, data in sorted(headers.items()):
            file_item = QTreeWidgetItem(self._headers_node, [fname])
            file_item.setData(0, Qt.ItemDataRole.UserRole, ("header", fname))
            for mod in data.get("modules", []):
                name = mod.get("name", "?")
                exports = mod.get("exports", [])
                mod_item = QTreeWidgetItem(file_item, [f"#{name}  ({len(exports)} exports)"])
                mod_item.setData(0, Qt.ItemDataRole.UserRole, ("header", fname))
        self._headers_node.setText(0, f"Headers ({self._headers_node.childCount()})")

    def _populate_routes(self, routes: dict):
        self._routes_node.takeChildren()
        for fname, entries in sorted(routes.items()):
            file_item = QTreeWidgetItem(self._routes_node, [f"{fname}  ({len(entries)})"])
            file_item.setData(0, Qt.ItemDataRole.UserRole, ("route", fname))
            for entry in entries:
                entry_item = QTreeWidgetItem(
                    file_item, [f"{entry.concept} -> {entry.path}"]
                )
                entry_item.setData(0, Qt.ItemDataRole.UserRole, ("route", fname))
        self._routes_node.setText(0, f"Routes ({self._routes_node.childCount()})")

    def _populate_tables(self, tables: dict):
        self._tables_node.takeChildren()
        for fname, text in sorted(tables.items()):
            item = QTreeWidgetItem(
                self._tables_node, [f"{fname}  ({len(text)} bytes)"]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, ("table", fname))
        self._tables_node.setText(0, f"Tables ({self._tables_node.childCount()})")

    def _populate_queue(self, queue_status: dict):
        self._queue_node.takeChildren()
        pending = queue_status.get("pending", 0)
        running = queue_status.get("running", 0)
        total = queue_status.get("total", 0)
        self._queue_node.setText(0, f"Queue ({total})")
        if total:
            QTreeWidgetItem(self._queue_node, [f"Pending: {pending}"])
            QTreeWidgetItem(self._queue_node, [f"Running: {running}"])

    def highlight_item(self, event_type: str, path: str):
        """Highlight a recently-changed item by event_type and path."""
        category_map = {
            "header": self._headers_node,
            "route": self._routes_node,
            "table": self._tables_node,
            "queue": self._queue_node,
            "hot_context": None,
            "results": self._queue_node,
            "tuning": None,
        }
        parent_node = category_map.get(event_type)
        if parent_node is None:
            return

        # Find matching child
        for i in range(parent_node.childCount()):
            child = parent_node.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if data and path.endswith(data[1]):
                self._apply_highlight(child)
                return

    def _apply_highlight(self, item: QTreeWidgetItem):
        """Bold + accent background, auto-clear after timeout."""
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        item.setBackground(0, QBrush(QColor(theme.BG_PANEL)))

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._clear_highlight(item, timer))
        timer.start(_HIGHLIGHT_MS)
        self._highlighted.append((item, timer))

    def _clear_highlight(self, item: QTreeWidgetItem, timer: QTimer):
        """Remove highlight from an item."""
        font = item.font(0)
        font.setBold(False)
        item.setFont(0, font)
        item.setBackground(0, QBrush())
        self._highlighted = [
            (i, t) for i, t in self._highlighted if t is not timer
        ]

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            self.item_selected.emit(data[0], data[1])
