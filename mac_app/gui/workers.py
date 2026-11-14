"""Thread-pool worker for long-running PDF operations."""

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    progress = Signal(str)
    error = Signal(str)


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.kwargs["on_progress"] = self.signals.progress.emit

    @Slot()
    def run(self) -> None:
        try:
            self.fn(*self.args, **self.kwargs)
        except Exception as e:
            self.signals.error.emit(str(e))
