"""An authored-normal candidate of SK_NyaagyuSamurai beside the s132 baseline, for root's controlled comparison.

Root (2026-10-26) asked for the same mesh source, pose, material, camera and light, with:
- recompute normals disabled, and the imported authored normals verified;
- the tangent settings explicit;
- the s132 baseline preserved;
- a separate candidate asset and output.

What it does:
- **The baseline** /Game/Generated/Meshes/SK_NyaagyuSamurai must be the package s132 drew (its files' SHA-256 against
  s132's recorded inputs). It is left alone, and hashed again at the end.
- **The candidate** is a duplicate of the baseline at a new path. It has the same imported source, LODs, sockets, morph
  targets, skeleton and material slots.
- **One setting changes:** the candidate's LOD0 build settings are the baseline's, with recompute_normals false. They
  are applied through SkeletalMeshEditorSubsystem.SetLodBuildSettings, which rebuilds the LOD from its imported source.
  The tangents stay as the baseline's, read back and required: recomputed, MikkTSpace, 8-bit basis. The FBX has none
  of its own, since Blender's export wrote normals only. LOD1 and LOD2 keep the baseline's settings: root's views are
  LOD0.
- **Readback:** both assets' build settings for every LOD. Every field must be equal, except recompute_normals on the
  candidate's LOD0.
- **Export:** the candidate goes out through Unreal's FBX exporter, every LOD with its morph targets, so
  compare_fbx_normals.py can verify on the host that LOD0 now carries the authored normals.

Run (lane holder; the skeletal FBX export needs the renderer):
  scripts/toolchain/run-editor-script.sh --rhi scripts/unreal/prepare_nyaakoto_authored_normals.py \\
      NYAAKOTO_AUTHORED_NORMALS_READY <log> -- --baseline-inputs Saved/W18Rebuild/s132_tp_review.inputs \\
      --readback Saved/NyaakotoThirdPerson/Unreal/<new>.json --export Saved/NyaakotoThirdPerson/Unreal/<new>.fbx

An asset preparation and readback only: not a render, and not an adoption of authored normals.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Nyaakoto authored-normal candidate")

ROOT = Path(unreal.Paths.project_dir()).resolve()
ASSETS = unreal.EditorAssetLibrary
SKEL = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
BASELINE = "/Game/Generated/Meshes/SK_NyaagyuSamurai"
CANDIDATE_DIR = "/Game/Generated/Candidates/AuthoredNormals"
CANDIDATE = f"{CANDIDATE_DIR}/SK_NyaagyuSamurai_AuthoredNormals"
MARKER = "NYAAKOTO_AUTHORED_NORMALS_READY"
MORPHS = ["PawEmpty_L", "PawEmpty_R"]
# FSkeletalMeshBuildSettings, as Python names them. Each is read on both assets and compared.
FIELDS = ("recompute_normals", "recompute_tangents", "use_mikk_t_space", "compute_weighted_normals",
          "remove_degenerates", "use_high_precision_tangent_basis", "use_high_precision_skin_weights",
          "use_full_precision_u_vs", "use_backwards_compatible_f16_trunc_u_vs", "threshold_position",
          "threshold_tangent_normal", "threshold_uv", "morph_threshold_position", "bone_influence_limit")
TANGENTS = {"recompute_tangents": True, "use_mikk_t_space": True, "use_high_precision_tangent_basis": False}


def fail(message):
    raise RuntimeError("nyaakoto authored normals: " + message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def arg(name):
    args = sys.argv[1:]
    if name not in args:
        fail(f"{name} is required")
    return args[args.index(name) + 1]


def package_files(asset_path):
    """The files on disk of an asset's package (.uasset and any sidecars), relative to the project."""
    rel = asset_path[len("/Game/"):]
    base = ROOT / "Content" / rel
    return sorted(p for p in base.parent.glob(base.name + ".*") if p.is_file())


def settings_row(mesh, lod):
    s = unreal.SkeletalMeshEditorSubsystem.get_lod_build_settings(mesh, lod)
    row = {}
    for key in FIELDS:
        try:
            value = s.get_editor_property(key)
            row[key] = value if isinstance(value, (bool, int, float)) else str(value)
        except Exception as exc:  # a field this engine names otherwise: recorded, not guessed
            row[key] = f"unread: {exc.__class__.__name__}"
    return row


