"""Pixel Colors & Colormap tab: exact-hex remap (Section A) + ImageMagick palette map (Section B)."""

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.colormap_magick import magick_available, run_image_map
from core.image_io import normalize_mode
from core.pixel_colors import (
    LARGE_PALETTE_WARNING_THRESHOLD,
    apply_color_mapping,
    get_colors_from_image,
    hex_to_rgba,
    is_valid_hex_color,
)

from .color_picker_cell import ColorPickerCell
from .image_open import open_image_dialog
from .image_preview import ImagePreviewWidget
from .image_state import ImageState
from .shared_toolbar import SharedImageToolbar


class PixelColorsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_state = ImageState()

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

        # Section A: exact-hex color remap
        remap_group = QGroupBox("Pixel Color Remap")
        remap_layout = QVBoxLayout(remap_group)
        remap_layout.setSpacing(4)

        load_colors_btn = QPushButton("Load Colors")
        load_colors_btn.clicked.connect(self._load_colors)
        remap_layout.addWidget(load_colors_btn)

        self.mapping_table = QTableWidget(0, 2)
        self.mapping_table.setHorizontalHeaderLabels(["From", "To (blank = keep)"])
        self.mapping_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        remap_layout.addWidget(self.mapping_table)

        apply_map_btn = QPushButton("Apply Mapping")
        apply_map_btn.clicked.connect(self._apply_mapping)
        remap_layout.addWidget(apply_map_btn)

        undo_map_btn = QPushButton("Undo Mapping")
        undo_map_btn.clicked.connect(self._undo_mapping)
        remap_layout.addWidget(undo_map_btn)

        controls.addWidget(remap_group)

        # Section B: ImageMagick colormap
        colormap_group = QGroupBox("Colormap (ImageMagick)")
        colormap_layout = QVBoxLayout(colormap_group)
        colormap_layout.setSpacing(4)

        self.palette_path_edit = QLineEdit()
        self.palette_path_edit.setPlaceholderText("Palette / reference image…")
        pick_palette_btn = QPushButton("Choose Palette Image…")
        pick_palette_btn.clicked.connect(self._choose_palette)
        colormap_layout.addWidget(self.palette_path_edit)
        colormap_layout.addWidget(pick_palette_btn)

        self.run_colormap_btn = QPushButton("Run Colormap")
        self.run_colormap_btn.clicked.connect(self._run_colormap)
        colormap_layout.addWidget(self.run_colormap_btn)

        self.colormap_status = QLabel()
        if not magick_available():
            self.run_colormap_btn.setEnabled(False)
            self.colormap_status.setText("ImageMagick not found — install with: brew install imagemagick")
        colormap_layout.addWidget(self.colormap_status)

        controls.addWidget(colormap_group)

        self.toolbar = SharedImageToolbar(self.image_state)
        controls.addWidget(self.toolbar)

        controls.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(controls_widget)
        scroll.setMinimumWidth(240)
        splitter.addWidget(scroll)

        self.preview = ImagePreviewWidget(self.image_state, pixel_perfect=True)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([340, 860])

        root.addWidget(splitter)

    def _open_image(self) -> None:
        result = open_image_dialog(self)
        if result:
            image, path = result
            self.image_state.load(image, source_path=path)

    def _require_image(self):
        image = self.image_state.current_image
        if image is None:
            QMessageBox.warning(self, "No image", "Open an image first.")
            return None
        return image

    def _load_colors(self) -> None:
        image = self._require_image()
        if image is None:
            return
        colors = get_colors_from_image(image)
        if len(colors) > LARGE_PALETTE_WARNING_THRESHOLD:
            QMessageBox.information(
                self,
                "Large palette",
                f"This image has {len(colors)} distinct colors — showing the "
                f"top {LARGE_PALETTE_WARNING_THRESHOLD} most frequent.",
            )
            colors = colors[:LARGE_PALETTE_WARNING_THRESHOLD]

        self.mapping_table.setRowCount(0)
        for hex_code in colors:
            self._add_color_row(hex_code)

    def _add_color_row(self, from_hex: str) -> None:
        row = self.mapping_table.rowCount()
        self.mapping_table.insertRow(row)

        from_item = QTableWidgetItem(from_hex)
        # Frozen: rows come straight from the loaded image's colors, not
        # free text, so the From cell is display-only.
        from_item.setFlags(from_item.flags() & ~Qt.ItemIsEditable)
        if is_valid_hex_color(from_hex):
            # QColor(str) expects Qt's alpha-first "#aarrggbb" for an 8-digit
            # hex, not our "#rrggbbaa" — build it from parsed components
            # instead of handing the string straight to the constructor.
            color = QColor(*hex_to_rgba(from_hex))
            from_item.setBackground(color)
            from_item.setForeground(QColor("black" if color.lightnessF() > 0.5 else "white"))
        self.mapping_table.setItem(row, 0, from_item)

        # "To" is left blank by default — an empty cell means "keep this
        # pixel's original color" when the mapping is applied.
        self.mapping_table.setCellWidget(row, 1, ColorPickerCell())

    def _apply_mapping(self) -> None:
        image = self._require_image()
        if image is None:
            return
        color_map = {}
        invalid_rows = []
        for row in range(self.mapping_table.rowCount()):
            from_item = self.mapping_table.item(row, 0)
            to_cell = self.mapping_table.cellWidget(row, 1)
            from_hex = from_item.text().strip() if from_item else ""
            to_hex = to_cell.hex_text() if to_cell else ""

            if not from_hex or not to_hex:
                continue  # blank "to" (or no "from") -> leave this color unchanged
            if not is_valid_hex_color(from_hex) or not is_valid_hex_color(to_hex):
                invalid_rows.append(row + 1)
                continue
            color_map[from_hex] = to_hex

        if invalid_rows:
            QMessageBox.warning(
                self,
                "Invalid hex color",
                "Skipped row(s) with an invalid hex color: " + ", ".join(map(str, invalid_rows)),
            )
        if not color_map:
            QMessageBox.warning(self, "No mapping", "Enter at least one replacement color.")
            return
        try:
            result = apply_color_mapping(image, color_map)
        except Exception as e:
            QMessageBox.warning(self, "Mapping failed", str(e))
            return
        self.image_state.push(result)

    def _undo_mapping(self) -> None:
        self.image_state.undo()
        for row in range(self.mapping_table.rowCount()):
            to_cell = self.mapping_table.cellWidget(row, 1)
            if to_cell is not None:
                to_cell.clear()

    def _choose_palette(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Palette Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if path:
            self.palette_path_edit.setText(path)

    def _run_colormap(self) -> None:
        image = self._require_image()
        if image is None:
            return
        palette_path = self.palette_path_edit.text().strip()
        if not palette_path:
            QMessageBox.warning(self, "No palette", "Choose a palette image first.")
            return

        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.png"
            output_path = Path(tmp) / "output.png"
            image.save(input_path)
            try:
                run_image_map(input_path, palette_path, output_path)
            except Exception as e:
                QMessageBox.warning(self, "Colormap failed", str(e))
                return
            self.image_state.push(normalize_mode(Image.open(output_path)))
