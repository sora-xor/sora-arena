#!/usr/bin/env bash
# Run rendered game automation (art-review or baseline captures) in the
# pinned editor binary's standalone game mode, against this checkout's
# uncooked Content/Generated: faster than a cook/stage for art iteration.
#
#   scripts/toolchain/capture-editor-game.sh <automation filter> [width] [height]
#
# Same flags as capture-packaged-mac.sh's launch: offscreen Metal, unattended,
# App Nap disabled for this launch. Frames land under Saved/Screenshots/ (for
# SoraCapture.ArtReview: Saved/Screenshots/SoraArtReview/<w>x<h>/). These are
# uncooked editor-binary game frames, labelled as such; packaged captures
# remain the release evidence. SORA_EXEC_PREFIX="cvar value," (comma-separated) runs console
# commands before the tests (art-review A/B switches).
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
FILTER="${1:?Usage: capture-editor-game.sh <automation filter> [width] [height]}"
WIDTH="${2:-1920}"
HEIGHT="${3:-1080}"
LOG="$PROJECT_ROOT/Saved/ClaudeArt/logs/game-$(echo "$FILTER" | tr -c 'A-Za-z0-9.' '_')-$(date +%H%M%S).log"
mkdir -p "$(dirname "$LOG")"
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
source "$SCRIPT_DIR/editor-config-guard.sh"
guard_config
echo "Game automation $FILTER at ${WIDTH}x${HEIGHT}; log: $LOG" >&2
set +e
"$EDITOR" "$PROJECT" -game -unattended -nopause -nosplash -nosound -stdout -FullStdOutLogOutput \
  -RenderOffscreen "-ResX=$WIDTH" "-ResY=$HEIGHT" -windowed -NoTextureStreaming \
  "-ExecCmds=${SORA_EXEC_PREFIX:-}Automation RunTests $FILTER;Quit" "${EDITOR_CONFIG_ARGS[@]}" -NSAppSleepDisabled YES >"$LOG" 2>&1
STATUS=$?
set -e
grep -E "SORA_ART_REVIEW_FRAME|Test Completed|Error: |LogAutomationController: .*(Fail|Success)" "$LOG" | grep -v "UnifiedErrorTest\|Condition failed" | tail -30 || true
exit "$STATUS"
