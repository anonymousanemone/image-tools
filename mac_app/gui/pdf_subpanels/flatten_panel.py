from PySide6.QtWidgets import QLabel, QPushButton, QSpinBox

from core.pdf.flatten import strip_text_layer

from .base_panel import BasePdfPanel


class FlattenPanel(BasePdfPanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.input_edit = self.add_file_picker("Input PDF:")
        self.output_edit = self.add_save_picker("Output PDF:", "scan_only.pdf")

        self.layout_.addWidget(QLabel("DPI:"))
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setValue(300)
        self.layout_.addWidget(self.dpi_spin)

        run_btn = QPushButton("Flatten (Strip Text Layer)")
        run_btn.clicked.connect(self._run)
        self.layout_.addWidget(run_btn)
        self.layout_.addWidget(self.log)

    def _run(self) -> None:
        input_pdf = self.input_edit.text().strip()
        output_pdf = self.output_edit.text().strip() or "scan_only.pdf"
        if not input_pdf:
            self.log.appendPlainText("ERROR: choose an input PDF first.")
            return
        self.run_in_background(strip_text_layer, input_pdf, output_pdf, dpi=self.dpi_spin.value())
