"""Scale every PDF page to one reference page's width (port of pdf_resizer.py).

`output_path` defaults to `<stem>-resized<ext>`.
"""

import os
from typing import Callable, Optional

from pypdf import PdfReader, PdfWriter


def normalize_pdf_width(
    input_path: str,
    output_path: Optional[str] = None,
    reference_page_index: int = 0,
    on_progress: Optional[Callable[[str], None]] = None,
) -> str:
    def report(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}-resized{ext}"

    reader = PdfReader(input_path)
    writer = PdfWriter()

    if reference_page_index < 0 or reference_page_index >= len(reader.pages):
        raise ValueError("Reference page index is out of range.")

    target_width = reader.pages[reference_page_index].mediabox.width

    for page in reader.pages:
        current_width = page.mediabox.width
        if current_width != target_width:
            scale_factor = target_width / current_width
            page.scale_by(scale_factor)
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    report(f"Saved resized PDF to: {output_path}")
    return output_path
