from PySide6.QtWidgets import QLabel, QPushButton, QSpinBox

from core.pdf.to_images import pdf_to_images

from .base_panel import BasePdfPanel


class ToImagesPanel(BasePdfPanel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.input_edit = self.add_file_picker("Input PDF:")
        self.output_edit = self.add_dir_picker("Output folder (optional):")

        self.layout_.addWidget(QLabel("DPI:"))
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setValue(300)
        self.layout_.addWidget(self.dpi_spin)

        self.layout_.addWidget(QLabel("JPEG Quality:"))
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(95)
        self.layout_.addWidget(self.quality_spin)

        run_btn = QPushButton("Convert PDF to Images")
        run_btn.clicked.connect(self._run)
        self.layout_.addWidget(run_btn)
        self.layout_.addWidget(self.log)

    def _run(self) -> None:
        input_pdf = self.input_edit.text().strip()
        if not input_pdf:
            self.log.appendPlainText("ERROR: choose an input PDF first.")
            return
        output_dir = self.output_edit.text().strip() or None
        self.run_in_background(
            pdf_to_images,
            input_pdf,
            dpi=self.dpi_spin.value(),
            jpeg_quality=self.quality_spin.value(),
            output_dir=output_dir,
        )
