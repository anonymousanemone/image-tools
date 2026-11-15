import os
import tempfile

from core.pdf.sidebyside import combine_pdfs_side_by_side
from core.utils import session_temp_dir

from .base_panel import BasePdfPanel, PreviewDoc, PreviewRequest, _sibling_path


class SideBySidePanel(BasePdfPanel):
    INPUT_LABEL = "Left PDF:"
    RUN_TEXT = "Combine Side by Side"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._preview_dir = session_temp_dir()
        self.right_edit = self.add_input_picker("Right PDF:")
        self.options_group.setVisible(False)

    def options(self) -> dict:
        return {"right": self.right_edit.text().strip()}

    def default_output(self, params: dict) -> str:
        return _sibling_path(params["input"], "combined")

    def _run(self) -> None:
        if not self.params()["right"]:
            self._set_status("Choose both PDFs first.", error=True)
            return
        super()._run()

    def run_job(self, temp_dir: str, params: dict, on_progress) -> list[str]:
        output = os.path.join(temp_dir, os.path.basename(self.default_output(params)))
        combine_pdfs_side_by_side(params["input"], params["right"], output, on_progress=on_progress)
        return [output]

    def preview_job(self, request: PreviewRequest) -> PreviewDoc:
        params = request.params
        if not params["right"]:
            return PreviewDoc(params["input"])
        fd, combined = tempfile.mkstemp(suffix=".pdf", dir=self._preview_dir)
        os.close(fd)
        combine_pdfs_side_by_side(params["input"], params["right"], combined)
        return PreviewDoc(combined)

    def on_preview_shown(self, doc: PreviewDoc) -> None:
        for name in os.listdir(self._preview_dir):
            path = os.path.join(self._preview_dir, name)
            if path != doc.path:
                os.remove(path)
