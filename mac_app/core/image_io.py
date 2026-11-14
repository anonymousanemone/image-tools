"""Open any image the GUI accepts (incl. HEIC/HEIF and PDF pages) as plain RGB/RGBA.

Normalizing the mode up front keeps pil_to_cv2 from misreading P, LA or CMYK images.
"""

from pathlib import Path

import pymupdf
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()

PDF_EXTENSIONS = {".pdf"}

OPEN_FILE_FILTER = (
    "Images (*.png *.jpg *.jpeg *.jfif *.bmp *.tif *.tiff *.webp *.gif "
    "*.heic *.heif *.pdf);;All Files (*)"
)


def normalize_mode(image: Image.Image) -> Image.Image:
    """Collapse any PIL mode down to plain RGB or RGBA."""
    if image.mode in ("RGB", "RGBA"):
        return image
    if image.mode in ("P", "LA") or "transparency" in image.info:
        return image.convert("RGBA")
    return image.convert("RGB")


def pdf_page_count(path) -> int:
    doc = pymupdf.open(str(path))
    try:
        return doc.page_count
    finally:
        doc.close()


def load_pdf_page(path, page_index: int = 0, dpi: int = 300) -> Image.Image:
    """Rasterize one PDF page (flattened onto white, like a scanned page)."""
    doc = pymupdf.open(str(path))
    try:
        if page_index >= doc.page_count:
            raise ValueError(f"PDF has no page {page_index + 1}.")
        page = doc.load_page(page_index)
        zoom = dpi / 72
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    finally:
        doc.close()


def open_image_any(path) -> Image.Image:
    """Open a supported file (PDF: first page) as RGB/RGBA, EXIF-rotated."""
    path = Path(path)
    if path.suffix.lower() in PDF_EXTENSIONS:
        return load_pdf_page(path)
    image = Image.open(path)
    image.load()
    image = ImageOps.exif_transpose(image)
    return normalize_mode(image)
