"""Per-tab image state: original, current image, undo stack, change signal."""

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
        """The image as loaded, before any edits."""
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
        """Revert to the original, clearing undo history."""
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


class VectorState:
    """A tab's latest Vectorize result; read on demand, so no signal."""

    def __init__(self):
        self.trace: VectorTrace | None = None
