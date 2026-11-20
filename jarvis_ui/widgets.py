from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from .ui_spec import StatusCardSpec


class StatusCard(QFrame):
    def __init__(self, spec: StatusCardSpec, status: str, parent=None):
        super().__init__(parent)
        self.setObjectName("statusCard")
        self.setMinimumHeight(150)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(7)

        top = QHBoxLayout()
        icon = QLabel(spec.icon)
        icon.setObjectName("cardIcon")
        icon.setFixedWidth(42)
        top.addWidget(icon)

        title = QLabel(spec.title)
        title.setObjectName("cardTitle")
        top.addWidget(title)
        top.addStretch()
        root.addLayout(top)

        status_row = QHBoxLayout()
        dot = QLabel("●")
        dot.setObjectName("statusDot")
        dot.setFixedWidth(14)
        status_row.addWidget(dot)

        self.status_label = QLabel(status)
        self.status_label.setObjectName("statusText")
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        root.addLayout(status_row)

        description = QLabel(spec.description)
        description.setObjectName("cardDescription")
        description.setWordWrap(True)
        root.addWidget(description)
        root.addStretch()

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)
