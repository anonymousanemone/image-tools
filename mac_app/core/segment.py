"""macOS Vision-based background removal.

Vendored from OstracaBinarization/src/segmentation.py (vision_available,
segment_vision, _vision_pixel_buffer_to_mask, find_contour) — the other
segmentation methods in that file (HSV/k-means, saturation Otsu) are
intentionally not included; this app exposes background removal as a single
macOS-Vision-only button.
"""

import cv2
import numpy as np


def vision_available() -> bool:
    """Whether macOS Vision-based segmentation can run (macOS + pyobjc frameworks)."""
    try:
        import Vision  # noqa: F401
        import Quartz  # noqa: F401
        from Foundation import NSData  # noqa: F401
    except ImportError:
        return False
    return hasattr(Vision, "VNGenerateForegroundInstanceMaskRequest")


def segment_vision(img: np.ndarray, debug: bool = False) -> np.ndarray:
    """Foreground subject mask via macOS's Vision framework.

    This is the same on-device model behind "Remove Background" in Preview
    and "Lift Subject" in Photos (VNGenerateForegroundInstanceMaskRequest,
    macOS 13+). Requires pyobjc-framework-Vision/-Quartz/-Cocoa and only
    runs on macOS.
    """
    try:
        import Vision
        import Quartz
        from Foundation import NSData
    except ImportError as e:
        raise RuntimeError(
            "Vision-based segmentation requires macOS with pyobjc installed: "
            "pip install pyobjc-framework-Vision pyobjc-framework-Quartz pyobjc-framework-Cocoa"
        ) from e

    ok, encoded = cv2.imencode(".png", img)
    if not ok:
        raise ValueError("Failed to encode image for Vision")
    nsdata = NSData.dataWithBytes_length_(encoded.tobytes(), len(encoded))
    img_src = Quartz.CGImageSourceCreateWithData(nsdata, None)
    if img_src is None:
        raise ValueError("Vision could not read the image")
    cgimg = Quartz.CGImageSourceCreateImageAtIndex(img_src, 0, None)

    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cgimg, None)
    request = Vision.VNGenerateForegroundInstanceMaskRequest.alloc().init()
    ok, err = handler.performRequests_error_([request], None)
    if not ok:
        raise RuntimeError(f"Vision request failed: {err}")

    results = request.results()
    if not results:
        raise ValueError("Vision did not find a foreground subject in this image")

    observation = results[0]
    instances = observation.allInstances()
    if not instances:
        raise ValueError("Vision did not find a foreground subject in this image")

    pixel_buffer, err = observation.generateMaskForInstances_error_(instances, None)
    if pixel_buffer is None:
        raise RuntimeError(f"Vision mask generation failed: {err}")

    mask = _vision_pixel_buffer_to_mask(pixel_buffer, Quartz)
    h, w = img.shape[:2]
    mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_LINEAR)
    _, binary = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    if debug:
        cv2.imshow("Vision foreground mask", binary)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return binary


def _vision_pixel_buffer_to_mask(pixel_buffer, Quartz) -> np.ndarray:
    """Read a CVPixelBuffer (OneComponent8 or OneComponent32Float) into a uint8 0-255 mask."""
    fmt = Quartz.CVPixelBufferGetPixelFormatType(pixel_buffer)
    Quartz.CVPixelBufferLockBaseAddress(pixel_buffer, 0)
    try:
        w = Quartz.CVPixelBufferGetWidth(pixel_buffer)
        h = Quartz.CVPixelBufferGetHeight(pixel_buffer)
        bpr = Quartz.CVPixelBufferGetBytesPerRow(pixel_buffer)
        base = Quartz.CVPixelBufferGetBaseAddress(pixel_buffer)
        buf = base.as_buffer(bpr * h)
        if fmt == Quartz.kCVPixelFormatType_OneComponent32Float:
            arr = np.frombuffer(buf, dtype=np.float32).reshape(h, bpr // 4)[:, :w].copy()
            arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
        else:
            arr = np.frombuffer(buf, dtype=np.uint8).reshape(h, bpr)[:, :w].copy()
    finally:
        Quartz.CVPixelBufferUnlockBaseAddress(pixel_buffer, 0)
    return arr


def find_contour(mask: np.ndarray, debug: bool = False):
    """Keep only the largest external contour of a binary mask, filled in.

    Returns (contour_line, filled_mask), both same shape as `mask`.
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if debug:
        print(f"  Found {len(contours)} contour(s)")
    assert len(contours) > 0, "No contours found — boundary detection failed."

    largest_contour = max(contours, key=cv2.contourArea)
    filled_mask = np.zeros_like(mask)
    cv2.drawContours(filled_mask, [largest_contour], -1, 255, thickness=cv2.FILLED)

    contour_line = np.zeros_like(mask)
    cv2.drawContours(contour_line, [largest_contour], -1, 255, thickness=2)

    if debug:
        if len(mask.shape) == 2:
            outline = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        else:
            outline = mask.copy()
        cv2.drawContours(outline, [largest_contour], -1, (0, 0, 255), 2)
        cv2.imshow("Original", mask)
        cv2.imshow("Boundary mask (raw)", mask)
        cv2.imshow("Largest Contour Filled Mask", filled_mask)
        cv2.imshow("Largest Contour Outlined", outline)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return contour_line, filled_mask


def remove_background(img: np.ndarray) -> np.ndarray:
    """One-button remove background: Vision mask -> largest-contour cleanup -> RGBA cutout."""
    mask = segment_vision(img)
    _, filled_mask = find_contour(mask)

    if img.ndim == 2:
        bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    else:
        bgr = img

    b, g, r = cv2.split(bgr)
    return cv2.merge([b, g, r, filled_mask])
