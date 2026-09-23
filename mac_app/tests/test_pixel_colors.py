import time

import numpy as np
from PIL import Image

from core.pixel_colors import apply_color_mapping, get_colors_from_image, hex_to_rgb, rgb_to_hex, rgba_to_hex


def _original_loop_apply_color_mapping(image: Image.Image, color_map: dict[str, str]) -> Image.Image:
    """The original notebook's O(width*height) pure-Python loop, kept here only
    as a parity baseline for the vectorized core.pixel_colors.apply_color_mapping."""
    image = image.copy()
    width, height = image.size
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b)
            if hex_color in color_map:
                new_r, new_g, new_b = hex_to_rgb(color_map[hex_color])
                pixels[x, y] = (new_r, new_g, new_b)
    return image


def test_hex_rgb_roundtrip():
    assert rgb_to_hex((224, 248, 207)) == "#e0f8cf"
    assert hex_to_rgb("#e0f8cf") == (224, 248, 207)


def test_rgba_to_hex_omits_alpha_when_opaque():
    assert rgba_to_hex((224, 248, 207, 255)) == "#e0f8cf"
    assert rgba_to_hex((224, 248, 207, 0)) == "#e0f8cf00"


def test_get_colors_from_image_finds_distinct_colors(pixel_art_image):
    colors = get_colors_from_image(pixel_art_image)
    assert set(colors) == {"#e0f8cf", "#86c06c", "#071821", "#306850"}


def test_get_colors_from_image_keeps_transparent_pixels_distinct():
    arr = np.zeros((2, 2, 4), dtype=np.uint8)
    arr[0, 0] = (255, 0, 0, 255)  # opaque red
    arr[0, 1] = (255, 0, 0, 0)  # transparent, same RGB as the opaque red
    arr[1, 0] = (255, 0, 0, 0)
    arr[1, 1] = (0, 255, 0, 255)
    image = Image.fromarray(arr, mode="RGBA")
    colors = get_colors_from_image(image)
    assert set(colors) == {"#ff0000", "#ff000000", "#00ff00"}


def test_apply_color_mapping_matches_alpha_on_rgba_image():
    arr = np.zeros((2, 2, 4), dtype=np.uint8)
    arr[0, 0] = (255, 0, 0, 255)  # opaque red -> should be untouched
    arr[0, 1] = (255, 0, 0, 0)  # transparent red -> should be remapped
    arr[1, 0] = (255, 0, 0, 0)
    arr[1, 1] = (0, 255, 0, 255)
    image = Image.fromarray(arr, mode="RGBA")

    result = apply_color_mapping(image, {"#ff000000": "#0000ff"})
    out = np.array(result)
    assert tuple(out[0, 0]) == (255, 0, 0, 255)
    assert tuple(out[0, 1]) == (0, 0, 255, 0)
    assert tuple(out[1, 0]) == (0, 0, 255, 0)
    assert tuple(out[1, 1]) == (0, 255, 0, 255)


def test_apply_color_mapping_matches_original_loop(pixel_art_image):
    color_map = {"#e0f8cf": "#e5d3b3", "#86c06c": "#b99976"}
    expected = _original_loop_apply_color_mapping(pixel_art_image, color_map)
    actual = apply_color_mapping(pixel_art_image, color_map)
    assert np.array_equal(np.array(expected), np.array(actual))


def test_apply_color_mapping_is_faster_than_loop_on_larger_image():
    arr = np.zeros((200, 200, 3), dtype=np.uint8)
    arr[:100, :100] = (224, 248, 207)
    arr[100:, 100:] = (7, 24, 33)
    image = Image.fromarray(arr, mode="RGB")
    color_map = {"#e0f8cf": "#e5d3b3", "#071821": "#664229"}

    start = time.perf_counter()
    apply_color_mapping(image, color_map)
    vectorized_time = time.perf_counter() - start

    start = time.perf_counter()
    _original_loop_apply_color_mapping(image, color_map)
    loop_time = time.perf_counter() - start

    assert vectorized_time < loop_time
