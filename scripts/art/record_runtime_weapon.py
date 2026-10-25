#!/usr/bin/env python3
"""Record one runtime weapon's exact outputs in the runtime-weapons OWN manifest, and nothing else's.

  python3 scripts/art/record_runtime_weapon.py --weapon 18 --preflight
  python3 scripts/art/record_runtime_weapon.py --weapon 18 \
      --generator scripts/art/yumi_nigiri.py --generator scripts/art/yumi_ya.py [--check]

**Why.** Root's decision for the W18 rebuild (Codex, 2026-10-25): record W18
only. create_runtime_weapon_build_all.py records a weapon by rewriting the
whole manifest (Content/SourceArt/Weapons/Runtime/manifest.json) from the
files on disk. That would refresh every other weapon's hashes, including
entries that are stale on this branch and await their own review. Root keeps
its own validated ledger baseline, and merges only reviewed W18 records.

**What it replaces** is only the weapon's scope:
- its static outputs: every file under Runtime/<key>/, except *.blend1 and
  any subfolder holding its own manifest.ledger.json (W18_Yumi/Rig: the rig
  keeps its own OWN ledger);
- its renders: Runtime/Renders/<asset>_*.png for each of its assets.
Each is recorded with its size and SHA-256 as it is on disk now.

**What it keeps:** every other entry, exactly as it was and where it was,
stale or not. So also the document's other fields, except two:
- generator_scripts gains the weapon's own generators not yet listed;
- scoped_updates gains one entry: the weapon, the time, its generators
  (SHA-256), its derived inputs (the third-party files its build record
  names, SHA-256), the files recorded, and that this is OWN provenance
  (authorship and exact bytes), not geometric or visual admission.

**sources_manifest.json** must already list every derived input at its
current SHA-256, or the run fails. This adds none: build_all's ledger lookup
owns that list.

**Options:**
- --preflight, before a rebuild: every derived input of the weapon's current
  build record must be present and match the ledger, or exit 1. The Blender
  builders raise on a missing one, but here that is found before any job
  starts.
- --check writes nothing, and exits 1 if the weapon's entries differ from
  the files on disk.

Read-only apart from the manifest it rewrites; it never stages anything.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNTIME_REL = "Content/SourceArt/Weapons/Runtime"
PROVENANCE = ("OWN provenance: authorship and the exact bytes of these files. Not geometric or visual admission, "
              "which only root's review of the rebuilt originals can give.")


class RecordError(Exception):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def in_scope(rel_path: str, key: str, assets, own_ledger_dirs) -> bool:
    """Whether a manifest path belongs to this weapon's recorded scope."""
    base = f"{RUNTIME_REL}/{key}/"
    if rel_path.startswith(base):
        return not any(rel_path.startswith(d.rstrip("/") + "/") for d in own_ledger_dirs) and not rel_path.endswith(".blend1")
    name = rel_path.rsplit("/", 1)[-1]
    return rel_path.startswith(f"{RUNTIME_REL}/Renders/") and any(name.startswith(a + "_") and name.endswith(".png")
                                                                  for a in assets)


def own_ledger_dirs(root: Path, key: str):
    base = root / RUNTIME_REL / key
    return sorted(rel(root, p.parent) for p in base.rglob("manifest.ledger.json"))


def outputs(root: Path, key: str, assets):
    """The weapon's scope as it is on disk: [{file, bytes, sha256}], sorted by path."""
    dirs = own_ledger_dirs(root, key)
    runtime = root / RUNTIME_REL
    paths = set()
    for p in (runtime / key).rglob("*"):
        if p.is_file() and p.name not in ("manifest.json", "sources_manifest.json"):
            paths.add(p)
    for p in (runtime / "Renders").glob("*.png"):
        paths.add(p)
    out = []
    for p in sorted(paths, key=lambda q: rel(root, q)):
        r = rel(root, p)
        if in_scope(r, key, assets, dirs):
            out.append({"file": r, "bytes": p.stat().st_size, "sha256": sha256(p)})
    return out, dirs


def derived_inputs(root: Path, key: str):
    rec = json.loads((root / RUNTIME_REL / key / "build_record.json").read_text(encoding="utf-8"))
    if "textures" not in rec or "renders" not in rec:
        raise RecordError(f"{key}: its build record has no textures or renders; a geometry-only run is not a deliverable")
    return rec, sorted(rec.get("sources", []))


def preflight(root: Path, key: str, ledger_table: dict):
    """Problems with the weapon's derived inputs: each must exist and match the ledger."""
    _rec, sources = derived_inputs(root, key)
    problems = []
    for src in sources:
        p = root / src
        hit = ledger_table.get(src)
        if not p.is_file():
            problems.append(f"{src}: missing (link the raw CC0 cache at Local/ThirdPartyRaw before building)")
        elif hit is None:
            problems.append(f"{src}: no ledger record")
        elif sha256(p) != hit[0]:
            problems.append(f"{src}: differs from its ledger record")
    return problems


