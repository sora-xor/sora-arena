"""Read saved DojoKit packages in a fresh editor process; never repair or save.

Run after import_nyaagyu_dojo_kit.py. This verifies saved resources and fallback
LODs, not Nanite rasterization, M1 compatibility, or photoreal art acceptance.
"""
from pathlib import Path
import hashlib
import json
import os
import sys


def main():
    import unreal
    root = Path(unreal.Paths.project_dir()).resolve()
    sys.path.insert(0, str(root / "scripts/unreal"))
    from sora_engine_pin import require_running_engine
    from dojo_nanite import audit_saved_module, read_import_baselines, verify_saved_import, require
    require_running_engine("DojoKit saved-package validation")
    manifest = json.loads((root / "Content/SourceArt/Environment/NyaagyuDojoKit/manifest.json").read_text())
    require(hashlib.sha256((root / manifest["generator"]).read_bytes()).hexdigest() == manifest["generator_sha256"],
            "generator changed since the kit was built")
    modules = manifest["modules"]
    names = [module["asset"] for module in modules]
    required = {"SM_DojoBay_" + name for name in ("Panel", "Renji", "RenjiHigh", "Shoji", "DoorOpen")}
    required.update("SM_DojoRail_" + name for name in ("Nageshi", "Cornice", "Koshi", "Nuki"))
    required.update("SM_DojoFloor_" + str(i) for i in range(4))
    required.update(("SM_DojoColumn", "SM_DojoCeiling", "SM_DojoKamiza"))
    require(len(names) == len(required) and set(names) == required, "required kit module inventory differs")
    require(bool(os.environ.get("SORA_DOJO_IMPORT_LOG")), "set SORA_DOJO_IMPORT_LOG to the completed import log")
    baselines = read_import_baselines(os.environ["SORA_DOJO_IMPORT_LOG"], names)
    subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for module in modules:
        for lod in module["lods"]:
            source = root / lod["file"]
            require(source.is_file() and hashlib.sha256(source.read_bytes()).hexdigest() == lod["sha256"],
                    f"{module['asset']}: authored LOD source is missing or changed")
        audit = audit_saved_module(module, root, unreal, subsystem,
                                   unreal.EditorAssetLibrary, unreal.MaterialEditingLibrary)
        verify_saved_import(audit, baselines[module["asset"]])
        unreal.log("SORA_DOJO_SAVED_MODULE " + json.dumps(audit, sort_keys=True))
    unreal.log(f"SORA_DOJO_KIT_VALIDATED: {len(modules)} saved modules reopened with full fallback and materials")


if __name__ == "__main__":
    main()
