"""Tsumagizaka dojo hall: hinoki floor tiles whose every board is cut from its own log.

Run (Blender 5.2.2):
  blender -b --factory-startup --python scripts/art/create_nyaagyu_dojo_floor.py -- \
      [--tiles N] [--pool N] [--cpu] [--verify]

The kit's floor tile (create_nyaagyu_dojo_kit.py floor_tile): 3.6 x 2.6 m, 18
rows of boards 14.4 cm wide and 3 cm thick running along X, butt joints
staggered by a random first cut of 0.9, 1.8 or 2.7 m. Each board here is a
flat-sawn hinoki member from its own seeded log (sora_timber_lib), laid with
its room face up:

* the top face is detailed at 5 mm, the 8 mm of each edge that shows in the
  gaps between boards finer, the underside coarse;
* the top arrises are eased and worn; boards cup across their width
  (flat-sawn boards do), sit a fraction of a millimetre proud of or below their
  neighbours and tilt slightly; shallow checks and small knots;
* gaps of 0.5-1.2 mm between boards show dark.

Unlike the columns and rails, floor boards are unique within each tile, but
the tiles repeat across a hall (a unique log for each of about 1,800 boards
per hall would be some 250 M triangles). Variety across the hall comes from
the variants, their placement and the material.

Sets, as for the columns: SM_DojoTimberFloor_NN (Nanite; dense, rebuilt from
seeds into Local/ArtCache) and SM_DojoTimberFloor_MAC_NN (SM5; coarse boards
with the NormalDX/Masks of their own dense logs, committed). Outputs, digests
and evidence follow create_nyaagyu_dojo_timbers.py, under
Content/SourceArt/Environment/NyaagyuDojoTimbers/Floor.
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

GEN = "scripts/art/create_nyaagyu_dojo_floor.py"
INPUTS = ("scripts/art/sora_timber_lib.py", "scripts/art/sora_timber_bake.py", "scripts/art/dojo_hall_placements.py",
          "scripts/art/create_runtime_weapon_lib.py")
OUT = L.ROOT / "Content/SourceArt/Environment/NyaagyuDojoTimbers/Floor"
CACHE = L.ROOT / "Local/ArtCache/NyaagyuDojoTimbers/Floor"
TILE = (3.6, 2.6)
ROWS = 18
THICK = 0.030
EDGE_SHOWN = 0.008            # the part of a board's edge visible in the gap
SPACING = 0.005


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"tiles": 12, "pool": 4, "cpu": False, "verify": False, "bake_res": 2048}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--tiles", "--pool", "--bake-res"):
            o[a[2:].replace("-", "_")] = int(argv[i + 1])
            i += 1
        elif a in ("--cpu", "--verify"):
            o[a[2:]] = True
        i += 1
    return o


def board_layout(seed: int):
    """[(row, x0, x1, gap_lo, gap_hi)] for one tile: boards along X, joints staggered."""
    rng = np.random.default_rng(seed)
    sx, sy = TILE
    pitch = sy / ROWS
    boards = []
    for r in range(ROWS):
        x = -sx / 2
        segs = [float(rng.choice([0.9, 1.8, 2.7]))] + [3.6] * 3
        for ln in segs:
            x1 = min(sx / 2, x + ln)
            if x1 - x < 0.05:
                break
            boards.append((r, x, x1, rng.uniform(0.0005, 0.0012), rng.uniform(0.0005, 0.0012)))
            x = x1
            if x >= sx / 2 - 1e-6:
                break
    return boards, pitch


def board_member(seed: int, name: str, length: float, width: float) -> T.Member:
    rng = np.random.default_rng(seed)
    log = T.make_log(seed, length, cut="flat", width=width, depth=THICK, ring_width=rng.uniform(0.0016, 0.0026),
                     knot_count=(0, 3), knot_size=(0.002, 0.005), check_count=(0, 2), check_faces=(3,),
                     check_u={3: (-width * 0.3, width * 0.3)}, check_width=(0.0002, 0.0007),
                     check_depth=(0.0008, 0.003), check_length=(0.06, 0.5))
    # Member frame: Z along the board, X across it, Y through it (-Y faces up
    # once laid). Face 0 (+X) and face 2 (-X) are the edges: only their top
    # 8 mm show in the gaps.
    return T.Member(name=name, length=length, width=width, depth=THICK, log=log,
                    finish=("planed", "hidden", "planed", "planed"),
                    visible=((-THICK / 2, -THICK / 2 + EDGE_SHOWN), None, (THICK / 2 - EDGE_SHOWN, THICK / 2), None),
                    arris_r=(0.0012, 0.0012, 0.0016, 0.0016), arris_wear=(0.0, 0.0, 0.0012, 0.0012),
                    handling=(length / 2, length * 3), dents=int(rng.integers(3, 10)),
                    dent_zone=(0.05, max(0.06, length - 0.05)), bow=rng.uniform(0.0002, 0.0008), soot_from=99.0,
                    spacing=SPACING, hidden_spacing=0.03, seed=seed)


def lay_board(obj, m: T.Member, cx: float, cy: float, rng):
    """Member frame -> tile frame by a proper rotation: length along X, room
    face up, top at z 0; then cup across the width, offset and tilt."""
    rot = Matrix(((0.0, 0.0, 1.0, cx - m.length / 2), (-1.0, 0.0, 0.0, cy), (0.0, -1.0, 0.0, -THICK / 2),
                  (0.0, 0.0, 0.0, 1.0)))
    me = obj.data
    me.transform(rot)
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3).astype(np.float64)
    across = np.clip((co[:, 1] - cy) / (m.width / 2), -1, 1)
    along = (co[:, 0] - (cx - m.length / 2)) / m.length
    cup = rng.uniform(0.0002, 0.0007) * across ** 2                     # edges a little high
    proud = rng.normal(0.0, 0.00018)                                    # against its neighbours
    tilt = rng.normal(0.0, 0.00025) * across + rng.normal(0.0, 0.0002) * (along - 0.5)
    co[:, 2] += cup + proud + tilt
    me.vertices.foreach_set("co", co.astype(np.float32).ravel())
    me.update()


def tile(name: str, seed: int):
    """Build every board of one tile; returns the joined Blender object."""
    boards, pitch = board_layout(seed)
    objs = []
    rng = np.random.default_rng(seed + 1)
    for k, (r, x0, x1, g0, g1) in enumerate(boards):
        width = pitch - (g0 + g1) / 2
        cy = -TILE[1] / 2 + (r + 0.5) * pitch + (g0 - g1) / 4
        bseed = HP.seed_of(f"{name}_R{r:02d}_S{k:02d}")
        m = board_member(bseed, f"{name}_R{r:02d}_S{k:02d}", (x1 - x0) - 0.0006, width)
        ob = T.to_blender(m.name, T.build_member(m), m)
        lay_board(ob, m, (x0 + x1) / 2, cy, rng)
        objs.append(ob)
    joined = L.join(objs, name)
    joined.data.name = name
    return joined, len(boards)


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


def main():
    o = parse()
    scene = L.reset_scene()
    if o["cpu"]:
        scene.cycles.device = "CPU"
    committed = json.loads((OUT / "manifest.json").read_text()) if o["verify"] else None
    evidence = {"generator": GEN, "blender": bpy.app.version_string,
                "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "fbx": {}}
    mismatches = []

    def check(name, key, digest, family):
        if committed is not None:
            want = next((r for r in committed[family] if r["asset"] == name), None)
            if want is None or want[key] != digest:
                mismatches.append(f"{name}.{key}")

    tiles, pool = [], []
    for i in range(o["tiles"]):
        t0 = time.time()
        name = f"SM_DojoTimberFloor_{i:02d}"
        obj, n = tile(name, HP.seed_of(name))
        digest = T.canonical_digest(obj)
        path = export_fbx(obj, CACHE / "Tiles" / f"{name}.fbx")
        evidence["fbx"][L.rel(path)] = {"sha256": L.sha256(path), "bytes": path.stat().st_size, "digest": digest}
        tiles.append({"asset": name, "seed": HP.seed_of(name), "boards": n, "triangles": len(obj.data.polygons),
                      "digest": digest, "cache_fbx": L.rel(path), "ring_width_m": 0.0021,
                      "seconds": round(time.time() - t0, 1)})
        check(name, "digest", digest, "tiles")
        print("FLOOR_TILE", name, n, tiles[-1]["triangles"], tiles[-1]["seconds"], flush=True)
        me = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(me)
    for i in range(o["pool"]):
        t0 = time.time()
        name = f"SM_DojoTimberFloor_MAC_{i:02d}"
        seed = HP.seed_of(name)
        # A pool tile's boards: dense for the bake, coarse for the runtime.
        boards, pitch = board_layout(seed)
        rng_d, rng_f = np.random.default_rng(seed + 1), np.random.default_rng(seed + 1)
        dense, coarse = [], []
        for k, (r, x0, x1, g0, g1) in enumerate(boards):
            width = pitch - (g0 + g1) / 2
            cy = -TILE[1] / 2 + (r + 0.5) * pitch + (g0 - g1) / 4
            m = board_member(HP.seed_of(f"{name}_R{r:02d}_S{k:02d}"), f"{name}_R{r:02d}_S{k:02d}", (x1 - x0) - 0.0006, width)
            mf = T.fallback_of(m)
            od = T.to_blender(m.name + "_D", T.build_member(m), m)
            of = T.to_blender(m.name, T.build_member(mf), mf)
            lay_board(od, m, (x0 + x1) / 2, cy, rng_d)
            lay_board(of, m, (x0 + x1) / 2, cy, rng_f)
            dense.append(od)
            coarse.append(of)
        od = L.join(dense, name + "_Dense")
        of = L.join(coarse, name)
        dense_digest, digest = T.canonical_digest(od), T.canonical_digest(of)
        dpath = export_fbx(od, CACHE / "PoolDense" / f"{name}_Dense.fbx")
        evidence["fbx"][L.rel(dpath)] = {"sha256": L.sha256(dpath), "bytes": dpath.stat().st_size, "digest": dense_digest}
        cpath = OUT / "FBX" / f"{name}.fbx"
        if o["verify"]:
            check(name, "digest", digest, "pool")
            check(name, "dense_digest", dense_digest, "pool")
            evidence["fbx"][L.rel(cpath)] = {"sha256": L.sha256(cpath), "bytes": cpath.stat().st_size, "digest": digest}
        else:
            export_fbx(of, cpath)
            maps = TB.bake_fallback(od, of, OUT / "Maps", name.removeprefix("SM_"), res=o["bake_res"])
            evidence["fbx"][L.rel(cpath)] = {"sha256": L.sha256(cpath), "bytes": cpath.stat().st_size, "digest": digest}
            pool.append({"asset": name, "seed": seed, "boards": len(boards), "triangles": len(od.data.polygons),
                         "fallback_triangles": len(of.data.polygons), "dense_digest": dense_digest, "digest": digest,
                         "ring_width_m": 0.0021, "fallback_fbx": L.rel(cpath), "fallback_fbx_bytes": cpath.stat().st_size,
                         "fallback_fbx_sha256": L.sha256(cpath), "dense_cache_fbx": L.rel(dpath),
                         "fallback_maps": {k: {"file": L.rel(p), "sha256": L.sha256(p), "bytes": p.stat().st_size,
                                               "res": o["bake_res"]} for k, p in maps.items()},
                         "seconds": round(time.time() - t0, 1)})
            print("FLOOR_POOL", name, pool[-1]["triangles"], pool[-1]["fallback_triangles"], pool[-1]["seconds"],
                  flush=True)
        for ob in (od, of):
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.meshes.remove(me)
    evidence["digest_mismatches"] = mismatches
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "evidence.json").write_text(json.dumps(evidence, indent=1) + "\n")
    if o["verify"]:
        if mismatches:
            print("DOJO_FLOOR_VERIFY_FAILED", ", ".join(mismatches), flush=True)
            sys.exit(1)
        print("DOJO_FLOOR_VERIFIED", len(tiles) + o["pool"], flush=True)
        return
    manifest = {
        "schema_version": 1, "kit": "NyaagyuDojoFloor", "generator": GEN, "generator_sha256": L.sha256(L.ROOT / GEN),
        "inputs": {p: L.sha256(L.ROOT / p) for p in INPUTS},
        "versions": {"blender": bpy.app.version_string, "numpy": np.__version__, "python": platform.python_version()},
        "digest": T.DIGEST_VERSION, "tiles": tiles, "pool": pool,
        "notes": {"frame": "tile frame of the kit: 3.6 x 2.6 m centred, boards along X, top at z 0",
                  "uniqueness": "each board of a tile is its own log; tiles repeat across a hall",
                  "renders": "none yet"},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print("DOJO_FLOOR_READY", len(tiles), "tiles;", len(pool), "pool", flush=True)


if __name__ == "__main__":
    main()
