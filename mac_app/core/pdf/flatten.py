"""Strip a PDF's text layer by rasterizing every page (port of pdf_flatten.py)."""

import io
import os
from typing import Callable, Optional

import pymupdf as fitz

from core.image_io import PYMUPDF_LOCK, render_pdf_pages


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

    with PYMUPDF_LOCK:
        out_doc = fitz.open()

    report("Stripping text layer...")

    try:
        for page_num, img in enumerate(render_pdf_pages(input_pdf, dpi / 72), start=1):
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            with PYMUPDF_LOCK:
                pdf_page = out_doc.new_page(width=img.width, height=img.height)
                pdf_page.insert_image(pdf_page.rect, stream=img_bytes.getvalue())
            report(f"Processed page {page_num}")

        with PYMUPDF_LOCK:
            out_doc.save(output_pdf)
    finally:
        with PYMUPDF_LOCK:
            out_doc.close()

    report(f"Done. Output saved to: {output_pdf}")
