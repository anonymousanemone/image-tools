"""Discrete, combinable image filters for the Binarizer tab's filter toolbox.

These are new thin cv2 wrappers (no 1:1 notebook source) exposed as
individually-clickable buttons rather than a fixed automatic pipeline.
Default parameter values borrow from OstracaBinarization/src/processing.py's
run_binarize()/DEFAULT_OPTIONS as sane starting points.
"""

import cv2
import numpy as np


def bilateral_filter(img: np.ndarray, d: int = 5, sigma_color: float = 50, sigma_space: float = 20) -> np.ndarray:
    return cv2.bilateralFilter(img, d=d, sigmaColor=sigma_color, sigmaSpace=sigma_space)


def gaussian_filter(img: np.ndarray, ksize: int = 5, sigma: float = 0) -> np.ndarray:
    ksize = ksize | 1  # must be odd
    return cv2.GaussianBlur(img, (ksize, ksize), sigma)


def median_filter(img: np.ndarray, ksize: int = 5) -> np.ndarray:
    ksize = ksize | 1
    return cv2.medianBlur(img, ksize)


def erode(img: np.ndarray, ksize: int = 3, iterations: int = 1) -> np.ndarray:
    kernel = np.ones((ksize, ksize), np.uint8)
    return cv2.erode(img, kernel, iterations=iterations)


def dilate(img: np.ndarray, ksize: int = 3, iterations: int = 1) -> np.ndarray:
    kernel = np.ones((ksize, ksize), np.uint8)
    return cv2.dilate(img, kernel, iterations=iterations)


def morph_open(img: np.ndarray, ksize: int = 5) -> np.ndarray:
    kernel = np.ones((ksize, ksize), np.uint8)
    return cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)


def morph_close(img: np.ndarray, ksize: int = 10) -> np.ndarray:
    kernel = np.ones((ksize, ksize), np.uint8)
    return cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)


def find_contour_outline(img: np.ndarray) -> np.ndarray:
    """Standalone 'find contour' filter button: binary/gray in, largest contour outline mask out."""
    from .segment import find_contour

    if img.ndim == 3:
        gray = cv2.cvtColor(img[:, :, :3] if img.shape[2] == 4 else img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    contour_line, _ = find_contour(binary)
    return contour_line


FILTERS = {
    "Bilateral": bilateral_filter,
    "Gaussian": gaussian_filter,
    "Median": median_filter,
    "Erode": erode,
    "Dilate": dilate,
    "Morph Open": morph_open,
    "Morph Close": morph_close,
    "Find Contour": find_contour_outline,
}
