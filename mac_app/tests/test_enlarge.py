import numpy as np
from PIL import Image

from core.binarize import binarize_array
from core.enlarge import enlarge_array
from core.utils import pil_to_qpixmap


def test_enlarge_scales_dimensions(sample_doc_image):
    for sharp in (False, True):
        out = enlarge_array(sample_doc_image, 2, sharp=sharp)
        assert out.shape[:2] == (240, 320)


def test_sharp_enlarge_of_binary_stays_binary():
    binary = np.full((40, 40), 255, np.uint8)
    binary[10:14, 5:35] = 0
    out = enlarge_array(binary, 3, sharp=True, binary=True)
    assert out.shape == (120, 120)
    assert set(np.unique(out)) <= {0, 255}
    # line stays roughly 3x as thick
    assert 10 <= (out[:, 60] == 0).sum() <= 14


def test_sharp_enlarge_of_transparent_binary_keeps_alpha_shape():
    rgba = np.zeros((20, 20, 4), np.uint8)
    rgba[5:8, 2:18, 3] = 255
    out = enlarge_array(rgba, 2, sharp=True, binary=True)
    assert out.shape == (40, 40, 4)
    assert set(np.unique(out[:, :, 3])) <= {0, 255}


def test_antialias_adds_intermediate_values(sample_doc_image):
    plain = binarize_array(sample_doc_image, func="OTSU")
    soft = binarize_array(sample_doc_image, func="OTSU", antialias=True)
    assert set(np.unique(plain)) <= {0, 255}
    assert len(np.unique(soft)) > 2


def test_antialias_with_transparent_gives_partial_alpha(sample_doc_image):
    out = binarize_array(sample_doc_image, func="OTSU", antialias=True, transparent=True)
    assert len(np.unique(out[:, :, 3])) > 2


def test_pil_to_qpixmap_rgb_width_not_multiple_of_four():
    from PySide6.QtGui import QGuiApplication

    _app = QGuiApplication.instance() or QGuiApplication([])
    # 5 px wide RGB rows are 15 bytes, not 4-byte aligned: the old conversion
    # sheared these into diagonal ghost copies.
    arr = np.zeros((4, 5, 3), np.uint8)
    arr[:, 0] = (255, 0, 0)
    img = pil_to_qpixmap(Image.fromarray(arr)).toImage()
    for y in range(4):
        assert img.pixelColor(0, y).red() == 255
        assert img.pixelColor(1, y).red() == 0
