#!/usr/bin/env bash
# Install only free art/source-control tools. No Apple/Epic login or license acceptance.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
if [[ "$(uname -s)" != Darwin ]]; then
  echo 'This installer currently supports macOS Homebrew only.' >&2
  exit 1
fi
command -v brew >/dev/null || { echo 'Install Homebrew from https://brew.sh first.' >&2; exit 1; }

# Refuse a silently drifting Homebrew version before changing the machine.
python3 - "$SCRIPT_DIR/versions.json" <<'PY'
import json, subprocess, sys
pins = json.load(open(sys.argv[1]))
for package, kind, key in [('git-lfs', 'formula', 'git_lfs'), ('blender', 'cask', 'blender')]:
    info = json.loads(subprocess.check_output(['brew', 'info', '--json=v2', '--'+kind, package]))
    version = info['formulae'][0]['versions']['stable'] if kind == 'formula' else info['casks'][0]['version']
    if version != pins[key]:
        sys.exit(f'{package}: Homebrew offers {version}, project pins {pins[key]}. Review versions.json before upgrading; nothing installed.')
PY
HOMEBREW_NO_AUTO_UPDATE=1 brew install git-lfs
HOMEBREW_NO_AUTO_UPDATE=1 brew install --cask blender
git -C "$PROJECT_ROOT" lfs install --local
git lfs version
blender --background --factory-startup --python-expr 'import bpy; print("SORA_BLENDER_VERIFIED=" + bpy.app.version_string)'
echo 'Free tools installed. Unreal Engine and compatible Xcode are separate prerequisites; run doctor.py.'
