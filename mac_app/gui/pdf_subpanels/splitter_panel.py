from PySide6.QtWidgets import QLabel, QPushButton, QSpinBox

from core.pdf.splitter import split_pdf_by_size

from .base_panel import BasePdfPanel


class SplitterPanel(BasePdfPanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.input_edit = self.add_file_picker("Input PDF:")

        self.layout_.addWidget(QLabel("Max size per part (MB):"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 500)
        self.size_spin.setValue(9)
        self.layout_.addWidget(self.size_spin)

        run_btn = QPushButton("Split PDF")
        run_btn.clicked.connect(self._run)
        self.layout_.addWidget(run_btn)
        self.layout_.addWidget(self.log)

    def _run(self) -> None:
        input_pdf = self.input_edit.text().strip()
        if not input_pdf:
            self.log.appendPlainText("ERROR: choose an input PDF first.")
            return
        self.run_in_background(split_pdf_by_size, input_pdf, self.size_spin.value())
