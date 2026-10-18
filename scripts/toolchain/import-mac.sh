#!/usr/bin/env bash
# Import the pinned source art with the headless Mac editor, then load every
# expected package with the editor validator. UnrealEditor-Cmd can exit 0 after
# a Python exception, so each step must also log its completion marker and no
# Python error.
# Usage: import-mac.sh [log-directory]
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
if [[ $# -gt 1 ]]; then
  echo 'Usage: import-mac.sh [log-directory]' >&2
  exit 2
fi
OUTPUT="${1:-$PROJECT_ROOT/Saved/Import/$(date -u +%Y%m%dT%H%M%SZ)}"
MIN_FREE_GIB="${SORA_MIN_FREE_GIB:-30}"
TOOLCHAIN_EXPORTS="$(PYTHONDONTWRITEBYTECODE=1 python3 - "$SCRIPT_DIR" <<'PY'
import importlib.util, shlex, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('doctor', Path(sys.argv[1])/'doctor.py')
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)
report = doctor.inspect()
editor = Path(report['engine_root'])/'Engine/Binaries/Mac/UnrealEditor-Cmd'
if not report['build_ready'] or not editor.is_file():
    sys.exit('Selected editor prerequisites are unavailable; run scripts/toolchain/doctor.py and build-mac.sh first.')
for name, value in [('EDITOR_CMD', str(editor)), ('DEVELOPER_DIR', report['developer_dir']),
                    ('SDKROOT', report['sdk_root']),
                    ('PROJECT', str(next(doctor.ROOT.glob('*.uproject'))))]:
    print('export '+name+'='+shlex.quote(value))
PY
)" || exit 1
eval "$TOOLCHAIN_EXPORTS"

require_free_disk() {
  local free_gib
  free_gib="$(df -Pk "$PROJECT_ROOT" | awk 'NR==2 {print int($4/1048576)}')"
  if (( free_gib < MIN_FREE_GIB )); then
    echo "Only ${free_gib} GiB free; asset import requires at least ${MIN_FREE_GIB} GiB." >&2
    exit 1
  fi
}
require_free_disk
mkdir -p "$OUTPUT"
# The importers load the project module, and Unreal does not rebuild it with
# -unattended. UBT decides what is stale and does nothing when it is current.
echo "Building the editor module; log: $OUTPUT/build.log" >&2
if ! "$SCRIPT_DIR/build-mac.sh" Development Editor >"$OUTPUT/build.log" 2>&1; then
  tail -n 20 "$OUTPUT/build.log" >&2
  echo "FAIL: build-mac.sh Development failed; see $OUTPUT/build.log" >&2
  exit 1
fi
# The host check verifies every source hash and yields the package count that
# the editor validator must load; a mismatch means a changed manifest.
SOURCE_CHECK="$(PYTHONDONTWRITEBYTECODE=1 python3 "$PROJECT_ROOT/scripts/unreal/validate_imported_assets.py" --source-only)"
EXPECTED_PACKAGES="$(sed -n 's/^SORA_ASSET_SOURCE_CHECK_COMPLETE: \([0-9][0-9]*\) expected Unreal packages$/\1/p' <<<"$SOURCE_CHECK")"
if [[ -z "$EXPECTED_PACKAGES" ]]; then
  echo "Source art check did not report an expected package count: $SOURCE_CHECK" >&2
  exit 1
fi
# The CC0 environment library reads the first-slice ledgers' raw files from the
# clone's Local/ tree (shared by git worktrees), checks every SHA-256 and the
# period-accuracy policy, and packs the separate AO/roughness/metal maps into
# ARM textures under Saved/ before the editor imports them.
PYTHONDONTWRITEBYTECODE=1 python3 "$PROJECT_ROOT/scripts/unreal/pack_cc0_environment.py" >&2
CC0_CHECK="$(PYTHONDONTWRITEBYTECODE=1 python3 "$PROJECT_ROOT/scripts/unreal/validate_cc0_environment.py" --source-only)"
EXPECTED_CC0="$(sed -n 's/^SORA_CC0_SOURCE_CHECK_COMPLETE: \([0-9][0-9]*\) expected Unreal packages$/\1/p' <<<"$CC0_CHECK")"
if [[ -z "$EXPECTED_CC0" ]]; then
  echo "CC0 environment check did not report an expected package count: $CC0_CHECK" >&2
  exit 1
