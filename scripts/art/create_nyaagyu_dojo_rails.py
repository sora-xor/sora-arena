"""Tsumagizaka dojo hall: the bay rails as timbers cut from their own logs.

Run (Blender 5.2.2):
  blender -b --factory-startup --python scripts/art/create_nyaagyu_dojo_rails.py -- \
      [--halls ch01|all|none] [--pool N] [--lookdev] [--cpu] [--samples N] [--verify]

The rails that SM_DojoRail_* boxes stand for in each bay
(scripts/art/create_nyaagyu_dojo_kit.py RAILS), as horizontal members:

* nageshi (2.10-2.30 m) and cornice (6.78-7.00 m) run the full bay in front of
  the columns, quarter-sawn, so their faces show straight grain, and knot-free,
  as a formal hall's would be;
* koshi (0.88-1.00 m) and nuki (4.30-4.42 m) span between the columns'
  faces, flat-sawn, with a few small knots; the koshi, at hand height, wears
  along its top arris.

Placements (SM6) are named SM_DojoTimberRail_<Kind>_<rect>_S<side>_B<bay> after
the bay they sit in (scripts/art/dojo_hall_placements.py walks the same
layout), cut at that bay's exact length, and drawn by Nanite. The MAC pool
(SM5) is a few baked conventional rails per kind at the nominal 1.8 m bay,
which HallInterior stretches to fit; with neither, the box rail remains.
Outputs, digests and evidence follow create_nyaagyu_dojo_timbers.py, in
Content/SourceArt/Environment/NyaagyuDojoTimbers/Rails and
Local/ArtCache/NyaagyuDojoTimbers/Rails.
"""

from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import create_runtime_weapon_lib as L  # noqa: E402
import dojo_hall_placements as HP  # noqa: E402
import sora_timber_bake as TB  # noqa: E402
import sora_timber_lib as T  # noqa: E402

GEN = "scripts/art/create_nyaagyu_dojo_rails.py"
INPUTS = ("scripts/art/sora_timber_lib.py", "scripts/art/sora_timber_bake.py", "scripts/art/dojo_hall_placements.py",
          "scripts/art/create_runtime_weapon_lib.py")
OUT = L.ROOT / "Content/SourceArt/Environment/NyaagyuDojoTimbers/Rails"
CACHE = L.ROOT / "Local/ArtCache/NyaagyuDojoTimbers/Rails"
CH01_DOJO = (8000, -1300, 11600, 1300)
BAY_W = 1.80
COL = 0.24
SLAB0 = 0.030                 # kit: rails' back faces meet the wall here
SPACING = 0.005
# kind: (z0, z1, face_y, full_bay, cut, knots, checks, wear)
RAILS = {
    "Nageshi": (2.10, 2.30, -0.070, True, "quarter", (0, 1), (0, 2), 0.0),
    "Cornice": (6.78, 7.00, -0.080, True, "quarter", (0, 1), (0, 2), 0.0),
    "Koshi": (0.88, 1.00, -0.005, False, "flat", (0, 3), (0, 2), 0.004),
    "Nuki": (4.30, 4.42, 0.000, False, "flat", (0, 3), (0, 2), 0.0),
}
KOSHI_BAYS = {HP.PANEL, HP.RENJI, HP.RENJI_HIGH}


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"halls": "ch01", "pool": 3, "lookdev": False, "cpu": False, "samples": 96, "verify": False, "bake_res": 1024}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--halls", "--pool", "--samples", "--bake-res"):
            v = argv[i + 1]
            o[a[2:].replace("-", "_")] = v if a == "--halls" else int(v)
            i += 1
        elif a in ("--lookdev", "--cpu", "--verify"):
            o[a[2:]] = True
        i += 1
    return o


def rail_placements(halls):
    """(name, kind, rect, side, bay, length_m) for every rail in the given halls."""
    out = []
    for rect in halls:
        x0, y0, x1, y1 = rect
        counts = [max(1, HP.round_half_up(((x1 - x0) if s % 2 == 0 else (y1 - y0)) / (BAY_W * 100))) for s in range(4)]
        for side in range(4):
            count = counts[side]
            width = (((x1 - x0) if side % 2 == 0 else (y1 - y0)) / count) / 100.0
            index = 0
            while index < count:
                bay = HP.bay_for(side, index, count)
                if bay == HP.KAMIZA:
                    index += 4
                    continue
                for kind, (_, _, _, full, *_rest) in RAILS.items():
                    if kind == "Koshi" and bay not in KOSHI_BAYS:
                        continue
                    name = (f"SM_DojoTimberRail_{kind}_{HP.tag(x0)}_{HP.tag(y0)}_{HP.tag(x1)}_{HP.tag(y1)}"
                            f"_S{side}_B{index:02d}")
                    out.append({"name": name, "kind": kind, "rect": list(rect), "side": side, "bay": index,
                                "length_m": round(width if full else width - COL, 5), "seed": HP.seed_of(name)})
                index += 1
    return out


