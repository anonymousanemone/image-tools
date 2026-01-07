"""
Crops a transparent image to its non-transparent content.
"""

import os
from PIL import Image

# ==========================
# INPUT VALUES
# ==========================
# A file or a directory
INPUT_PATH = None 
OUTPUT_PATH = None  # Optional

def crop_transparent_image(image_path, output_path):
    img = Image.open(image_path).convert("RGBA")
    alpha = img.split()[-1]
    bbox = alpha.getbbox()

    if bbox:
        cropped_img = img.crop(bbox)
        cropped_img.save(output_path)
        print(f"Cropped: {image_path} -> {output_path}")
    else:
        print(f"Skipped (fully transparent): {image_path}")

def process_images(input_path, output_dir=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    if os.path.isfile(input_path):
        # Handle a single image
        if not output_dir:
            output_dir = os.path.dirname(input_path)
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.basename(input_path)
        output_path = os.path.join(output_dir, filename)
        crop_transparent_image(input_path, output_path)

    elif os.path.isdir(input_path):
        # Handle a directory of images
        if not output_dir:
            output_dir = os.path.join(input_path, "cropped")
        os.makedirs(output_dir, exist_ok=True)

        for filename in os.listdir(input_path):
            if filename.lower().endswith((".png", ".webp")):
                full_input_path = os.path.join(input_path, filename)
                output_path = os.path.join(output_dir, filename)
                crop_transparent_image(full_input_path, output_path)

    else:
        raise ValueError("Input path must be a file or directory.")
    

if __name__ == "__main__":
    process_images(INPUT_PATH, OUTPUT_PATH)