from core.pdf.sidebyside import combine_pdfs_side_by_side
from PySide6.QtWidgets import QPushButton

from .base_panel import BasePdfPanel


class SideBySidePanel(BasePdfPanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf1_edit = self.add_file_picker("Left PDF:")
        self.pdf2_edit = self.add_file_picker("Right PDF:")
        self.output_edit = self.add_save_picker("Output PDF:", "combined.pdf")

        run_btn = QPushButton("Combine Side by Side")
        run_btn.clicked.connect(self._run)
        self.layout_.addWidget(run_btn)
        self.layout_.addWidget(self.log)

    def _run(self) -> None:
        pdf1 = self.pdf1_edit.text().strip()
        pdf2 = self.pdf2_edit.text().strip()
        output = self.output_edit.text().strip() or "combined.pdf"
        if not pdf1 or not pdf2:
            self.log.appendPlainText("ERROR: choose both PDFs first.")
            return
        self.run_in_background(combine_pdfs_side_by_side, pdf1, pdf2, output)
