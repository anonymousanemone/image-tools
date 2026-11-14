"""Combine two equal-length PDFs page by page, side by side (port of pdf_sidebyside.py)."""

from pathlib import Path
from typing import Callable, Optional

from pypdf import PageObject, PdfReader, PdfWriter


def combine_pdfs_side_by_side(
    pdf1_path: Path,
    pdf2_path: Path,
    output_path: Path,
    on_progress: Optional[Callable[[str], None]] = None,
) -> None:
    def report(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    reader1 = PdfReader(pdf1_path)
    reader2 = PdfReader(pdf2_path)
    pages1 = len(reader1.pages)
    pages2 = len(reader2.pages)

    if pages1 != pages2:
        raise ValueError(
            f"Both PDFs must have the same number of pages "
            f"(pdf1: {pages1} pages, pdf2: {pages2} pages)."
        )

    writer = PdfWriter()

    for i in range(pages1):
        page1 = reader1.pages[i]
        page2 = reader2.pages[i]

        width1 = page1.mediabox.width
        height1 = page1.mediabox.height
        width2 = page2.mediabox.width
        height2 = page2.mediabox.height

        new_page = PageObject.create_blank_page(
            width=width1 + width2,
            height=max(height1, height2),
        )

        new_page.merge_page(page1)
        new_page.merge_translated_page(page2, tx=width1, ty=0)

        writer.add_page(new_page)
        report(f"Merged page {i + 1}/{pages1}")

    with open(output_path, "wb") as f:
        writer.write(f)
    report(f"Done. Output saved to: {output_path}")
