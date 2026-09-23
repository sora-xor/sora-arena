#!/usr/bin/env bash
# Stage and archive a previously built/cooked Mac game with pinned toolchains.
set -euo pipefail
if [[ $# -ne 1 ]]; then
  echo "usage: $0 ARCHIVE_DIRECTORY" >&2
  exit 2
fi
ARCHIVE_DIRECTORY="$(python3 - "$1" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
)"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TOOLCHAIN_EXPORTS="$(PYTHONDONTWRITEBYTECODE=1 python3 - "$SCRIPT_DIR" <<'PY'
import importlib.util, shlex, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('doctor', Path(sys.argv[1])/'doctor.py')
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)
report = doctor.inspect()
if not report['build_ready']:
    sys.exit('Selected Unreal/Xcode stage prerequisites are not ready; run scripts/toolchain/doctor.py for details.')
if report['engine_mode'] == 'interim_compile_diagnostic':
    print('INTERIM UE 5.8.3 STAGE DIAGNOSTIC ONLY; UE 5.8.2 release prerequisites remain unmet.',
          file=sys.stderr)
project = next(doctor.ROOT.glob('*.uproject'))
for name, value in [('UE_ROOT', report['engine_root']), ('DEVELOPER_DIR', report['developer_dir']),
                    ('SDKROOT', report['sdk_root']), ('PROJECT', str(project))]:
    print('export '+name+'='+shlex.quote(value))
PY
)" || exit 1
eval "$TOOLCHAIN_EXPORTS"
PROJECT_ROOT="$(dirname -- "$PROJECT")"
if [[ ! -x "$PROJECT_ROOT/Binaries/Mac/SoraArena.app/Contents/MacOS/SoraArena" ]]; then
  echo "Mac game target is missing; build it before staging." >&2
  exit 1
fi
if [[ ! -f "$PROJECT_ROOT/Binaries/Mac/SoraArena.target" ]]; then
  echo "Mac game target receipt is missing; finish the build before staging." >&2
  exit 1
fi
if [[ ! -f "$PROJECT_ROOT/Saved/Cooked/Mac/ue.projectstore" ]]; then
  echo "Mac cooked content is missing; run scripts/toolchain/cook-mac.sh first." >&2
  exit 1
fi
UAT="$UE_ROOT/Engine/Build/BatchFiles/RunUAT.sh"
if [[ ! -x "$UAT" ]]; then
  echo "RunUAT.sh is missing: $UAT" >&2
  exit 1
fi
"$UAT" BuildCookRun -project="$PROJECT" -platform=Mac \
  -clientconfig=Development -skipbuild -skipcook -stage -pak -package -archive \
  -archivedirectory="$ARCHIVE_DIRECTORY" -unattended -noP4
APP_PLIST="$ARCHIVE_DIRECTORY/Mac/$(basename "$PROJECT" .uproject).app/Contents/Info.plist"
ACTUAL_BUNDLE_ID="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP_PLIST")"
if [[ "$ACTUAL_BUNDLE_ID" != 'org.sora.soraarena' ]]; then
  echo "Packaged Mac bundle identifier mismatch: expected org.sora.soraarena, got $ACTUAL_BUNDLE_ID" >&2
  exit 1
fi
echo "Verified Mac bundle identifier: $ACTUAL_BUNDLE_ID"
