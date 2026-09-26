#!/usr/bin/env bash
# Test a staged Mac package headless, as a player's copy runs: no editor, the
# cooked content in its IoStore containers and the kernel, Connect bridge and
# data files that UAT staged beside it.
#
# 1. The bundle: identifier org.sora.soraarena, a strict code signature, and
#    the staged kernel, Connect bridge, arena map and campaign data.
# 2. A startup smoke with -NullRHI: the default map loads with SoraGameMode,
#    the game culture is Japanese, the app quits with status 0 and logs no
#    fatal error or ensure.
# 3. The project's client-context Unreal automation inside the package with
#    -RenderOffscreen (Metal, no window), so the rendered front-end test runs
#    too. It fails unless every test reports Success in Unreal's exported JSON
#    report and no cooked material falls back to the default material for a
#    missing usage flag, and lists the result of each test in results.tsv.
#
# Editor-only tests (EditorContext without ClientContext) are not compiled into
# a game's test list; they are run by run-automation-mac.sh.
#
# Each launch gets its own empty -UserDir, so the package writes saves,
# settings, screenshots, logs and the report there and never touches the
# player's saves. UE signs the Mac app with the App Sandbox (its default
# Build/Mac/Resources/Sandbox.Server.entitlements), and a sandboxed app can
# write only inside ~/Library/Containers/<bundle id>/Data, so those user
# directories live in a new run directory under that container's tmp/ and are
# copied to OUTPUT/app-data after the launches; the container copy is left for
# macOS to clear with the rest of the app's tmp/.
# Usage: test-packaged-mac.sh ARCHIVE_DIRECTORY [Filter[+Filter...]] [output-directory]
#   ARCHIVE_DIRECTORY is the directory given to stage-mac.sh.
#   SORA_PACKAGED_TIMEOUT_SECONDS bounds each launch (default 3600).
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
if [[ $# -lt 1 || $# -gt 3 ]]; then
  echo 'Usage: test-packaged-mac.sh ARCHIVE_DIRECTORY [Filter[+Filter...]] [output-directory]' >&2
  exit 2
fi
ARCHIVE_DIRECTORY="$(cd -- "$1" && pwd -P)"
FILTER="${2:-SoraArena}"
OUTPUT="${3:-$PROJECT_ROOT/Saved/PackagedAutomation/$(date -u +%Y%m%dT%H%M%SZ)}"
case "$FILTER" in
  ''|*[!A-Za-z0-9_.+]*) echo 'Usage: test-packaged-mac.sh ARCHIVE_DIRECTORY [Filter[+Filter...]] [output-directory]' >&2; exit 2;;
esac
TIMEOUT_SECONDS="${SORA_PACKAGED_TIMEOUT_SECONDS:-3600}"
case "$TIMEOUT_SECONDS" in
  ''|*[!0-9]*|0) echo 'SORA_PACKAGED_TIMEOUT_SECONDS must be a positive number of seconds.' >&2; exit 2;;
esac
MIN_FREE_GIB="${SORA_MIN_FREE_GIB:-30}"
FREE_GIB="$(df -Pk "$PROJECT_ROOT" | awk 'NR==2 {print int($4/1048576)}')"
if (( FREE_GIB < MIN_FREE_GIB )); then
  echo "Only ${FREE_GIB} GiB free; packaged automation requires at least ${MIN_FREE_GIB} GiB." >&2
  exit 1
fi

# UAT archives into ARCHIVE_DIRECTORY/Mac unless a component of that path
# already starts with the platform name (DeploymentContext.cs), as
# Local/Packages/mac-wavec-baseline does; stage-mac.sh applies the same rule.
APP="$(python3 - "$ARCHIVE_DIRECTORY" <<'PY'
from pathlib import Path
import sys
archive = Path(sys.argv[1])
named = any(part.lower().startswith('mac') for part in archive.parts[1:])
print((archive if named else archive / 'Mac') / 'SoraArena.app')
PY
)"
EXE="$APP/Contents/MacOS/SoraArena"
STAGED="$APP/Contents/UE/SoraArena"
if [[ ! -x "$EXE" ]]; then
  echo "No packaged game at $EXE; run stage-mac.sh $ARCHIVE_DIRECTORY first." >&2
  exit 1
fi
# Every launch starts from empty saves and settings, so a reused directory
# would test whatever an earlier run left there.
if [[ -e "$OUTPUT" && -n "$(ls -A "$OUTPUT")" ]]; then
  echo "Output directory $OUTPUT is not empty; give a new one." >&2
  exit 2
