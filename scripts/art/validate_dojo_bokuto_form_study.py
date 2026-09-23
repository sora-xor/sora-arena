"""Round-trip and provenance checks for the source-only bokuto form study.

Run: blender -b --factory-startup --python scripts/art/validate_dojo_bokuto_form_study.py
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Weapons/DojoBokutoForm"
record = json.loads((OUT / "manifest.json").read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert record["schema_version"] == 1
assert record["name"] == "SM_Nyaagyu_BokutoForm"
assert record["dimensions_cm"] == {"total": 101.5, "grip": 24.2, "sori": 1.5}
assert record["scope"].startswith("Source-only")
for file_field, hash_field in (
        ("source_blend", "blend_sha256"), ("fbx", "fbx_sha256"),
        ("preview", "preview_sha256"),
        ("detail_preview", "detail_preview_sha256")):
    assert sha(OUT / record[file_field]) == record[hash_field], file_field
assert sha(ROOT / "Content/SourceArt/Weapons/DojoBokkenPBR/texture_manifest.json") == record["source_texture_manifest_sha256"]
assert sha(ROOT / "Content/SourceArt/Weapons/NyaagyuYumi/manifest.json") == record["leather_source_manifest_sha256"]


def check_meshes(parts):
    assert len(parts) == 4, [obj.name for obj in parts]
    assert sum(len(poly.vertices)-2 for obj in parts for poly in obj.data.polygons) == record["triangles"]
    assert sorted(obj.data.materials[0].name for obj in parts) == sorted(record["materials"])
    xs = [float((obj.matrix_world @ vertex.co).x) for obj in parts for vertex in obj.data.vertices]
    assert abs(min(xs) - record["bounds_m"]["min_x"]) < .0001
    assert abs(max(xs) - record["bounds_m"]["max_x"]) < .0001
    assert abs((max(xs)-min(xs)) - 1.015) < .0001
    for obj in parts:
        assert len(obj.data.uv_layers) == 1 and obj.data.uv_layers[0].name == "UV0", obj.name
        uv = [loop.uv for loop in obj.data.uv_layers[0].data]
        assert all(math.isfinite(v) for point in uv for v in point)
        assert max(p.x for p in uv)-min(p.x for p in uv) > .25, obj.name
        assert max(p.y for p in uv)-min(p.y for p in uv) > .25, obj.name
        assert not any(math.isnan(float(c)) for v in obj.data.vertices for c in v.co)
        if obj.name.startswith("Tsuba_"):
            # Planar faces and both ring walls must have nonzero UV area.
            for poly in obj.data.polygons:
                points = [uv[index] for index in poly.loop_indices]
                area = abs(sum(a.x*b.y-b.x*a.y for a, b in
                               zip(points, points[1:]+points[:1])))*.5
                assert area > 1e-6, (obj.name, poly.index, area)
    grip = next(obj for obj in parts if obj.name.startswith("Tsuka_"))
    blade = next(obj for obj in parts if obj.name.startswith("Tachi_"))
    guard = next(obj for obj in parts if obj.name.startswith("Tsuba_"))
    retainer = next(obj for obj in parts if obj.name.startswith("Tsubadome_"))
    gx = [float((grip.matrix_world @ v.co).x) for v in grip.data.vertices]
    bx = [float((blade.matrix_world @ v.co).x) for v in blade.data.vertices]
    assert abs((max(gx)-min(gx))-.242) < .0001
    assert abs(min(bx)) < .0001 and abs(max(bx)-.773) < .0001
    assert 0.01 < max(float((guard.matrix_world @ v.co).y) for v in guard.data.vertices) < .05
    assert abs(min(float((retainer.matrix_world @ v.co).x) for v in retainer.data.vertices)+.009) < .0001
    assert abs(max(float((retainer.matrix_world @ v.co).x) for v in retainer.data.vertices)+.0025) < .0001
    # The midspan deviation of the blade's centreline from its end chord is
    # the modeled sori. Its deliberately blunt final profile remains >4 mm wide.
    sections = sorted(set(round(float((blade.matrix_world @ v.co).x), 5)
                          for v in blade.data.vertices))
    assert len(sections) == 160
    middle = sections[len(sections)//2]
    middle_z = [float((blade.matrix_world @ v.co).z) for v in blade.data.vertices
                if abs(float((blade.matrix_world @ v.co).x)-middle) < .00001]
    assert .012 < (max(middle_z)+min(middle_z))*.5 < .018
    tip_y = [float((blade.matrix_world @ v.co).y) for v in blade.data.vertices
             if abs(float((blade.matrix_world @ v.co).x)-.773) < .00001]
    assert max(tip_y)-min(tip_y) > .005
    for obj in (grip, blade):
        bad = 0
        for poly in obj.data.polygons[:-2]:
            center = obj.matrix_world @ poly.center
            radius = Vector((0,center.y,center.z))
            if obj is blade:
                u = max(0,min(1,center.x/.773))
                radius.z -= .015*4*u*(1-u)
            if radius.length > .002 and (obj.matrix_world.to_3x3() @ poly.normal).dot(radius) <= 0:
                bad += 1
        assert bad == 0, (obj.name, bad)


bpy.ops.wm.open_mainfile(filepath=str(OUT / record["source_blend"]))
parts = [obj for obj in bpy.data.collections["BokutoForm_Editable"].objects if obj.type == "MESH"]
check_meshes(parts)
assert sum(bool(image.packed_file) for image in bpy.data.images
           if image.source == "FILE") >= 6

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(OUT / record["fbx"]))
roundtrip = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
check_meshes(roundtrip)
print("BOKUTO_FORM_ROUNDTRIP_VALID", record["triangles"], record["fbx_sha256"])
