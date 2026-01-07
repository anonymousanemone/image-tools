"""
Combines two pdfs horizontally side by side for each page.
"""

import sys
from pathlib import Path
from pypdf import PdfReader, PdfWriter, PageObject
import os
import subprocess


# ==========================
# INPUT VALUES
# ==========================
# 1 is on the left, 2 is on the right
HARDCODED_PDF_1 = "/Users/sophial/Downloads/Readings-thesis/carthage/Delattre-LESCIMETIRESROMAINS-1898 en-US.pdf"
HARDCODED_PDF_2 = "/Users/sophial/Downloads/Readings-thesis/carthage/Delattre-LESCIMETIRESROMAINS-1898.pdf"
HARDCODED_RESULT_DIR = None


def parse_args():
    pdf1 = HARDCODED_PDF_1
    pdf2 = HARDCODED_PDF_2
    result_dir = HARDCODED_RESULT_DIR

    if not pdf1 or not pdf2:
        print("Error: Two PDF files must be provided.")
        sys.exit(1)

    pdf1_path = Path(pdf1).resolve()
    pdf2_path = Path(pdf2).resolve()

    if not pdf1_path.exists() or not pdf2_path.exists():
        print("Error: One or both PDF files do not exist.")
        sys.exit(1)

    result_dir_path = (
        Path(result_dir).resolve() if result_dir else pdf1_path.parent
    )

    return pdf1_path, pdf2_path, result_dir_path


def combine_pdfs_side_by_side(
    pdf1_path: Path,
    pdf2_path: Path,
    output_path: Path,
    preview_only: bool = False
):
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
            height=max(height1, height2)
        )

        new_page.merge_page(page1)
        new_page.merge_translated_page(page2, tx=width1, ty=0)

        writer.add_page(new_page)

    with open(output_path, "wb") as f:
        writer.write(f)

def open_pdf_preview(path: Path):
    """Attempt to open a PDF in the system default viewer.
    Falls back to printing the full path if it fails.
    """
    try:
        if sys.platform.startswith("darwin"):  # macOS
            subprocess.run(["open", path], check=True)

        elif os.name == "nt":  # Windows
            os.startfile(path)  # type: ignore[attr-defined]

        else:  # Linux / Unix
            subprocess.run(["xdg-open", path], check=True)

    except Exception:
        print("Could not automatically open preview.")
        print(f"Preview file: {path.resolve()}")

if __name__ == "__main__":
    pdf1_path, pdf2_path, result_dir = parse_args()

    result_dir.mkdir(parents=True, exist_ok=True)

    output_name = pdf1_path.stem + "_combined.pdf"
    preview_name = pdf1_path.stem + "_preview.pdf"

    output_path = result_dir / output_name
    preview_path = result_dir / preview_name

    print(f"Result dir: {result_dir}")
    print("Generating preview (first page only)...")
    combine_pdfs_side_by_side(
        pdf1_path, pdf2_path, preview_path, preview_only=True
    )

    print("Opening preview in your default PDF viewer...")
    open_pdf_preview(preview_path)

    confirm = input("Continue and generate full PDF? [y/N]: ").strip().lower()

    if confirm != "y":
        print("Aborted by user.")
        sys.exit(0)

    print("Generating full combined PDF...")
    combine_pdfs_side_by_side(
        pdf1_path, pdf2_path, output_path, preview_only=False
    )

    print(f"Done. Output written to:\n{output_path}")
