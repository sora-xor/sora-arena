"""Round-trip Nyaakoto's authored skeletal LOD FBXs in a clean Blender session.

Run: blender -b --factory-startup --python scripts/art/validate_nyaakoto_lods.py

Each LOD FBX, re-imported: its record's hash, counts, 20 bones, 23 slots, CoatBlend, bounds (its own and LOD0's), the
four exact SORA kamon at the hero source's recorded placements, and its empty-fist morph targets. PawEmpty_R and
PawEmpty_L are 0, each moves exactly its paw's vertices to where nyaakoto_tp_paws.empty_points puts them from this
LOD's own bind, and nothing else moves.
"""

import atexit
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nyaakoto_tp_paws as TPP  # noqa: E402
from sora_kamon_validation import assert_paths_embedded, expected_paths, reference_paths


passed = False


def ensure_failure_exit():
    if not passed:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(ensure_failure_exit)
root = Path(__file__).resolve().parents[2]
hero = root / "Content/SourceArt/Characters/Hero"
lod_dir = hero / "LOD"
record = json.loads((lod_dir / "manifest.json").read_text())
runtime = json.loads((hero / "runtime_skin_manifest.json").read_text())
source = json.loads((hero / "manifest.json").read_text())
pbr = json.loads((hero / "PBR/manifest.json").read_text())
assert record["schema_version"] == 1
assert record["source_blend_sha256"] == runtime["runtime_blend_sha256"]
assert record["lod0_fbx_sha256"] == runtime["skeletal_fbx_sha256"]
assert record["sora_kamon_svg_sha256"] == runtime["sora_kamon_svg_sha256"]
assert [entry["level"] for entry in record["lods"]] == [1, 2]
assert record["lods"][0]["vertices"] < runtime["source_vertices"] * .5
assert record["lods"][1]["vertices"] < record["lods"][0]["vertices"] * .5
assert hashlib.sha256((root / "Content/SourceArt/SK_NyaagyuSamurai.fbx").read_bytes()).hexdigest() == record["lod0_fbx_sha256"]

paths = reference_paths(root)
# Each placement as the hero source records it: study A moved the chest and sode kamon rigidly (proportions).
assert set(source["sora_kamon_marks"]) == {"chest", "waist", "sode_-1", "sode_1"}
marks = {placement: expected_paths(paths, m["center"], m["diameter"], m["plane"])
         for placement, m in source["sora_kamon_marks"].items()}
for entry in record["lods"]:
    file = lod_dir / entry["fbx"]
    assert file.is_file() and file.stat().st_size > 10000
    assert hashlib.sha256(file.read_bytes()).hexdigest() == entry["sha256"]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(file))
    imported = set(bpy.data.objects) - before
    meshes = [obj for obj in imported if obj.type == "MESH"]
    rigs = [obj for obj in imported if obj.type == "ARMATURE"]
    assert len(meshes) == len(rigs) == 1
    mesh, rig = meshes[0], rigs[0]
    assert mesh.name == f"SK_NyaagyuSamurai_LOD{entry['level']}"
    assert mesh.parent == rig and len(rig.data.bones) == 20
    assert set(rig.data.bones.keys()) == set(runtime["skeleton_bones"])
    assert len(mesh.data.vertices) == entry["vertices"]
    triangles = sum(len(face.vertices) - 2 for face in mesh.data.polygons)
    assert triangles == entry["triangles"]
    assert all(len(vertex.groups) == 1 for vertex in mesh.data.vertices)
    materials = {material.name.split(".", 1)[0] for material in mesh.data.materials}
    assert materials == set(entry["material_slots"]) == set(pbr["material_slots"])
    coat = mesh.data.color_attributes.get("CoatBlend")
    assert coat is not None and coat.domain == "CORNER"
    assert len(mesh.data.color_attributes) == 1 and len(coat.data) == len(mesh.data.loops)
    grey_slot = next(index for index, material in enumerate(mesh.data.materials)
                     if material.name.split(".",1)[0] == "M_Hero_GreyTabbyFur")
    grey_blend = [coat.data[loop].color[0] for face in mesh.data.polygons
                  if face.material_index == grey_slot for loop in face.loop_indices]
    assert min(grey_blend) < .01 and max(grey_blend) > .99
    assert sum(.1 < value < .9 for value in grey_blend) > 50
    world = [mesh.matrix_world @ Vector(corner) for corner in mesh.bound_box]
    for axis_index, axis_name in enumerate("xyz"):
        low = min(point[axis_index] for point in world)
        high = max(point[axis_index] for point in world)
        assert math.isclose(low, entry["bounds_m"][axis_name][0], abs_tol=.012)
        assert math.isclose(high, entry["bounds_m"][axis_name][1], abs_tol=.012)
        assert math.isclose(low, runtime["bounds_m"]["min"][axis_index], abs_tol=.02)    # LOD0's bounds
        assert math.isclose(high, runtime["bounds_m"]["max"][axis_index], abs_tol=.02)
    assert_paths_embedded((mesh.matrix_world @ vertex.co for vertex in mesh.data.vertices), marks)
    assert mesh.data.uv_layers.active is not None
    keys = mesh.data.shape_keys
    assert keys is not None and [kb.name for kb in keys.key_blocks] == ["Basis", "PawEmpty_R", "PawEmpty_L"]
    assert all(kb.value == 0.0 for kb in keys.key_blocks[1:])
    mw = np.array([list(r) for r in mesh.matrix_world])

    def key_world(block):
        co = np.empty(len(block.data) * 3, np.float32)
        block.data.foreach_get("co", co)
        return co.reshape(-1, 3).astype(np.float64) @ mw[:3, :3].T + mw[:3, 3]

    bind = key_world(keys.key_blocks["Basis"])
    group = np.array([mesh.vertex_groups[v.groups[0].group].name for v in mesh.data.vertices])
    morph = {}
    for side in ("R", "L"):
        paw = entry["paws"]["by_side"][side]
        skel = TPP.skeleton({k: (np.array(v) if isinstance(v, list) else v) for k, v in paw["frame"].items()},
                            paw["palm_radii_m"])
        hand = group == f"hand_{side}"
        assert int(hand.sum()) == paw["vertices"], (entry["level"], side, int(hand.sum()), paw["vertices"])
        got = key_world(keys.key_blocks[f"PawEmpty_{side}"])
        rule = float(np.abs(got[hand] - TPP.empty_points(bind[hand], skel)).max())
        others = float(np.abs(got[~hand] - bind[~hand]).max())
        moved = float(np.linalg.norm(got[hand] - bind[hand], axis=1).max())
        assert rule < 1e-5 and others == 0.0 and moved > 0.02, (entry["level"], side, rule, others, moved)
        morph[side] = [round(rule * 1000.0, 5), round(moved * 100.0, 3)]
    print("NYAAKOTO_LOD_FBX_PASS", entry["level"], len(mesh.data.vertices),
          triangles, len(mesh.data.materials), len(rig.data.bones), "morph rule mm / move cm", morph)

passed = True
