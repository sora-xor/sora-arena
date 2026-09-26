"""Build the runtime SORA mon mesh from the user-supplied SVG's two paths.

Run: blender -b --factory-startup --python scripts/art/create_sora_kamon_mon.py
Validate: blender -b --factory-startup --python scripts/art/validate_sora_kamon_mon.py

The mark is the byte-pinned Content/SourceArt/UI/sora_logo_NOtext2.svg,
imported through Blender's SVG importer and never redrawn or simplified: every
tessellated vertex of both filled paths is kept, scaled uniformly so the disc
is 1 m across, and extruded 1 cm. The mark stands in the Y-Z plane facing +X
with its legs down, centred on the origin; the cut-away strokes stay open, so
whatever stands behind the mon shows through them as the field. Practice
presentation (sashimono, barricades, the Control point, spawn pads, the
payload) places and colours this one mesh at runtime.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "Content/SourceArt/UI"
OUT = UI / "SoraKamonMon"
NAME = "SM_SoraKamon"
FBX = OUT / f"{NAME}.fbx"
MANIFEST = OUT / "manifest.json"
LOGO = UI / "sora_logo_NOtext2.svg"
LOGO_RECORD = json.loads((UI / "sora_logo_manifest.json").read_text())
DIAMETER_M = 1.0
THICKNESS_M = .01


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert sha(LOGO) == LOGO_RECORD["source_sha256"], "The user-supplied SORA SVG changed"
OUT.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1

before = set(bpy.data.objects)
bpy.ops.import_curve.svg(filepath=str(LOGO))
curves = [obj for obj in set(bpy.data.objects) - before if obj.type == "CURVE"]
assert len(curves) == 2, [obj.name for obj in curves]
corners = [obj.matrix_world @ Vector(corner) for obj in curves for corner in obj.bound_box]
min_x, max_x = min(p.x for p in corners), max(p.x for p in corners)
min_y, max_y = min(p.y for p in corners), max(p.y for p in corners)
origin_x, origin_y = (min_x + max_x) / 2, (min_y + max_y) / 2
size = max(max_x - min_x, max_y - min_y)
assert size > 0

paths = []
for index, obj in enumerate(sorted(curves, key=lambda o: o.name)):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    assert obj.data.polygons, "An SVG path converted without its fill"
    # Image right is +Y and image up is +Z; the mark faces +X.
    for vertex in obj.data.vertices:
        p = obj.matrix_world @ vertex.co
        vertex.co = (0.0, (p.x - origin_x) / size * DIAMETER_M, (p.y - origin_y) / size * DIAMETER_M)
    obj.matrix_world.identity()
    obj.name = f"SORA_Mon_Path_{index}"
    obj["source_svg_sha256"] = LOGO_RECORD["source_sha256"]
    paths.append(obj)

bpy.ops.object.select_all(action="DESELECT")
for obj in paths:
    obj.select_set(True)
bpy.context.view_layer.objects.active = paths[0]
bpy.ops.object.join()
mon = bpy.context.object
mon.name = NAME
mesh = mon.data
mesh.name = NAME

# Both faces carry every SVG vertex: the flat fill is copied to x = +-T/2 and
# the outline is bridged into the rim, so no vertex moves within the plane.
bm = bmesh.new()
bm.from_mesh(mesh)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
for face in bm.faces:
    if face.normal.x < 0:
        face.normal_flip()
extruded = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:], use_keep_orig=True)
moved = [item for item in extruded["geom"] if isinstance(item, bmesh.types.BMVert)]
bmesh.ops.translate(bm, verts=moved, vec=(-THICKNESS_M, 0, 0))
bmesh.ops.translate(bm, verts=bm.verts, vec=(THICKNESS_M / 2, 0, 0))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bmesh.ops.triangulate(bm, faces=bm.faces[:])
bm.to_mesh(mesh)
bm.free()
mesh.update()

# A planar UV over the disc for the texture-free lacquer and dye materials.
uv = mesh.uv_layers.new(name="Mon_UV")
for loop in mesh.loops:
    co = mesh.vertices[loop.vertex_index].co
    uv.data[loop.index].uv = (co.y / DIAMETER_M + .5, co.z / DIAMETER_M + .5)
# One slot; the importer's own SVG material is dropped.
mesh.materials.clear()
material = bpy.data.materials.new("M_SoraKamon")
material.diffuse_color = (0.768, 0.018, 0.026, 1.0)
mesh.materials.append(material)
for polygon in mesh.polygons:
    polygon.material_index = 0
    polygon.use_smooth = False

xs = [v.co.x for v in mesh.vertices]
ys = [v.co.y for v in mesh.vertices]
zs = [v.co.z for v in mesh.vertices]
assert abs(max(xs) - THICKNESS_M / 2) < 1e-6 and abs(min(xs) + THICKNESS_M / 2) < 1e-6
assert abs((max(ys) - min(ys)) - DIAMETER_M) < 1e-3 and abs((max(zs) - min(zs)) - DIAMETER_M) < 1e-3

bpy.ops.object.select_all(action="DESELECT")
mon.select_set(True)
bpy.context.view_layer.objects.active = mon
bpy.ops.export_scene.fbx(filepath=str(FBX), use_selection=True, object_types={"MESH"}, add_leaf_bones=False,
                         apply_unit_scale=True, axis_forward="-Y", axis_up="Z", mesh_smooth_type="FACE",
                         use_mesh_modifiers=False, path_mode="STRIP")

record = {
    "schema_version": 1,
    "name": NAME,
    "generator": "scripts/art/create_sora_kamon_mon.py",
    "validator": "scripts/art/validate_sora_kamon_mon.py",
    "source_svg": "../sora_logo_NOtext2.svg",
    "source_svg_sha256": LOGO_RECORD["source_sha256"],
    "fbx": FBX.name,
    "fbx_sha256": sha(FBX),
    "unreal_asset": f"/Game/Generated/UI/{NAME}.{NAME}",
    "diameter_m": DIAMETER_M,
    "thickness_m": THICKNESS_M,
    "orientation": "mark in the Y-Z plane facing +X, legs toward -Z, centred on the origin",
    "vertices": len(mesh.vertices),
    "triangles": len(mesh.polygons),
    "material_slots": ["M_SoraKamon"],
    "collision": "Visual only; practice presentation never collides",
    "license": "User-supplied SORA mark for SORA Arena, geometry taken unchanged from the pinned SVG's two paths; no third-party license is asserted",
}
MANIFEST.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
print("SORA_KAMON_MON_EXPORTED", record["fbx_sha256"], record["vertices"], record["triangles"])
