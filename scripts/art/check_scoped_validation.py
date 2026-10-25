#!/usr/bin/env python3
"""Gate one weapon's targeted metric validation on its own row, beside the validator's real exit.

  python3 scripts/art/check_scoped_validation.py --weapon 18 --expected-failures 3,11,13,16 \
      --before <metric_report.json archived before the run> \
      --after Content/SourceArt/Weapons/Runtime/metric_report.json \
      --build-record Content/SourceArt/Weapons/Runtime/W18_Yumi/build_record.json \
      --log <the validation's log> --validator-exit <its real exit> --out <result.json>

**Why.** create_runtime_weapon_validation.py --only 18 validates W18 alone,
but it rewrites the whole metric_report.json and exits from the accumulated
summary of every row. The four blockout weapons' rows (03, 11, 13, 16) fail
and are carried over unchanged, so the run exits 1 whatever W18 does.

**Root's rule for the W18 rebuild** (Codex, 2026-10-25): keep the validator's
real exit and its full report, and gate the new W18 row separately. The
narrow expected-baseline exception holds only if all of these hold, and any
other result stops the sequence.

- **W18's row, recomputed, not trusted.** Root's probes of fe74f78 showed
  the row's own pass bits accept a row cut to one check, a row relabelled
  W19, a tolerance widened to 100, and an infinite measurement. So the row
  is checked against what the validator would have written:
  - **Identity:** id 18 (an integer) and the spec's key, W18_Yumi.
  - **Inventory:** exactly the checks validate() appends for this weapon,
    unique and in its order. For each asset of the build record (which must
    be the spec's assets): UV0 overlap, FBX bounds parity and LOD triangles.
    Then the normal tilt, when the record has a Normal map, and the texel
    density, when it has one. Then every spec check.
  - **Fixed metadata:** each check's keys are exactly the validator's, and
    everything but the measurement equals the authored value. Expected,
    tolerance and the LOD0 budget come from the validator's rules and the
    spec (create_runtime_weapon_specs.py); method, basis and source from the
    spec's checks; minima from the validator's MIN_NORMAL_TILT and the spec's
    MIN_TEXEL_DENSITY. A check the reviewed row before the run also holds
    must have the same metadata there.
  - **The validator's rules:** its source must still state each rule this
    gate recomputes (RULES, whitespace collapsed), or the gate refuses.
  - **Measurements:** finite numbers, never a boolean, NaN or infinity.
    Overlap and parity are not negative; coverage is a share; LOD triangles
    are three positive integers.
  - **Pass, recomputed:** each check passes by the validator's own rule on
    its recorded measurement. The validator records spec and overlap
    measurements rounded to 5 decimals, so |measured - expected| may exceed
    its own by half that step (ROUNDED_SLACK), and by no more. The pass bits
    must say true as well.
  - **Against the build record:** each LOD triangle list is the record's,
    and the texel density its p05, rounded as the validator rounds it.
  - **No errors.**
- **The same failures:** the failing rows before and after the run are
  exactly the expected pre-run failures.
- **Every other row byte-identical:** the report after the run is exactly the
  report before it, with only W18's row and the summary replaced, serialised
  as the validator writes it. The report before must reproduce its own bytes
  that way, or nothing can be compared.
- **The summary:** before and after, its weapon count is the report's row
  count and its pass count the rows that pass. Its counts, validator and
  keys are unchanged; only its time and Blender version may differ.
- **The log:** it validated W18 alone, named it PASS, and printed the
  summary's count, with no Python traceback.
- **The exit:** the validator's real exit is what its own summary implies
  (1 while any row fails). The result records it beside the scoped result,
  never in place of it.

Writes --out (created exclusively) and prints SCOPED_VALIDATION_OK, or
SCOPED_VALIDATION_FAILED naming every problem (exit 1). Reads nothing else
and writes nothing else.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VALIDATOR = ROOT / "scripts/art/create_runtime_weapon_validation.py"
SPECS = ROOT / "scripts/art/create_runtime_weapon_specs.py"
VALIDATED = re.compile(r"^\[validate\] (\S+): (PASS|FAIL)$", re.M)

# The validator's own statements of each rule this gate recomputes (create_runtime_weapon_validation.py, whitespace
# collapsed). If its source no longer says one of them, the gate cannot recompute that check, and refuses.
RULES = (
    'res["checks"].append({"name": f"{asset}_uv0_overlap", "measured": round(over, 5), "expected": 0.0, '
    '"tol": 0.004, "pass": over <= 0.004, "coverage": round(cov, 4)})',
    'res["checks"].append({"name": f"{asset}_fbx_bounds_parity_m", "measured": d, "expected": 0.0, "tol": 1e-4, '
    '"pass": d <= 1e-4})',
    'budget = spec["lod0_tri_budget"] if asset == spec["asset"] else spec["lod0_tri_budget"]',
    'ok = t[0] <= budget and all(b_ < a_ for a_, b_ in zip(t[:-1], t[1:])) and len(t) == 3',
    'res["checks"].append({"name": f"{asset}_lod_triangles", "measured": t, "budget_lod0": budget, "pass": ok})',
    'chk = {"name": "normal_tilt_mean", "measured": round(t_all, 4), "expected_min": MIN_NORMAL_TILT, '
    '"pass": t_all >= MIN_NORMAL_TILT}',
    'chk["covered_texels_mean"] = round(float(sub[coverage].mean()), 4)',
    'res["checks"].append({"name": "texel_density_p05_px_per_m", "measured": round(dens["p05"], 1), '
    '"expected_min": S.MIN_TEXEL_DENSITY, "pass": dens["p05"] >= S.MIN_TEXEL_DENSITY})',
    'ok = abs(val - chk["expected"]) <= chk["tol"]',
    'res["checks"].append({"name": chk["name"], "method": chk["method"], "measured": round(val, 5), '
    '"expected": chk["expected"], "tol": chk["tol"], "basis": chk["basis"], "source": chk["source"], "pass": ok})',
    'res["pass"] = not res["errors"] and all(c.get("pass") for c in res["checks"])',
    'report["summary"] = {"weapons": len(allw), "passed": sum(1 for r in allw.values() if r.get("pass")),',
)
UV_OVERLAP_TOL = 0.004          # as RULES state them
PARITY_TOL = 1e-4
ROUNDED_SLACK = 5e-6            # half the 5th decimal the validator rounds spec and overlap measurements to
FLOAT_SLACK = 1e-12
ROW_KEYS = {"id", "key", "checks", "errors", "pass"}
MEASURED = {"measured", "pass", "coverage", "covered_texels_mean"}
KEYS = {
    "uv0": {"name", "measured", "expected", "tol", "pass", "coverage"},
    "parity": {"name", "measured", "expected", "tol", "pass"},
    "lods": {"name", "measured", "budget_lod0", "pass"},
    "tilt": {"name", "measured", "expected_min", "pass", "covered_texels_mean"},
    "density": {"name", "measured", "expected_min", "pass"},
    "spec": {"name", "method", "measured", "expected", "tol", "basis", "source", "pass"},
}


class ScopeError(Exception):
    pass


def serialise(doc) -> bytes:
    """As create_runtime_weapon_validation.py writes metric_report.json."""
    return (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def digest(data: bytes) -> dict:
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def failing(doc):
    return sorted(int(k) for k, r in doc["weapons"].items() if not (isinstance(r, dict) and r.get("pass") is True))


def validator_constants(text: str) -> dict:
    """The validator's MIN_NORMAL_TILT, once its source is seen to state every rule in RULES."""
    norm = re.sub(r"\s+", " ", text)
    missing = [r for r in RULES if r not in norm]
    if missing:
        raise ScopeError(f"the validator no longer states {len(missing)} rules this gate recomputes: {missing}")
    m = re.search(r"^MIN_NORMAL_TILT = ([0-9.eE+-]+)$", text, re.M)
    if not m:
        raise ScopeError("the validator states no MIN_NORMAL_TILT")
    return {"min_normal_tilt": float(m.group(1))}


