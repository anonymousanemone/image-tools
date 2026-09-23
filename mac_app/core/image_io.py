"""Robust "open any image" for the GUI's Open Image dialogs.

Two problems this fixes:

1. Pillow can't read HEIC/HEIF at all without a plugin, and can't read PDFs
   as raster images — both raise on Image.open(), which was unhandled in the
   GUI and looked like the app "freaking out".
2. pil_to_cv2() (core/utils.py) only knows how to branch on 2-channel-vs-3-vs-4
   arrays, assuming RGB/RGBA. A palette PNG (mode "P") collapses to a 2D
   array of palette *indices*, and a CMYK JPEG has 4 channels but isn't
   RGBA — both get silently misinterpreted as something else, and "LA" mode
   crashes cv2.cvtColor outright. Normalizing every opened image down to
   plain RGB/RGBA here means downstream code never sees those modes.
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
    """Open any supported file — including HEIC/HEIF and the first page of a
    PDF — normalized to plain RGB/RGBA with EXIF orientation applied."""
    path = Path(path)
    if path.suffix.lower() in PDF_EXTENSIONS:
        return load_pdf_page(path)
    image = Image.open(path)
    image.load()
    image = ImageOps.exif_transpose(image)
    return normalize_mode(image)
