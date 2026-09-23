"""Scrollable image preview bound to an ImageState: fits to window by default, zoomable.

Trackpad pinch-to-zoom and Ctrl+scroll-wheel zoom are handled via an event
filter installed on the scroll area's viewport and the image label — a
wheelEvent/event() override on this outer widget would never actually fire,
since the QScrollArea child covers the whole area and receives those events
first.
"""

import subprocess
import tempfile
from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.utils import pil_to_qpixmap
from core.vectorize import build_svg, find_inkscape

from .image_state import ImageState, VectorState

ZOOM_STEP = 1.25
ZOOM_MIN = 0.1
ZOOM_MAX = 8.0


class ImagePreviewWidget(QWidget):
    def __init__(
        self,
        image_state: ImageState,
        parent=None,
        pixel_perfect: bool = False,
        vector_state: VectorState | None = None,
    ):
        super().__init__(parent)
        self.image_state = image_state
        self.vector_state = vector_state
        self._preview_tmp_dir: Path | None = None
        self.image_state.image_changed.connect(self.refresh)
        # Pixel art needs nearest-neighbor scaling (crisp square pixels) rather
        # than the smooth/blurred interpolation used for photographic content.
        self._transform_mode = Qt.FastTransformation if pixel_perfect else Qt.SmoothTransformation

        self._pixmap: QPixmap | None = None
        self._override_pixmap: QPixmap | None = None
        self._zoom = 1.0
        self._fit_to_window = True
        self._panning = False
        self._pan_start_global = None
        self._pan_start_scroll = (0, 0)

        toolbar = QHBoxLayout()
        zoom_out_btn = QPushButton("−")
        zoom_out_btn.setFixedWidth(28)
        zoom_out_btn.clicked.connect(self.zoom_out)
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedWidth(28)
        zoom_in_btn.clicked.connect(self.zoom_in)
        fit_btn = QPushButton("Fit")
        fit_btn.clicked.connect(self.zoom_fit)
        self._zoom_label = QLabel("100%")
        self._zoom_label.setFixedWidth(48)
        self._zoom_label.setAlignment(Qt.AlignCenter)
        preview_btn = QPushButton("See in Preview")
        preview_btn.clicked.connect(self.open_in_native_preview)
        toolbar.addWidget(zoom_out_btn)
        toolbar.addWidget(self._zoom_label)
        toolbar.addWidget(zoom_in_btn)
        toolbar.addWidget(fit_btn)
        toolbar.addWidget(preview_btn)
        toolbar.addStretch()

        self._label = QLabel("No image loaded")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        self._scroll = QScrollArea()
        # widgetResizable=True would make the scroll area keep forcing the
        # label back down to viewport size on every layout pass, silently
        # discarding the larger pixmap set when zoomed in — leaving nothing
        # to actually scroll/pan through. We size the label ourselves in
        # _rescale() instead, so the scroll area can tell when it's bigger
        # than the viewport and enable panning.
        self._scroll.setWidgetResizable(False)
        self._scroll.setAlignment(Qt.AlignCenter)
        self._scroll.setWidget(self._label)

        # Wheel/gesture/mouse events over the image go to the viewport or
        # the label depending on zoom state, not to this outer widget.
        self._scroll.viewport().installEventFilter(self)
        self._label.installEventFilter(self)
        self._scroll.viewport().setCursor(Qt.OpenHandCursor)
        self._label.setCursor(Qt.OpenHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(toolbar)
        layout.addWidget(self._scroll)

    def refresh(self) -> None:
        # Any change to the bound raster (binarize, filter, undo, open a new
        # image) invalidates whatever vector overlay was being shown, since
        # it was traced from a now-superseded image.
        self._override_pixmap = None
        image = self.image_state.current_image
        if image is None:
            self._pixmap = None
            self._label.setText("No image loaded")
            self._label.setPixmap(QPixmap())
            return
        self._pixmap = pil_to_qpixmap(image)
        self._label.setText("")
        self._rescale()

    def show_override(self, pixmap: QPixmap) -> None:
        """Display `pixmap` instead of the bound ImageState's current image
        (used for the Vectorize preview), until the next refresh()."""
        self._override_pixmap = pixmap
        self._label.setText("")
        self._rescale()

    def clear_override(self) -> None:
        if self._override_pixmap is None:
            return
        self._override_pixmap = None
        self._rescale()

    def _rescale(self) -> None:
        pixmap = self._override_pixmap if self._override_pixmap is not None else self._pixmap
        if pixmap is None:
            return
        if self._fit_to_window:
            target = self._scroll.viewport().size()
            if target.width() > 0 and target.height() > 0:
                scaled = pixmap.scaled(target, Qt.KeepAspectRatio, self._transform_mode)
                self._zoom = scaled.width() / pixmap.width() if pixmap.width() else 1.0
            else:
                scaled = pixmap
        else:
            w = max(1, int(pixmap.width() * self._zoom))
            h = max(1, int(pixmap.height() * self._zoom))
            scaled = pixmap.scaled(w, h, Qt.KeepAspectRatio, self._transform_mode)
        self._label.setPixmap(scaled)
        self._label.resize(scaled.size())
        self._zoom_label.setText(f"{round(self._zoom * 100)}%")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._fit_to_window:
            self._rescale()

    def zoom_in(self) -> None:
        self._fit_to_window = False
        self._zoom = min(self._zoom * ZOOM_STEP, ZOOM_MAX)
        self._rescale()

    def zoom_out(self) -> None:
        self._fit_to_window = False
        self._zoom = max(self._zoom / ZOOM_STEP, ZOOM_MIN)
        self._rescale()

    def zoom_fit(self) -> None:
        self._fit_to_window = True
        self._rescale()

    def eventFilter(self, obj, event) -> bool:
        # Trackpad pinch gesture (macOS delivers this as a native gesture,
        # not a QPinchGesture — no grabGesture() call needed).
        if event.type() == QEvent.NativeGesture and event.gestureType() == Qt.ZoomNativeGesture:
            self._fit_to_window = False
            self._zoom = max(ZOOM_MIN, min(ZOOM_MAX, self._zoom * (1.0 + event.value())))
            self._rescale()
            return True
        # Ctrl+scroll-wheel zoom (a plain two-finger scroll is left alone so
        # QScrollArea can pan normally when the image is zoomed in).
        if event.type() == QEvent.Wheel and event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            return True
        # Click-and-drag panning: QScrollArea has no built-in drag-to-pan, so
        # track the drag manually and push it into the scrollbars.
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self._panning = True
            self._pan_start_global = event.globalPosition()
            self._pan_start_scroll = (
                self._scroll.horizontalScrollBar().value(),
                self._scroll.verticalScrollBar().value(),
            )
            self._scroll.viewport().setCursor(Qt.ClosedHandCursor)
            return True
        if event.type() == QEvent.MouseMove and self._panning:
            delta = event.globalPosition() - self._pan_start_global
            h0, v0 = self._pan_start_scroll
            self._scroll.horizontalScrollBar().setValue(round(h0 - delta.x()))
            self._scroll.verticalScrollBar().setValue(round(v0 - delta.y()))
            return True
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton and self._panning:
            self._panning = False
            self._scroll.viewport().setCursor(Qt.OpenHandCursor)
            return True
        return super().eventFilter(obj, event)

    def _preview_tmp_path(self, suffix: str) -> Path:
        # A fixed filename that's overwritten on every open, rather than a
        # fresh one each time — keeps this from littering the temp dir, and
        # a TemporaryDirectory context manager can't be used here since
        # Preview/Inkscape read the file after this call returns.
        if self._preview_tmp_dir is None:
            self._preview_tmp_dir = Path(tempfile.mkdtemp(prefix="image_tools_preview_"))
        return self._preview_tmp_dir / f"preview{suffix}"

    def open_in_native_preview(self) -> None:
        """Open the current image at full resolution in a native app: macOS
        Preview for raster content, or Inkscape when a vector trace is
        showing — Preview can't render arbitrary SVG path data reliably."""
        trace = self.vector_state.trace if self.vector_state is not None else None
        if trace is not None:
            self._open_svg_in_inkscape(trace)
            return
        image = self.image_state.current_image
        if image is None:
            QMessageBox.warning(self, "No image", "Load an image first.")
            return
        path = self._preview_tmp_path(".png")
        image.save(path, format="PNG")
        subprocess.Popen(["open", "-a", "Preview", str(path)])

    def _open_svg_in_inkscape(self, trace) -> None:
        inkscape = find_inkscape()
        if inkscape is None:
            QMessageBox.warning(
                self, "Inkscape not found",
                "Viewing the vector trace requires Inkscape — install it "
                "(https://inkscape.org) and ensure it's on PATH, or at "
                "/Applications/Inkscape.app.",
            )
            return
        svg = build_svg(
            trace.width, trace.height, trace.path_d,
            raster_image=trace.traced_image, raster_visible=False,
            path_fill="black", path_opacity=1.0,
        )
        path = self._preview_tmp_path(".svg")
        path.write_text(svg)
        subprocess.Popen([inkscape, str(path)])
