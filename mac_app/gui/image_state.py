"""Per-tab working-image state: original (unedited) image, current working image,
linear undo stack, change signal."""

from PIL import Image
from PySide6.QtCore import QObject, Signal

from core.vectorize import VectorTrace


class ImageState(QObject):
    image_changed = Signal()

    def __init__(self):
        super().__init__()
        self._current: Image.Image | None = None
        self._original: Image.Image | None = None
        self._undo_stack: list[Image.Image] = []
        self.source_path: str | None = None

    @property
    def current_image(self) -> Image.Image | None:
        return self._current

    @property
    def original_image(self) -> Image.Image | None:
        """The unedited image as loaded, unaffected by any filters/edits since."""
        return self._original

    def load(self, image: Image.Image, source_path: str | None = None) -> None:
        self._current = image
        self._original = image.copy()
        self._undo_stack = []
        self.source_path = source_path
        self.image_changed.emit()

    def push(self, image: Image.Image) -> None:
        """Apply a new processed image, keeping the previous one for undo."""
        if self._current is not None:
            self._undo_stack.append(self._current)
        self._current = image
        self.image_changed.emit()

    def reset_to_original(self) -> None:
        """Discard the current working image (and undo history), reverting to the unedited original."""
        if self._original is None:
            return
        self._current = self._original.copy()
        self._undo_stack = []
        self.image_changed.emit()

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        self._current = self._undo_stack.pop()
        self.image_changed.emit()
        return True

    def has_alpha(self) -> bool:
        return self._current is not None and self._current.mode == "RGBA"


class VectorState:
    """Holds the most recent Vectorize result for a tab, if any. Plain
    (non-Qt-signal) holder: the trace is read on demand (preview refresh,
    download) rather than reacted to."""

    def __init__(self):
        self.trace: VectorTrace | None = None
