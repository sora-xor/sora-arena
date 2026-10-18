#!/usr/bin/env python3
"""Require complete Unreal automation results from a rendered editor-game run."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys


def problems(report: dict, log: str, status: int, shader_model: str) -> list[str]:
    failures = []
    if status:
        failures.append(f"editor exited {status}")
    tests = report.get("tests", [])
    if not tests:
        failures.append("no automation tests were reported")
    found = re.findall(r"Found (\d+) automation tests based on '[^']*'", log)
    if not found or sum(map(int, found)) != len(tests):
        failures.append("reported test count does not match discovered tests")
    if any(report.get(key, 0) for key in ("failed", "notRun", "inProcess")):
        failures.append("report contains failed or unfinished tests")
    for test in tests:
        events = [entry.get("event", {}) for entry in test.get("entries", [])]
        if (test.get("state") != "Success" or test.get("errors", 0)
                or any(event.get("type") == "Error" for event in events)):
            failures.append(f"unsuccessful test: {test.get('fullTestPath', '<unnamed>')}")
    devices = report.get("devices", [])
    if not devices or any("metal" not in device.get("rHI", "").lower() for device in devices):
        failures.append("report does not identify the Metal renderer")
    if shader_model != "auto" and any(
            device.get("renderMode", "").lower() != shader_model for device in devices):
        failures.append(f"actual shader model differs from requested {shader_model}")
    return failures


def main() -> int:
    report_path, log_path = map(Path, sys.argv[1:3])
    status, shader_model = int(sys.argv[3]), sys.argv[4]
    try:
        report = json.loads(report_path.read_text(encoding="utf-8-sig"))
        log = log_path.read_text(errors="replace")
    except (OSError, ValueError) as error:
        print(f"FAIL: missing or invalid capture report: {error}", file=sys.stderr)
        return 1
    failures = problems(report, log, status, shader_model)
    for test in report.get("tests", []):
        print(f"{test.get('state', 'Unknown')}: {test.get('fullTestPath', '<unnamed>')}")
    print(f"Report: {report_path}")
    if failures:
        print("FAIL: " + "; ".join(failures), file=sys.stderr)
        return 1
    print(f"PASS: {len(report['tests'])} rendered automation tests; "
          "uncooked editor-game evidence, not packaged qualification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
