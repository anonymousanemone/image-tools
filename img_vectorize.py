"""Batch raster -> SVG vectorizer for any binarized image, using Inkscape's
headless CLI for bitmap tracing (potrace under the hood) plus a
path-simplify decimation pass. Strips the embedded source raster that
Inkscape leaves behind, so each output SVG is a clean vector-only path.

Assumes a white background with dark foreground by default; pass --invert
for source images that use the opposite convention (dark background, light
foreground). --pad_bg adds a background-colored border around each image
before tracing, so traced contours don't get clipped right at the image
edge; the border color is chosen to match the source image's own background
(white normally, black when --invert is given), then the whole padded image
is inverted together if --invert was passed -- so tracing always sees a
consistent white-bg/dark-fg image regardless of source convention.

Safety valve: refuses to run on a whole directory unless --all is passed,
since this is meant to be eyeballed on a small batch first. Use --files or
--glob for a test run.

Usage:
    python3 trace_batch_generic.py --input-dir crops/ --files a.png b.png
    python3 trace_batch_generic.py --input-dir crops/ --glob "cat_*.png"
    python3 trace_batch_generic.py --input-dir crops/ --all --invert --pad_bg
"""
import argparse
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageOps

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}

# object-trace argument order: scans,smooth,stack,remove_background,speckles,smooth_corners,optimize
DEFAULT_TRACE_PARAMS = "2,false,true,true,2,1,0.4"

PAD_PX = 10


def find_inkscape() -> str:
    found = shutil.which("inkscape")
    if found:
        return found
    mac_path = "/Applications/Inkscape.app/Contents/MacOS/inkscape"
    if Path(mac_path).exists():
        return mac_path
    raise RuntimeError("inkscape binary not found on PATH or at the usual macOS app location")


def preprocess_one(src_path: Path, out_path: Path, invert: bool, pad_px: int) -> None:
    """Optionally pad with a background-colored border, then optionally
    invert, so tracing always sees a consistent white-bg/dark-fg image."""
    im = Image.open(src_path).convert("L")
    if pad_px:
        fill = 0 if invert else 255
        im = ImageOps.expand(im, border=pad_px, fill=fill)
    if invert:
        im = ImageOps.invert(im)
    im.save(out_path)


def trace_one(inkscape: str, src_path: Path, svg_path: Path, trace_params: str) -> None:
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
        raise RuntimeError(f"inkscape failed on {src_path.name}:\n{result.stderr}")
    if "expected argument format" in result.stderr:
        raise RuntimeError(f"object-trace rejected params for {src_path.name}:\n{result.stderr}")


def strip_embedded_raster(svg_path: Path) -> None:
    """Remove the source <image> Inkscape leaves behind after tracing, so
    only the traced <path> element(s) remain."""
    tree = ET.parse(svg_path)
    root = tree.getroot()
    removed = 0
    for parent in root.iter():
        for image in list(parent.findall(f"{{{SVG_NS}}}image")):
            parent.remove(image)
            removed += 1
    if removed == 0:
        raise RuntimeError(f"{svg_path.name}: no embedded raster found to strip (unexpected)")
    tree.write(svg_path, encoding="unicode", xml_declaration=True)


def resolve_targets(args, input_dir: Path) -> list[Path]:
    if args.files:
        targets = [input_dir / name for name in args.files]
        missing = [t for t in targets if not t.exists()]
        if missing:
            raise SystemExit(f"missing input files: {[m.name for m in missing]}")
        return targets
    if args.glob:
        targets = sorted(input_dir.glob(args.glob))
        if not targets:
            raise SystemExit(f"no files matched glob {args.glob!r} in {input_dir}")
        return targets
    if args.all:
        targets = sorted(p for p in input_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
        if not targets:
            raise SystemExit(f"no images (extensions: {sorted(IMAGE_EXTS)}) found in {input_dir}")
        return targets
    raise SystemExit("refusing to run with no scope: pass --files, --glob, or --all")


def build_preview_html(triples: list[tuple[Path, Path, Path]], out_path: Path) -> None:
    rows = []
    for src_path, pre_path, svg_path in triples:
        rows.append(f"""
    <div class="row">
      <div class="cell"><div class="label">{src_path.name} (original)</div>
        <img src="original/{src_path.name}" class="raster"></div>
      <div class="cell"><div class="label">{pre_path.name} (preprocessed)</div>
        <img src="preprocessed/{pre_path.name}" class="raster"></div>
      <div class="cell"><div class="label">{svg_path.name} (traced)</div>
        <img src="svg/{svg_path.name}" class="vector"></div>
    </div>""")
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Trace preview</title>
<style>
  body {{ font-family: sans-serif; background: white; color: #222; }}
  .row {{ display: flex; gap: 24px; align-items: flex-end; border-bottom: 1px solid #ddd; padding: 12px 0; }}
  .cell {{ text-align: center; }}
  .label {{ font-size: 12px; color: #666; margin-bottom: 4px; }}
  img {{ background: white; max-height: 160px; }}
</style></head>
<body>
  <h2>Original vs. preprocessed vs. traced SVG</h2>
  {''.join(rows)}
</body></html>"""
    out_path.write_text(html)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-dir", required=True, help="directory containing source images")
    parser.add_argument("--files", nargs="+", help="explicit image filenames (relative to --input-dir)")
    parser.add_argument("--glob", help="glob pattern within --input-dir, e.g. 'cat_*.png'")
    parser.add_argument("--all", action="store_true", help="process every image in --input-dir (no safety valve)")
    parser.add_argument("--invert", action="store_true",
                         help="source images have a dark background / light foreground")
    parser.add_argument("--pad_bg", action="store_true",
                         help=f"pad {PAD_PX}px of background color on every side before tracing")
    parser.add_argument("--trace-params", default=DEFAULT_TRACE_PARAMS,
                         help="object-trace args: scans,smooth,stack,remove_background,speckles,smooth_corners,optimize")
    parser.add_argument("--out", default="./trace_output", help="output directory")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    out_dir = Path(args.out)
    svg_dir = out_dir / "svg"
    pre_dir = out_dir / "preprocessed"
    orig_dir = out_dir / "original"
    for d in (svg_dir, pre_dir, orig_dir):
        d.mkdir(parents=True, exist_ok=True)

    targets = resolve_targets(args, input_dir)
    inkscape = find_inkscape()

    triples = []
    for src_path in targets:
        pre_path = pre_dir / src_path.name
        svg_path = svg_dir / (src_path.stem + ".svg")
        print(f"tracing {src_path.name} -> {svg_path.relative_to(out_dir.parent)}")
        preprocess_one(src_path, pre_path, args.invert, PAD_PX if args.pad_bg else 0)
        trace_one(inkscape, pre_path, svg_path, args.trace_params)
        strip_embedded_raster(svg_path)
        shutil.copy(src_path, orig_dir / src_path.name)
        triples.append((src_path, pre_path, svg_path))

    preview_path = out_dir / "preview.html"
    build_preview_html(triples, preview_path)
    print(f"\n{len(triples)} image(s) traced. Preview: {preview_path}")


if __name__ == "__main__":
    main()
