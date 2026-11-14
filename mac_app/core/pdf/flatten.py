"""Strip a PDF's text layer by rasterizing every page (port of pdf_flatten.py)."""

import io
import os
from typing import Callable, Optional

import pymupdf as fitz
from PIL import Image


def strip_text_layer(
    input_pdf: str,
    output_pdf: str,
    dpi: int = 300,
    on_progress: Optional[Callable[[str], None]] = None,
) -> None:
    if not os.path.isfile(input_pdf):
        raise FileNotFoundError(input_pdf)

    def report(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    src_doc = fitz.open(input_pdf)
    out_doc = fitz.open()

    zoom = dpi / 72  # PDF default is 72 DPI
    matrix = fitz.Matrix(zoom, zoom)

    report(f"Stripping text layer from {len(src_doc)} pages...")

    for page_num, page in enumerate(src_doc, start=1):
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        pdf_page = out_doc.new_page(width=img.width, height=img.height)

        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        pdf_page.insert_image(pdf_page.rect, stream=img_bytes.read())

        report(f"Processed page {page_num}")

    out_doc.save(output_pdf)
    out_doc.close()
    src_doc.close()

    report(f"Done. Output saved to: {output_pdf}")
