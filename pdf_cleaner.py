import fitz  # PyMuPDF

doc = fitz.open("/Users/sophial/Downloads/Readings-thesis/carthage/Ferron-Latabelladefixionis-1967 copy.pdf")

for page in doc:
    blocks = page.get_text("dict")["blocks"]

    for block in blocks:
        if block["type"] != 0:
            continue

        bbox = fitz.Rect(block["bbox"])

        # Draw white background rectangle
        page.draw_rect(
            bbox,
            color=None,
            fill=(1, 1, 1),  # white
            overlay=True
        )

        # Re-insert the text on top
        for line in block["lines"]:
            for span in line["spans"]:
                page.insert_text(
                    fitz.Point(span["origin"][0], span["origin"][1]),
                    span["text"],
                    fontname=span["font"],
                    fontsize=span["size"],
                    color=(0, 0, 0)  # black text
                )

doc.save("highlighted.pdf")
