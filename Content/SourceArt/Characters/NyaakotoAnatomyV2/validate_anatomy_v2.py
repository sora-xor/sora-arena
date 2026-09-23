"""Validate the isolated editable V2 source and its FBX round trip."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parent
manifest = json.loads((ROOT / "manifest.json").read_text())
assert manifest["production_status"].startswith("REVIEW_ONLY")
for relative, expected in manifest["files_sha256"].items():
    source = ROOT / relative
    assert source.is_file(), f"Missing candidate file: {relative}"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected, f"Changed candidate file: {relative}"

bpy.ops.wm.open_mainfile(filepath=str(ROOT / manifest["source_blend"]))
head = bpy.data.objects.get("SM_Nyaakoto_FacialAnatomy_V2_Study")
assert head and head.type == "MESH"
assert len(head.data.polygons) >= 70000
assert head.data.uv_layers and head.data.uv_layers[0].name == "UVMap"
assert "CoatMix" in head.data.color_attributes
assert all(bpy.data.objects.get(f"Ear_CuppedCartilage_{side}") for side in (-1, 1))
assert all("BowlMix" in bpy.data.objects[f"Ear_CuppedCartilage_{side}"].data.color_attributes for side in (-1, 1))
assert all(bpy.data.objects.get(f"Iris_UV0_{side}") for side in (-1, 1))
assert all(bpy.data.objects.get(f"Cornea_ClearConvex_{side}") for side in (-1, 1))
cards = bpy.data.objects.get("Fur_Cards_Head_Directional")
assert cards and len(cards.data.polygons) >= 3000
fur_card_count = len(cards.data.polygons)
assert all(ob.data.uv_layers for ob in bpy.data.objects if ob.type == "MESH")
assert not any(ob.type == "ARMATURE" for ob in bpy.data.objects), "Candidate is intentionally unrigged"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(ROOT / manifest["fbx"]))
meshes = [ob for ob in bpy.context.scene.objects if ob.type == "MESH"]
assert len(meshes) >= 100, len(meshes)
assert all(ob.data.uv_layers for ob in meshes), "FBX UV0 missing"
roundtrip = bpy.data.objects.get("SM_Nyaakoto_FacialAnatomy_V2_Study")
assert roundtrip and len(roundtrip.data.polygons) >= 70000
assert len(roundtrip.data.uv_layers[0].data) == len(roundtrip.data.loops)
coords = [vertex.co for vertex in roundtrip.data.vertices]
low = [min(p[i] for p in coords) for i in range(3)]
high = [max(p[i] for p in coords) for i in range(3)]
assert -0.2 < low[0] < -0.1 and 0.20 < high[0] < 0.25, (low, high)
assert -0.15 < low[1] < -0.10 and 0.10 < high[1] < 0.15, (low, high)
assert 1.40 < low[2] < 1.46 and 1.77 < high[2] < 1.81, (low, high)
print("NYAAKOTO_FACIAL_ANATOMY_V2_SOURCE_VALID", len(meshes), "FBX meshes", len(roundtrip.data.polygons), "head polygons", fur_card_count, "fur cards")
