"""HeadersBrowser — tree of scaffold modules + exports + deps."""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
)


class HeadersBrowser(QDialog):
    """Tree of headers/modules. Doubles as the UI for `terra dep`."""

    def __init__(self, scaffold_state, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Headers / Modules")
        self.setMinimumSize(720, 520)
        self._state = scaffold_state

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Headers / Modules")
        header.setObjectName("section_header")
        layout.addWidget(header)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Module", "Detail"])
        self.tree.setColumnWidth(0, 240)
        layout.addWidget(self.tree, 1)

        # Footer
        footer = QHBoxLayout()
        self.count_label = QLabel("")
        self.count_label.setObjectName("dim")
        footer.addWidget(self.count_label)
        footer.addStretch(1)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self._reload)
        footer.addWidget(refresh)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

        self._reload()

    def _reload(self):
        self.tree.clear()
        total_modules = 0
        for filename, data in self._state.headers.items():
            modules = data.get("modules", []) if isinstance(data, dict) else []
            file_node = QTreeWidgetItem([filename, f"{len(modules)} modules"])
            self.tree.addTopLevelItem(file_node)
            for module in modules:
                if not isinstance(module, dict):
                    continue
                name = module.get("name", "")
                desc = module.get("desc", "")
                module_node = QTreeWidgetItem([name, desc])
                file_node.addChild(module_node)
                exports = module.get("exports", [])
                if exports:
                    exp_node = QTreeWidgetItem(["exports", ", ".join(exports)])
                    module_node.addChild(exp_node)
                depends = module.get("depends", [])
                if depends:
                    dep_node = QTreeWidgetItem(["depends", ", ".join(depends)])
                    module_node.addChild(dep_node)
                path = module.get("path", "")
                if path:
                    path_node = QTreeWidgetItem(["path", path])
                    module_node.addChild(path_node)
                total_modules += 1
            file_node.setExpanded(True)
        self.count_label.setText(f"{total_modules} modules in {len(self._state.headers)} files")
