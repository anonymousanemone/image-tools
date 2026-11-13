"""Build a layered MediBang Paint (.mdp) file from a scanned plate, ready for
hand cleanup:

    top     -- ink: a doxapy binarization, black on a transparent background
    middle  -- colors: img_colorquantize.py's flat-color version
    bottom  -- original: the untouched scan, for reference

Usage:
    python mdp_process.py input.jpg
    python mdp_process.py input.jpg --method WOLF --despeckle 40 -n 8
    python mdp_process.py input.jpg -o outputs/plate.mdp --thicken

Binarization methods (from doxapy, as in img_binarizer.ipynb):
    OTSU BERNSEN NIBLACK SAUVOLA WOLF GATOS NICK SU TRSINGH BATAINEH ISAUVOLA WAN

.mdp layout (reverse-engineered from MediBang Paint Pro files):
    "mdipack\\0" + u32 0 + u32 xml_len + u32 bin_len, then the XML, then
    "PAC " chunks: u32 chunk_len, u32 zlib_flag, u32 data_len, u32 raw_len,
    48 zero bytes, 64-byte name, data. A layer chunk is u32 n_tiles,
    u32 tile_size (128), then per tile u32 x, u32 y, u32 0, u32 len and a
    zlib stream of straight-alpha BGRA, padded to 4 bytes. Layers are listed
    bottom to top. The thumbnail is one plain zlib BGRA chunk.
"""
import argparse
import struct
import time
import zlib
from pathlib import Path

import cv2
import doxapy
import numpy as np

from img_colorquantize import OUTPUT_DIR, quantize

METHODS = ["OTSU", "BERNSEN", "NIBLACK", "SAUVOLA", "WOLF", "GATOS",
           "NICK", "SU", "TRSINGH", "BATAINEH", "ISAUVOLA", "WAN"]
TILE = 128
THUMB_MAX = 256


