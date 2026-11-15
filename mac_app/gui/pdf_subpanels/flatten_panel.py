import os

from PySide6.QtWidgets import QSpinBox

from core.pdf.flatten import strip_text_layer

from .base_panel import BasePdfPanel, _sibling_path


class FlattenPanel(BasePdfPanel):
    RUN_TEXT = "Flatten (Strip Text Layer)"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setValue(300)
        self.dpi_spin.valueChanged.connect(self._on_inputs_changed)
        self.options_layout.addRow("DPI:", self.dpi_spin)

    def options(self) -> dict:
        return {"dpi": self.dpi_spin.value()}

    def default_output(self, params: dict) -> str:
        return _sibling_path(params["input"], "flattened")

    def run_job(self, temp_dir: str, params: dict, on_progress) -> list[str]:
        output = os.path.join(temp_dir, os.path.basename(self.default_output(params)))
        strip_text_layer(params["input"], output, dpi=params["dpi"], on_progress=on_progress)
        return [output]
