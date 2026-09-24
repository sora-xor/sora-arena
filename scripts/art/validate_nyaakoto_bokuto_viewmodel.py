"""Independent source/FBX audit for the source-only Nyaakoto bokuto paws.

Run from repository root:
  blender -b --factory-startup --python scripts/art/validate_nyaakoto_bokuto_viewmodel.py
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Characters/NyaakotoBokutoViewmodel"
record = json.loads((OUT / "manifest.json").read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


assert record["schema_version"] == 1
assert record["name"] == "SK_Nyaakoto_BokutoPaws_SourceOnly"
assert record["status"].startswith("source-only")
assert record["digit_mesh_count"] == 8
assert record["digital_pad_count"] == 8
assert record["idle_review_transform"] == {
    "weapon_root_location_cm":[40,18,-18], "mesh_scale":.75,
    "camera_horizontal_fov_degrees":70}
for filename, item in record["outputs"].items():
    path = OUT / filename
    assert path.stat().st_size == item["bytes"]
    assert sha(path) == item["sha256"], filename
for relative, digest in record["source_manifests"].items():
    assert sha(ROOT / relative) == digest, relative
for relative, digest in record["source_texture_hashes"].items():
    assert sha(ROOT / relative) == digest, relative
assert sha(ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg") == record["sora_logo_svg_sha256"]
assert sha(ROOT / "Content/SourceArt/UI/SORA_Resistance_Logo.png") == record["sora_logo_png_sha256"]
assert sha(ROOT / record["review_prop"]) == record["review_prop_sha256"]


def audit_meshes(meshes, source):
    assert len(meshes) == record["mesh_count"], (source,len(meshes))
    assert len([o for o in meshes if o.name.endswith("_Phalanges")]) == 8
    assert len([o for o in meshes if "Digit_" in o.name and "ContactPad" in o.name]) == 8
    assert len([o for o in meshes if o.name.endswith("_OpposingThumb")]) == 2
    assert len([o for o in meshes if "MountedSORA_Kamon" in o.name]) == 1
    for obj in meshes:
        assert len(obj.data.materials) >= 1, (source,obj.name)
        assert len(obj.data.uv_layers) == 1 and obj.data.uv_layers[0].name == "UV0", (source,obj.name)
        coords = [loop.uv for loop in obj.data.uv_layers[0].data]
        assert coords and all(math.isfinite(v) for p in coords for v in p), (source,obj.name)
        assert max(p.x for p in coords)-min(p.x for p in coords) > .25, (source,obj.name)
        assert max(p.y for p in coords)-min(p.y for p in coords) > .25, (source,obj.name)
        assert all(math.isfinite(v) for vert in obj.data.vertices for v in vert.co), (source,obj.name)
        assert len(obj.vertex_groups) >= 1, (source,obj.name)
        for vertex in obj.data.vertices:
            assert vertex.groups and abs(sum(g.weight for g in vertex.groups)-1) < 1e-4, (source,obj.name,vertex.index)


bpy.ops.wm.open_mainfile(filepath=str(OUT / "Nyaakoto_BokutoPaws.blend"))
model = bpy.data.collections["Nyaakoto_BokutoPaws_Editable"]
meshes = [obj for obj in model.objects if obj.type == "MESH"]
rigs = [obj for obj in model.objects if obj.type == "ARMATURE"]
assert len(rigs) == 1 and rigs[0].name == "RIG_Nyaakoto_BokutoPaws"
rig = rigs[0]
assert sorted(b.name for b in rig.data.bones) == record["rig_bones"]
assert len(rig.data.bones) == 15
audit_meshes(meshes,"blend")
assert sum(len(poly.vertices)-2 for obj in meshes for poly in obj.data.polygons) == record["mesh_triangles"]
assert len([obj for obj in bpy.data.collections["ReviewOnly_RealBokuto"].objects if obj.type=="MESH"]) == 4
camera = bpy.data.objects["Camera_NormalIdlePose_FOV70"]
assert abs(math.degrees(camera.data.angle)-70) < .001
assert tuple(round(v,6) for v in camera.location) == (0,0,0)
for obj in meshes:
    modifiers = [m for m in obj.modifiers if m.type == "ARMATURE"]
    assert len(modifiers) == 1 and modifiers[0].object == rig, obj.name
    assert obj.get("runtime_status", "").startswith("source-only")
    assert obj.get("rig_bone") in rig.data.bones
for name in ("M_Paw_ShortWhiteFur_UV0","M_Kote_WornIndigoSilk_UV0",
             "M_Paw_OriginalPad_UV0","M_Kote_ExactSORAKamon_Enamel"):
    mat = bpy.data.materials[name]
    assert any(node.type == "UVMAP" and node.uv_map == "UV0"
               for node in mat.node_tree.nodes), name
    assert not any(node.type == "TEX_COORD" for node in mat.node_tree.nodes), name

# A pose control must actually deform its digit mesh, not just be an unused
# named bone. The source file is not saved after this test.
digit = bpy.data.objects["R_Digit_1_Phalanges"]
depsgraph = bpy.context.evaluated_depsgraph_get()
before = digit.evaluated_get(depsgraph).to_mesh().vertices[0].co.copy()
bone = rig.pose.bones["R_Digit_1"]
bone.rotation_mode = "XYZ"
bone.rotation_euler[0] = .35
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
after = digit.evaluated_get(depsgraph).to_mesh().vertices[0].co.copy()
assert (after-before).length > .0002, (before[:],after[:])

# Contact pads are sited on the real .242 m oval oak handle. Their surface
# centres are within a few millimetres of the source's 16.4 mm Y semiaxis.
for x,y,z in record["contact_pad_centres_m"]:
    assert -.242 < x < -.004
    assert .015 < abs(y) < .026
    assert abs(z) < .003

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(OUT / "SK_Nyaakoto_BokutoPaws_SourceOnly.fbx"))
roundtrip = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
assert len(armatures) == 1
assert set(record["rig_bones"]).issubset({b.name for b in armatures[0].data.bones})
audit_meshes(roundtrip,"fbx")
assert not any(obj.name.startswith("ReviewOnly_") for obj in roundtrip)
print("NYAAKOTO_BOKUTO_VIEWMODEL_ROUNDTRIP_VALID",
      len(roundtrip),len(armatures[0].data.bones),record["mesh_triangles"],flush=True)
