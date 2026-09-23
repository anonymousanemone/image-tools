"""Make near-white pixels transparent, reused as-is from img_transparent_bg.py."""

import numpy as np
from PIL import Image


def make_white_transparent(img: Image.Image, threshold: int = 250) -> Image.Image:
    """Convert white (or near-white) pixels to transparent.

    threshold: 0-255 (higher = stricter white detection)
    """
    img = img.convert("RGBA")
    data = np.array(img)

    r = data[..., 0]
    g = data[..., 1]
    b = data[..., 2]

    white_mask = (r >= threshold) & (g >= threshold) & (b >= threshold)
    data[..., 3] = np.where(white_mask, 0, 255)

    return Image.fromarray(data)
