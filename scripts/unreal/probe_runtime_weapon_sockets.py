"""Import runtime weapon FBXs with root's weapon import options, unsaved, and read their sockets back.

It reads each original kit file and, when staged, its corrected re-export. It is the UE 5.8 evidence for
docs/art-direction/WEAPON_SOCKET_EXPORT_PLAN.md.

Run (UE 5.8, headless, by the holder of the shared engine lane):
  scripts/toolchain/run-editor-script.sh scripts/unreal/probe_runtime_weapon_sockets.py
      RUNTIME_WEAPON_SOCKET_PROBE_DONE <log> -- out=<json> stage=<stage_report.json>[,<stage_report.json>...]
      [controls=Saved/WeaponSocketFix/s82_diag]
  ... -- out=<json> readonly=/Game/Generated/Meshes/SM_Weapon_02,/Game/Generated/Meshes/SM_Weapon_15
      (reads assets that already exist, and imports nothing)

**Import mode.** For every file in the stage reports (scripts/art/reexport_runtime_weapon_sockets.py --stage), it
imports two files into /Game/ArtLaneProbes/WeaponSockets/{original,corrected}/<asset>, with task.save False:
- the original kit LOD0, hash-checked against the report, from whichever tree the report names;
- the staged corrected file.

**The options** are those import_original_assets.py uses for SM_Weapon_XX, root's runtime weapon import: FbxImportUI
as a static mesh, import_materials True, import_textures False, combine_meshes True, no lightmap UVs, and
auto_generate_collision False. Weapons carry no UCX hulls.

**The readback:**
- each socket as SoraViewmodelComponent reads it: FindSocket's relative location, scale and rotation, with the
  rotation's forward, right and up vectors;
- LOD0's render sections: positions, triangles, normals, UVs and tangents;
- the material slots;
- the convex and other simple collision counts.

**Gates** (weapon_socket_gates.py):
- the corrected file must pass socket_failures: positions, unit scale, and signed forward, right and up;
- the corrected import must repeat the original's LOD0 arrays, material slots and collision counts (same_import);
- both files must follow fbx_unreal_sockets' prediction on every axis (model_agreement). That tests the model beyond
  the drone it was calibrated on, before its screen of the other files is trusted.

**controls=** names a diagnose_weapon_socket_reexport.py output. Each asset's control is the library's convention
re-exported from the same blend, so it carries the original's inexact node turn. It is imported as a third file,
hash-checked against the diagnosis. Its comparisons with the original and with the corrected file are recorded,
not gated: they attribute any difference between the original and corrected imports.

The original is expected to fail the socket gates, and that is recorded, not raised. The report stores counts,
bounds and gaps, not the arrays.
Asset readback only: not a render, a capture or a gameplay admission.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402
import weapon_socket_gates as G  # noqa: E402

require_running_engine("Runtime weapon socket probe")
OPTS = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
ROOT = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/ArtLaneProbes/WeaponSockets"
OPTIONS = {"source": "scripts/unreal/import_original_assets.py (SM_Weapon_XX)", "import_materials": True,
           "import_textures": False, "combine_meshes": True, "generate_lightmap_u_vs": False,
           "auto_generate_collision": False, "save": False}
meshes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def fail(message):
    raise RuntimeError("Runtime weapon socket probe: " + message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve(p):
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def options():
    ui = unreal.FbxImportUI()
    ui.import_mesh = True
    ui.import_materials = OPTIONS["import_materials"]
    ui.import_textures = OPTIONS["import_textures"]
    ui.import_as_skeletal = False
    ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    data = ui.static_mesh_import_data
    data.combine_meshes = OPTIONS["combine_meshes"]
    data.generate_lightmap_u_vs = OPTIONS["generate_lightmap_u_vs"]
    data.auto_generate_collision = OPTIONS["auto_generate_collision"]
    return ui


def import_one(tag, asset, fbx):
    task = unreal.AssetImportTask()
    task.filename = str(fbx)
    task.destination_path = f"{DEST}/{tag}"
    task.destination_name = asset
    task.automated = True
    task.replace_existing = True
    task.save = OPTIONS["save"]
    task.options = options()
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.EditorAssetLibrary.load_asset(f"{DEST}/{tag}/{asset}")
    if not isinstance(mesh, unreal.StaticMesh):
        fail(f"{tag} {asset} did not import as a static mesh")
    return mesh


def vec(v):
    return [v.x, v.y, v.z]


def read_sockets(mesh):
    """Every socket as SoraViewmodelComponent reads it: relative location, scale and rotation."""
    probe = unreal.StaticMeshComponent()
    if not probe.set_static_mesh(mesh):
        fail("the socket probe could not bind " + mesh.get_path_name())
    out = {}
    for socket_name in probe.get_all_socket_names():
        socket = mesh.find_socket(socket_name)
        r = socket.get_editor_property("relative_rotation")
        out[str(socket_name)] = {"position": vec(socket.get_editor_property("relative_location")),
                                 "scale": vec(socket.get_editor_property("relative_scale")),
                                 "forward": vec(unreal.MathLibrary.get_forward_vector(r)),
                                 "right": vec(unreal.MathLibrary.get_right_vector(r)),
                                 "up": vec(unreal.MathLibrary.get_up_vector(r)),
                                 "rotation_pyr": [r.pitch, r.yaw, r.roll]}
    return out


def read_mesh(mesh):
    """LOD0's render sections, the material slots and the collision counts."""
    sections = []
    for section in range(mesh.get_num_sections(0)):
        positions, indices, normals, uvs, tangents = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, section)
        sections.append({"positions": [vec(p) for p in positions], "indices": list(indices),
                         "normals": [vec(n) for n in normals], "uvs": [[t.x, t.y] for t in uvs],
                         "tangents": [vec(t.get_editor_property("tangent_x")) for t in tangents]})
    pts = [p for s in sections for p in s["positions"]]
    if not pts:
        fail("empty LOD0 render data: " + mesh.get_path_name())
    materials = [[str(m.get_editor_property("material_slot_name")), str(m.get_editor_property("imported_material_slot_name")),
                  m.get_editor_property("material_interface").get_name() if m.get_editor_property("material_interface") else None]
                 for m in mesh.get_editor_property("static_materials")]
    return {"lod0": {"sections": sections}, "materials": materials,
            "collision": {"convex": meshes.get_convex_collision_count(mesh), "other_simple": meshes.get_simple_collision_count(mesh)},
            "summary": {"lods": meshes.get_lod_count(mesh), "triangles": mesh.get_num_triangles(0), "vertices": len(pts),
                        "sections": len(sections), "min_cm": [min(p[a] for p in pts) for a in range(3)],
                        "max_cm": [max(p[a] for p in pts) for a in range(3)]}}


