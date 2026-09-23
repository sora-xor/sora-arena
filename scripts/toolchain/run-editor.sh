#!/usr/bin/env bash
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
editor = Path(report['engine_root'])/'Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor'
if not report['build_ready'] or not editor.is_file():
    sys.exit('Pinned editor prerequisites are unavailable; run scripts/toolchain/doctor.py and build-mac.sh first.')
for name, value in [('EDITOR', str(editor)), ('DEVELOPER_DIR', report['developer_dir']),
                    ('SDKROOT', report['sdk_root']),
                    ('PROJECT', str(next(doctor.ROOT.glob('*.uproject'))))]:
    print('export '+name+'='+shlex.quote(value))
PY
)" || exit 1
eval "$TOOLCHAIN_EXPORTS"
exec "$EDITOR" "$PROJECT" "$@"
