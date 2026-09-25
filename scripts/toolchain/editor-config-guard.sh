# Sourced by the headless editor runners (run-automation-mac.sh, import-mac.sh).
#
# Two engine features rewrite project Config on every editor start: the
# Enhanced Input editor module upgrades the default input classes in
# DefaultInput.ini, and AndroidFileServer writes a fresh security token to
# DefaultEngine.ini. EDITOR_CONFIG_ARGS turns both off for that one editor
# process with command-line ini overrides, so the editor leaves Config alone
# and runs the legacy input classes that a packaged game uses.
#
# Nothing is copied back or deleted afterwards. The working tree is shared, and
# a Config file that changed during the run may hold someone else's edit. The
# guard names every file under Config/ that changed, appeared or disappeared,
# leaves it as it is, and fails the run.
EDITOR_CONFIG_ARGS=(
  '-ini:Engine:[ConsoleVariables]:EnhancedInput.bEnableAutoUpgrade=0'
  '-ini:Engine:[/Script/AndroidFileServerEditor.AndroidFileServerRuntimeSettings]:SecurityToken=SoraHeadlessEditor'
)

config_hashes() {
  (cd "$PROJECT_ROOT" && find Config -type f -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256)
}

# Call once, just before the first editor process starts.
guard_config() {
  CONFIG_SNAPSHOT="$(mktemp "${TMPDIR:-/tmp}/sora-editor-config.XXXXXX")"
  config_hashes >"$CONFIG_SNAPSHOT"
  trap check_config EXIT
}

check_config() {
  local status=$? changed
  changed="$( { config_hashes | diff "$CONFIG_SNAPSHOT" - || true; } | sed -n 's/^[<>] [0-9a-f]*  //p' | LC_ALL=C sort -u)"
  rm -f "$CONFIG_SNAPSHOT"
  if [[ -n "$changed" ]]; then
    echo 'FAIL: these Config files changed during the editor run and were left as they are:' >&2
    sed 's/^/  /' <<<"$changed" >&2
    echo 'Another writer or a new editor rewrite changed them. Review git diff -- Config;' \
      'never commit an AndroidFileServer SecurityToken.' >&2
    exit 1
  fi
  exit "$status"
}