def main():
    inputs = (ROOT / arg("--baseline-inputs")).read_text().splitlines()
    readback_path = (ROOT / arg("--readback")).resolve()
    export_path = (ROOT / arg("--export")).resolve()
    for p in (readback_path, export_path):
        if p.exists() or not p.is_relative_to(ROOT / "Saved/NyaakotoThirdPerson/Unreal"):
            fail(f"{p} must be a new file under Saved/NyaakotoThirdPerson/Unreal")
    if ASSETS.does_asset_exist(CANDIDATE):
        fail(f"{CANDIDATE} exists: the candidate is a new asset")
    # The baseline is the package s132 drew.
    recorded = {line.split("  ", 1)[1]: line.split("  ", 1)[0] for line in inputs if "  " in line}
    before = {}
    for f in package_files(BASELINE):
        rel = "Meshes/" + f.name                    # s132's inputs list Content/Generated relative paths
        if recorded.get(rel) != sha256(f):
            fail(f"{f.name} is not the package s132 drew ({recorded.get(rel)})")
        before[f.relative_to(ROOT).as_posix()] = sha256(f)
    if not before:
        fail("no baseline package files")
    baseline = unreal.load_asset(BASELINE)
    lods = SKEL.get_lod_count(baseline)
    base_rows = [settings_row(baseline, lod) for lod in range(lods)]
    ASSETS.make_directory(CANDIDATE_DIR)
    candidate = ASSETS.duplicate_asset(BASELINE, CANDIDATE)
    if not isinstance(candidate, unreal.SkeletalMesh):
        fail("the duplicate is not a skeletal mesh")
    settings = unreal.SkeletalMeshEditorSubsystem.get_lod_build_settings(candidate, 0)
    settings.set_editor_property("recompute_normals", False)
    for key, value in TANGENTS.items():
        settings.set_editor_property(key, value)
    unreal.SkeletalMeshEditorSubsystem.set_lod_build_settings(candidate, 0, settings)
    unreal.SystemLibrary.execute_console_command(
        unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(), "Editor.AsyncAssetCompilationFinishAll")
    if not ASSETS.save_loaded_asset(candidate):
        fail("the candidate did not save")
    candidate = unreal.load_asset(CANDIDATE)
    cand_rows = [settings_row(candidate, lod) for lod in range(SKEL.get_lod_count(candidate))]
    if len(cand_rows) != lods:
        fail(f"the candidate has {len(cand_rows)} LODs, the baseline {lods}")
    differences = []
    for lod, (b, c) in enumerate(zip(base_rows, cand_rows)):
        for key in FIELDS:
            if b[key] != c[key]:
                differences.append({"lod": lod, "field": key, "baseline": b[key], "candidate": c[key]})
    if differences != [{"lod": 0, "field": "recompute_normals", "baseline": True, "candidate": False}]:
        fail(f"the candidate's settings differ otherwise: {differences}")
    for key, value in TANGENTS.items():
        if cand_rows[0][key] != value or base_rows[0][key] != value:
            fail(f"{key} reads baseline {base_rows[0][key]}, candidate {cand_rows[0][key]}, not {value}")
    names = sorted(str(n) for n in candidate.get_all_morph_target_names())
    if names != MORPHS or not candidate.has_vertex_colors():
        fail(f"the candidate's morphs read {names}, vertex colours {candidate.has_vertex_colors()}")
    slots = [str(s.get_editor_property("material_slot_name")) for s in candidate.get_editor_property("materials")]
    base_slots = [str(s.get_editor_property("material_slot_name")) for s in baseline.get_editor_property("materials")]
    if slots != base_slots:
        fail("the candidate's material slots differ from the baseline's")
    options = unreal.FbxExportOption()
    for prop, value in (("level_of_detail", True), ("export_morph_targets", True), ("ascii", False),
                        ("collision", False), ("vertex_color", True)):
        options.set_editor_property(prop, value)
    task = unreal.AssetExportTask()
    task.object = candidate
    task.filename = str(export_path)
    task.automated = True
    task.prompt = False
    task.replace_identical = False
    task.exporter = unreal.SkeletalMeshExporterFBX()
    task.options = options
    export_path.parent.mkdir(parents=True, exist_ok=True)
    if not unreal.Exporter.run_asset_export_task(task) or not export_path.is_file():
        fail(f"Unreal did not export {export_path.name}")
    after = {f.relative_to(ROOT).as_posix(): sha256(f) for f in package_files(BASELINE)}
    if after != before:
        fail("the baseline's package changed")
    readback = {"baseline": {"asset": BASELINE, "package_sha256": before, "package_sha256_after": after,
                             "lod_build_settings": base_rows},
                "candidate": {"asset": CANDIDATE, "duplicated_from": BASELINE,
                              "package_sha256": {f.relative_to(ROOT).as_posix(): sha256(f) for f in package_files(CANDIDATE)},
                              "lod_build_settings": cand_rows, "morph_targets": names, "material_slots": slots},
                "differences": differences, "tangents_required": TANGENTS,
                "export": {"file": str(export_path.relative_to(ROOT)), "sha256": sha256(export_path)},
                "baseline_inputs": {"file": arg("--baseline-inputs"), "sha256": sha256(ROOT / arg("--baseline-inputs"))}}
    with open(readback_path, "x", encoding="utf-8") as fh:
        json.dump(readback, fh, indent=1)
    print(MARKER, json.dumps({"differences": differences, "export_sha256": readback["export"]["sha256"],
                              "baseline_unchanged": after == before}))


main()