def expected_checks(spec: dict, rec: dict, min_normal_tilt: float, min_texel_density: float):
    """[(kind, fixed metadata)]: the checks validate() appends for this weapon, in its order."""
    assets = list(rec.get("assets", {}))
    want = [spec["asset"]] + list(spec.get("extra_assets", []))
    if sorted(assets) != sorted(want):
        raise ScopeError(f"the build record's assets {assets} are not the spec's {want}")
    out = []
    for a in assets:
        out += [("uv0", {"name": f"{a}_uv0_overlap", "expected": 0.0, "tol": UV_OVERLAP_TOL}),
                ("parity", {"name": f"{a}_fbx_bounds_parity_m", "expected": 0.0, "tol": PARITY_TOL}),
                ("lods", {"name": f"{a}_lod_triangles", "budget_lod0": spec["lod0_tri_budget"]})]
    if rec.get("textures", {}).get("Normal"):
        out.append(("tilt", {"name": "normal_tilt_mean", "expected_min": min_normal_tilt}))
    if rec.get("texel_density_px_per_m"):
        out.append(("density", {"name": "texel_density_p05_px_per_m", "expected_min": min_texel_density}))
    for c in spec["checks"]:
        out.append(("spec", {k: c[k] for k in ("name", "method", "expected", "tol", "basis", "source")}))
    return out


