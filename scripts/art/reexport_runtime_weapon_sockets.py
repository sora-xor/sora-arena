"""Re-export the runtime weapons' socketed LOD0 FBXs from their reviewed kit blends, in the socket convention
(fbx_socket_export.py), so UE 5.8 imports every SOCKET_ empty at scale 1 on its authored axes.

Run (Blender 5.2.2, by the holder of the engine/Blender lane):
  blender -b --factory-startup --python-exit-code 1 --python scripts/art/reexport_runtime_weapon_sockets.py
      -- --stage Saved/<dir> [--source-root <tree>] [--only W02_Kusarigama,...] [--files SM_Weapon_02.fbx,...]
  blender ... -- --apply --archive <dir> [--only ...]   (only with root's word, after the staged probe)

**Why.** Root's 0eb8c5e import of the drone, and fbx_unreal_sockets.py. screen_fbx_sockets.py predicts that all 83
sockets of the 26 socketed weapon FBXs import at scale 100, with their forward and up reversed and their right kept.
That is a prediction until probe_runtime_weapon_sockets.py reads real imports back.

**Scope.** Only LOD0 files that carry SOCKET_ empties are written.
- LOD1, LOD2, the blends, the maps, the library and the builders are not written.
- Nothing is rebuilt or rebaked, and no blend is saved.

**Modes:**
- **--stage** writes each corrected file to <dir>/<kit>/<file>, and <dir>/stage_report.json. The dir must be under
  this worktree's Saved/.
  - It writes nothing under Content/, so the kit records, the manifest and their digests stay as they are.
  - **--source-root** reads the kits from another tree instead, read-only. Root's reconciled W14 (3b0a662d) exists
    only in root's tree. Each report row names its tree, branch, HEAD and the kit's last commit, so provenance stays
    apart.
- **--apply** archives each original FBX and record under --archive, then writes the corrected file in place.
  - It amends the kit record (fbx_socket_export.amend_record).
  - In the runtime weapons manifest, it updates the entries of the files it rewrote and appends a scoped update.
  - It works only on this worktree, and refuses before writing if a record or the manifest would be reformatted.

**Checks, for every file, before anything is written outside the staging dir. It stops at the first failure.**
- **Inputs:**
  - the record's LOD0 and blend hashes match the files;
  - the LOD0 mesh is at the origin;
  - its SOCKET_ children are exactly the record's sockets, within 1e-5 m of the record.
- **The new file, through Interchange's rule (fbx_unreal_sockets.interchange):**
  - it is in Unreal's import axes and centimetres;
  - it holds exactly the mesh and its sockets, and no node is turned or scaled except by the sockets' own turns;
  - each socket is at scale 1 within 1e-6, on the blend's axes within 1e-5, and within 1e-3 cm of the record.
- **Against the original, array by array:**
  - the vertices are 100 x the original's, within 1e-6 cm;
  - every other geometry array, the material layer included, is equal within 1e-6;
  - Interchange's baked vertices are equal within 1e-4 cm.
- **Afterwards:** the kit's other LODs and its blend keep their hashes.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

passed = False


def fail_on_exit():
    if not passed:
        sys.stdout.flush()
        os._exit(1)


__import__("atexit").register(fail_on_exit)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fbx_socket_export as X  # noqa: E402
import fbx_unreal_sockets as F  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TOOL = "scripts/art/reexport_runtime_weapon_sockets.py"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


STAGE, APPLY = opt("--stage"), "--apply" in argv
assert bool(STAGE) != APPLY, "give exactly one of --stage <dir> and --apply"
SRC = Path(opt("--source-root", str(ROOT))).resolve()
if STAGE:
    STAGE = (ROOT / STAGE).resolve() if not Path(STAGE).is_absolute() else Path(STAGE).resolve()
    assert STAGE.is_relative_to(ROOT / "Saved"), "the staging dir must be under this worktree's Saved/"
ARCHIVE = Path(opt("--archive")).resolve() if APPLY else None
assert not APPLY or (ARCHIVE and ARCHIVE.is_relative_to(ROOT / "Saved")), "--apply needs an --archive under Saved/"
assert not APPLY or SRC == ROOT, "--apply works only on this worktree"
RUNTIME = SRC / "Content/SourceArt/Weapons/Runtime"
ONLY = set(opt("--only", "").split(",")) - {""}
FILES = set(opt("--files", "").split(",")) - {""}


def git(*args):
    return subprocess.run(["git", "-C", str(SRC), *args], capture_output=True, text=True, check=True).stdout.strip()


def read_json_exactly(path):
    """A record or manifest, refused unless rewriting it changes only what is amended (indent 1, UTF-8)."""
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    assert json.dumps(data, ensure_ascii=False, indent=1) + "\n" == text, f"{path} would be reformatted"
    return data


def work():
    """(kit dir, record, [(asset, LOD0 file, its sockets)]) for every kit asset whose LOD0 carries sockets."""
    out = []
    for rec_path in sorted(RUNTIME.glob("W*/build_record.json")):
        kit = rec_path.parent
        if ONLY and kit.name not in ONLY:
            continue
        record = json.loads(rec_path.read_text(encoding="utf-8"))
        assets = [(a, e["lods"][0]["file"], e["sockets"]) for a, e in record["assets"].items()
                  if e.get("sockets") and (not FILES or Path(e["lods"][0]["file"]).name in FILES)]
        if assets:
            out.append((kit, record, assets))
    missing = (ONLY - {k.name for k, _r, _a in out}) | (FILES - {Path(f).name for _k, _r, a in out for _x, f, _s in a})
    assert not missing, f"not found as socketed kit LOD0s: {sorted(missing)}"
    return out


def socket_rows(sockets):
    return {n: {"position_cm": s["position_cm"].round(5).tolist(), "scale": s["scale"].round(7).tolist(),
                "forward": s["x"].round(7).tolist(), "right": s["y"].round(7).tolist(), "up": s["z"].round(7).tolist()}
            for n, s in sockets.items()}


def check_unreal(path, asset, sockets, axes):
    """The rewritten file through Interchange's rule; returns Unreal's sockets as rows, and the baked vertices."""
    scene = F.read_fbx(path)
    assert scene["axes"] == F.UNREAL_IMPORT_AXES and scene["unit"] == 1.0, (path, scene["axes"], scene["unit"])
    assert set(scene["nodes"]) == {asset} | {f"SOCKET_{s}" for s in sockets}, (path, sorted(scene["nodes"]))
    for name, node in scene["nodes"].items():
        assert name.startswith("SOCKET_") or np.abs(np.array(node["R"])).max() < 1e-6, (path, name, node["R"])
        assert np.abs(np.array(node["S"]) - 1.0).max() < 1e-6, (path, name, node["S"])
    result = F.interchange(scene)
    for name, s in result["sockets"].items():
        assert np.abs(s["scale"] - 1.0).max() < 1e-6, (path, name, s["scale"].tolist())
        assert np.abs(s["x"] - F.to_unreal_axis(axes[name]["x"])).max() < 1e-5, (path, name, s["x"].tolist())
        assert np.abs(s["z"] - F.to_unreal_axis(axes[name]["z"])).max() < 1e-5, (path, name, s["z"].tolist())
        assert np.abs(s["position_cm"] - F.to_unreal(sockets[name])).max() < 1e-3, (path, name, s["position_cm"].tolist())
    return socket_rows(result["sockets"]), result["vertices"][asset]


def check_same_geometry(original, new, asset, baked_new):
    """Array by array against the original LOD0; returns the worst difference of each array."""
    old_arrays, new_arrays = F.geometry_arrays(original)[asset], F.geometry_arrays(new)[asset]
    assert set(old_arrays) == set(new_arrays), (asset, sorted(set(old_arrays) ^ set(new_arrays)))
    worst = {}
    for key in sorted(old_arrays):
        a, b = old_arrays[key].astype(float), new_arrays[key].astype(float)
        assert a.shape == b.shape, (asset, key, a.shape, b.shape)
        worst[key] = float(np.abs((a * 100.0 if key == "Vertices" else a) - b).max()) if a.size else 0.0
        assert worst[key] <= 1e-6, (asset, key, worst[key])
    baked_old = F.interchange(F.read_fbx(original))["vertices"][asset]
    worst["interchange_vertices_cm"] = float(np.abs(baked_old - baked_new).max())
    assert worst["interchange_vertices_cm"] <= 1e-4, (asset, worst["interchange_vertices_cm"])
    return {k: float(f"{v:.3g}") for k, v in worst.items()}


def unhide(objs):
    """In memory only (the blend is never saved): the exporter takes context.selected_objects, which skips hidden
    objects."""
    layer = bpy.context.view_layer.objects
    for o in objs:
        assert o.name in layer, f"{o.name} is not in the view layer"
        o.hide_set(False)
        o.hide_viewport = False


rows, rewritten = [], {}
JOBS = work()
if APPLY:                          # refuse before any file is written in place
    read_json_exactly(RUNTIME / "manifest.json")
    for kit, _record, _assets in JOBS:
        read_json_exactly(kit / "build_record.json")
tree = {"root": str(SRC), "branch": git("branch", "--show-current"), "head": git("rev-parse", "HEAD"),
        "clean_kits": git("status", "--porcelain", "--", "Content/SourceArt/Weapons/Runtime") == ""}
for kit, record, assets in JOBS:
    inputs = [(record["assets"][a]["lods"][0]["file"], record["assets"][a]["lods"][0]["sha256"]) for a, _f, _s in assets]
    inputs.append((record["blend"]["file"], record["blend"]["sha256"]))
    for f, h in inputs:
        assert X.sha256(SRC / f) == h, f"the record and the file differ: {SRC / f}"
    others = {l["file"]: l["sha256"] for e in record["assets"].values() for l in e["lods"]
              if l["file"] not in {f for _a, f, _s in assets}}
    provenance = {**tree, "kit_last_commit": git("log", "-1", "--format=%H %s", "--", str(kit.relative_to(SRC)))}
    bpy.ops.wm.open_mainfile(filepath=str(SRC / record["blend"]["file"]), load_ui=False)
    for asset, file, sockets in assets:
        mesh = bpy.data.objects[asset]
        assert mesh.type == "MESH", asset
        ident = np.abs(np.array(mesh.matrix_world) - np.eye(4)).max()
        assert ident < 1e-9, f"{asset} is not at the origin ({ident})"
        empties = sorted((o for o in bpy.data.objects if o.parent == mesh and o.name.startswith("SOCKET_")),
                         key=lambda o: o.name)
        assert [o.type for o in empties] == ["EMPTY"] * len(empties), asset
        assert {o.name[len("SOCKET_"):] for o in empties} == set(sockets), (asset, [o.name for o in empties], sorted(sockets))
        for o in empties:
            got = o.matrix_basis.translation
            assert (got - Vector(sockets[o.name[len("SOCKET_"):]])).length < 1e-5, (asset, o.name, tuple(got))
        axes = X.socket_axes(empties)
        original = SRC / file
        out = STAGE / kit.name / original.name if STAGE else original
        if APPLY:
            (ARCHIVE / kit.name).mkdir(parents=True, exist_ok=True)
            kept = ARCHIVE / kit.name / original.name
            assert not kept.exists(), f"the archive already holds {kept}"
            shutil.copy2(original, kept)
            original = kept
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            assert not out.exists(), f"the staging dir already holds {out}"
        unhide([mesh, *empties])
        X.export(out, mesh, empties)
        unreal, baked = check_unreal(out, asset, sockets, axes)
        same = check_same_geometry(original, out, asset, baked)
        rows.append({"kit": kit.name, "asset": asset, "file": file, "original_path": str(original),
                     "original_sha256": X.sha256(original), "new_path": str(out), "new_sha256": X.sha256(out),
                     "provenance": provenance, "socket_axes": axes, "record_sockets": sockets,
                     "sockets_in_unreal": unreal,
                     "predicted_original": socket_rows(F.interchange(F.read_fbx(original))["sockets"]),
                     "same_geometry": same})
        rewritten.setdefault(kit, {})[asset] = (file, X.sha256(out), X.sha256(original), axes)
        print("WEAPON_SOCKETS_REEXPORTED " + json.dumps(rows[-1]), flush=True)
    for f, h in others.items():
        assert X.sha256(SRC / f) == h, f"changed by the re-export: {f}"
    assert X.sha256(SRC / record["blend"]["file"]) == record["blend"]["sha256"], "the blend changed"

stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
report = {"tool": TOOL, "tool_sha256": X.sha256(ROOT / TOOL), "convention": X.SOCKET_FBX,
          "module_sha256": {p: X.sha256(ROOT / p) for p in ("scripts/art/fbx_socket_export.py",
                                                          "scripts/art/fbx_unreal_sockets.py")},
          "blender": bpy.app.version_string, "mode": "apply" if APPLY else "stage", "recorded_at_utc": stamp,
          "source": tree, "files": rows}
if STAGE:
    (STAGE / "stage_report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
else:
    manifest_path = RUNTIME / "manifest.json"
    shutil.copy2(manifest_path, ARCHIVE / "manifest.json")
    manifest = read_json_exactly(manifest_path)
    listed = {e["file"]: e for e in manifest.get("files", [])}
    changed = []
    for kit, assets in rewritten.items():
        rec_path = kit / "build_record.json"
        shutil.copy2(rec_path, ARCHIVE / kit.name / "build_record.json")
        record = read_json_exactly(rec_path)
        amended = X.amend_record(record, {a: v[:3] for a, v in assets.items()}, {a: v[3] for a, v in assets.items()}, TOOL)
        rec_path.write_text(json.dumps(amended, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        for f in [v[0] for v in assets.values()] + [str(rec_path.relative_to(ROOT))]:
            entry = {"file": f, "bytes": (ROOT / f).stat().st_size, "sha256": X.sha256(ROOT / f)}
            if f in listed:
                listed[f].update(entry)
            changed.append(entry)
    manifest.setdefault("scoped_updates", []).append(
        {"key": "socket_fbx", "recorded_at_utc": stamp, "scope": "the socketed LOD0 FBXs listed here, re-exported from "
         "their reviewed blends in the socket convention, and their kit records. Nothing rebuilt or rebaked",
         "generators": [{"path": p, "sha256": X.sha256(ROOT / p)} for p in
                        (TOOL, "scripts/art/fbx_socket_export.py", "scripts/art/fbx_unreal_sockets.py")],
         "files": changed})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (ARCHIVE / "apply_report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
print("WEAPON_SOCKETS_DONE " + json.dumps({"mode": report["mode"], "source": str(SRC), "files": len(rows),
                                           "sockets": sum(len(r["sockets_in_unreal"]) for r in rows)}))
passed = True
