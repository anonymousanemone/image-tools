"""Scale every PDF page to one reference page's width (port of pdf_resizer.py).

`output_path` defaults to `<stem>-resized<ext>`.
"""

import os
from typing import Callable, Optional

from pypdf import PdfReader, PdfWriter


def _check_reference(reader: PdfReader, reference_page_index: int) -> None:
    if reference_page_index < 0 or reference_page_index >= len(reader.pages):
        raise ValueError("Reference page index is out of range.")


def page_width_changes(input_path: str, reference_page_index: int = 0) -> list[int]:
    """Per page: -1 if resizing shrinks it, 1 if it enlarges it, 0 if unchanged."""
    reader = PdfReader(input_path)
    _check_reference(reader, reference_page_index)
    target_width = reader.pages[reference_page_index].mediabox.width
    changes = []
    for page in reader.pages:
        width = page.mediabox.width
        if width > target_width:
            changes.append(-1)
        elif width < target_width:
            changes.append(1)
        else:
            changes.append(0)
    return changes


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
    _check_reference(reader, reference_page_index)

    # pypdf 7 only scales pages already attached to a writer.
    writer = PdfWriter(clone_from=reader)
    target_width = writer.pages[reference_page_index].mediabox.width

    for page in writer.pages:
        current_width = page.mediabox.width
        if current_width != target_width:
            page.scale_by(target_width / current_width)

    with open(output_path, "wb") as f:
        writer.write(f)

    report(f"Saved resized PDF to: {output_path}")
    return output_path
