"""Reduce a grainy/noisy scan (e.g. a painted papyrus plate) to n flat colors,
using its dark outlines as a guide for where color blobs begin and end.

Plain quantizers (ImageMagick's image_quantize, etc.) work pixel-by-pixel, so
paper grain and print noise survive as speckle. This instead:

  1. Denoises in Lab space with an edge-preserving filter, so blobs flatten
     out but outlines stay sharp.
  2. Binarizes to find the ink: anything locally darker than its
     surroundings (Sauvola) or globally very dark. Ink becomes one color.
  3. Runs k-means on the non-ink pixels to pick the other n-1 colors, with
     lightness down-weighted so paper shading doesn't hog colors, then
     merges near-duplicates (so n acts as a maximum). Or snaps to a fixed
     --palette instead.
  4. Cleans labels using the ink as walls: each region enclosed by ink that
     is small enough gets a single majority color; inside bigger regions a
     majority filter removes grain; leftover specks below --min-area are
     absorbed by the nearest larger blob.

Optionally (--bin-method), a doxapy binarization of the scan is Gaussian
blurred into a soft "near ink" map and added as an extra k-means feature next
to Lab, so clusters can also separate by how close/dense the linework is.

Usage:
    python img_colorquantize.py input.jpg -n 10
    python img_colorquantize.py input.jpg -n 10 -o out.png --debug
    python img_colorquantize.py input.jpg -n 10 --bin-method WOLF --bin-blur 5 --bin-weight 0.5
    python img_colorquantize.py input.jpg --palette 1a1a1a f3e3c3 a0201a 2e6b5e ...
"""
import argparse
from pathlib import Path

import cv2
import doxapy
import numpy as np
from scipy import ndimage
from skimage.filters import threshold_sauvola
from sklearn.cluster import MiniBatchKMeans

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
BIN_METHODS = ["OTSU", "BERNSEN", "NIBLACK", "SAUVOLA", "WOLF", "GATOS",
               "NICK", "SU", "TRSINGH", "BATAINEH", "ISAUVOLA", "WAN"]


def denoise(bgr: np.ndarray, strength: int, spatial: int, color: int) -> np.ndarray:
    """Median to kill salt/pepper grain, bilateral passes to calm texture,
    then mean-shift to pull each area toward its dominant color."""
    out = cv2.medianBlur(bgr, 5)
    for _ in range(strength):
        out = cv2.bilateralFilter(out, d=9, sigmaColor=30, sigmaSpace=9)
    return cv2.pyrMeanShiftFiltering(out, sp=spatial, sr=color)


def ink_mask(bgr: np.ndarray, window: int, k: float, dark_pct: float, max_gray: int,
             min_ink: int) -> np.ndarray:
    """Boolean mask of outline/ink pixels."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    # Local threshold finds thin lines, but at the edge of a dark paint area
    # (red next to pale paper) it also flags the paint; requiring real
    # darkness keeps only the ink
    local = (gray < threshold_sauvola(gray, window_size=window, k=k)) & (gray < max_gray)
    # Sauvola misses the interior of large solid black areas; catch those globally
    dark = gray < np.percentile(gray, dark_pct)
    return remove_small(local | dark, min_ink)


def soft_binary(bgr: np.ndarray, method: str, sigma: float) -> np.ndarray:
    """doxapy binarization (ink = 1), Gaussian blurred into a 0-1 map of how
    much ink is nearby."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    binary = np.empty(gray.shape, gray.dtype)
    algo = doxapy.Binarization(getattr(doxapy.Binarization.Algorithms, method))
    algo.initialize(gray)
    algo.to_binary(binary)
    ink = (binary == 0).astype(np.float32)
    return cv2.GaussianBlur(ink, (0, 0), sigma) if sigma > 0 else ink


def remove_small(mask: np.ndarray, min_area: int) -> np.ndarray:
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    keep = stats[:, cv2.CC_STAT_AREA] >= min_area
    keep[0] = False
    return keep[lab]


