"""The first-person paw's fur cost in Unreal: material statistics, and GPU time with the shells drawn and not.

Run (UE 5.8, the full editor offscreen, by the holder of the shared engine lane), after import_nyaakoto_fp_paws.py:
  scripts/toolchain/run-editor-script.sh --editor scripts/unreal/measure_fp_fur_cost.py FP_FUR_COST_COMPLETE <log> \
      -- out=Saved/NyaakotoFPPaws/Cost/<name>.json [holds=right_cheek_clear,paw] [frames=120]

Root's review of capture v7: the shells' 1,781-instruction material over ten translucent layers "needs measured
performance before acceptance".

**Material statistics** (MaterialEditingLibrary.get_statistics, for the running shader platform):
- every paw material as imported;
- transient copies of M_NyaakotoFP_FurShells under each other translucency lighting mode. Each is compiled, read
  and deleted, so the forward shading's share of the instructions shows.

**GPU time** is measured in render_yumi_fp_review's own scene: its level, sun, exposure, rig, poses and cameras,
imported from it. Per hold, three states:
- shells: the paw as imported;
- shells_clear: the shells' slot drawn by a translucent unlit material of opacity 0, so the shells still rasterise
  and blend but are not shaded;
- no_paw: the paw hidden.

Each state settles for SETTLE frames. Then the CSV profiler records `frames` frames with r.GPUCsvStatsEnabled 1.
The CSV is read back, and per column whose name holds "GPU", and for the thread and frame times, the run reports
the median and quartiles. csv_summary does that reading and runs without the engine.

**The viewport:** the CSV frames are the editor viewport's own, not a HighResShot's. Its size is read once per hold
from a HighResShot at multiplier 1 (the viewport's size, PNG header) and recorded, so the times are at that size.
scripts/art/fp_fur_overdraw.py counts the shells' fragments per hold at a capture's size.

After each hold the paw's slots are gated again (fp_material_bindings), as the capture gates them after its ID pass.
The JSON is written exclusively. This is measurement only: not a render for review, an admission or a performance
acceptance.
"""
from __future__ import annotations

import csv
import gzip
import importlib.util
import io
import json
import statistics
import struct
import sys
import time
from pathlib import Path

STATES = ("shells", "shells_clear", "no_paw")
SHELL_SLOT = "M_NyaakotoFP_FurShells"
PAW_MATERIALS = ("M_NyaakotoFP_FurSkin", "M_NyaakotoFP_PawPad", SHELL_SLOT, "M_NyaakotoFP_FurCards",
                 "M_NyaakotoFP_KoteSilk", "M_NyaakotoFP_KoteUrushi", "M_NyaakotoFP_CordVermilion",
                 "M_NyaakotoFP_MonGold")
LIGHTING_MODES = ("TLM_VOLUMETRIC_NON_DIRECTIONAL", "TLM_VOLUMETRIC_DIRECTIONAL", "TLM_SURFACE",
                  "TLM_VOLUMETRIC_PER_VERTEX_NON_DIRECTIONAL")
STAT_NAMES = ("num_vertex_shader_instructions", "num_pixel_shader_instructions", "num_samplers",
              "num_vertex_texture_samples", "num_pixel_texture_samples", "num_virtual_texture_samples",
              "num_uv_scalars", "num_interpolator_scalars")
TIME_COLUMNS = ("FrameTime", "GameThreadTime", "RenderThreadTime", "RHIThreadTime")
SETTLE = 60                    # frames each state settles (TSR, exposure) before the CSV records
CSV_STABLE_TICKS = 10          # a CSV's size must hold this many ticks before it is read


def csv_summary(text):
    """A CSV profile's per-frame columns: {"frames": n, "columns_total": n, "columns": [...], "stats": {column:
    {median, p25, p75, n}}}, for every column whose name holds "GPU" and for TIME_COLUMNS ("columns" lists those
    found). Rows after the data (the trailing "[HasHeaderRowAtEnd]" metadata and repeated header) and cells that are
    not numbers are skipped."""
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return {"frames": 0, "columns_total": 0, "columns": [], "stats": {}}
    header = [h.strip() for h in rows[0]]
    keep = [i for i, h in enumerate(header) if "GPU" in h.upper() or h in TIME_COLUMNS]
    values = {header[i]: [] for i in keep}
    frames = 0
    for row in rows[1:]:
        if not row or row[0].startswith("["):
            break
        if len(row) < len(header):
            continue
        frames += 1
        for i in keep:
            try:
                values[header[i]].append(float(row[i]))
            except ValueError:
                pass
    out = {}
    for name, v in values.items():
        if not v:
            continue
        v = sorted(v)
        q = statistics.quantiles(v, n=4) if len(v) >= 2 else [v[0], v[0], v[0]]
        out[name] = {"median": round(statistics.median(v), 4), "p25": round(q[0], 4), "p75": round(q[2], 4),
                     "n": len(v)}
    return {"frames": frames, "columns_total": len(header), "columns": [header[i] for i in keep], "stats": out}


