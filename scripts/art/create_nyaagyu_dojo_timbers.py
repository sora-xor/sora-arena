"""Tsumagizaka dojo hall: timbers cut from their own logs (Nanite + SM5 fallback).

Run (Blender 5.2.2):
  blender -b --factory-startup --python scripts/art/create_nyaagyu_dojo_timbers.py -- \
      [--halls ch01|all|none] [--pool-wall N] [--pool-open N] \
      [--lookdev] [--quick] [--samples N] [--cpu] [--verify]

Hinoki columns, 24 cm square and 7 m tall like SM_DojoColumn, with its pivot
(floor level; the room-facing -Y face 4 cm proud of the bay line, the back face
in the wall), in two sets:

* Placements (SM6): one log per column placement in the estate halls
  (scripts/art/dojo_hall_placements.py replays HallInterior's layout from the
  campaign spaces), named by the hall's rect, wall and bay and seeded from that
  name. Only dense Nanite meshes, rebuilt from the seeds into the ignored
  Local/ArtCache/NyaagyuDojoTimbers; Unreal generates their fallback. --halls
  ch01 builds the chapter-1 dojo's rect, all builds every estate hall, and the
  manifest's coverage records which placements have their own log.
* MAC pool (SM5): SM_DojoTimberColumn_MAC_{Wall,Open}_NN, a few conventional
  columns for renderers without Nanite. Each is the coarse fallback of its own
  dense log, with its checks in geometry and NormalDX/Masks baked from that log.
  They are the runtime fallback, so they are committed (LFS) in
  Content/SourceArt/Environment/NyaagyuDojoTimbers.

Wall columns detail the room face and the 6 cm of each side in front of the
infill; Open columns, beside door and engawa bays, detail every face.

Every exported mesh records a canonical geometry digest
(sora_timber_lib.canonical_digest). A build writes the manifest and, in the
cache, evidence.json with this run's FBX hashes and digests. --verify instead
rebuilds against the committed manifest: it fails on any digest mismatch and
refreshes only the evidence, which the Unreal importer requires.
Look-dev renders are Blender (Cycles) source renders, labelled as such.
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
import create_runtime_weapon_lib as L  # noqa: E402
import dojo_hall_placements as HP  # noqa: E402
import sora_prop_lib as PL  # noqa: E402
import sora_timber_bake as TB  # noqa: E402
import sora_timber_lib as T  # noqa: E402
import sora_timber_lookdev as LD  # noqa: E402

GEN = "scripts/art/create_nyaagyu_dojo_timbers.py"
INPUTS = ("scripts/art/sora_timber_lib.py", "scripts/art/sora_timber_lookdev.py", "scripts/art/sora_timber_bake.py",
          "scripts/art/dojo_hall_placements.py", "scripts/art/sora_prop_lib.py",
          "scripts/art/create_runtime_weapon_lib.py")
CH01_DOJO = (8000, -1300, 11600, 1300)   # chapter_01.json pl_tsumagizaka_dojo
OUT = L.ROOT / "Content/SourceArt/Environment/NyaagyuDojoTimbers"
CACHE = L.ROOT / "Local/ArtCache/NyaagyuDojoTimbers"
COL = 0.24
WALL_H = 7.0
COL_CENTRE_Y = 0.08          # kit: column spans y -0.04 .. 0.20, room at -Y
INFILL_Y = 0.02              # kit infill plane
SIDE_VISIBLE = COL / 2 - (INFILL_Y - (COL_CENTRE_Y - COL / 2)) + 0.01   # u extent from the front corner
SPACING = 0.005              # dense vertex spacing on visible faces
POOL_SEED = {"wall": 2101, "open": 2111}


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"halls": "ch01", "pool": {"wall": 10, "open": 3}, "lookdev": False, "quick": False,
         "samples": 96, "cpu": False, "verify": False, "bake_res": 2048}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--pool-wall", "--pool-open"):
            o["pool"][a.split("-")[-1]] = int(argv[i + 1])
            i += 1
        elif a == "--halls":
            o["halls"] = argv[i + 1]
            i += 1
        elif a == "--samples":
            o["samples"] = int(argv[i + 1])
            i += 1
        elif a == "--bake-res":
            o["bake_res"] = int(argv[i + 1])
            i += 1
        elif a in ("--lookdev", "--quick", "--cpu", "--verify"):
            o[a[2:]] = True
        i += 1
    return o


def column_member(seed: int, kind: str, name: str) -> T.Member:
    rng = np.random.default_rng(seed)
    front_u = (-0.07, 0.07)
    if kind == "wall":
        check_faces = (3,)
        check_u = {3: front_u}
        finish = ("planed", "hidden", "planed", "planed")
        # Face 0 (+X) runs u along +Y, face 2 (-X) along -Y: the front 6 cm show.
        vis = ((-COL / 2, -COL / 2 + SIDE_VISIBLE), None, (COL / 2 - SIDE_VISIBLE, COL / 2), None)
        wear = (0.0, 0.0, rng.uniform(0.003, 0.007), rng.uniform(0.003, 0.007))
    else:
        check_faces = (3, 0, 2, 1)
        check_u = {f: front_u for f in range(4)}
        finish = ("planed",) * 4
        vis = (None,) * 4
        wear = tuple(rng.uniform(0.002, 0.007) for _ in range(4))
    # Boxed-heart columns check down the middle of their faces; one check
    # always runs through eye height on the room face.
    log = T.make_log(seed, WALL_H, cut="boxed_heart", width=COL, depth=COL, ring_width=rng.uniform(0.0015, 0.0024),
                     knot_count=(3, 8), check_count=(2, 5), check_faces=check_faces, check_u=check_u,
                     check_length=(0.4, 2.4), check_cover=(0.9, 1.9))
    return T.Member(name=name, length=WALL_H, width=COL, depth=COL, log=log, finish=finish, visible=vis,
                    arris_r=(0.0025,) * 4, arris_wear=wear, handling=(rng.uniform(1.05, 1.3), 0.5),
                    dents=int(rng.integers(16, 34)), dent_zone=(0.35, 2.0), bow=rng.uniform(0.0006, 0.0018),
                    spacing=SPACING, seed=seed, offset=(0.0, COL_CENTRE_Y, 0.0))


def export_fbx(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    L.deselect_all()
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    obj.data.uv_layers.active = obj.data.uv_layers["UV0"]
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
                             apply_scale_options="FBX_SCALE_NONE", global_scale=1.0, axis_forward="-Y", axis_up="Z",
                             mesh_smooth_type="FACE", use_tspace=True, use_triangles=True, use_mesh_modifiers=False,
                             colors_type="LINEAR", add_leaf_bones=False, bake_anim=False, path_mode="STRIP",
                             embed_textures=False, use_custom_props=False)
    return path


def drop(*objs):
    for ob in objs:
        if ob is None:
            continue
        me = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.meshes.remove(me)


def lookdev(o, obj, m: T.Member, fallback_obj, maps, shared):
    scene = bpy.context.scene
    out = OUT / "Renders"
    LD.stage(infill_y=INFILL_Y)
    wood = LD.timber_material(f"LD_{m.name}", "column_fukiurushi", shared)
    wood_fb = LD.timber_material(f"LD_{m.name}_Fallback", "column_fukiurushi", shared, maps)
    clay = LD.clay_material()
    obj.data.materials[0] = wood
    fallback_obj.data.materials[0] = wood_fb
    # Close-up target: the room-face check nearest eye height (1.3 m).
    front_y = COL_CENTRE_Y - COL / 2
    target = (0.0, front_y, 1.3)
    best = math.inf
    for ck in m.log.checks:
        if ck.face != 3:
            continue
        zc = float(np.clip(1.3, ck.z0 + 0.05, ck.z1 - 0.05))
        if abs(zc - 1.3) < best:
            best = abs(zc - 1.3)
            uc, _, _ = T._check_at(ck, zc)
            target = (float(uc), front_y, zc)
    shots = {
        "Full": dict(eye=(1.5, -5.4, 1.9), target=(0.0, front_y, 3.35), lens=24.0, size=(1000, 1500)),
        "Mid": dict(eye=(0.45, -1.2, 1.42), target=(0.0, front_y, 1.18), lens=50.0, size=(1600, 1000)),
        "Close": dict(eye=(target[0] + 0.12, front_y - 0.30, target[2] + 0.05), target=target, lens=60.0,
                      size=(1600, 1000)),
    }
    plan = [("Studio", "Mid"), ("GoldenHour", "Full"), ("GoldenHour", "Mid"), ("Raking", "Mid"),
            ("Raking", "Close"), ("Lantern", "Mid"), ("Raking", "Close", "Clay"), ("Raking", "Close", "Fallback"),
            ("GoldenHour", "Mid", "Fallback")]
    if o["quick"]:
        plan = [("Raking", "Mid"), ("Raking", "Close"), ("Raking", "Close", "Clay"), ("Raking", "Close", "Fallback")]
        for s in shots.values():
            s["size"] = (s["size"][0] * 3 // 4, s["size"][1] * 3 // 4)
    files = []
    for entry in plan:
        rig, shot = entry[0], entry[1]
        # "Nanite": the dense log (vertex masks); "Fallback": the SM5 mesh with
        # its baked NormalDX and Masks on UV1; "Clay": the dense geometry alone.
        material = entry[2] if len(entry) > 2 else "Nanite"
        show_fb = material == "Fallback"
        obj.hide_render = show_fb
        fallback_obj.hide_render = not show_fb
        obj.data.materials[0] = clay if material == "Clay" else wood
        if rig == "Raking":
            LD.raking_rig(scene)
        else:
            PL.setup_rig(scene, rig)
        s = shots[shot]
        LD.camera(scene, "LD_Cam", s["eye"], s["target"], s["lens"])
        path = out / f"{m.name}_{material}_{rig}_{shot}.png"
        t0 = time.time()
        LD.render(scene, path, s["size"], o["samples"])
        files.append({"file": L.rel(path), "rig": rig, "shot": shot, "material": material,
                      "kind": "Blender Cycles source render (CPU)" if o["cpu"] else "Blender Cycles source render",
                      "seconds": round(time.time() - t0, 1)})
        print("TIMBER_RENDER", L.rel(path), files[-1]["seconds"], flush=True)
    obj.data.materials[0] = wood
    obj.hide_render = False
    return files


def member_record(m: T.Member, kind: str, obj, digest):
    return {"asset": m.name, "kind": kind, "seed": m.seed, "length_m": m.length, "section_m": [m.width, m.depth],
            "spacing_m": m.spacing, "finish": list(m.finish), "vertices": len(obj.data.vertices),
            "triangles": len(obj.data.polygons), "knots": len(m.log.knots), "checks": len(m.log.checks),
            "ring_width_m": round(m.log.ring_width, 6), "digest": digest}


def main():
    o = parse()
    scene = L.reset_scene()
    if o["cpu"]:
        # Cycles' Metal pipeline compile hangs on macOS 27 (observed on the M2
        # Ultra, 2026-10-18); the CPU path renders the same image.
        scene.cycles.device = "CPU"
    committed = json.loads((OUT / "manifest.json").read_text()) if o["verify"] else None
    shared_files = T.shared_textures(OUT / "Shared")
    shared = {k: p for k, (p, _) in shared_files.items()}
    evidence = {"generator": GEN, "blender": bpy.app.version_string, "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "fbx": {}}
    mismatches = []

    def check(rec_name, kind_key, digest, family):
        if committed is None:
            return
        want = next((r for r in committed[family] if r["asset"] == rec_name), None)
        if want is None or want[kind_key] != digest:
            mismatches.append(f"{rec_name}.{kind_key}")

    every = HP.placements()
    if o["halls"] == "all":
        todo = every
    elif o["halls"] == "ch01":
        todo = [p for p in every if tuple(p["rect"]) == CH01_DOJO]
    else:
        todo = []
    unique, pool = [], []
    for p in todo:
        t0 = time.time()
        m = column_member(p["seed"], p["kind"], p["name"])
        B = T.build_member(m)
        obj = T.to_blender(m.name, B, m)
        digest = T.canonical_digest(obj)
        path = export_fbx(obj, CACHE / "Unique" / f"{m.name}.fbx")
        evidence["fbx"][L.rel(path)] = {"sha256": L.sha256(path), "bytes": path.stat().st_size, "digest": digest}
        rec = member_record(m, p["kind"], obj, digest)
        rec.update({"rect": p["rect"], "side": p["side"], "bay": p["bay"], "used_by": p["used_by"],
                    "cache_fbx": L.rel(path), "seconds": round(time.time() - t0, 1)})
        check(m.name, "digest", digest, "placements")
        unique.append(rec)
        print("TIMBER_PLACEMENT", m.name, rec["kind"], rec["triangles"], rec["seconds"], flush=True)
        drop(obj)
    built = {r["asset"] for r in unique}
    coverage = {"estate_placements": len(every), "with_own_log": len(built),
                "halls": sorted({tuple(p["rect"]) for p in every}),
                "halls_without_logs": sorted({tuple(p["rect"]) for p in every if p["name"] not in built})}
    keep = None
    for kind in ("wall", "open"):
        for i in range(o["pool"][kind]):
            t0 = time.time()
            m = column_member(POOL_SEED[kind] + i, kind, f"SM_DojoTimberColumn_MAC_{kind.capitalize()}_{i:02d}")
            B = T.build_member(m)
            mf = T.fallback_of(m)
            Bf = T.build_member(mf)
            obj = T.to_blender(f"{m.name}_Dense", B, m)
            objf = T.to_blender(m.name, Bf, mf)
            dense_digest = T.canonical_digest(obj)
            digest = T.canonical_digest(objf)
            dense = export_fbx(obj, CACHE / "PoolDense" / f"{m.name}_Dense.fbx")
            evidence["fbx"][L.rel(dense)] = {"sha256": L.sha256(dense), "bytes": dense.stat().st_size,
                                             "digest": dense_digest}
            coarse = OUT / "FBX" / f"{m.name}.fbx"
            if o["verify"]:
                # The committed fallback and maps stay byte-identical: a rebuild
                # only proves the geometry still matches (digest), and the
                # evidence vouches for the committed file as it is.
                check(m.name, "digest", digest, "pool")
                check(m.name, "dense_digest", dense_digest, "pool")
                evidence["fbx"][L.rel(coarse)] = {"sha256": L.sha256(coarse), "bytes": coarse.stat().st_size,
                                                  "digest": digest}
                print("TIMBER_POOL_VERIFIED", m.name, flush=True)
                drop(obj, objf)
                continue
            export_fbx(objf, coarse)
            maps = TB.bake_fallback(obj, objf, OUT / "Maps", m.name.removeprefix("SM_"), res=o["bake_res"])
            evidence["fbx"][L.rel(coarse)] = {"sha256": L.sha256(coarse), "bytes": coarse.stat().st_size,
                                              "digest": digest}
            rec = member_record(m, kind, obj, dense_digest)
            rec = {**rec, "dense_digest": rec.pop("digest"), "digest": digest,
                   "fallback_vertices": len(objf.data.vertices), "fallback_triangles": len(objf.data.polygons),
                   "fallback_fbx": L.rel(coarse), "fallback_fbx_bytes": coarse.stat().st_size,
                   "fallback_fbx_sha256": L.sha256(coarse),
                   "fallback_maps": {k: {"file": L.rel(p), "sha256": L.sha256(p), "bytes": p.stat().st_size,
                                         "res": o["bake_res"]} for k, p in maps.items()},
                   "dense_cache_fbx": L.rel(dense), "seconds": round(time.time() - t0, 1)}
            check(m.name, "digest", digest, "pool")
            check(m.name, "dense_digest", dense_digest, "pool")
            pool.append(rec)
            print("TIMBER_POOL", m.name, rec["triangles"], rec["fallback_triangles"], rec["seconds"], flush=True)
            if keep is None:
                keep = (obj, m, objf, maps)
                obj.hide_set(True)
                objf.hide_set(True)
            else:
                drop(obj, objf)
    renders = lookdev(o, keep[0], keep[1], keep[2], keep[3], shared) if (o["lookdev"] and keep and not o["verify"]) else []
    evidence["digest_mismatches"] = mismatches
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "evidence.json").write_text(json.dumps(evidence, indent=1) + "\n")
    if o["verify"]:
        if mismatches:
            print("DOJO_TIMBERS_VERIFY_FAILED", ", ".join(mismatches), flush=True)
            sys.exit(1)
        print("DOJO_TIMBERS_VERIFIED", len(unique) + len(pool), flush=True)
        return
    manifest = {
        "schema_version": 1, "kit": "NyaagyuDojoTimbers", "generator": GEN, "generator_sha256": L.sha256(L.ROOT / GEN),
        "inputs": {p: L.sha256(L.ROOT / p) for p in INPUTS},
        "versions": {"blender": bpy.app.version_string, "numpy": np.__version__, "python": platform.python_version()},
        "digest": T.DIGEST_VERSION,
        "shared_textures": {k: {"file": L.rel(p), "sha256": L.sha256(p), "kind": kind}
                            for k, (p, kind) in shared_files.items()},
        "coverage": coverage, "placements": unique, "pool": pool, "lookdev_renders": renders,
        "notes": {
            "pivot": "floor level; room-facing -Y face at y -0.04, like SM_DojoColumn; Z along the column",
            "uv": "UV0 metric (1 = 1 m, along the perimeter and the length); UV1 unique atlas for the SM5 bake; "
                  "UVLogQ/UVLogZ the log frame (offset from the pith in metres; height and per-log seed)",
            "colors": "Masks (linear): R cavity, G wear, B soot, A knot",
            "placements": "SM6: one log per column placement, named by hall rect, wall and bay; dense FBX rebuilt "
                          "from the seeds into Local/ArtCache (not committed). coverage lists halls still without "
                          "their own logs",
            "pool": "SM5 (MAC tier): conventional fallbacks with checks in geometry and maps baked from their own logs",
            "renders": "Blender Cycles source renders, not Unreal captures",
        },
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print("DOJO_TIMBERS_READY", len(unique), "of", len(every), "placements with their own log;", len(pool), "pool",
          flush=True)


if __name__ == "__main__":
    main()