def replace_scope(files, new_entries, key, assets, dirs):
    """The manifest's files with this weapon's scope replaced. Every other entry is kept, unchanged and in its
    own order. The new entries are merged in by path, since the scope spans two parts of the sorted list (its
    renders under Renders/ and its own folder)."""
    kept = [e for e in files if not in_scope(e.get("file", ""), key, assets, dirs)]
    new_sorted = sorted(new_entries, key=lambda e: e["file"])
    out, i = [], 0
    for entry in kept:
        while i < len(new_sorted) and new_sorted[i]["file"] < entry.get("file", ""):
            out.append(new_sorted[i])
            i += 1
        out.append(entry)
    out.extend(new_sorted[i:])
    return out


def record(root: Path, wid: int, key: str, assets, generators, check=False, now=None):
    """Rewrite (or, with check, compare) the weapon's scope. Returns (changed, document)."""
    runtime = root / RUNTIME_REL
    manifest_path = runtime / "manifest.json"
    sources_path = runtime / "sources_manifest.json"
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    _rec, sources = derived_inputs(root, key)
    new_entries, dirs = outputs(root, key, assets)
    if not new_entries:
        raise RecordError(f"{key}: no outputs on disk")
    files = replace_scope(doc["files"], new_entries, key, assets, dirs)
    changed = files != doc["files"] or any(g not in doc["generator_scripts"] for g in generators)
    if check or not changed:
        return changed, doc                              # nothing to record: no duplicate scoped_updates entry
    listed = {e["file"]: e["sha256"] for e in json.loads(sources_path.read_text(encoding="utf-8"))["inputs"]}
    problems = [s for s in sources if s not in listed]
    for s in sources:
        p = root / s
        if s in listed and p.is_file() and sha256(p) != listed[s]:
            problems.append(f"{s} (changed)")
    if problems:
        raise RecordError(f"{key}: derived inputs not in sources_manifest.json at their current SHA-256: {problems}")
    gens = []
    for g in generators:
        p = root / g
        if not p.is_file():
            raise RecordError(f"generator {g} not found")
        gens.append({"path": g, "sha256": sha256(p)})
    doc["files"] = files
    for g in generators:
        if g not in doc["generator_scripts"]:
            doc["generator_scripts"] = sorted(doc["generator_scripts"] + [g])
    for w in doc.get("weapons", []):
        if w.get("id") == wid:
            w["assets"] = sorted(assets)
    stamp = now or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    doc.setdefault("scoped_updates", []).append({
        "weapon": wid, "key": key, "recorded_at_utc": stamp, "generators": gens,
        "derived_from": [{"path": s, "sha256": listed[s]} for s in sources],
        "files": [e["file"] for e in new_entries], "own_ledgers_kept_apart": dirs,
        "scope": PROVENANCE})
    manifest_path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return True, doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--weapon", type=int, required=True)
    ap.add_argument("--generator", action="append", default=[],
                    help="the weapon's own generators besides its build record's builder and library")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--preflight", action="store_true")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(HERE))
    import create_runtime_weapon_specs as S  # noqa: E402

    spec = S.WEAPONS.get(a.weapon)
    if spec is None:
        print(f"no weapon {a.weapon}", file=sys.stderr)
        return 1
    if spec.get("status") == "blockout":
        print(f"{spec['key']} is held back (blockout): not recorded", file=sys.stderr)
        return 1
    assets = [spec["asset"]] + list(spec.get("extra_assets", []))
    try:
        if a.preflight:
            import create_runtime_weapon_build_all as BA  # noqa: E402

            problems = preflight(ROOT, spec["key"], BA.ledger_lookup())
            if problems:
                print("RECORD_PREFLIGHT_FAILED:\n  " + "\n  ".join(problems), file=sys.stderr)
                return 1
            print(f"RECORD_PREFLIGHT_OK {spec['key']}: every derived input present and as the ledger records it")
            return 0
        rec = json.loads((ROOT / RUNTIME_REL / spec["key"] / "build_record.json").read_text(encoding="utf-8"))
        generators = sorted({rec["builder"], rec["library"], "scripts/art/create_runtime_weapon_specs.py",
                             "scripts/art/create_runtime_weapon_validation.py", *a.generator})
        changed, _doc = record(ROOT, a.weapon, spec["key"], assets, generators, check=a.check)
    except RecordError as exc:
        print(f"RECORD_FAILED: {exc}", file=sys.stderr)
        return 1
    if a.check:
        print(f"RECORD_CHECK {spec['key']}: the record {'would change (files or generators)' if changed else 'matches'}")
        return 1 if changed else 0
    print(f"RECORDED {spec['key']}: its scope only; every other entry kept")
    return 0


if __name__ == "__main__":
    sys.exit(main())
