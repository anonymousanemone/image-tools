"""Pixel-exact color inspection and remapping, ported from img_pixel_colors.ipynb.

apply_color_mapping is rewritten as vectorized numpy — the original iterated
every pixel in pure Python (O(width*height) Python-level work), which is only
practical on pixel-art-scale images. get_colors/hex_to_rgb are reused as-is.
"""

from pathlib import Path

import numpy as np
from PIL import Image

# get_colors(maxcolors=1_000_000) is tuned for pixel-art-scale palettes; a
# photo can return hundreds of thousands of distinct colors, which is not
# useful to render as a swatch strip. Callers should warn/cap above this.
LARGE_PALETTE_WARNING_THRESHOLD = 256


def rgb_to_hex(color: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % tuple(color[:3])


def rgba_to_hex(color: tuple[int, int, int, int]) -> str:
    """6-digit hex for an opaque color, 8-digit #rrggbbaa when it has alpha —
    matches hex_to_rgba's own format so it round-trips."""
    r, g, b, a = color
    if a == 255:
        return rgb_to_hex((r, g, b))
    return "#%02x%02x%02x%02x" % (r, g, b, a)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.strip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def hex_to_rgba(hex_color: str) -> tuple[int, int, int, int]:
    """Parses a 6-digit (#rrggbb, alpha defaults to opaque) or 8-digit
    (#rrggbbaa) hex color, for replacement colors that carry an explicit
    alpha value."""
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


def get_colors(image_path) -> list[str]:
    image = Image.open(image_path).convert("RGB")
    return get_colors_from_image(image)


def get_colors_from_image(image: Image.Image) -> list[str]:
    """Distinct hex colors in an in-memory image, most-frequent first.

    RGBA images are grouped by (r, g, b, a) rather than flattened to RGB, so
    e.g. a transparent background comes back as its own #rrggbbaa entry
    instead of being merged into whatever opaque pixels share its RGB.
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
    """Replace exact-hex-match pixels per color_map. Vectorized (see module docstring).

    On an RGBA image, a "from" value is matched on its full (r, g, b, a) —
    an 8-digit #rrggbbaa "from" only matches that exact transparency, and a
    plain 6-digit "from" only matches fully-opaque pixels of that color,
    consistent with the alpha-aware colors get_colors_from_image() loads.
    A "to" value may be an 8-digit #rrggbbaa hex to also overwrite the alpha
    channel of matched pixels; a plain 6-digit hex leaves the existing alpha
    of matched pixels untouched.
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


def apply_color_mapping_file(image_path, color_map: dict[str, str], output_path) -> None:
    """File-path wrapper, kept for parity testing against the original notebook loop."""
    image = Image.open(image_path)
    result = apply_color_mapping(image, color_map)
    result.save(Path(output_path))
