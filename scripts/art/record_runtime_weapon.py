#!/usr/bin/env python3
"""Record one runtime weapon's exact outputs in the runtime-weapons OWN manifest, and nothing else's.

  python3 scripts/art/record_runtime_weapon.py --weapon 18 --preflight
  python3 scripts/art/record_runtime_weapon.py --weapon 18 \
      --generator scripts/art/yumi_nigiri.py --generator scripts/art/yumi_ya.py [--check] \
      [--metric-before <metric_report.json archived before the validation> --metric-log <its log> \
       --metric-validator-exit <its real exit> --metric-expected-failures 3,11,13,16]

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

**Provenance is checked first, every run.** Before anything is recorded or
reported as matching (root's adversarial probes of a5a966c):
- every derived input must exist and match its sources_manifest.json SHA-256
  (this adds none: build_all's ledger lookup owns that list);
- every generator must exist.
Otherwise it fails. And a record "matches" only when the latest scoped
update for the weapon names the same generators, derived inputs (both by
SHA-256) and files. A stale or absent provenance record never matches.

**The metric report's entry** (root's W18-scoped metadata exception, Codex,
2026-10-25). The manifest records Runtime/metric_report.json, a global file
outside any weapon's scope. The targeted validation rewrites it, changing
only the weapon's row and the summary. With the four --metric options, and
only then, that one entry is updated:
- check_scoped_validation runs again here, on the report archived before the
  validation and the report now, with the weapon's build record, the
  validation's log and its real exit. Any refusal fails the record;
- the manifest's entry must be the report before, or already the report now
  (a rerun). Anything else fails: it is never refreshed from disk alone;
- the scoped update records the exception: the report before and after,
  the validator's real exit, the failing rows and W18's row before and after.
Without them the entry is kept as it is, like every other entry outside the
scope.

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
METRIC_REL = f"{RUNTIME_REL}/metric_report.json"
VALIDATOR_REL = "scripts/art/create_runtime_weapon_validation.py"
METRIC_RULE = ("root's W18-scoped metadata exception (Codex, 2026-10-25): the targeted validation changed "
               "metric_report.json only in this weapon's row and the summary, as check_scoped_validation found again "
               "here; this one entry is updated, and no other weapon's entry or output is refreshed")
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


def current_provenance(root: Path, sources, listed: dict, generators):
    """(generators, derived inputs) as they are now, each by SHA-256; RecordError if any is missing,
    unlisted or off its sources_manifest.json hash."""
    problems, derived, gens = [], [], []
    for src in sources:
        p = root / src
        if src not in listed:
            problems.append(f"{src}: not in sources_manifest.json")
        elif not p.is_file():
            problems.append(f"{src}: missing")
        else:
            digest = sha256(p)
            if digest != listed[src]:
                problems.append(f"{src}: differs from its sources_manifest.json hash")
            else:
                derived.append({"path": src, "sha256": digest})
    for g in generators:
        p = root / g
        if not p.is_file():
            problems.append(f"generator {g}: missing")
        else:
            gens.append({"path": g, "sha256": sha256(p)})
    if problems:
        raise RecordError("provenance: " + "; ".join(problems))
    return gens, derived


def latest_scoped(doc: dict, wid: int):
    entries = [u for u in doc.get("scoped_updates", []) if u.get("weapon") == wid]
    return entries[-1] if entries else None


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


def digest(data: bytes) -> dict:
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def metric_exception(root: Path, wid: int, key: str, doc: dict, metric: dict):
    """(the metric report's new entry, the exception's record), or RecordError. ``metric``: before (the report
    archived before the validation), log, validator_exit and expected_failures."""
    import check_scoped_validation as G  # noqa: E402
    import create_runtime_weapon_specs as S  # noqa: E402

    try:
        before = Path(metric["before"]).read_bytes()
        after = (root / METRIC_REL).read_bytes()
        rec_bytes = (root / RUNTIME_REL / key / "build_record.json").read_bytes()
        log = Path(metric["log"]).read_text(encoding="utf-8", errors="replace")
        validator = (root / VALIDATOR_REL).read_text(encoding="utf-8")
    except OSError as exc:
        raise RecordError(f"the metric report exception: {exc}") from None
    try:
        result = G.compare(before, after, wid, metric["expected_failures"], log, metric["validator_exit"],
                           S.WEAPONS[wid], json.loads(rec_bytes.decode("utf-8")), validator, S.MIN_TEXEL_DENSITY)
    except G.ScopeError as exc:
        raise RecordError(f"the metric report exception: the scoped gate refuses: {exc}") from None
    entry = next((e for e in doc["files"] if e.get("file") == METRIC_REL), None)
    if entry is None:
        raise RecordError(f"the metric report exception: the manifest has no {METRIC_REL} entry")
    was = {"bytes": entry.get("bytes"), "sha256": entry.get("sha256")}
    if was not in (digest(before), digest(after)):
        raise RecordError(f"the metric report exception: the manifest's entry {was} is neither the report before the "
                          f"validation {digest(before)} nor the report now {digest(after)}")
    return {"file": METRIC_REL, **digest(after)}, {
        "file": METRIC_REL, "before": digest(before), "after": digest(after),
        "validator_exit": result["validator_exit"], "failing_rows": result["failing_rows"],
        "row_before": result["row_before"], "row_after": result["row_after"],
        "checks_new_since_the_reviewed_row": result["checks_new_since_the_reviewed_row"],
        "build_record_sha256": digest(rec_bytes)["sha256"], "validator_sha256": result["validator_sha256"],
        "rule": METRIC_RULE}


def record(root: Path, wid: int, key: str, assets, generators, check=False, now=None, metric=None):
    """Rewrite (or, with check, compare) the weapon's scope. Returns (changed, document).

    Provenance is validated first, in both modes: no success, and no "matches", on a missing or changed
    input or generator. ``metric`` asks for the metric report's exception (see the module)."""
    runtime = root / RUNTIME_REL
    manifest_path = runtime / "manifest.json"
    sources_path = runtime / "sources_manifest.json"
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    _rec, sources = derived_inputs(root, key)
    listed = {e["file"]: e["sha256"] for e in json.loads(sources_path.read_text(encoding="utf-8"))["inputs"]}
    gens, derived = current_provenance(root, sources, listed, generators)
    new_entries, dirs = outputs(root, key, assets)
    if not new_entries:
        raise RecordError(f"{key}: no outputs on disk")
    files = replace_scope(doc["files"], new_entries, key, assets, dirs)
    exception = None
    if metric is not None:
        metric_entry, exception = metric_exception(root, wid, key, doc, metric)
        files = [metric_entry if e.get("file") == METRIC_REL else e for e in files]
    latest = latest_scoped(doc, wid)
    now_record = {"generators": gens, "derived_from": derived, "files": [e["file"] for e in new_entries]}
    if exception is not None:
        now_record["metadata_exception"] = exception
    provenance_matches = latest is not None and all(latest.get(k) == v for k, v in now_record.items())
    changed = (files != doc["files"] or any(g not in doc["generator_scripts"] for g in generators)
               or not provenance_matches)
    if check or not changed:
        return changed, doc                              # nothing to record: no duplicate scoped_updates entry
    doc["files"] = files
    for g in generators:
        if g not in doc["generator_scripts"]:
            doc["generator_scripts"] = sorted(doc["generator_scripts"] + [g])
    for w in doc.get("weapons", []):
        if w.get("id") == wid:
            w["assets"] = sorted(assets)
    stamp = now or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    doc.setdefault("scoped_updates", []).append({
        "weapon": wid, "key": key, "recorded_at_utc": stamp, **now_record,
        "own_ledgers_kept_apart": dirs, "scope": PROVENANCE})
    manifest_path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return True, doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--weapon", type=int, required=True)
    ap.add_argument("--generator", action="append", default=[],
                    help="the weapon's own generators besides its build record's builder and library")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--metric-before", type=Path, help="metric_report.json as archived before the validation")
    ap.add_argument("--metric-log", type=Path, help="the targeted validation's log")
    ap.add_argument("--metric-validator-exit", type=int, help="the validation's real exit")
    ap.add_argument("--metric-expected-failures", help="comma-separated weapon ids failing before it")
    a = ap.parse_args(argv)
    given = [x is not None for x in (a.metric_before, a.metric_log, a.metric_validator_exit,
                                     a.metric_expected_failures)]
    if any(given) and not all(given):
        print("the metric report exception needs all four --metric options", file=sys.stderr)
        return 1
    metric = None
    if all(given):
        metric = {"before": a.metric_before, "log": a.metric_log, "validator_exit": a.metric_validator_exit,
                  "expected_failures": [int(x) for x in a.metric_expected_failures.split(",")]}
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
        changed, _doc = record(ROOT, a.weapon, spec["key"], assets, generators, check=a.check, metric=metric)
    except RecordError as exc:
        print(f"RECORD_FAILED: {exc}", file=sys.stderr)
        return 1
    if a.check:
        print(f"RECORD_CHECK {spec['key']}: the record "
              f"{'would change (files, generators or provenance)' if changed else 'matches, provenance included'}")
        return 1 if changed else 0
    print(f"RECORDED {spec['key']}: its scope only"
          + (", and the metric report's entry by the W18-scoped exception" if metric else "") + "; every other entry kept")
    return 0


if __name__ == "__main__":
    sys.exit(main())
