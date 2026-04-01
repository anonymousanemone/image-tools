import fitz  # PyMuPDF
from PIL import Image
import io
import os

def strip_text_layer(input_pdf, output_pdf, dpi=300):
    if not os.path.isfile(input_pdf):
        raise FileNotFoundError(input_pdf)

    src_doc = fitz.open(input_pdf)
    out_doc = fitz.open()

    zoom = dpi / 72  # PDF default is 72 DPI
    matrix = fitz.Matrix(zoom, zoom)

    print(f"Stripping text layer from {len(src_doc)} pages...")

    for page_num, page in enumerate(src_doc, start=1):
        # Render page to image
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        img = Image.open(io.BytesIO(pix.tobytes("png")))

        # Create a new PDF page sized to the image
        pdf_page = out_doc.new_page(
            width=img.width,
            height=img.height
        )

        # Insert image into page
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        pdf_page.insert_image(
            pdf_page.rect,
            stream=img_bytes.read()
        )

        print(f"Processed page {page_num}")

    out_doc.save(output_pdf)
    out_doc.close()
    src_doc.close()

    print(f"Done. Output saved to: {output_pdf}")

strip_text_layer(
    input_pdf="/Users/sophial/Downloads/Readings-thesis/carthage/archive/REDISSI, Taoufik. ETUDE DES AMULETTES DE TYPE EGYPTIEN ET EGYPTISANT ET DIVERS AEGYPTIACA DE CARTHAGE-f2.pdf",
    output_pdf="scan_only.pdf",
    dpi=300
)