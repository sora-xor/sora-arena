"""Split the existing Dojo source into four visual-only Lumen study FBXs.

Run:
  blender -b Content/SourceArt/Environment/NyaagyuDojo/Nyaagyu_EstateDojo.blend \
    --python scripts/art/create_nyaagyu_dojo_lumen_modules.py

The original .blend and combined FBX are read-only inputs. The split preserves
all visible source polygons and material face assignments; no roof sheets are
closed or otherwise repaired here. Unreal import/cook and Lumen coverage are
not established by this source-only operation.
"""

from __future__ import annotations

import atexit
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys

import bmesh
import bpy


DONE = False


def fail_if_incomplete():
    if not DONE:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


atexit.register(fail_if_incomplete)
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Content/SourceArt/Environment/NyaagyuDojo"
OUT = SOURCE / "LumenModules"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nyaagyu_dojo_module_common import (  # noqa: E402
    MODULE_STEMS, bounds_close, classify, material_triangle_counts,
    triangle_count, triangle_digest, triangle_records, union_bounds, world_bounds,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert bpy.app.version[:2] == (5, 2)
original = json.loads((SOURCE / "manifest.json").read_text())
blend = SOURCE / original["source_blend"]
combined_fbx = SOURCE / original["fbx"]
assert Path(bpy.data.filepath).resolve() == blend.resolve()
assert sha(blend) == original["blend_sha256"]
assert sha(combined_fbx) == original["fbx_sha256"]
editable = bpy.data.collections.get("Nyaagyu_EstateDojo_Editable")
assert editable is not None
parts = [obj for obj in editable.objects if obj.type == "MESH"]
assert len(parts) == original["source_parts"] == 424
groups = classify(parts)
assert triangle_count(parts) == original["source_triangles"] == 73946
source_records = triangle_records(parts)
source_bounds = world_bounds(parts)
source_materials = material_triangle_counts(parts)

OUT.mkdir(parents=True, exist_ok=True)
TEMP_BLEND = Path("/tmp/sora-dojo-lumen-export.blend")

# Match the original combined-FBX export: linked CC0 images stay in the
# unchanged source .blend, while the FBXs carry material identities only.
image_links = []
for mat in bpy.data.materials:
    if mat.name in ("M_Env_Timber", "M_Env_Stone") and mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                image_links.append((node, node.image))
                node.image = None

# Blender writes its current .blend path into FBX Document metadata. Export
# from a disposable /tmp copy so the authored project path is not published.
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(TEMP_BLEND))

modules = []
all_module_records = []
try:
    for label in ("Roof", "Eaves", "Body", "Shoji"):
        selected = groups[label]
        source_subset_records = triangle_records(selected)
        assert triangle_count(selected) == len(source_subset_records)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in selected:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = selected[0]
        export_name = f"SM_Nyaagyu_EstateDojo_{label}"
        boundary_edges = 0
        nonmanifold_edges = 0
        for obj in selected:
            mesh = bmesh.new()
            mesh.from_mesh(obj.data)
            boundary_edges += sum(edge.is_boundary for edge in mesh.edges)
            nonmanifold_edges += sum(not edge.is_manifold for edge in mesh.edges)
            mesh.free()
        fbx = OUT / f"{export_name}.fbx"
        # Blender's FBX exporter truncates names at decimal points (several
        # authored part names encode positions). Temporary stable export IDs
        # retain a lossless source-to-FBX object mapping in the manifest.
        source_names = {obj: obj.name for obj in selected}
        export_names = {
            obj.name: f"DM_{label}_{index:03d}"
            for index, obj in enumerate(selected)
        }
        try:
            for obj in selected:
                obj.name = export_names[source_names[obj]]
            bpy.ops.export_scene.fbx(
                filepath=str(fbx), use_selection=True, object_types={"MESH"},
                apply_unit_scale=True, global_scale=1.0,
                axis_forward="-Y", axis_up="Z", add_leaf_bones=False,
                bake_anim=False, path_mode="STRIP",
            )
        finally:
            for obj in selected:
                obj.name = source_names[obj]
        assert fbx.is_file() and fbx.read_bytes().startswith(b"Kaydara FBX Binary")
        assert b"/Users/" not in fbx.read_bytes(), fbx
        module = {
            "name": export_name,
            "fbx": fbx.name,
            "fbx_sha256": sha(fbx),
            "fbx_bytes": fbx.stat().st_size,
            "parts": len(selected),
            "part_names": [obj.name for obj in selected],
            "export_object_names": export_names,
            "part_material_slots": {
                obj.name: [slot.material.name if slot.material else None
                           for slot in obj.material_slots]
                for obj in selected
            },
            "triangles": triangle_count(selected),
            "world_bounds_m": world_bounds(selected),
            "world_triangle_sha256": triangle_digest(source_subset_records),
            "material_slots": sorted({slot.material.name
                                      for obj in selected for slot in obj.material_slots
                                      if slot.material}),
            "material_triangle_counts": material_triangle_counts(selected),
            "open_boundary_edges_per_part_sum": boundary_edges,
            "nonmanifold_edges_per_part_sum": nonmanifold_edges,
            "export_object_count": len(selected),
        }
        modules.append(module)
        all_module_records.extend(source_subset_records)
        print("NYAAGYU_DOJO_MODULE", label, module["parts"], module["triangles"],
              module["open_boundary_edges_per_part_sum"], fbx, flush=True)
