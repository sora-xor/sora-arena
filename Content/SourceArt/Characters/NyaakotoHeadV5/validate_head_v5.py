"""Output and provenance checks for the V5 source study.

Run: blender -b --factory-startup --python Content/SourceArt/Characters/NyaakotoHeadV5/validate_head_v5.py
This cannot certify visual photorealism, topology deformation, or game readiness.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy

ROOT=Path(__file__).resolve().parent
manifest=json.loads((ROOT/"manifest.json").read_text())
base=ROOT.parent/"NyaakotoHeadV4"/"Nyaakoto_HeadAnatomy_V4_Study.blend"
assert hashlib.sha256(base.read_bytes()).hexdigest()==manifest["base_v4_blend_sha256"]
for name,digest in manifest["files_sha256"].items():
    p=ROOT/name
    assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==digest,name
assert not any(".glb"==p.suffix.lower() for p in ROOT.iterdir()),"third-party raw scan in public source"

bpy.ops.wm.open_mainfile(filepath=str(ROOT/"Nyaakoto_AdultCatHead_V5_Study.blend"))
head=bpy.data.objects["SM_Nyaakoto_AdultCatHead_V5_Study"]
assert len(head.data.vertices)==82566
assert head.data.uv_layers.active is not None
assert head.data.color_attributes.get("CoatMix") is not None

# Check that sculpting retained the connected shell, not merely overlapping
# independent spheres. Other facial/eye details remain separate editable parts.
parents=list(range(len(head.data.vertices)))
def find(i):
    while parents[i]!=i:
        parents[i]=parents[parents[i]];i=parents[i]
    return i
for e in head.data.edges:
    a,b=map(find,e.vertices)
    if a!=b:parents[b]=a
assert len({find(i) for i in range(len(parents))})==1

points=[v.co for v in head.data.vertices]
bridge=[v.x for v in points if 1.65<v.z<1.69 and abs(v.y)<.025]
cheek=[abs(v.y) for v in points if .04<v.x<.15 and 1.5882<v.z<1.65 and abs(v.y)>.07]
assert bridge and max(bridge)<.19,"central bridge still protrudes like V4"
assert cheek and max(cheek)<.10,"lateral cheek did not shrink"

ears=[o for o in bpy.data.objects if o.name.startswith("Ear_AnatomyV5_")]
assert len(ears)==2 and not [o for o in bpy.data.objects if o.name.startswith("Ear_CuppedThick_V4_")]
for ear in ears:
    assert ear.data.uv_layers.active is not None
    assert len(ear.data.polygons)>1800
    xx=[v.co.x for v in ear.data.vertices]
    assert max(xx)-min(xx)>.025
    assert len(ear.data.color_attributes["EarSkinMix"].data)==len(ear.data.loops)

mat=head.data.materials[0]
for name in ("UniqueUV_Albedo","UniqueUV_NormalGL","UniqueUV_ORM"):
    assert mat.node_tree.nodes[name].image.packed_file is not None,name
assert len(bpy.data.objects["Groom_Nyaakoto_ShortGuard_V4"].data.splines)>18000
for label in ("Front","Profile","ThreeQuarter"):
    im=bpy.data.images.load(str(ROOT/f"Nyaakoto_HeadV5_{label}.png"),check_existing=False)
    assert tuple(im.size)==(1152,1152)

before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(ROOT/"SM_Nyaakoto_AdultCatHead_V5_Study.fbx"))
new=set(bpy.data.objects)-before
fbx_head=next(o for o in new if o.type=="MESH" and o.name.startswith("SM_Nyaakoto_AdultCatHead_V5_Study"))
assert len(fbx_head.data.vertices)>=82566 and fbx_head.data.uv_layers.active is not None
assert all(math.isfinite(v.co.x) and math.isfinite(v.co.y) and math.isfinite(v.co.z) for v in fbx_head.data.vertices)
print("NYAAKOTO_V5_VALID",len(points),"connected head vertices,",len(ears),"UV ears,",len(new),"FBX objects")
