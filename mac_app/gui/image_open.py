"""Shared "Open Image…" dialog, used by every tab that loads a source image."""

from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from core.image_io import OPEN_FILE_FILTER, open_image_any, pdf_page_count


def open_image_dialog(parent: QWidget) -> tuple[Image.Image, str] | None:
    """Show an Open Image dialog and load the chosen file.

    Returns (image, path) on success, or None if the user cancelled or the
    file couldn't be opened (a warning is shown to the user in that case).
    """
    path, _ = QFileDialog.getOpenFileName(parent, "Open Image", "", OPEN_FILE_FILTER)
    if not path:
        return None
    try:
        if Path(path).suffix.lower() == ".pdf" and pdf_page_count(path) > 1:
            QMessageBox.information(
                parent,
                "Multi-page PDF",
                "This PDF has multiple pages — only the first page will be loaded.\n"
                "Use the PDF Tools tab to work with all pages.",
            )
        image = open_image_any(path)
    except Exception as e:
        QMessageBox.warning(parent, "Couldn't open file", f"{Path(path).name}:\n{e}")
        return None
    return image, path
