#!/usr/bin/env bash
# Build the native C ABI, then verify and stage it with its committed source identity.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
IROHA_SOURCE_ROOT="${IROHA_SOURCE_ROOT:-$PROJECT_ROOT/../iroha-arena}"
[[ -f "$IROHA_SOURCE_ROOT/crates/connect_norito_bridge/Cargo.toml" ]] || { echo 'Set IROHA_SOURCE_ROOT to the matching Iroha source checkout.' >&2; exit 1; }
IROHA_SOURCE_ROOT="$(cd -- "$IROHA_SOURCE_ROOT" && pwd)"
case "$(uname -s)" in
  Darwin) BRIDGE_PLATFORM=Mac; BRIDGE_LIBRARY=libconnect_norito_bridge.dylib ;;
  Linux) BRIDGE_PLATFORM=Linux; BRIDGE_LIBRARY=libconnect_norito_bridge.so ;;
  *) echo 'ABI 30 Windows is blocked: the current native KAGEMUSHA backend has a cfg(not(unix)) compile_error. A platform port and Windows runtime qualification are required.' >&2; exit 1 ;;
esac
CHECK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/sora-connect-stage.XXXXXX")"
trap 'rm -rf -- "$CHECK_DIR"' EXIT
python3 - "$IROHA_SOURCE_ROOT" "$CHECK_DIR/source.json" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path
source, output = Path(sys.argv[1]), Path(sys.argv[2])
def git(*args):
    return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()
if git('status', '--porcelain=v1', '--untracked-files=all'):
    sys.exit('Native source must be clean and committed, including untracked files, before building or staging.')
files = ['Cargo.lock', 'crates/connect_norito_bridge/include/connect_norito_bridge.h']
files += ['javascript/iroha_js/test/fixtures/' + name + '.json' for name in
          ('game-v1-codec', 'nft-market-v1-codec', 'game-resource-v1-codec')]
for name in files:
    subprocess.run(['git', '-C', str(source), 'ls-files', '--error-unmatch', name],
                   stdout=subprocess.DEVNULL, check=True)
record = {'source_path': str(source), 'source_revision': git('rev-parse', 'HEAD'),
          'source_tree': git('rev-parse', 'HEAD^{tree}'), 'source_status': 'clean',
          'source_files_sha256': {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in files}}
output.write_text(json.dumps(record, indent=2) + '\n')
PY
export CARGO_TARGET_DIR="${SORA_CONNECT_TARGET_DIR:-$IROHA_SOURCE_ROOT/target}"
# Cargo resolves a relative target from its source working directory; keep
# the verifier and staging reads on that same directory after Cargo exits.
if [[ "$CARGO_TARGET_DIR" != /* ]]; then
  export CARGO_TARGET_DIR="$IROHA_SOURCE_ROOT/$CARGO_TARGET_DIR"
fi
(
  cd -- "$IROHA_SOURCE_ROOT"
  cargo build --locked --release --lib --jobs "${SORA_CONNECT_JOBS:-2}" -p connect_norito_bridge
)
BUILT_BRIDGE="$CARGO_TARGET_DIR/release/$BRIDGE_LIBRARY"
python3 "$SCRIPT_DIR/check-abi.py" --header "$IROHA_SOURCE_ROOT/crates/connect_norito_bridge/include/connect_norito_bridge.h" > "$CHECK_DIR/abi.txt"
cat "$CHECK_DIR/abi.txt"
python3 "$SCRIPT_DIR/verify-bridge.py" "$BUILT_BRIDGE" \
  --fixture-dir "$IROHA_SOURCE_ROOT/javascript/iroha_js/test/fixtures" > "$CHECK_DIR/smoke.json"
python3 - "$IROHA_SOURCE_ROOT" "$BUILT_BRIDGE" "$PROJECT_ROOT" "$BRIDGE_PLATFORM" "$CHECK_DIR" <<'PY'
import hashlib, json, os, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
source, built, project, platform, evidence = (Path(sys.argv[1]), Path(sys.argv[2]),
    Path(sys.argv[3]), sys.argv[4], Path(sys.argv[5]))
record = json.loads((evidence / 'source.json').read_text())
def git(*args):
    return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()
if (git('rev-parse', 'HEAD') != record['source_revision'] or
        git('status', '--porcelain=v1', '--untracked-files=all')):
    sys.exit('Native source changed during build/verification; no library was staged.')
for name, expected in record['source_files_sha256'].items():
    if hashlib.sha256((source / name).read_bytes()).hexdigest() != expected:
        sys.exit('Native source inputs changed during build/verification; no library was staged.')
smoke = json.loads((evidence / 'smoke.json').read_text())
abi = (evidence / 'abi.txt').read_text()
library_hash = hashlib.sha256(built.read_bytes()).hexdigest()
if (smoke['abi'] != 30 or smoke['required_symbols'] != 26 or smoke['sha256'] != library_hash
        or 'Checked 26 dynamic function-pointer types ' not in abi
        or smoke['native_game_builder']['canonical_cases'] != 8
        or len(smoke['native_game_builder']['canonical_actions']) != 7
        or not smoke['arena_join_terms_inspector']):
    sys.exit('Native evidence does not match the required ABI, features, or built output; no library was staged.')
record.update({'schema': 'sora.connect.bridge_build.v2', 'verified_at_utc': datetime.now(timezone.utc).isoformat(),
               'platform': platform, 'library_sha256': library_hash, 'abi_check': abi.strip(), 'native_smoke': smoke,
               'rustc': subprocess.check_output(['rustc', '-Vv'], cwd=source, text=True).strip(),
               'cargo': subprocess.check_output(['cargo', '--version'], cwd=source, text=True).strip(),
               'consumer_checks_sha256': {name: hashlib.sha256((project / name).read_bytes()).hexdigest()
                   for name in ('scripts/connect/check-abi.py', 'scripts/connect/verify-bridge.py',
                                'scripts/connect/build-bridge.sh', 'Source/SoraArena/Private/ArenaWalletSubsystem.cpp')},
               'note': 'Clean committed source and local native verification only. No live wallet, settlement, Windows runtime, or release-signing qualification.'})
destination = project / 'Binaries' / platform / built.name
destination.parent.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='.connect-stage-', dir=destination.parent) as temp:
    staged = Path(temp) / built.name
    shutil.copy2(built, staged)
    if hashlib.sha256(staged.read_bytes()).hexdigest() != library_hash:
        sys.exit('Native library changed while staging.')
    manifest = staged.with_suffix(staged.suffix + '.build.json')
    manifest.write_text(json.dumps(record, indent=2) + '\n')
    os.replace(staged, destination)
    os.replace(manifest, destination.with_suffix(destination.suffix + '.build.json'))
print('Verified native bridge staged:', destination)
print('Source:', record['source_revision'], 'Library SHA-256:', library_hash)
print('ABI 30; 26 Connect declarations; seven builders; eight fixture cases;',
      smoke['native_game_builder']['malformed_requests_rejected'], 'malformed requests rejected.')
PY
