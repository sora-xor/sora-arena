"""The six v2 pilot members: the same chapter-1 logs as v1, rebuilt with v2 relief.

Numpy only (the Blender driver is create_nyaagyu_dojo_timbers_pilot.py). Each
member is the first chapter-1 placement of its kind in the frozen manifests,
with the same seed, log and finish, renamed ``<v1 name>_V2``. The v1 recipes
come from timber_density_study.py, whose tests prove they rebuild the
committed triangle counts.

Where geometric raised grain goes follows one physical rule. It is geometry
wherever a player can come within about a metre; there a 1.4-2.4 mm ring is
several pixels. Further off it is under a pixel, Nanite would simplify it
away, and the shader carries it. The rule gives:

* **Columns:** the close-view band, 0.6-2.0 m. Every visible face of an open
  column; the room face and front strips of a wall column. An indoor
  latewood relief of 25-45 um.
* **Nageshi (2.1-2.3 m):** the room face, the whole length, 25-40 um.
* **Koshi (0.88-1.00 m):** the hand-worn top at 0.10-0.18 mm and the room face
  at 30-60 um, the whole length.
* **Cornice (6.8-7.0 m):** none; never within a metre, so shader only.
* **Nuki (4.3 m):** chona-adzed (scalloped) underside and room face, with
  scallops 0.9-2.3 mm deep, visible from the floor. A planed top.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sora_timber_lib as T  # noqa: E402
import sora_timber_v2 as V  # noqa: E402
import timber_density_study as D  # noqa: E402

ROOT = HERE.parents[1]
KIT = ROOT / "Content/SourceArt/Environment/NyaagyuDojoTimbers"
INDOOR = (25e-6, 45e-6)
# Each geometry version writes a namespace of its own. These are as frozen as
# the v1 kit and its cache, each archived read-only:
# - run 1, the v2 pilot (verified from the frozen 82869a4 inputs);
# - the v2.1 pilot (made at 4481327).
NAMESPACE = "NyaagyuDojoTimbersV22Pilot"
OUT = ROOT / "Local/ArtCache" / NAMESPACE
RUN1 = ROOT / "Local/ArtCache/NyaagyuDojoTimbersV2Pilot"
RUN_V21 = ROOT / "Local/ArtCache/NyaagyuDojoTimbersV21Pilot"
FROZEN = (KIT, ROOT / "Local/ArtCache/NyaagyuDojoTimbers", RUN1, RUN_V21)


def guard(path: Path) -> Path:
    """``path`` if it lies in the pilot namespace; refuses anything else,
    above all the frozen v1 kit, its baseline cache and the archived run 1."""
    p = Path(path).resolve()
    out = OUT.resolve()
    if p != out and out not in p.parents:
        raise ValueError(f"pilot: refusing to write outside {OUT}: {p}")
    for frozen in FROZEN:
        f = frozen.resolve()
        if p == f or f in p.parents:
            raise ValueError(f"pilot: refusing to write into the frozen baseline: {p}")
    return Path(path)


def _twist(seed: int) -> float:
    return float(0.001 + 0.002 * T.hash01(seed, 4242))


def pilot_members(length_cap: float | None = None):
    """[(MemberV2, family, kind, v1 record)] for the six pilot members.

    ``length_cap`` shortens every member (tests only); the real pilot leaves it None."""
    columns = json.loads((KIT / "manifest.json").read_text())["placements"]
    rails = json.loads((KIT / "Rails/manifest.json").read_text())["placements"]
    out = []
    for kind in ("wall", "open"):
        rec = next(p for p in columns if p["kind"] == kind)
        m1 = D.column_member(rec["seed"], kind, rec["asset"])
        faces = (0, 2, 3) if kind == "wall" else (0, 1, 2, 3)
        m = V.to_v2(m1, name=rec["asset"] + "_V2", corner_samples=6, grain={f: INDOOR for f in faces},
                    grain_zone=(0.6, 2.0), twist=_twist(rec["seed"]))
        out.append((m, "column", kind, rec))
    grain = {"Nageshi": {3: (25e-6, 40e-6)}, "Cornice": {}, "Koshi": {2: (100e-6, 180e-6), 3: (30e-6, 60e-6)}, "Nuki": {}}
    for kind in ("Nageshi", "Cornice", "Koshi", "Nuki"):
        rec = next(p for p in rails if p["kind"] == kind)
        m1 = D.rail_member(rec["seed"], kind, rec["asset"], rec["length_m"])
        finish = ("adze", "hidden", "planed", "adze") if kind == "Nuki" else m1.finish
        m = V.to_v2(m1, name=rec["asset"] + "_V2", corner_samples=6, finish=finish, grain=grain[kind],
                    grain_zone=None, twist=0.0)
        out.append((m, "rail", kind, rec))
    if length_cap:
        import dataclasses
        out = [(dataclasses.replace(m, length=min(m.length, length_cap), dent_zone=(0.05, min(m.length, length_cap) - 0.05),
                                    grain_zone=None if m.grain_zone is None else (0.05, min(m.length, length_cap) - 0.05)),
                fam, kind, rec) for m, fam, kind, rec in out]
    return out


def budget():
    """Triangles of each pilot member, dense and fallback (sampling only, no displacement)."""
    arrays = V.shared_arrays()
    rows = []
    for m, fam, kind, rec in pilot_members():
        S = V.sample(m, arrays)
        Sf = V.sample(V.fallback(m), arrays)
        rows.append({"asset": m.name, "family": fam, "kind": kind, "v1_triangles": rec["triangles"],
                     "v2_triangles": 2 * int(S.x.size), "v2_fallback_triangles": 2 * int(Sf.x.size)})
    return rows


def checks():
    """Every pilot mesh's check_mesh result, and the room face's relief visibility,
    as docs/art-direction/data/timber_pilot_checks.json records them."""
    arrays = V.shared_arrays()
    rows = []
    for m, fam, kind, rec in pilot_members():
        B = V.build(m, arrays)
        mf = V.fallback(m)
        Bf = V.build(mf, arrays)
        dense, fb = V.check_mesh(B, m), V.check_mesh(Bf, mf)
        rows.append({"asset": m.name, "kind": kind, "v1_triangles": rec["triangles"],
                     "triangles": dense["metrics"]["triangles"], "fallback_triangles": fb["metrics"]["triangles"],
                     "ok": dense["ok"] and fb["ok"], "dense_checks": dense["metrics"], "fallback_checks": fb["metrics"],
                     "failures": dense["failures"] + fb["failures"],
                     "visibility": V.relief_visibility(B, m, face=2 if kind == "Koshi" else 3)})
    return {"pilot": rows, "digest": V.DIGEST_VERSION, "wander": [V.WANDER_RINGS_PER_UNIT, V.WANDER_AMPLITUDE],
            "uv_contract": V.UV_CONTRACT}


if __name__ == "__main__":
    if "--checks" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--checks") + 1])
        data = checks()
        out.write_text(json.dumps(data, indent=1) + "\n")
        print(out, "ok" if all(r["ok"] for r in data["pilot"]) else "FAILURES")
    else:
        for row in budget():
            print(json.dumps(row))
