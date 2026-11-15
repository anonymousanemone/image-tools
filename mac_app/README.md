# Image Tools (macOS app)

A consolidated desktop app for document binarization, pixel-color remapping/colormapping, and PDF utilities. Built with Python + PySide6, packaged as a native `.app` with PyInstaller.

Co-authored with Claude Opus 5.5.

Three tabs:
- **Binarizer** — 12 classical/local-adaptive binarization algorithms (doxapy), one-button macOS Vision background removal, a filter toolbox (bilateral, gaussian, median, erode, dilate, morph open/close, find contour), and the shared image toolbar.
- **Pixel Colors & Colormap** — inspect an image's distinct colors, remap exact hex colors, and map an image onto a reference palette via ImageMagick.
- **PDF Tools** — Flatten (strip text layer), Resize (normalize page width), Side by Side (combine two PDFs), Split (by max size), To Images (rasterize pages).

The shared toolbar (Crop Transparent / Make Transparent / Download as PNG, JPG, or SVG) appears in both the Binarizer and Pixel Colors tabs. Downloads default to the opened file's folder and name. The name gets a tag appended: the binarization method in the Binarizer tab (`scan-WOLF.png`), or `-processed` when the image wasn't binarized (`scan-processed.png`) and always in Pixel Colors.

The Binarizer's **Enlarge** panel scales the image up (simple bicubic, or "Sharp lines": Lanczos + light blur, re-thresholded when the image is already black/white), either on the current image or on the source right before binarizing — the latter gives the cleanest result. **Anti-alias** softens the binarized edges.

"Open Image…" (Binarizer and Pixel Colors tabs) accepts PNG, JPEG, BMP, TIFF, WebP, GIF, HEIC/HEIF, and single-page PDFs (only the first page of a multi-page PDF is loaded — use the PDF Tools tab for the rest). Any input mode (palette, CMYK, grayscale+alpha, etc.) is normalized to plain RGB/RGBA on load.

## Requirements

- macOS 13+ (Ventura or later) — required for the Vision-based background removal.
- Python 3.12 (doxapy ships a prebuilt wheel for this version; other versions may require a local compile).
- ImageMagick 7+ (optional, `brew install imagemagick` via [Homebrew](https://brew.sh)). The Colormap section of the Pixel Colors tab calls its `magick` CLI. Without it, the app disables the Colormap controls (see Help → Check Dependencies).

## Setup (development)

```bash
conda activate general
cd mac_app
pip install PySide6 opencv-python doxapy pillow-heif pypdf PyMuPDF \
    pyobjc-framework-Vision pyobjc-framework-Quartz pyobjc-framework-Cocoa pytest pyinstaller
```

## Run

```bash
conda activate general
python main.py
```

## Test

```bash
conda activate general
pytest
```

## Build the .app

```bash
conda activate general
pyinstaller packaging/pyinstaller.spec --distpath dist --workpath build --noconfirm
xattr -cr "dist/Image Tools.app"   # clears extended attrs that otherwise break codesign
codesign -s - --force --deep "dist/Image Tools.app"   # ad-hoc sign, single-machine use
ditto "dist/Image Tools.app" "build/Image Tools.app"   # keep a copy of the app in build/ (gitignored)
rm -rf dist   # optional: dist/ is disposable once the copy is in build/
open "build/Image Tools.app"
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

- `magick` is **not bundled** — it's a separate Homebrew binary invoked via
  `subprocess`. A `.app` launched from Finder does not inherit your shell's
  `PATH`, so lookups fall back to checking `/opt/homebrew/bin` and
  `/usr/local/bin` directly (see `core/utils.py`'s `which()`).
- If you add new dependencies with dynamic imports (like doxapy's
  `getattr`-based algorithm dispatch, or Vision/Quartz's lazy imports inside
  `segment_vision()`), add them to `hiddenimports` in
  `packaging/pyinstaller.spec` — PyInstaller's static analysis won't find them
  on its own.
