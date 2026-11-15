import os
from pathlib import Path

from PySide6.QtWidgets import QSpinBox

from core.pdf.to_images import pdf_to_images

from .base_panel import BasePdfPanel


class ToImagesPanel(BasePdfPanel):
    RUN_TEXT = "Convert PDF to Images"
    OUTPUT_IS_FOLDER = True

    def __init__(self, parent=None):
        super().__init__(parent)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setValue(300)
        self.dpi_spin.valueChanged.connect(self._on_inputs_changed)
        self.options_layout.addRow("DPI:", self.dpi_spin)

        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(95)
        self.quality_spin.valueChanged.connect(self._on_inputs_changed)
        self.options_layout.addRow("JPEG Quality:", self.quality_spin)

    def options(self) -> dict:
        return {"dpi": self.dpi_spin.value(), "quality": self.quality_spin.value()}

    def default_output(self, params: dict) -> str:
        path = Path(params["input"])
        return str(path.with_name(path.stem))

    def run_job(self, temp_dir: str, params: dict, on_progress) -> list[str]:
        pdf_to_images(
            params["input"],
            dpi=params["dpi"],
            jpeg_quality=params["quality"],
            output_dir=temp_dir,
            on_progress=on_progress,
        )
        return sorted(os.path.join(temp_dir, name) for name in os.listdir(temp_dir))
