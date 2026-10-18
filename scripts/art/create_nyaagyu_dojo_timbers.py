"""Tsumagizaka dojo hall: unique timbers cut from their own logs (Nanite source).

Run (Blender 5.2.2):
  blender -b --factory-startup --python scripts/art/create_nyaagyu_dojo_timbers.py -- \
      [--out DIR] [--columns N] [--open-columns N] [--lookdev] [--samples N] [--no-export]

Replaces the box SM_DojoColumn with one-off columns (sora_timber_lib): each is
a boxed-heart hinoki column, 24 cm square and 7 m tall like the kit's, with the
same pivot (floor level; room-facing -Y face 4 cm proud of the bay line, back
face in the wall). ``wall`` columns detail the room face and the 6 cm of each
side that shows in front of the infill; ``open`` columns, for door and engawa
bays, detail every face. Each variant records its seed, so the dense mesh is
reproducible; the manifest records triangles, bounds and file hashes.

Outputs default to Saved/DojoTimbers/ (not source-controlled) until the kit's
storage is agreed. Look-dev renders are Blender source renders, labelled as such.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import create_runtime_weapon_lib as L  # noqa: E402
import sora_prop_lib as PL  # noqa: E402
import sora_timber_bake as TB  # noqa: E402
import sora_timber_lib as T  # noqa: E402
import sora_timber_lookdev as LD  # noqa: E402

GEN = "scripts/art/create_nyaagyu_dojo_timbers.py"
COL = 0.24
WALL_H = 7.0
COL_CENTRE_Y = 0.08          # kit: column spans y -0.04 .. 0.20, room at -Y
INFILL_Y = 0.02              # kit infill plane
SIDE_VISIBLE = COL / 2 - (INFILL_Y - (COL_CENTRE_Y - COL / 2)) + 0.01   # u extent from the front corner


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"out": L.ROOT / "Saved/DojoTimbers", "columns": 1, "open_columns": 0, "lookdev": False, "samples": 96,
         "export": True, "seed0": 2101, "bake_res": 2048, "bake": True}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--out":
            o["out"] = Path(argv[i + 1])
            i += 1
        elif a == "--columns":
            o["columns"] = int(argv[i + 1])
            i += 1
        elif a == "--open-columns":
            o["open_columns"] = int(argv[i + 1])
            i += 1
        elif a == "--samples":
            o["samples"] = int(argv[i + 1])
            i += 1
        elif a == "--seed0":
            o["seed0"] = int(argv[i + 1])
            i += 1
        elif a == "--lookdev":
            o["lookdev"] = True
        elif a == "--cpu":
            o["cpu"] = True
        elif a == "--quick":
            o["quick"] = True
        elif a == "--no-bake":
            o["bake"] = False
        elif a == "--bake-res":
            o["bake_res"] = int(argv[i + 1])
            i += 1
        elif a == "--no-export":
            o["export"] = False
        i += 1
    return o


def column_member(seed: int, kind: str, index: int) -> T.Member:
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
    # Unreal loads variants by index (SoraWorldBuilderDojoHall.cpp); the seed is
    # recorded in the manifest.
    return T.Member(name=f"SM_DojoTimberColumn_{kind.capitalize()}_{index:02d}", length=WALL_H, width=COL, depth=COL,
                    log=log, finish=finish, visible=vis, arris_r=(0.0025,) * 4, arris_wear=wear,
                    handling=(rng.uniform(1.05, 1.3), 0.5), dents=int(rng.integers(16, 34)), dent_zone=(0.35, 2.0),
                    bow=rng.uniform(0.0006, 0.0018), seed=seed, offset=(0.0, COL_CENTRE_Y, 0.0))


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


def lookdev(o, obj, m: T.Member, B, fallback_obj, maps, shared):
    scene = bpy.context.scene
    out = o["out"] / "LookDev" / m.name
    LD.stage(infill_y=INFILL_Y)
    wood = LD.timber_material(f"LD_{m.name}", "column_fukiurushi", shared)
    wood_fb = LD.timber_material(f"LD_{m.name}_Fallback", "column_fukiurushi", shared, maps) if maps else None
    clay = LD.clay_material()
    obj.data.materials.clear()
    obj.data.materials.append(wood)
    if fallback_obj is not None:
        fallback_obj.data.materials.clear()
        fallback_obj.data.materials.append(wood_fb or wood)
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
    plan = [("Studio", "Mid"), ("Studio", "Close"), ("GoldenHour", "Full"), ("GoldenHour", "Mid"),
            ("Raking", "Mid"), ("Raking", "Close"), ("Lantern", "Mid"), ("Raking", "Mid", "Clay"),
            ("Raking", "Close", "Clay"), ("Raking", "Close", "Fallback"), ("GoldenHour", "Mid", "Fallback")]
    if o.get("quick"):
        plan = [("Raking", "Mid"), ("Raking", "Close"), ("Raking", "Close", "Clay"), ("Raking", "Close", "Fallback")]
        for s in shots.values():
            s["size"] = (s["size"][0] * 3 // 4, s["size"][1] * 3 // 4)
    files = []
    for entry in plan:
        rig, shot = entry[0], entry[1]
        material = entry[2] if len(entry) > 2 else "Wood"
        if material == "Fallback" and fallback_obj is None:
            continue
        # "Wood" is the Nanite path (dense mesh, vertex masks); "Fallback" the
        # SM5 path (coarse mesh, baked NormalDX and Masks on UV1).
        show_fb = material == "Fallback"
        obj.hide_render = show_fb
        if fallback_obj is not None:
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
                      "seconds": round(time.time() - t0, 1)})
        print("TIMBER_RENDER", L.rel(path), files[-1]["seconds"], flush=True)
    obj.data.materials[0] = wood
    obj.hide_render = False
    return files


def main():
    o = parse()
    scene = L.reset_scene()
    if o.get("cpu"):
        # Cycles' Metal pipeline compile can hang on macOS 27 (observed on the
        # M2 Ultra, 2026-10-18); the CPU path renders the same image.
        scene.cycles.device = "CPU"
    o["out"].mkdir(parents=True, exist_ok=True)
    shared_files = T.shared_textures(o["out"] / "Shared")
    shared = {k: p for k, (p, _) in shared_files.items()}
    shared_rec = {k: {"file": L.rel(p), "sha256": L.sha256(p), "kind": kind} for k, (p, kind) in shared_files.items()}
    records = []
    kinds = ["wall"] * o["columns"] + ["open"] * o["open_columns"]
    first = None
    for i, kind in enumerate(kinds):
        seed = o["seed0"] + i
        t0 = time.time()
        m = column_member(seed, kind, kinds[:i].count(kind))
        B = T.build_member(m)
        mf = T.fallback_of(m)
        Bf = T.build_member(mf)
        t1 = time.time()
        obj = T.to_blender(f"{m.name}_HiRes", B, m)
        objf = T.to_blender(m.name, Bf, mf)
        t2 = time.time()
        rec = {"asset": m.name, "kind": kind, "seed": seed, "length_m": m.length, "section_m": [m.width, m.depth],
               "pivot": "floor; room face (-Y) at y -0.04, like SM_DojoColumn", "finish": list(m.finish),
               "vertices": len(obj.data.vertices), "triangles": len(obj.data.polygons),
               "fallback_vertices": len(objf.data.vertices), "fallback_triangles": len(objf.data.polygons),
               "knots": len(m.log.knots), "checks": len(m.log.checks), "ring_width_m": round(m.log.ring_width, 5),
               "build_seconds": round(t1 - t0, 2), "mesh_seconds": round(t2 - t1, 2)}
        if o["export"]:
            dense = export_fbx(obj, o["out"] / "FBX" / f"{m.name}_HiRes.fbx")
            coarse = export_fbx(objf, o["out"] / "FBX" / f"{m.name}.fbx")
            rec.update({"fbx": L.rel(dense), "fbx_bytes": dense.stat().st_size, "fbx_sha256": L.sha256(dense),
                        "fallback_fbx": L.rel(coarse), "fallback_fbx_bytes": coarse.stat().st_size,
                        "fallback_fbx_sha256": L.sha256(coarse), "export_seconds": round(time.time() - t2, 2)})
        maps = None
        if o["bake"]:
            t3 = time.time()
            maps = TB.bake_fallback(obj, objf, o["out"] / "Maps", m.name.removeprefix("SM_"), res=o["bake_res"])
            rec["fallback_maps"] = {k: {"file": L.rel(p), "sha256": L.sha256(p), "res": o["bake_res"]}
                                    for k, p in maps.items()}
            rec["bake_seconds"] = round(time.time() - t3, 1)
        records.append(rec)
        print("TIMBER_MEMBER", json.dumps(rec), flush=True)
        if first is None:
            first = (obj, m, B, objf, maps)
        else:
            for ob in (obj, objf):
                ob.hide_render = True
                ob.hide_set(True)
    renders = lookdev(o, *first, shared) if o["lookdev"] and first else []
    manifest = {"schema_version": 1, "kit": "NyaagyuDojoTimbers", "generator": GEN,
                "generator_sha256": L.sha256(L.ROOT / GEN),
                "library_sha256": {"sora_timber_lib": L.sha256(HERE / "sora_timber_lib.py"),
                                   "sora_timber_lookdev": L.sha256(HERE / "sora_timber_lookdev.py"),
                                   "sora_timber_bake": L.sha256(HERE / "sora_timber_bake.py")},
                "blender": bpy.app.version_string, "shared_textures": shared_rec, "members": records,
                "lookdev_renders": renders,
                "notes": {"uv": "UV0 metric (1 = 1 m, along the perimeter and the length); UV1 unique atlas for the "
                                "SM5 fallback bake; UVLogQ/UVLogZ log frame for the ring material",
                          "colors": "Masks (linear): R cavity, G wear, B soot, A knot",
                          "renders": "Blender Cycles source look-dev, not Unreal"}}
    (o["out"] / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print("DOJO_TIMBERS_READY", len(records), flush=True)


if __name__ == "__main__":
    main()
