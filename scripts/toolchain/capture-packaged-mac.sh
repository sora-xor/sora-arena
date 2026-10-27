#!/usr/bin/env bash
# Capture rendered baseline frames and practice frame time from a staged Mac
# package: Metal through -RenderOffscreen (no window, so a locked Mac still
# renders), never -NullRHI, at 1920x1080 under the platform's graphics preset.
#
# 1. The bundle: identifier org.sora.soraarena and a strict code signature.
# 2. fresh-startup: isolated untouched Title/focus assertion and one frame.
# 3. frontend: SoraArena.UIRendered.FrontEndScreens at 1920x1080, which saves
#    the title, main menu, chapter select, practice lobby, wallet, settings,
#    graphics, audio, subtitles, controls and rebind, accessibility, credits,
#    quit and pause screens.
# 4. capture: SoraCapture (Source/SoraArena/Private/SoraCaptureAutomation.cpp):
#    campaign beats in every chapter and each arena in practice, with frame
#    time measured in practice combat.
#
# Each launch runs as test-packaged-mac.sh launches it (its own empty
# -UserDir inside the sandboxed app's container, -LLM; see that script), and
# the run directory is cloned to OUTPUT/app-data afterwards (APFS clones, so
# the frames are not stored twice). OUTPUT/shots.tsv lists every frame with
# its size and SHA-256, OUTPUT/index.tsv what each campaign and practice frame
# shows, and OUTPUT/frame-times.tsv the stat-unit timers per arena and window
# beside the CSV profiles' own averages. OUTPUT/contention.txt says what else
# loaded the machine during the capture launch (other GPU work makes those
# frame times worthless). The run fails if a test fails, a frame is missing
# or a frame is not 1920x1080.
# Usage: capture-packaged-mac.sh ARCHIVE_DIRECTORY [output-directory]
#   SORA_CAPTURE_FILTER narrows the capture launch (default SoraCapture, e.g.
#   SoraCapture.Practice); SORA_CAPTURE_FRONTEND=0 skips the front-end launch.
#   SORA_CAPTURE_IDLE_WAIT=N waits up to N s for an idle GPU before the
#   capture launch (default 0: record, do not wait).
#   SORA_PACKAGED_TIMEOUT_SECONDS bounds each launch (default 3600).
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo 'Usage: capture-packaged-mac.sh ARCHIVE_DIRECTORY [output-directory]' >&2
  exit 2
fi
ARCHIVE_DIRECTORY="$(cd -- "$1" && pwd -P)"
OUTPUT="${2:-$PROJECT_ROOT/Saved/PackagedCapture/$(date -u +%Y%m%dT%H%M%SZ)}"
FILTER="${SORA_CAPTURE_FILTER:-SoraCapture}"
case "$FILTER" in
  ''|*[!A-Za-z0-9_.+]*) echo 'SORA_CAPTURE_FILTER must name automation tests (letters, digits, _ . +).' >&2; exit 2;;
esac
FRONTEND="${SORA_CAPTURE_FRONTEND:-1}"
TIMEOUT_SECONDS="${SORA_PACKAGED_TIMEOUT_SECONDS:-3600}"
case "$TIMEOUT_SECONDS" in
  ''|*[!0-9]*|0) echo 'SORA_PACKAGED_TIMEOUT_SECONDS must be a positive number of seconds.' >&2; exit 2;;
esac
IDLE_WAIT="${SORA_CAPTURE_IDLE_WAIT:-0}"
case "$IDLE_WAIT" in
  ''|*[!0-9]*) echo 'SORA_CAPTURE_IDLE_WAIT must be a number of seconds.' >&2; exit 2;;
esac
WIDTH=1920
HEIGHT=1080
MIN_FREE_GIB="${SORA_MIN_FREE_GIB:-30}"
FREE_GIB="$(df -Pk "$PROJECT_ROOT" | awk 'NR==2 {print int($4/1048576)}')"
if (( FREE_GIB < MIN_FREE_GIB )); then
  echo "Only ${FREE_GIB} GiB free; packaged capture requires at least ${MIN_FREE_GIB} GiB." >&2
  exit 1
fi

