"""Mapping-table "To" cell: swatch button (color picker with alpha) + hex field.

Blank means keep the original color.
"""

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QHBoxLayout, QLineEdit, QPushButton, QWidget

from core.pixel_colors import hex_to_rgba, is_valid_hex_color, rgba_to_hex


class ColorPickerCell(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        self.swatch_btn = QPushButton()
        self.swatch_btn.setFixedSize(22, 22)
        self.swatch_btn.clicked.connect(self._pick_color)
        layout.addWidget(self.swatch_btn)

        self.hex_edit = QLineEdit()
        self.hex_edit.setPlaceholderText("keep original")
        self.hex_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.hex_edit)

        self._update_swatch()

    def _pick_color(self) -> None:
        current = self.color()
        initial = current if current is not None else QColor(255, 255, 255)
        color = QColorDialog.getColor(
            initial, self, "Pick replacement color", QColorDialog.ShowAlphaChannel
        )
        if color.isValid():
            self.hex_edit.setText(rgba_to_hex(color.getRgb()))

    def _on_text_changed(self, _text: str) -> None:
        self._update_swatch()
        self.changed.emit()

    def color(self) -> QColor | None:
        text = self.hex_edit.text().strip()
        if not text or not is_valid_hex_color(text):
            return None
        r, g, b, a = hex_to_rgba(text)
        return QColor(r, g, b, a)

    def hex_text(self) -> str:
        return self.hex_edit.text().strip()

    def clear(self) -> None:
        self.hex_edit.clear()

    def _update_swatch(self) -> None:
        color = self.color()
        if color is None:
            self.swatch_btn.setStyleSheet("background-color: transparent; border: 1px dashed #888;")
        else:
            self.swatch_btn.setStyleSheet(
                f"background-color: {color.name(QColor.HexArgb)}; border: 1px solid #333;"
            )
