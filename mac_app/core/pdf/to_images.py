"""Convert a PDF's pages to JPEGs (port of pdf_to_images.py)."""

import os
from typing import Callable, Optional

from core.image_io import render_pdf_pages


def pdf_to_images(
    pdf_path: str,
    dpi: int = 300,
    jpeg_quality: int = 95,
    output_dir: Optional[str] = None,
    on_progress: Optional[Callable[[str], None]] = None,
) -> str:
    def report(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(pdf_path)

    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(pdf_path), pdf_name)
    os.makedirs(output_dir, exist_ok=True)

    report("Starting PDF -> image conversion (OCR optimized)...")

    page_num = 0
    for page_num, image in enumerate(render_pdf_pages(pdf_path, dpi / 72), start=1):
        image_path = os.path.join(output_dir, f"page_{page_num:04d}.jpeg")
        image.save(
            image_path,
            "JPEG",
            quality=jpeg_quality,
            subsampling=0,
            optimize=True,
        )
        report(f"Saved page {page_num}")

    report(f"Done. Converted {page_num} pages.")
    return output_dir
