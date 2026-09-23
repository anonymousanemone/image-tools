"""PDF Tools tab: Flatten / Resize / Side-by-Side / Split / To Images, picked from a left list."""

from PySide6.QtWidgets import QHBoxLayout, QListWidget, QStackedWidget, QWidget

from .pdf_subpanels.flatten_panel import FlattenPanel
from .pdf_subpanels.resizer_panel import ResizerPanel
from .pdf_subpanels.sidebyside_panel import SideBySidePanel
from .pdf_subpanels.splitter_panel import SplitterPanel
from .pdf_subpanels.to_images_panel import ToImagesPanel


class PdfToolsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)

        self.tool_list = QListWidget()
        self.tool_list.setMaximumWidth(160)
        self.tool_list.addItems(["Flatten", "Resize", "Side by Side", "Split", "To Images"])
        layout.addWidget(self.tool_list)

        self.stack = QStackedWidget()
        self.stack.addWidget(FlattenPanel())
        self.stack.addWidget(ResizerPanel())
        self.stack.addWidget(SideBySidePanel())
        self.stack.addWidget(SplitterPanel())
        self.stack.addWidget(ToImagesPanel())
        layout.addWidget(self.stack, 1)

        self.tool_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.tool_list.setCurrentRow(0)