fi
mkdir -p "$OUTPUT"

echo "Package: $APP"
BUNDLE_ID="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP/Contents/Info.plist")"
if [[ "$BUNDLE_ID" != 'org.sora.soraarena' ]]; then
  echo "FAIL: bundle identifier is $BUNDLE_ID, not org.sora.soraarena" >&2
  exit 1
fi
if ! /usr/bin/codesign --verify --deep --strict "$APP" 2>"$OUTPUT/codesign.log"; then
  cat "$OUTPUT/codesign.log" >&2
  echo "FAIL: the app's code signature does not verify" >&2
  exit 1
fi
for FILE in Binaries/Mac/libarena_ffi.dylib Binaries/Mac/libconnect_norito_bridge.dylib \
            crates/arena-core/data/arena-map-v1.json Content/Data/campaign; do
  if [[ ! -e "$STAGED/$FILE" ]]; then
    echo "FAIL: the package lacks $FILE" >&2
    exit 1
  fi
done
KERNEL_SHA="$(shasum -a 256 "$STAGED/Binaries/Mac/libarena_ffi.dylib" | awk '{print $1}')"
echo "Bundle org.sora.soraarena, signature verified, staged kernel sha256 $KERNEL_SHA"
SANDBOXED="$(/usr/bin/codesign -d --entitlements - --xml "$APP" 2>/dev/null | python3 -c '
import plistlib, sys
data = sys.stdin.buffer.read()
print("yes" if data and plistlib.loads(data).get("com.apple.security.app-sandbox") is True else "no")')"
if [[ "$SANDBOXED" == yes ]]; then
  APP_DATA="$HOME/Library/Containers/$BUNDLE_ID/Data/tmp/SoraPackagedAutomation/$(date -u +%Y%m%dT%H%M%SZ)-$$"
  echo "The app is sandboxed; its writable run directory: $APP_DATA"
else
  APP_DATA="$OUTPUT/app-data"
fi
if [[ -e "$APP_DATA" ]]; then
  echo "The app's run directory $APP_DATA already exists." >&2
  exit 1
fi

# launch NAME ARGS...: runs the packaged game with its own empty user
# directory and the launch's stdout log; a launch past the timeout is killed
# by SIGALRM (status 142). The app creates the directories it writes. macOS
# crash reports written during the launch are copied beside its log.
launch() {
  local name="$1" status
  shift
  echo "Launching the package ($name); log: $OUTPUT/$name.log" >&2
  touch "$OUTPUT/$name.started"
  set +e
  /usr/bin/perl -e 'alarm shift @ARGV; exec @ARGV or die "exec failed: $!\n"' "$TIMEOUT_SECONDS" \
    "$EXE" -game -unattended -nopause -nosplash -nosound -stdout -FullStdOutLogOutput \
    "-UserDir=$APP_DATA/$name-userdir" "$@" >"$OUTPUT/$name.log" 2>&1
  status=$?
  set -e
  echo "$status" >"$OUTPUT/$name.status"
  # ReportCrash writes the report a few seconds after a signal kills the app.
  local waited=0
  while (( status > 128 && status != 142 && waited < 20 )) &&
        [[ -z "$(find "$HOME/Library/Logs/DiagnosticReports" -maxdepth 1 -name 'SoraArena-*.ips' \
                  -newer "$OUTPUT/$name.started" 2>/dev/null)" ]]; do
    sleep 1
    waited=$((waited + 1))
  done
  { find "$HOME/Library/Logs/DiagnosticReports" -maxdepth 1 -name 'SoraArena-*.ips' \
      -newer "$OUTPUT/$name.started" -exec cp -p {} "$OUTPUT/" \; -print 2>/dev/null || true; } |
    sed 's/^/Crash report: /' >&2
  if [[ "$APP_DATA" != "$OUTPUT/app-data" && -d "$APP_DATA" ]]; then
    /usr/bin/ditto "$APP_DATA" "$OUTPUT/app-data"
  fi
}

launch smoke -NullRHI -ExecCmds=Quit
python3 - "$OUTPUT/smoke.log" "$(cat "$OUTPUT/smoke.status")" "$TIMEOUT_SECONDS" <<'PY'
import re
import sys
from pathlib import Path

log_path, status, timeout = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
log = log_path.read_text(errors='replace')
problems = []
if status == 142:
    problems.append(f'timed out after {timeout} s')
