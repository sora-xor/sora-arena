#!/usr/bin/env bash
# Cook Mac content with the same project-scoped Unreal/Xcode selection as builds.
# The cook commandlet starts the editor, so it gets the editor runners' Config
# guard: without it AndroidFileServer writes a SecurityToken into
# Config/DefaultEngine.ini. The log is kept under Saved/Cook/.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
TOOLCHAIN_EXPORTS="$(PYTHONDONTWRITEBYTECODE=1 python3 - "$SCRIPT_DIR" <<'PY'
import importlib.util, shlex, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('doctor', Path(sys.argv[1])/'doctor.py')
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)
report = doctor.inspect()
if not report['cook_ready']:
    sys.exit('Selected Unreal/Xcode/Metal cook prerequisites are not ready; run scripts/toolchain/doctor.py for details.')
project = next(doctor.ROOT.glob('*.uproject'))
for name, value in [('UE_ROOT', report['engine_root']), ('DEVELOPER_DIR', report['developer_dir']),
                    ('SDKROOT', report['sdk_root']), ('PROJECT', str(project))]:
    print('export '+name+'='+shlex.quote(value))
PY
)" || exit 1
eval "$TOOLCHAIN_EXPORTS"
EDITOR_CMD="$UE_ROOT/Engine/Binaries/Mac/UnrealEditor-Cmd"
if [[ ! -x "$EDITOR_CMD" ]]; then
  echo "UnrealEditor-Cmd is missing: $EDITOR_CMD" >&2
  exit 1
fi
COOK_LOG="$PROJECT_ROOT/Saved/Cook/$(date -u +%Y%m%dT%H%M%SZ).log"
mkdir -p "$(dirname -- "$COOK_LOG")"
echo "Cook log: $COOK_LOG" >&2
source "$SCRIPT_DIR/editor-config-guard.sh"
guard_config
python3 "$SCRIPT_DIR/mac_candidate.py" invalidate cook
CANDIDATE_START=""
if [[ -n "${SORA_CANDIDATE_SOURCE:-}" ]]; then
  : "${SORA_CANDIDATE_NATIVE:?Set the full native bridge source commit ID}"
  CANDIDATE_START="$PROJECT_ROOT/Saved/Qualification/MacArtifacts/cook-start.json"
  python3 "$SCRIPT_DIR/mac_candidate.py" begin cook "$CANDIDATE_START" \
    --source "$SORA_CANDIDATE_SOURCE" --native "$SORA_CANDIDATE_NATIVE"
fi
"$EDITOR_CMD" "$PROJECT" -run=Cook -TargetPlatform=Mac \
  -Unattended -NullRHI -NoSplash -NoSound -stdout -FullStdOutLogOutput \
  "${EDITOR_CONFIG_ARGS[@]}" "$@" 2>&1 | tee "$COOK_LOG"
python3 - "$COOK_LOG" <<'PY'
from pathlib import Path
import sys

lines = Path(sys.argv[1]).read_text(errors="replace").splitlines()
shader_failures = [line for line in lines if
    "Failed to compile Material for platform" in line or
    ("Cooking a material resource" in line and "valid ShaderMap" in line)]
if shader_failures:
    print("Mac cook rejected invalid material shader maps:", file=sys.stderr)
    for line in shader_failures[:12]:
        print(line, file=sys.stderr)
    sys.exit(1)
PY
if [[ -n "$CANDIDATE_START" ]]; then
  python3 "$SCRIPT_DIR/mac_candidate.py" finish "$CANDIDATE_START"
fi
