"""SVG export, ported from img_binarizer.ipynb's png_to_svg().

Wraps a base64-encoded PNG in a minimal SVG <image> tag (raster embedded in
an SVG wrapper, not true vector tracing) — matches the notebook's approach.
Uses cv2.imencode instead of the notebook's skimage.io.imsave so the app
doesn't need scikit-image (and its scipy/tifffile/imageio dependency chain)
just for this one call.
"""

import base64
from pathlib import Path

import cv2
import numpy as np


def png_to_svg(output: np.ndarray, svg_path) -> None:
    svg_path = Path(svg_path)

    ok, encoded = cv2.imencode(".png", output)
    if not ok:
        raise ValueError("Failed to encode image as PNG for SVG export")
    image_data = base64.b64encode(encoded.tobytes()).decode("utf-8")

    h, w = output.shape[:2]

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{w}" height="{h}" viewBox="0 0 {w} {h}">
    <image width="{w}" height="{h}"
           x="0" y="0"
           href="data:image/png;base64,{image_data}"
           preserveAspectRatio="none"/>
</svg>
'''

    svg_path.write_text(svg)
