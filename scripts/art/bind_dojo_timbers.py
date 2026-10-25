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

It refuses (exit 1) when a built log no longer fits the current layout. Each
built record must match its independently derived placement field by field:
name, kind, rect, side and bay, the seed, and for rails the length. A name may
be recorded only once. Otherwise the log is stale, for example its hall moved
or its bay changed kind, and the generator must be rerun. A hall without logs
only lowers the coverage: it draws the SM5 pool.

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
from collections import Counter
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
    """The rail kinds (with their full-bay flag), bay width, column width and koshi
    bays of create_nyaagyu_dojo_rails.py, read from its source (it needs Blender
    to import)."""
    found = {}
    for node in ast.parse(RAILS_GEN.read_text()).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            found[node.targets[0].id] = node.value
    kinds = [(kind, spec[3]) for kind, spec in ast.literal_eval(found["RAILS"]).items()]
    koshi = {getattr(HP, e.attr) for e in found["KOSHI_BAYS"].elts}
    return kinds, ast.literal_eval(found["BAY_W"]), ast.literal_eval(found["COL"]), koshi


def hall_rails(rect, layout):
    """Every rail in a hall, the way create_nyaagyu_dojo_rails.rail_placements lays
    it out: {name: {kind, rect, side, bay, length_m, seed}}."""
    kinds, bay_w, col, koshi = layout
    x0, y0, x1, y1 = rect
    counts = [max(1, HP.round_half_up(((x1 - x0) if s % 2 == 0 else (y1 - y0)) / (bay_w * 100))) for s in range(4)]
    rails = {}
    for side in range(4):
        count, index = counts[side], 0
        width = (((x1 - x0) if side % 2 == 0 else (y1 - y0)) / count) / 100.0
        while index < count:
            bay = HP.bay_for(side, index, count)
            if bay == HP.KAMIZA:
                index += 4
                continue
            for kind, full in kinds:
                if kind == "Koshi" and bay not in koshi:
                    continue
                name = (f"SM_DojoTimberRail_{kind}_{HP.tag(x0)}_{HP.tag(y0)}_{HP.tag(x1)}_{HP.tag(y1)}"
                        f"_S{side}_B{index:02d}")
                rails[name] = {"kind": kind, "rect": list(rect), "side": side, "bay": index,
                               "length_m": round(width if full else width - col, 5), "seed": HP.seed_of(name)}
            index += 1
    return rails


def hall_cols(rect):
    """Every column in a hall: {name: {kind, rect, side, bay, seed}}."""
    return {c["name"]: {"kind": c["kind"], "rect": list(rect), "side": c["side"], "bay": c["bay"], "seed": c["seed"]}
            for c in HP.hall_columns(rect)}


def records(manifest, label, stale):
    """The manifest's placement records by name; a name recorded twice is stale."""
    counts = Counter(r.get("asset") for r in manifest["placements"])
    for name, n in sorted(counts.items()):
        if n > 1:
            stale.append(f"{name}: {label} recorded {n} times")
    return {r.get("asset"): r for r in manifest["placements"]}


def mismatch(record, derived, fields):
    """The fields where a built record differs from its derived placement."""
    return [f"{f} {record.get(f)!r} (layout {derived[f]!r})" for f in fields if record.get(f) != derived[f]]


def layout_check(columns, rails, halls, layout):
    """Each current hall's coverage row, and every way a built log fails its layout."""
    stale = []
    built_cols = records(columns, "column", stale)
    built_rails = records(rails, "rail", stale)
    rows, used_cols, used_rails = [], set(), set()
    for rect, uses in sorted(halls.items()):
        cols, hall_rail = hall_cols(rect), hall_rails(rect, layout)
        own_cols = own_rails = 0
        for name, derived in cols.items():
            rec = built_cols.get(name)
            if rec is None:
                continue
            used_cols.add(name)
            wrong = mismatch(rec, derived, ("kind", "rect", "side", "bay", "seed"))
            if wrong:
                stale.append(f"{name}: built with {', '.join(wrong)}")
            else:
                own_cols += 1
        for name, derived in hall_rail.items():
            rec = built_rails.get(name)
            if rec is None:
                continue
            used_rails.add(name)
            wrong = mismatch(rec, derived, ("kind", "rect", "side", "bay", "length_m", "seed"))
            if rec.get("name", name) != name:
                wrong.append(f"name {rec.get('name')!r}")
            if wrong:
                stale.append(f"{name}: built with {', '.join(wrong)}")
            else:
                own_rails += 1
        here = {n for n, r in built_rails.items() if tuple(r.get("rect") or ()) == rect}
        if here and here != set(hall_rail):
            stale.append(f"hall {list(rect)}: its {len(here)} rail logs are not the {len(hall_rail)} rails it lays out")
        rows.append({"rect": list(rect), "zones": [f"{f}:{z}" for f, z in uses],
                     "columns": len(cols), "columns_with_own_log": own_cols,
                     "rails": len(hall_rail), "rails_with_own_log": own_rails})
    for name in sorted(set(built_cols) - used_cols):
        stale.append(f"{name}: no current estate hall has this column")
    for name in sorted(set(built_rails) - used_rails):
        stale.append(f"{name}: no current estate hall has this rail")
    return rows, stale


def bind(campaign_root: Path):
    columns, rails = (json.loads(p.read_text()) for p in MANIFESTS)
    rows, stale = layout_check(columns, rails, HP.estate_halls(campaign_root), rail_layout())
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
