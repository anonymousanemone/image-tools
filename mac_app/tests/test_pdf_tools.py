import io
import os

import numpy as np
import pymupdf
import pytest
from PIL import Image
from pypdf import PdfReader

from core.pdf.flatten import strip_text_layer
from core.pdf.resizer import normalize_pdf_width, page_width_changes
from core.pdf.sidebyside import combine_pdfs_side_by_side
from core.pdf.splitter import BYTES_IN_MB, plan_split, split_pdf_by_size
from core.pdf.to_images import pdf_to_images


def test_strip_text_layer_preserves_page_count(two_page_pdf, tmp_path):
    output = str(tmp_path / "flattened.pdf")
    strip_text_layer(two_page_pdf, output, dpi=72)
    reader = PdfReader(output)
    assert len(reader.pages) == 2


def test_strip_text_layer_rasterizes_at_the_requested_dpi(make_pdf, tmp_path):
    output = str(tmp_path / "flattened.pdf")
    strip_text_layer(make_pdf("doc", [144, 288], text=True), output, dpi=144)
    with pymupdf.open(output) as doc:
        assert [page.rect.width for page in doc] == [288, 576]
        assert all(page.get_text() == "" for page in doc)


def test_normalize_pdf_width_matches_reference_page(two_page_pdf, tmp_path):
    output = str(tmp_path / "resized.pdf")
    normalize_pdf_width(two_page_pdf, output_path=output, reference_page_index=0)
    reader = PdfReader(output)
    widths = {round(float(p.mediabox.width), 3) for p in reader.pages}
    assert len(widths) == 1


def test_normalize_pdf_width_scales_pages_with_content(make_pdf, tmp_path):
    mixed = make_pdf("mixed", [200, 400], text=True)

    output = str(tmp_path / "resized.pdf")
    normalize_pdf_width(mixed, output_path=output, reference_page_index=0)
    sizes = [(float(p.mediabox.width), float(p.mediabox.height)) for p in PdfReader(output).pages]
    assert sizes == [(200.0, 300.0), (200.0, 150.0)]


def test_page_width_changes_classifies_against_reference(make_pdf):
    path = make_pdf("mixed", [300, 300, 600, 150])
    assert page_width_changes(path, reference_page_index=0) == [0, 0, -1, 1]


def test_combine_pdfs_side_by_side_sums_widths(two_page_pdf, tmp_path):
    output = str(tmp_path / "combined.pdf")
    combine_pdfs_side_by_side(two_page_pdf, two_page_pdf, output)
    reader = PdfReader(output)
    original = PdfReader(two_page_pdf)
    assert len(reader.pages) == len(original.pages)
    combined_width = float(reader.pages[0].mediabox.width)
    original_width = float(original.pages[0].mediabox.width)
    assert abs(combined_width - 2 * original_width) < 1.0


def test_combine_pdfs_side_by_side_rejects_mismatched_page_counts(two_page_pdf, make_pdf, tmp_path):
    one_pager = make_pdf("one_page", [200])

    try:
        combine_pdfs_side_by_side(two_page_pdf, one_pager, str(tmp_path / "out.pdf"))
        assert False, "expected ValueError for mismatched page counts"
    except ValueError:
        pass


def _noise_pdf(path, noise_sides):
    """One page per entry, each holding an incompressible noise image of that side length."""
    rng = np.random.default_rng(0)
    doc = pymupdf.open()
    for side in noise_sides:
        page = doc.new_page(width=200, height=200)
        buffer = io.BytesIO()
        Image.fromarray(rng.integers(0, 256, (side, side, 3), dtype=np.uint8)).save(buffer, format="PNG")
        page.insert_image(page.rect, stream=buffer.getvalue())
    doc.save(str(path))
    doc.close()
    return str(path)


def test_plan_split_parts_cover_pages_and_match_written_files(tmp_path):
    pdf = _noise_pdf(tmp_path / "doc.pdf", [40] * 6)
    max_mb = 12_000 / BYTES_IN_MB
    parts = plan_split(pdf, max_mb)
    assert len(parts) >= 2
    assert all(pages for pages, _size in parts)
    assert [i for pages, _size in parts for i in pages] == list(range(6))

    outputs = split_pdf_by_size(pdf, max_mb, output_dir=str(tmp_path / "parts"))
    assert [len(PdfReader(p).pages) for p in outputs] == [len(pages) for pages, _size in parts]
    assert [os.path.getsize(p) for p in outputs] == [size for _pages, size in parts]


def test_plan_split_oversized_first_page_is_its_own_part(tmp_path):
    pdf = _noise_pdf(tmp_path / "doc.pdf", [120, 10, 10])
    max_mb = 20_000 / BYTES_IN_MB
    parts = plan_split(pdf, max_mb)
    assert parts[0][0] == [0]
    assert parts[0][1] > max_mb * BYTES_IN_MB
    assert [i for pages, _size in parts[1:] for i in pages] == [1, 2]
    assert all(pages for pages, _size in parts)


def test_split_pdf_by_size_writes_into_output_dir(two_page_pdf, tmp_path):
    output_dir = tmp_path / "parts"
    outputs = split_pdf_by_size(two_page_pdf, max_size_mb=1, output_dir=str(output_dir))
    assert outputs == [str(output_dir / f"sample_{n}.pdf") for n in range(1, len(outputs) + 1)]
    for path in outputs:
        assert os.path.getsize(path) <= 1 * 1024 * 1024


def test_pdf_to_images_creates_one_image_per_page(make_pdf, tmp_path):
    pdf = make_pdf("doc", [144, 288])
    output_dir = str(tmp_path / "images")
    pdf_to_images(pdf, dpi=144, output_dir=output_dir)
    assert sorted(os.listdir(output_dir)) == ["page_0001.jpeg", "page_0002.jpeg"]
    widths = [Image.open(os.path.join(output_dir, name)).width for name in sorted(os.listdir(output_dir))]
    assert widths == [288, 576]


def test_pdf_to_images_raises_when_a_page_fails(two_page_pdf, tmp_path, monkeypatch):
    def failing_pages(path, scale):
        yield Image.new("RGB", (10, 10))
        raise RuntimeError("page 2 failed")

    monkeypatch.setattr("core.pdf.to_images.render_pdf_pages", failing_pages)
    with pytest.raises(RuntimeError):
        pdf_to_images(two_page_pdf, dpi=72, output_dir=str(tmp_path / "images"))
