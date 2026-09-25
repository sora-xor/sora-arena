"""Import the authored Nyaakoto LOD1/LOD2 FBXs into the runtime skeletal mesh.

Run after SK_NyaagyuSamurai LOD0 exists. The source assets remain canonical;
Unreal does not silently generate or replace the close-range hero silhouette.
"""

import hashlib
import json
from pathlib import Path
import sys

import unreal


sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Nyaakoto LOD import")
root = Path(unreal.Paths.project_dir()).resolve()
hero = root / "Content/SourceArt/Characters/Hero"
lod_dir = hero / "LOD"
record = json.loads((lod_dir / "manifest.json").read_text())
runtime = json.loads((hero / "runtime_skin_manifest.json").read_text())
pbr = json.loads((hero / "PBR/manifest.json").read_text())
if (record.get("schema_version") != 1
        or record.get("generator") != "scripts/art/generate_nyaakoto_lods.py"
        or record.get("source_blend_sha256") != runtime["runtime_blend_sha256"]
        or record.get("lod0_fbx_sha256") != runtime["skeletal_fbx_sha256"]
        or record.get("sora_kamon_svg_sha256") != runtime["sora_kamon_svg_sha256"]
        or [entry["level"] for entry in record.get("lods", [])] != [1, 2]):
    raise RuntimeError("Nyaakoto authored LOD identities or source hashes changed")

assets = unreal.EditorAssetLibrary
mesh = assets.load_asset("/Game/Generated/Meshes/SK_NyaagyuSamurai.SK_NyaagyuSamurai")
if not isinstance(mesh, unreal.SkeletalMesh):
    raise RuntimeError("Nyaakoto LOD0 skeletal mesh must be imported first")
subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
if subsystem.get_lod_count(mesh) < 1:
    raise RuntimeError("Nyaakoto LOD0 is absent")
base_vertices = subsystem.get_num_verts(mesh, 0)
vertex_counts = [base_vertices]
for entry in record["lods"]:
    file = lod_dir / entry["fbx"]
    if (not file.is_file()
            or hashlib.sha256(file.read_bytes()).hexdigest() != entry["sha256"]
            or set(entry["material_slots"]) != set(pbr["material_slots"])
            or set(entry["bone_names"]) != set(runtime["skeleton_bones"])):
        raise RuntimeError(f"Authored Nyaakoto LOD source is missing or changed: {file}")
    result = subsystem.import_lod(mesh, entry["level"], str(file))
    if result != entry["level"]:
        raise RuntimeError(f"Unreal failed to import Nyaakoto LOD{entry['level']}: {result}")
    count = subsystem.get_num_verts(mesh, entry["level"])
    if not 0 < count < vertex_counts[-1] * .7:
        raise RuntimeError(f"Nyaakoto LOD{entry['level']} did not reduce runtime vertices: {count}")
    vertex_counts.append(count)

if subsystem.get_lod_count(mesh) != 3:
    raise RuntimeError("Nyaakoto must have exactly three authored runtime LODs")
slots = [str(item.get_editor_property("material_slot_name"))
         for item in mesh.get_editor_property("materials")]
if len(slots) != len(set(slots)) or set(slots) != set(pbr["material_slots"]):
    raise RuntimeError(f"Nyaakoto imported LODs changed the 23 PBR material slots: {slots}")
assets.save_loaded_asset(mesh)
unreal.log(f"NYAAKOTO_AUTHORED_LODS_READY: UE runtime vertices {vertex_counts}")
