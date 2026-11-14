"""Document binarization, ported from img_binarizer.ipynb.

Uses doxapy (https://pypi.org/project/doxapy/) for the 12 classical/
local-adaptive binarization algorithms. `binarize_array`/`all_binarize_algos`
are pure array-in/array-out functions (no plotting, no file I/O) so the GUI
can call them directly on the in-memory working image; `binarize_file`
preserves the notebook's original file-based behavior for parity testing.
"""

from pathlib import Path

import cv2
import doxapy
import numpy as np

from .enlarge import antialias_binary

ALGORITHMS = [
    "OTSU", "BERNSEN", "NIBLACK", "SAUVOLA", "WOLF", "GATOS",
    "NICK", "SU", "TRSINGH", "BATAINEH", "ISAUVOLA", "WAN",
]


def flatten_alpha_to_white(img: np.ndarray) -> np.ndarray:
    """RGBA -> grayscale, with transparent regions turned white first.

    Mirrors the identical block duplicated in the notebook's
    `all_binarize_algos` and `binarize` cells.
    """
    if img.ndim == 3 and img.shape[2] == 4:
        alpha = img[:, :, 3]
        rgb = img[:, :, :3]
        white = np.full_like(rgb, 255)
        rgb_flat = np.where(alpha[:, :, None] == 0, white, rgb)
        return cv2.cvtColor(rgb_flat, cv2.COLOR_RGB2GRAY)
    if img.ndim == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def _run_algorithm(gray_img: np.ndarray, func: str) -> np.ndarray:
    binary_image = np.empty(gray_img.shape, gray_img.dtype)
    facsimile = doxapy.Binarization(getattr(doxapy.Binarization.Algorithms, func))
    facsimile.initialize(gray_img)
    facsimile.to_binary(binary_image)
    return binary_image


def _postprocess(
    binary_image: np.ndarray, thicken_lines: bool, transparent: bool, antialias: bool = False
) -> np.ndarray:
    if thicken_lines:
        kernel = np.ones((3, 3), np.uint8)
        binary_image = cv2.erode(binary_image, kernel, iterations=1)

    if antialias:
        # Before the transparent branch so soft edges become partial alpha.
        binary_image = antialias_binary(binary_image)

    if transparent:
        h, w = binary_image.shape
        output = np.zeros((h, w, 4), dtype=np.uint8)
        output[..., 0:3] = 0
        # 255 - gray: identical to the 0/255 mapping, but keeps anti-aliased edges as partial alpha.
        output[..., 3] = 255 - binary_image
        return output

    return binary_image


def all_binarize_algos(img: np.ndarray) -> list[np.ndarray]:
    """Run every algorithm in ALGORITHMS, return the 12 binary images in order."""
    gray_img = flatten_alpha_to_white(img)
    return [_run_algorithm(gray_img, algo) for algo in ALGORITHMS]


def render_algorithm_grid(
    img: np.ndarray,
    cell_size: int = 600,
    label_height: int = 36,
    padding: int = 12,
) -> np.ndarray:
    """Tile all 12 algorithms' output into one 3x4 labeled grid image.

    Mirrors the notebook's plot_all_binarize() (a matplotlib 3x4 grid saved
    to all_bin.png), but composed with cv2 so it can be displayed directly
    as the working image rather than in a separate plot window. Never
    upscales beyond the source resolution (only downscales, so cells stay
    sharp); downscaling uses INTER_AREA (correct for shrinking) while any
    upscale of a small source uses INTER_CUBIC instead of blocky INTER_AREA.
    """
    results = all_binarize_algos(img)
    cols, rows = 4, 3

    h0, w0 = results[0].shape[:2]
    scale = min(cell_size / w0, cell_size / h0, 1.0)
    thumb_w, thumb_h = max(1, round(w0 * scale)), max(1, round(h0 * scale))
    interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC

    cell_w = thumb_w + 2 * padding
    cell_h = thumb_h + label_height + 2 * padding

    canvas = np.full((rows * cell_h, cols * cell_w, 3), 255, dtype=np.uint8)

    for i, (algo, binary) in enumerate(zip(ALGORITHMS, results)):
        r, c = divmod(i, cols)
        thumb = binary if scale == 1.0 else cv2.resize(binary, (thumb_w, thumb_h), interpolation=interp)
        thumb_rgb = cv2.cvtColor(thumb, cv2.COLOR_GRAY2BGR)

        x0 = c * cell_w + padding
        y0 = r * cell_h + label_height + padding
        canvas[y0:y0 + thumb_h, x0:x0 + thumb_w] = thumb_rgb

        cv2.putText(
            canvas, algo, (c * cell_w + padding, r * cell_h + label_height - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2, cv2.LINE_AA,
        )

    return canvas


def binarize_array(
    img: np.ndarray,
    func: str = "WOLF",
    thicken_lines: bool = False,
    transparent: bool = False,
    antialias: bool = False,
) -> np.ndarray:
    """Binarize an in-memory image (BGR/BGRA/grayscale, OpenCV convention).

    Returns a grayscale binary image, or an RGBA image with white pixels made
    transparent if `transparent=True`.
    """
    gray_img = flatten_alpha_to_white(img)
    binary_image = _run_algorithm(gray_img, func)
    return _postprocess(binary_image, thicken_lines, transparent, antialias)


def threshold_array(
    img: np.ndarray,
    thresh: int = 127,
    thicken_lines: bool = False,
    transparent: bool = False,
    antialias: bool = False,
) -> np.ndarray:
    """Plain global thresholding (cv2.threshold, THRESH_BINARY) at a fixed value.

    Unlike the 12 doxapy algorithms (which pick their own threshold per-pixel
    or per-image), this applies a single user-chosen cutoff (0-255) to every
    pixel — the manual-threshold slider in the GUI.
    """
    gray_img = flatten_alpha_to_white(img)
    _, binary_image = cv2.threshold(gray_img, thresh, 255, cv2.THRESH_BINARY)
    return _postprocess(binary_image, thicken_lines, transparent, antialias)


def binarize_file(
    img_file,
    func: str = "WOLF",
    save: bool = False,
    thicken_lines: bool = False,
    svg_format: bool = False,
    transparent: bool = False,
) -> np.ndarray:
    """File-based wrapper matching the notebook's original `binarize()` signature."""
    img_file = Path(img_file)
    img = cv2.imread(str(img_file), cv2.IMREAD_UNCHANGED)
    output = binarize_array(img, func=func, thicken_lines=thicken_lines, transparent=transparent)

    if save:
        output_path = img_file.with_name(f"{img_file.stem}_{func}.png")
        cv2.imwrite(str(output_path), output)

    if svg_format:
        from .svg_export import png_to_svg

        svg_path = img_file.with_name(f"{img_file.stem}_{func}.svg")
        png_to_svg(output, svg_path)

    return output
