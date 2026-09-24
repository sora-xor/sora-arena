"""Source-only fixed-camera roof fit review for the molded SORA eave cap.

Inputs are the exact pinned Blender assets and FBX revisions. The original
roof/cap assets are never saved. Set SORA_CAP_FIT_ANALYSIS_ONLY=1 to solve the
joint in memory without saving or rendering. Blender 5.2.2 LTS.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[2]
ROOF = ROOT / "Content/SourceArt/Environment/NyaagyuKawaraBay"
CAP = ROOT / "Content/SourceArt/Environment/NyaagyuSoraEaveCapStudy"
OUT = CAP / "RoofBayArtReview"
OUT.mkdir(parents=True, exist_ok=True)
roof_manifest = json.loads((ROOF / "manifest.json").read_text())
cap_manifest = json.loads((CAP / "manifest.json").read_text())
roof_blend = ROOF / "Nyaagyu_KawaraBay.blend"
cap_blend = CAP / "Nyaagyu_SORA_EaveCap.blend"
for base, manifest, names in (
    (ROOF, roof_manifest, ("Nyaagyu_KawaraBay.blend", "SM_Nyaagyu_KawaraBay.fbx")),
    (CAP, cap_manifest, ("Nyaagyu_SORA_EaveCap.blend", "SM_Nyaagyu_SORA_EaveCap.fbx")),
):
    for name in names:
        assert hashlib.sha256((base/name).read_bytes()).hexdigest() == manifest["outputs"][name], name

bpy.ops.wm.open_mainfile(filepath=str(roof_blend))
assert bpy.app.version_string == "5.2.2 LTS"
scene = bpy.context.scene
assert scene.camera.name == "RoofBay_ReviewCamera"
assert scene.render.engine == "CYCLES"
camera_before = tuple(tuple(row) for row in scene.camera.matrix_world)
camera_scale_before = scene.camera.data.ortho_scale
lights_before = {
    name: {"matrix": tuple(tuple(row) for row in bpy.data.objects[name].matrix_world),
           "energy": bpy.data.objects[name].data.energy,
           "size": bpy.data.objects[name].data.size,
           "color": tuple(bpy.data.objects[name].data.color)}
    for name in ("SkyKey", "SoftFill")
}
roof_collection = bpy.data.collections["KawaraBay_Editable"]
roof_names = {obj.name for obj in roof_collection.objects if obj.type == "MESH"}
assert len(roof_names) == 64
old_badge = ("SORA_Kamon_EaveCap", "Kamon_Brass_Ring", "SORA_Kamon_UserSuppliedLogo")
assert all(name in roof_names for name in old_badge)
cover = bpy.data.objects["MaruGawara_Cover_R0_C1"]

with bpy.data.libraries.load(str(cap_blend), link=False) as (source, destination):
    assert "SORA_EaveCap_Editable" in source.collections
    destination.collections = ["SORA_EaveCap_Editable"]
cap_collection = destination.collections[0]
scene.collection.children.link(cap_collection)
# A freshly library-appended object's matrix_world remains identity until the
# view layer evaluates, even when its saved matrix_basis is non-identity. The
# crest paths rely on that SVG placement; capture the evaluated source matrix.
bpy.context.view_layer.update()
cap_objects = {obj.name: obj for obj in cap_collection.objects}
assert len(cap_objects) == 6 and all(obj.type == "MESH" for obj in cap_objects.values())
source_matrices = {name: obj.matrix_world.copy() for name,obj in cap_objects.items()}
shank = cap_objects["VaultedCover_SolidClay"]
shank_world = [source_matrices[shank.name] @ v.co for v in shank.data.vertices]
front = shank_world[:33]
front_width = max(v.x for v in front)-min(v.x for v in front)
nominal_width = .087
scale = nominal_width/front_width
assert .87 < scale < .90, scale
source_anchor = shank_world[16]
roof_top = [cover.matrix_world @ v.co for v in cover.data.vertices[:117]]
roof_grid = [roof_top[row*13:(row+1)*13] for row in range(9)]
target_x = roof_grid[0][6].x
target_y = -.030  # cap/socket begins 26 mm ahead of the existing cover lip
top_source = shank_world[:33*14]


def roof_height(x: float, y: float):
    """Bilinear evaluation of the first cover's top-surface source grid."""
    if y < roof_grid[0][0].y or y > roof_grid[-1][0].y:
        return None
    for row in range(8):
        y0, y1 = roof_grid[row][0].y, roof_grid[row+1][0].y
        if y0 <= y <= y1:
            def across(points):
                if x < points[0].x or x > points[-1].x:
                    return None
                for col in range(12):
                    a,b=points[col],points[col+1]
                    if a.x <= x <= b.x:
                        t=(x-a.x)/(b.x-a.x)
                        return a.z*(1-t)+b.z*t
                return None
            a,b=across(roof_grid[row]),across(roof_grid[row+1])
            if a is None or b is None:
                return None
            t=(y-y0)/(y1-y0)
            return a*(1-t)+b*t
    return None


