"""Batch raster -> SVG vectorizer for any binarized image, using potracer
(a Python binding to the potrace bitmap tracing library) directly, with a
manual SVG path writer -- no Inkscape dependency.

Assumes a white background with dark foreground by default; pass --invert
for source images that use the opposite convention (dark background, light
foreground). --pad_bg adds a background-colored border around each image
before tracing, so traced contours don't get clipped right at the image
edge; the border color is chosen to match the source image's own background
(white normally, black when --invert is given), then the whole padded image
is inverted together if --invert was passed -- so tracing always sees a
consistent white-bg/dark-fg image regardless of source convention.

Default trace parameters match Inkscape's Trace Bitmap dialog defaults for
"Brightness cutoff" mode (read from Inkscape's own dialog-trace.glade):
threshold 0.45, speckle suppression (turdsize) 2px, corner smoothing
(alphamax) 1.0, path optimization on with tolerance (opttolerance) 0.2.

Safety valve: refuses to run on a whole directory unless --all is passed,
since this is meant to be eyeballed on a small batch first. Use --files or
--glob for a test run.

Usage:
    python3 img_vectorize.py --input-dir crops/ --files a.png b.png
    python3 img_vectorize.py --input-dir crops/ --glob "cat_*.png"
    python3 img_vectorize.py --input-dir crops/ --all --invert --pad_bg
"""
import argparse
import shutil
from pathlib import Path

from PIL import Image, ImageOps
from potrace import Bitmap, POTRACE_TURNPOLICY_MINORITY  # `potracer` library

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}

# Inkscape "Trace Bitmap" > Brightness cutoff defaults (dialog-trace.glade:
# SS_BC_T=0.45, speckles=2, smooth=1, optimize=0.20, all enabled by default)
DEFAULT_BLACKLEVEL = 0.45
DEFAULT_TURDSIZE = 2
DEFAULT_ALPHAMAX = 1.0
DEFAULT_OPTTOLERANCE = 0.2

PAD_PX = 10


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


def trace_one(src_path: Path, svg_path: Path, blacklevel: float, turdsize: int,
              alphamax: float, opttolerance: float, opticurve: bool) -> None:
    image = Image.open(src_path)
    bm = Bitmap(image, blacklevel=blacklevel)
    plist = bm.trace(
        turdsize=turdsize,
        turnpolicy=POTRACE_TURNPOLICY_MINORITY,
        alphamax=alphamax,
        opticurve=opticurve,
        opttolerance=opttolerance,
    )
    parts = []
    for curve in plist:
        fs = curve.start_point
        parts.append(f"M{fs.x},{fs.y}")
        for segment in curve.segments:
            if segment.is_corner:
                a = segment.c
                b = segment.end_point
                parts.append(f"L{a.x},{a.y}L{b.x},{b.y}")
            else:
                a = segment.c1
                b = segment.c2
                c = segment.end_point
                parts.append(f"C{a.x},{a.y} {b.x},{b.y} {c.x},{c.y}")
        parts.append("z")
    with open(svg_path, "w") as fp:
        fp.write(
            f'<svg version="1.1" xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{image.width}" height="{image.height}" '
            f'viewBox="0 0 {image.width} {image.height}">'
        )
        fp.write(f'<path stroke="none" fill="black" fill-rule="evenodd" d="{"".join(parts)}"/>')
        fp.write("</svg>")


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
    parser.add_argument("--blacklevel", type=float, default=DEFAULT_BLACKLEVEL,
                         help="brightness cutoff threshold, 0-1 (potrace blacklevel)")
    parser.add_argument("--turdsize", type=int, default=DEFAULT_TURDSIZE,
                         help="suppress speckles smaller than this many pixels")
    parser.add_argument("--alphamax", type=float, default=DEFAULT_ALPHAMAX,
                         help="corner smoothing, 0 (sharp) to 1.34 (smooth)")
    parser.add_argument("--opttolerance", type=float, default=DEFAULT_OPTTOLERANCE,
                         help="curve optimization tolerance")
    parser.add_argument("--no-optimize", dest="opticurve", action="store_false",
                         help="disable curve optimization (Inkscape's 'optimize paths' checkbox)")
    parser.set_defaults(opticurve=True)
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

    triples = []
    for src_path in targets:
        pre_path = pre_dir / src_path.name
        svg_path = svg_dir / (src_path.stem + ".svg")
        print(f"tracing {src_path.name} -> {svg_path.relative_to(out_dir.parent)}")
        preprocess_one(src_path, pre_path, args.invert, PAD_PX if args.pad_bg else 0)
        trace_one(pre_path, svg_path, args.blacklevel, args.turdsize,
                  args.alphamax, args.opttolerance, args.opticurve)
        shutil.copy(src_path, orig_dir / src_path.name)
        triples.append((src_path, pre_path, svg_path))

    preview_path = out_dir / "preview.html"
    build_preview_html(triples, preview_path)
    print(f"\n{len(triples)} image(s) traced. Preview: {preview_path}")


if __name__ == "__main__":
    main()
