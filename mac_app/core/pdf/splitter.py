"""Split a PDF into parts under a max size, ported from pdf_splitter.py.

argparse CLI dropped; split_pdf_by_size was already clean/importable.
"""

import os
from io import BytesIO
from typing import Callable, Optional

from pypdf import PdfReader, PdfWriter

BYTES_IN_MB = 1024 * 1024


def split_pdf_by_size(
    input_pdf: str,
    max_size_mb: int,
    on_progress: Optional[Callable[[str], None]] = None,
) -> list[str]:
    def report(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    max_size_bytes = max_size_mb * BYTES_IN_MB

    input_dir = os.path.dirname(os.path.abspath(input_pdf))
    base_name = os.path.splitext(os.path.basename(input_pdf))[0]

    reader = PdfReader(input_pdf)
    total_pages = len(reader.pages)

    part_number = 1
    current_writer = PdfWriter()
    output_paths = []

    for page_index in range(total_pages):
        current_writer.add_page(reader.pages[page_index])

        buffer = BytesIO()
        current_writer.write(buffer)
        current_size = buffer.tell()

        if current_size > max_size_bytes:
            current_writer.remove_page(-1)

            output_path = os.path.join(input_dir, f"{base_name}_{part_number}.pdf")
            with open(output_path, "wb") as f:
                current_writer.write(f)
            output_paths.append(output_path)
            report(f"Saved {output_path}")

            part_number += 1
            current_writer = PdfWriter()
            current_writer.add_page(reader.pages[page_index])

    if len(current_writer.pages) > 0:
        output_path = os.path.join(input_dir, f"{base_name}_{part_number}.pdf")
        with open(output_path, "wb") as f:
            current_writer.write(f)
        output_paths.append(output_path)
        report(f"Saved {output_path}")

    return output_paths
