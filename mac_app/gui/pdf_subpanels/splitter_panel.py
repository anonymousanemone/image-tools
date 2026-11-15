import os

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QSpinBox

from core.pdf.splitter import BYTES_IN_MB, part_filename, plan_split, split_pdf_by_size

from .base_panel import BasePdfPanel, PreviewDoc, PreviewRequest

PART_COLORS = [QColor(c) for c in ("#1e88e5", "#e53935", "#43a047", "#fb8c00", "#8e24aa", "#00897b")]


class SplitterPanel(BasePdfPanel):
    RUN_TEXT = "Split PDF"
    OUTPUT_IS_FOLDER = True

    def __init__(self, parent=None):
        super().__init__(parent)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 500)
        self.size_spin.setValue(9)
        self.size_spin.valueChanged.connect(self._on_inputs_changed)
        self.options_layout.addRow("Max size per part (MB):", self.size_spin)

    def options(self) -> dict:
        return {"max_mb": self.size_spin.value()}

    def default_output(self, params: dict) -> str:
        return os.path.dirname(os.path.abspath(params["input"]))

    def run_job(self, temp_dir: str, params: dict, on_progress) -> list[str]:
        return split_pdf_by_size(params["input"], params["max_mb"], output_dir=temp_dir, on_progress=on_progress)

    def preview_job(self, request: PreviewRequest) -> PreviewDoc:
        params = request.params
        marks, legend = [], []
        for number, (pages, size) in enumerate(plan_split(params["input"], params["max_mb"]), start=1):
            color = PART_COLORS[(number - 1) % len(PART_COLORS)]
            marks.extend((color, f"Part {number}") for _ in pages)
            over = " (over limit)" if size > params["max_mb"] * BYTES_IN_MB else ""
            legend.append((color, f"{part_filename(params['input'], number)} — {size / BYTES_IN_MB:.1f} MB{over}"))
        return PreviewDoc(params["input"], marks, legend)
