"""Check exact source provenance, hash pins and tile seams for horse PBR maps.

Run: python3 scripts/art/validate_nyaagyu_horse_pbr.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
HORSE = ROOT / "Content/SourceArt/Horses/Nyaagyu"
PBR = HORSE / "PBR"
base = json.loads((HORSE / "manifest.json").read_text())
record = json.loads((PBR / "manifest.json").read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert record["schema_version"] == 1
assert record["generator"] == "scripts/art/create_nyaagyu_horse_pbr.py"
assert record["base_horse_blend_sha256"] == base["blend_sha256"]
assert record["base_horse_fbx_sha256"] == base["fbx_sha256"]
assert record["sora_logo_sha256"] == base["insignia_sha256"]
assert sha(HORSE / base["source_blend"]) == base["blend_sha256"]
assert sha(HORSE / base["fbx"]) == base["fbx_sha256"]
assert set(record["material_slots"]) == {
    "M_Horse_SealBrownCoat", "M_Horse_DarkPoints",
    "M_Tack_DarkLeather", "M_Tack_BlackenedIron",
}
assert "not measured scans" in record["limitations"]
assert "no third-party stock textures" in record["source_license"]
assert len(record["sources"]) == 3 and len(record["maps"]) == 3
for source in record["sources"]:
    path = (PBR / source["file"]).resolve()
    assert path.is_relative_to((PBR / "Source").resolve())
    assert path.is_file() and sha(path) == source["sha256"]
    assert source["origin"].startswith("Built-in OpenAI image_gen.imagegen; text-only prompt")
    assert source["origin_output_id"].startswith("exec-")
    assert source["prompt"] and source["source_url"] is None
    assert source["rights_url"] == "https://openai.com/policies/row-terms-of-use/"

for material_set in record["maps"]:
    assert material_set["resolution"] == [2048, 2048]
    assert {entry["channel"] for entry in material_set["maps"]} == {"Albedo", "NormalDX", "ORM"}
    for entry in material_set["maps"]:
        path = (PBR / entry["file"]).resolve()
        assert path.parent == PBR.resolve()
        assert sha(path) == entry["sha256"]
        pixels = np.asarray(Image.open(path).convert("RGB"))
        assert pixels.shape == (2048, 2048, 3)
        assert np.array_equal(pixels[0], pixels[-1]), path
        assert np.array_equal(pixels[:, 0], pixels[:, -1]), path
        if entry["channel"] == "Albedo":
            assert float(pixels.std()) > 8
        elif entry["channel"] == "NormalDX":
            assert 215 < float(pixels[:, :, 2].mean()) <= 255
        else:
            assert float(pixels[:, :, 0].mean()) > 240
            expected_metal = round(material_set["metallic"] * 255)
            assert abs(float(pixels[:, :, 2].mean()) - expected_metal) < 1.5
    print("HORSE_PBR_MAPS_PASS", material_set["name"], material_set["resolution"])

print("NYAAGYU_HORSE_PBR_PROVENANCE_PASS", len(record["sources"]), len(record["material_slots"]))
