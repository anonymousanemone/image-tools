from pypdf import PdfReader, PdfWriter
import os


def normalize_pdf_width(reference_page_index=0):
    # 🔹 Hardcoded input file
    input_path = "/Users/sophial/Downloads/Readings-thesis/carthage/redissi-f1-1-pg1-227.pdf"

    # 🔹 Auto-generate output filename
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}-resized{ext}"

    reader = PdfReader(input_path)
    writer = PdfWriter()

    if reference_page_index < 0 or reference_page_index >= len(reader.pages):
        raise ValueError("Reference page index is out of range.")

    # Get target width from designated page
    target_width = reader.pages[reference_page_index].mediabox.width

    for page in reader.pages:
        current_width = page.mediabox.width

        if current_width != target_width:
            scale_factor = target_width / current_width
            page.scale_by(scale_factor)  # Works in older versions

        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"Saved resized PDF to: {output_path}")


# Run
normalize_pdf_width()