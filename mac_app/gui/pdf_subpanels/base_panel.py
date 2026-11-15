"""Shared PDF sub-panel scaffolding: Input / Options / Run / Output (Save) / status.

Run writes only into a fresh temp folder; Save copies that output to the chosen path.
Preview requests are snapshots: the tab shows a preview result only while its request is
the panel's `latest_request`, so late renders for stale inputs are dropped.
"""

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QThreadPool, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.utils import session_temp_dir

from ..workers import Worker

ERROR_STYLE = "color: #c62828;"
PDF_FILTER = "PDF Files (*.pdf)"


@dataclass(eq=False)
class PreviewRequest:
    params: dict
    view: str
    run_output: list[str]


@dataclass
class PreviewDoc:
    """The PDF to render. `marks` has one entry per page: None, or (QColor, label or None). `legend` rows are (QColor, text)."""

    path: str
    marks: list = field(default_factory=list)
    legend: list = field(default_factory=list)


def _sibling_path(input_path: str, tag: str) -> str:
    path = Path(input_path)
    return str(path.with_name(f"{path.stem}-{tag}.pdf"))


class BasePdfPanel(QWidget):
    INPUT_LABEL = "Input PDF:"
    RUN_TEXT = "Run"
    OUTPUT_IS_FOLDER = False
    HAS_RESULT_VIEW = False

    preview_requested = Signal(object)
    toggle_changed = Signal(bool, bool, str)
    input_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.latest_request: PreviewRequest | None = None
        self._params: dict | None = None
        self._run_params: dict | None = None
        self._run_output: list[str] = []
        self._run_dir: str | None = None
        self._view = "original"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.input_group = QGroupBox("Input")
        self.input_layout = QVBoxLayout(self.input_group)
        self.input_edit = self.add_input_picker(self.INPUT_LABEL)
        layout.addWidget(self.input_group)

        self.options_group = QGroupBox("Options")
        self.options_layout = QFormLayout(self.options_group)
        layout.addWidget(self.options_group)

        self.run_btn = QPushButton(self.RUN_TEXT)
        self.run_btn.clicked.connect(self._run)
        layout.addWidget(self.run_btn)

        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        output_row = QHBoxLayout()
        self.output_edit = QLineEdit()
        output_row.addWidget(self.output_edit)
        choose_btn = QPushButton("Choose…")
        choose_btn.clicked.connect(self._choose_output)
        output_row.addWidget(choose_btn)
        output_layout.addLayout(output_row)
        self.save_btn = QPushButton("Save")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save)
        output_layout.addWidget(self.save_btn)
        layout.addWidget(output_group)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    # --- subclass interface -------------------------------------------------

    def options(self) -> dict:
        """The tool's own inputs and options, beyond the shared input PDF."""
        return {}

    def default_output(self, params: dict) -> str:
        raise NotImplementedError

    def run_job(self, temp_dir: str, params: dict, on_progress) -> list[str]:
        """Runs off the GUI thread: write into `temp_dir`, return the written files."""
        raise NotImplementedError

    def preview_job(self, request: PreviewRequest) -> PreviewDoc:
        """Runs off the GUI thread."""
        return PreviewDoc(request.params["input"])

    def on_preview_shown(self, doc: PreviewDoc) -> None:
        pass

    # --- inputs ---------------------------------------------------------------

    def params(self) -> dict:
        """Snapshot of inputs and options; "input" is the shared input PDF."""
        return {"input": self.input_edit.text().strip(), **self.options()}

    def add_input_picker(self, label: str) -> QLineEdit:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        edit = QLineEdit()
        edit.editingFinished.connect(self._on_inputs_changed)
        row.addWidget(edit)
        btn = QPushButton("Choose…")
        btn.clicked.connect(lambda: self._pick_input(edit))
        row.addWidget(btn)
        self.input_layout.addLayout(row)
        return edit

    def _pick_input(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose PDF", os.path.dirname(edit.text()), PDF_FILTER)
        if path:
            edit.setText(path)
            self._on_inputs_changed()

    def set_input(self, path: str) -> None:
        self.input_edit.setText(path)
        self._on_inputs_changed()

    def _on_inputs_changed(self) -> None:
        params = self.params()
        if params == self._params:
            return
        input_changed = self._params is None or params["input"] != self._params["input"]
        self._params = params
        self._clear_run_output()
        self.output_edit.setPlaceholderText(self.default_output(params) if params["input"] else "")
        self.request_preview()
        if input_changed:
            self.input_changed.emit(params["input"])

    # --- preview --------------------------------------------------------------

    def request_preview(self) -> None:
        params = self.params()
        if params["input"]:
            self.latest_request = PreviewRequest(params, self._view, list(self._run_output))
        else:
            self.latest_request = None
        self.preview_requested.emit(self.latest_request)

    def toggle_state(self) -> tuple[bool, bool, str]:
        return self.HAS_RESULT_VIEW, bool(self._run_output), self._view

    def set_view(self, view: str) -> None:
        self._view = view
        self.request_preview()

    # --- run ------------------------------------------------------------------

    def _clear_run_output(self) -> None:
        self._run_output = []
        self.save_btn.setEnabled(False)
        self._view = "original"
        self.toggle_changed.emit(*self.toggle_state())

    def _run(self) -> None:
        self._on_inputs_changed()
        params = self.params()
        if not params["input"]:
            self._set_status("Choose an input PDF first.", error=True)
            return
        self._clear_run_output()
        # Only a result view depends on the run output; other previews stay as they are.
        if self.HAS_RESULT_VIEW:
            self.request_preview()
        if self._run_dir:
            shutil.rmtree(self._run_dir, ignore_errors=True)
        self._run_dir = session_temp_dir()
        self._run_params = params
        self._set_busy(True)
        self._set_status("Running…")
        worker = Worker(self.run_job, self._run_dir, params)
        # Bound methods, not lambdas: a lambda's queued call is dropped once the
        # finished worker's signals object is destroyed.
        worker.signals.progress.connect(self._set_status)
        worker.signals.result.connect(self._on_run_done)
        worker.signals.error.connect(self._on_run_error)
        QThreadPool.globalInstance().start(worker)

    def _on_run_done(self, paths: list[str]) -> None:
        self._set_busy(False)
        # The shared input can change while this panel runs (picked in another tool).
        if self.params() != self._run_params:
            self._set_status("The input changed during the run — run again.")
            return
        self._run_output = paths
        self.save_btn.setEnabled(True)
        self._set_status("Done — click Save to keep the result.")
        self.toggle_changed.emit(*self.toggle_state())
        if self.HAS_RESULT_VIEW:
            self.request_preview()

    def _on_run_error(self, message: str) -> None:
        self._set_busy(False)
        self._set_status(message, error=True)

    def _set_busy(self, busy: bool) -> None:
        for widget in (self.input_group, self.options_group, self.run_btn):
            widget.setEnabled(not busy)
        if busy:
            self.save_btn.setEnabled(False)

    def _set_status(self, text: str, error: bool = False) -> None:
        self.status_label.setStyleSheet(ERROR_STYLE if error else "")
        self.status_label.setText(text)

    # --- output ---------------------------------------------------------------

    def _target(self) -> str:
        return self.output_edit.text().strip() or self.output_edit.placeholderText()

    def _choose_output(self) -> None:
        start = self._target()
        if self.OUTPUT_IS_FOLDER:
            path = QFileDialog.getExistingDirectory(self, "Choose Output Folder", os.path.dirname(start))
        else:
            path, _ = QFileDialog.getSaveFileName(self, "Save As", start, PDF_FILTER)
        if path:
            self.output_edit.setText(path)

    def _save(self) -> None:
        target = self._target()
        if not self._run_output or not target:
            return
        if self.OUTPUT_IS_FOLDER:
            copies = [(src, os.path.join(target, os.path.basename(src))) for src in self._run_output]
        else:
            src = self._run_output[0]
            if os.path.isdir(target):
                target = os.path.join(target, os.path.basename(src))
            copies = [(src, target)]
        existing = [dst for _src, dst in copies if os.path.exists(dst)]
        if existing:
            answer = QMessageBox.question(
                self, "Overwrite?",
                f"{len(existing)} file(s) already exist, e.g. {existing[0]}. Overwrite?",
            )
            if answer != QMessageBox.Yes:
                self._set_status("Not saved.")
                return
        try:
            os.makedirs(target if self.OUTPUT_IS_FOLDER else os.path.dirname(os.path.abspath(target)), exist_ok=True)
            for src, dst in copies:
                shutil.copy2(src, dst)
        except OSError as e:
            self._set_status(str(e), error=True)
            return
        self._set_status(f"Saved to {target}")
