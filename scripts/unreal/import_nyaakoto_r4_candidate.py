"""The r4 repaired-paw candidate of SK_NyaagyuSamurai, beside the s132 baseline and s133's authored-normal candidate.

Root's 21:53 UTC entry (2026-10-26) allows a separate candidate once the UV and pad-contour checks justify it. It is to
use authored normals, for the new candidate only, and to leave s132, s133 and s134 untouched.

**Inputs, by hash:**
- the assembly's FBX (assemble_nyaakoto_r4_paws.py's record);
- its host check (check_nyaakoto_r4_fbx.py), which must have failed nothing;
- the baseline's package, as s132 drew it;
- s133's candidate package, as its readback recorded it.

**The import:** the FBX goes into a new asset, /Game/Generated/Candidates/R4Paws/SK_NyaagyuSamurai_R4Paws, and the
script refuses if it exists. The settings are import_nyaakoto_third_person.py's body import (vertex colours replaced,
morph targets imported), except:
- the baseline's skeleton, so the guard and strike clips play on it;
- no materials (the game binds MI_Nyaakoto_X by slot name);
- no animation and no physics asset.

**Then:**
- **Sockets:** the baseline's three are copied, with bone, location, rotation and scale.
- **LOD0's build settings:** s133's candidate's, field for field: the baseline's with recompute_normals off, and the
  tangents explicit (recomputed, MikkTSpace, 8-bit basis). They are applied through SetLodBuildSettings, which rebuilds
  LOD0 from its imported source.
- **LODs:** LOD0 is the only one. The views are LOD0; LOD1 and LOD2 are not part of this candidate.
- **Readback:** the skeleton, morph targets and vertex colours; the 23 slots (the same names as the baseline's, and
  whether in its order); the LOD count; LOD0's vertices and settings; and the sockets against the baseline's.
- **Export:** through Unreal's FBX exporter, with LOD0's morph targets, so compare_fbx_normals.py can verify on the host
  that LOD0 carries the authored normals.
- **Untouched:** the baseline's, its skeleton's and s133's packages are hashed before and after.

Run (lane holder; the skeletal FBX export needs the renderer):
  scripts/toolchain/run-editor-script.sh --rhi scripts/unreal/import_nyaakoto_r4_candidate.py \\
      NYAAKOTO_R4_CANDIDATE_READY <log> -- --assembly Saved/NyaakotoThirdPerson/Candidates/r4/<assembly> \\
      --fbx-check <check .json> --baseline-inputs Saved/W18Rebuild/s132_tp_review.inputs \\
      --s133-readback Saved/NyaakotoThirdPerson/Unreal/s133_authored_normals_readback.json \\
      --readback Saved/NyaakotoThirdPerson/Unreal/<new>.json --export Saved/NyaakotoThirdPerson/Unreal/<new>.fbx

This is an asset import and readback only: not a render, and not an adoption.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Nyaakoto r4 paw candidate")

ROOT = Path(unreal.Paths.project_dir()).resolve()
ASSETS = unreal.EditorAssetLibrary
SKEL = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
BASELINE = "/Game/Generated/Meshes/SK_NyaagyuSamurai"
SKELETON = "/Game/Generated/Meshes/SK_NyaagyuSamurai_Skeleton"
S133 = "/Game/Generated/Candidates/AuthoredNormals/SK_NyaagyuSamurai_AuthoredNormals"
CANDIDATE_DIR = "/Game/Generated/Candidates/R4Paws"
NAME = "SK_NyaagyuSamurai_R4Paws"
CANDIDATE = f"{CANDIDATE_DIR}/{NAME}"
MARKER = "NYAAKOTO_R4_CANDIDATE_READY"
MORPHS = ["PawEmpty_L", "PawEmpty_R"]
SOCKETS = ("hand_r_grip", "hand_l_grip", "gear_saya_l")
SOCKET_TOL = 1e-4                     # cm, deg
FIELDS = ("recompute_normals", "recompute_tangents", "use_mikk_t_space", "compute_weighted_normals",
          "remove_degenerates", "use_high_precision_tangent_basis", "use_high_precision_skin_weights",
          "use_full_precision_u_vs", "use_backwards_compatible_f16_trunc_u_vs", "threshold_position",
          "threshold_tangent_normal", "threshold_uv", "morph_threshold_position", "bone_influence_limit")
TANGENTS = {"recompute_tangents": True, "use_mikk_t_space": True, "use_high_precision_tangent_basis": False}


def fail(message):
    raise RuntimeError("nyaakoto r4 candidate: " + message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def arg(name):
    args = sys.argv[1:]
    if name not in args:
        fail(f"{name} is required")
    return args[args.index(name) + 1]


def package_sha(asset_path):
    """The SHA-256 of each file of an asset's package (.uasset and any sidecars), by project-relative path."""
    base = ROOT / "Content" / asset_path[len("/Game/"):]
    return {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted(base.parent.glob(base.name + ".*")) if p.is_file()}


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


