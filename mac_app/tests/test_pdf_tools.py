import os

from pypdf import PdfReader

from core.pdf.flatten import strip_text_layer
from core.pdf.resizer import normalize_pdf_width
from core.pdf.sidebyside import combine_pdfs_side_by_side
from core.pdf.splitter import split_pdf_by_size
from core.pdf.to_images import pdf_to_images


def test_strip_text_layer_preserves_page_count(two_page_pdf, tmp_path):
    output = str(tmp_path / "flattened.pdf")
    strip_text_layer(two_page_pdf, output, dpi=72)
    reader = PdfReader(output)
    assert len(reader.pages) == 2


def test_normalize_pdf_width_matches_reference_page(two_page_pdf, tmp_path):
    output = str(tmp_path / "resized.pdf")
    normalize_pdf_width(two_page_pdf, output_path=output, reference_page_index=0)
    reader = PdfReader(output)
    widths = {round(float(p.mediabox.width), 3) for p in reader.pages}
    assert len(widths) == 1


def test_combine_pdfs_side_by_side_sums_widths(two_page_pdf, tmp_path):
    output = str(tmp_path / "combined.pdf")
    combine_pdfs_side_by_side(two_page_pdf, two_page_pdf, output)
    reader = PdfReader(output)
    original = PdfReader(two_page_pdf)
    assert len(reader.pages) == len(original.pages)
    combined_width = float(reader.pages[0].mediabox.width)
    original_width = float(original.pages[0].mediabox.width)
    assert abs(combined_width - 2 * original_width) < 1.0


def test_combine_pdfs_side_by_side_rejects_mismatched_page_counts(two_page_pdf, tmp_path):
    import pymupdf

    one_pager = tmp_path / "one_page.pdf"
    doc = pymupdf.open()
    doc.new_page(width=200, height=300)
    doc.save(str(one_pager))
    doc.close()

    try:
        combine_pdfs_side_by_side(two_page_pdf, str(one_pager), str(tmp_path / "out.pdf"))
        assert False, "expected ValueError for mismatched page counts"
    except ValueError:
        pass


def test_split_pdf_by_size_respects_limit(two_page_pdf, tmp_path):
    outputs = split_pdf_by_size(two_page_pdf, max_size_mb=1)
    assert len(outputs) >= 1
    for path in outputs:
        assert os.path.getsize(path) <= 1 * 1024 * 1024


def test_pdf_to_images_creates_one_image_per_page(two_page_pdf, tmp_path):
    if shutil_which_pdftoppm() is None:
        import pytest

        pytest.skip("Poppler (pdftoppm) not installed")
    output_dir = str(tmp_path / "images")
    pdf_to_images(two_page_pdf, dpi=72, output_dir=output_dir)
    files = [f for f in os.listdir(output_dir) if f.endswith(".jpeg")]
    assert len(files) == 2


def shutil_which_pdftoppm():
    import shutil

    return shutil.which("pdftoppm")
