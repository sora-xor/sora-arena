"""The v2 timber pilot: six members with real geometric raised grain and adze, SM5 fallbacks, close renders.

Run (Blender 5.2.2; the pinned CPU path, since Cycles' Metal compile hangs on macOS 27):
  blender -b --factory-startup --python-exit-code 1 --python scripts/art/create_nyaagyu_dojo_timbers_pilot.py -- --cpu
      [--samples 96] [--bake-res 2048] [--no-renders] [--verify]

The six members are dojo_timber_pilot.pilot_members(): the first chapter-1
wall column, open column, nageshi, cornice, koshi and nuki. They have v1's
logs, rebuilt with sora_timber_v2.

Everything goes to the versioned namespace ``Local/ArtCache/NyaagyuDojoTimbersV2Pilot/``,
never the frozen kit (Content/SourceArt/Environment/NyaagyuDojoTimbers) or
its baseline cache (Local/ArtCache/NyaagyuDojoTimbers):

* ``Dense/<asset>.fbx``: the Nanite source;
* ``Fallback/<asset>_Fallback.fbx`` and
  ``Maps/T_<asset>_{NormalDX,Masks}.png``: the separate SM5/M1 fallback, baked
  from the dense mesh;
* ``Shared/``: copies of the three shared textures;
* ``Renders/*.png`` and ``renders.json``: Cycles CPU source renders. Clay
  shots prove the geometry alone carries the relief; material shots use the
  v2 look-dev, whose latewood is the geometry's phase;
* ``manifest.json``, ``evidence.json`` (each FBX's SHA-256 and v2 canonical
  digest) and ``checks.json``.

``checks.json`` holds sora_timber_v2.check_mesh for every mesh. The run stops
before exporting anything if a mesh fails: not closed, inconsistently wound,
folded, crossed, needled, degenerate, or missing its feature relief.

``--verify`` rebuilds and compares digests with the pilot manifest, writing
only evidence.json.
"""
from __future__ import annotations

import json
import math
import platform
import sys
import time
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import create_nyaagyu_dojo_rails as RG  # noqa: E402
import create_nyaagyu_dojo_timbers as TG  # noqa: E402
import create_runtime_weapon_lib as L  # noqa: E402
import dojo_timber_pilot as PILOT  # noqa: E402
import sora_prop_lib as PL  # noqa: E402
import sora_timber_bake as TB  # noqa: E402
import sora_timber_lib as T  # noqa: E402
import sora_timber_lookdev as LD  # noqa: E402
import sora_timber_lookdev_v2 as LD2  # noqa: E402
import sora_timber_v2 as V  # noqa: E402

GEN = "scripts/art/create_nyaagyu_dojo_timbers_pilot.py"
INPUTS = ("scripts/art/sora_timber_v2.py", "scripts/art/dojo_timber_pilot.py", "scripts/art/sora_timber_lookdev_v2.py",
          "scripts/art/timber_density_study.py", "scripts/art/sora_timber_lib.py", "scripts/art/sora_timber_bake.py",
          "scripts/art/sora_timber_lookdev.py", "scripts/art/create_nyaagyu_dojo_timbers.py",
          "scripts/art/create_nyaagyu_dojo_rails.py", "scripts/art/create_runtime_weapon_lib.py",
          "scripts/art/sora_prop_lib.py")
OUT = PILOT.OUT
guard = PILOT.guard


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"cpu": "--cpu" in argv, "renders": "--no-renders" not in argv, "verify": "--verify" in argv,
         "samples": 96, "bake_res": 2048}
    for key in ("--samples", "--bake-res"):
        if key in argv:
            o[key[2:].replace("-", "_")] = int(argv[argv.index(key) + 1])
    return o


def export(obj, path: Path):
    return TG.export_fbx(obj, guard(path))


