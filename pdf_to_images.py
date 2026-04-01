import os
from pdf2image import convert_from_path

def pdf_to_images(
    pdf_path,
    dpi=300,
    jpeg_quality=95,
    poppler_path=None
):
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(pdf_path)

    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.join(os.path.dirname(pdf_path), pdf_name)
    os.makedirs(output_dir, exist_ok=True)

    page_num = 1

    print("Starting PDF → image conversion (OCR optimized)...")

    while True:
        try:
            pages = convert_from_path(
                pdf_path,
                dpi=dpi,
                first_page=page_num,
                last_page=page_num,
                poppler_path=poppler_path
            )
        except Exception as e:
            print(f"Stopping at page {page_num}: {e}")
            break

        if not pages:
            break

        image_path = os.path.join(
            output_dir,
            f"page_{page_num:04d}.jpeg"
        )

        pages[0].save(
            image_path,
            "JPEG",
            quality=jpeg_quality,
            subsampling=0,   # critical for OCR quality
            optimize=True
        )

        print(f"Saved page {page_num}")
        page_num += 1

    print(f"Done. Converted {page_num - 1} pages.")


# Example usage
if __name__ == "__main__":
    pdf_to_images("/Users/sophial/Downloads/Readings-thesis/1442307.pdf")