def fit_palette(lab_px: np.ndarray, k: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    sample = lab_px[rng.choice(len(lab_px), size=min(200_000, len(lab_px)), replace=False)]
    km = MiniBatchKMeans(n_clusters=k, random_state=seed, n_init=5, batch_size=4096).fit(sample)
    return km.cluster_centers_


def merge_close(centers: np.ndarray, counts: np.ndarray, thresh: float) -> np.ndarray:
    """Greedily merge the closest pair of centers (count-weighted) until every
    pair is at least thresh apart. Returns the surviving centers."""
    centers, counts = list(centers), list(counts.astype(float))
    while len(centers) > 1:
        c = np.array(centers)
        d = np.sqrt(((c[:, None] - c[None]) ** 2).sum(-1))
        np.fill_diagonal(d, np.inf)
        i, j = np.unravel_index(d.argmin(), d.shape)
        if d[i, j] >= thresh:
            break
        tot = counts[i] + counts[j]
        centers[i] = (centers[i] * counts[i] + centers[j] * counts[j]) / max(tot, 1)
        counts[i] = tot
        del centers[j], counts[j]
    return np.array(centers)


def assign(lab_px: np.ndarray, centers: np.ndarray) -> np.ndarray:
    labels = np.empty(len(lab_px), dtype=np.int32)
    for i in range(0, len(lab_px), 1_000_000):
        chunk = lab_px[i:i + 1_000_000]
        d = ((chunk[:, None, :] - centers[None, :, :]) ** 2).sum(-1)
        labels[i:i + 1_000_000] = d.argmin(1)
    return labels


def majority_filter(labels: np.ndarray, valid: np.ndarray, n: int, size: int) -> np.ndarray:
    """Per-pixel mode over a size x size window, counting only valid (non-ink)
    pixels so colors don't bleed across outlines."""
    best = np.full(labels.shape, -1.0, dtype=np.float32)
    out = labels.copy()
    for c in range(n):
        votes = cv2.boxFilter(((labels == c) & valid).astype(np.float32), -1, (size, size), normalize=False)
        better = votes > best
        best[better] = votes[better]
        out[better] = c
    out[~valid] = labels[~valid]
    return out


def fill_regions(labels: np.ndarray, ink: np.ndarray, n: int, max_region: int) -> np.ndarray:
    """Every ink-enclosed region smaller than max_region gets its majority color."""
    nreg, reg = cv2.connectedComponents((~ink).astype(np.uint8), connectivity=4)
    counts = np.zeros((nreg, n), dtype=np.int64)
    np.add.at(counts, (reg[~ink], labels[~ink]), 1)
    sizes = counts.sum(1)
    small = (sizes > 0) & (sizes < max_region)
    small[0] = False if ink[reg == 0].all() else small[0]
    majority = counts.argmax(1)
    out = labels.copy()
    sel = small[reg] & ~ink
    out[sel] = majority[reg[sel]]
    return out


def absorb_specks(labels: np.ndarray, ink: np.ndarray, n: int, min_area: int) -> np.ndarray:
    """Blobs (per color) smaller than min_area are replaced by the nearest
    surviving non-ink pixel's color."""
    keep = ink.copy()
    for c in range(n):
        m = (labels == c) & ~ink
        keep |= remove_small(m, min_area)
    if keep.all():
        return labels
    # nearest kept non-ink pixel
    src = keep & ~ink
    _, (iy, ix) = ndimage.distance_transform_edt(~src, return_indices=True)
    out = labels.copy()
    fix = ~keep
    out[fix] = labels[iy[fix], ix[fix]]
    return out


def parse_hex(colors: list[str]) -> np.ndarray:
    rgb = np.array([[int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)] for h in colors], dtype=np.uint8)
    return rgb


def to_lab(rgb_or_bgr: np.ndarray, code: int) -> np.ndarray:
    return cv2.cvtColor(rgb_or_bgr.reshape(-1, 1, 3), code).reshape(-1, 3).astype(np.float32)


