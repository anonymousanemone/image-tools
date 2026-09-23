"""Shared pytest fixtures: small synthetic images/PDFs generated on the fly
(no binary fixture files checked into the repo)."""

import numpy as np
import pymupdf
import pytest
from PIL import Image


@pytest.fixture
def sample_doc_image() -> np.ndarray:
    """A small synthetic 'document' image (dark text-like strokes on a light background)."""
    img = np.full((120, 160, 3), 235, dtype=np.uint8)
    img[20:30, 10:150] = 30
    img[50:60, 10:100] = 30
    img[80:90, 10:130] = 30
    return img


@pytest.fixture
def sample_rgba_with_alpha() -> np.ndarray:
    img = np.full((80, 80, 4), 255, dtype=np.uint8)
    img[10:70, 10:70] = [50, 60, 70, 255]
    img[0:10, :, 3] = 0
    return img


@pytest.fixture
def pixel_art_image() -> Image.Image:
    """A 4x4-color pixel-art-style RGBA image."""
    arr = np.zeros((8, 8, 3), dtype=np.uint8)
    colors = [(224, 248, 207), (134, 192, 108), (7, 24, 33), (48, 104, 80)]
    for i, color in enumerate(colors):
        r, c = divmod(i, 2)
        arr[r * 4:(r + 1) * 4, c * 4:(c + 1) * 4] = color
    return Image.fromarray(arr, mode="RGB")


@pytest.fixture
def two_page_pdf(tmp_path):
    doc = pymupdf.open()
    for i in range(2):
        page = doc.new_page(width=200, height=300)
        page.insert_text((50, 50), f"Page {i + 1}")
    path = tmp_path / "sample.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)
