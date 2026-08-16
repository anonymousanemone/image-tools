import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def make_white_transparent(img: Image.Image, threshold=250):
    """
    Convert white (or near-white) pixels to transparent.
    threshold: 0–255 (higher = stricter white detection)
    """
    img = img.convert("RGBA")
    data = np.array(img)

    r = data[..., 0]
    g = data[..., 1]
    b = data[..., 2]

    # Detect near-white pixels
    white_mask = (r >= threshold) & (g >= threshold) & (b >= threshold)

    # Set alpha to 0 for white pixels
    data[..., 3] = np.where(white_mask, 0, 255)

    return Image.fromarray(data)


def process_file(input_path: Path, output_path: Path, threshold=250):
    try:
        img = Image.open(input_path)
        result = make_white_transparent(img, threshold)
        result.save(output_path.with_suffix(".png"))
        print(f"✔ Processed: {input_path}")
    except Exception as e:
        print(f"✘ Failed: {input_path} ({e})")


def process_path(path_str, threshold=250):
    path = Path(path_str)

    if path.is_file():
        output_path = path.with_name(path.stem + "_transparent.png")
        process_file(path, output_path, threshold)

    elif path.is_dir():
        supported = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}

        for file in path.iterdir():
            if file.suffix.lower() in supported:
                output_path = file.with_name(file.stem + "_transparent.png")
                process_file(file, output_path, threshold)
    else:
        print("Invalid path")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python make_transparent.py <file_or_folder> [threshold]")
        sys.exit(1)

    input_path = sys.argv[1]
    threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 250

    process_path(input_path, threshold)