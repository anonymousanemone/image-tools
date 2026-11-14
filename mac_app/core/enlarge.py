"""Image enlarging (pre- or post-binarization) and binary anti-aliasing.

Two enlarge modes, both array-in/array-out (OpenCV BGR/BGRA/grayscale):

* ``sharp=False`` — plain bicubic resize (cv2.INTER_CUBIC).
* ``sharp=True`` — made for line art / scanned documents, where the goal is a
  bigger image whose strokes stay crisp and smooth rather than blocky or blurry:
    1. Lanczos resize (cv2.INTER_LANCZOS4), which keeps edges steeper than
       bicubic.
    2. A light Gaussian blur scaled to the enlarge factor, which averages out
       pixel-level speckle so a later threshold doesn't turn it into noise.
    3. If the input is already binary (``binary=True``), re-threshold at 127.
       This is the standard "upscale smoothly, then threshold again" approach:
       the interpolation rounds off the stair-stepped edges of the small
       image, and the threshold snaps the result back to crisp black/white.
       When enlarging *before* binarizing, the binarization step itself plays
       the role of that final threshold.

Written from the general technique, not copied from a library. References
consulted while designing it:
  - OpenCV resize / interpolation flags:
    https://docs.opencv.org/4.x/da/d54/group__imgproc__transform.html
  - Binary Document Image Super Resolution for Improved Readability and OCR
    Performance (bicubic upscale as the first stage, then sharpening edges):
    https://arxiv.org/abs/1812.02475
  - Scale2x/EPX (pixel-art upscalers) and OpenCV's dnn_superres (EDSR/ESPCN/
    FSRCNN) were looked at and deliberately not used: the first is for pixel
    art, the second needs downloaded model weights.
"""

import cv2
import numpy as np

# Blur strength per unit of enlarge factor; chosen by eye on a noisy text scan —
# higher smooths edges more but starts closing small counters/gaps.
_SHARP_BLUR_PER_FACTOR = 0.5
# Gaussian sigma (px) used to soften binarized edges for anti-aliasing.
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
    """Enlarge `img` by `factor` (>1). See module docstring for the modes.

    `binary=True` (only used with ``sharp``) says the input is a black/white
    result — grayscale 0/255, or RGBA whose shape is carried by its alpha
    channel — so the output is re-thresholded back to pure black/white.
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
    """Soften the hard 1-pixel stair-steps of a 0/255 grayscale image with a
    small Gaussian blur, giving edges intermediate gray values."""
    return cv2.GaussianBlur(binary, (0, 0), ANTIALIAS_SIGMA)
