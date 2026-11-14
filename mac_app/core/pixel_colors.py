"""Exact-color inspection and remapping (vectorized port of img_pixel_colors.ipynb)."""

import numpy as np
from PIL import Image

# Callers warn and cap the color list above this (photos can have 100k+ colors).
LARGE_PALETTE_WARNING_THRESHOLD = 256


def rgb_to_hex(color: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % tuple(color[:3])


def rgba_to_hex(color: tuple[int, int, int, int]) -> str:
    """#rrggbb when opaque, else #rrggbbaa (round-trips with hex_to_rgba)."""
    r, g, b, a = color
    if a == 255:
        return rgb_to_hex((r, g, b))
    return "#%02x%02x%02x%02x" % (r, g, b, a)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.strip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def hex_to_rgba(hex_color: str) -> tuple[int, int, int, int]:
    """Parse #rrggbb (alpha 255) or #rrggbbaa."""
    stripped = hex_color.strip().lstrip("#")
    if len(stripped) == 6:
        r, g, b = (int(stripped[i:i + 2], 16) for i in (0, 2, 4))
        return (r, g, b, 255)
    if len(stripped) == 8:
        r, g, b, a = (int(stripped[i:i + 2], 16) for i in (0, 2, 4, 6))
        return (r, g, b, a)
    raise ValueError(f"Invalid hex color: {hex_color!r}")


def is_valid_hex_color(hex_color: str) -> bool:
    try:
        hex_to_rgba(hex_color)
        return True
    except ValueError:
        return False


def get_colors_from_image(image: Image.Image) -> list[str]:
    """Distinct hex colors, most frequent first.

    RGBA keeps alpha, so e.g. a transparent background is its own #rrggbbaa entry.
    """
    if image.mode == "RGBA":
        colors = image.getcolors(maxcolors=1_000_000)
        colors = sorted(colors, key=lambda c: c[0], reverse=True)
        return [rgba_to_hex(color) for _, color in colors]
    rgb_image = image.convert("RGB")
    colors = rgb_image.getcolors(maxcolors=1_000_000)
    colors = sorted(colors, key=lambda c: c[0], reverse=True)
    return [rgb_to_hex(color) for _, color in colors]


def apply_color_mapping(image: Image.Image, color_map: dict[str, str]) -> Image.Image:
    """Replace pixels exactly matching each "from" hex with its "to" hex.

    On RGBA, "from" matches full RGBA (a 6-digit hex matches opaque pixels only).
    An 8-digit "to" also sets alpha; a 6-digit one keeps it.
    """
    has_alpha = image.mode == "RGBA"
    working = image.convert("RGBA" if has_alpha else "RGB")
    arr = np.array(working)

    for from_hex, to_hex in color_map.items():
        to_r, to_g, to_b, to_a = hex_to_rgba(to_hex)
        if has_alpha:
            from_rgba = hex_to_rgba(from_hex)
            mask = np.all(arr == np.array(from_rgba, dtype=arr.dtype), axis=-1)
        else:
            from_rgb = hex_to_rgb(from_hex)
            mask = np.all(arr[..., :3] == np.array(from_rgb, dtype=arr.dtype), axis=-1)
        arr[..., :3][mask] = (to_r, to_g, to_b)
        if has_alpha and len(to_hex.strip().lstrip("#")) == 8:
            arr[..., 3][mask] = to_a

    return Image.fromarray(arr, mode=working.mode)