def quantize(img_bgr, n, palette_hex=None, strength=3, ms_spatial=12, ms_color=20, l_weight=0.35, merge=14.0,
             sauvola_window=31, sauvola_k=0.15, dark_pct=6.0, ink_max_gray=105, min_ink=30, smooth=9,
             max_region=4000, min_area=80, seed=0, bin_method=None, bin_blur=5.0, bin_weight=0.5):
    h, w = img_bgr.shape[:2]
    smooth_bgr = denoise(img_bgr, strength, ms_spatial, ms_color)
    lab = to_lab(smooth_bgr, cv2.COLOR_BGR2LAB).reshape(h, w, 3)
    ink = ink_mask(img_bgr, sauvola_window, sauvola_k, dark_pct, ink_max_gray, min_ink)
    # Cluster with lightness down-weighted, so shading/staining in the paper
    # doesn't eat up colors that should go to actual hue differences
    wts = np.array([l_weight, 1.0, 1.0], dtype=np.float32)
    feat = lab * wts
    soft = None
    if bin_method:
        # Extra feature: blurred binarization scaled to Lab's 0-100 range
        soft = soft_binary(img_bgr, bin_method, bin_blur)
        if not palette_hex:
            feat = np.dstack([feat, soft * 100 * bin_weight])

    if palette_hex:
        pal_rgb = parse_hex(palette_hex)
        pal_lab = to_lab(pal_rgb, cv2.COLOR_RGB2LAB)
        ink_idx = int(pal_lab[:, 0].argmin())  # darkest palette color is ink
        centers = pal_lab * wts
    else:
        paper = feat[~ink]
        centers = fit_palette(paper, n - 1, seed)
        if merge > 0:
            sample = paper[::max(1, len(paper) // 500_000)]
            counts = np.bincount(assign(sample, centers), minlength=len(centers))
            centers = merge_close(centers, counts, merge)
        # ink color from the darkest core of the strokes, not their soft edges
        ink_px = feat[ink]
        core = ink_px[ink_px[:, 0] <= np.percentile(ink_px[:, 0], 30)]
        centers = np.vstack([centers, np.median(core, axis=0)])
        pal_lab = centers[:, :3] / wts
        ink_idx = len(pal_lab) - 1
    k = len(pal_lab)

    labels = assign(feat.reshape(-1, feat.shape[-1]), centers).reshape(h, w)
    labels[ink] = ink_idx

    labels = fill_regions(labels, ink, k, max_region)
    labels = majority_filter(labels, ~ink, k, smooth)
    labels = absorb_specks(labels, ink, k, min_area)

    if not palette_hex:
        pal_rgb = cv2.cvtColor(pal_lab.reshape(-1, 1, 3).round().astype(np.uint8),
                               cv2.COLOR_LAB2RGB).reshape(-1, 3)
    return pal_rgb[labels], pal_rgb, {"denoised": smooth_bgr, "ink": ink, "soft": soft}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path)
    ap.add_argument("-n", "--colors", type=int, default=10, help="total colors including ink (default 10)")
    ap.add_argument("-o", "--output", type=Path, help="default: outputs/<input>_q<n>.png in this repo")
    ap.add_argument("--palette", nargs="+", help="fixed hex colors to snap to instead of k-means (darkest = ink)")
    ap.add_argument("--strength", type=int, default=3, help="bilateral denoise passes (default 3)")
    ap.add_argument("--ms-spatial", type=int, default=12, help="mean-shift spatial radius (px)")
    ap.add_argument("--ms-color", type=int, default=20, help="mean-shift color radius; higher = flatter")
    ap.add_argument("--l-weight", type=float, default=0.35,
                    help="weight of lightness vs. hue when clustering; lower ignores shading more")
    ap.add_argument("--merge", type=float, default=14.0,
                    help="merge k-means colors closer than this (weighted Lab); 0 = keep exactly n")
    ap.add_argument("--sauvola-window", type=int, default=31, help="odd window size for local ink threshold")
    ap.add_argument("--sauvola-k", type=float, default=0.15, help="higher = less ink detected")
    ap.add_argument("--dark-pct", type=float, default=6.0,
                    help="percentile of gray below which a pixel is always ink (default 6)")
    ap.add_argument("--ink-max-gray", type=int, default=105,
                    help="outline ink must be darker than this (0-255); raise if faint lines vanish")
    ap.add_argument("--min-ink", type=int, default=30, help="drop ink specks smaller than this (px)")
    ap.add_argument("--smooth", type=int, default=9, help="majority filter window (px)")
    ap.add_argument("--max-region", type=int, default=4000,
                    help="ink-enclosed regions smaller than this get a single color (px)")
    ap.add_argument("--min-area", type=int, default=80, help="color blobs smaller than this get absorbed (px)")
    ap.add_argument("--bin-method", choices=BIN_METHODS,
                    help="add a blurred doxapy binarization as an extra k-means feature (default off)")
    ap.add_argument("--bin-blur", type=float, default=5.0, help="Gaussian sigma (px) for --bin-method (default 5)")
    ap.add_argument("--bin-weight", type=float, default=0.5,
                    help="weight of the --bin-method feature vs. color; 0.5 = up to 50 Lab units (default 0.5)")
    ap.add_argument("--debug", action="store_true", help="also save denoised image, ink mask and palette swatch")
    args = ap.parse_args()

    img = cv2.imread(str(args.input), cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit(f"could not read {args.input}")
    n = len(args.palette) if args.palette else args.colors
    out_rgb, pal, dbg = quantize(
        img, n, args.palette, args.strength, args.ms_spatial, args.ms_color, args.l_weight, args.merge,
        args.sauvola_window, args.sauvola_k, args.dark_pct, args.ink_max_gray, args.min_ink, args.smooth,
        args.max_region, args.min_area, bin_method=args.bin_method, bin_blur=args.bin_blur,
        bin_weight=args.bin_weight,
    )

    tag = f"_{args.bin_method}" if args.bin_method else ""
    out = args.output or OUTPUT_DIR / f"{args.input.stem}_q{n}{tag}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    if len(pal) < n:
        print(f"merged near-duplicate colors: {n} -> {len(pal)} (use --merge 0 to keep all {n})")
    cv2.imwrite(str(out), cv2.cvtColor(out_rgb, cv2.COLOR_RGB2BGR))
    print(f"wrote {out}")
    print("palette:", " ".join(f"#{r:02x}{g:02x}{b:02x}" for r, g, b in pal))

    if args.debug:
        stem = out.with_suffix("")
        cv2.imwrite(f"{stem}_denoised.png", dbg["denoised"])
        cv2.imwrite(f"{stem}_ink.png", np.where(dbg["ink"], 0, 255).astype(np.uint8))
        if dbg["soft"] is not None:
            cv2.imwrite(f"{stem}_soft.png", (255 - dbg["soft"] * 255).round().astype(np.uint8))
        swatch = np.repeat(np.repeat(pal[None, :, :], 60, 0), 60, 1)
        cv2.imwrite(f"{stem}_palette.png", cv2.cvtColor(swatch, cv2.COLOR_RGB2BGR))


if __name__ == "__main__":
    main()