def check_problems(c: dict, kind: str, fixed: dict, rec: dict):
    """Problems with one check of the new row, by the validator's own rule for its kind."""
    name = fixed["name"]
    if set(c) != KEYS[kind]:
        return [f"{name}: keys {sorted(c)}, not the validator's {sorted(KEYS[kind])}"]
    problems = []
    got = {k: v for k, v in c.items() if k not in MEASURED}
    if got != fixed:
        problems.append(f"{name}: metadata {got} is not the authored {fixed}")
    if c["pass"] is not True:
        problems.append(f"{name}: its pass bit is {c['pass']!r}")
    m = c["measured"]
    if kind == "lods":
        asset = name[: -len("_lod_triangles")]
        recorded = [lod.get("triangles") for lod in rec["assets"][asset].get("lods", [])]
        if not (isinstance(m, list) and len(m) == 3 and all(type(t) is int and t > 0 for t in m)):
            problems.append(f"{name}: {m!r} is not three positive triangle counts")
        elif not (all(b < a for a, b in zip(m, m[1:])) and m[0] <= fixed["budget_lod0"]):
            problems.append(f"{name}: {m} is not decreasing within the LOD0 budget {fixed['budget_lod0']}")
        if m != recorded:
            problems.append(f"{name}: {m!r}, but the build record says {recorded}")
        return problems
    if not finite(m):
        return problems + [f"{name}: the measurement {m!r} is not a finite number"]
    if kind in ("uv0", "parity", "spec"):
        if kind != "spec" and m < 0:
            problems.append(f"{name}: the measurement {m} is negative")
        slack = (0.0 if kind == "parity" else ROUNDED_SLACK) + FLOAT_SLACK
        if not abs(m - fixed["expected"]) <= fixed["tol"] + slack:
            problems.append(f"{name}: {m} is outside {fixed['expected']} +/- {fixed['tol']}")
    elif not m >= fixed["expected_min"]:
        problems.append(f"{name}: {m} is below {fixed['expected_min']}")
    if kind == "uv0" and not (finite(c["coverage"]) and 0.0 <= c["coverage"] <= 1.0):
        problems.append(f"{name}: coverage {c['coverage']!r} is not a share")
    if kind == "tilt" and not (finite(c["covered_texels_mean"]) and c["covered_texels_mean"] >= 0.0):
        problems.append(f"{name}: covered_texels_mean {c['covered_texels_mean']!r} is not a finite tilt")
    if kind == "density":
        want = round(rec["texel_density_px_per_m"]["p05"], 1)
        if m != want:
            problems.append(f"{name}: {m}, but the build record's p05 rounds to {want}")
    return problems


