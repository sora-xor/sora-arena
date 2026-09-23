"""Check the skinned runtime samurai and exported static FBX use the exact SORA kamon.

Run: blender -b Content/SourceArt/SoraArena_OriginalAssets.blend \
  --python scripts/art/validate_original_sora_kamon.py
This validates source/export geometry, not a cooked Unreal package or screen readability.
"""

import atexit
import json
import os
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_kamon_validation import (PINNED_SVG_SHA256, assert_paths_embedded,
                                   expected_paths, reference_paths)


validated = False


def fail_exit():
    if not validated:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(fail_exit)
root = Path(__file__).resolve().parents[2]
out = root / "Content/SourceArt"
manifest = json.loads((out / "manifest.json").read_text())
assert Path(bpy.data.filepath).resolve() == (out / "SoraArena_OriginalAssets.blend").resolve()
assert manifest["sora_kamon_svg_sha256"] == PINNED_SVG_SHA256
assert manifest["sora_kamon_placements"] == ["headband", "chest"]
hero = bpy.data.objects["SM_NyaagyuSamurai"]
assert hero.type == "MESH"
assert hero.get("sora_kamon_svg_sha256") == PINNED_SVG_SHA256
assert hero.get("sora_kamon_placements") == "headband,chest"
assert hero.parent and hero.parent.type == "ARMATURE"
assert len(hero.parent.data.bones) == 20
source_paths = reference_paths(root)
kamon = {
    "headband": expected_paths(source_paths, (.111, 0, 1.71), .032, "YZ"),
    "chest": expected_paths(source_paths, (.249, 0, 1.085), .074, "YZ"),
}
assert_paths_embedded((vertex.co for vertex in hero.data.vertices), kamon)

fbx = out / "SM_NyaagyuSamurai.fbx"
assert fbx.read_bytes().startswith(b"Kaydara FBX Binary")
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(fbx))
imported = [obj for obj in set(bpy.data.objects)-before if obj.type == "MESH"]
assert len(imported) == 1 and imported[0].name.startswith("SM_NyaagyuSamurai"), [obj.name for obj in imported]
assert_paths_embedded((imported[0].matrix_world @ vertex.co for vertex in imported[0].data.vertices), kamon)
skinned_fbx = out / "SK_NyaagyuSamurai.fbx"
assert skinned_fbx.read_bytes().startswith(b"Kaydara FBX Binary")
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(skinned_fbx))
skinned = [obj for obj in set(bpy.data.objects)-before if obj.type == "MESH"]
assert len(skinned) == 1, [obj.name for obj in skinned]
assert_paths_embedded((vertex.co for vertex in skinned[0].data.vertices), kamon)
print("ORIGINAL_SORA_KAMON_PASS", PINNED_SVG_SHA256, len(source_paths),
      {name: sum(len(path) for path in paths) for name, paths in kamon.items()})
validated = True
