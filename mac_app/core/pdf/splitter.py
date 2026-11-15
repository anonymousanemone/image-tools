"""Split a PDF into parts under a max size (port of pdf_splitter.py)."""

import os
from io import BytesIO
from typing import Callable, Optional

from pypdf import PdfReader, PdfWriter

BYTES_IN_MB = 1024 * 1024


def part_filename(input_pdf: str, part_number: int) -> str:
    return f"{os.path.splitext(os.path.basename(input_pdf))[0]}_{part_number}.pdf"


def _part_writer(reader: PdfReader, pages: list[int]) -> PdfWriter:
    writer = PdfWriter()
    for page_index in pages:
        writer.add_page(reader.pages[page_index])
    return writer


def _written_size(writer: PdfWriter) -> int:
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.tell()


def plan_split(
    input_pdf: str,
    max_size_mb: float,
    on_progress: Optional[Callable[[str], None]] = None,
) -> list[tuple[list[int], int]]:
    """Each part's page indices and written byte size. A page that alone exceeds the limit becomes its own part."""
    max_size_bytes = max_size_mb * BYTES_IN_MB
    reader = PdfReader(input_pdf)

    parts = []
    pages: list[int] = []
    size = 0
    for page_index in range(len(reader.pages)):
        new_size = _written_size(_part_writer(reader, pages + [page_index]))
        if new_size > max_size_bytes and pages:
            parts.append((pages, size))
            pages = []
            new_size = _written_size(_part_writer(reader, [page_index]))
        pages.append(page_index)
        size = new_size
        if on_progress:
            on_progress(f"Measured page {page_index + 1}/{len(reader.pages)}")
    if pages:
        parts.append((pages, size))
    return parts


def split_pdf_by_size(
    input_pdf: str,
    max_size_mb: float,
    output_dir: Optional[str] = None,
    on_progress: Optional[Callable[[str], None]] = None,
) -> list[str]:
    def report(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(input_pdf))
    else:
        os.makedirs(output_dir, exist_ok=True)

    reader = PdfReader(input_pdf)
    output_paths = []
    for part_number, (pages, _size) in enumerate(plan_split(input_pdf, max_size_mb, on_progress), start=1):
        writer = _part_writer(reader, pages)
        output_path = os.path.join(output_dir, part_filename(input_pdf, part_number))
        with open(output_path, "wb") as f:
            writer.write(f)
        output_paths.append(output_path)
        report(f"Saved {output_path}")

    return output_paths
