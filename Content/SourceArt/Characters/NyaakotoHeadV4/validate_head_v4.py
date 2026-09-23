"""Independent source/output validation. Run with `blender -b --factory-startup --python ...`."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent
manifest = json.loads((ROOT / "manifest.json").read_text())
base = ROOT.parent / "NyaakotoCoatV3" / "Nyaakoto_HeadCoat_V3_Study.blend"
assert hashlib.sha256(base.read_bytes()).hexdigest() == manifest["base_v3_blend_sha256"]
for name, digest in manifest["files_sha256"].items():
    p = ROOT / name
    assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == digest, name

bpy.ops.wm.open_mainfile(filepath=str(ROOT / "Nyaakoto_HeadAnatomy_V4_Study.blend"))
head = bpy.data.objects["SM_Nyaakoto_HeadAnatomy_V4_Study"]
assert len(head.data.vertices) >= 80000
assert len(head.data.polygons) >= 70000
assert head.data.uv_layers.active is not None
assert head.data.color_attributes.get("CoatMix") is not None

# One connected facial shell rather than discrete sphere primitives. This is
# a topology check, not a judgement that its sculpted form is convincing.
parent = list(range(len(head.data.vertices)))
def find(v):
    while parent[v] != v:
        parent[v] = parent[parent[v]]
        v = parent[v]
    return v
for edge in head.data.edges:
    a, b = map(find, edge.vertices)
    if a != b:
        parent[b] = a
components = len({find(i) for i in range(len(parent))})
assert components == 1, f"facial shell has {components} separate components"

ears = [o for o in bpy.data.objects if o.name.startswith("Ear_CuppedThick_V4_")]
assert len(ears) == 2
for ear in ears:
    xx = [v.co.x for v in ear.data.vertices]
    assert max(xx)-min(xx) > .025, "ear does not have adequate front/back relief"
    assert ear.data.uv_layers.active is not None
    assert len(ear.data.polygons) > 1000
    assert len(ear.data.color_attributes["EarSkinMix"].data) == len(ear.data.loops)

assert bpy.data.objects.get("Groom_Nyaakoto_ShortGuard_V4")
assert len(bpy.data.objects["Groom_Nyaakoto_ShortGuard_V4"].data.splines) >= 15000
assert len(bpy.data.objects["Vibrissae_CurvedKeratin_V4"].data.splines) == 10
assert len([o for o in bpy.data.objects if o.name.startswith("FollicleV4_")]) == 10
assert not [o for o in bpy.data.objects if o.name.startswith(("Groom_Nyaakoto_ShortDirectional_V3", "Ear_CuppedOrganic_", "Vibrissae_FineKeratin_V3"))]

maps = ("Albedo", "NormalGL", "NormalDX", "ORM")
for kind in maps:
    image = bpy.data.images.load(str(ROOT / f"T_Nyaakoto_HeadV4_{kind}.png"), check_existing=False)
    assert tuple(image.size) == (2048, 2048)
    image.unpack(method="REMOVE") if image.packed_file else None
for name in ("Front", "Profile", "ThreeQuarter"):
    image = bpy.data.images.load(str(ROOT / f"Nyaakoto_HeadV4_{name}.png"), check_existing=False)
    assert tuple(image.size) == (1152, 1152)

# A separate FBX import checks that UV0 geometry was actually exported.
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(ROOT / "SM_Nyaakoto_HeadAnatomy_V4_Study.fbx"))
loaded = list(set(bpy.data.objects)-before)
fbx_head = next(o for o in loaded if o.type == "MESH" and o.name.startswith("SM_Nyaakoto_HeadAnatomy_V4_Study"))
assert len(fbx_head.data.vertices) >= 80000
assert fbx_head.data.uv_layers.active is not None
assert all(math.isfinite(v.co.x) and math.isfinite(v.co.y) and math.isfinite(v.co.z) for v in fbx_head.data.vertices)
print("NYAAKOTO_HEAD_V4_VALID",len(head.data.vertices),"connected vertices,",len(ears),"thick ears,",len(loaded),"FBX objects")
