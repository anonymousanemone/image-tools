import os

from PySide6.QtGui import QColor
from pypdf import PdfReader
from PySide6.QtWidgets import QSpinBox

from core.pdf.resizer import normalize_pdf_width, page_width_changes

from .base_panel import BasePdfPanel, PreviewDoc, PreviewRequest, _sibling_path

SHRUNK_COLOR = QColor(0, 153, 0)
ENLARGED_COLOR = QColor(0, 0, 255)
CHANGE_MARKS = {-1: (SHRUNK_COLOR, None), 1: (ENLARGED_COLOR, None)}


class ResizerPanel(BasePdfPanel):
    RUN_TEXT = "Normalize Page Width"
    HAS_RESULT_VIEW = True

    def __init__(self, parent=None):
        super().__init__(parent)

        self.ref_page_spin = QSpinBox()
        self.ref_page_spin.setRange(0, 0)
        self.ref_page_spin.valueChanged.connect(self._on_inputs_changed)
        self.options_layout.addRow("Reference page (0-based):", self.ref_page_spin)

    def _on_inputs_changed(self) -> None:
        # pypdf, not PyMuPDF: this runs on the GUI thread and must not wait on PYMUPDF_LOCK.
        try:
            last_page = len(PdfReader(self.input_edit.text().strip()).pages) - 1
        except Exception:
            last_page = 0
        self.ref_page_spin.blockSignals(True)
        self.ref_page_spin.setMaximum(max(0, last_page))
        self.ref_page_spin.blockSignals(False)
        super()._on_inputs_changed()

    def options(self) -> dict:
        return {"ref": self.ref_page_spin.value()}

    def default_output(self, params: dict) -> str:
        return _sibling_path(params["input"], "resized")

    def run_job(self, temp_dir: str, params: dict, on_progress) -> list[str]:
        output = os.path.join(temp_dir, os.path.basename(self.default_output(params)))
        normalize_pdf_width(
            params["input"], output_path=output, reference_page_index=params["ref"], on_progress=on_progress
        )
        return [output]

    def preview_job(self, request: PreviewRequest) -> PreviewDoc:
        params = request.params
        changes = page_width_changes(params["input"], params["ref"])
        marks = [CHANGE_MARKS.get(change) for change in changes]
        legend = [(SHRUNK_COLOR, "Shrunk"), (ENLARGED_COLOR, "Enlarged")]
        if request.view == "result" and request.run_output:
            return PreviewDoc(request.run_output[0], marks, legend)
        return PreviewDoc(params["input"], marks, legend)
