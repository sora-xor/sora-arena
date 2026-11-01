"""The v2.1 timber pilot: six members with real geometric raised grain and adze, SM5 fallbacks, close renders.

Run (Blender 5.2.2; the pinned CPU path, since Cycles' Metal compile hangs on macOS 27):
  blender -b --factory-startup --python-exit-code 1 --python scripts/art/create_nyaagyu_dojo_timbers_pilot.py -- --cpu
      [--samples 96] [--bake-res 2048] [--no-renders]
  blender -b --factory-startup --python-exit-code 1 --python scripts/art/create_nyaagyu_dojo_timbers_pilot.py -- --cpu
      --verify [--archive-receipt Local/ArtCache/Archive/<namespace>/run1/receipt.json] [--accept-generator SHA256]

The six members are dojo_timber_pilot.pilot_members(): the first chapter-1
wall column, open column, nageshi, cornice, koshi and nuki. They have v1's
logs, rebuilt with sora_timber_v2 (sora-timber-geometry-v2.1).

Everything goes to the versioned namespace ``Local/ArtCache/NyaagyuDojoTimbersV21Pilot/``,
never these, which the path guard refuses:
* the frozen kit (Content/SourceArt/Environment/NyaagyuDojoTimbers);
* its baseline cache (Local/ArtCache/NyaagyuDojoTimbers);
* run 1, the archived v2 pilot (Local/ArtCache/NyaagyuDojoTimbersV2Pilot).

Run 1 is verified only from the frozen 82869a4 inputs; this tree's v2.1
sources can't reproduce its canonical geometry.

The output:

* ``Dense/<asset>.fbx``: the Nanite source;
* ``Fallback/<asset>_Fallback.fbx`` and
  ``Maps/T_<asset>_{NormalDX,Masks}.png``: the separate SM5/M1 fallback, baked
  from the dense mesh;
* ``Shared/``: copies of the three shared textures;
* ``Renders/*.png`` and ``renders.json``: Cycles CPU source renders. Clay
  shots prove the geometry alone carries the relief; material shots use the
  v2 look-dev, whose latewood is the geometry's phase;
* ``manifest.json``, ``evidence.json`` (each FBX's SHA-256 and v2.1 canonical
  digest) and ``checks.json``. The manifest carries sora_timber_v2.UV_CONTRACT:
  each UV channel's payload, its Unreal decode, the material's ring formula
  with the UVKnot select, and the Unreal content path.

``checks.json`` holds sora_timber_v2.check_mesh for every mesh. The run stops
before exporting anything if a mesh fails: not closed, inconsistently wound,
folded, crossed, needled, degenerate, or missing its feature relief.

A generation never writes into a namespace that already holds a run: a later
generation gets a new namespace, so an archived run is never overwritten.

``--verify`` only reads the run (dojo_timber_pilot_verify.py). It rebuilds
every member, and compares:

* the canonical digests with the manifest and the original evidence;
* the check reports with the original checks.json;
* the FBX SHA-256 and bytes on disk with the original evidence;
* the Shared textures, rebuilt in a temporary directory, with the manifest and
  the files on disk;
* the inputs with the manifest;
* optionally, every file with its archive receipt.

A generator that differs from the manifest's fails as INPUTS_CHANGED, unless
``--accept-generator`` names its exact current SHA-256, say for a
verify-only edit. The receipt keeps the manifest's original generator hash,
and records the pin and whether it was accepted.

Its passing verdict is GEOMETRY_INPUTS_VERIFIED: geometry and inputs only
(dojo_timber_pilot_verify.SCOPE). It is not a re-export, re-bake or
re-render.

Its only output is a new receipt under
``Local/ArtCache/Verification/<namespace>/``, created exclusively. It exits 1
unless everything matches.
"""
from __future__ import annotations

import json
import math
import platform
import subprocess
import sys
import tempfile
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
import dojo_timber_pilot_verify as VF  # noqa: E402
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
         "samples": 96, "bake_res": 2048, "archive_receipt": None, "accept_generator": None}
    for key in ("--samples", "--bake-res"):
        if key in argv:
            o[key[2:].replace("-", "_")] = int(argv[argv.index(key) + 1])
    if "--archive-receipt" in argv:
        o["archive_receipt"] = Path(argv[argv.index("--archive-receipt") + 1])
    if "--accept-generator" in argv:
        o["accept_generator"] = argv[argv.index("--accept-generator") + 1]
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


