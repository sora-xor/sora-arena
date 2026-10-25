"""What the first-person parts actually draw with, read back in a fresh editor.

Run (UE 5.8, headless, by the holder of the shared engine lane), in its own
editor process after import_runtime_weapon_yumi_rig.py and
import_nyaakoto_fp_paws.py, and before any first-person capture:
  scripts/toolchain/run-editor-script.sh scripts/unreal/verify_yumi_rig_materials.py \
      YUMI_RIG_MATERIALS_OK Saved/YumiRig/material_check.log

The first lit capture drew the bow in /Engine/EngineMaterials/WorldGridMaterial
(Saved/YumiFP/v2). Its importer had written the transient Materials array
while the mesh's async build ran. The importer's own checks run inside the
importing process. The bytes of its saved package are supporting evidence
only. This is the proof: a new editor loads each asset from disk and reads
two things.

- **The assets' slots:** SK_Weapon_18's Materials (one slot, M_Weapon_18 ->
  MI_W18_Weapon), SM_Weapon_18_Ya's static materials (MI_W18_Hane) and
  SM_NyaakotoFP_PawL_Yumi's seven slots (each its own M_NyaakotoFP_*).
- **The components:** a SkeletalMeshComponent and two StaticMeshComponents
  given those meshes, in actors spawned into the editor world, which is
  never saved. GetMaterials must return the same paths, and none may be an
  engine default.

Writes Saved/YumiRig/material_check.json, with every path read. Then it prints
YUMI_RIG_MATERIALS_OK, or raises naming what differs, as the importers do.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("yumi rig material check")
ROOT = Path(unreal.Paths.project_dir()).resolve()
RIG = "/Game/Generated/Qualification/W18YumiRig"
PAWS = "/Game/Generated/Qualification/NyaakotoFPPaws"
OUT = ROOT / "Saved/YumiRig/material_check.json"
PAW_SLOTS = ("M_NyaakotoFP_FurSkin", "M_NyaakotoFP_PawPad", "M_NyaakotoFP_FurCards", "M_NyaakotoFP_KoteSilk",
             "M_NyaakotoFP_KoteUrushi", "M_NyaakotoFP_CordVermilion", "M_NyaakotoFP_MonGold")
WANT = {
    "SK_Weapon_18": {"M_Weapon_18": f"{RIG}/MI_W18_Weapon.MI_W18_Weapon"},
    "SM_Weapon_18_Ya": {"M_Weapon_18": f"{RIG}/MI_W18_Hane.MI_W18_Hane"},
    "SM_NyaakotoFP_PawL_Yumi": {s: f"{PAWS}/{s}.{s}" for s in PAW_SLOTS},
}
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def fail(message):
    raise RuntimeError("yumi rig materials: " + message)


def path(obj):
    return obj.get_path_name() if obj else None


def load(asset_path):
    asset = unreal.load_asset(asset_path)
    if asset is None:
        fail(f"missing {asset_path}")
    return asset


def main():
    record = {"scope": "fresh-editor readback of material bindings; not a render or an admission",
              "assets": {}, "components": {}}
    bow = load(f"{RIG}/SK_Weapon_18")
    arrow = load(f"{RIG}/SM_Weapon_18_Ya")
    paw = load(f"{PAWS}/SM_NyaakotoFP_PawL_Yumi")
    record["assets"]["SK_Weapon_18"] = {str(s.get_editor_property("material_slot_name")):
                                        path(s.get_editor_property("material_interface"))
                                        for s in bow.get_editor_property("materials")}
    for name, mesh in (("SM_Weapon_18_Ya", arrow), ("SM_NyaakotoFP_PawL_Yumi", paw)):
        record["assets"][name] = {str(s.get_editor_property("material_slot_name")):
                                  path(s.get_editor_property("material_interface"))
                                  for s in mesh.get_editor_property("static_materials")}
    # Components resolve what a level draws: the same paths, in slot order.
    sk = ACTORS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0.0, 0.0, 0.0))
    comp = sk.skeletal_mesh_component
    if hasattr(comp, "set_skeletal_mesh_asset"):
        comp.set_skeletal_mesh_asset(bow)
    else:
        comp.set_skeletal_mesh(bow)
    record["components"]["SK_Weapon_18"] = [path(m) for m in comp.get_materials()]
    spawned = [sk]
    for name, mesh in (("SM_Weapon_18_Ya", arrow), ("SM_NyaakotoFP_PawL_Yumi", paw)):
        a = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0.0, 0.0, 0.0))
        a.static_mesh_component.set_static_mesh(mesh)
        record["components"][name] = [path(m) for m in a.static_mesh_component.get_materials()]
        spawned.append(a)
    for a in spawned:
        ACTORS.destroy_actor(a)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1) + "\n")
    problems = []
    for name, want in WANT.items():
        if record["assets"][name] != want:
            problems.append(f"{name} slots {record['assets'][name]} != {want}")
        if sorted(record["components"][name]) != sorted(want.values()):
            problems.append(f"{name} component draws {record['components'][name]}")
        if any(p is None or p.startswith("/Engine/") for p in record["components"][name]):
            problems.append(f"{name} component draws an engine default: {record['components'][name]}")
    if problems:
        fail("; ".join(problems))
    unreal.log("YUMI_RIG_MATERIALS_OK " + json.dumps(record["components"]))


main()