def png_size(data):
    """(width, height) from a PNG's IHDR."""
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("not a PNG")
    return struct.unpack(">II", data[16:24])


def main():
    import unreal

    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("render_yumi_fp_review", here / "render_yumi_fp_review.py")
    R = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(R)                               # its main() runs only as __main__

    opts = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
    if "out" not in opts:
        raise RuntimeError("fp fur cost: out=<path> is required")
    target = R.ROOT / opts["out"]
    if target.exists():
        raise RuntimeError(f"fp fur cost: {target} exists; a run never writes over earlier evidence")
    holds = [h for h in opts.get("holds", "right_cheek_clear,paw").split(",") if h]
    unknown = [h for h in holds if h not in R.HOLDS]
    if unknown:
        raise RuntimeError(f"fp fur cost: unknown holds {unknown}")
    frames = int(opts.get("frames", "120"))
    shots = target.parent / (target.stem + "_viewport")
    shots.mkdir(parents=True, exist_ok=True)
    csv_dir = R.ROOT / "Saved/Profiling/CSV"
    lib = unreal.MaterialEditingLibrary
    assets = unreal.EditorAssetLibrary

    def stats_of(m):
        s = lib.get_statistics(m)
        out, missing = {}, []
        for key in STAT_NAMES:
            try:
                out[key] = s.get_editor_property(key)
            except Exception:
                missing.append(key)
        out["missing"] = missing
        return out

    # --- Material statistics, before the scene ------------------------------------------------------------
    folder = R.LEVEL.rsplit("/", 1)[0]
    assets.make_directory(folder)
    materials = {}
    for name in PAW_MATERIALS:
        path = f"{R.PAWS}/{name}"
        if assets.does_asset_exist(path):
            materials[name] = stats_of(R.load(path))
    variants = {}
    for mode in LIGHTING_MODES:
        enum = getattr(unreal.TranslucencyLightingMode, mode, None)
        if enum is None:
            variants[mode] = {"missing": "this engine has no such lighting mode"}
            continue
        dst = f"{folder}/MV_FurShells_{mode}"
        if assets.does_asset_exist(dst):
            assets.delete_asset(dst)
        dup = assets.duplicate_asset(f"{R.PAWS}/{SHELL_SLOT}", dst)
        dup.set_editor_property("translucency_lighting_mode", enum)
        lib.recompile_material(dup)
        variants[mode] = stats_of(dup)
        assets.delete_asset(dst)

    # --- The scene, as the capture builds it ----------------------------------------------------------------
    env = R.build_level()
    ev100 = R.metered_ev100()
    R.exposure(ev100)
    vm = R.Viewmodel(True)
    pc = vm.paw.static_mesh_component
    rows = R.B.asset_rows(pc.get_editor_property("static_mesh"))
    shell_index = [i for i, n, _p in rows if n == SHELL_SLOT]
    if len(shell_index) != 1:
        raise RuntimeError(f"fp fur cost: the paw has {len(shell_index)} {SHELL_SLOT} slots")
    shell_index = shell_index[0]
    clear_path = f"{folder}/M_FPFurCost_Clear"
    if assets.does_asset_exist(clear_path):                  # the review folder is shared across runs
        clear = R.load(clear_path)
        for e in list(lib.get_material_expressions(clear)):
            lib.delete_material_expression(clear, e)
    else:
        clear = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_FPFurCost_Clear", folder, unreal.Material,
                                                                        unreal.MaterialFactoryNew())
    clear.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    clear.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    zero = lib.create_material_expression(clear, unreal.MaterialExpressionConstant, -300, 0)
    zero.set_editor_property("r", 0.0)
    lib.connect_material_property(zero, "", unreal.MaterialProperty.MP_OPACITY)
    lib.connect_material_property(zero, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(clear)
    variants["clear (shells_clear state)"] = stats_of(clear)
    cvars = {}
    for cmd in ("r.GPUStatsEnabled 1", "r.GPUCsvStatsEnabled 1"):
        unreal.SystemLibrary.execute_console_command(R.world(), cmd)
        name = cmd.split()[0]
        cvars[name] = unreal.SystemLibrary.get_console_variable_int_value(name)
    for name in ("r.ScreenPercentage", "r.TSR.History.SampleCount"):
        cvars[name] = unreal.SystemLibrary.get_console_variable_float_value(name)
    status = {"frames": 0, "queue": list(holds), "phase": "pose", "count": 0, "results": {}, "viewport": {},
              "regates": {}}

    def apply(state):
        pc.set_material(shell_index, clear if state == "shells_clear" else None)
        R.hide([vm.paw], state == "no_paw")

    def finish(message, error=False):
        unreal.unregister_slate_post_tick_callback(handle)
        (unreal.log_error if error else unreal.log)(message)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)

    def write():
        record = {"schema_version": 1, "generator": "scripts/unreal/measure_fp_fur_cost.py",
                  "engine": unreal.SystemLibrary.get_engine_version(), "holds": holds, "frames_per_state": frames,
                  "settle_frames": SETTLE, "states": list(STATES), "cvars": cvars, "materials": materials,
                  "shell_lighting_variants": variants, "viewport": status["viewport"], "gpu": status["results"],
                  "materials_after": status["regates"], "assets_sha256": R.imported_assets(),
                  "scope": "editor measurement: GPU times at the editor viewport's size (recorded), not a capture's "
                           "1920 x 1080; not a render for review, an admission or a performance acceptance"}
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "x", encoding="utf-8") as fh:
            fh.write(json.dumps(record, indent=1) + "\n")

    def tick(_delta):
        try:
            step()
        except Exception as exc:  # never spin on a failing callback
            finish(f"FP_FUR_COST_FAILED: {exc!r}", error=True)

    def step():
        status["frames"] += 1
        R.LEVELS.editor_invalidate_viewports()
        if status["frames"] < 30:
            return
        ph = status["phase"]
        if ph == "pose":
            if not status["queue"]:
                write()
                finish(f"FP_FUR_COST_COMPLETE: {target}")
                return
            hold = status["queue"][0]
            vm.pose(hold)
            status.update(phase="settle_pose", count=0, hold=hold, states=list(STATES))
            return
        hold = status["hold"]
        status["count"] += 1
        if ph == "settle_pose":
            if status["count"] < 20:
                return
            vm.check_pose(hold)
            vm.nock_arrow()
            cam = R.camera_for(hold, 1920, 1080)
            R.LEVELS.pilot_level_actor(cam)
            R.LEVELS.editor_set_game_view(True)
            status.update(phase="light", count=0, cam=cam)
        elif ph == "light" and status["count"] >= 150:
            shot = shots / f"{hold}.png"
            status.update(phase="size", count=0, shot=shot, started=time.time())
            unreal.SystemLibrary.execute_console_command(R.world(), f'HighResShot 1 filename="{shot}"')
        elif ph == "size":
            shot = status["shot"]
            if shot.is_file() and shot.stat().st_mtime >= status["started"] and shot.stat().st_size > 24:
                w, h = png_size(shot.read_bytes()[:32])
                status["viewport"][hold] = {"width": w, "height": h, "png": shot.name}
                status.update(phase="apply", count=0)
            elif status["count"] > 4000:
                raise RuntimeError(f"{shot} was not written")
        elif ph == "apply":
            state = status["states"][0]
            apply(state)
            status.update(phase="settle_state", count=0, state=state)
        elif ph == "settle_state" and status["count"] >= SETTLE:
            status["before"] = {p.name for p in csv_dir.glob("*.csv*")} if csv_dir.is_dir() else set()
            unreal.SystemLibrary.execute_console_command(R.world(), "csvprofile start")
            status.update(phase="record", count=0)
        elif ph == "record" and status["count"] >= frames:
            unreal.SystemLibrary.execute_console_command(R.world(), "csvprofile stop")
            status.update(phase="csv_wait", count=0, size=-1, stable=0)
        elif ph == "csv_wait":
            new = [p for p in csv_dir.glob("*.csv*") if p.name not in status["before"]] if csv_dir.is_dir() else []
            if len(new) == 1:
                size = new[0].stat().st_size
                status["stable"] = status["stable"] + 1 if size == status["size"] and size > 0 else 0
                status["size"] = size
                if status["stable"] >= CSV_STABLE_TICKS:
                    data = new[0].read_bytes()
                    text = (gzip.decompress(data) if new[0].suffix == ".gz" else data).decode("utf-8", "replace")
                    status["results"].setdefault(hold, {})[status["state"]] = dict(csv_summary(text), file=new[0].name)
                    apply("shells")
                    status["states"].pop(0)
                    status.update(phase="apply" if status["states"] else "done", count=0)
            elif len(new) > 1:
                raise RuntimeError(f"several new CSVs: {[p.name for p in new]}")
            elif status["count"] > 3000:
                raise RuntimeError("csvprofile stop wrote no CSV")
        elif ph == "done":
            status["regates"][hold] = vm.check_materials(f"after the {hold} cost states")
            R.ACTORS.destroy_actor(status["cam"])
            status["queue"].pop(0)
            status.update(phase="pose", count=0)

    handle = unreal.register_slate_post_tick_callback(tick)
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)


if __name__ == "__main__":
    main()
