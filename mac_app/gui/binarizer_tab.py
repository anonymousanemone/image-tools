"""Binarizer tab: 12 doxapy algorithms (+ Compare All), filter toolbox, Vision background removal.

Binarize always runs on the original, unedited image (never on top of
whatever filters happen to be currently applied) — changing the algorithm
dropdown discards any filters applied since the last binarize, since a new
algorithm choice means starting over from the source image.
"""

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.binarize import ALGORITHMS, binarize_array, render_algorithm_grid, threshold_array
from core.filters import FILTERS
from core.segment import remove_background, vision_available
from core.utils import cv2_to_pil, pil_to_cv2, svg_to_qpixmap
from core.vectorize import PAD_PX, build_svg, inkscape_available, trace_image

from .image_open import open_image_dialog
from .image_preview import ImagePreviewWidget
from .image_state import ImageState, VectorState
from .shared_toolbar import SharedImageToolbar

COMPARE_ALL = "Compare All"
THRESHOLD = "THRESHOLD"


class BinarizerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_state = ImageState()
        self.vector_state = VectorState()
        self._is_binarized = False
        self.image_state.image_changed.connect(self._on_raster_changed)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        controls_widget = QWidget()
        controls = QVBoxLayout(controls_widget)
        controls.setSpacing(8)
        controls.setContentsMargins(8, 8, 8, 8)

        open_btn = QPushButton("Open Image…")
        open_btn.clicked.connect(self._open_image)
        controls.addWidget(open_btn)

        # Binarization controls
        bin_group = QGroupBox("Binarize")
        bin_layout = QVBoxLayout(bin_group)
        bin_layout.setSpacing(4)

        self.algo_combo = QComboBox()
        self.algo_combo.addItems([COMPARE_ALL, THRESHOLD, *ALGORITHMS])
        self.algo_combo.setCurrentIndex(0)
        bin_layout.addWidget(self.algo_combo)

        self.threshold_row_widget = QWidget()
        threshold_row = QHBoxLayout(self.threshold_row_widget)
        threshold_row.setContentsMargins(0, 0, 0, 0)
        threshold_row.addWidget(QLabel("Threshold:"))
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(0, 255)
        self.threshold_slider.setValue(127)
        self.threshold_value_label = QLabel("127")
        self.threshold_value_label.setFixedWidth(30)
        self.threshold_slider.valueChanged.connect(
            lambda v: self.threshold_value_label.setText(str(v))
        )
        threshold_row.addWidget(self.threshold_slider)
        threshold_row.addWidget(self.threshold_value_label)
        self.threshold_row_widget.setVisible(False)
        bin_layout.addWidget(self.threshold_row_widget)

        self.thicken_check = QCheckBox("Thicken lines (erode)")
        bin_layout.addWidget(self.thicken_check)

        self.transparent_check = QCheckBox("Transparent background (white → alpha 0)")
        bin_layout.addWidget(self.transparent_check)

        binarize_btn = QPushButton("Binarize")
        binarize_btn.clicked.connect(self._binarize)
        bin_layout.addWidget(binarize_btn)

        controls.addWidget(bin_group)

        # Changing the algorithm cancels any filters applied on top of the
        # previous result — connected after initial setup so it doesn't fire
        # during construction.
        self.algo_combo.currentIndexChanged.connect(self._on_algo_changed)

        # Remove background
        seg_group = QGroupBox("Background Removal")
        seg_layout = QVBoxLayout(seg_group)
        seg_layout.setSpacing(4)
        self.remove_bg_btn = QPushButton("Remove Background (macOS Vision)")
        self.remove_bg_btn.clicked.connect(self._remove_background)
        if not vision_available():
            self.remove_bg_btn.setEnabled(False)
            self.remove_bg_btn.setToolTip(
                "Requires macOS 13+ with pyobjc-framework-Vision/-Quartz/-Cocoa installed."
            )
        seg_layout.addWidget(self.remove_bg_btn)
        controls.addWidget(seg_group)

        # Filter toolbox — compact grid: label | param | apply
        filter_group = QGroupBox("Filters")
        grid = QGridLayout(filter_group)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(3)
        for row, (name, func) in enumerate(FILTERS.items()):
            grid.addWidget(QLabel(name), row, 0)
            spin = None
            if name != "Find Contour":
                spin = QSpinBox()
                spin.setRange(1, 99)
                spin.setValue(5)
                spin.setFixedWidth(52)
                grid.addWidget(spin, row, 1)
            apply_btn = QPushButton("Apply")
            apply_btn.setFixedWidth(56)
            apply_btn.clicked.connect(lambda _, f=func, s=spin: self._apply_filter(f, s))
            grid.addWidget(apply_btn, row, 2)
        controls.addWidget(filter_group)

        # Vectorize — shells out to Inkscape's object-trace + path-simplify
        # actions (ported from img_vectorize2.py), not potrace directly, so
        # the whole panel is disabled when Inkscape isn't found.
        vec_group = QGroupBox("Vectorize (requires Inkscape)")
        vec_layout = QVBoxLayout(vec_group)
        vec_layout.setSpacing(4)

        scans_row = QHBoxLayout()
        scans_row.addWidget(QLabel("Scans:"))
        self.vec_scans_spin = QSpinBox()
        self.vec_scans_spin.setRange(2, 256)
        self.vec_scans_spin.setValue(2)
        scans_row.addWidget(self.vec_scans_spin)
        vec_layout.addLayout(scans_row)

        self.vec_smooth_scans_check = QCheckBox("Smooth scans")
        self.vec_smooth_scans_check.setChecked(False)
        vec_layout.addWidget(self.vec_smooth_scans_check)

        self.vec_stack_check = QCheckBox("Stack scans")
        self.vec_stack_check.setChecked(True)
        vec_layout.addWidget(self.vec_stack_check)

        self.vec_remove_bg_check = QCheckBox("Remove background")
        self.vec_remove_bg_check.setChecked(True)
        vec_layout.addWidget(self.vec_remove_bg_check)

        speckles_row = QHBoxLayout()
        speckles_row.addWidget(QLabel("Suppress speckles (px²):"))
        self.vec_speckles_spin = QSpinBox()
        self.vec_speckles_spin.setRange(0, 1000)
        self.vec_speckles_spin.setValue(2)
        speckles_row.addWidget(self.vec_speckles_spin)
        vec_layout.addLayout(speckles_row)

        smooth_row = QHBoxLayout()
        smooth_row.addWidget(QLabel("Smooth corners:"))
        self.vec_smooth_corners_spin = QDoubleSpinBox()
        self.vec_smooth_corners_spin.setRange(0.0, 1.34)
        self.vec_smooth_corners_spin.setSingleStep(0.01)
        self.vec_smooth_corners_spin.setDecimals(2)
        self.vec_smooth_corners_spin.setValue(1.0)
        smooth_row.addWidget(self.vec_smooth_corners_spin)
        vec_layout.addLayout(smooth_row)

        optimize_row = QHBoxLayout()
        optimize_row.addWidget(QLabel("Optimize tolerance:"))
        self.vec_optimize_spin = QDoubleSpinBox()
        self.vec_optimize_spin.setRange(0.0, 5.0)
        self.vec_optimize_spin.setSingleStep(0.05)
        self.vec_optimize_spin.setDecimals(2)
        self.vec_optimize_spin.setValue(0.4)
        optimize_row.addWidget(self.vec_optimize_spin)
        vec_layout.addLayout(optimize_row)

        self.vec_invert_check = QCheckBox("Invert image")
        vec_layout.addWidget(self.vec_invert_check)

        self.vec_pad_check = QCheckBox("Pad background border (avoid edge clipping)")
        vec_layout.addWidget(self.vec_pad_check)

        vectorize_btn = QPushButton("Vectorize")
        vectorize_btn.clicked.connect(self._vectorize)
        vec_layout.addWidget(vectorize_btn)

        self.vec_show_below_check = QCheckBox("Show image below vector")
        self.vec_show_below_check.toggled.connect(self._update_vector_preview)
        vec_layout.addWidget(self.vec_show_below_check)

        if not inkscape_available():
            vec_group.setEnabled(False)
            vec_group.setToolTip(
                "Requires Inkscape (https://inkscape.org) installed and on PATH, "
                "or at /Applications/Inkscape.app."
            )

        controls.addWidget(vec_group)

        undo_btn = QPushButton("Undo")
        undo_btn.clicked.connect(self.image_state.undo)
        controls.addWidget(undo_btn)

        self.toolbar = SharedImageToolbar(self.image_state, vector_state=self.vector_state)
        controls.addWidget(self.toolbar)

        controls.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(controls_widget)
        scroll.setMinimumWidth(200)
        splitter.addWidget(scroll)

        self.preview = ImagePreviewWidget(self.image_state, vector_state=self.vector_state)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 900])

        root.addWidget(splitter)

    def _open_image(self) -> None:
        result = open_image_dialog(self)
        if result:
            image, path = result
            self._is_binarized = False
            self.image_state.load(image, source_path=path)

    def _require_original(self):
        original = self.image_state.original_image
        if original is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return None
        return original

    def _binarize(self) -> None:
        original = self._require_original()
        if original is None:
            return
        algo = self.algo_combo.currentText()
        if algo == COMPARE_ALL:
            self._compare_all(original)
            return
        self._run_binarize(original, algo)

    def _run_binarize(self, original: Image.Image, algo: str) -> None:
        cv_img = pil_to_cv2(original)
        if algo == THRESHOLD:
            result = threshold_array(
                cv_img,
                thresh=self.threshold_slider.value(),
                thicken_lines=self.thicken_check.isChecked(),
                transparent=self.transparent_check.isChecked(),
            )
        else:
            result = binarize_array(
                cv_img,
                func=algo,
                thicken_lines=self.thicken_check.isChecked(),
                transparent=self.transparent_check.isChecked(),
            )
        # Binarize always starts from the original image — discard any
        # filters applied since, then apply the fresh result.
        self.image_state.reset_to_original()
        self.image_state.push(cv2_to_pil(result))
        self._is_binarized = True

    def _compare_all(self, original: Image.Image) -> None:
        """Show all 12 algorithms tiled in one labeled grid, directly in the
        main preview (like the notebook's plot_all_binarize), not a popup."""
        cv_img = pil_to_cv2(original)
        grid = render_algorithm_grid(cv_img)
        self.image_state.reset_to_original()
        self.image_state.push(cv2_to_pil(grid))
        self._is_binarized = False

    def _on_algo_changed(self, _index: int) -> None:
        self.threshold_row_widget.setVisible(self.algo_combo.currentText() == THRESHOLD)
        if self.image_state.original_image is not None:
            self.image_state.reset_to_original()
            self._is_binarized = False

    def _remove_background(self) -> None:
        image = self.image_state.current_image
        if image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        try:
            result = remove_background(pil_to_cv2(image))
        except Exception as e:
            QMessageBox.warning(self, "Remove Background failed", str(e))
            return
        self.image_state.push(cv2_to_pil(result))

    def _apply_filter(self, func, spin: QSpinBox | None) -> None:
        image = self.image_state.current_image
        if image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        cv_img = pil_to_cv2(image)
        try:
            result = func(cv_img, spin.value()) if spin is not None else func(cv_img)
        except Exception as e:
            QMessageBox.warning(self, "Filter failed", str(e))
            return
        self.image_state.push(cv2_to_pil(result))

    def _on_raster_changed(self) -> None:
        """Any raster edit (binarize, filter, undo, open) invalidates the
        current trace — it was drawn from an image that's no longer current."""
        self.vector_state.trace = None
        if self.vec_show_below_check.isChecked():
            self.vec_show_below_check.blockSignals(True)
            self.vec_show_below_check.setChecked(False)
            self.vec_show_below_check.blockSignals(False)

    def _vectorize(self) -> None:
        if not self._is_binarized:
            QMessageBox.warning(
                self, "Not binarized",
                "Vectorizing isn't available until the image has been binarized.",
            )
            return
        image = self.image_state.current_image
        if image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return
        trace_params = ",".join([
            str(self.vec_scans_spin.value()),
            "true" if self.vec_smooth_scans_check.isChecked() else "false",
            "true" if self.vec_stack_check.isChecked() else "false",
            "true" if self.vec_remove_bg_check.isChecked() else "false",
            str(self.vec_speckles_spin.value()),
            f"{self.vec_smooth_corners_spin.value():g}",
            f"{self.vec_optimize_spin.value():g}",
        ])
        try:
            trace = trace_image(
                image,
                trace_params=trace_params,
                invert=self.vec_invert_check.isChecked(),
                pad_px=PAD_PX if self.vec_pad_check.isChecked() else 0,
            )
        except Exception as e:
            QMessageBox.warning(self, "Vectorize failed", str(e))
            return
        self.vector_state.trace = trace
        self._update_vector_preview()

    def _update_vector_preview(self) -> None:
        trace = self.vector_state.trace
        if trace is None:
            return
        if self.vec_show_below_check.isChecked():
            svg = build_svg(
                trace.width, trace.height, trace.path_d,
                raster_image=trace.traced_image, raster_visible=True,
                path_fill="red", path_opacity=0.8,
            )
        else:
            svg = build_svg(trace.width, trace.height, trace.path_d, path_fill="black", path_opacity=1.0)
        self.preview.show_override(svg_to_qpixmap(svg, trace.width, trace.height))
