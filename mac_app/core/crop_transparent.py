"""Crop an image to its non-transparent content (port of img_crop_transparent.py)."""

from PIL import Image


def crop_transparent(image: Image.Image) -> Image.Image | None:
    """Crop to the alpha channel's bounding box. Returns None if fully transparent."""
    img = image.convert("RGBA")
    alpha = img.split()[-1]
    bbox = alpha.getbbox()
    if bbox is None:
        return None
    return img.crop(bbox)
