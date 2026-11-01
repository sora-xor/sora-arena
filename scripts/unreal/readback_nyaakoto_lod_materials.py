"""Read back what each LOD of the imported SK_NyaagyuSamurai renders its sections with, and each LOD's morph threshold.

**Why.** Unreal's FBX export of the mesh (s110) writes each section's own MaterialIndex (FbxSkeletalMeshExport.cpp:226),
not routed through LODInfo.LODMaterialMap, which the renderer uses. In that export LOD2's materials are a permutation
of ours. Our LOD2 FBX lists its 23 materials in another order than LOD0's, and an imported LOD's sections keep its own
order: FLODUtilities::MatchImportedMaterials maps them to the base slots by imported slot name, through
LODMaterialMap (LODUtilities.cpp:3948-3981). This reads what the renderer gets.

**Per LOD:**
- the section count;
- each section's material slot as SkeletalMeshEditorSubsystem.GetLODMaterialSlot routes it (through LODMaterialMap);
- the LOD's build settings' MorphThresholdPosition (check_nyaakoto_ue_morph_export.py models it).

**Per slot:** its material and its imported slot name.

check_nyaakoto_lod_materials.py (host Python) pairs the sections with the export's polygon runs and compares each
LOD's triangles per material with our FBX's.

Read-only: nothing is imported, changed or saved.

Run: scripts/toolchain/run-editor-script.sh scripts/unreal/readback_nyaakoto_lod_materials.py NYAAKOTO_LOD_MATERIALS_READY
         [log] -- --out Saved/NyaakotoThirdPerson/Unreal/<new name>.json
"""

import json
import sys
from pathlib import Path

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Nyaakoto LOD material readback")

ROOT = Path(unreal.Paths.project_dir()).resolve()
ASSET = "/Game/Generated/Meshes/SK_NyaagyuSamurai"
MARKER = "NYAAKOTO_LOD_MATERIALS_READY"


def fail(message):
    raise RuntimeError("nyaakoto LOD material readback: " + message)


args = sys.argv[1:]
if "--out" not in args:
    fail("--out <new .json under Saved/NyaakotoThirdPerson/Unreal> is required")
OUT = (ROOT / args[args.index("--out") + 1]).resolve()
if OUT.exists() or OUT.suffix != ".json" or not OUT.is_relative_to(ROOT / "Saved/NyaakotoThirdPerson/Unreal"):
    fail(f"the output must be a new .json under Saved/NyaakotoThirdPerson/Unreal: {OUT}")
SUB = unreal.SkeletalMeshEditorSubsystem
missing = [n for n in ("get_lod_count", "get_num_sections", "get_lod_material_slot", "get_lod_build_settings",
                       "get_num_verts") if not hasattr(SUB, n)]
if missing:
    fail(f"SkeletalMeshEditorSubsystem lacks {missing}")
sub = unreal.get_editor_subsystem(SUB)
mesh = unreal.EditorAssetLibrary.load_asset(ASSET)
if not isinstance(mesh, unreal.SkeletalMesh):
    fail(f"{ASSET} is not a skeletal mesh")


def prop(struct, name):
    try:
        return struct.get_editor_property(name)
    except Exception as exc:                                  # an unexposed property is recorded, not guessed
        return f"unreadable: {exc.__class__.__name__}"


slots = []
for i, m in enumerate(mesh.get_editor_property("materials")):
    mi = prop(m, "material_interface")
    slots.append({"slot": i, "material": mi.get_name() if isinstance(mi, unreal.MaterialInterface) else str(mi),
                  "slot_name": str(prop(m, "material_slot_name")),
                  "imported_slot_name": str(prop(m, "imported_material_slot_name"))})
lods = []
for lod in range(sub.get_lod_count(mesh)):
    n = sub.get_num_sections(mesh, lod)
    if n is None or n < 1:
        fail(f"LOD{lod} has no sections ({n})")
    section_slots = [int(sub.get_lod_material_slot(mesh, lod, s)) for s in range(n)]
    if any(s < 0 or s >= len(slots) for s in section_slots):
        fail(f"LOD{lod} routes a section to no slot: {section_slots}")
    settings = sub.get_lod_build_settings(mesh, lod)
    lods.append({"lod": lod, "vertices": int(sub.get_num_verts(mesh, lod)), "sections": int(n),
                 "section_slots": section_slots,
                 "section_materials": [slots[s]["material"] for s in section_slots],
                 "morph_threshold_position_cm": float(settings.get_editor_property("morph_threshold_position")),
                 "recompute_normals": bool(settings.get_editor_property("recompute_normals"))})
record = {"asset": ASSET, "slots": slots, "lods": lods,
          "note": "GetLODMaterialSlot routes each section through LODInfo.LODMaterialMap where it has an entry"}
OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "x", encoding="utf-8") as fh:
    json.dump(record, fh, indent=1)
print(MARKER, json.dumps([{k: l[k] for k in ("lod", "sections", "vertices", "morph_threshold_position_cm")} for l in lods]))
