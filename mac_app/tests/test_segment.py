import numpy as np

from core.segment import find_contour, vision_available


def test_vision_available_is_bool():
    assert isinstance(vision_available(), bool)


def test_find_contour_keeps_largest_blob():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[10:40, 10:40] = 255  # small blob, area ~900
    mask[50:90, 50:90] = 255  # larger blob, area ~1600
    contour_line, filled = find_contour(mask)
    assert filled.shape == mask.shape
    # the small blob should have been dropped, the large one kept
    assert filled[20, 20] == 0
    assert filled[70, 70] == 255
