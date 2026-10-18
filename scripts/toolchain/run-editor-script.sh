#!/usr/bin/env bash
# Run one editor Python script headless in the pinned UE, with the Config guard.
#
#   scripts/toolchain/run-editor-script.sh [--rhi|--editor] <scripts/unreal/x.py> <marker> [log] [-- script args]
#
# --rhi renders offscreen through Metal (shader compiles) in UnrealEditor-Cmd,
# which exits once the script returns; --editor runs the full UnrealEditor
# offscreen for scripts that keep working on editor ticks (look-development
# captures) and quit the editor themselves. Without either the editor runs
# -nullrhi (imports). The run fails if
# the editor exits non-zero, logs a Python error, never prints the marker, or
# changes any file under Config/.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
RHI="-nullrhi"
BINARY="UnrealEditor-Cmd"
THROTTLE=()
if [[ "${1:-}" == --rhi ]]; then RHI="-RenderOffscreen"; shift;
elif [[ "${1:-}" == --editor ]]; then RHI="-RenderOffscreen"; BINARY="UnrealEditor.app/Contents/MacOS/UnrealEditor"; shift; fi
# An offscreen editor is never the foreground app; without this it throttles
# its tick rate and tick-driven captures crawl.
THROTTLE=('-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False')
[[ $# -ge 2 ]] || { echo 'Usage: run-editor-script.sh [--rhi] <script.py> <marker> [log] [-- args]' >&2; exit 2; }
SCRIPT="$(cd -- "$(dirname -- "$1")" && pwd)/$(basename -- "$1")"
MARKER="$2"
shift 2
LOG="$PROJECT_ROOT/Saved/ClaudeArt/logs/$(basename "$SCRIPT" .py).log"
if [[ $# -gt 0 && "$1" != -- ]]; then LOG="$1"; shift; fi
EXTRA=()
if [[ $# -gt 0 && "$1" == -- ]]; then shift; EXTRA=("$@"); fi
mkdir -p "$(dirname "$LOG")"
TOOLCHAIN_EXPORTS="$(PYTHONDONTWRITEBYTECODE=1 python3 - "$SCRIPT_DIR" "$BINARY" <<'PY'
import importlib.util, shlex, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('doctor', Path(sys.argv[1])/'doctor.py')
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)
report = doctor.inspect()
editor = Path(report['engine_root'])/'Engine/Binaries/Mac'/sys.argv[2]
if not report['build_ready'] or not editor.is_file():
    sys.exit('Editor prerequisites are unavailable; run scripts/toolchain/doctor.py and build-mac.sh first.')
for name, value in [('EDITOR_CMD', str(editor)), ('DEVELOPER_DIR', report['developer_dir']),
                    ('SDKROOT', report['sdk_root']), ('PROJECT', str(next(doctor.ROOT.glob('*.uproject'))))]:
    print('export '+name+'='+shlex.quote(value))
PY
)" || exit 1
eval "$TOOLCHAIN_EXPORTS"
source "$SCRIPT_DIR/editor-config-guard.sh"
guard_config
ARGS_LINE=""
if [[ ${#EXTRA[@]} -gt 0 ]]; then ARGS_LINE=" ${EXTRA[*]}"; fi
set +e
"$EDITOR_CMD" "$PROJECT" "-ExecutePythonScript=$SCRIPT$ARGS_LINE" \
  -unattended -nopause "$RHI" -nosplash -nosound -stdout -FullStdOutLogOutput \
  "${EDITOR_CONFIG_ARGS[@]}" "${THROTTLE[@]}" >"$LOG" 2>&1
STATUS=$?
set -e
python3 - "$LOG" "$STATUS" "$MARKER" <<'PY'
import sys
from pathlib import Path

log_path, status, marker = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
lines = log_path.read_text(errors='replace').splitlines()
errors = [line for line in lines if 'LogPython: Error' in line or 'Traceback (most recent call last)' in line]
for line in errors[:30]:
    print(f'  {line[:400]}', file=sys.stderr)
hits = [line.split('LogPython: ', 1)[1] for line in lines if 'LogPython: ' in line
        and line.split('LogPython: ', 1)[1].startswith(marker)]
problems = []
# A full editor that quits itself from Python (--editor) exits 1 without error.
if status != 0 and not (status == 1 and hits and not errors):
    problems.append(f'editor exited {status}')
if errors:
    problems.append(f'{len(errors)} Python error lines')
if not hits:
    problems.append(f'no completion marker {marker!r}')
if problems:
    sys.exit(f'FAIL {log_path}: ' + '; '.join(problems))
print(hits[-1])
PY