def pilot_shots(members):
    """Camera, target and rig per shot (member frame for columns; bay frame for laid-down rails)."""
    front_y = TG.COL_CENTRE_Y - TG.COL / 2
    shots = []
    wall = next(m for m, fam, kind, rec in members if kind == "wall")
    # The room-face check nearest eye height, as v1's close-up chose it.
    best, check_target = math.inf, (0.0, front_y, 1.3)
    for ck in wall.log.checks:
        if ck.face != 3:
            continue
        zc = float(np.clip(1.3, ck.z0 + 0.05, ck.z1 - 0.05))
        if abs(zc - 1.3) < best:
            best = abs(zc - 1.3)
            uc, _, _ = T._check_at(ck, zc)
            check_target = (float(uc), front_y, zc)
    dent = next((d for d in V.dent_sites(wall) if d[0] == 3), None)
    dent_target = (float(dent[1]), front_y, float(dent[2])) if dent else (0.03, front_y, 1.2)
    grain_target = (0.04, front_y, 1.45)
    shots += [
        ("wall", "GrainClose", "Raking", grain_target, (grain_target[0] + 0.10, front_y - 0.22, 1.50), 70.0),
        ("wall", "CheckClose", "Raking", check_target, (check_target[0] + 0.10, front_y - 0.26, check_target[2] + 0.05), 60.0),
        ("wall", "DentClose", "Raking", dent_target, (dent_target[0] + 0.08, front_y - 0.20, dent_target[2] + 0.04), 70.0),
        ("wall", "ArrisMid", "GoldenHour", (-0.12, front_y, 1.2), (0.35, front_y - 0.9, 1.45), 50.0),
    ]
    for kind in ("Koshi", "Nuki", "Nageshi"):
        z0, z1, face_y, *_ = RG.RAILS[kind]
        if kind == "Koshi":
            target = (0.15, (face_y + RG.SLAB0) / 2, z1)
            eye = (0.32, face_y - 0.22, z1 + 0.16)
            shots.append((kind, "WornTopClose", "Raking", target, eye, 60.0))
        elif kind == "Nuki":
            target = (0.0, face_y, (z0 + z1) / 2)
            eye = (0.35, face_y - 1.6, (z0 + z1) / 2 - 1.0)
            shots.append((kind, "AdzeMid", "Raking", target, eye, 50.0))
        else:
            target = (0.1, face_y, (z0 + z1) / 2)
            eye = (0.25, face_y - 0.28, (z0 + z1) / 2 + 0.02)
            shots.append((kind, "GrainClose", "Raking", target, eye, 60.0))
    return shots


def lookdev(o, built, shared):
    scene = bpy.context.scene
    LD.stage(infill_y=TG.INFILL_Y)
    clay = LD.clay_material()
    files = []
    by_kind = {kind: entry for kind, entry in built.items()}
    for kind, shot, rig, target, eye, lens in pilot_shots([(e["member"], e["family"], k, e["record"]) for k, e in built.items()]):
        e = by_kind[kind]
        m, obj, objf = e["member"], e["obj"], e["objf"]
        preset = "column_fukiurushi"
        wood = LD2.timber_material(f"LD2_{m.name}", preset, shared, m.log.ring_width)
        wood_fb = LD2.timber_material(f"LD2_{m.name}_Fallback", preset, shared, m.log.ring_width, e["maps"])
        variants = [("Clay", clay, False), ("Nanite", wood, False)]
        if kind == "wall" and shot == "CheckClose":
            variants.append(("Fallback", wood_fb, True))
        for label, mat, show_fb in variants:
            for other in built.values():
                other["obj"].hide_render = True
                other["objf"].hide_render = True
            obj.hide_render = show_fb
            objf.hide_render = not show_fb
            (objf if show_fb else obj).data.materials[0] = mat
            if rig == "Raking":
                LD.raking_rig(scene)
            else:
                PL.setup_rig(scene, rig)
            LD.camera(scene, "LD2_Cam", eye, target, lens)
            path = guard(OUT / "Renders" / f"{m.name}_{label}_{shot}.png")
            t0 = time.time()
            LD.render(scene, path, (1600, 1000), o["samples"])
            files.append({"file": L.rel(path), "member": m.name, "shot": shot, "rig": rig, "material": label,
                          "kind": "Blender Cycles source render (CPU)" if o["cpu"] else "Blender Cycles source render",
                          "seconds": round(time.time() - t0, 1)})
            print("PILOT_RENDER", L.rel(path), files[-1]["seconds"], flush=True)
    return files


