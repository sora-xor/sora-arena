#!/usr/bin/env bash
# Run rendered game automation (art-review or baseline captures) in the
# pinned editor binary's standalone game mode, against this checkout's
# uncooked Content/Generated: faster than a cook/stage for art iteration.
#
#   scripts/toolchain/capture-editor-game.sh <automation filter> [width] [height] [auto|sm5|sm6]
#
# Same flags as capture-packaged-mac.sh's launch: offscreen Metal, unattended,
# App Nap disabled for this launch. Frames land under Saved/Screenshots/ (for
# SoraCapture.ArtReview: Saved/Screenshots/SoraArtReview/<w>x<h>/). These are
# uncooked editor-binary game frames, labelled as such; packaged captures
# remain the release evidence. SORA_EXEC_PREFIX="cvar value," (comma-separated) runs console
# commands before the tests (art-review A/B switches). A forced shader model is
# checked against Unreal's report. Every requested test must finish successfully;
# process exit alone cannot establish a successful capture.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
FILTER="${1:?Usage: capture-editor-game.sh <automation filter> [width] [height] [auto|sm5|sm6]}"
WIDTH="${2:-1920}"
HEIGHT="${3:-1080}"
SHADER_MODEL="${4:-auto}"
[[ $# -le 4 && "$FILTER" =~ ^[A-Za-z0-9_.+]+$ && "$WIDTH" =~ ^[1-9][0-9]*$ && "$HEIGHT" =~ ^[1-9][0-9]*$ ]] || {
  echo 'Invalid filter, viewport dimensions or argument count.' >&2; exit 2;
}
SHADER_ARGS=()
case "$SHADER_MODEL" in
  auto) ;;
  sm5|sm6) SHADER_ARGS=("-$SHADER_MODEL") ;;
  *) echo 'Shader model must be auto, sm5 or sm6.' >&2; exit 2 ;;
esac
OUTPUT="$PROJECT_ROOT/Saved/Capture/$(date -u +%Y%m%dT%H%M%SZ)-$SHADER_MODEL-$$"
LOG="$OUTPUT/editor.log"
LOG_COMPLETION="$OUTPUT/log-completion.json"
REPORT="$OUTPUT/report"
mkdir -p "$OUTPUT"
TOOLCHAIN_EXPORTS="$(PYTHONDONTWRITEBYTECODE=1 python3 - "$SCRIPT_DIR" <<'PY'
import importlib.util, shlex, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('doctor', Path(sys.argv[1])/'doctor.py')
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)
report = doctor.inspect()
editor = Path(report['engine_root'])/'Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor'
if not report['build_ready'] or not editor.is_file():
    sys.exit('Editor prerequisites are unavailable; run scripts/toolchain/doctor.py and build-mac.sh first.')
for name, value in [('EDITOR', str(editor)), ('DEVELOPER_DIR', report['developer_dir']),
                    ('SDKROOT', report['sdk_root']), ('PROJECT', str(next(doctor.ROOT.glob('*.uproject'))))]:
    print('export '+name+'='+shlex.quote(value))
PY
)" || exit 1
eval "$TOOLCHAIN_EXPORTS"
# Prevent an uncooked capture from testing a stale project module.
echo "Building editor module; log: $OUTPUT/build.log" >&2
if ! "$SCRIPT_DIR/build-mac.sh" Development Editor >"$OUTPUT/build.log" 2>&1; then
  tail -n 20 "$OUTPUT/build.log" >&2
  exit 1
fi
source "$SCRIPT_DIR/editor-config-guard.sh"
guard_config
git -C "$PROJECT_ROOT" rev-parse HEAD >"$OUTPUT/source-commit.txt"
git -C "$PROJECT_ROOT" status --porcelain >"$OUTPUT/source-status.txt"
START_NS="$(python3 -c 'import time; print(time.time_ns())')"
echo "Game automation $FILTER at ${WIDTH}x${HEIGHT}, $SHADER_MODEL; log: $LOG" >&2
set +e
# Name the project's entry map before AppKit's bare YES argument can be
# mistaken for the startup URL by Unreal's command-line parser.
# A sponsored trace child can write after the editor exits. The collector owns
# the file and waits for the inherited pipe's EOF before any manifest hashes it.
python3 "$SCRIPT_DIR/run_logged_process.py" --log "$LOG" --receipt "$LOG_COMPLETION" -- \
  "$EDITOR" "$PROJECT" /Engine/Maps/Entry -game -unattended -nopause -nosplash -nosound -stdout -FullStdOutLogOutput \
  -RenderOffscreen "-ResX=$WIDTH" "-ResY=$HEIGHT" -windowed -NoTextureStreaming \
  "${SHADER_ARGS[@]}" "-ReportExportPath=$REPORT" \
  "-ExecCmds=${SORA_EXEC_PREFIX:-}Automation RunTests $FILTER;Quit" "${EDITOR_CONFIG_ARGS[@]}" -NSAppSleepDisabled YES
STATUS=$?
set -e
python3 "$SCRIPT_DIR/verify-capture-report.py" "$REPORT/index.json" "$LOG" "$STATUS" "$SHADER_MODEL" \
  --log-completion "$LOG_COMPLETION" \
  --archive "$PROJECT_ROOT" "$(dirname -- "$EDITOR")/../../.." "$OUTPUT" "$START_NS" "$WIDTH" "$HEIGHT" "$FILTER"
