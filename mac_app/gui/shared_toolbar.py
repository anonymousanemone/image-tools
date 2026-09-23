"""Shared utility toolbar embedded in both the Binarizer and Pixel Colors tabs.

Crop Transparent / Make Transparent / Download (PNG, JPG, or SVG) — each acts
on the owning tab's ImageState. Download as SVG offers two variants: the
"wrapper" (unchanged: current raster embedded in an SVG <image>, no real
vector data) and the "vector" one (only offered when a `vector_state` is
passed in, i.e. from the Binarizer tab's Vectorize panel: the traced <path>
plus the raster it was traced from, embedded but hidden).
"""

from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from core.crop_transparent import crop_transparent
from core.svg_export import png_to_svg
from core.transparent_bg import make_white_transparent
from core.utils import pil_to_cv2
from core.vectorize import build_svg

from .image_state import ImageState, VectorState


class ThresholdDialog(QDialog):
    def __init__(self, parent=None, default: int = 250):
        super().__init__(parent)
        self.setWindowTitle("Make Transparent")
        self.value = default

        layout = QVBoxLayout(self)
        self._label = QLabel(f"White threshold: {default}")
        layout.addWidget(self._label)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 255)
        slider.setValue(default)
        slider.valueChanged.connect(self._on_change)
        layout.addWidget(slider)

        buttons = QHBoxLayout()
        ok = QPushButton("Apply")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)

    def _on_change(self, value: int) -> None:
        self.value = value
        self._label.setText(f"White threshold: {value}")


class SharedImageToolbar(QWidget):
    def __init__(self, image_state: ImageState, vector_state: VectorState | None = None, parent=None):
        super().__init__(parent)
        self.image_state = image_state
        self.vector_state = vector_state

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        crop_btn = QPushButton("Crop Transparent")
        crop_btn.clicked.connect(self._crop_transparent)
        top_row.addWidget(crop_btn)

        transparent_btn = QPushButton("Make Transparent…")
        transparent_btn.clicked.connect(self._make_transparent)
        top_row.addWidget(transparent_btn)
        layout.addLayout(top_row)

        bottom_row = QHBoxLayout()
        download_btn = QToolButton()
        download_btn.setText("Download ▾")
        menu = QMenu(download_btn)
        menu.addAction("Download as PNG", self._download_png)
        menu.addAction("Download as JPG", self._download_jpg)
        menu.addAction("Download SVG Wrapper (raster only)", self._download_svg_wrapper)
        if self.vector_state is not None:
            menu.addAction("Download SVG (vector)", self._download_svg_vector)
        download_btn.setMenu(menu)
        download_btn.setPopupMode(QToolButton.InstantPopup)
        bottom_row.addWidget(download_btn)
        bottom_row.addStretch()
        layout.addLayout(bottom_row)

    def _require_image(self):
        image = self.image_state.current_image
        if image is None:
            QMessageBox.warning(self, "No image", "Load an image first.")
            return None
        return image

    def _default_save_path(self, suffix: str) -> str:
        """Same name/location as the source file, with the given extension."""
        source = self.image_state.source_path
        if source:
            return str(Path(source).with_suffix(suffix))
        return f"output{suffix}"

    def _crop_transparent(self) -> None:
        image = self._require_image()
        if image is None:
            return
        cropped = crop_transparent(image)
        if cropped is None:
            QMessageBox.warning(self, "Fully transparent", "Image has no visible content to crop to.")
            return
        self.image_state.push(cropped)

    def _make_transparent(self) -> None:
        image = self._require_image()
        if image is None:
            return
        dialog = ThresholdDialog(self)
        if dialog.exec() == QDialog.Accepted:
            result = make_white_transparent(image, threshold=dialog.value)
            self.image_state.push(result)

    def _download_png(self) -> None:
        image = self._require_image()
        if image is None:
            return
        default = self._default_save_path(".png")
        path, _ = QFileDialog.getSaveFileName(self, "Download as PNG", default, "PNG Files (*.png)")
        if path:
            image.save(path, format="PNG")

    def _download_jpg(self) -> None:
        image = self._require_image()
        if image is None:
            return
        default = self._default_save_path(".jpg")
        path, _ = QFileDialog.getSaveFileName(self, "Download as JPG", default, "JPEG Files (*.jpg *.jpeg)")
        if path:
            to_save = image
            if image.mode == "RGBA":
                # JPEG has no alpha channel — flatten transparency onto white.
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.getchannel("A"))
                to_save = background
            elif image.mode != "RGB":
                to_save = image.convert("RGB")
            to_save.save(path, format="JPEG", quality=95)

    def _download_svg_wrapper(self) -> None:
        image = self._require_image()
        if image is None:
            return
        default = self._default_save_path(".svg")
        path, _ = QFileDialog.getSaveFileName(self, "Download SVG Wrapper", default, "SVG Files (*.svg)")
        if path:
            png_to_svg(pil_to_cv2(image), path)

    def _download_svg_vector(self) -> None:
        trace = self.vector_state.trace if self.vector_state else None
        if trace is None:
            QMessageBox.warning(
                self, "Not vectorized",
                "Click Vectorize in the Vectorize panel first — there's no traced path to download yet.",
            )
            return
        default = self._default_save_path(".svg")
        path, _ = QFileDialog.getSaveFileName(self, "Download SVG (vector)", default, "SVG Files (*.svg)")
        if path:
            svg = build_svg(
                trace.width, trace.height, trace.path_d,
                raster_image=trace.traced_image, raster_visible=False,
                path_fill="black", path_opacity=1.0,
            )
            Path(path).write_text(svg)
