"""Matched views of the r4 repaired-paw candidate beside the s132 baseline and s133's authored-normal candidate.

Root's 21:53 UTC entry (2026-10-26) allows a separate candidate built once the UV and pad-contour checks justify it,
with matched views captured. The candidate is import_nyaakoto_r4_candidate.py's: the r4 paw skins (cut along the
pads' smooth contour, with the seamless periodic UVs), authored normals, and LOD0 only. s133's candidate differs from
the baseline only in its authored normals. So r4 against s133 isolates the paw surface, and r4 against the baseline
shows both changes.

**The views** are nine, all LOD0:
- s134's three: guard_front, paw_R_back_empty and cuff_R_outside;
- six more of the paws: R and L pads holding (guard), L back empty (guard), R and L pads empty (rest), and R pads
  holding (rest).

**Each view is shot three times in one level,** under one light and exposure: the baseline, then s133's candidate, then
r4. It is render_nyaakoto_normals_comparison.py's method:
- **The asset** is swapped on the same character (render_nyaakoto_tp_review.Character.use_mesh). The game's materials
  are bound again and gated on all 23 slots, and the clip and morphs are set again.
- **The pose, state and LOD** are s132's for that view, gated before and after each image.
- **The camera** is s132's own, replayed. Its rotation must read back within 0.001 deg of s132's.
- **The images** are 3840x2160, at s132's console variables and run-up.
- **The three packages** are checked by SHA-256 before anything is drawn:
  - the baseline against s132's manifest;
  - s133's candidate against its preparation's readback;
  - r4 against its import's readback.

Writes Saved/NyaakotoThirdPerson/Review/<out>/<view>__<variant>.png and manifest.json. The manifest records every file's
SHA-256, each variant's asset, packages and build settings, the replayed cameras, the gates, the console variables and
the light.

Run (lane holder, full editor):
  scripts/toolchain/run-editor-script.sh --editor scripts/unreal/render_nyaakoto_r4_comparison.py \\
      NYAAKOTO_R4_COMPARISON_COMPLETE <log> -- out=<new folder> \\
      s133=Saved/NyaakotoThirdPerson/Unreal/s133_authored_normals_readback.json r4=Saved/NyaakotoThirdPerson/Unreal/<import>.json

These are editor review originals, not an adoption. Whether the r4 paws are taken up is root's decision.
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
VIEWS = ("guard_front_LOD0", "paw_R_back_empty_LOD0", "cuff_R_outside_LOD0",
         "paw_R_pads_holding_LOD0", "paw_L_pads_holding_LOD0", "paw_L_back_empty_LOD0",
         "paw_R_pads_empty_rest_LOD0", "paw_L_pads_empty_rest_LOD0", "paw_R_pads_holding_rest_LOD0")
BASELINE_RUN = "Saved/NyaakotoThirdPerson/Review/s132/manifest.json"
S133 = "/Game/Generated/Candidates/AuthoredNormals/SK_NyaagyuSamurai_AuthoredNormals"
R4 = "/Game/Generated/Candidates/R4Paws/SK_NyaagyuSamurai_R4Paws"
VARIANTS = (("baseline", R.MESH_PATH), ("authored_normals", S133), ("r4_paws", R4))
MARKER = "NYAAKOTO_R4_COMPARISON_COMPLETE"
ROT_TOL_DEG = 1e-3
LOC_TOL_CM = 1e-3


def angle_diff(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def package_sha(asset_path):
    base = R.ROOT / "Content" / asset_path[len("/Game/"):]
    return {p.relative_to(R.ROOT).as_posix(): R.sha256(p) for p in sorted(base.parent.glob(base.name + ".*")) if p.is_file()}


def main():
    opts = {"out": "", "s133": "", "r4": "", "runup": "auto"}
    for a in sys.argv[1:]:
        if "=" in a:
            k, v = a.split("=", 1)
            opts[k] = v
    if not (opts["out"] and opts["s133"] and opts["r4"]):
        R.fail("out=<new folder>, s133=<its preparation's readback> and r4=<its import's readback> are required")
    out = R.ROOT / "Saved/NyaakotoThirdPerson/Review" / opts["out"]
    if out.exists():
        R.fail(f"{out} exists: originals go to a new folder")
    run_bytes = (R.ROOT / BASELINE_RUN).read_bytes()
    run = json.loads(run_bytes.decode("utf-8"))
    width, height = run["resolution"]
    s133_bytes = (R.ROOT / opts["s133"]).read_bytes()
    s133 = json.loads(s133_bytes.decode("utf-8"))
    r4_bytes = (R.ROOT / opts["r4"]).read_bytes()
    r4 = json.loads(r4_bytes.decode("utf-8"))
    # The three packages, before anything is drawn.
    for rel, digest in package_sha(R.MESH_PATH).items():
        if run["packages_sha256"].get(rel) != digest:
            R.fail(f"{rel} is not the package s132 drew")
    if s133["candidate"]["asset"] != S133 or package_sha(S133) != s133["candidate"]["package_sha256"]:
        R.fail("s133's candidate on disk is not the one its preparation read back")
    if r4["candidate"]["asset"] != R4 or package_sha(R4) != r4["candidate"]["package_sha256"]:
        R.fail("the r4 candidate on disk is not the one its import read back")
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
              "views": list(VIEWS), "variants_order": [v for v, _ in VARIANTS], "sun": R.SUN, "ev100": ev100,
              "exposure_bias": 1.0 - ev100, "floor": R.FLOOR, "highres_runup": runup,
              "inputs": {BASELINE_RUN: hashlib.sha256(run_bytes).hexdigest(),
                         opts["s133"]: hashlib.sha256(s133_bytes).hexdigest(), opts["r4"]: hashlib.sha256(r4_bytes).hexdigest(),
                         plan_path: hashlib.sha256(plan_bytes).hexdigest(),
                         "scripts/unreal/render_nyaakoto_r4_comparison.py": R.sha256(__file__),
                         "scripts/unreal/render_nyaakoto_tp_review.py": R.sha256(R.__file__),
                         "scripts/art/nyaakoto_tp_review_geometry.py": R.sha256(G.__file__)},
              "variants": {}, "shots": {}, "files": {},
              "scope": "editor review originals of the r4 repaired-paw candidate: not an adoption"}
    queue = [(view, variant, path) for view in VIEWS for variant, path in VARIANTS]
    status = {"frames": 0, "phase": "state", "count": 0}

    def write_manifest(name):
        record["cvars"] = {k: R.cvar(k) for k in R.CVARS}
        record["packages_sha256"] = {variant: package_sha(path) for variant, path in VARIANTS}
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
            finish(f"NYAAKOTO_R4_COMPARISON_FAILED: {exc!r}", error=True)

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
                record["variants"][variant] = {"asset": path, "lod_count": ch.lod_count,
                                               "lod_build_settings": ch.build_settings(),
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
            record["shots"][name] = {"view": view, "variant": variant,
                                     "state": {k: v for k, v in status["want"].items() if k != "stance"},
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
