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
# UAT archives into ARCHIVE_DIRECTORY/Mac unless a component of that path
# already starts with the platform name (DeploymentContext.cs), as
# Local/Packages/mac-wavec-baseline does; test-packaged-mac.sh applies the same rule.
APP="$(python3 - "$ARCHIVE_DIRECTORY" "$(basename "$PROJECT" .uproject)" <<'PY'
from pathlib import Path
import sys
archive, name = Path(sys.argv[1]), sys.argv[2]
named = any(part.lower().startswith('mac') for part in archive.parts[1:])
print((archive if named else archive / 'Mac') / f'{name}.app')
PY
)"
APP_PLIST="$APP/Contents/Info.plist"
# On a restage Xcode's incremental package build syncs the new staged data into
# the app but skips its CodeSign step when the executable is unchanged, so a
# changed pak falls outside the seal. Only for that failure (every complaint is
# a staged file under Contents/UE), sign again as Xcode does: ad hoc, with the
# app's own entitlements.
if ! SIGNATURE_CHECK="$(/usr/bin/codesign --verify --deep --strict -vv "$APP" 2>&1)"; then
  if ! python3 - "$APP" "$SIGNATURE_CHECK" <<'PY'
import sys
app, check = sys.argv[1], sys.argv[2].splitlines()
staged = app + '/Contents/UE/'
sealed = [line for line in check if line == f'{app}: a sealed resource is missing or invalid']
files = [line for line in check if line not in sealed]
sys.exit(0 if sealed and files and all(
    line.split(': ', 1)[0] in ('file modified', 'file added', 'file missing')
    and line.split(': ', 1)[1].startswith(staged) for line in files) else 1)
PY
  then
    echo "$SIGNATURE_CHECK" >&2
    echo 'The archived Mac app has an invalid signature.' >&2
    exit 1
  fi
  echo "$SIGNATURE_CHECK" >&2
  echo 'Xcode left restaged data outside the seal; signing the archived app again.' >&2
  ENTITLEMENTS="$(mktemp "${TMPDIR:-/tmp}/sora-mac-entitlements.XXXXXX")"
  trap 'rm -f "$ENTITLEMENTS"' EXIT
  /usr/bin/codesign -d --entitlements - --xml "$APP" >"$ENTITLEMENTS"
  /usr/bin/codesign --force --sign - --entitlements "$ENTITLEMENTS" --timestamp=none \
    --generate-entitlement-der "$APP"
  /usr/bin/codesign --verify --deep --strict --verbose=2 "$APP"
fi
ACTUAL_BUNDLE_ID="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP_PLIST")"
if [[ "$ACTUAL_BUNDLE_ID" != 'org.sora.soraarena' ]]; then
  echo "Packaged Mac bundle identifier mismatch: expected org.sora.soraarena, got $ACTUAL_BUNDLE_ID" >&2
  exit 1
fi
echo "Verified Mac bundle identifier: $ACTUAL_BUNDLE_ID; app: $APP"
