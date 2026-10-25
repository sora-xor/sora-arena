#!/usr/bin/env python3
"""Gate one weapon's targeted metric validation on its own row, beside the validator's real exit.

  python3 scripts/art/check_scoped_validation.py --weapon 18 --expected-failures 3,11,13,16 \
      --before <metric_report.json archived before the run> \
      --after Content/SourceArt/Weapons/Runtime/metric_report.json \
      --log <the validation's log> --validator-exit <its real exit> --out <result.json>

**Why.** create_runtime_weapon_validation.py --only 18 validates W18 alone,
but it rewrites the whole metric_report.json and exits from the accumulated
summary of every row. The four blockout weapons' rows (03, 11, 13, 16) fail
and are carried over unchanged, so the run exits 1 whatever W18 does.

**Root's rule for the W18 rebuild** (Codex, 2026-10-25): keep the validator's
real exit and its full report, and gate the new W18 row separately. The
narrow expected-baseline exception holds only if all of these hold, and any
other result stops the sequence:
- **W18 passes:** its row passes every check, with no errors. It is not the
  row from before the run: the run wrote it.
- **The same failures:** the failing rows before and after the run are
  exactly the expected pre-run failures.
- **Every other row byte-identical:** the report after the run is exactly the
  report before it, with only W18's row and the summary replaced, serialised
  as the validator writes it. The report before must reproduce its own bytes
  that way, or nothing can be compared.
- **The summary:** its weapon and pass counts, its validator and its keys
  are unchanged; only its time and Blender version may differ.
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
import re
import sys
from pathlib import Path

VALIDATED = re.compile(r"^\[validate\] (\S+): (PASS|FAIL)$", re.M)


class ScopeError(Exception):
    pass


def serialise(doc) -> bytes:
    """As create_runtime_weapon_validation.py writes metric_report.json."""
    return (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def digest(data: bytes) -> dict:
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def failing(doc):
    return sorted(int(k) for k, r in doc["weapons"].items() if r.get("pass") is not True)


def _report(data: bytes, name: str):
    try:
        doc = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ScopeError(f"the {name} report is unreadable ({type(exc).__name__}: {exc})") from None
    if not (isinstance(doc, dict) and set(doc) == {"weapons", "summary"} and isinstance(doc["weapons"], dict)
            and isinstance(doc["summary"], dict)):
        raise ScopeError(f"the {name} report is not a record of weapons and a summary")
    return doc


def compare(before_bytes: bytes, after_bytes: bytes, weapon: int, expected_failures, log_text: str,
            validator_exit: int) -> dict:
    """The scoped result of one targeted validation run, or ScopeError naming every problem."""
    before, after = _report(before_bytes, "before"), _report(after_bytes, "after")
    problems = []
    if serialise(before) != before_bytes:
        problems.append("the before report does not reproduce its own bytes as the validator writes them")
    key = str(weapon)
    row = after["weapons"].get(key)
    if not isinstance(row, dict):
        raise ScopeError(f"the after report has no row {key}")
    bad = [c.get("name") for c in row.get("checks", []) if c.get("pass") is not True]
    if row.get("pass") is not True or row.get("errors") or bad or not row.get("checks"):
        problems.append(f"row {key} does not pass every check (pass {row.get('pass')!r}, errors {row.get('errors')}, "
                        f"failing checks {bad})")
    if before["weapons"].get(key) == row:
        problems.append(f"row {key} is the row from before the run: the run did not write it")
    want = sorted(expected_failures)
    for name, doc in (("before", before), ("after", after)):
        if failing(doc) != want:
            problems.append(f"the failing rows {name} the run are {failing(doc)}, not the expected {want}")
    if list(before["weapons"]) != list(after["weapons"]):
        problems.append("the rows or their order changed")
    expected = json.loads(before_bytes.decode("utf-8"))
    expected["weapons"][key] = row
    expected["summary"] = after["summary"]
    if serialise(expected) != after_bytes:
        moved = sorted((k for k in after["weapons"] if k != key and after["weapons"][k] != before["weapons"].get(k)),
                       key=int)
        problems.append(f"the report changed outside row {key} and the summary"
                        + (f": rows {moved}" if moved else ": its bytes"))
    sb, sa = before["summary"], after["summary"]
    if set(sb) != set(sa):
        problems.append(f"the summary's keys changed: {sorted(sb)} before, {sorted(sa)} after")
    for k in ("weapons", "passed", "validator"):
        if sb.get(k) != sa.get(k):
            problems.append(f"the summary's {k} changed: {sb.get(k)!r} before, {sa.get(k)!r} after")
    validated = VALIDATED.findall(log_text)
    if validated != [(row.get("key"), "PASS")]:
        problems.append(f"the log validated {validated}, not {row.get('key')} alone with PASS")
    if f"[validate] {sa.get('passed')}/{sa.get('weapons')} weapons pass" not in log_text:
        problems.append("the log does not print the after summary's count")
    if "Traceback (most recent call last)" in log_text:
        problems.append("the log holds a Python traceback")
    implied = 0 if sa.get("passed") == sa.get("weapons") else 1
    if validator_exit != implied:
        problems.append(f"the validator exited {validator_exit}; its summary implies {implied}")
    if problems:
        raise ScopeError("; ".join(problems))
    return {
        "schema_version": 1, "generator": "scripts/art/check_scoped_validation.py", "weapon": weapon,
        "validator_exit": validator_exit, "validator_exit_implied_by_summary": implied,
        "scoped_result": f"row {key} passes every check; only row {key} and the summary changed",
        "failing_rows": want, "row_checks": len(row["checks"]),
        "report_before": digest(before_bytes), "report_after": digest(after_bytes),
        "row_before": digest(serialise(before["weapons"].get(key))), "row_after": digest(serialise(row)),
        "summary_before": sb, "summary_after": sa,
        "scope": "the narrow expected-baseline exception root authorised for the targeted W18 validation; the "
                 "validator's own exit stands beside it. Not geometric or visual admission.",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--weapon", type=int, required=True)
    ap.add_argument("--expected-failures", required=True, help="comma-separated weapon ids failing before the run")
    ap.add_argument("--before", type=Path, required=True)
    ap.add_argument("--after", type=Path, required=True)
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--validator-exit", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        print(f"SCOPED_VALIDATION_FAILED: {a.out} exists; a result is never overwritten", file=sys.stderr)
        return 1
    try:
        result = compare(a.before.read_bytes(), a.after.read_bytes(), a.weapon,
                         [int(x) for x in a.expected_failures.split(",")],
                         a.log.read_text(encoding="utf-8", errors="replace"), a.validator_exit)
    except (ScopeError, OSError) as exc:
        print(f"SCOPED_VALIDATION_FAILED: {exc}", file=sys.stderr)
        return 1
    with open(a.out, "x", encoding="utf-8") as f:
        f.write(json.dumps(result, indent=1) + "\n")
    print(f"SCOPED_VALIDATION_OK W{a.weapon:02d}: {result['scoped_result']}; the validator's own exit "
          f"{a.validator_exit} stands beside it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