# UAT archives into ARCHIVE_DIRECTORY/Mac unless a component of that path
# already starts with the platform name (DeploymentContext.cs); stage-mac.sh
# and test-packaged-mac.sh apply the same rule.
APP="$(python3 - "$ARCHIVE_DIRECTORY" <<'PY'
from pathlib import Path
import sys
archive = Path(sys.argv[1])
named = any(part.lower().startswith('mac') for part in archive.parts[1:])
print((archive if named else archive / 'Mac') / 'SoraArena.app')
PY
)"
EXE="$APP/Contents/MacOS/SoraArena"
if [[ ! -x "$EXE" ]]; then
  echo "No packaged game at $EXE; run stage-mac.sh $ARCHIVE_DIRECTORY first." >&2
  exit 1
fi
if [[ -e "$OUTPUT" && -n "$(ls -A "$OUTPUT")" ]]; then
  echo "Output directory $OUTPUT is not empty; give a new one." >&2
  exit 2
fi
mkdir -p "$OUTPUT"

echo "Package: $APP"
BUNDLE_ID="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP/Contents/Info.plist")"
if [[ "$BUNDLE_ID" != 'org.sora.soraarena' ]]; then
  echo "FAIL: bundle identifier is $BUNDLE_ID, not org.sora.soraarena" >&2
  exit 1
fi
if ! /usr/bin/codesign --verify --deep --strict "$APP" 2>"$OUTPUT/codesign.log"; then
  cat "$OUTPUT/codesign.log" >&2
  echo "FAIL: the app's code signature does not verify" >&2
  exit 1
fi
/usr/bin/shasum -a 256 "$EXE" | awk '{print "Executable sha256 " $1}' | tee "$OUTPUT/package.txt"
SANDBOXED="$(/usr/bin/codesign -d --entitlements - --xml "$APP" 2>/dev/null | python3 -c '
import plistlib, sys
data = sys.stdin.buffer.read()
print("yes" if data and plistlib.loads(data).get("com.apple.security.app-sandbox") is True else "no")')"
if [[ "$SANDBOXED" == yes ]]; then
  APP_DATA="$HOME/Library/Containers/$BUNDLE_ID/Data/tmp/SoraPackagedCapture/$(date -u +%Y%m%dT%H%M%SZ)-$$"
  echo "The app is sandboxed; its writable run directory: $APP_DATA"
else
  APP_DATA="$OUTPUT/app-data"
fi
if [[ -e "$APP_DATA" ]]; then
  echo "The app's run directory $APP_DATA already exists." >&2
  exit 1
fi

# The whole GPU's busy figure (IOAccelerator "Device Utilization %", every
# process together); empty if the driver does not report it. Like
# other_load, it never fails, so a sample cannot stop the script (pipefail).
gpu_busy() {
  { /usr/sbin/ioreg -r -d 1 -w 0 -c IOAccelerator 2>/dev/null |
      sed -n 's/.*"Device Utilization %"=\([0-9]*\).*/\1/p' | head -n 1; } || true
}

# Processes other than this launch's game that can load the GPU: Blender, an
# Unreal editor or game, shader workers. Frame times measured beside them are
# not the game's own.
GPU_WORK='^(Blender|UnrealEditor|SoraArena|ShaderCompileWorker)$'

