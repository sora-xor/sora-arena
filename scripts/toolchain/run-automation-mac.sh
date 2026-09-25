#!/usr/bin/env bash
# Build the editor module, run the project's Unreal automation tests headless in
# the Mac editor, and fail unless every selected test reports Success in
# Unreal's exported JSON report and nothing under Config/ changed during the run.
# Usage: run-automation-mac.sh [Filter[+Filter...]] [output-directory]
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
FILTER="${1:-SoraArena}"
OUTPUT="${2:-$PROJECT_ROOT/Saved/Automation/$(date -u +%Y%m%dT%H%M%SZ)}"
case "$FILTER" in
  ''|*[!A-Za-z0-9_.+]*) echo 'Usage: run-automation-mac.sh [Filter[+Filter...]] [output-directory]' >&2; exit 2;;
esac
MIN_FREE_GIB="${SORA_MIN_FREE_GIB:-30}"
TOOLCHAIN_EXPORTS="$(PYTHONDONTWRITEBYTECODE=1 python3 - "$SCRIPT_DIR" <<'PY'
import importlib.util, shlex, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('doctor', Path(sys.argv[1])/'doctor.py')
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)
report = doctor.inspect()
editor = Path(report['engine_root'])/'Engine/Binaries/Mac/UnrealEditor-Cmd'
if not report['build_ready'] or not editor.is_file():
    sys.exit('Selected editor prerequisites are unavailable; run scripts/toolchain/doctor.py and build-mac.sh first.')
for name, value in [('EDITOR_CMD', str(editor)), ('DEVELOPER_DIR', report['developer_dir']),
                    ('SDKROOT', report['sdk_root']),
                    ('PROJECT', str(next(doctor.ROOT.glob('*.uproject'))))]:
    print('export '+name+'='+shlex.quote(value))
PY
)" || exit 1
eval "$TOOLCHAIN_EXPORTS"

FREE_GIB="$(df -Pk "$PROJECT_ROOT" | awk 'NR==2 {print int($4/1048576)}')"
if (( FREE_GIB < MIN_FREE_GIB )); then
  echo "Only ${FREE_GIB} GiB free; automation requires at least ${MIN_FREE_GIB} GiB." >&2
  exit 1
fi

mkdir -p "$OUTPUT"
LOG="$OUTPUT/editor.log"
REPORT="$OUTPUT/report"
rm -rf "$REPORT"
# Unreal does not rebuild the project module with -unattended, so a stale one
# would test old code. UBT decides what is stale from every source, header
# (including the kernel's arena.h) and build rule, and does nothing when the
# module is current.
echo "Building the editor module; log: $OUTPUT/build.log" >&2
if ! "$SCRIPT_DIR/build-mac.sh" Development Editor >"$OUTPUT/build.log" 2>&1; then
  tail -n 20 "$OUTPUT/build.log" >&2
  echo "FAIL: build-mac.sh Development failed; see $OUTPUT/build.log" >&2
  exit 1
fi
source "$SCRIPT_DIR/editor-config-guard.sh"
guard_config

echo "Running Unreal automation '$FILTER'; log: $LOG" >&2
set +e
"$EDITOR_CMD" "$PROJECT" "-ExecCmds=Automation RunTests $FILTER;Quit" \
  -unattended -nopause -nullrhi -nosplash -nosound -stdout -FullStdOutLogOutput \
  "${EDITOR_CONFIG_ARGS[@]}" "-ReportExportPath=$REPORT" >"$LOG" 2>&1
EDITOR_STATUS=$?
set -e

python3 - "$REPORT/index.json" "$LOG" "$FILTER" "$EDITOR_STATUS" "$PROJECT_ROOT" <<'PY'
import json
import re
import sys
from pathlib import Path

report_path, log_path, test_filter = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
editor_status, project_root = int(sys.argv[4]), Path(sys.argv[5])
log = log_path.read_text(errors='replace')
found = re.findall(r"Found (\d+) automation tests based on '([^']*)'", log)
if not report_path.is_file():
    sys.exit(f'FAIL: Unreal wrote no automation report (editor exit {editor_status}); see {log_path}')
report = json.loads(report_path.read_text(encoding='utf-8-sig'))
tests = report.get('tests', [])
failures = []
print(f'{"RESULT":8} {"ERR":>4} {"WARN":>4} {"SEC":>7}  TEST')
for test in sorted(tests, key=lambda item: item['fullTestPath']):
    entries = [entry['event'] for entry in test.get('entries', [])]
    errors = [event['message'] for event in entries if event.get('type') == 'Error']
    warnings = [event['message'] for event in entries if event.get('type') == 'Warning']
    state = test.get('state', 'Unknown')
    print(f'{state:8} {len(errors):4} {len(warnings):4} {test.get("duration", 0.0):7.2f}  {test["fullTestPath"]}')
    if state != 'Success':
        failures.append(test['fullTestPath'])
        for message in errors[:5]:
            print(f'           {message[:220]}')
        if len(errors) > 5:
            print(f'           ... {len(errors) - 5} more errors')
expected = sum(int(count) for count, _ in found)
problems = []
if not tests:
    problems.append(f"no tests matched '{test_filter}'")
if found and expected != len(tests):
    problems.append(f'{expected} tests were found but {len(tests)} were reported')
for key in ('notRun', 'inProcess'):
    if report.get(key):
        problems.append(f'{report[key]} tests {key}')
if failures:
    problems.append(f'{len(failures)} of {len(tests)} tests failed')
# Unreal exits nonzero when tests fail; any other nonzero exit is a crash or error.
if editor_status != 0 and not failures:
    problems.append(f'editor exited {editor_status} although every reported test passed')
if failures and not (project_root / 'Content/Generated').is_dir():
    # Reported, never excused: the run still fails.
    print('Note: Content/Generated is absent in this checkout, so tests that load imported '
          '/Game/Generated assets cannot pass until scripts/toolchain/import-mac.sh runs.')
print(f'Report: {report_path.parent}')
if problems:
    sys.exit('FAIL: ' + '; '.join(problems))
print(f'PASS: {len(tests)} automation tests')
PY