def row_problems(row, before_row, weapon: int, spec: dict, rec: dict, constants: dict, min_texel_density: float):
    """Problems with the new row, recomputed from the authored rules and the build record, never its pass bits
    alone."""
    if not isinstance(row, dict):
        return [f"row {weapon} is not a record"]
    problems = []
    if set(row) != ROW_KEYS:
        problems.append(f"row {weapon}'s keys are {sorted(row)}, not {sorted(ROW_KEYS)}")
    if not (type(row.get("id")) is int and row["id"] == weapon and row.get("key") == spec["key"]):
        problems.append(f"row {weapon} is not W{weapon:02d}: id {row.get('id')!r}, key {row.get('key')!r}, "
                        f"the spec's {spec['key']!r}")
    if row.get("errors") != []:
        problems.append(f"row {weapon} has errors {row.get('errors')!r}")
    if row.get("pass") is not True:
        problems.append(f"row {weapon}'s pass bit is {row.get('pass')!r}")
    checks = row.get("checks")
    if not (isinstance(checks, list) and all(isinstance(c, dict) for c in checks)):
        return problems + [f"row {weapon}'s checks are not a list of records"]
    names = [c.get("name") for c in checks]
    dup = sorted({n for n in names if names.count(n) > 1}, key=str)
    if dup:
        problems.append(f"row {weapon} repeats the checks {dup}")
    want = expected_checks(spec, rec, constants["min_normal_tilt"], min_texel_density)
    if names != [f["name"] for _, f in want]:
        return problems + [f"row {weapon}'s checks {names} are not the validator's inventory "
                           f"{[f['name'] for _, f in want]}"]
    for c, (kind, fixed) in zip(checks, want):
        problems += check_problems(c, kind, fixed, rec)
    if isinstance(before_row, dict):
        mine = {c["name"]: c for c in checks}
        for b in before_row.get("checks", []):
            a = mine.get(b.get("name"))
            if a is None:
                problems.append(f"the reviewed row's check {b.get('name')!r} is not in the validator's inventory")
            elif {k: v for k, v in a.items() if k not in MEASURED} != {k: v for k, v in b.items() if k not in MEASURED}:
                problems.append(f"{b['name']}: its metadata differs from the reviewed row's")
    return problems


def _report(data: bytes, name: str):
    try:
        doc = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ScopeError(f"the {name} report is unreadable ({type(exc).__name__}: {exc})") from None
    if not (isinstance(doc, dict) and set(doc) == {"weapons", "summary"} and isinstance(doc["weapons"], dict)
            and isinstance(doc["summary"], dict)):
        raise ScopeError(f"the {name} report is not a record of weapons and a summary")
    return doc


def summary_problems(doc: dict, name: str):
    s, rows = doc["summary"], doc["weapons"]
    passed = sum(1 for r in rows.values() if isinstance(r, dict) and r.get("pass") is True)
    problems = []
    if s.get("weapons") != len(rows):
        problems.append(f"the {name} summary counts {s.get('weapons')!r} weapons; the report has {len(rows)} rows")
    if s.get("passed") != passed:
        problems.append(f"the {name} summary counts {s.get('passed')!r} passed; {passed} rows pass")
    if not (finite(s.get("seconds")) and s["seconds"] >= 0 and isinstance(s.get("blender"), str)):
        problems.append(f"the {name} summary's time or Blender version is malformed")
    return problems