finally:
    for node, image in image_links:
        node.image = image
    TEMP_BLEND.unlink(missing_ok=True)

assert len(editable.objects) == 424
assert sorted(all_module_records) == source_records
assert sum(item["parts"] for item in modules) == 424
assert sum(item["triangles"] for item in modules) == 73946
assert bounds_close(union_bounds([item["world_bounds_m"] for item in modules]), source_bounds)
aggregate_materials = Counter()
for item in modules:
    aggregate_materials.update(item["material_triangle_counts"])
assert dict(sorted(aggregate_materials.items())) == source_materials
assert sum(item["fbx_bytes"] for item in modules) < 100_000_000

record = {
    "schema_version": 1,
    "scope": "Source-only modular Lumen coverage experiment; no Unreal import, card capture, or release change",
    "generator": "scripts/art/create_nyaagyu_dojo_lumen_modules.py",
    "generator_sha256": sha(ROOT / "scripts/art/create_nyaagyu_dojo_lumen_modules.py"),
    "classification": "scripts/art/nyaagyu_dojo_module_common.py",
    "classification_sha256": sha(ROOT / "scripts/art/nyaagyu_dojo_module_common.py"),
    "source_blend": str(blend.relative_to(ROOT)),
    "source_blend_sha256": original["blend_sha256"],
    "source_combined_fbx": str(combined_fbx.relative_to(ROOT)),
    "source_combined_fbx_sha256": original["fbx_sha256"],
    "source_parts": 424,
    "source_triangles": 73946,
    "source_world_bounds_m": source_bounds,
    "source_world_triangle_sha256": triangle_digest(source_records),
    "source_material_triangle_counts": source_materials,
    "export_axis_forward": "-Y",
    "export_axis_up": "Z",
    "placement": "Future Unreal import must enable Combine Meshes for each FBX, disable auto collision, and attach all four resulting visual meshes at the same existing Dojo origin, yaw and scale; not yet implemented",
    "license": original["license"],
    "risks": [
        "Thin and open curved tile courses remain open after splitting; software Lumen distance fields may still be unreliable",
        "Each FBX contains unchanged source objects and transforms rather than a Blender-joined mesh, avoiding join/apply float drift; future Unreal Combine Meshes needs an independent exact-placement check",
        "Additional meshes can increase draw calls and do not guarantee Surface Cache roof coverage",
        "No module has been imported, cooked or profiled in UE 5.8.2 or 5.8.3",
    ],
    "modules": modules,
}
(OUT / "manifest.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
assert sum(path.stat().st_size for path in OUT.iterdir() if path.is_file()) < 100_000_000
print("NYAAGYU_DOJO_MODULES_CREATED", len(modules), record["source_triangles"],
      record["source_world_bounds_m"], flush=True)
DONE = True
