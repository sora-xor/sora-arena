"""Count pink Surface Cache pixels in fixed Estate roof/eave image regions.

This reads two unedited 1280x720 PNGs and prints measurements only. A lower
count is evidence about card coverage, not a lighting or photorealism score.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
ARCHIVED = ROOT / "docs/render-qualification/estate-ue583-m1-20260924/Estate_Entrance_LumenSurfaceCache.png"
ARCHIVED_SHA256 = "b68b619ac483596c9cb3d37b68d59b563eb43e6af0f1db6ce86bd438bbc20733"
REGIONS = {
    "left_roof_eave": (135, 250, 280, 320),
    "right_roof_eave": (1000, 250, 1145, 320),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pink(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return r >= 210 and b >= 210 and g <= 100 and min(r, b) - g >= 120


def measure(path: Path) -> dict:
    with Image.open(path) as source:
        if source.size != (1280, 720) or source.mode not in ("RGB", "RGBA"):
            raise ValueError(f"Expected an original 1280x720 RGB(A) PNG: {path}")
        frame = source.convert("RGB")
        found = {}
        covered_pixels = set()
        for name, (x0, y0, x1, y1) in REGIONS.items():
            pixels = frame.crop((x0, y0, x1, y1))
            found[name] = sum(pink(pixel) for pixel in pixels.getdata())
            covered_pixels.update((x, y) for y in range(y0, y1) for x in range(x0, x1))
        other = sum(pink(frame.getpixel((x, y))) for y in range(720)
                    for x in range(1280) if (x, y) not in covered_pixels)
    return {"sha256": sha256(path), "regions": found, "other_pink_pixels": other}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path, nargs="?")
    parser.add_argument("candidate", type=Path, nargs="?")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        result = measure(ARCHIVED)
        assert result["sha256"] == ARCHIVED_SHA256
        assert result["regions"] == {"left_roof_eave": 475, "right_roof_eave": 512}
        print("SORA_LUMEN_ROOF_ROI_SELF_CHECK_OK", json.dumps(result, sort_keys=True))
        return
    if args.baseline is None or args.candidate is None:
        parser.error("provide same-package baseline and candidate PNGs")
    before = measure(args.baseline)
    after = measure(args.candidate)
    print(json.dumps({
        "method": "RGB r,b >= 210; g <= 100; min(r,b)-g >= 120",
        "regions_xyxy": REGIONS,
        "baseline": before,
        "candidate": after,
        "delta_candidate_minus_baseline": {
            name: after["regions"][name] - before["regions"][name]
            for name in REGIONS
        },
        "other_pink_delta": after["other_pink_pixels"] - before["other_pink_pixels"],
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