def compare(before_bytes: bytes, after_bytes: bytes, weapon: int, expected_failures, log_text: str,
            validator_exit: int, spec: dict, rec: dict, validator_text: str, min_texel_density: float) -> dict:
    """The scoped result of one targeted validation run, or ScopeError naming every problem."""
    constants = validator_constants(validator_text)
    before, after = _report(before_bytes, "before"), _report(after_bytes, "after")
    problems = []
    if serialise(before) != before_bytes:
        problems.append("the before report does not reproduce its own bytes as the validator writes them")
    key = str(weapon)
    row = after["weapons"].get(key)
    before_row = before["weapons"].get(key)
    problems += row_problems(row, before_row, weapon, spec, rec, constants, min_texel_density)
    if not isinstance(before_row, dict) or before_row.get("id") != weapon or before_row.get("key") != spec["key"]:
        problems.append(f"the reviewed row {key} before the run is not W{weapon:02d}")
    if before_row == row:
        problems.append(f"row {key} is the row from before the run: the run did not write it")
    want = sorted(expected_failures)
    for name, doc in (("before", before), ("after", after)):
        if failing(doc) != want:
            problems.append(f"the failing rows {name} the run are {failing(doc)}, not the expected {want}")
        problems += summary_problems(doc, name)
    if list(before["weapons"]) != list(after["weapons"]):
        problems.append("the rows or their order changed")
    expected = json.loads(before_bytes.decode("utf-8"))
    expected["weapons"][key] = row
    expected["summary"] = after["summary"]
    if serialise(expected) != after_bytes:
        moved = sorted((k for k in after["weapons"] if k != key and after["weapons"][k] != before["weapons"].get(k)),
                       key=lambda k: (len(k), k))
        problems.append(f"the report changed outside row {key} and the summary"
                        + (f": rows {moved}" if moved else ": its bytes"))
    sb, sa = before["summary"], after["summary"]
    if set(sb) != set(sa):
        problems.append(f"the summary's keys changed: {sorted(sb)} before, {sorted(sa)} after")
    for k in ("weapons", "passed", "validator"):
        if sb.get(k) != sa.get(k):
            problems.append(f"the summary's {k} changed: {sb.get(k)!r} before, {sa.get(k)!r} after")
    validated = VALIDATED.findall(log_text)
    if validated != [(spec["key"], "PASS")]:
        problems.append(f"the log validated {validated}, not {spec['key']} alone with PASS")
    if f"[validate] {sa.get('passed')}/{sa.get('weapons')} weapons pass" not in log_text:
        problems.append("the log does not print the after summary's count")
    if "Traceback (most recent call last)" in log_text:
        problems.append("the log holds a Python traceback")
    implied = 0 if sa.get("passed") == sa.get("weapons") else 1
    if validator_exit != implied:
        problems.append(f"the validator exited {validator_exit}; its summary implies {implied}")
    if problems:
        raise ScopeError("; ".join(problems))
    reviewed = {c["name"] for c in before_row["checks"]}
    return {
        "schema_version": 2, "generator": "scripts/art/check_scoped_validation.py", "weapon": weapon,
        "key": spec["key"], "validator_exit": validator_exit, "validator_exit_implied_by_summary": implied,
        "scoped_result": f"row {key} passes every check, recomputed from the authored rules; only row {key} and "
                         "the summary changed",
        "failing_rows": want,
        "checks": [{"name": c["name"], "measured": c["measured"]} for c in row["checks"]],
        "checks_new_since_the_reviewed_row": [c["name"] for c in row["checks"] if c["name"] not in reviewed],
        "report_before": digest(before_bytes), "report_after": digest(after_bytes),
        "row_before": digest(serialise(before_row)), "row_after": digest(serialise(row)),
        "summary_before": sb, "summary_after": sa,
        "validator_sha256": hashlib.sha256(validator_text.encode("utf-8")).hexdigest(),
        "min_normal_tilt": constants["min_normal_tilt"], "min_texel_density": min_texel_density,
        "scope": "the narrow expected-baseline exception root authorised for the targeted W18 validation; the "
                 "validator's own exit stands beside it. Not geometric or visual admission.",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--weapon", type=int, required=True)
    ap.add_argument("--expected-failures", required=True, help="comma-separated weapon ids failing before the run")
    ap.add_argument("--before", type=Path, required=True)
    ap.add_argument("--after", type=Path, required=True)
    ap.add_argument("--build-record", type=Path, required=True, help="the build record the validation read")
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--validator-exit", type=int, required=True)
    ap.add_argument("--validator", type=Path, default=VALIDATOR)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        print(f"SCOPED_VALIDATION_FAILED: {a.out} exists; a result is never overwritten", file=sys.stderr)
        return 1
    sys.path.insert(0, str(HERE))
    import create_runtime_weapon_specs as S  # noqa: E402

    try:
        spec = S.WEAPONS.get(a.weapon)
        if spec is None:
            raise ScopeError(f"no weapon {a.weapon} in the spec")
        rec_bytes = a.build_record.read_bytes()
        result = compare(a.before.read_bytes(), a.after.read_bytes(), a.weapon,
                         [int(x) for x in a.expected_failures.split(",")],
                         a.log.read_text(encoding="utf-8", errors="replace"), a.validator_exit, spec,
                         json.loads(rec_bytes.decode("utf-8")), a.validator.read_text(encoding="utf-8"),
                         S.MIN_TEXEL_DENSITY)
    except (ScopeError, OSError, ValueError) as exc:
        print(f"SCOPED_VALIDATION_FAILED: {exc}", file=sys.stderr)
        return 1
    result["build_record"] = digest(rec_bytes)
    result["specs_sha256"] = hashlib.sha256(SPECS.read_bytes()).hexdigest()
    with open(a.out, "x", encoding="utf-8") as f:
        f.write(json.dumps(result, indent=1) + "\n")
    print(f"SCOPED_VALIDATION_OK W{a.weapon:02d}: {result['scoped_result']}; the validator's own exit "
          f"{a.validator_exit} stands beside it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