fi
# The masters' Custom HLSL, wrapped as the 5.8 material translator wraps it,
# must compile with the engine's own DXC before an editor builds the graphs.
PYTHONDONTWRITEBYTECODE=1 python3 "$PROJECT_ROOT/scripts/unreal/check_cc0_custom_hlsl.py" >&2
# The audio checks verify the runtime audio data against the game, then the
# OWN audio hashes, loop chunks, bus tree and cue routing, and yield the audio
# package count its editor validator must load.
PYTHONDONTWRITEBYTECODE=1 python3 "$PROJECT_ROOT/scripts/audio/validate_audio_data.py"
AUDIO_CHECK="$(PYTHONDONTWRITEBYTECODE=1 python3 "$PROJECT_ROOT/scripts/unreal/validate_audio_import.py" --source-only)"
EXPECTED_AUDIO_PACKAGES="$(sed -n 's/^SORA_AUDIO_SOURCE_CHECK_COMPLETE: \([0-9][0-9]*\) expected Unreal packages .*$/\1/p' <<<"$AUDIO_CHECK")"
if [[ -z "$EXPECTED_AUDIO_PACKAGES" ]]; then
  echo "Source audio check did not report an expected package count: $AUDIO_CHECK" >&2
  exit 1
fi


source "$SCRIPT_DIR/editor-config-guard.sh"
guard_config

# run_step NAME SCRIPT MARKER: a LogPython message must begin with MARKER.
run_step() {
  local name="$1" script="$PROJECT_ROOT/scripts/unreal/$2" marker="$3"
  local log="$OUTPUT/$name.log" status
  require_free_disk
  echo "Running $2; log: $log" >&2
  set +e
  "$EDITOR_CMD" "$PROJECT" "-ExecutePythonScript=$script" \
    -unattended -nopause -nullrhi -nosplash -nosound -stdout -FullStdOutLogOutput \
    "${EDITOR_CONFIG_ARGS[@]}" >"$log" 2>&1
  status=$?
  set -e
  python3 - "$log" "$status" "$marker" <<'PY'
import sys
from pathlib import Path

log_path, status, marker = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
lines = log_path.read_text(errors='replace').splitlines()
errors = [line for line in lines if 'LogPython: Error' in line or 'Traceback (most recent call last)' in line]
for line in errors[:20]:
    print(f'  {line[:300]}', file=sys.stderr)
problems = []
if status != 0:
    problems.append(f'editor exited {status}')
if errors:
    problems.append(f'{len(errors)} Python error lines')
if not any(line.split('LogPython: ', 1)[1].startswith(marker) for line in lines if 'LogPython: ' in line):
    problems.append(f'no completion marker {marker!r}')
if problems:
    sys.exit(f'FAIL {log_path.name}: ' + '; '.join(problems))
print(next(line.split('LogPython: ', 1)[1] for line in lines
           if 'LogPython: ' in line and line.split('LogPython: ', 1)[1].startswith(marker)))
PY
}

# The palette step binds materials to meshes from the first step, the CC0
# library binds the palette's plaster and stone-path maps, and the validators
# read all three; the order is fixed.
run_step import-original import_original_assets.py 'SORA_ASSET_IMPORT_COMPLETE: '
run_step import-palette import_environment_palette.py 'NYAAGYU_PBR_READY: '
run_step import-cc0 import_cc0_environment.py 'SORA_CC0_ENVIRONMENT_READY: '
run_step validate validate_imported_assets.py \
  "SORA_ASSET_VALIDATION_COMPLETE: $EXPECTED_PACKAGES packages loaded with expected types"
run_step validate-cc0 validate_cc0_environment.py \
  "SORA_CC0_ENVIRONMENT_VALIDATED: $EXPECTED_CC0 packages loaded with expected types"
# Audio is independent of the art: sound waves, then the bus tree and ducking.
run_step import-audio import_audio.py 'SORA_AUDIO_IMPORT_COMPLETE: '
run_step validate-audio validate_audio_import.py \
  "SORA_AUDIO_VALIDATION_COMPLETE: $EXPECTED_AUDIO_PACKAGES packages loaded with expected types and routing"

echo "PASS: imported and loaded $EXPECTED_PACKAGES art, $EXPECTED_CC0 CC0 environment and $EXPECTED_AUDIO_PACKAGES audio packages; logs: $OUTPUT"
