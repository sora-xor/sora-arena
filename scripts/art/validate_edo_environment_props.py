"""Blender source/FBX round-trip check for the three modular hero props.

Run: blender -b Content/SourceArt/Environment/Original/Edo_Alien_Props.blend \
  --python scripts/art/validate_edo_environment_props.py

This verifies authoring/export scale and slot identities in Blender. It cannot
substitute for an Unreal import, visual pass, or performance test.
"""

import hashlib
import json
import atexit
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

# Blender 5.2 returns status 0 after an uncaught --python exception. Make a
# failed assertion fail the invoking build/validation command as well.
_validated = False
def _exit_failed_validation():
    if not _validated:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
atexit.register(_exit_failed_validation)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/Original"
manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
expected = ["SM_Edo_LanternPost", "SM_Nyaagyu_ToriiGate", "SM_Alien_DebtKiosk"]
assert bpy.app.version[:2] == (5, 2), bpy.app.version_string
assert Path(bpy.data.filepath).resolve() == (OUT / manifest["source_blend"]).resolve()
assert [entry["name"] for entry in manifest["assets"]] == expected
assert manifest["schema_version"] == 1
assert manifest["lantern_light_local_z_m"] == 2.52
assert "Original project-owned geometry" in manifest["license"]
assert "CC0 Poly Haven" in manifest["license"]
for name in (manifest["source_blend"], manifest["preview"], manifest["detail_preview"]):
    assert (OUT / name).stat().st_size > 1000, name

image_paths = [Path(bpy.path.abspath(image.filepath)).resolve() for image in bpy.data.images if image.source == "FILE"]
assert len(image_paths) >= 9, image_paths
assert all(path.is_file() and path.is_relative_to(OUT.parent / "PolyHaven") for path in image_paths)

lantern_collection = bpy.data.collections.get("Edo_LanternPost_Editable")
assert lantern_collection is not None
core = lantern_collection.objects.get("Amber_LightCore")
assert core is not None and abs(core.location.z - manifest["lantern_light_local_z_m"]) < 0.001

for entry in manifest["assets"]:
    fbx = OUT / entry["fbx"]
    assert entry["fbx"] == entry["name"] + ".fbx"
    assert fbx.read_bytes().startswith(b"Kaydara FBX Binary")
    assert b"/Users/" not in fbx.read_bytes(), "Export must not embed the artist's absolute texture path"
    assert hashlib.sha256(fbx.read_bytes()).hexdigest() == entry["fbx_sha256"]
    assert entry["source_triangles"] >= 3000
    assert entry["world_builder_yaw_offset_deg"] == (0 if "Lantern" in entry["name"] else 90)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    render = [obj for obj in meshes if obj.name == entry["name"]]
    proxies = [obj for obj in meshes if obj.name.startswith("UCX_" + entry["name"] + "_")]
    assert len(render) == 1 and len(proxies) == entry["collision_boxes"], (entry["name"], [obj.name for obj in meshes])
    bounds = [render[0].matrix_world @ Vector(corner) for corner in render[0].bound_box]
    for axis in range(3):
        assert abs(min(p[axis] for p in bounds) - entry["bounds_m"]["min"][axis]) < 0.02, entry["name"]
        assert abs(max(p[axis] for p in bounds) - entry["bounds_m"]["max"][axis]) < 0.02, entry["name"]
    # Opening the source .blend before FBX import forces Blender to suffix
    # imported material datablocks with .001; Unreal receives unsuffixed names.
    slots = {mat.name.split(".", 1)[0] for mat in render[0].data.materials}
    assert len(slots) >= 4, (entry["name"], slots)
    if "Lantern" in entry["name"]:
        assert {"M_Env_Timber", "M_Env_Stone", "M_Env_WashiPaper"} <= slots
    elif "Torii" in entry["name"]:
        assert {"M_Env_VermilionLacquer", "M_Env_Timber", "M_Env_Stone"} <= slots
    else:
        assert {"M_Env_Metal", "M_Env_Stone", "M_Env_AlienCyan"} <= slots
    print("FBX_ROUNDTRIP_PASS", entry["name"], "bounds_m", entry["bounds_m"], "slots", len(slots), "ucx", len(proxies))

print("EDO_ENVIRONMENT_SOURCE_VALIDATED: 3 meshes, metric scale, editable Blender source, linked CC0 maps, FBX slots/UCX/hashes")
_validated = True
