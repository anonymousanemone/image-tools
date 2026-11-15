"""Shared conversion helpers and external-tool availability checks."""

import atexit
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Homebrew bin dirs (Apple Silicon, Intel): a Finder-launched .app lacks the shell's PATH.
_EXTRA_BIN_DIRS = ["/opt/homebrew/bin", "/usr/local/bin"]


def which(binary_name: str) -> str | None:
    found = shutil.which(binary_name)
    if found:
        return found
    for bin_dir in _EXTRA_BIN_DIRS:
        candidate = Path(bin_dir) / binary_name
        if candidate.is_file():
            return str(candidate)
    return None


_session_dir: str | None = None


def session_temp_dir() -> str:
    """A new folder inside this session's temp folder, which is deleted when the app exits."""
    global _session_dir
    if _session_dir is None:
        _session_dir = tempfile.mkdtemp(prefix="image_tools_")
        atexit.register(shutil.rmtree, _session_dir, True)
    return tempfile.mkdtemp(dir=_session_dir)


def pil_to_cv2(image: Image.Image) -> np.ndarray:
    """RGBA/RGB PIL Image -> BGR(A) numpy array (OpenCV convention)."""
    arr = np.array(image)
    if arr.ndim == 2:
        return arr
    if arr.shape[2] == 4:
        return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGRA)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def cv2_to_pil(arr: np.ndarray) -> Image.Image:
    """BGR(A) or grayscale numpy array (OpenCV convention) -> PIL Image."""
    if arr.ndim == 2:
        return Image.fromarray(arr)
    if arr.shape[2] == 4:
        return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGRA2RGBA))
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))


def pil_to_qimage(image: Image.Image) -> QImage:
    """Safe off the GUI thread, unlike pil_to_qpixmap."""
    if image.mode not in ("RGBA", "RGB"):
        image = image.convert("RGBA")
    data = image.tobytes("raw", image.mode)
    fmt = QImage.Format_RGBA8888 if image.mode == "RGBA" else QImage.Format_RGB888
    # Explicit bytesPerLine: RGB888 rows aren't 4-byte aligned, and assuming so shears the image.
    bytes_per_line = image.width * (4 if image.mode == "RGBA" else 3)
    return QImage(data, image.width, image.height, bytes_per_line, fmt).copy()


def pil_to_qpixmap(image: Image.Image) -> QPixmap:
    return QPixmap.fromImage(pil_to_qimage(image))


def svg_to_qpixmap(svg_text: str, width: int, height: int) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    qimage = QImage(width, height, QImage.Format_ARGB32)
    qimage.fill(Qt.transparent)
    painter = QPainter(qimage)
    renderer.render(painter)
    painter.end()
    return QPixmap.fromImage(qimage)
