"""Reusable dialogs: dependency diagnostics."""

from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from core.colormap_magick import magick_available
from core.segment import vision_available


class DependencyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Check Dependencies")
        layout = QVBoxLayout(self)

        checks = [
            ("macOS Vision (Remove Background)", vision_available(), None),
            ("ImageMagick `magick` CLI (Colormap)", magick_available(), "brew install imagemagick"),
        ]

        for name, ok, fix in checks:
            status = "✓ Available" if ok else "✗ Not available"
            text = f"{name}: {status}"
            if not ok and fix:
                text += f"  —  install with: {fix}"
            layout.addWidget(QLabel(text))

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
