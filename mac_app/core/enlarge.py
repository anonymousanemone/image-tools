"""Image enlarging and binary anti-aliasing (OpenCV BGR(A)/grayscale arrays).

* Simple: bicubic resize.
* Sharp (line art): Lanczos resize, then a light blur scaled to the factor to
  smooth stair-stepped edges, then (for binary input) a re-threshold at 127 to
  snap back to crisp black/white. When enlarging before binarizing, the
  binarization does that final threshold.
"""

import cv2
import numpy as np

# Blur sigma per unit of enlarge factor (tuned by eye; higher closes small gaps).
_SHARP_BLUR_PER_FACTOR = 0.5
# Blur sigma (px) for anti-aliasing binarized edges.
ANTIALIAS_SIGMA = 0.8


def _resize(img: np.ndarray, factor: float, interpolation: int) -> np.ndarray:
    h, w = img.shape[:2]
    size = (max(1, round(w * factor)), max(1, round(h * factor)))
    return cv2.resize(img, size, interpolation=interpolation)


def _sharp_gray(gray: np.ndarray, factor: float, binary: bool) -> np.ndarray:
    big = _resize(gray, factor, cv2.INTER_LANCZOS4)
    big = cv2.GaussianBlur(big, (0, 0), _SHARP_BLUR_PER_FACTOR * factor)
    if binary:
        _, big = cv2.threshold(big, 127, 255, cv2.THRESH_BINARY)
    return big


def enlarge_array(
    img: np.ndarray, factor: float, sharp: bool = False, binary: bool = False
) -> np.ndarray:
    """Enlarge `img` by `factor` (see module docstring for the modes).

    With `sharp`, `binary=True` marks black/white input (grayscale 0/255, or
    RGBA with the shape in alpha) so the output is re-thresholded.
    """
    if factor == 1:
        return img
    if not sharp:
        return _resize(img, factor, cv2.INTER_CUBIC)

    if img.ndim == 2:
        return _sharp_gray(img, factor, binary)

    if img.shape[2] == 4 and binary:
        alpha = _sharp_gray(img[:, :, 3], factor, binary=True)
        out = np.zeros((*alpha.shape, 4), dtype=np.uint8)
        out[:, :, 3] = alpha
        return out

    channels = cv2.split(img)
    return cv2.merge([_sharp_gray(c, factor, binary=False) for c in channels])


def antialias_binary(binary: np.ndarray) -> np.ndarray:
    """Soften a 0/255 image's stair-stepped edges into gray with a small blur."""
    return cv2.GaussianBlur(binary, (0, 0), ANTIALIAS_SIGMA)
