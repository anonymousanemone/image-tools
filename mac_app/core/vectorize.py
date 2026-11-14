"""Bitmap -> SVG path tracing via Inkscape's CLI (object-trace, then path-simplify).

Port of img_vectorize2.py. Callers check inkscape_available() first.
"""

import base64
import io
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

SVG_NS = "http://www.w3.org/2000/svg"

# object-trace argument order: scans,smooth,stack,remove_background,speckles,smooth_corners,optimize
DEFAULT_TRACE_PARAMS = "2,false,true,true,2,1,0.4"

PAD_PX = 10


@dataclass
class VectorTrace:
    path_d: str
    width: int
    height: int
    # The exact (inverted/padded) bitmap traced, aligned with path_d's coordinates.
    traced_image: Image.Image


def find_inkscape() -> str | None:
    found = shutil.which("inkscape")
    if found:
        return found
    mac_path = "/Applications/Inkscape.app/Contents/MacOS/inkscape"
    if Path(mac_path).exists():
        return mac_path
    return None


def inkscape_available() -> bool:
    return find_inkscape() is not None


def trace_image(
    image: Image.Image,
    *,
    trace_params: str = DEFAULT_TRACE_PARAMS,
    invert: bool = False,
    pad_px: int = 0,
) -> VectorTrace:
    inkscape = find_inkscape()
    if inkscape is None:
        raise RuntimeError("Inkscape not found — install it and ensure it's on PATH.")

    proc = image.convert("L")
    if pad_px:
        fill = 0 if invert else 255
        proc = ImageOps.expand(proc, border=pad_px, fill=fill)
    if invert:
        proc = ImageOps.invert(proc)

    with tempfile.TemporaryDirectory() as tmp:
        # Open an SVG wrapping the bitmap at 1:1, not the PNG itself: opening a
        # PNG can pop Inkscape's modal "bitmap image import" dialog.
        src_path = Path(tmp) / "source.svg"
        svg_path = Path(tmp) / "traced.svg"
        src_path.write_text(
            f'<svg xmlns="{SVG_NS}" width="{proc.width}" height="{proc.height}" '
            f'viewBox="0 0 {proc.width} {proc.height}">'
            f'<image width="{proc.width}" height="{proc.height}" href="{image_to_data_uri(proc)}"/>'
            f"</svg>"
        )

        actions = (
            f"select-all;"
            f"object-trace:{trace_params};"
            f"path-simplify;"
            f"export-filename:{svg_path};export-plain-svg;export-do;"
            f"quit-immediate"
        )
        result = subprocess.run(
            [inkscape, str(src_path), "--actions", actions, "--batch-process"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Inkscape trace failed:\n{result.stderr}")
        if "expected argument format" in result.stderr:
            raise RuntimeError(f"object-trace rejected params {trace_params!r}:\n{result.stderr}")
        if not svg_path.exists():
            raise RuntimeError(f"Inkscape did not produce an SVG:\n{result.stderr}")

        path_d = _extract_path_d(svg_path)

    if not path_d:
        raise RuntimeError("Inkscape traced no paths (try lowering speckle suppression or check the source image).")

    return VectorTrace(path_d=path_d, width=proc.width, height=proc.height, traced_image=proc)


def _extract_path_d(svg_path: Path) -> str:
    tree = ET.parse(svg_path)
    root = tree.getroot()
    return "".join(el.get("d", "") for el in root.iter(f"{{{SVG_NS}}}path") if el.get("d"))


def image_to_data_uri(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"


def build_svg(
    width: int,
    height: int,
    path_d: str,
    *,
    raster_image: Image.Image | None = None,
    raster_visible: bool = True,
    path_fill: str = "black",
    path_opacity: float = 1.0,
) -> str:
    """SVG of the traced <path> over an optional embedded raster.

    `raster_visible=False` keeps the raster in the file but hidden.
    """
    parts = ['<?xml version="1.0" encoding="UTF-8"?>\n']
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
    )
    if raster_image is not None:
        uri = image_to_data_uri(raster_image)
        style = "" if raster_visible else ' style="display:none"'
        parts.append(
            f'  <image id="raster" width="{width}" height="{height}" x="0" y="0" '
            f'href="{uri}" preserveAspectRatio="none"{style}/>\n'
        )
    parts.append(
        f'  <path id="vector" d="{path_d}" fill="{path_fill}" fill-opacity="{path_opacity}" '
        f'fill-rule="evenodd" stroke="none"/>\n'
    )
    parts.append("</svg>\n")
    return "".join(parts)