report = {"engine": unreal.SystemLibrary.get_engine_version(), "probe_sha256": sha(__file__),
          "gates_sha256": sha(Path(__file__).resolve().parent / "weapon_socket_gates.py"), "options": OPTIONS,
          "saved_packages": False}
problems = []
controls = {}
if "controls" in OPTS:
    control_dir = resolve(OPTS["controls"])
    diagnosis = json.loads((control_dir / "diagnosis.json").read_text(encoding="utf-8"))
    report["controls"] = {"dir": str(control_dir), "diagnosis_sha256": sha(control_dir / "diagnosis.json")}
    for d in diagnosis["rows"]:
        if "asset" in d:
            controls[d["asset"]] = (control_dir / d["kit"] / "control" / f"{d['asset']}.fbx", d["control_sha256"])
if "stage" in OPTS:
    report["stage_reports"], report["imports"] = [], {}
    for stage_path in (resolve(p) for p in OPTS["stage"].split(",")):
        stage = json.loads(stage_path.read_text(encoding="utf-8"))
        report["stage_reports"].append({"file": str(stage_path), "sha256": sha(stage_path), "source": stage["source"]})
        for f in stage["files"]:
            original, corrected = resolve(f["original_path"]), resolve(f["new_path"])
            if sha(original) != f["original_sha256"] or sha(corrected) != f["new_sha256"]:
                fail(f"{f['asset']}: a file changed since staging")
            if f["asset"] in report["imports"]:
                fail(f"{f['asset']} is staged twice")
            main = re.fullmatch(r"SM_Weapon_\d\d", f["asset"]) is not None
            row, read = {"kit": f["kit"], "provenance": f["provenance"]}, {}
            for tag, path, predicted in (("original", original, f["predicted_original"]),
                                         ("corrected", corrected, f["sockets_in_unreal"])):
                mesh = import_one(tag, f["asset"], path)
                sockets = read_sockets(mesh)
                read[tag] = read_mesh(mesh)
                agreement = G.model_agreement(sockets, predicted)
                row[tag] = {"fbx": str(path), "sha256": sha(path), "sockets": sockets, "mesh": read[tag]["summary"],
                            "materials": read[tag]["materials"], "collision": read[tag]["collision"],
                            "gate_failures": G.socket_failures(sockets, f["record_sockets"], f["socket_axes"], main),
                            "model_agreement": agreement, "model_agrees": G.agrees(agreement)}
                if not row[tag]["model_agrees"]:
                    problems.append(f"{f['asset']} {tag}: the import departs from the model {agreement}")
            row["same_import_gaps"], same_failures = G.same_import(read["original"], read["corrected"])
            row["same_import_failures"] = same_failures
            if f["asset"] in controls:
                path, digest = controls[f["asset"]]
                if sha(path) != digest:
                    fail(f"{f['asset']}: the control changed since the diagnosis")
                read["control"] = read_mesh(import_one("control", f["asset"], path))
                row["control"] = {"fbx": str(path), "sha256": digest, "mesh": read["control"]["summary"]}
                for label, x, y in (("original_vs_control", "original", "control"),
                                    ("control_vs_corrected", "control", "corrected")):
                    gaps, failures = G.same_import(read[x], read[y])
                    row[label] = {"gaps": gaps, "failures": failures}
            if row["corrected"]["gate_failures"]:
                problems.append(f"{f['asset']} corrected: " + "; ".join(row["corrected"]["gate_failures"]))
            if same_failures:
                problems.append(f"{f['asset']}: the corrected import differs: " + "; ".join(same_failures))
            report["imports"][f["asset"]] = row
            unreal.log(f"RUNTIME_WEAPON_SOCKET_PROBE {f['asset']}: " + json.dumps(row, sort_keys=True))
if "readonly" in OPTS:
    report["readonly"] = {}
    for path in OPTS["readonly"].split(","):
        mesh = unreal.EditorAssetLibrary.load_asset(path)
        report["readonly"][path] = read_sockets(mesh) if isinstance(mesh, unreal.StaticMesh) else "not a static mesh"
        unreal.log(f"RUNTIME_WEAPON_SOCKET_PROBE readonly {path}: " + json.dumps(report["readonly"][path], sort_keys=True))
if "imports" not in report and "readonly" not in report:
    fail("give stage=<stage_report.json> or readonly=<asset paths>")
report["problems"] = problems
out = resolve(OPTS["out"])
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "x", encoding="utf-8") as fh:
    fh.write(json.dumps(report, indent=1) + "\n")
if problems:
    fail("; ".join(problems))
unreal.log("RUNTIME_WEAPON_SOCKET_PROBE_DONE " + json.dumps(
    {"imports": sorted(report.get("imports", {})), "readonly": sorted(report.get("readonly", {})), "out": str(out)}))
