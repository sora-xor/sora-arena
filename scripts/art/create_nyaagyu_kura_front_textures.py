"""Build a reproducible PBR door atlas from the project's pinned CC0 wood scan.

The atlas preserves the source photograph's grain, normal and ARM detail. The
per-board crops, modest patina and UV layout are original SORA Arena work.
Run before create_nyaagyu_kura_front.py with Python 3, Pillow and NumPy.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuKuraFront"
SCAN = ROOT / "Content/SourceArt/Environment/PolyHaven/wood_planks_dirt"
PALETTE = ROOT / "Content/SourceArt/Environment/PolyHaven/manifest.json"
SIZE = 2048
BOARD_COUNT = 14


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    record = json.loads(PALETTE.read_text())
    asset = next(x for x in record["assets"] if x["asset_id"] == "wood_planks_dirt")
    assert asset["license"] == "CC0-1.0"
    files = {x["channel"].lower(): x for x in asset["files"]}
    inputs = {}
    for role, key in (("Albedo", "diffuse"), ("NormalDX", "nor_dx"), ("ARM", "arm")):
        item = files[key]
        path = SCAN / Path(item["file"]).name
        assert sha256(path) == item["sha256"], path
        inputs[role] = (path, np.asarray(Image.open(path).convert("RGB")))
    rng = np.random.default_rng(0x4E594147)
    atlases = {key: np.zeros((SIZE, SIZE, 3), dtype=np.uint8) for key in inputs}
    crops = []
    for i in range(BOARD_COUNT):
        left = round(i * SIZE / BOARD_COUNT)
        right = round((i + 1) * SIZE / BOARD_COUNT)
        source_x = 95 + (i * 271) % 3570
        source_y = 40 + (i * 37) % 360
        # Tall strips follow the photographed grain. Each source region is
        # unique and the exact same crop is applied to color, normal and ARM.
        rect = (source_x, source_y, source_x + 340, source_y + 3500)
        crops.append(rect)
        for role, (_, source) in inputs.items():
            sample = Image.fromarray(source).crop(rect)
            strip = np.asarray(sample.resize((right - left, SIZE), Image.Resampling.LANCZOS),
                               dtype=np.float32).copy()
            if role == "Albedo":
                tone = [1.02, .88, 1.10, .94, .79, 1.04, .91,
                        1.08, .86, 1.00, .83, 1.12, .95, .89][i]
                # Hand-applied low-frequency rain stain. Its amplitude stays
                # below the underlying photographed grain contrast.
                low = rng.uniform(.15, .85, (16, 3)).astype(np.float32)
                field = np.asarray(Image.fromarray(np.uint8(low * 255)).resize(
                    (right-left, SIZE), Image.Resampling.BICUBIC), dtype=np.float32) / 255
                field = np.clip(field, 0, 1)
                foot = np.clip((np.arange(SIZE, dtype=np.float32) / SIZE - .67) / .33, 0, 1)
                stain = (1 - .12 * field * foot[:, None])[:, :, None]
                strip = np.clip(strip * tone * stain, 0, 255)
            elif role == "ARM":
                # The lower wood is rain-damp; preserve scan AO/metalness.
                foot = np.clip((np.arange(SIZE, dtype=np.float32) / SIZE - .76) / .24, 0, 1)
                strip[:, :, 1] = np.clip(strip[:, :, 1] - foot[:, None] * 11, 0, 255)
            atlases[role][:, left:right] = strip.astype(np.uint8)
    OUT.mkdir(parents=True, exist_ok=True)
    names = {
        "Albedo": "T_KuraFront_AgedCedar_Albedo_2k.jpg",
        "NormalDX": "T_KuraFront_AgedCedar_NormalDX_2k.png",
        "ARM": "T_KuraFront_AgedCedar_ARM_2k.png",
    }
    for role, name in names.items():
        target = OUT / name
        image = Image.fromarray(atlases[role], "RGB")
        image.save(target, quality=94, subsampling=0) if target.suffix == ".jpg" else image.save(target)
    manifest = {
        "schema_version": 1,
        "generator": "scripts/art/create_nyaagyu_kura_front_textures.py",
        "license": "Derived from Rob Tuytel's Wood Planks Dirt scan, Poly Haven CC0-1.0; SORA Arena crop, UV atlas and subtle patina work is original project-owned work.",
        "source_url": asset["asset_url"],
        "license_url": asset["license_url"],
        "source_dimensions_mm": asset["source_dimensions_mm"],
        "source_files": {role: {"file": str(path.relative_to(ROOT)), "sha256": sha256(path)}
                         for role, (path, _) in inputs.items()},
        "atlas_files": {role: {"file": name, "sha256": sha256(OUT / name)}
                        for role, name in names.items()},
        "size_px": SIZE,
        "board_count": BOARD_COUNT,
        "source_crop_rects_px": crops,
        "normal_convention": "DirectX green-down; invert green in Blender, import without flip into Unreal",
        "packing": "ARM red AO, green roughness, blue metallic",
    }
    (OUT / "texture_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("NYAAGYU_KURA_FRONT_TEXTURES_READY", {k: sha256(OUT / v) for k,v in names.items()})


if __name__ == "__main__":
    main()
