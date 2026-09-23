from PySide6.QtWidgets import QLabel, QPushButton, QSpinBox

from core.pdf.resizer import normalize_pdf_width

from .base_panel import BasePdfPanel


class ResizerPanel(BasePdfPanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.input_edit = self.add_file_picker("Input PDF:")
        self.output_edit = self.add_save_picker("Output PDF (optional):", "input-resized.pdf")

        self.layout_.addWidget(QLabel("Reference page index (0-based):"))
        self.ref_page_spin = QSpinBox()
        self.ref_page_spin.setRange(0, 9999)
        self.layout_.addWidget(self.ref_page_spin)

        run_btn = QPushButton("Normalize Page Width")
        run_btn.clicked.connect(self._run)
        self.layout_.addWidget(run_btn)
        self.layout_.addWidget(self.log)

    def _run(self) -> None:
        input_pdf = self.input_edit.text().strip()
        if not input_pdf:
            self.log.appendPlainText("ERROR: choose an input PDF first.")
            return
        output_pdf = self.output_edit.text().strip() or None
        self.run_in_background(
            normalize_pdf_width,
            input_pdf,
            output_path=output_pdf,
            reference_page_index=self.ref_page_spin.value(),
        )
