"""Zoomable, scrolling view of a PDF's rendered pages, stacked vertically.

Marks (page borders and "Part N" tags) are scene items drawn over the pages, so they never reach an output file.
Zoom is the view transform, so zooming never rescales pixmaps.
"""

import subprocess

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPixmap, QTransform
from PySide6.QtWidgets import (
    QButtonGroup,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .zoom import ZoomMixin

PAGE_SPACING = 16
MARK_WIDTH = 4
REDUCED_NOTE = "File too large — showing reduced preview"


class PdfPagesView(ZoomMixin, QWidget):
    view_toggled = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._page_items: list = []
        self._mark_items: list = []
        self._path: str | None = None

        toolbar = self._init_zoom()

        self._toggle = QWidget()
        toggle_row = QHBoxLayout(self._toggle)
        toggle_row.setContentsMargins(0, 0, 0, 0)
        toggle_row.setSpacing(0)
        self._original_btn = QPushButton("Original")
        self._result_btn = QPushButton("Result")
        self._toggle_group = QButtonGroup(self)
        for btn in (self._original_btn, self._result_btn):
            btn.setCheckable(True)
            self._toggle_group.addButton(btn)
            toggle_row.addWidget(btn)
        self._original_btn.setChecked(True)
        self._toggle_group.buttonClicked.connect(self._on_toggle_clicked)
        self._toggle.setVisible(False)

        self._preview_btn = QPushButton("See in Preview")
        self._preview_btn.clicked.connect(self.open_in_native_preview)
        self._preview_btn.setEnabled(False)

        toolbar.addWidget(self._toggle)
        toolbar.addWidget(self._preview_btn)
        toolbar.addStretch()

        self._scene = QGraphicsScene(self)
        self._view = QGraphicsView(self._scene)
        self._view.setDragMode(QGraphicsView.ScrollHandDrag)
        self._view.setRenderHint(QPainter.SmoothPixmapTransform)
        self._view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self._view.setBackgroundBrush(QColor("#9e9e9e"))
        self._view.viewport().installEventFilter(self)

        self._legend = QLabel()
        self._legend.setWordWrap(True)
        self._legend.setVisible(False)
        self._note = QLabel()
        self._note.setWordWrap(True)
        self._note.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(toolbar)
        layout.addWidget(self._view, 1)
        layout.addWidget(self._legend)
        layout.addWidget(self._note)

    def show_pages(self, images: list, marks, legend, path: str, reduced: bool) -> None:
        """Show `images` (QImages), emptying the list as each page becomes a pixmap."""
        self._clear_scene()
        widest = max((image.width() for image in images), default=0)
        y = 0
        images.reverse()
        while images:
            image = images.pop()
            item = self._scene.addPixmap(QPixmap.fromImage(image))
            item.setTransformationMode(Qt.SmoothTransformation)
            item.setPos((widest - image.width()) / 2, y)
            self._page_items.append(item)
            y += image.height() + PAGE_SPACING
        self._scene.setSceneRect(
            self._scene.itemsBoundingRect().adjusted(-PAGE_SPACING, -PAGE_SPACING, PAGE_SPACING, PAGE_SPACING)
        )
        self._path = path
        self._preview_btn.setEnabled(True)
        self._set_note(REDUCED_NOTE if reduced else "")
        self.set_marks(marks, legend)
        self._fit_to_window = True
        self._apply_zoom()
        self._view.verticalScrollBar().setValue(self._view.verticalScrollBar().minimum())

    def set_marks(self, marks, legend) -> None:
        for item in self._mark_items:
            self._scene.removeItem(item)
        self._mark_items = []
        for page_item, mark in zip(self._page_items, marks):
            if mark is not None:
                self._add_mark(page_item, *mark)
        self._legend.setText("   ".join(
            f'<span style="color:{color.name()}">■</span> {text}' for color, text in legend
        ))
        self._legend.setVisible(bool(legend))

    def _add_mark(self, page_item, color: QColor, label: str | None) -> None:
        rect = page_item.sceneBoundingRect()
        pen = QPen(color, MARK_WIDTH)
        pen.setCosmetic(True)
        border = self._scene.addRect(rect, pen)
        self._mark_items.append(border)
        if label:
            text = QGraphicsSimpleTextItem(label)
            text.setBrush(QBrush(Qt.white))
            tag = QGraphicsRectItem(text.boundingRect().adjusted(-4, -2, 4, 2))
            tag.setBrush(QBrush(color))
            tag.setPen(QPen(Qt.NoPen))
            tag.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            text.setParentItem(tag)
            tag.setPos(rect.topLeft())
            self._scene.addItem(tag)
            self._mark_items.append(tag)

    def show_error(self, message: str) -> None:
        self.clear()
        self._set_note(message)

    def clear(self) -> None:
        self._clear_scene()
        self._path = None
        self._preview_btn.setEnabled(False)
        self._legend.setVisible(False)
        self._set_note("")

    def set_toggle(self, visible: bool, result_enabled: bool, selected: str) -> None:
        self._toggle.setVisible(visible)
        self._result_btn.setEnabled(result_enabled)
        (self._result_btn if selected == "result" else self._original_btn).setChecked(True)

    def _on_toggle_clicked(self, button) -> None:
        self.view_toggled.emit("result" if button is self._result_btn else "original")

    def _clear_scene(self) -> None:
        self._scene.clear()
        self._scene.setSceneRect(QRectF())
        self._page_items = []
        self._mark_items = []

    def _set_note(self, text: str) -> None:
        self._note.setText(text)
        self._note.setVisible(bool(text))

    def _apply_zoom(self) -> None:
        # QGraphicsView centers against the width without the scrollbar unless the bar is
        # AlwaysOn, so turn it on whenever the pages overflow to keep both side gaps equal.
        scene_rect = self._scene.sceneRect()
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        available = self._view.maximumViewportSize()
        if self._fit_to_window and self._page_items:
            self._zoom = (available.width() - 1) / scene_rect.width()
        if self._page_items and scene_rect.height() * self._zoom > available.height():
            self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            if self._fit_to_window:
                self._zoom = (self._view.maximumViewportSize().width() - 1) / scene_rect.width()
        self._view.setTransform(QTransform.fromScale(self._zoom, self._zoom))
        self._show_zoom()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._fit_to_window:
            self._apply_zoom()

    def eventFilter(self, obj, event) -> bool:
        return self._zoom_event(event) or super().eventFilter(obj, event)

    def open_in_native_preview(self) -> None:
        if self._path:
            subprocess.Popen(["open", "-a", "Preview", self._path])