def rail_member(seed: int, kind: str, name: str, length: float) -> T.Member:
    z0, z1, face_y, full, cut, knots, checks, wear = RAILS[kind]
    height, depth = z1 - z0, SLAB0 - face_y
    rng = np.random.default_rng(seed)
    # Member frame: Z along the rail, X its height (+X is the underside once
    # laid down), Y its depth (-Y faces the room).
    log = T.make_log(seed, length, cut=cut, width=height, depth=depth, ring_width=rng.uniform(0.0014, 0.0022),
                     knot_count=knots, knot_size=(0.002, 0.005), check_count=checks, check_faces=(3,),
                     check_u={3: (-height * 0.3, height * 0.3)}, check_width=(0.0003, 0.0009),
                     check_depth=(0.002, 0.010), check_length=(0.08, 0.5))
    return T.Member(name=name, length=length, width=height, depth=depth, log=log,
                    finish=("planed", "hidden", "planed", "planed"), arris_r=(0.0018,) * 4,
                    # Corner 2 joins the top (-X) and the room face (-Y): the
                    # hand runs along it on the koshi.
                    arris_wear=(0.0, 0.0, wear, 0.0), handling=(length / 2, length * 2), dents=int(rng.integers(2, 8)),
                    dent_zone=(0.1, max(0.11, length - 0.1)), bow=rng.uniform(0.0003, 0.0010), soot_from=0.0,
                    spacing=SPACING, seed=seed)


def lay_down(obj, m: T.Member, kind: str):
    """Member frame -> bay frame: a proper rotation (no mirror), length along X,
    centred on the bay; the room face stays -Y; heights as in the kit."""
    z0, z1, face_y, *_ = RAILS[kind]
    yc = (face_y + SLAB0) / 2
    zc = (z0 + z1) / 2
    rot = Matrix(((0.0, 0.0, 1.0, -m.length / 2), (0.0, 1.0, 0.0, yc), (-1.0, 0.0, 0.0, zc), (0.0, 0.0, 0.0, 1.0)))
    obj.data.transform(rot)
    obj.data.update()


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
        if ob is not None:
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.meshes.remove(me)


