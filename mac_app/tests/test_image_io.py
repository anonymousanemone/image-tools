import pymupdf
from PIL import Image

from core.image_io import load_pdf_page, normalize_mode, open_image_any, pdf_page_count


def test_normalize_mode_converts_palette_to_rgba():
    image = Image.new("P", (10, 10))
    assert normalize_mode(image).mode == "RGBA"


def test_normalize_mode_converts_cmyk_to_rgb():
    image = Image.new("CMYK", (10, 10))
    assert normalize_mode(image).mode == "RGB"


def test_normalize_mode_converts_la_to_rgba():
    image = Image.new("LA", (10, 10))
    assert normalize_mode(image).mode == "RGBA"


def test_normalize_mode_leaves_rgb_and_rgba_unchanged():
    rgb = Image.new("RGB", (10, 10))
    rgba = Image.new("RGBA", (10, 10))
    assert normalize_mode(rgb).mode == "RGB"
    assert normalize_mode(rgba).mode == "RGBA"


def test_open_image_any_normalizes_palette_png(tmp_path):
    path = tmp_path / "palette.png"
    Image.new("P", (10, 10)).save(path)
    image = open_image_any(path)
    assert image.mode in ("RGB", "RGBA")


def test_open_image_any_opens_heic(tmp_path):
    path = tmp_path / "photo.heic"
    Image.new("RGB", (10, 10), (10, 20, 30)).save(path, format="HEIF")
    image = open_image_any(path)
    assert image.size == (10, 10)
    assert image.mode in ("RGB", "RGBA")


def test_open_image_any_reads_first_pdf_page(tmp_path):
    path = tmp_path / "doc.pdf"
    doc = pymupdf.open()
    doc.new_page(width=200, height=100)
    doc.save(str(path))
    doc.close()

    image = open_image_any(path)
    assert image.mode == "RGB"
    assert image.width > 0 and image.height > 0


def test_pdf_page_count(tmp_path):
    path = tmp_path / "two.pdf"
    doc = pymupdf.open()
    doc.new_page(width=200, height=100)
    doc.new_page(width=200, height=100)
    doc.save(str(path))
    doc.close()

    assert pdf_page_count(path) == 2


def test_load_pdf_page_out_of_range_raises(tmp_path):
    path = tmp_path / "one.pdf"
    doc = pymupdf.open()
    doc.new_page(width=200, height=100)
    doc.save(str(path))
    doc.close()

    try:
        load_pdf_page(path, page_index=1)
        assert False, "expected ValueError for out-of-range page"
    except ValueError:
        pass
