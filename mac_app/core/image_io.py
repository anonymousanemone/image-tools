"""Open any image the GUI accepts (incl. HEIC/HEIF and PDF pages) as plain RGB/RGBA.

Also holds the PyMuPDF lock and the whole-document page rendering the PDF tools use.

Normalizing the mode up front keeps pil_to_cv2 from misreading P, LA or CMYK images.
"""

import math
import threading
from collections.abc import Iterator
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()

PDF_EXTENSIONS = {".pdf"}

# PyMuPDF is not thread-safe, even across separate documents: hold this for every call into it.
PYMUPDF_LOCK = threading.Lock()

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
    with PYMUPDF_LOCK, pymupdf.open(str(path)) as doc:
        return doc.page_count


def _render_page(page, scale: float) -> Image.Image:
    pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def load_pdf_page(path, page_index: int = 0, dpi: int = 300) -> Image.Image:
    """Rasterize one PDF page (flattened onto white, like a scanned page)."""
    with PYMUPDF_LOCK, pymupdf.open(str(path)) as doc:
        if page_index >= doc.page_count:
            raise ValueError(f"PDF has no page {page_index + 1}.")
        return _render_page(doc.load_page(page_index), dpi / 72)


def page_sizes(path) -> list[tuple[float, float]]:
    """Each page's (width, height) in points, without rendering."""
    with PYMUPDF_LOCK, pymupdf.open(str(path)) as doc:
        return [(page.rect.width, page.rect.height) for page in doc]


def _rendered_bytes(sizes: list[tuple[float, float]], scale: float) -> int:
    return sum(4 * max(1, math.ceil(w * scale)) * max(1, math.ceil(h * scale)) for w, h in sizes)


def preview_scale(
    sizes: list[tuple[float, float]], max_side: int = 1000, budget_bytes: int = 1 << 30
) -> tuple[float, bool]:
    """One render scale for the whole document, and whether the memory budget lowered it.

    At 4 bytes per pixel, the pages rendered at the returned scale fit in `budget_bytes`, unless even one pixel per longest page side overflows it.
    """
    longest = max(max(w, h) for w, h in sizes)
    area = sum(w * h for w, h in sizes)
    side_scale = max_side / longest
    scale = min(side_scale, math.sqrt(budget_bytes / (4 * area)))
    smallest = 1 / longest
    while scale > smallest and _rendered_bytes(sizes, scale) > budget_bytes:
        scale *= 0.98
    if _rendered_bytes(sizes, scale) > budget_bytes:
        return smallest, True
    return scale, scale < side_scale


def render_pdf_pages(path, scale: float) -> Iterator[Image.Image]:
    """Yield every page at one `scale` (pixels per point), flattened onto white.

    Pages are yielded lazily, so a caller that converts each page keeps only one PIL image alive at a time. The lock
    is held per page, so another thread waits at most one page render.
    """
    with PYMUPDF_LOCK:
        doc = pymupdf.open(str(path))
        page_count = doc.page_count
    try:
        for index in range(page_count):
            with PYMUPDF_LOCK:
                image = _render_page(doc.load_page(index), scale)
            yield image
    finally:
        with PYMUPDF_LOCK:
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
