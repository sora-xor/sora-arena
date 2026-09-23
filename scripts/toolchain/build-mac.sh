#!/usr/bin/env bash
# Build the project editor or game with project-scoped Xcode selection.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONFIGURATION="${1:-Development}"
TARGET_KIND="${2:-Editor}"
case "$CONFIGURATION" in Development|DebugGame) ;; *) echo 'Usage: build-mac.sh [Development|DebugGame] [Editor|Game]' >&2; exit 2;; esac
case "$TARGET_KIND" in Editor|Game) ;; *) echo 'Usage: build-mac.sh [Development|DebugGame] [Editor|Game]' >&2; exit 2;; esac
TOOLCHAIN_EXPORTS="$(PYTHONDONTWRITEBYTECODE=1 python3 - "$SCRIPT_DIR" <<'PY'
import importlib.util, shlex, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('doctor', Path(sys.argv[1])/'doctor.py')
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)
report = doctor.inspect()
if not report['build_ready']:
    sys.exit('Selected Unreal/Xcode build prerequisites are not ready; run scripts/toolchain/doctor.py for details.')
if report['engine_mode'] == 'interim_compile_diagnostic':
    print('INTERIM UE 5.8.3 COMPILE DIAGNOSTIC ONLY; UE 5.8.2 release prerequisites remain unmet.',
          file=sys.stderr)
project = next(doctor.ROOT.glob('*.uproject'))
for name, value in [('UE_ROOT', report['engine_root']), ('DEVELOPER_DIR', report['developer_dir']),
                    ('SDKROOT', report['sdk_root']),
                    ('PROJECT', str(project)), ('EDITOR_TARGET', project.stem+'Editor'),
                    ('GAME_TARGET', project.stem)]:
    print('export '+name+'='+shlex.quote(value))
PY
)" || exit 1
eval "$TOOLCHAIN_EXPORTS"
if [[ "$TARGET_KIND" == Game ]]; then
  # UBT-launched Xcode inherits UBA_DETOURED and fails the generated scheme's
  # pre-action on this Mac. Its supported -NoUBA flag disables that detour.
  exec "$UE_ROOT/Engine/Build/BatchFiles/Mac/Build.sh" "$GAME_TARGET" Mac "$CONFIGURATION" \
    "-Project=$PROJECT" -WaitMutex -architecture=arm64 -NoUBA
fi
exec "$UE_ROOT/Engine/Build/BatchFiles/Mac/Build.sh" "$EDITOR_TARGET" Mac "$CONFIGURATION" \
  "-Project=$PROJECT" -WaitMutex -architecture=arm64
