"""Blender look-dev of a committed dojo timber column: Nanite path vs SM5 fallback.

Run (Blender 5.2.2):
  blender -b --factory-startup --python scripts/art/render_dojo_timbers_lookdev.py -- [--quick] [--samples N] [--cpu]

Rebuilds MAC pool column 0 in memory from the committed manifest's seed
(create_nyaagyu_dojo_timbers.column_member), checks both canonical digests
against the manifest, and renders it with the committed shared textures and
baked fallback maps:

* "Nanite": the dense log with its vertex masks;
* "Fallback": the SM5 mesh with its baked NormalDX/Masks;
* "Clay": the dense geometry alone.

It writes only Content/SourceArt/Environment/NyaagyuDojoTimbers/Renders/ and
Renders/renders.json, never the meshes, maps or manifest. These are Blender
Cycles source renders, not Unreal captures.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import create_nyaagyu_dojo_timbers as D  # noqa: E402
import create_runtime_weapon_lib as L  # noqa: E402
import sora_timber_lib as T  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"quick": "--quick" in argv, "cpu": "--cpu" in argv, "lookdev": True, "verify": False,
         "samples": int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 96}
    scene = L.reset_scene()
    if o["cpu"]:
        scene.cycles.device = "CPU"
    manifest = json.loads((D.OUT / "manifest.json").read_text())
    rec = next(r for r in manifest["pool"] if r["asset"].endswith("MAC_Wall_00"))
    m = D.column_member(rec["seed"], rec["kind"], rec["asset"])
    obj = T.to_blender(f"{m.name}_Dense", T.build_member(m), m)
    mf = T.fallback_of(m)
    objf = T.to_blender(m.name, T.build_member(mf), mf)
    dense, coarse = T.canonical_digest(obj), T.canonical_digest(objf)
    if dense != rec["dense_digest"] or coarse != rec["digest"]:
        sys.exit(f"{m.name}: rebuilt geometry differs from the committed manifest")
    maps = {k: L.ROOT / v["file"] for k, v in rec["fallback_maps"].items()}
    shared = {k: L.ROOT / v["file"] for k, v in manifest["shared_textures"].items()}
    files = D.lookdev(o, obj, m, objf, maps, shared)
    out = D.OUT / "Renders" / "renders.json"
    out.write_text(json.dumps({"subject": m.name, "seed": m.seed, "dense_digest": dense, "digest": coarse,
                               "manifest_generator_sha256": manifest["generator_sha256"],
                               "renderer": "Blender Cycles (CPU)" if o["cpu"] else "Blender Cycles",
                               "renders": files}, indent=1) + "\n")
    print("TIMBER_LOOKDEV_READY", len(files), flush=True)


if __name__ == "__main__":
    main()