def main():
    o = parse()
    scene = L.reset_scene()
    if o["cpu"]:
        scene.cycles.device = "CPU"
    arrays = V.shared_arrays()
    shared_files = T.shared_textures(guard(OUT / "Shared"))
    shared = {k: p for k, (p, _) in shared_files.items()}
    committed = json.loads((OUT / "manifest.json").read_text()) if o["verify"] else None
    evidence = {"generator": GEN, "blender": bpy.app.version_string,
                "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "fbx": {}}
    checks, records, built, mismatches = {}, [], {}, []
    for m, fam, kind, rec in PILOT.pilot_members():
        t0 = time.time()
        B = V.build(m, arrays)
        mf = V.fallback(m)
        Bf = V.build(mf, arrays)
        for label, mesh, mm in (("dense", B, m), ("fallback", Bf, mf)):
            report = V.check_mesh(mesh, mm)
            checks[f"{m.name}:{label}"] = report
            if not report["ok"]:
                (OUT / "checks.json").write_text(json.dumps(checks, indent=1) + "\n")
                raise SystemExit(f"pilot: {m.name} {label} fails its mesh checks: {report['failures']}")
        checks[f"{m.name}:visibility"] = V.relief_visibility(B, m, face=2 if kind == "Koshi" else 3)
        obj = T.to_blender(m.name, B, m)
        objf = T.to_blender(mf.name, Bf, mf)
        if fam == "rail":
            RG.lay_down(obj, m, kind)
            RG.lay_down(objf, m, kind)
        digest, fb_digest = V.canonical_digest(obj), V.canonical_digest(objf)
        if committed is not None:
            want = next((r for r in committed["members"] if r["asset"] == m.name), {})
            if want.get("digest") != digest or want.get("fallback_digest") != fb_digest:
                mismatches.append(m.name)
            for path in (OUT / "Dense" / f"{m.name}.fbx", OUT / "Fallback" / f"{mf.name}.fbx"):
                evidence["fbx"][L.rel(path)] = {"sha256": L.sha256(path), "bytes": path.stat().st_size}
            TG.drop(obj, objf)
            print("PILOT_VERIFIED" if m.name not in mismatches else "PILOT_MISMATCH", m.name, flush=True)
            continue
        dense = export(obj, OUT / "Dense" / f"{m.name}.fbx")
        coarse = export(objf, OUT / "Fallback" / f"{mf.name}.fbx")
        maps = TB.bake_fallback(obj, objf, guard(OUT / "Maps"), m.name.removeprefix("SM_"), res=o["bake_res"])
        evidence["fbx"][L.rel(dense)] = {"sha256": L.sha256(dense), "bytes": dense.stat().st_size, "digest": digest}
        evidence["fbx"][L.rel(coarse)] = {"sha256": L.sha256(coarse), "bytes": coarse.stat().st_size, "digest": fb_digest}
        records.append({
            "asset": m.name, "family": fam, "kind": kind, "v1_asset": rec["asset"], "seed": m.seed,
            "ring_width_m": round(m.log.ring_width, 6), "grain": {str(f): list(v) for f, v in m.grain.items()},
            "grain_zone": m.grain_zone, "finish": list(m.finish), "length_m": m.length,
            "triangles": len(obj.data.polygons), "vertices": len(obj.data.vertices), "digest": digest,
            "cache_fbx": L.rel(dense), "fallback_fbx": L.rel(coarse), "fallback_triangles": len(objf.data.polygons),
            "fallback_digest": fb_digest,
            "fallback_maps": {k: {"file": L.rel(p), "sha256": L.sha256(p), "bytes": p.stat().st_size, "res": o["bake_res"]}
                              for k, p in maps.items()},
            "seconds": round(time.time() - t0, 1)})
        built[kind] = {"member": m, "family": fam, "record": rec, "obj": obj, "objf": objf, "maps": maps}
        obj.hide_set(True)
        objf.hide_set(True)
        print("PILOT_MEMBER", m.name, records[-1]["triangles"], records[-1]["fallback_triangles"], records[-1]["seconds"],
              flush=True)
    evidence["digest_mismatches"] = mismatches
    guard(OUT / "evidence.json").write_text(json.dumps(evidence, indent=1) + "\n")
    if o["verify"]:
        if mismatches:
            print("PILOT_VERIFY_FAILED", ", ".join(mismatches), flush=True)
            sys.exit(1)
        print("PILOT_VERIFIED_ALL", len(PILOT.pilot_members()), flush=True)
        return
    guard(OUT / "checks.json").write_text(json.dumps(checks, indent=1) + "\n")
    renders = lookdev(o, built, shared) if o["renders"] else []
    guard(OUT / "Renders").mkdir(parents=True, exist_ok=True)
    guard(OUT / "Renders" / "renders.json").write_text(json.dumps({"renderer": "Blender Cycles (CPU)" if o["cpu"] else "Blender Cycles",
                                                                   "renders": renders}, indent=1) + "\n")
    manifest = {
        "schema_version": 1, "kit": PILOT.NAMESPACE, "generator": GEN, "generator_sha256": L.sha256(L.ROOT / GEN),
        "inputs": {p: L.sha256(L.ROOT / p) for p in INPUTS},
        "versions": {"blender": bpy.app.version_string, "numpy": np.__version__, "python": platform.python_version()},
        "digest": V.DIGEST_VERSION,
        "wander": {"rings_per_unit": V.WANDER_RINGS_PER_UNIT, "amplitude": V.WANDER_AMPLITUDE},
        "shared_textures": {k: {"file": L.rel(p), "sha256": L.sha256(p), "kind": kind} for k, (p, kind) in shared_files.items()},
        "members": records, "renders": renders,
        "notes": {
            "scope": "pilot only: six chapter-1 members in a versioned namespace; the frozen v1 kit and cache are untouched",
            "uv": "as v1; UVLogQ is the log frame before the grain relief, the frame the raised grain is cut from",
            "materials": "the latewood matches the geometry only with the v2 ring wander and Unreal's V-flip correction "
                         "(q = (U, 1 - V), seed = 1 - UV3.V, RingNoise/RingRandom at 1 - v)",
        },
    }
    guard(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print("PILOT_READY", len(records), "members,", sum(r["triangles"] for r in records), "Nanite source triangles,",
          len(renders), "renders", flush=True)


if __name__ == "__main__":
    main()
