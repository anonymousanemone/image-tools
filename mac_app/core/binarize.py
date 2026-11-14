"""Document binarization (port of img_binarizer.ipynb).

The 12 doxapy algorithms plus a manual global threshold, all array in/array out.
"""

import cv2
import doxapy
import numpy as np

from .enlarge import antialias_binary

ALGORITHMS = [
    "OTSU", "BERNSEN", "NIBLACK", "SAUVOLA", "WOLF", "GATOS",
    "NICK", "SU", "TRSINGH", "BATAINEH", "ISAUVOLA", "WAN",
]


def flatten_alpha_to_white(img: np.ndarray) -> np.ndarray:
    """BGR(A) -> grayscale, with transparent pixels turned white first."""
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
        # Black ink -> opaque, white -> clear; anti-aliased edges -> partial alpha.
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
    """Tile all 12 algorithms' output into one labeled 3x4 grid image.

    Cells are downscaled to fit `cell_size`, never upscaled.
    """
    results = all_binarize_algos(img)
    cols, rows = 4, 3

    h0, w0 = results[0].shape[:2]
    scale = min(cell_size / w0, cell_size / h0, 1.0)
    thumb_w, thumb_h = max(1, round(w0 * scale)), max(1, round(h0 * scale))

    cell_w = thumb_w + 2 * padding
    cell_h = thumb_h + label_height + 2 * padding

    canvas = np.full((rows * cell_h, cols * cell_w, 3), 255, dtype=np.uint8)

    for i, (algo, binary) in enumerate(zip(ALGORITHMS, results)):
        r, c = divmod(i, cols)
        thumb = binary if scale == 1.0 else cv2.resize(binary, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
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
    """Binarize a BGR(A)/grayscale image with doxapy algorithm `func`.

    Returns grayscale (0/255 unless `antialias`), or RGBA with white made transparent
    if `transparent`.
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
    """Global threshold at a fixed 0-255 cutoff (the GUI's manual-threshold slider)."""
    gray_img = flatten_alpha_to_white(img)
    _, binary_image = cv2.threshold(gray_img, thresh, 255, cv2.THRESH_BINARY)
    return _postprocess(binary_image, thicken_lines, transparent, antialias)
