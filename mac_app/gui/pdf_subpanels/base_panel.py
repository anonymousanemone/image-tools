"""Shared PDF sub-panel scaffolding: file pickers, progress log, background runs."""

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..workers import Worker


class BasePdfPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pool = QThreadPool.globalInstance()
        self.layout_ = QVBoxLayout(self)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)

    def add_file_picker(self, label: str, filter_str: str = "PDF Files (*.pdf)") -> QLineEdit:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        edit = QLineEdit()
        row.addWidget(edit)
        btn = QPushButton("Choose…")
        btn.clicked.connect(lambda: self._pick_file(edit, filter_str))
        row.addWidget(btn)
        self.layout_.addLayout(row)
        return edit

    def add_save_picker(self, label: str, default_name: str, filter_str: str = "PDF Files (*.pdf)") -> QLineEdit:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        edit = QLineEdit()
        row.addWidget(edit)
        btn = QPushButton("Choose…")
        btn.clicked.connect(lambda: self._pick_save(edit, default_name, filter_str))
        row.addWidget(btn)
        self.layout_.addLayout(row)
        return edit

    def add_dir_picker(self, label: str) -> QLineEdit:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        edit = QLineEdit()
        row.addWidget(edit)
        btn = QPushButton("Choose…")
        btn.clicked.connect(lambda: self._pick_dir(edit))
        row.addWidget(btn)
        self.layout_.addLayout(row)
        return edit

    def _pick_file(self, edit: QLineEdit, filter_str: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose File", "", filter_str)
        if path:
            edit.setText(path)

    def _pick_save(self, edit: QLineEdit, default_name: str, filter_str: str) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save As", default_name, filter_str)
        if path:
            edit.setText(path)

    def _pick_dir(self, edit: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose Folder")
        if path:
            edit.setText(path)

    def run_in_background(self, fn, *args, **kwargs) -> None:
        self.log.clear()
        worker = Worker(fn, *args, **kwargs)
        worker.signals.progress.connect(self.log.appendPlainText)
        # A bound method, not a lambda: a lambda's queued call is dropped once the
        # finished worker's signals object is destroyed.
        worker.signals.error.connect(self._log_error)
        self._pool.start(worker)

    def _log_error(self, msg: str) -> None:
        self.log.appendPlainText(f"ERROR: {msg}")
