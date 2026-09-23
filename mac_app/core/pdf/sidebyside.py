"""Combine two PDFs horizontally side by side per page, ported from pdf_sidebyside.py.

argparse/CLI scaffolding stripped; combine_pdfs_side_by_side and
open_pdf_preview are already clean, importable functions.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

from pypdf import PageObject, PdfReader, PdfWriter


def combine_pdfs_side_by_side(
    pdf1_path: Path,
    pdf2_path: Path,
    output_path: Path,
    preview_only: bool = False,
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
    page_count = 1 if preview_only else len(reader1.pages)

    for i in range(page_count):
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
        report(f"Merged page {i + 1}/{page_count}")

    with open(output_path, "wb") as f:
        writer.write(f)
    report(f"Done. Output saved to: {output_path}")


def open_pdf_preview(path: Path) -> None:
    """Attempt to open a PDF in the system default viewer."""
    try:
        if sys.platform.startswith("darwin"):
            subprocess.run(["open", path], check=True)
        elif os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", path], check=True)
    except Exception:
        print(f"Could not automatically open preview. Preview file: {Path(path).resolve()}")
