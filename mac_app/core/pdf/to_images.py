"""Convert a PDF's pages to JPEGs, ported from pdf_to_images.py.

Added optional output_dir param (original hardcoded it inside the function).
Requires Poppler (brew install poppler) for pdf2image.
"""

import os
from typing import Callable, Optional

from pdf2image import convert_from_path


def pdf_to_images(
    pdf_path: str,
    dpi: int = 300,
    jpeg_quality: int = 95,
    poppler_path: Optional[str] = None,
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

    page_num = 1
    report("Starting PDF -> image conversion (OCR optimized)...")

    while True:
        try:
            pages = convert_from_path(
                pdf_path,
                dpi=dpi,
                first_page=page_num,
                last_page=page_num,
                poppler_path=poppler_path,
            )
        except Exception as e:
            report(f"Stopping at page {page_num}: {e}")
            break

        if not pages:
            break

        image_path = os.path.join(output_dir, f"page_{page_num:04d}.jpeg")
        pages[0].save(
            image_path,
            "JPEG",
            quality=jpeg_quality,
            subsampling=0,
            optimize=True,
        )

        report(f"Saved page {page_num}")
        page_num += 1

    report(f"Done. Converted {page_num - 1} pages.")
    return output_dir
