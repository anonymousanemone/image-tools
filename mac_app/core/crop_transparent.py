"""Crop an image to its non-transparent content, ported from img_crop_transparent.py.

Rewritten to operate in-memory (PIL.Image in/out) for the shared toolbar's
undo-stack composition; a file-path wrapper is kept for parity testing.
"""

from PIL import Image


def crop_transparent(image: Image.Image) -> Image.Image | None:
    """Crop to the alpha channel's bounding box. Returns None if fully transparent."""
    img = image.convert("RGBA")
    alpha = img.split()[-1]
    bbox = alpha.getbbox()
    if bbox is None:
        return None
    return img.crop(bbox)


def crop_transparent_image(image_path, output_path) -> None:
    """File-path wrapper matching the original script's signature."""
    img = Image.open(image_path)
    cropped = crop_transparent(img)
    if cropped is None:
        print(f"Skipped (fully transparent): {image_path}")
        return
    cropped.save(output_path)
    print(f"Cropped: {image_path} -> {output_path}")
