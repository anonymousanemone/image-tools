"""Photographic palette mapping, ported from colormap.R (R magick::image_map).

Shells out to ImageMagick's `magick` CLI rather than reimplementing
nearest-color matching in Python. `magick <input> -remap <palette> <output>`
maps every pixel to the nearest color in the palette image without dithering
by default, matching R magick's `image_map(dither = FALSE)` default.
Requires ImageMagick 7+ (the unified `magick` binary — a legacy
convert/mogrify-only install won't work).
"""

import subprocess
from pathlib import Path

from .utils import which


def magick_available() -> bool:
    return which("magick") is not None


def run_image_map(input_path, palette_path, output_path, dither: bool = False) -> None:
    magick_bin = which("magick")
    if magick_bin is None:
        raise RuntimeError(
            "ImageMagick's `magick` CLI was not found. Install it with: brew install imagemagick"
        )

    input_path = Path(input_path)
    palette_path = Path(palette_path)
    output_path = Path(output_path)

    dither_flag = "-dither" if dither else "+dither"
    cmd = [magick_bin, str(input_path), dither_flag, "-remap", str(palette_path), str(output_path)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ImageMagick colormap failed: {result.stderr.strip()}")
