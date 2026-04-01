import argparse
import os
from io import BytesIO
from pypdf import PdfReader, PdfWriter

# =========================
# Hardcoded defaults
# =========================
DEFAULT_INPUT_PDF = "/Users/sophial/Downloads/Taoufik_Redissi_1987_Etude_des_amulettes.pdf"
DEFAULT_MAX_MB = 9

BYTES_IN_MB = 1024 * 1024


def split_pdf_by_size(
    input_pdf: str,
    max_size_mb: int
):
    max_size_bytes = max_size_mb * BYTES_IN_MB

    input_dir = os.path.dirname(os.path.abspath(input_pdf))
    base_name = os.path.splitext(os.path.basename(input_pdf))[0]

    reader = PdfReader(input_pdf)
    total_pages = len(reader.pages)

    part_number = 1
    current_writer = PdfWriter()

    for page_index in range(total_pages):
        current_writer.add_page(reader.pages[page_index])

        buffer = BytesIO()
        current_writer.write(buffer)
        current_size = buffer.tell()

        if current_size > max_size_bytes:
            # Remove last page and save previous chunk
            current_writer.remove_page(-1)

            output_path = os.path.join(
                input_dir,
                f"{base_name}_{part_number}.pdf"
            )

            with open(output_path, "wb") as f:
                current_writer.write(f)

            print(f"Saved {output_path}")

            part_number += 1

            current_writer = PdfWriter()
            current_writer.add_page(reader.pages[page_index])

    # Save remaining pages
    if len(current_writer.pages) > 0:
        output_path = os.path.join(
            input_dir,
            f"{base_name}_{part_number}.pdf"
        )

        with open(output_path, "wb") as f:
            current_writer.write(f)

        print(f"Saved {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Split a PDF into parts of a given maximum size (in MB)"
    )

    parser.add_argument(
        "-i", "--input",
        default=DEFAULT_INPUT_PDF,
        help=f"Input PDF file (default: {DEFAULT_INPUT_PDF})"
    )

    parser.add_argument(
        "-s", "--size",
        type=int,
        default=DEFAULT_MAX_MB,
        help=f"Maximum size per PDF in MB (default: {DEFAULT_MAX_MB})"
    )

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        raise FileNotFoundError(f"Input PDF not found: {args.input}")

    split_pdf_by_size(
        input_pdf=args.input,
        max_size_mb=args.size
    )


if __name__ == "__main__":
    main()
