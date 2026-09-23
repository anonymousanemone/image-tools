import numpy as np

from core.binarize import (
    ALGORITHMS,
    all_binarize_algos,
    binarize_array,
    flatten_alpha_to_white,
    threshold_array,
)


def test_flatten_alpha_to_white_turns_transparent_pixels_white(sample_rgba_with_alpha):
    gray = flatten_alpha_to_white(sample_rgba_with_alpha)
    assert gray.ndim == 2
    # fully-transparent top rows should have flattened to white (255), not black
    assert gray[0, 0] == 255


def test_binarize_array_all_algorithms_run(sample_doc_image):
    for algo in ALGORITHMS:
        result = binarize_array(sample_doc_image, func=algo)
        assert result.shape == sample_doc_image.shape[:2]
        assert set(np.unique(result)).issubset({0, 255})


def test_binarize_array_transparent_output_has_alpha(sample_doc_image):
    result = binarize_array(sample_doc_image, func="WOLF", transparent=True)
    assert result.shape[2] == 4


def test_binarize_array_thicken_lines_changes_output(sample_doc_image):
    plain = binarize_array(sample_doc_image, func="WOLF")
    thickened = binarize_array(sample_doc_image, func="WOLF", thicken_lines=True)
    assert not np.array_equal(plain, thickened)


def test_all_binarize_algos_returns_one_per_algorithm(sample_doc_image):
    results = all_binarize_algos(sample_doc_image)
    assert len(results) == len(ALGORITHMS)
    for r in results:
        assert r.shape == sample_doc_image.shape[:2]


def test_binarize_array_matches_all_binarize_algos(sample_doc_image):
    """The single-algorithm path and the all-algorithms path must agree exactly."""
    all_results = all_binarize_algos(sample_doc_image)
    idx = ALGORITHMS.index("SAUVOLA")
    single = binarize_array(sample_doc_image, func="SAUVOLA")
    assert np.array_equal(all_results[idx], single)


def test_threshold_array_is_binary(sample_doc_image):
    result = threshold_array(sample_doc_image, thresh=127)
    assert result.shape == sample_doc_image.shape[:2]
    assert set(np.unique(result)).issubset({0, 255})


def test_threshold_array_respects_cutoff():
    # a flat mid-gray image should flip from all-black to all-white as the
    # threshold crosses its value
    gray = np.full((20, 20, 3), 100, dtype=np.uint8)
    below = threshold_array(gray, thresh=50)
    above = threshold_array(gray, thresh=150)
    assert np.all(below == 255)
    assert np.all(above == 0)


def test_threshold_array_transparent_and_thicken_lines(sample_doc_image):
    result = threshold_array(sample_doc_image, thresh=127, transparent=True)
    assert result.shape[2] == 4
    plain = threshold_array(sample_doc_image, thresh=127)
    thickened = threshold_array(sample_doc_image, thresh=127, thicken_lines=True)
    assert not np.array_equal(plain, thickened)
