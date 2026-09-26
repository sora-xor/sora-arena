#!/usr/bin/env python3
"""Tone-map the EXR stills from render_vfx_previews.py and tile them into review sheets.

    python3 scripts/unreal/diagnostics/vfx_preview_sheet.py Saved/VFXPreview [--out DIR]

The EXRs hold linear scene colour (pre-exposed by the capture's fixed manual
exposure). Each light setting gets one fixed exposure, chosen so the stone
floor reads as a mid-grey in the day shots, then a small bloom of values above
display white and the ACES filmic fit. Every system gets one sheet with its
stills left to right by age, labelled with the file name.
"""
from __future__ import annotations

import argparse
import re
import struct
import zlib
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

# Scene-colour multipliers for the display, per light setting (see render_vfx_previews.py).
EXPOSURE = {"day": 0.3, "dusk": 1.5}


def read_exr(path: Path) -> np.ndarray:
    """Scanline EXR (NONE/ZIPS/ZIP, half or float channels) as an HxWx3 float array."""
    data = path.read_bytes()
    if data[:4] != b"\x76\x2f\x31\x01":
        raise ValueError(f"{path} is not an OpenEXR file")
    pos, header = 8, {}
    while data[pos] != 0:
        end = data.index(b"\0", pos)
        name = data[pos:end].decode()
        pos = data.index(b"\0", end + 1) + 1
        size = struct.unpack_from("<i", data, pos)[0]
        header[name] = data[pos + 4:pos + 4 + size]
        pos += 4 + size
    pos += 1
    chlist, channels, p = header["channels"], [], 0
    while chlist[p] != 0:
        end = chlist.index(b"\0", p)
        channels.append((chlist[p:end].decode(), struct.unpack_from("<i", chlist, end + 1)[0]))
        p = end + 17
    xmin, ymin, xmax, ymax = struct.unpack("<4i", header["dataWindow"])
    width, height = xmax - xmin + 1, ymax - ymin + 1
    compression = header["compression"][0]
    lines = {0: 1, 2: 1, 3: 16}[compression]
    offsets = struct.unpack_from(f"<{(height + lines - 1) // lines}Q", data, pos)
    planes = {name: np.zeros((height, width), np.float32) for name, _ in channels}
    for offset in offsets:
        y, size = struct.unpack_from("<ii", data, offset)
        raw = data[offset + 8:offset + 8 + size]
        rows = min(lines, ymax - y + 1)
        expected = sum(2 if kind == 1 else 4 for _, kind in channels) * width * rows
        if compression and size < expected:
            t = np.frombuffer(zlib.decompress(raw), np.uint8).astype(np.int64)
            t[1:] -= 128
            t = (np.cumsum(t) & 0xFF).astype(np.uint8)
            half = (len(t) + 1) // 2
            merged = np.empty(len(t), np.uint8)
            merged[0::2], merged[1::2] = t[:half], t[half:]
            raw = merged.tobytes()
        cursor = 0
        for row in range(rows):
            for name, kind in channels:
                dtype, step = (np.float16, 2) if kind == 1 else (np.float32, 4)
                planes[name][y - ymin + row] = np.frombuffer(raw, dtype, width, cursor)
                cursor += step * width
    return np.stack([planes["R"], planes["G"], planes["B"]], -1)


def aces(x):
    return np.clip((x * (2.51 * x + .03)) / (x * (2.43 * x + .59) + .14), 0, 1)


def display(scene: np.ndarray, exposure: float) -> np.ndarray:
    exposed = np.nan_to_num(scene) * exposure
    bright = np.clip(exposed - 1.0, 0, None)
    bloom = ndimage.gaussian_filter(bright, (4, 4, 0)) * .15 + ndimage.gaussian_filter(bright, (18, 18, 0)) * .1   # ~ the project's 0.2-0.28
    return (aces(exposed + bloom) ** (1 / 2.2) * 255 + .5).astype(np.uint8)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folder", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    out = args.out or args.folder / "sheets"
    out.mkdir(parents=True, exist_ok=True)
    groups = defaultdict(list)
    pattern = re.compile(r"(?P<name>.+)_(?P<light>day|dusk)_(?P<age>[0-9.]+)s\.exr$")
    for path in sorted(args.folder.glob("*.exr")):
        match = pattern.match(path.name)
        if match:
            groups[(match["name"], match["light"])].append((float(match["age"]), path))
    for (name, light), shots in sorted(groups.items()):
        tiles = []
        for age, path in sorted(shots):
            image = Image.fromarray(display(read_exr(path), EXPOSURE[light])).resize((640, 360), Image.Resampling.LANCZOS)
            ImageDraw.Draw(image).text((8, 6), f"{name} {light} {age:.2f}s", fill=(255, 255, 255))
            tiles.append(image)
        sheet = Image.new("RGB", (640 * min(3, len(tiles)), 360 * ((len(tiles) + 2) // 3)))
        for index, tile in enumerate(tiles):
            sheet.paste(tile, ((index % 3) * 640, (index // 3) * 360))
        target = out / f"{name}_{light}.png"
        sheet.save(target)
        print(target)


if __name__ == "__main__":
    main()