def socket_row(mesh, name):
    s = mesh.find_socket(name)
    if s is None:
        return None
    loc, rot = s.get_editor_property("relative_location"), s.get_editor_property("relative_rotation")
    scale = s.get_editor_property("relative_scale")
    return {"bone": str(s.get_editor_property("bone_name")), "location_cm": [loc.x, loc.y, loc.z],
            "rotation_deg": [rot.pitch, rot.yaw, rot.roll], "scale": [scale.x, scale.y, scale.z]}


def finish_compilation():
    unreal.SystemLibrary.execute_console_command(
        unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(), "Editor.AsyncAssetCompilationFinishAll")


def main():
    assembly = (ROOT / arg("--assembly")).resolve()
    rec_bytes = (assembly / "record.json").read_bytes()
    rec = json.loads(rec_bytes.decode("utf-8"))
    fbx = assembly / rec["candidate"]["file"]
    if sha256(fbx) != rec["candidate"]["sha256"]:
        fail(f"{fbx.name} is not the assembly's")
    check_path = (ROOT / arg("--fbx-check")).resolve()
    check = json.loads(check_path.read_text())
    if check["failed"] or check["inputs"]["candidate"] != rec["candidate"]["sha256"] \
            or check["inputs"]["assembly_record"] != hashlib.sha256(rec_bytes).hexdigest():
        fail("the FBX's host check did not pass for this assembly")
    inputs = (ROOT / arg("--baseline-inputs")).read_text().splitlines()
    recorded = {line.split("  ", 1)[1]: line.split("  ", 1)[0] for line in inputs if "  " in line}
    s133_path = ROOT / arg("--s133-readback")
    s133 = json.loads(s133_path.read_text())
    readback_path, export_path = (ROOT / arg("--readback")).resolve(), (ROOT / arg("--export")).resolve()
    for p in (readback_path, export_path):
        if p.exists() or not p.is_relative_to(ROOT / "Saved/NyaakotoThirdPerson/Unreal"):
            fail(f"{p} must be a new file under Saved/NyaakotoThirdPerson/Unreal")
    if ASSETS.does_asset_exist(CANDIDATE):
        fail(f"{CANDIDATE} exists: the candidate is a new asset")
    # The baseline is the package s132 drew; s133's candidate is the one its readback recorded.
    before = package_sha(BASELINE)
    if not before or any(recorded.get("Meshes/" + Path(rel).name) != digest for rel, digest in before.items()):
        fail("the baseline is not the package s132 drew")
    s133_before = package_sha(S133)
    if s133_before != s133["candidate"]["package_sha256"]:
        fail("s133's candidate is not the package its readback recorded")
    skeleton_before = package_sha(SKELETON)
    if not skeleton_before or any(recorded.get("Meshes/" + Path(rel).name) != d for rel, d in skeleton_before.items()):
        fail("the skeleton is not the package s132 drew")
    baseline = unreal.load_asset(BASELINE)
    skeleton = baseline.get_editor_property("skeleton")
    if skeleton is None or skeleton.get_path_name().split(".")[0] != SKELETON:
        fail(f"the baseline's skeleton is {skeleton.get_path_name() if skeleton else None}")
    # --- The import ---------------------------------------------------------------------------------------------
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = True
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    options.skeleton = skeleton
    options.skeletal_mesh_import_data.set_editor_property("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)
    options.skeletal_mesh_import_data.set_editor_property("import_morph_targets", True)
    ASSETS.make_directory(CANDIDATE_DIR)
    task = unreal.AssetImportTask()
    task.filename = str(fbx)
    task.destination_path = CANDIDATE_DIR
    task.destination_name = NAME
    task.automated = True
    task.replace_existing = False
    task.save = True
    task.options = options
    TOOLS.import_asset_tasks([task])
    imported = sorted(str(p) for p in task.imported_object_paths)
    mesh = ASSETS.load_asset(CANDIDATE)
    if not isinstance(mesh, unreal.SkeletalMesh):
        fail(f"{CANDIDATE} did not import as a skeletal mesh (imported {imported})")
    strays = [p for p in imported if p.split(".")[0] != CANDIDATE]
    outside = [p for p in strays if not p.startswith(CANDIDATE_DIR + "/")]
    if outside:
        fail(f"the import made assets outside {CANDIDATE_DIR}: {outside}")
    if mesh.get_editor_property("skeleton") != skeleton:
        fail("the candidate has another skeleton")
    names = sorted(str(n) for n in mesh.get_all_morph_target_names())
    if names != MORPHS or not mesh.has_vertex_colors():
        fail(f"the candidate's morphs read {names}, vertex colours {mesh.has_vertex_colors()}")
    slots = [str(s.get_editor_property("material_slot_name")) for s in mesh.get_editor_property("materials")]
    base_slots = [str(s.get_editor_property("material_slot_name")) for s in baseline.get_editor_property("materials")]
    if sorted(slots) != sorted(base_slots) or len(slots) != 23:
        fail(f"the candidate's slots {slots} are not the baseline's 23")
    if SKEL.get_lod_count(mesh) != 1:
        fail(f"the candidate imported {SKEL.get_lod_count(mesh)} LODs")
    # --- Sockets, from the baseline ---------------------------------------------------------------------------------
    require = [n for n in ("set_socket_parent",) if not hasattr(unreal.SkeletalMeshSocket, n)]
    if require or not hasattr(unreal.SkeletalMeshEditorSubsystem, "rename_socket"):
        fail(f"the socket API lacks {require or ['rename_socket']}")
    for name in SOCKETS:
        want = baseline.find_socket(name)
        if want is None:
            fail(f"the baseline has no socket {name}")
        socket = mesh.find_socket(name)
        if socket is None:
            socket = unreal.SkeletalMeshSocket(mesh)
            mesh.add_socket(socket, False)
            placeholder = socket.get_editor_property("socket_name")
            if not unreal.SkeletalMeshEditorSubsystem.rename_socket(mesh, placeholder, name):
                fail(f"cannot rename socket {placeholder} to {name}")
        socket.set_socket_parent(mesh, str(want.get_editor_property("bone_name")))
        for prop in ("relative_location", "relative_rotation", "relative_scale"):
            socket.set_editor_property(prop, want.get_editor_property(prop))
    # --- LOD0's build settings: s133's candidate's ------------------------------------------------------------------
    want_row = s133["candidate"]["lod_build_settings"][0]
    if any(want_row[k] != v for k, v in TANGENTS.items()) or want_row["recompute_normals"] is not False:
        fail(f"s133's LOD0 settings are not authored normals with explicit tangents: {want_row}")
    settings = unreal.SkeletalMeshEditorSubsystem.get_lod_build_settings(mesh, 0)
    imported_row = settings_row(mesh, 0)
    for key in FIELDS:
        settings.set_editor_property(key, want_row[key])
    unreal.SkeletalMeshEditorSubsystem.set_lod_build_settings(mesh, 0, settings)
    finish_compilation()
    if not ASSETS.save_loaded_asset(mesh):
        fail("the candidate did not save")
    mesh = unreal.load_asset(CANDIDATE)
    row = settings_row(mesh, 0)
    differences = [{"field": k, "s133": want_row[k], "candidate": row[k]} for k in FIELDS if row[k] != want_row[k]]
    if differences:
        fail(f"LOD0's settings read back otherwise than s133's: {differences}")
    sockets = {}
    for name in SOCKETS:
        got, want = socket_row(mesh, name), socket_row(baseline, name)
        if got is None or got["bone"] != want["bone"] or any(
                abs(a - b) > SOCKET_TOL for k in ("location_cm", "rotation_deg", "scale") for a, b in zip(got[k], want[k])):
            fail(f"socket {name} read back {got}, the baseline's {want}")
        sockets[name] = got
    # --- Export, for the host's normal check -----------------------------------------------------------------------
    options = unreal.FbxExportOption()
    for prop, value in (("level_of_detail", True), ("export_morph_targets", True), ("ascii", False),
                        ("collision", False), ("vertex_color", True)):
        options.set_editor_property(prop, value)
    export = unreal.AssetExportTask()
    export.object = mesh
    export.filename = str(export_path)
    export.automated = True
    export.prompt = False
    export.replace_identical = False
    export.exporter = unreal.SkeletalMeshExporterFBX()
    export.options = options
    export_path.parent.mkdir(parents=True, exist_ok=True)
    if not unreal.Exporter.run_asset_export_task(export) or not export_path.is_file():
        fail(f"Unreal did not export {export_path.name}")
    after = {"baseline": package_sha(BASELINE), "skeleton": package_sha(SKELETON), "s133": package_sha(S133)}
    if after["baseline"] != before or after["skeleton"] != skeleton_before or after["s133"] != s133_before:
        fail("a preserved package changed")
    readback = {
        "candidate": {"asset": CANDIDATE, "fbx": str(fbx.relative_to(ROOT)), "fbx_sha256": rec["candidate"]["sha256"],
                      "package_sha256": package_sha(CANDIDATE), "imported_objects": imported, "stray_imports": strays,
                      "skeleton": SKELETON, "morph_targets": names, "material_slots": slots,
                      "slots_in_baseline_order": slots == base_slots, "lod_count": SKEL.get_lod_count(mesh),
                      "lod0_vertices": SKEL.get_num_verts(mesh, 0), "lod_build_settings": [row],
                      "lod0_settings_as_imported": imported_row, "sockets": sockets},
        "baseline": {"asset": BASELINE, "package_sha256": before, "lod0_vertices": SKEL.get_num_verts(baseline, 0)},
        "s133": {"asset": S133, "package_sha256": s133_before,
                 "lod0_vertices": SKEL.get_num_verts(unreal.load_asset(S133), 0)},
        "skeleton_package_sha256": skeleton_before, "preserved_after": after, "tangents_required": TANGENTS,
        "export": {"file": str(export_path.relative_to(ROOT)), "sha256": sha256(export_path)},
        "inputs": {"assembly_record": hashlib.sha256(rec_bytes).hexdigest(), "fbx_check": sha256(check_path),
                   "baseline_inputs": sha256(ROOT / arg("--baseline-inputs")), "s133_readback": sha256(s133_path),
                   "scripts/unreal/import_nyaakoto_r4_candidate.py": sha256(__file__)}}
    with open(readback_path, "x", encoding="utf-8") as fh:
        json.dump(readback, fh, indent=1)
    print(MARKER, json.dumps({"lod0_vertices": readback["candidate"]["lod0_vertices"],
                              "slots_in_baseline_order": readback["candidate"]["slots_in_baseline_order"],
                              "export_sha256": readback["export"]["sha256"], "preserved": True}))


main()
