#!/usr/bin/env bash
# Cook Mac content with the same project-scoped Unreal/Xcode selection as builds.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TOOLCHAIN_EXPORTS="$(PYTHONDONTWRITEBYTECODE=1 python3 - "$SCRIPT_DIR" <<'PY'
import importlib.util, shlex, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('doctor', Path(sys.argv[1])/'doctor.py')
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)
report = doctor.inspect()
if not report['build_ready']:
    sys.exit('Selected Unreal/Xcode cook prerequisites are not ready; run scripts/toolchain/doctor.py for details.')
if report['engine_mode'] == 'interim_compile_diagnostic':
    print('INTERIM UE 5.8.3 COOK DIAGNOSTIC ONLY; UE 5.8.2 release prerequisites remain unmet.',
          file=sys.stderr)
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
exec "$EDITOR_CMD" "$PROJECT" -run=Cook -TargetPlatform=Mac \
  -Unattended -NullRHI -NoSplash -NoSound -stdout -FullStdOutLogOutput "$@"
