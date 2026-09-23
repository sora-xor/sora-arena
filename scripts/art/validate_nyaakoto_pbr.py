"""Check every runtime Nyaakoto PBR map and its exact material-slot contract."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Content/SourceArt/Characters/Hero/PBR"
record = json.loads((SOURCE / "manifest.json").read_text())
assert record["schema_version"] == 1
assert record["generator"] == "scripts/art/create_nyaakoto_pbr_textures.py"
assert record["source_license"].startswith("Project-owned")
assert {group["name"] for group in record["maps"]} == {
    "fur_grey", "fur_white", "fur_charcoal", "silk_indigo", "lacquer_oxblood", "neutral"}
assert len(record["material_slots"]) == 23
assert {item["surface"] for item in record["fur_sources"]} == {
    "fur_grey", "fur_white", "fur_charcoal"}
for source in record["fur_sources"]:
    path = SOURCE / source["file"]
    assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
    assert source["origin"].startswith("Built-in OpenAI image_gen.imagegen")
    assert source["origin_output_id"].startswith("exec-")
    assert source["source_url"] is None and len(source["prompt"]) > 400
    assert source["rights_url"] == "https://openai.com/policies/row-terms-of-use/"

for group in record["maps"]:
    assert {item["channel"] for item in group["maps"]} == {"Albedo", "NormalDX", "ORM"}
    maps = {}
    for item in group["maps"]:
        path = SOURCE / item["file"]
        assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        with Image.open(path) as image:
            assert image.mode == "RGB" and list(image.size) == group["resolution"]
            pixels = np.asarray(image)
        assert np.array_equal(pixels[0], pixels[-1])
        assert np.array_equal(pixels[:, 0], pixels[:, -1])
        maps[item["channel"]] = pixels
    normal = maps["NormalDX"]
    assert np.max(normal[:, :, 2]) > 245
    assert np.max(maps["ORM"][:, :, 0]) == 255
    if group["name"] != "neutral":
        assert np.std(maps["Albedo"][:, :, 0]) > 1.0
        assert np.std(normal[:, :, 0]) > 1.0
        assert 25 < np.mean(maps["ORM"][:, :, 1]) < 250

for slot_name, surface in record["material_slots"].items():
    assert slot_name.startswith("M_Hero_")
    assert surface["surface"] in {group["name"] for group in record["maps"]}
    assert len(surface["tint"]) == 3 and all(0 <= x <= 1 for x in surface["tint"])
    assert 0 < surface["roughness_scale"] <= 2
    assert 0 <= surface["metallic_scale"] <= 1

if "--maps-only" not in sys.argv:
    # Keep the full source/runtime check separate from the map-only gate so
    # material work can be validated while another artist regenerates FBXs.
    skin = json.loads((SOURCE.parent / "runtime_skin_manifest.json").read_text())
    hero = json.loads((SOURCE.parent / "manifest.json").read_text())
    assert skin["source_parts"] == hero["source_parts"] and len(skin["skeleton_bones"]) == 20
assert "M_Hero_GreyTabbyFur" in record["material_slots"]
assert "M_Hero_SORAResistanceRed" in record["material_slots"]
print("NYAAKOTO_PBR_VALID: 6 texture sets, 23 runtime materials, exact tile seams",
      "maps only" if "--maps-only" in sys.argv else "full")
