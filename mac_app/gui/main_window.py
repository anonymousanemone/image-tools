"""Main application window: 3 tabs + Help menu."""

from PySide6.QtWidgets import QMainWindow, QTabWidget

from .binarizer_tab import BinarizerTab
from .dialogs import DependencyDialog
from .pdf_tab import PdfToolsTab
from .pixel_colors_tab import PixelColorsTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Tools")
        self.resize(1200, 800)

        tabs = QTabWidget()
        tabs.addTab(BinarizerTab(), "Binarizer")
        tabs.addTab(PixelColorsTab(), "Pixel Colors & Colormap")
        tabs.addTab(PdfToolsTab(), "PDF Tools")
        self.setCentralWidget(tabs)

        help_menu = self.menuBar().addMenu("Help")
        help_menu.addAction("Check Dependencies…", self._show_dependencies)

    def _show_dependencies(self) -> None:
        DependencyDialog(self).exec()
