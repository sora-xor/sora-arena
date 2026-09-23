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
  # UBT has compiled and linked the Mac game target but its nested Xcode
  # finalization can fail at this generated-scheme pre-action. Reuse that exact
  # scheme and Apple's signing path only for this specific observed failure.
  BUILD_LOG="$(mktemp "${TMPDIR:-/tmp}/sora-mac-game-build.XXXXXX")"
  trap 'rm -f "$BUILD_LOG"' EXIT
  set +e
  "$UE_ROOT/Engine/Build/BatchFiles/Mac/Build.sh" "$GAME_TARGET" Mac "$CONFIGURATION" \
    "-Project=$PROJECT" -WaitMutex -architecture=arm64 2>&1 | tee "$BUILD_LOG"
  PIPE_RESULTS=("${PIPESTATUS[@]}")
  set -e
  BUILD_STATUS="${PIPE_RESULTS[0]}"
  if [[ "${PIPE_RESULTS[1]}" -ne 0 ]]; then
    echo 'Mac game build log could not be captured.' >&2
    exit "${PIPE_RESULTS[1]}"
  fi
  if [[ "$BUILD_STATUS" -eq 0 ]]; then
    exit 0
  fi
  if ! grep -Fq 'ApplePostBuildSync Executing PostBuildSync' "$BUILD_LOG" ||
     ! grep -Fq "Run custom shell script 'Touch UBT generated tiles'" "$BUILD_LOG" ||
     ! grep -Fq 'ERROR: Failed to finalize the .app with Xcode' "$BUILD_LOG"; then
    exit "$BUILD_STATUS"
  fi
  WORKSPACE="$PROJECT_ROOT/Intermediate/ProjectFiles/${GAME_TARGET}_Mac_${GAME_TARGET}.xcworkspace"
  APP="$PROJECT_ROOT/Binaries/Mac/${GAME_TARGET}.app"
  if [[ ! -f "$WORKSPACE/contents.xcworkspacedata" ||
        ! -f "$PROJECT_ROOT/Binaries/Mac/$GAME_TARGET" ]]; then
    echo 'Mac game post-build recovery lacks a generated workspace or linked executable.' >&2
    exit "$BUILD_STATUS"
  fi
  echo 'Retrying exact generated Xcode scheme directly after UBT pre-action failure.' >&2
  UBT_NO_POST_DEPLOY=true "$DEVELOPER_DIR/usr/bin/xcodebuild" build \
    -workspace "$WORKSPACE" -scheme "$GAME_TARGET" -configuration "$CONFIGURATION" \
    -destination 'generic/platform=macOS' CODE_SIGN_ALLOW_ENTITLEMENTS_MODIFICATION=YES \
    -allowProvisioningUpdates UE_XCODE_BUILD_MODE=PostBuildSync
  /usr/bin/codesign --verify --deep --strict --verbose=2 "$APP"
  # The failed UBT action would normally run WriteMetadata after finalizing
  # the app. Complete that native action so UAT can consume its target receipt.
  METADATA="$PROJECT_ROOT/Intermediate/Build/Mac/arm64/$GAME_TARGET/$CONFIGURATION/TargetMetadata.json"
  python3 - "$METADATA" "$PROJECT_ROOT" "$GAME_TARGET" "$CONFIGURATION" <<'PY'
import json
from pathlib import Path
import sys

metadata, project_root, target, configuration = map(Path, sys.argv[1:])
data = json.loads(metadata.read_text())
receipt = data['Receipt']
expected = project_root / 'Binaries' / 'Mac' / f'{target}.target'
if (receipt['TargetName'] != str(target)
        or receipt['Platform'] != 'Mac'
        or receipt['Configuration'] != str(configuration)
        or Path(data['ReceiptFile']) != expected):
    raise SystemExit('UBT metadata does not match this Mac game build')
missing = [entry['Path'] for entry in receipt['BuildProducts']
           if not Path(entry['Path']).exists()]
if missing:
    raise SystemExit(f'UBT build products missing: {missing}')
PY
  DOTNET="$UE_ROOT/Engine/Binaries/ThirdParty/DotNet/10.0/mac-$(uname -m)/dotnet"
  UBT="$UE_ROOT/Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll"
  [[ -x "$DOTNET" && -f "$UBT" ]] || { echo 'Bundled UBT metadata writer unavailable.' >&2; exit 1; }
  "$DOTNET" "$UBT" -Mode=WriteMetadata -Input="$METADATA" -Version=2
  [[ -f "$PROJECT_ROOT/Binaries/Mac/$GAME_TARGET.target" ]] || {
    echo 'UBT did not write the Mac game receipt.' >&2; exit 1;
  }
  exit 0
fi
exec "$UE_ROOT/Engine/Build/BatchFiles/Mac/Build.sh" "$EDITOR_TARGET" Mac "$CONFIGURATION" \
  "-Project=$PROJECT" -WaitMutex -architecture=arm64
