"""Zoom state, the −/%/+/Fit toolbar, and pinch / ⌘+wheel zoom shared by the preview widgets.

A widget mixing this in calls `_init_zoom()`, implements `_apply_zoom()` (which fits when
`_fit_to_window` is set, then calls `_show_zoom()`), and routes its event filter through `_zoom_event()`.
"""

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton

ZOOM_STEP = 1.25
ZOOM_MIN = 0.1
ZOOM_MAX = 8.0


class ZoomMixin:
    def _init_zoom(self) -> QHBoxLayout:
        """Set up the zoom state and return a toolbar row holding the zoom controls."""
        self._zoom = 1.0
        self._fit_to_window = True

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
        toolbar.addWidget(zoom_out_btn)
        toolbar.addWidget(self._zoom_label)
        toolbar.addWidget(zoom_in_btn)
        toolbar.addWidget(fit_btn)
        return toolbar

    def _apply_zoom(self) -> None:
        raise NotImplementedError

    def _show_zoom(self) -> None:
        self._zoom_label.setText(f"{round(self._zoom * 100)}%")

    def zoom_in(self) -> None:
        self._fit_to_window = False
        self._zoom = min(self._zoom * ZOOM_STEP, ZOOM_MAX)
        self._apply_zoom()

    def zoom_out(self) -> None:
        self._fit_to_window = False
        self._zoom = max(self._zoom / ZOOM_STEP, ZOOM_MIN)
        self._apply_zoom()

    def zoom_fit(self) -> None:
        self._fit_to_window = True
        self._apply_zoom()

    def _zoom_event(self, event) -> bool:
        """Handle trackpad pinch and ⌘+wheel; True when the event was a zoom."""
        # Trackpad pinch (a macOS native gesture, no grabGesture() needed).
        if event.type() == QEvent.NativeGesture and event.gestureType() == Qt.ZoomNativeGesture:
            self._fit_to_window = False
            self._zoom = max(ZOOM_MIN, min(ZOOM_MAX, self._zoom * (1.0 + event.value())))
            self._apply_zoom()
            return True
        # ⌘+wheel zooms (Qt's ControlModifier is Command on macOS); a plain wheel falls through and scrolls.
        if event.type() == QEvent.Wheel and event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            return True
        return False