def binarize(img_bgr: np.ndarray, method: str, thicken: bool, despeckle: int = 0) -> np.ndarray:
    """Black ink on a transparent background, as straight-alpha BGRA. Ink
    blobs smaller than despeckle px (paper grain) are dropped."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    binary = np.empty(gray.shape, gray.dtype)
    algo = doxapy.Binarization(getattr(doxapy.Binarization.Algorithms, method))
    algo.initialize(gray)
    algo.to_binary(binary)
    if thicken:
        binary = cv2.erode(binary, np.ones((3, 3), np.uint8), iterations=1)
    if despeckle:
        ink = binary == 0
        _, lab, stats, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
        small = stats[:, cv2.CC_STAT_AREA] < despeckle
        small[0] = False
        binary[small[lab] & ink] = 255
    out = np.zeros((*gray.shape, 4), np.uint8)
    out[..., 3] = np.where(binary == 255, 0, 255)
    return out


def to_bgra(img_bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2BGRA)


def pac_chunk(name: str, data: bytes, zlib_flag: int, raw_len: int) -> bytes:
    header = b"PAC " + struct.pack("<4I", 132 + len(data), zlib_flag, len(data), raw_len)
    return header + bytes(48) + name.encode().ljust(64, b"\0") + data


def layer_data(bgra: np.ndarray) -> bytes:
    """Tile the layer, skipping fully transparent tiles."""
    h, w = bgra.shape[:2]
    tiles = []
    for ty in range(0, (h + TILE - 1) // TILE):
        for tx in range(0, (w + TILE - 1) // TILE):
            tile = bgra[ty * TILE:(ty + 1) * TILE, tx * TILE:(tx + 1) * TILE]
            if not tile[..., 3].any():
                continue
            if tile.shape[:2] != (TILE, TILE):
                padded = np.zeros((TILE, TILE, 4), np.uint8)
                padded[:tile.shape[0], :tile.shape[1]] = tile
                tile = padded
            comp = zlib.compress(np.ascontiguousarray(tile).tobytes(), 6)
            pad = -len(comp) % 4
            tiles.append(struct.pack("<4I", tx, ty, 0, len(comp)) + comp + bytes(pad))
    if not tiles:
        return struct.pack("<I", 0)
    return struct.pack("<II", len(tiles), TILE) + b"".join(tiles)


def composite(layers: list[np.ndarray]) -> np.ndarray:
    """Alpha-over composite of straight-alpha BGRA layers, bottom first."""
    out = np.zeros(layers[0].shape[:2] + (3,), np.float32)
    for lay in layers:
        a = lay[..., 3:4].astype(np.float32) / 255
        out = lay[..., :3] * a + out * (1 - a)
    return out.round().astype(np.uint8)


def write_mdp(path: Path, layers: list[tuple[str, np.ndarray]], dpi: int = 300) -> None:
    """layers: (name, BGRA array) pairs, bottom to top."""
    h, w = layers[0][1].shape[:2]
    scale = THUMB_MAX / max(w, h)
    tw, th = max(1, round(w * scale)), max(1, round(h * scale))
    thumb = cv2.resize(to_bgra(composite([l for _, l in layers])), (tw, th), interpolation=cv2.INTER_AREA)

    chunks = [pac_chunk("thumb", zlib.compress(thumb.tobytes(), 6), 1, thumb.nbytes)]
    layer_xml = []
    for i, (name, bgra) in enumerate(layers):
        data = layer_data(bgra)
        chunks.append(pac_chunk(f"layer{i}img", data, 0, len(data)))
        layer_xml.append(
            f'        <Layer ofsx="0" ofsy="0" width="{w}" height="{h}" mode="normal" alpha="255" '
            f'visible="true" protectAlpha="false" locked="false" clipping="false" masking="false" '
            f'maskingType="0" group="-1" id="{i}" draft="false" parentId="-1" name="{name}" '
            f'binType="2" bin="layer{i}img" type="32bpp" />'
        )

    now = int(time.time())
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now))
    xml = (
        '<?xml version="1.0" encoding="UTF-8" ?>\n'
        f'<Mdiapp width="{w}" height="{h}" dpi="{dpi}" checkerBG="true" '
        'bgColorR="255" bgColorG="255" bgColorB="255">\n'
        f'    <CreateTime time="{now}" timeString="{stamp}" />\n'
        f'    <UpdateTime time="{now}" timeString="{stamp}" rev="1" />\n'
        f'    <Thumb width="{tw}" height="{th}" bin="thumb" />\n'
        '    <Snaps />\n'
        '    <Guides />\n'
        f'    <Layers active="{len(layers) - 1}">\n'
        + "\n".join(layer_xml) + "\n"
        '    </Layers>\n'
        '    <appInfo name="MediBang Paint Pro" rev="86" bitType="64" />\n'
        '</Mdiapp>\n'
    ).encode()
    body = b"".join(chunks)
    path.write_bytes(b"mdipack\0" + struct.pack("<3I", 0, len(xml), len(body)) + xml + body)


def read_mdp(path: Path) -> tuple[dict, list[tuple[str, np.ndarray]]]:
    """Minimal reader, used to check write_mdp's output round-trips."""
    import xml.etree.ElementTree as ET
    f = path.read_bytes()
    assert f[:8] == b"mdipack\0", "not an .mdp file"
    xml_len, bin_len = struct.unpack("<II", f[12:20])
    root = ET.fromstring(f[20:20 + xml_len])
    w, h = int(root.get("width")), int(root.get("height"))
    chunks, p = {}, 20 + xml_len
    while p < len(f):
        assert f[p:p + 4] == b"PAC ", f"bad chunk at {p}"
        total, _, dlen, _ = struct.unpack("<4I", f[p + 4:p + 20])
        chunks[f[p + 68:p + 132].split(b"\0")[0].decode()] = f[p + 132:p + 132 + dlen]
        p += total
    layers = []
    for el in root.find("Layers"):
        data, img = chunks[el.get("bin")], np.zeros((h, w, 4), np.uint8)
        n = struct.unpack("<I", data[:4])[0]
        q = 8
        for _ in range(n):
            tx, ty, _, ln = struct.unpack("<4I", data[q:q + 16])
            tile = np.frombuffer(zlib.decompress(data[q + 16:q + 16 + ln]), np.uint8).reshape(TILE, TILE, 4)
            q += 16 + ln + (-ln % 4)
            y0, x0 = ty * TILE, tx * TILE
            img[y0:y0 + TILE, x0:x0 + TILE] = tile[:h - y0, :w - x0]
        layers.append((el.get("name"), img))
    return dict(root.attrib), layers


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path, help="default: outputs/<input>.mdp in this repo")
    ap.add_argument("--method", choices=METHODS, default="GATOS", help="binarization for the ink layer (default GATOS)")
    ap.add_argument("--despeckle", type=int, default=20,
                    help="drop ink blobs smaller than this many px (paper grain); 0 = keep all")
    ap.add_argument("--thicken", action="store_true", help="thicken ink lines by 1px")
    ap.add_argument("-n", "--colors", type=int, default=10, help="max colors for the color layer")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--check", action="store_true", help="re-read the written file and verify every layer")
    args = ap.parse_args()

    img = cv2.imread(str(args.input), cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit(f"could not read {args.input}")

    print("quantizing colors...")
    colors_rgb, pal, _ = quantize(img, args.colors)
    print("palette:", " ".join(f"#{r:02x}{g:02x}{b:02x}" for r, g, b in pal))
    print(f"binarizing ({args.method})...")
    layers = [
        ("original", to_bgra(img)),
        ("colors", to_bgra(cv2.cvtColor(colors_rgb, cv2.COLOR_RGB2BGR))),
        (f"ink {args.method}", binarize(img, args.method, args.thicken, args.despeckle)),
    ]

    out = args.output or OUTPUT_DIR / f"{args.input.stem}_{args.method}.mdp"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_mdp(out, layers, args.dpi)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")

    if args.check:
        _, back = read_mdp(out)
        for (name, orig), (name2, got) in zip(layers, back):
            assert name == name2 and np.array_equal(orig, got), f"layer {name} did not round-trip"
        print("check: all layers round-trip exactly")


if __name__ == "__main__":
    main()