elif status != 0:
    problems.append(f'exited {status}')
if "Game class is 'SoraGameMode'" not in log:
    problems.append('the default map did not start SoraGameMode')
if not re.search(r'LoadMap\(/Engine/Maps/Entry\)', log):
    problems.append('the default map /Engine/Maps/Entry was not loaded')
languages = re.findall(r'Overriding language with [\w ]+ configuration option \(([^)]+)\)', log)
# Unreal logs the language and locale overrides once per initialization pass.
if not languages or set(languages) != {'ja'}:
    problems.append(f'the game language overrides were {sorted(set(languages)) or "absent"}, not ja from DefaultGame.ini')
fatal = [line for line in log.splitlines()
         if re.search(r'Fatal error|=== Critical error|Assertion failed|Ensure condition failed|LogOutputDevice: Error', line)]
for line in fatal[:10]:
    print(f'  {line[:240]}', file=sys.stderr)
if fatal:
    problems.append(f'{len(fatal)} fatal, assertion or ensure lines')
if problems:
    sys.exit('FAIL startup smoke: ' + '; '.join(problems) + f'; see {log_path}')
print('PASS startup smoke: /Engine/Maps/Entry with SoraGameMode, language ja, exit 0')
PY

REPORT="$APP_DATA/report"
launch automation -RenderOffscreen -ResX=1280 -ResY=720 -windowed \
  "-ExecCmds=Automation RunTests $FILTER;Quit" "-ReportExportPath=$REPORT"

python3 - "$OUTPUT/app-data/report/index.json" "$OUTPUT/automation.log" "$FILTER" "$(cat "$OUTPUT/automation.status")" \
  "$TIMEOUT_SECONDS" "$OUTPUT/results.tsv" <<'PY'
import json
import re
import sys
from pathlib import Path

report_path, log_path, test_filter = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
status, timeout, results_path = int(sys.argv[4]), sys.argv[5], Path(sys.argv[6])
log = log_path.read_text(errors='replace')
found = re.findall(r"Found (\d+) automation tests based on '([^']*)'", log)
if status == 142:
    sys.exit(f'FAIL: the package timed out after {timeout} s; see {log_path}')
if not report_path.is_file():
    sys.exit(f'FAIL: the package wrote no automation report (exit {status}); see {log_path}')
report = json.loads(report_path.read_text(encoding='utf-8-sig'))
tests = sorted(report.get('tests', []), key=lambda item: item['fullTestPath'])
failures = []
rows = ['state\terrors\twarnings\tseconds\ttest']
print(f'{"RESULT":8} {"ERR":>4} {"WARN":>4} {"SEC":>7}  TEST')
for test in tests:
    entries = [entry['event'] for entry in test.get('entries', [])]
    errors = [event['message'] for event in entries if event.get('type') == 'Error']
    warnings = [event['message'] for event in entries if event.get('type') == 'Warning']
    state = test.get('state', 'Unknown')
    seconds = test.get('duration', 0.0)
    print(f'{state:8} {len(errors):4} {len(warnings):4} {seconds:7.2f}  {test["fullTestPath"]}')
    rows.append(f'{state}\t{len(errors)}\t{len(warnings)}\t{seconds:.2f}\t{test["fullTestPath"]}')
    if state != 'Success':
        failures.append(test['fullTestPath'])
        for message in errors[:5]:
            print(f'           {message[:220]}')
        if len(errors) > 5:
            print(f'           ... {len(errors) - 5} more errors')
results_path.write_text('\n'.join(rows) + '\n', encoding='utf-8')
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
if status != 0 and not failures:
    problems.append(f'the package exited {status} although every reported test passed')
# A cooked material cannot gain a usage flag at runtime, so a mesh that needs
# one draws with the default material in the shipped game; only a package
# shows this, and a test that passed does not excuse it.
defaults = sorted(set(re.findall(
    r'LogMaterial: Warning: Material (\S+) missing usage flag (\w+)! Default Material will be used in game', log)))
for material, usage in defaults:
    print(f'Default material in game: {material} lacks usage {usage}')
if defaults:
    problems.append(f'{len(defaults)} cooked materials lack a usage flag and draw as the default material')
print(f'Report: {report_path.parent}; per-test results: {results_path}')
if problems:
    sys.exit('FAIL: ' + '; '.join(problems))
print(f'PASS: {len(tests)} automation tests in the package')
PY
