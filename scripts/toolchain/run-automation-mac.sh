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
# The editor resolves relative report paths from Engine/Binaries/Mac, whereas
# the shell reads them from its own working directory. Give both the same path.
OUTPUT="$(cd -- "$OUTPUT" && pwd)"
LOG="$OUTPUT/editor.log"
LOG_COMPLETION="$OUTPUT/editor-log-completion.json"
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
# Trace descendants can retain stdout after the editor exits. Only the
# collector owns the log file; finish its inherited stream before validation.
python3 "$SCRIPT_DIR/run_logged_process.py" --log "$LOG" --receipt "$LOG_COMPLETION" -- \
  "$EDITOR_CMD" "$PROJECT" "-ExecCmds=Automation RunTests $FILTER;Quit" \
  -unattended -nopause -nullrhi -nosplash -nosound -stdout -FullStdOutLogOutput \
  "${EDITOR_CONFIG_ARGS[@]}" "-ReportExportPath=$REPORT"
EDITOR_STATUS=$?
set -e

if ! python3 "$SCRIPT_DIR/verify_automation_report.py" "$REPORT/index.json" "$LOG" "$FILTER" "$EDITOR_STATUS" \
  "$OUTPUT/results.tsv" "$PROJECT_ROOT/Binaries/Mac/libconnect_norito_bridge.dylib" --context editor; then
  if [[ ! -d "$PROJECT_ROOT/Content/Generated" ]]; then
    echo 'Note: Content/Generated is absent; tests loading imported assets require import-mac.sh. This does not excuse the failed run.' >&2
  fi
  exit 1
fi
