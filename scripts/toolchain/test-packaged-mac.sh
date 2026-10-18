#!/usr/bin/env bash
# Test a staged Mac package headless, as a player's copy runs: no editor, the
# cooked content in its IoStore containers and the kernel, Connect bridge and
# data files that UAT staged beside it.
#
# 1. The bundle: identifier org.sora.soraarena, a strict code signature, and
#    the staged kernel, Connect bridge, arena map and campaign data.
# 2. A startup smoke with -NullRHI: the default map loads with SoraGameMode,
#    the game culture is Japanese, the app quits with status 0 and logs no
#    fatal error or ensure (one engine exit race is named as known; see below).
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
: "${SORA_CANDIDATE_SOURCE:?Set the full game source commit ID}"
: "${SORA_CANDIDATE_NATIVE:?Set the full native bridge source commit ID}"
if [[ -n "${SORA_CONNECT_BRIDGE:-}" ]]; then
  echo 'Packaged qualification requires SORA_CONNECT_BRIDGE unset.' >&2
  exit 1
fi
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
python3 "$SCRIPT_DIR/mac_candidate.py" verify "$APP" "$ARCHIVE_DIRECTORY/package-candidate.json" \
  "$OUTPUT/candidate-verified.json" "$SORA_CANDIDATE_SOURCE" "$SORA_CANDIDATE_NATIVE"
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
#
# -LLM keeps Unreal's low-level memory tracker on. A Development or Test Mac
# build of UE 5.8.3 starts it at launch and, without -LLM, turns it off and
# frees its trackers early in the game thread's PreInit. On the Mac the main
# thread is then still handling AppKit's launch Apple event, which allocates
# inside a tracker scope; when the teardown lands inside that scope the scope's
# PopTag finds no tracker and the app dies with SIGSEGV before its first log
# line (4 of 26 launches on 2026-09-26; FLLMScope in LLM.cpp takes no lock
# against ProcessCommandLine). With the tracker left on there is no teardown.
# Shipping builds compile the tracker out (LowLevelMemTrackerDefines.h).
launch() {
  local name="$1" status
  shift
  echo "Launching the package ($name); log: $OUTPUT/$name.log" >&2
  touch "$OUTPUT/$name.started"
  set +e
  /usr/bin/perl -e 'alarm shift @ARGV; exec @ARGV or die "exec failed: $!\n"' "$TIMEOUT_SECONDS" \
    "$EXE" -game -unattended -nopause -nosplash -nosound -stdout -FullStdOutLogOutput -LLM \
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
lines = log.splitlines()
# UE 5.8.3's IoDispatcher teardown races its own file backend: during engine
# exit, ~FIoDispatcherImpl unbinds the backend's wake-up delegate while a read
# that completes on the backend's thread may still be executing it, and the
# Development build's delegate race detector reports that as an ensure (then
# two more as the same delegates are destroyed). A launch that quits on its
# first frame, as this one does, can still have reads in flight; 2 of 109
# such launches on 2026-09-26 hit it. Only ensure blocks that are that engine race,
# wholly inside engine exit and engine I/O teardown with no project frame, are
# reported as known rather than failing the smoke; anything else fails it.
known, block = set(), None
for index, line in enumerate(lines):
    if 'LogOutputDevice: Error: === Handled ensure: ===' in line:
        block = [index]
        continue
    if block is not None and 'LogOutputDevice: Error:' in line:
        block.append(index)
        continue
    if block is not None:
        text = '\n'.join(lines[i] for i in block)
        if ('Ensure condition failed: UE::Private::FMTAccessDetectorOptions::bSuppressCheckFailure' in text
                and 'SoraArena!FEngineLoop::Exit()' in text
                and ('SoraArena!FIoDispatcherImpl::~FIoDispatcherImpl()' in text
                     or 'SoraArena!FFileIoStore::~FFileIoStore()' in text)
                and not re.search(r'SoraArena!\S*(Sora|Arena)', text)):
            known.update(block)
        block = None
known_ensures = sum(1 for i in known if 'LogOutputDevice: Error: === Handled ensure: ===' in lines[i])
if known_ensures:
    print(f'Known engine exit race: {known_ensures} IoDispatcher teardown ensure(s) during engine exit, no project frame')
fatal = [line for index, line in enumerate(lines) if index not in known
         and re.search(r'Fatal error|=== Critical error|Assertion failed|Ensure condition failed|LogOutputDevice: Error', line)]
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

# Recheck after execution so the evidence cannot describe replaced artifacts.
python3 "$SCRIPT_DIR/mac_candidate.py" verify "$APP" "$ARCHIVE_DIRECTORY/package-candidate.json" \
  "$OUTPUT/candidate-verified-after.json" "$SORA_CANDIDATE_SOURCE" "$SORA_CANDIDATE_NATIVE"
python3 "$SCRIPT_DIR/verify_packaged_report.py" "$OUTPUT/app-data/report/index.json" "$OUTPUT/automation.log" \
  "$FILTER" "$(cat "$OUTPUT/automation.status")" "$OUTPUT/results.tsv" "$STAGED/Binaries/Mac/libconnect_norito_bridge.dylib"