def fit_matrix(theta: float, target_z: float):
    return (Matrix.Translation(Vector((target_x,target_y,target_z)))
            @ Matrix.Rotation(theta,4,"X")
            @ Matrix.Diagonal(Vector((scale,scale,scale,1)))
            @ Matrix.Translation(-source_anchor))


def sampled_deltas(matrix, sparse=True):
    deltas=[]
    rows=range(14)
    columns=range(0,33,4) if sparse else range(33)
    for row in rows:
        for col in columns:
            p=matrix @ top_source[row*33+col]
            target=roof_height(p.x,p.y)
            if target is not None:
                deltas.append(p.z-target)
    return deltas


# Optimize only pitch and vertical socket placement. The nominal 87 mm width,
# front y and source topology are fixed. This avoids shaping the cover mesh to
# hide a failed fit; all six cap parts receive one identical rigid/uniform map.
best=None
for step in range(181):
    theta=.10+step*.001
    zero=sampled_deltas(fit_matrix(theta,0),sparse=True)
    if len(zero)<50:
        continue
    z=-sum(zero)/len(zero)
    residual=[d+z for d in zero]
    rms=(sum(d*d for d in residual)/len(residual))**.5
    if best is None or rms<best[0]:
        best=(rms,theta,z)
assert best is not None
roughness_rms, theta, matched_z = best
visible_clearance=.0015
matrix=fit_matrix(theta,matched_z+visible_clearance)
all_deltas=sampled_deltas(matrix,sparse=False)
stats={
    "sample_count": len(all_deltas),
    "mean_clearance_mm": round(sum(all_deltas)/len(all_deltas)*1000,3),
    "min_clearance_mm": round(min(all_deltas)*1000,3),
    "max_clearance_mm": round(max(all_deltas)*1000,3),
    "rms_from_intended_clearance_mm": round((sum((d-visible_clearance)**2 for d in all_deltas)/len(all_deltas))**.5*1000,3),
}
surface_alignment_gate = (stats["min_clearance_mm"] > -3.0
                          and stats["max_clearance_mm"] < 6.0
                          and stats["rms_from_intended_clearance_mm"] < 2.5)
shank_back_center=matrix @ shank_world[13*33+16]
next_cover=bpy.data.objects["MaruGawara_Cover_R1_C1"]
next_cover_front_y=min((next_cover.matrix_world @ v.co).y
                       for v in next_cover.data.vertices)
joint_gap_mm=(next_cover_front_y-shank_back_center.y)*1000
# A real overlap must tuck the socket at least 5 mm below the next course.
# A positive value leaves an exposed butt seam on top of row 0.
hidden_joint_gate=joint_gap_mm <= -5.0
fit_gate=surface_alignment_gate and hidden_joint_gate
print("SORA_CAP_FIT", json.dumps({"scale":scale,"pitch_degrees":math.degrees(theta),
                                   "anchor_z_m":matched_z+visible_clearance,
                                   "surface_alignment_gate":surface_alignment_gate,
                                   "hidden_joint_gate":hidden_joint_gate,
                                   "overall_geometry_gate":fit_gate,
                                   "exposed_gap_to_next_cover_mm":round(joint_gap_mm,3),
                                   "stats":stats},sort_keys=True))
