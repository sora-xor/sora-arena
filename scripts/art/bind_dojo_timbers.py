#!/usr/bin/env python3
"""Bind the dojo timber kit to the campaign chapter files it is placed from.

  python3 scripts/art/bind_dojo_timbers.py [--check] [--campaign-root DIR]

Every timber placement is named and seeded from its estate hall's rect in
Content/Data/campaign/chapter_*.json (dojo_hall_placements.py). The kit's
manifests pin the generator scripts but not those chapter files. This writes
Content/SourceArt/Environment/NyaagyuDojoTimbers/campaign_binding.json, which
pins them:

* the SHA-256 of every chapter file read and of both kit manifests;
* every current estate hall: its rect, the zones that use it, and how many of
  its columns and rails have their own log;
* the estate coverage: placements with their own log, of all placements.

It refuses (exit 1) when a built log no longer fits the current layout, for
example its hall moved or its bay changed kind. Such a log is stale, and the
generator must be rerun. A hall without logs only lowers the coverage: it draws
the SM5 pool.

The importer (scripts/unreal/import_nyaagyu_dojo_timbers.py) requires this
binding to match the current chapter files and manifests, so a campaign edit
fails the import until this script has been rerun.

Pure Python: no Blender, no Unreal.

* ``--check`` writes nothing, and fails if the committed binding is out of date.
* ``--campaign-root`` reads the chapter files of another checkout and only
  prints the result.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dojo_hall_placements as HP  # noqa: E402

ROOT = HP.ROOT
KIT = ROOT / "Content/SourceArt/Environment/NyaagyuDojoTimbers"
MANIFESTS = (KIT / "manifest.json", KIT / "Rails/manifest.json")
OUT = KIT / "campaign_binding.json"
RAILS_GEN = HERE / "create_nyaagyu_dojo_rails.py"
SCHEMA = "sora-dojo-timber-campaign-binding-v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def rail_layout():
    """The rail kinds, bay width and koshi bays of create_nyaagyu_dojo_rails.py,
    read from its source (it needs Blender to import)."""
    found = {}
    for node in ast.parse(RAILS_GEN.read_text()).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            found[node.targets[0].id] = node.value
    kinds = list(ast.literal_eval(found["RAILS"]).keys())
    bay_w = ast.literal_eval(found["BAY_W"])
    koshi = {getattr(HP, e.attr) for e in found["KOSHI_BAYS"].elts}
    return kinds, bay_w, koshi


def hall_rails(rect, layout):
    """Every rail name in a hall, the way create_nyaagyu_dojo_rails.rail_placements
    lays them out. A disagreement with a built hall fails the binding."""
    kinds, bay_w, koshi = layout
    x0, y0, x1, y1 = rect
    counts = [max(1, HP.round_half_up(((x1 - x0) if s % 2 == 0 else (y1 - y0)) / (bay_w * 100))) for s in range(4)]
    names = []
    for side in range(4):
        count, index = counts[side], 0
        while index < count:
            bay = HP.bay_for(side, index, count)
            if bay == HP.KAMIZA:
                index += 4
                continue
            for kind in kinds:
                if kind == "Koshi" and bay not in koshi:
                    continue
                names.append(f"SM_DojoTimberRail_{kind}_{HP.tag(x0)}_{HP.tag(y0)}_{HP.tag(x1)}_{HP.tag(y1)}"
                             f"_S{side}_B{index:02d}")
            index += 1
    return names


def bind(campaign_root: Path):
    columns, rails = (json.loads(p.read_text()) for p in MANIFESTS)
    halls = HP.estate_halls(campaign_root)
    layout = rail_layout()
    built_cols = {p["asset"]: p for p in columns["placements"]}
    built_rails = {p["asset"]: p for p in rails["placements"]}
    stale, rows = [], []
    used_cols, used_rails = set(), set()
    for rect, uses in sorted(halls.items()):
        cols = HP.hall_columns(rect)
        rail_names = hall_rails(rect, layout)
        own_cols = own_rails = 0
        for col in cols:
            rec = built_cols.get(col["name"])
            if rec is None:
                continue
            used_cols.add(col["name"])
            if (rec["kind"], rec["seed"], rec["side"], rec["bay"]) != (col["kind"], col["seed"], col["side"], col["bay"]):
                stale.append(f"{col['name']}: built as a {rec['kind']} column, the layout now has a {col['kind']} one")
            else:
                own_cols += 1
        here = {n for n, r in built_rails.items() if tuple(r["rect"]) == rect}
        if here and here != set(rail_names):
            stale.append(f"hall {list(rect)}: its {len(here)} rail logs are not the {len(rail_names)} rails it lays out")
        own_rails = len(here & set(rail_names))
        used_rails |= here
        rows.append({"rect": list(rect), "zones": [f"{f}:{z}" for f, z in uses],
                     "columns": len(cols), "columns_with_own_log": own_cols,
                     "rails": len(rail_names), "rails_with_own_log": own_rails})
    for name in sorted(set(built_cols) - used_cols):
        stale.append(f"{name}: no current estate hall has this column")
    for name in sorted(set(built_rails) - used_rails):
        stale.append(f"{name}: no current estate hall has this rail")
    chapters = sorted((campaign_root / "Content/Data/campaign").glob("chapter_*.json"))
    doc = {
        "schema": SCHEMA,
        "binder": rel(Path(__file__)),
        "binder_sha256": sha(Path(__file__)),
        "manifests": {rel(p): sha(p) for p in MANIFESTS},
        "campaign": {p.relative_to(campaign_root).as_posix(): sha(p) for p in chapters},
        "halls": rows,
        "coverage": {
            "columns": sum(r["columns"] for r in rows),
            "columns_with_own_log": sum(r["columns_with_own_log"] for r in rows),
            "rails": sum(r["rails"] for r in rows),
            "rails_with_own_log": sum(r["rails_with_own_log"] for r in rows),
        },
    }
    return doc, stale


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="write nothing; fail if the committed binding is stale")
    ap.add_argument("--campaign-root", type=Path, default=ROOT,
                    help="checkout whose chapter files to read (prints only, unless it is this one)")
    a = ap.parse_args(argv)
    root = a.campaign_root.resolve()
    doc, stale = bind(root)
    cov = doc["coverage"]
    for row in doc["halls"]:
        print(f"hall {row['rect']}: columns {row['columns_with_own_log']}/{row['columns']}, rails "
              f"{row['rails_with_own_log']}/{row['rails']}; {', '.join(row['zones'])}")
    print(f"estate: columns {cov['columns_with_own_log']}/{cov['columns']}, rails "
          f"{cov['rails_with_own_log']}/{cov['rails']} with their own log")
    if stale:
        print("\n".join(f"STALE: {s}" for s in stale), file=sys.stderr)
        print(f"DOJO_TIMBERS_BINDING_STALE {len(stale)}: rerun the timber and rail generators", file=sys.stderr)
        return 1
    text = json.dumps(doc, indent=1) + "\n"
    if a.check:
        ok = OUT.is_file() and OUT.read_text() == text
        print("DOJO_TIMBERS_BINDING_CURRENT" if ok else "DOJO_TIMBERS_BINDING_OUTDATED: rerun without --check")
        return 0 if ok else 1
    if root != ROOT:
        print(f"DOJO_TIMBERS_BINDING_PREVIEW for {root} (nothing written)")
        return 0
    OUT.write_text(text)
    print(f"DOJO_TIMBERS_BOUND {rel(OUT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
