"""PDF Tools tab: tool buttons and the active tool's controls on the left, page preview on the right.

Previews render on a dedicated one-thread pool, so a Run (on the global pool) never queues behind them.
Rendered pages are not cached: the tab keeps only the document on screen, and re-renders only when that document's file changes.
"""

import os
from dataclasses import dataclass

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.image_io import page_sizes, preview_scale, render_pdf_pages
from core.utils import pil_to_qimage

from .pdf_pages_view import PdfPagesView
from .pdf_subpanels.base_panel import PreviewDoc, PreviewRequest
from .pdf_subpanels.flatten_panel import FlattenPanel
from .pdf_subpanels.resizer_panel import ResizerPanel
from .pdf_subpanels.sidebyside_panel import SideBySidePanel
from .pdf_subpanels.splitter_panel import SplitterPanel
from .pdf_subpanels.to_images_panel import ToImagesPanel
from .workers import Worker

TOOL_BUTTON_PADDING = 28

TOOLS = [
    ("Flatten", FlattenPanel),
    ("Split", SplitterPanel),
    ("To Images", ToImagesPanel),
    ("Resize", ResizerPanel),
    ("Side by Side", SideBySidePanel),
]


@dataclass
class PreviewOutcome:
    request: PreviewRequest
    doc: PreviewDoc | None = None
    key: tuple | None = None
    images: list | None = None
    reduced: bool = False
    error: str | None = None


def _doc_key(path: str) -> tuple:
    stat = os.stat(path)
    return path, stat.st_mtime_ns, stat.st_size


def _render_preview(panel, request: PreviewRequest, shown_key, on_progress=None) -> PreviewOutcome:
    """Off the GUI thread; renders only when the document differs from the one already shown."""
    try:
        doc = panel.preview_job(request)
        key = _doc_key(doc.path)
        if key == shown_key:
            return PreviewOutcome(request, doc, key)
        scale, reduced = preview_scale(page_sizes(doc.path))
        images = [pil_to_qimage(image) for image in render_pdf_pages(doc.path, scale)]
        return PreviewOutcome(request, doc, key, images, reduced)
    except Exception as e:
        return PreviewOutcome(request, error=str(e))


class PdfToolsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._preview_pool = QThreadPool(self)
        self._preview_pool.setMaxThreadCount(1)
        self._shown_key: tuple | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        controls_widget = QWidget()
        controls = QVBoxLayout(controls_widget)
        controls.setSpacing(8)
        controls.setContentsMargins(8, 8, 8, 8)

        tool_group = QGroupBox("Tool")
        tool_rows = QVBoxLayout(tool_group)
        tool_rows.setSpacing(4)
        rows = [QHBoxLayout(), QHBoxLayout()]
        for row in rows:
            row.setSpacing(4)
            tool_rows.addLayout(row)
        self.tool_buttons = QButtonGroup(self)
        self.stack = QStackedWidget()
        for index, (name, panel_cls) in enumerate(TOOLS):
            button = QPushButton(name)
            button.setCheckable(True)
            # Size to the label; the style's default minimum would pad short names to one width.
            button.setFixedWidth(button.fontMetrics().horizontalAdvance(name) + TOOL_BUTTON_PADDING)
            self.tool_buttons.addButton(button, index)
            rows[index // 3].addWidget(button)
            panel = panel_cls()
            panel.preview_requested.connect(self._on_preview_requested)
            panel.toggle_changed.connect(self._on_toggle_changed)
            panel.input_changed.connect(self._on_input_changed)
            self.stack.addWidget(panel)
        for row in rows:
            row.addStretch()
        self.tool_buttons.idClicked.connect(self._select_tool)
        controls.addWidget(tool_group)
        controls.addWidget(self.stack)
        controls.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(controls_widget)
        scroll.setMinimumWidth(260)
        splitter.addWidget(scroll)

        self.preview = PdfPagesView()
        self.preview.view_toggled.connect(self._on_view_toggled)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([340, 860])

        root.addWidget(splitter)

        self.tool_buttons.button(0).setChecked(True)
        self._select_tool(0)

    def _select_tool(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        panel = self.stack.currentWidget()
        self.preview.set_toggle(*panel.toggle_state())
        panel.request_preview()

    def _on_toggle_changed(self, visible: bool, result_enabled: bool, selected: str) -> None:
        if self.sender() is self.stack.currentWidget():
            self.preview.set_toggle(visible, result_enabled, selected)

    def _on_input_changed(self, path: str) -> None:
        if self.sender() is not self.stack.currentWidget():
            return
        for index in range(self.stack.count()):
            panel = self.stack.widget(index)
            if panel is not self.sender():
                panel.set_input(path)

    def _on_view_toggled(self, view: str) -> None:
        self.stack.currentWidget().set_view(view)

    def _on_preview_requested(self, request: PreviewRequest | None) -> None:
        if self.sender() is self.stack.currentWidget():
            self._submit_preview(self.sender(), request)

    def _submit_preview(self, panel, request: PreviewRequest | None) -> None:
        self._preview_pool.clear()
        if request is None:
            self._show_nothing()
            return
        worker = Worker(_render_preview, panel, request, self._shown_key)
        worker.signals.result.connect(self._on_preview_result)
        self._preview_pool.start(worker)

    def _on_preview_result(self, outcome: PreviewOutcome) -> None:
        panel = self.stack.currentWidget()
        if outcome.request is not panel.latest_request:
            return
        if outcome.error is not None:
            self._shown_key = None
            self.preview.show_error(outcome.error)
            return
        doc = outcome.doc
        if outcome.images is None:
            if outcome.key != self._shown_key:
                self._submit_preview(panel, outcome.request)
                return
            self.preview.set_marks(doc.marks, doc.legend)
        else:
            self._shown_key = outcome.key
            self.preview.show_pages(outcome.images, doc.marks, doc.legend, doc.path, outcome.reduced)
        panel.on_preview_shown(doc)

    def _show_nothing(self) -> None:
        self._shown_key = None
        self.preview.clear()
