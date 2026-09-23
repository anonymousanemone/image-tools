# Image Tools (macOS app)

A consolidated desktop app for document binarization, pixel-color remapping/colormapping, and PDF utilities. Built with Python + PySide6, packaged as a native `.app` with PyInstaller.

Three tabs:
- **Binarizer** — 12 classical/local-adaptive binarization algorithms (doxapy), one-button macOS Vision background removal, a filter toolbox (bilateral, gaussian, median, erode, dilate, morph open/close, find contour), and the shared image toolbar.
- **Pixel Colors & Colormap** — inspect an image's distinct colors, remap exact hex colors, and map an image onto a reference palette via ImageMagick.
- **PDF Tools** — Flatten (strip text layer), Resize (normalize page width), Side by Side (combine two PDFs), Split (by max size), To Images (rasterize pages).

The shared toolbar (Crop Transparent / Make Transparent / Download as PNG, JPG, or SVG) appears in both the Binarizer and Pixel Colors tabs. Downloads default to the same file name and folder as the opened file, with the extension swapped for the chosen format.

"Open Image…" (Binarizer and Pixel Colors tabs) accepts PNG, JPEG, BMP, TIFF, WebP, GIF, HEIC/HEIF, and single-page PDFs (only the first page of a multi-page PDF is loaded — use the PDF Tools tab for the rest). Any input mode (palette, CMYK, grayscale+alpha, etc.) is normalized to plain RGB/RGBA on load.

## Requirements

- macOS 13+ (Ventura or later) — required for the Vision-based background removal.
- Python 3.12 (doxapy ships a prebuilt wheel for this version; other versions may require a local compile).
- [Homebrew](https://brew.sh) for two optional system dependencies:
  - `brew install imagemagick` — needed for the Colormap section of the Pixel Colors tab (ImageMagick 7+, the unified `magick` CLI).
  - `brew install poppler` — needed for the PDF Tools "To Images" panel (`pdf2image` wraps Poppler's `pdftoppm`).

Both are optional at a feature level — the app detects their absence and disables/warns on the relevant controls (see Help → Check Dependencies).

## Setup (development)

```bash
cd mac_app
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
source .venv/bin/activate
python main.py
```

## Test

```bash
source .venv/bin/activate
pytest
```

## Build the .app

```bash
source .venv/bin/activate
pyinstaller packaging/pyinstaller.spec --distpath dist --workpath build --noconfirm
xattr -cr "dist/Image Tools.app"   # clears extended attrs that otherwise break codesign
codesign -s - --force --deep "dist/Image Tools.app"   # ad-hoc sign, single-machine use
open "dist/Image Tools.app"
```

The `xattr -cr` step matters: PyInstaller's own ad-hoc codesign step can fail with
"resource fork, Finder information, or similar detritus not allowed" if any
extended attributes (e.g. quarantine flags from a copied file) linger in
`dist/`. Clearing them before signing fixes it.

### Sharing the app with another Mac

An ad-hoc-signed `.app` will trigger a Gatekeeper warning on any Mac other than
the one it was built on — right-click → Open once to bypass it. For real
distribution beyond your own machine, you'd want a paid Apple Developer ID and
notarization, which is out of scope for this build.

### Known packaging pitfalls

- `magick` and `pdftoppm` are **not bundled** — they're separate Homebrew
  binaries invoked via `subprocess`. A `.app` launched from Finder does not
  inherit your shell's `PATH`, so lookups fall back to checking
  `/opt/homebrew/bin` and `/usr/local/bin` directly (see `core/utils.py`'s
  `which()`).
- If you add new dependencies with dynamic imports (like doxapy's
  `getattr`-based algorithm dispatch, or Vision/Quartz's lazy imports inside
  `segment_vision()`), add them to `hiddenimports` in
  `packaging/pyinstaller.spec` — PyInstaller's static analysis won't find them
  on its own.