# other_load: every other process that uses at least half a core or is GPU
# work, as name:pid:cpu% separated by spaces.
other_load() {
  { ps -Axo pid=,pcpu=,comm= | awk -v exe="$EXE" -v gpu="$GPU_WORK" '
      index($0, exe) { next }
      {
        path = $0; sub(/^ *[0-9]+ +[0-9.]+ +/, "", path)
        count = split(path, part, "/"); name = part[count]; gsub(/ /, "_", name)
        if ($2 >= 50 || name ~ gpu) { printf "%s%s:%s:%.0f", sep, name, $1, $2; sep = " " }
      }'; } || true
}

# sample_load FILE: every 2 s until killed, the local time, GPU busy %,
# 1-minute load and other_load.
sample_load() {
  printf 'time\tgpu_busy\tload1\tothers\n' >"$1"
  while :; do
    printf '%s\t%s\t%s\t%s\n' "$(date +%Y-%m-%dT%H:%M:%S)" "$(gpu_busy)" \
      "$(sysctl -n vm.loadavg | awk '{print $2}')" "$(other_load)" >>"$1"
    sleep 2
  done
}

# wait_idle SECONDS: until, for ten seconds in a row, the GPU reads at most
# 10% busy and no other GPU work runs, or SECONDS pass.
wait_idle() {
  local limit="$1" waited=0 quiet=0 busy='' work=''
  while (( waited < limit )); do
    busy="$(gpu_busy)"
    work="$(other_load | tr ' ' '\n' | awk -F: -v gpu="$GPU_WORK" '$1 ~ gpu { printf "%s ", $1 }' || true)"
    if [[ -n "$busy" && -z "$work" ]] && (( busy <= 10 )); then quiet=$((quiet + 1)); else quiet=0; fi
    if (( quiet >= 10 )); then
      echo "The GPU is idle (${busy}% busy, no other GPU work) after ${waited} s of waiting."
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done
  echo "After ${limit} s the GPU is ${busy:-?}% busy${work:+ beside ${work% }}; capturing anyway." >&2
}

# launch NAME FILTER: one rendered launch running FILTER, with its own user
# directory and report; past the timeout SIGALRM kills it (status 142).
# OUTPUT/NAME.load.tsv samples what else ran meanwhile (sample_load).
# An offscreen, silent app has no visible window, so macOS App Nap coalesces
# its timers: in the first run a 5 ms sleep took 8.6-32 ms, and the 60 fps cap,
# which waits by sleeping, held the game at 20-25 fps. The trailing
# "-NSAppSleepDisabled YES" pair sets that AppKit default for this launch
# only (NSUserDefaults' argument domain), after which the sleep takes 6 ms.
# Explicitly name the project's entry map first, so Unreal does not mistake
# AppKit's bare YES argument for the startup URL.
launch() {
  local name="$1" filter="$2" status sampler
  echo "Launching the package ($name: $filter); log: $OUTPUT/$name.log" >&2
  touch "$OUTPUT/$name.started"
  sample_load "$OUTPUT/$name.load.tsv" &
  sampler=$!
  set +e
  /usr/bin/perl -e 'alarm shift @ARGV; exec @ARGV or die "exec failed: $!\n"' "$TIMEOUT_SECONDS" \
    "$EXE" /Engine/Maps/Entry -game -unattended -nopause -nosplash -nosound -stdout -FullStdOutLogOutput -LLM \
    -RenderOffscreen "-ResX=$WIDTH" "-ResY=$HEIGHT" -windowed \
    "-UserDir=$APP_DATA/$name-userdir" "-ExecCmds=Automation RunTests $filter;Quit" \
    "-ReportExportPath=$APP_DATA/$name-report" -NSAppSleepDisabled YES >"$OUTPUT/$name.log" 2>&1
  status=$?
  kill "$sampler" 2>/dev/null
  wait "$sampler" 2>/dev/null
  set -e
  echo "$status" >"$OUTPUT/$name.status"
  local waited=0
  while (( status > 128 && status != 142 && waited < 20 )) &&
        [[ -z "$(find "$HOME/Library/Logs/DiagnosticReports" -maxdepth 1 -name 'SoraArena-*.ips' \
                  -newer "$OUTPUT/$name.started" 2>/dev/null)" ]]; do
    sleep 1
    waited=$((waited + 1))
  done
  { find "$HOME/Library/Logs/DiagnosticReports" -maxdepth 1 -name 'SoraArena-*.ips' \
      -newer "$OUTPUT/$name.started" -exec cp -p {} "$OUTPUT/" \; -print 2>/dev/null || true; } |
    sed 's/^/Crash report: /' >&2
}

LAUNCHES=()
if [[ "$FRONTEND" != 0 ]]; then
  launch fresh-startup SoraStartup.RenderedFreshLaunch
  if ! python3 "$SCRIPT_DIR/verify_fresh_startup.py" "$APP_DATA/fresh-startup-report/index.json" \
    "$OUTPUT/fresh-startup.log" "$(cat "$OUTPUT/fresh-startup.status")" \
    "$APP_DATA/fresh-startup-userdir/Saved/Screenshots/SoraStartup/${WIDTH}x${HEIGHT}/01_Title.png" "$WIDTH" "$HEIGHT"; then
    # Preserve the failed startup before aborting; successful runs are cloned
    # once below, after navigation and capture have finished.
    if [[ "$APP_DATA" != "$OUTPUT/app-data" && -d "$APP_DATA" ]]; then
      /bin/cp -cRp "$APP_DATA" "$OUTPUT/app-data"
    fi
    exit 1
  fi
  LAUNCHES+=(fresh-startup)
  launch frontend SoraArena.UIRendered
  LAUNCHES+=(frontend)
fi
if (( IDLE_WAIT > 0 )); then
  wait_idle "$IDLE_WAIT"
fi
gpu_busy >"$OUTPUT/capture.gpu-before"
echo "GPU busy before the capture launch: $(cat "$OUTPUT/capture.gpu-before")%"
launch capture "$FILTER"
LAUNCHES+=(capture)
if [[ "$APP_DATA" != "$OUTPUT/app-data" && -d "$APP_DATA" ]]; then
  /bin/cp -cRp "$APP_DATA" "$OUTPUT/app-data"
fi

python3 - "$OUTPUT" "$WIDTH" "$HEIGHT" "$TIMEOUT_SECONDS" "${LAUNCHES[@]}" <<'PY'
import csv
import datetime
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

output, width, height, timeout = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
launches = sys.argv[5:]
data = output / 'app-data'
problems = []

print(f'{"RESULT":8} {"ERR":>4} {"WARN":>4} {"SEC":>7}  TEST')
for name in launches:
    status = int((output / f'{name}.status').read_text())
    log = (output / f'{name}.log').read_text(errors='replace')
    report_path = data / f'{name}-report' / 'index.json'
    if status == 142:
        problems.append(f'{name} timed out after {timeout} s')
    if not report_path.is_file():
        problems.append(f'{name} wrote no automation report (exit {status})')
        continue
    report = json.loads(report_path.read_text(encoding='utf-8-sig'))
    tests = sorted(report.get('tests', []), key=lambda item: item['fullTestPath'])
    found = sum(int(count) for count in re.findall(r"Found (\d+) automation tests based on", log))
    if not tests:
        problems.append(f'{name} ran no tests')
    if found and found != len(tests):
        problems.append(f'{name}: {found} tests were found but {len(tests)} were reported')
    failed = 0
    for test in tests:
        entries = [entry['event'] for entry in test.get('entries', [])]
        errors = [event['message'] for event in entries if event.get('type') == 'Error']
        warnings = [event['message'] for event in entries if event.get('type') == 'Warning']
        state = test.get('state', 'Unknown')
        print(f'{state:8} {len(errors):4} {len(warnings):4} {test.get("duration", 0.0):7.2f}  {test["fullTestPath"]}')
        for message in (errors + warnings)[:8]:
            print(f'           {message[:220]}')
        if state != 'Success':
            failed += 1
    if failed:
        problems.append(f'{name}: {failed} of {len(tests)} tests failed')
    if status != 0 and not failed:
        problems.append(f'{name} exited {status} although every reported test passed')

def png_size(path):
    with path.open('rb') as handle:
        head = handle.read(24)
    if head[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    return struct.unpack('>II', head[16:24])

rows = ['file\twidth\theight\tbytes\tsha256']
frames = sorted(data.glob(f'*-userdir/Saved/Screenshots/*/{width}x{height}/*.png'))
for frame in frames:
    size = png_size(frame)
    rows.append(f'{frame.relative_to(output)}\t{size[0] if size else "?"}\t{size[1] if size else "?"}\t'
                f'{frame.stat().st_size}\t{hashlib.sha256(frame.read_bytes()).hexdigest()}')
    if size != (width, height):
        problems.append(f'{frame.name} is {size}, not {width}x{height}')
wrong = [path for path in data.glob('*-userdir/Saved/Screenshots/*/*x*') if path.name != f'{width}x{height}']
for path in wrong:
    problems.append(f'frames were saved at {path.name}, not {width}x{height}: {path.relative_to(output)}')
(output / 'shots.tsv').write_text('\n'.join(rows) + '\n', encoding='utf-8')
print(f'{len(frames)} frames at {width}x{height}; list: {output / "shots.tsv"}')
if not frames:
    problems.append('no frames were saved')

index = sorted(data.glob(f'capture-userdir/Saved/Screenshots/SoraCapture/{width}x{height}/index.tsv'))
if index:
    (output / 'index.tsv').write_text(index[0].read_text(encoding='utf-8'), encoding='utf-8')
    listed = [line.split('\t', 1)[0] for line in index[0].read_text(encoding='utf-8').splitlines()[1:] if line]
    missing = [name for name in listed if not (index[0].parent / name).is_file()]
    if missing:
        problems.append(f'{len(missing)} indexed frames are missing: {", ".join(missing[:5])}')

def csv_profile(path):
    """Frames, per-column means and the SoraCaptureWindow label of one CSV profile."""
    with path.open(newline='', encoding='utf-8', errors='replace') as handle:
        rows = list(csv.reader(handle))
    header = rows[0] if rows else []
    columns = {name: index for index, name in enumerate(header)}
    wanted = ['FrameTime', 'GameThreadTime', 'RenderThreadTime', 'RHIThreadTime', 'GPUTime']
    sums, count = {name: 0.0 for name in wanted if name in columns}, 0
    for row in rows[1:]:
        if not row or row[0].startswith('[') or len(row) < len(header):
            break
        try:
            values = {name: float(row[columns[name]]) for name in sums}
        except ValueError:
            break
        for name, value in values.items():
            sums[name] += value
        count += 1
    metadata = {}
    for row in rows[1:]:
        if row and row[0].startswith('['):
            metadata.update({row[at].strip('[]').lower(): row[at + 1]
                             for at in range(0, len(row) - 1, 2) if row[at].startswith('[')})
    return count, {name: total / count for name, total in sums.items()} if count else {}, metadata.get('soracapturewindow', '')

GPU_WORK = ('Blender', 'UnrealEditor', 'SoraArena', 'ShaderCompileWorker')

# What else ran during the capture launch (sample_load in the shell above):
# (time, 1-minute load, {name: [(pid, cpu%)]}) every 2 s.
samples = []
load_path = output / 'capture.load.tsv'
before_path = output / 'capture.gpu-before'
gpu_before = before_path.read_text().strip() if before_path.is_file() else ''
if load_path.is_file():
    for line in load_path.read_text(encoding='utf-8').splitlines()[1:]:
        cells = line.split('\t')
        try:
            others = {}
            for item in (cells[3].split() if len(cells) > 3 else []):
                name, pid, cpu = item.rsplit(':', 2)
                others.setdefault(name, []).append((pid, float(cpu)))
            samples.append((datetime.datetime.fromisoformat(cells[0]), float(cells[2] or 0), others))
        except (IndexError, ValueError):
            continue  # a line cut short when the sampler was stopped

def beside(start, seconds):
    """Other GPU work and the median load in the samples from start to start + seconds."""
    inside = [sample for sample in samples if start <= sample[0] <= start + datetime.timedelta(seconds=seconds + 2)]
    work = sorted({name for _, _, others in inside for name in others if name in GPU_WORK})
    loads = sorted(load for _, load, _ in inside)
    return ('+'.join(work) if work else ('-' if inside else '?')), (loads[len(loads) // 2] if loads else '?')

timing_rows = ['arena\twindow\tframes\tseconds\tfps\tframe_mean_ms\tframe_p95_ms\tframe_p99_ms\tgame_ms\trender_ms\trhi_ms\t'
               'gpu_mean_ms\tgpu_p95_ms\tover_16_7ms\tcsv_frames\tcsv_frame_ms\tcsv_gpu_ms\tother_gpu_work\tload1']
# Both in the order they were measured: the CSV profiles are named by their
# start time, and the log has one SORA_FRAMETIME line per arena as it ends.
profiles = sorted(data.glob('capture-userdir/Saved/Profiling/CSV/Profile(*).csv'))
records = {path.name: path for path in data.glob(f'capture-userdir/Saved/Screenshots/SoraCapture/{width}x{height}/*_frametime.json')}
capture_log = output / 'capture.log'
measured = re.findall(r'SORA_FRAMETIME \{"arena":"([A-Za-z]+)"',
                      capture_log.read_text(errors='replace') if capture_log.is_file() else '')
# A failed test's log lines are echoed once more when it ends; keep the first.
ordered = [name for arena in dict.fromkeys(measured) for name in sorted(records) if name.endswith(f'_{arena}_frametime.json')]
if sorted(ordered) != sorted(records):
    print('Note: the log does not name every frame-time record; CSV columns left blank')
    ordered, profiles = sorted(records), []
windows = []
for path in (records[name] for name in ordered):
    record = json.loads(path.read_text(encoding='utf-8'))
    for window in record['windows']:
        windows.append((record, window))
if profiles and len(profiles) != len(windows):
    print(f'Note: {len(profiles)} CSV profiles for {len(windows)} measured windows; CSV and load columns left blank')
contended = []
for position, (record, window) in enumerate(windows):
    csv_frames, csv_values, label, work, load = 0, {}, '', '?', '?'
    if len(profiles) == len(windows):
        csv_frames, csv_values, label = csv_profile(profiles[position])
        # Profile(YYYYMMDD_HHMMSS).csv: the local time its window began.
        began = datetime.datetime.strptime(profiles[position].name[8:23], '%Y%m%d_%H%M%S')
        work, load = beside(began, window['seconds'])
    if label and label != window['window']:
        print(f'Note: {profiles[position].name} is a {label} window, not {record["arena"]} {window["window"]}; CSV columns left blank')
        csv_frames, csv_values, work, load = 0, {}, '?', '?'
    if work not in ('-', '?'):
        contended.append(f'{record["arena"]} {window["window"]} ({work})')
    frame, gpu = window['frame_ms'], window['gpu_ms']
    timing_rows.append('\t'.join(str(value) for value in [
        record['arena'], window['window'], window['frames'], window['seconds'], window['fps'], frame['mean'], frame['p95'],
        frame['p99'], window['game_ms']['mean'], window['render_ms']['mean'], window['rhi_ms']['mean'], gpu['mean'], gpu['p95'],
        window['frames_over_16_7ms'], csv_frames, round(csv_values.get('FrameTime', 0.0), 2), round(csv_values.get('GPUTime', 0.0), 2),
        work, load]))

contention = []
if samples:
    seen = {}
    for _, _, others in samples:
        for name, entries in others.items():
            entry = seen.setdefault(name, {'pids': set(), 'samples': 0, 'cpu': 0.0})
            entry['pids'].update(pid for pid, _ in entries)
            entry['samples'] += 1
            entry['cpu'] = max([entry['cpu']] + [cpu for _, cpu in entries])
    loads = sorted(load for _, load, _ in samples)
    contention.append(f'GPU busy before the capture launch: {gpu_before or "unknown"}%')
    contention.append(f'{len(samples)} samples every 2 s during the capture launch; median 1-minute load {loads[len(loads) // 2]}')
    for name, entry in sorted(seen.items(), key=lambda item: -item[1]['samples']):
        contention.append(f'  {name}: {len(entry["pids"])} process(es), in {entry["samples"]} of {len(samples)} samples, '
                          f'up to {entry["cpu"]:.0f}% CPU')
    if contended:
        contention.append('CONTENDED windows (other GPU work ran; not the game\'s own frame time): ' + '; '.join(contended))
    elif windows:
        contention.append('No other GPU work ran during any measured window.')
    (output / 'contention.txt').write_text('\n'.join(contention) + '\n', encoding='utf-8')

if windows:
    (output / 'frame-times.tsv').write_text('\n'.join(timing_rows) + '\n', encoding='utf-8')
    print('Frame time (ms; stat-unit timers, M1 Ultra, Mac preset):')
    for row in timing_rows:
        print('  ' + row.replace('\t', '  '))
    settings = windows[0][0]['settings']
    print('  settings: ' + ', '.join(f'{key}={value}' for key, value in settings.items()))
    for line in contention:
        print('  ' + line)
if problems:
    sys.exit('FAIL: ' + '; '.join(problems))
print(f'PASS: rendered capture in {output}')
PY