def main():
    o = parse()
    scene = L.reset_scene()
    if o["cpu"]:
        scene.cycles.device = "CPU"
    committed = json.loads((OUT / "manifest.json").read_text()) if o["verify"] else None
    halls = {"all": sorted(HP.estate_halls()), "ch01": [CH01_DOJO], "none": []}[o["halls"]]
    every = rail_placements(sorted(HP.estate_halls()))
    todo = rail_placements(halls)
    evidence = {"generator": GEN, "blender": bpy.app.version_string,
                "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "fbx": {}}
    mismatches = []

    def check(name, key, digest, family):
        if committed is not None:
            want = next((r for r in committed[family] if r["asset"] == name), None)
            if want is None or want[key] != digest:
                mismatches.append(f"{name}.{key}")

    placements, pool = [], []
    for p in todo:
        t0 = time.time()
        m = rail_member(p["seed"], p["kind"], p["name"], p["length_m"])
        obj = T.to_blender(m.name, T.build_member(m), m)
        lay_down(obj, m, p["kind"])
        digest = T.canonical_digest(obj)
        path = export_fbx(obj, CACHE / "Placements" / f"{m.name}.fbx")
        evidence["fbx"][L.rel(path)] = {"sha256": L.sha256(path), "bytes": path.stat().st_size, "digest": digest}
        placements.append({**p, "asset": m.name, "triangles": len(obj.data.polygons), "digest": digest,
                           "ring_width_m": round(m.log.ring_width, 6), "cache_fbx": L.rel(path),
                           "seconds": round(time.time() - t0, 1)})
        check(m.name, "digest", digest, "placements")
        print("RAIL_PLACEMENT", m.name, placements[-1]["triangles"], placements[-1]["seconds"], flush=True)
        drop(obj)
    for kind in RAILS:
        z0, z1, face_y, full, *_ = RAILS[kind]
        length = BAY_W if full else BAY_W - COL
        for i in range(o["pool"]):
            t0 = time.time()
            name = f"SM_DojoTimberRail_MAC_{kind}_{i:02d}"
            m = rail_member(HP.seed_of(name), kind, name, length)
            mf = T.fallback_of(m)
            obj = T.to_blender(f"{name}_Dense", T.build_member(m), m)
            objf = T.to_blender(name, T.build_member(mf), mf)
            for ob in (obj, objf):
                lay_down(ob, m, kind)
            dense_digest, digest = T.canonical_digest(obj), T.canonical_digest(objf)
            dense = export_fbx(obj, CACHE / "PoolDense" / f"{name}_Dense.fbx")
            evidence["fbx"][L.rel(dense)] = {"sha256": L.sha256(dense), "bytes": dense.stat().st_size,
                                             "digest": dense_digest}
            coarse = OUT / "FBX" / f"{name}.fbx"
            if o["verify"]:
                # Committed fallbacks and maps stay byte-identical; only their
                # geometry is re-proved, and the evidence vouches for them as is.
                check(name, "digest", digest, "pool")
                check(name, "dense_digest", dense_digest, "pool")
                evidence["fbx"][L.rel(coarse)] = {"sha256": L.sha256(coarse), "bytes": coarse.stat().st_size,
                                                  "digest": digest}
                drop(obj, objf)
                continue
            export_fbx(objf, coarse)
            maps = TB.bake_fallback(obj, objf, OUT / "Maps", name.removeprefix("SM_"), res=o["bake_res"])
            evidence["fbx"][L.rel(coarse)] = {"sha256": L.sha256(coarse), "bytes": coarse.stat().st_size,
                                              "digest": digest}
            pool.append({"asset": name, "kind": kind, "seed": m.seed, "length_m": length,
                         "triangles": len(obj.data.polygons), "fallback_triangles": len(objf.data.polygons),
                         "dense_digest": dense_digest, "digest": digest, "ring_width_m": round(m.log.ring_width, 6),
                         "fallback_fbx": L.rel(coarse), "fallback_fbx_bytes": coarse.stat().st_size,
                         "fallback_fbx_sha256": L.sha256(coarse), "dense_cache_fbx": L.rel(dense),
                         "fallback_maps": {k: {"file": L.rel(p), "sha256": L.sha256(p), "bytes": p.stat().st_size,
                                               "res": o["bake_res"]} for k, p in maps.items()},
                         "seconds": round(time.time() - t0, 1)})
            check(name, "digest", digest, "pool")
            check(name, "dense_digest", dense_digest, "pool")
            print("RAIL_POOL", name, pool[-1]["triangles"], pool[-1]["fallback_triangles"], pool[-1]["seconds"],
                  flush=True)
            drop(obj, objf)
    evidence["digest_mismatches"] = mismatches
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "evidence.json").write_text(json.dumps(evidence, indent=1) + "\n")
    if o["verify"]:
        if mismatches:
            print("DOJO_RAILS_VERIFY_FAILED", ", ".join(mismatches), flush=True)
            sys.exit(1)
        print("DOJO_RAILS_VERIFIED", len(placements) + len(pool), flush=True)
        return
    built = {r["asset"] for r in placements}
    manifest = {
        "schema_version": 1, "kit": "NyaagyuDojoRails", "generator": GEN, "generator_sha256": L.sha256(L.ROOT / GEN),
        "inputs": {p: L.sha256(L.ROOT / p) for p in INPUTS},
        "versions": {"blender": bpy.app.version_string, "numpy": np.__version__, "python": platform.python_version()},
        "digest": T.DIGEST_VERSION,
        "coverage": {"estate_rail_placements": len(every), "with_own_log": len(built),
                     "halls_without_logs": sorted({tuple(p["rect"]) for p in every if p["name"] not in built})},
        "placements": placements, "pool": pool,
        "notes": {"frame": "bay frame of the kit: X along the wall centred on the bay, -Y the room, Z up from the floor",
                  "placements": "SM6 logs cut at their bay's exact length; drawn unscaled",
                  "pool": "SM5 MAC rails at the nominal 1.8 m bay; HallInterior stretches them to fit"},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print("DOJO_RAILS_READY", len(placements), "of", len(every), "rail placements;", len(pool), "pool", flush=True)


if __name__ == "__main__":
    main()