if os.environ.get("SORA_CAP_FIT_ANALYSIS_ONLY") == "1":
    raise SystemExit(0)

for name in old_badge:
    bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
for name,obj in cap_objects.items():
    obj.matrix_world=matrix @ source_matrices[name]
    obj["roof_fit_review_only"] = True
    obj["fit_scale"] = scale
    obj["fit_pitch_degrees"] = math.degrees(theta)
assert tuple(tuple(row) for row in scene.camera.matrix_world)==camera_before
assert scene.camera.data.ortho_scale==camera_scale_before
for name, values in lights_before.items():
    light=bpy.data.objects[name]
    assert tuple(tuple(row) for row in light.matrix_world)==values["matrix"]
    assert light.data.energy==values["energy"] and light.data.size==values["size"]
    assert tuple(light.data.color)==values["color"]

bpy.context.preferences.filepaths.save_version=0
scene.render.filepath=str(OUT/"Nyaagyu_KawaraBay_SORA_Cap_FixedReview.png")
for image in bpy.data.images:
    if image.source == "FILE" and image.filepath:
        image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"Nyaagyu_KawaraBay_SORA_Cap_FitReview.blend"))
bpy.ops.render.render(write_still=True)

manifest={
    "status":"derived source-only art review; never a playable or parent-roof change",
    "generator":"scripts/art/create_nyaagyu_sora_eave_roof_fit_review.py",
    "inputs":{
        "roof_blend_sha256":roof_manifest["outputs"][roof_blend.name],
        "roof_fbx_sha256":roof_manifest["outputs"]["SM_Nyaagyu_KawaraBay.fbx"],
        "cap_blend_sha256":cap_manifest["outputs"][cap_blend.name],
        "cap_fbx_sha256":cap_manifest["outputs"]["SM_Nyaagyu_SORA_EaveCap.fbx"],
        "sora_svg_sha256":cap_manifest["source_svg_sha256"],
    },
    "removed_old_review_badge_only":list(old_badge),
    "fit":{
        "nominal_cover_width_m":nominal_width,
        "measured_cap_shank_front_width_m":front_width,
        "uniform_scale":scale,
        "pitch_degrees":math.degrees(theta),
        "source_anchor_m":list(source_anchor),
        "target_anchor_m":[target_x,target_y,matched_z+visible_clearance],
        "transform_rows":[list(row) for row in matrix],
        "roof_clearance_mm":stats,
        "surface_alignment_gate_pass":surface_alignment_gate,
        "exposed_gap_to_next_cover_mm":joint_gap_mm,
        "hidden_joint_requires_overlap_mm":5.0,
        "hidden_joint_gate_pass":hidden_joint_gate,
        "geometry_gate_pass":fit_gate,
        "gate_note":"FAILED: source shank ends before next cover; surface clearance alone is insufficient. No historical, Lumen/Nanite, or visual AAA approval.",
    },
    "fixed_camera_visual_review":{
        "status":"failed source-only art review",
        "findings":["exposed shank butt seam before the next course",
                    "cap clay finish visibly differs from the surrounding ibushi roof",
                    "SORA molded crest has weak contrast and is small at this roof camera distance"],
    },
    "review_camera_unchanged":True,
    "review_lights_unchanged":True,
    "render_engine":scene.render.engine,
    "render_resolution":[scene.render.resolution_x,scene.render.resolution_y],
    "outputs":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        OUT/"Nyaagyu_KawaraBay_SORA_Cap_FitReview.blend",
        OUT/"Nyaagyu_KawaraBay_SORA_Cap_FixedReview.png")},
}
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print("SORA_CAP_FIT_REVIEW",json.dumps(manifest,sort_keys=True))
