#!/usr/bin/env bash
# Build the native C ABI only, then verify and stage it. Never links a full wallet SDK into UE.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
IROHA_SOURCE_ROOT="${IROHA_SOURCE_ROOT:-$PROJECT_ROOT/../iroha-arena}"
[[ -f "$IROHA_SOURCE_ROOT/crates/connect_norito_bridge/Cargo.toml" ]] || { echo 'Set IROHA_SOURCE_ROOT to the matching Iroha source checkout.' >&2; exit 1; }
IROHA_SOURCE_ROOT="$(cd -- "$IROHA_SOURCE_ROOT" && pwd)"
case "$(uname -s)" in
  Darwin) BRIDGE_PLATFORM=Mac; BRIDGE_LIBRARY=libconnect_norito_bridge.dylib ;;
  Linux) BRIDGE_PLATFORM=Linux; BRIDGE_LIBRARY=libconnect_norito_bridge.so ;;
  *) echo 'For Windows build connect_norito_bridge with Cargo/MSVC and run verify-bridge.py before staging in Binaries/Win64.' >&2; exit 1 ;;
esac
export CARGO_TARGET_DIR="${SORA_CONNECT_TARGET_DIR:-$IROHA_SOURCE_ROOT/target}"
(
  cd -- "$IROHA_SOURCE_ROOT"
  cargo build --locked --release --lib --jobs "${SORA_CONNECT_JOBS:-4}" -p connect_norito_bridge
)
BUILT_BRIDGE="$CARGO_TARGET_DIR/release/$BRIDGE_LIBRARY"
python3 "$SCRIPT_DIR/verify-bridge.py" "$BUILT_BRIDGE" --game-fixtures "$IROHA_SOURCE_ROOT/javascript/iroha_js/test/fixtures/game-v1-codec.json"
mkdir -p "$PROJECT_ROOT/Binaries/$BRIDGE_PLATFORM"
cp "$BUILT_BRIDGE" "$PROJECT_ROOT/Binaries/$BRIDGE_PLATFORM/$BRIDGE_LIBRARY"
python3 - "$IROHA_SOURCE_ROOT" "$PROJECT_ROOT/Binaries/$BRIDGE_PLATFORM/$BRIDGE_LIBRARY" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path
source, library = Path(sys.argv[1]), Path(sys.argv[2])
revision = subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
diff = subprocess.check_output(['git','-C',str(source),'diff','HEAD','--'])
header = source/'crates/connect_norito_bridge/include/connect_norito_bridge.h'
manifest = {'source_revision':revision, 'tracked_diff_sha256':hashlib.sha256(diff).hexdigest(),
            'header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),
            'library_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),
            'note':'Local source build; inspect untracked source files separately. Smoke verification is not live wallet or settlement qualification.'}
library.with_suffix(library.suffix+'.build.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Verified native bridge staged:', library)
PY
