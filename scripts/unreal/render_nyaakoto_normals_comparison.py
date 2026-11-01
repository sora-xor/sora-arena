"""Root's controlled authored-normal comparison: the s132 baseline against its authored-normal candidate, in three views.

Root (2026-10-26) asked for an identical mesh source, pose, material, camera and light, with recompute normals disabled
on a separate candidate (prepare_nyaakoto_authored_normals.py) and the s132 baseline preserved. The views are three:
guard_front_LOD0, paw_R_back_empty_LOD0 and cuff_R_outside_LOD0.

Each view is shot twice in one level, under one light and exposure, the baseline first, then the candidate:
- **The asset** is swapped on the same character: render_nyaakoto_tp_review.Character.use_mesh. The game's materials
  are bound again and gated on all 23 slots, and the clip and morphs are set again.
- **The pose, state and LOD** are s132's for that view, gated before and after each image, as the review gates them.
- **The camera** is s132's own, replayed: its recorded location, the point it looked at, and its field of view. Its
  rotation must read back within 0.001 deg of s132's.
- **The images** are 3840x2160, at the same console variables and run-up as s132.
- **Both packages** are checked by SHA-256 before anything is drawn: the baseline against s132's manifest, the candidate
  against the preparation's readback.

Writes Saved/NyaakotoThirdPerson/Review/<out>/<view>__baseline.png and <view>__authored_normals.png, and manifest.json.
The manifest records every file's SHA-256, both variants' assets, packages and build settings, the replayed cameras,
the gates, the console variables and the light. compare the images on the host with
check_nyaakoto_normals_comparison.py.

Run (lane holder, full editor):
  scripts/toolchain/run-editor-script.sh --editor scripts/unreal/render_nyaakoto_normals_comparison.py \\
      NYAAKOTO_NORMALS_COMPARISON_COMPLETE <log> -- out=<new folder> readback=Saved/NyaakotoThirdPerson/Unreal/<prep>.json

Editor review originals, not an adoption: whether to import authored normals is root's decision.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_nyaakoto_tp_review as R  # noqa: E402  (its capture runs only as __main__)

G = R.G
VIEWS = ("guard_front_LOD0", "paw_R_back_empty_LOD0", "cuff_R_outside_LOD0")
BASELINE_RUN = "Saved/NyaakotoThirdPerson/Review/s132/manifest.json"
CANDIDATE = "/Game/Generated/Candidates/AuthoredNormals/SK_NyaagyuSamurai_AuthoredNormals"
VARIANTS = (("baseline", R.MESH_PATH), ("authored_normals", CANDIDATE))
MARKER = "NYAAKOTO_NORMALS_COMPARISON_COMPLETE"
ROT_TOL_DEG = 1e-3
LOC_TOL_CM = 1e-3


def angle_diff(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def package_sha(asset_path):
    base = R.ROOT / "Content" / asset_path[len("/Game/"):]
    return {p.relative_to(R.ROOT).as_posix(): R.sha256(p) for p in sorted(base.parent.glob(base.name + ".*")) if p.is_file()}


def main():
    opts = {"out": "", "readback": "", "runup": "auto"}
    for a in sys.argv[1:]:
        if "=" in a:
            k, v = a.split("=", 1)
            opts[k] = v
    if not opts["out"] or not opts["readback"]:
        R.fail("out=<new folder> and readback=<the preparation's readback .json> are required")
    out = R.ROOT / "Saved/NyaakotoThirdPerson/Review" / opts["out"]
    if out.exists():
        R.fail(f"{out} exists: originals go to a new folder")
    run_bytes = (R.ROOT / BASELINE_RUN).read_bytes()
    run = json.loads(run_bytes.decode("utf-8"))
    width, height = run["resolution"]
    prep_bytes = (R.ROOT / opts["readback"]).read_bytes()
    prep = json.loads(prep_bytes.decode("utf-8"))
    # Both packages, before anything is drawn.
    base_now = package_sha(R.MESH_PATH)
    for rel, digest in base_now.items():
        if run["packages_sha256"].get(rel) != digest:
            R.fail(f"{rel} is not the package s132 drew")
    cand_now = package_sha(CANDIDATE)
    if prep["candidate"]["asset"] != CANDIDATE or cand_now != prep["candidate"]["package_sha256"]:
        R.fail("the candidate on disk is not the one the preparation read back")
    plan_path = next(k for k in run["inputs"] if k.endswith(".json") and "review_plan" in k)
    plan_bytes = (R.ROOT / plan_path).read_bytes()
    if hashlib.sha256(plan_bytes).hexdigest() != run["inputs"][plan_path]:
        R.fail(f"{plan_path} is not the plan s132 used")
    plan = json.loads(plan_bytes.decode("utf-8"))
    views = {name: run["shots"][name] for name in VIEWS}
    out.mkdir(parents=True)
    R.build_level()
    runup = R.highres_runup(opts["runup"])
    ev100 = R.metered_ev100()
    R.exposure(ev100)
    unreal.SystemLibrary.execute_console_command(R.world(), "Editor.AsyncAssetCompilationFinishAll")
    ch = R.Character(plan)
    unreal.SystemLibrary.execute_console_command(R.world(), "Editor.AsyncAssetCompilationFinishAll")
    record = {"level": R.LEVEL, "engine": unreal.SystemLibrary.get_engine_version(), "resolution": [width, height],
              "views": list(VIEWS), "sun": R.SUN, "ev100": ev100, "exposure_bias": 1.0 - ev100, "floor": R.FLOOR,
              "highres_runup": runup,
              "inputs": {BASELINE_RUN: hashlib.sha256(run_bytes).hexdigest(), opts["readback"]: hashlib.sha256(prep_bytes).hexdigest(),
                         plan_path: hashlib.sha256(plan_bytes).hexdigest(),
                         "scripts/unreal/render_nyaakoto_normals_comparison.py": R.sha256(__file__),
                         "scripts/unreal/render_nyaakoto_tp_review.py": R.sha256(R.__file__),
                         "scripts/art/nyaakoto_tp_review_geometry.py": R.sha256(G.__file__)},
              "variants": {}, "shots": {}, "files": {},
              "scope": "editor review originals for root's authored-normal comparison: not an adoption"}
    queue = [(view, variant, path) for view in VIEWS for variant, path in VARIANTS]
    status = {"frames": 0, "phase": "state", "count": 0}

    def write_manifest(name):
        record["cvars"] = {k: R.cvar(k) for k in R.CVARS}
        record["packages_sha256"] = {"baseline": package_sha(R.MESH_PATH), "authored_normals": package_sha(CANDIDATE)}
        (out / name).write_text(json.dumps(record, indent=1) + "\n")

    def finish(message, error=False):
        unreal.unregister_slate_post_tick_callback(handle)
        (unreal.log_error if error else unreal.log)(message)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)

    def tick(delta):
        try:
            step()
        except Exception as exc:  # never spin on a failing callback
            try:
                write_manifest("manifest.partial.json")
            except Exception:
                pass
            finish(f"NYAAKOTO_NORMALS_COMPARISON_FAILED: {exc!r}", error=True)

    def step():
        status["frames"] += 1
        R.LEVELS.editor_invalidate_viewports()
        if status["frames"] < 30:
            return
        if status["phase"] == "state":
            if not queue:
                write_manifest("manifest.json")
                finish(f"{MARKER}: {len(record['files'])} captures in {out}")
                return
            view, variant, path = queue[0]
            if ch.mesh.get_path_name().split(".")[0] != path:
                ch.use_mesh(path)
            if variant not in record["variants"]:
                record["variants"][variant] = {"asset": path, "lod_build_settings": ch.build_settings(),
                                               "materials": ch.check_materials(f"{variant} bound")}
            shot = views[view]["shot"]
            status.update(view=view, variant=variant, want=ch.set_state(shot["pose"], shot["state"], shot["lod"]),
                          phase="settle", count=0)
            return
        view, variant = status["view"], status["variant"]
        name = f"{view}__{variant}"
        if status["phase"] == "settle":
            status["count"] += 1
            if status["count"] < 20:
                return
            gates = ch.check_state(status["want"])
            ch.check_materials(f"before {name}")
            cam_rec = views[view]["camera"]
            cam, got = R.spawn_camera(tuple(cam_rec["location_cm"]), tuple(cam_rec["target_cm"]),
                                      cam_rec["field_of_view_deg"], width, height)
            drift = {"location_cm": max(abs(a - b) for a, b in zip(got["location_cm"], cam_rec["location_cm"])),
                     "rotation_deg": max(angle_diff(a, b) for a, b in zip(got["rotation_deg"], cam_rec["rotation_deg"]))}
            if drift["location_cm"] > LOC_TOL_CM or drift["rotation_deg"] > ROT_TOL_DEG:
                R.fail(f"{name}: the replayed camera is {drift} from s132's")
            record["shots"][name] = {"view": view, "variant": variant, "state": {k: v for k, v in status["want"].items() if k != "stance"},
                                     "gates": gates, "camera": got, "camera_from_s132": cam_rec, "camera_drift": drift}
            R.LEVELS.pilot_level_actor(cam)
            R.LEVELS.editor_set_game_view(True)
            status.update(phase="light", count=0, cam=cam)
            return
        if status["phase"] == "light":
            status["count"] += 1
            if status["count"] < (R.FIRST_SETTLE if not record["files"] else R.SETTLE):
                return
            path = out / f"{name}.png"
            status.update(phase="shot", path=path, started=time.time(), count=0)
            unreal.SystemLibrary.execute_console_command(R.world(), f'HighResShot {width}x{height} filename="{path}"')
            return
        if status["phase"] == "shot":
            p = status["path"]
            if not p.is_file() or p.stat().st_mtime < status["started"]:
                status["count"] += 1
                if status["count"] > 6000:
                    R.fail(f"{p} was not written")
                return
            record["files"][p.name] = R.sha256(p)
            record["shots"][name]["gates_after"] = ch.check_state(status["want"])
            R.ACTORS.destroy_actor(status["cam"])
            queue.pop(0)
            status["phase"] = "state"

    handle = unreal.register_slate_post_tick_callback(tick)
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)


if __name__ == "__main__":
    main()
