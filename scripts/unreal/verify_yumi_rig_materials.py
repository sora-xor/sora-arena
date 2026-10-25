"""What the first-person parts actually draw with, read back in a fresh editor.

Run (UE 5.8, headless, by the holder of the shared engine lane), in its own
editor process after import_runtime_weapon_yumi_rig.py and
import_nyaakoto_fp_paws.py, and before any first-person capture:
  scripts/toolchain/run-editor-script.sh scripts/unreal/verify_yumi_rig_materials.py \
      YUMI_RIG_MATERIALS_OK Saved/YumiRig/material_check.log

The first lit capture drew the bow in /Engine/EngineMaterials/WorldGridMaterial
(Saved/YumiFP/v2). Its importer edited copies: an unreal.Array hands out a
copy of each struct element (PyWrapperArray.cpp:409-426,
EPyConversionMethod::Copy), so the slots it changed were never the mesh's,
and it wrote the unchanged array back. The W18 rebuild's step 7 attempt 1
reproduced this through SetMaterials (Saved/W18Rebuild/
ue_rig_import_attempt1.log). The async build, blamed at first, is not needed
to explain it. The importer now writes the edited copies back (131ad94).

The importer's own checks run inside the importing process. The bytes of
its saved package are supporting evidence only. This is the proof: a new
editor loads each asset from disk and reads two things.

- **The rows:** each asset's slots as ordered rows (index, slot name,
  material path), and what a component given that asset draws, as ordered
  rows (index, material path). The components are a SkeletalMeshComponent
  and StaticMeshComponents in actors spawned into the editor world, which is
  never saved.
- **The check:** fp_material_bindings.check against the serialized
  expectations (docs/art-direction/data/fp_material_bindings.json), the same
  rows the capture's gate uses:
  - each asset has exactly its expected slot count and names, each bound to
    its expected material;
  - each component index draws its asset's slot at that index, so a swapped
    override fails;
  - no part draws an engine default.

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
import fp_material_bindings as B  # noqa: E402

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = ROOT / "Saved/YumiRig/material_check.json"
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def fail(message):
    raise RuntimeError("yumi rig materials: " + message)


def load(asset_path):
    asset = unreal.load_asset(asset_path)
    if asset is None:
        fail(f"missing {asset_path}")
    return asset


def component_for(mesh):
    """A component given ``mesh``, in a spawned actor (the editor world is never saved)."""
    if isinstance(mesh, unreal.SkeletalMesh):
        actor = ACTORS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0.0, 0.0, 0.0))
        comp = actor.skeletal_mesh_component
        if hasattr(comp, "set_skeletal_mesh_asset"):
            comp.set_skeletal_mesh_asset(mesh)
        else:
            comp.set_skeletal_mesh(mesh)
    else:
        actor = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0.0, 0.0, 0.0))
        comp = actor.static_mesh_component
        comp.set_static_mesh(mesh)
    return actor, comp


def main():
    expectations = B.load()
    record = {"scope": "fresh-editor readback of material bindings; not a render or an admission",
              "expectations": str(B.EXPECTATIONS.relative_to(ROOT)), "assets": {}}
    problems = []
    for asset_path, want in expectations.items():
        mesh = load(asset_path)
        slots = B.asset_rows(mesh)
        actor, comp = component_for(mesh)
        drawn = B.component_rows(comp)
        ACTORS.destroy_actor(actor)
        record["assets"][asset_path] = B.as_json(slots, drawn)
        problems += B.check(asset_path, slots, drawn, want)
    record["problems"] = problems
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1) + "\n")
    if problems:
        fail("; ".join(problems))
    unreal.log("YUMI_RIG_MATERIALS_OK " + json.dumps({a: [r["material"] for r in v["component"]]
                                                       for a, v in record["assets"].items()}))


main()
