"""Palette mapping via ImageMagick 7's `magick -remap` (port of colormap.R's image_map).

Maps each pixel to the nearest palette-image color, undithered by default.
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
