"""Verify the source, channel semantics, and recoverability of the torii PBR maps."""

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/ToriiLacquer"
record = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
assert record["schema_version"] == 1
assert record["generator"] == "scripts/art/create_torii_lacquer_pbr.py"
assert record["material_slot"] == "M_Env_VermilionLacquer"
assert record["tile_size_cm"] == 120.0
assert record["license"] == "Original project-owned procedural texture; no third-party input image"
assert set(record["maps"]) == {"Albedo", "NormalDX", "ORM"}
maps = {}
for channel, entry in record["maps"].items():
    file = OUT / entry["file"]
    assert file.name == f"T_Nyaagyu_ToriiLacquer_{channel}.png"
    assert hashlib.sha256(file.read_bytes()).hexdigest() == entry["sha256"]
    with Image.open(file) as image:
        assert image.mode == "RGB" and image.size == (2048, 2048)
        maps[channel] = np.asarray(image, dtype=np.uint8)
assert float(maps["Albedo"][:, :, 0].std()) > 10
assert float(maps["Albedo"][:, :, 0].mean()) > float(maps["Albedo"][:, :, 1].mean()) * 3
assert 100 < float(maps["NormalDX"][:, :, 2].mean()) <= 255
assert np.any(maps["NormalDX"][:, :, 0] != 128)
assert np.max(maps["ORM"][:, :, 2]) == 0  # dielectric lacquer, not metallic paint
assert 40 < float(maps["ORM"][:, :, 1].mean()) < 180
assert float(maps["ORM"][:, :, 1].std()) > 5
assert (OUT / record["review"]).stat().st_size > 100_000
print("TORII_LACQUER_PBR_VALIDATED: 2K source, hashes, dielectric ORM, nonflat normals")