def _git(*args):
    try:
        return subprocess.run(["git", "-C", str(L.ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def rebuild(arrays, on_member=None):
    """Every pilot member rebuilt: ({asset: (dense digest, fallback digest)},
    {entry: check report}), with no export, bake or render."""
    digests, checks = {}, {}
    for m, fam, kind, rec in PILOT.pilot_members():
        B = V.build(m, arrays)
        mf = V.fallback(m)
        Bf = V.build(mf, arrays)
        checks[f"{m.name}:dense"] = V.check_mesh(B, m)
        checks[f"{m.name}:fallback"] = V.check_mesh(Bf, mf)
        checks[f"{m.name}:visibility"] = V.relief_visibility(B, m, face=2 if kind == "Koshi" else 3)
        obj = V.to_blender(m.name, B, m)
        objf = V.to_blender(mf.name, Bf, mf)
        if fam == "rail":
            RG.lay_down(obj, m, kind)
            RG.lay_down(objf, m, kind)
        digests[m.name] = (V.canonical_digest(obj), V.canonical_digest(objf))
        TG.drop(obj, objf)
        if on_member:
            on_member(m.name)
    return digests, checks


def verify(o):
    """Read the run, rebuild it, compare, and write only a new receipt outside the run."""
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    manifest, evidence, original_checks = VF.load_run(OUT)
    arrays = V.shared_arrays()
    with tempfile.TemporaryDirectory(prefix="pilot_verify_shared_") as tmp:
        T.shared_textures(Path(tmp))
        shared = VF.compare_shared(L.ROOT, manifest, Path(tmp))
    digests, checks = rebuild(arrays, lambda name: print("PILOT_VERIFY_MEMBER", name, flush=True))
    fbx = VF.compare_fbx(L.ROOT, evidence)
    digest_cmp = VF.compare_digests(manifest, evidence, digests)
    check_cmp = VF.compare_checks(original_checks, checks)
    inputs = VF.compare_inputs(L.ROOT, manifest)
    archive = VF.compare_archive(OUT, o["archive_receipt"]) if o["archive_receipt"] else None
    status, problems = VF.verdict(fbx, digest_cmp, check_cmp, shared, inputs, archive, o["accept_generator"])
    data = {
        "schema_version": 1, "kind": "art-run-verification", "status": status, "scope": VF.SCOPE, "problems": problems,
        "run": L.rel(OUT), "run_manifest_sha256": L.sha256(OUT / "manifest.json"),
        "run_evidence_sha256": L.sha256(OUT / "evidence.json"), "run_checks_sha256": L.sha256(OUT / "checks.json"),
        "verifier": {"generator": GEN, "generator_sha256": L.sha256(L.ROOT / GEN), "head": _git("rev-parse", "HEAD"),
                     "uncommitted": _git("status", "--porcelain", "--", GEN, *INPUTS, "scripts/art/dojo_timber_pilot_verify.py")},
        "versions": {"blender": bpy.app.version_string, "numpy": np.__version__, "python": platform.python_version()},
        "started_utc": started, "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "digests": digest_cmp, "fbx": fbx, "checks": check_cmp, "shared_textures": shared, "inputs": inputs,
        "generator_drift": VF.generator_drift(inputs, o["accept_generator"]),
        "archive": archive,
    }
    path = VF.write_receipt(VF.receipt_path(manifest["kit"]), OUT, data, frozen=PILOT.FROZEN)
    print("PILOT_VERIFY_RECEIPT", L.rel(path), flush=True)
    if status != VF.PASSED:
        print(f"PILOT_VERIFY_{status}", "; ".join(problems), flush=True)
        sys.exit(1)
    print("PILOT_GEOMETRY_INPUTS_VERIFIED", len(digests), flush=True)


def main():
    o = parse()
    scene = L.reset_scene()
    if o["cpu"]:
        scene.cycles.device = "CPU"
    if o["verify"]:
        verify(o)
        return
    if OUT.exists() and any(OUT.iterdir()):
        raise SystemExit(f"pilot: {OUT} already holds a run; a new generation needs a new namespace")
    arrays = V.shared_arrays()
    shared_files = T.shared_textures(guard(OUT / "Shared"))
    shared = {k: p for k, (p, _) in shared_files.items()}
    evidence = {"generator": GEN, "blender": bpy.app.version_string,
                "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "fbx": {}}
    checks, records, built = {}, [], {}
    for m, fam, kind, rec in PILOT.pilot_members():
        t0 = time.time()
        B = V.build(m, arrays)
        mf = V.fallback(m)
        Bf = V.build(mf, arrays)
        for label, mesh, mm in (("dense", B, m), ("fallback", Bf, mf)):
            report = V.check_mesh(mesh, mm)
            checks[f"{m.name}:{label}"] = report
            if not report["ok"]:
                guard(OUT / "checks.json").write_text(json.dumps(checks, indent=1) + "\n")
                raise SystemExit(f"pilot: {m.name} {label} fails its mesh checks: {report['failures']}")
        checks[f"{m.name}:visibility"] = V.relief_visibility(B, m, face=2 if kind == "Koshi" else 3)
        obj = V.to_blender(m.name, B, m)
        objf = V.to_blender(mf.name, Bf, mf)
        if fam == "rail":
            RG.lay_down(obj, m, kind)
            RG.lay_down(objf, m, kind)
        digest, fb_digest = V.canonical_digest(obj), V.canonical_digest(objf)
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
    evidence["digest_mismatches"] = []
    guard(OUT / "evidence.json").write_text(json.dumps(evidence, indent=1) + "\n")
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
        "uv_contract": V.UV_CONTRACT,
        "shared_textures": {k: {"file": L.rel(p), "sha256": L.sha256(p), "kind": kind} for k, (p, kind) in shared_files.items()},
        "members": records, "renders": renders,
        "notes": {
            "scope": "pilot only: six chapter-1 members in a versioned namespace; the frozen v1 kit, its cache and "
                     "run 1 are untouched",
            "uv": "UV0-UV3 as v1, plus UVKnot (UV4); UVLogQ is the log frame before the grain relief, the frame "
                  "the raised grain is cut from, with v2.1's periodic wobble and no knot swap (see uv_contract)",
            "materials": "the latewood matches the geometry only with the v2 ring wander, the UVKnot select and "
                         "Unreal's (U, 1 - V) decode (uv_contract); the baseline master's ring model does not apply",
        },
    }
    guard(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print("PILOT_READY", len(records), "members,", sum(r["triangles"] for r in records), "Nanite source triangles,",
          len(renders), "renders", flush=True)


if __name__ == "__main__":
    main()
