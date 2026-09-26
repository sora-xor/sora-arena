"""What the audio import builds: shared by import_audio.py and validate_audio_import.py.

Pure Python, no ``unreal``, so the host check and the editor scripts read one
definition. Its sources:

* the bus tree, default levels, user sliders and ducking come from the cue
  proposal (``Content/SourceArt/Audio/cues.proposed.json``, docs/audio.md
  section 2);
* the SoundWaves are the WAV records of the two OWN manifests
  (``Original/manifest.json`` and ``Music/manifest.json``), each checked
  against its SHA-256, its byte size and its own RIFF chunks;
* a CC0 audio record would be imported only once the ledger admits it to the
  repository. Today every ``scripts/assets/manifests/audio_*.json`` record is
  ``storage: local-private``, ``committed: false``, and a promoted record fails
  here until its import route is defined.

Every SoundWave takes the bus of the cues it plays in (section 3). A wave
that several ready cues share keeps their common bus; one shared with a cue
still needing its own sound (a placeholder) takes the bus of its ready cue.
A cue has one bus, so a cue that mixes buses names its exceptions in
BUS_OVERRIDES.
"""

import hashlib
import json
import math
import struct
from pathlib import Path


SOURCE = "Content/SourceArt/Audio"
PROPOSAL = f"{SOURCE}/cues.proposed.json"
OWN_MANIFESTS = (f"{SOURCE}/Original/manifest.json", f"{SOURCE}/Music/manifest.json")
AUDIO_LEDGERS = "scripts/assets/manifests"
GENERATED = "/Game/Generated/Audio"
BUSES = f"{GENERATED}/Buses"
SAMPLE_RATE = 48000

# Files whose bus differs from their cue's. site.restored plays on UI, but its
# note and docs/audio.md section 3.5 keep its stinger on the Music bus.
BUS_OVERRIDES = {
    f"{SOURCE}/Music/Stingers/mus_sting_site_restored.wav": "Music",
}

# ESoraAudioBus order (Source/SoraArena/Public/SoraSettings.h): the six user
# sliders, each a bus of its own name.
USER_SLIDERS = ("Master", "Music", "SFX", "Voice", "UI", "Ambience")

# How each bus's sounds load (ESoundWaveLoadingBehavior). A bus not listed
# inherits from its nearest listed ancestor; the waves themselves inherit.
# Telegraphs and interface sounds keep their first chunk resident so they are
# never late; music and dialogue stream on demand.
LOADING = {
    "Music": "LOAD_ON_DEMAND",
    "SFX": "PRIME_ON_LOAD",
    "SFX_Telegraph": "RETAIN_ON_LOAD",
    "Voice": "LOAD_ON_DEMAND",
    "UI": "RETAIN_ON_LOAD",
    "Ambience": "PRIME_ON_LOAD",
}
# Boss telegraphs and captioned barks always win the voice-priority sort
# (section 2: never ducked or virtualised).
ALWAYS_PLAY = frozenset({"SFX_Telegraph", "Voice_Barks"})
# Interface sounds keep playing while the game is paused.
UI_SOUND = frozenset({"UI"})
MUSIC = frozenset({"Music"})
# Buses no ducking may lower, directly or through an ancestor.
NEVER_DUCKED = frozenset({"SFX_Telegraph", "Voice_Barks"})

# The final limiter on the Master submix (section 2: -1 dBTP). Unreal's
# limiter reads sample peaks, not true peaks; the packaged mix is still to be
# measured (section 4.1).
MASTER_LIMITER = {
    "threshold_db": -1.0,
    "look_ahead_ms": 5.0,
    "attack_ms": 1.0,
    "release_ms": 100.0,
    "knee_db": 0.0,
}

# Stems and loop mixes must stay sample-locked while silent, and telegraphs
# are never virtualised; everything else restarts on realisation.
PLAY_WHEN_SILENT = "PLAY_WHEN_SILENT"
RESTART = "RESTART"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def class_path(bus):
    return f"{BUSES}/SC_{bus}"


def submix_path(bus):
    return f"{BUSES}/SMX_{bus}"


def mix_path(trigger):
    return f"{BUSES}/SMIX_Duck_{trigger}"


LIMITER_PATH = f"{BUSES}/SFXP_MasterLimiter"


def object_path(package):
    return f"{package}.{package.rsplit('/', 1)[1]}"


def db_to_gain(db):
    return 10.0 ** (db / 20.0)


def read_json(path):
    require(path.is_file(), f"Missing audio source data: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def wav_layout(data, name):
    """Return (sample rate, channels, bits, frames, smpl loops as (start, end))."""
    require(data[:4] == b"RIFF" and data[8:12] == b"WAVE", f"Not a RIFF WAVE file: {name}")
    chunks = {}
    offset = 12
    while offset + 8 <= len(data):
        chunk_id = data[offset:offset + 4].decode("latin-1")
        size = struct.unpack("<I", data[offset + 4:offset + 8])[0]
        require(chunk_id not in chunks, f"Repeated {chunk_id!r} chunk in {name}")
        chunks[chunk_id] = data[offset + 8:offset + 8 + size]
        offset += 8 + size + (size & 1)
    require("fmt " in chunks and "data" in chunks, f"WAV without fmt or data chunk: {name}")
    fmt = chunks["fmt "]
    audio_format, channels, rate = struct.unpack("<HHI", fmt[:8])
    bits = struct.unpack("<H", fmt[14:16])[0]
    require(audio_format == 1, f"WAV is not integer PCM: {name}")
    frames = len(chunks["data"]) // (channels * bits // 8)
    loops = []
    if "smpl" in chunks:
        smpl = chunks["smpl"]
        count = struct.unpack("<I", smpl[28:32])[0]
        for index in range(count):
            _, loop_type, start, end, _, play_count = struct.unpack(
                "<6I", smpl[36 + 24 * index:60 + 24 * index])
            require(loop_type == 0 and play_count == 0,
                    f"Only endless forward smpl loops are expected: {name}")
            loops.append((start, end))
    return rate, channels, bits, frames, loops


def check_ledger_admits_no_cc0(root):
    """Count the CC0 audio records and refuse any admitted to the repository."""
    records = 0
    for path in sorted((root / AUDIO_LEDGERS).glob("audio_*.json")):
        ledger = read_json(path)
        require(ledger.get("raw_committed") is False,
                f"{path.name}: raw audio is declared committed")
        for record in ledger["assets"]:
            records += 1
            require(record.get("committed") is False and record.get("storage") == "local-private",
                    f"{path.name}: {record.get('asset_id')} is admitted to the repository; "
                    "define its import route (bus, asset path) in sora_audio_spec.py first")
    return records


def resolve_buses(proposal):
    """Return {source file: bus} from the cues and music states."""
    uses = {}
    for cue in proposal["cues"]:
        for file in cue["files"]:
            uses.setdefault(file, []).append((cue["status"], cue["bus"], cue["id"]))
    for state in proposal["music"]["states"]:
        for file in state["files"]:
            uses.setdefault(file, []).append(("ready-own", "Music", f"music:{state['state']}"))
    buses = {}
    for file, bus in BUS_OVERRIDES.items():
        require(file in uses and bus not in {cue_bus for _, cue_bus, _ in uses[file]},
                f"Bus override for {file} is stale: its cues already play it on {bus}")
    for file, cues in uses.items():
        if file in BUS_OVERRIDES:
            buses[file] = BUS_OVERRIDES[file]
            continue
        ready = {bus for status, bus, _ in cues if status == "ready-own"}
        candidates = ready or {bus for _, bus, _ in cues}
        require(len(candidates) == 1,
                f"{file} plays on several buses {sorted(candidates)} in "
                f"{sorted(cue for _, _, cue in cues)}; give it one")
        buses[file] = candidates.pop()
    return buses


def bus_tree(proposal):
    """Validate the proposal's buses and ducking; return (buses, ducking mixes)."""
    buses = proposal["buses"]
    names = [bus["id"] for bus in buses]
    require(len(names) == len(set(names)), "Duplicate bus in the cue proposal")
    by_name = {bus["id"]: bus for bus in buses}
    roots = [bus["id"] for bus in buses if bus["parent"] is None]
    require(roots == ["Master"], f"The bus tree needs Master as its only root: {roots}")
    for bus in buses:
        require(bus["parent"] is None or (bus["parent"] in by_name
                                          and names.index(bus["parent"]) < names.index(bus["id"])),
                f"Bus {bus['id']} has no parent listed before it")
        require(bus["default_db"] <= 0.0, f"Bus {bus['id']} would boost its sounds")
    sliders = tuple(bus["id"] for bus in buses if "user_slider" in bus)
    require(sorted(sliders) == sorted(USER_SLIDERS)
            and all(by_name[name].get("user_slider") == name for name in USER_SLIDERS),
            f"The user sliders must be the ESoraAudioBus buses {USER_SLIDERS}: {sliders}")
    for name in list(LOADING) + list(ALWAYS_PLAY) + list(UI_SOUND) + list(MUSIC):
        require(name in by_name, f"Audio policy names an unknown bus {name}")

    def ancestors(name):
        chain = []
        while by_name[name]["parent"] is not None:
            name = by_name[name]["parent"]
            chain.append(name)
        return chain

    protected = set(NEVER_DUCKED)
    for name in NEVER_DUCKED:
        protected.update(ancestors(name))
    mixes = {}
    for rule in proposal["ducking"]:
        require(rule["trigger"] in by_name and rule["target"] in by_name,
                f"Ducking names an unknown bus: {rule}")
        require(rule["target"] not in protected,
                f"Ducking {rule['target']} would lower a telegraph bus: {rule}")
        require(rule["db"] < 0.0 and rule["attack_ms"] > 0 and rule["release_ms"] > 0,
                f"Ducking must lower its target over a positive attack and release: {rule}")
        mix = mixes.setdefault(rule["trigger"], {
            "trigger": rule["trigger"], "attack_ms": rule["attack_ms"],
            "release_ms": rule["release_ms"], "targets": []})
        require((mix["attack_ms"], mix["release_ms"]) == (rule["attack_ms"], rule["release_ms"]),
                f"One trigger's ducking needs one attack and release: {rule['trigger']}")
        require(rule["target"] not in [target for target, _ in mix["targets"]],
                f"Duplicate ducking of {rule['target']} by {rule['trigger']}")
        mix["targets"].append((rule["target"], rule["db"]))
    for mix in mixes.values():
        # A trigger bus's sub-buses duck the same targets (Voice_Barks is Voice).
        mix["sources"] = [name for name in names
                          if name == mix["trigger"] or mix["trigger"] in ancestors(name)]
    return buses, list(mixes.values())


def load(root):
    """Return the complete, verified import spec for the project at ``root``."""
    root = Path(root)
    proposal = read_json(root / PROPOSAL)
    require(proposal["sample_rate_hz"] == SAMPLE_RATE, "The cue proposal changed its sample rate")
    buses, mixes = bus_tree(proposal)
    bus_of = resolve_buses(proposal)
    unknown = sorted(set(bus_of.values()) - {bus["id"] for bus in buses})
    require(not unknown, f"Audio is routed to buses the tree lacks: {unknown}")
    cc0_records = check_ledger_admits_no_cc0(root)

    waves = []
    for manifest_path in OWN_MANIFESTS:
        manifest = read_json(root / manifest_path)
        require(manifest.get("schema_version") == 2 and manifest.get("tier") == "OWN",
                f"{manifest_path} is not a schema-2 OWN manifest")
        for record in manifest["files"]:
            relative = record["file"]
            if not relative.endswith(".wav"):
                continue
            require(relative.startswith(SOURCE + "/"), f"Audio outside {SOURCE}: {relative}")
            path = root / relative
            require(path.is_file(), f"Missing OWN audio: {relative}")
            data = path.read_bytes()
            require(len(data) == record["bytes"]
                    and hashlib.sha256(data).hexdigest() == record["sha256"],
                    f"OWN audio does not match its manifest: {relative}")
            rate, channels, bits, frames, loops = wav_layout(data, relative)
            qa = record["qa"]
            require(rate == SAMPLE_RATE == qa["sr"] and channels == qa["channels"] and bits == 24,
                    f"Unexpected WAV format for {relative}: {rate} Hz, {channels} ch, {bits} bit")
            require(abs(frames / rate - qa["seconds"]) < 0.002,
                    f"{relative} length differs from its QA record")
            looping = record["loop"]
            require(isinstance(looping, bool), f"{relative} has no loop flag")
            if looping:
                # One smpl loop over the whole file; the RIFF end is inclusive.
                require(loops == [(0, frames - 1)] and qa["loop"] == [0, frames - 1],
                        f"{relative} must loop its whole file: smpl {loops}, {frames} frames")
            else:
                require(not loops and qa["loop"] is None, f"One-shot {relative} carries a loop")
            require(relative in bus_of, f"No cue or music state plays {relative}")
            bus = bus_of[relative]
            stem = Path(relative).stem
            folder = str(Path(relative).parent.relative_to(SOURCE)).replace("\\", "/")
            package = f"{GENERATED}/{folder}/{stem}"
            waves.append({
                "source": relative,
                "package": package,
                "object_path": object_path(package),
                "bus": bus,
                "loop": looping,
                "frames": frames,
                "channels": channels,
                "smpl_loop": loops[0] if loops else None,
                "virtualization": PLAY_WHEN_SILENT
                if bus == "SFX_Telegraph" or (bus == "Music" and looping) else RESTART,
            })
    unused = sorted(set(bus_of) - {wave["source"] for wave in waves})
    require(not unused, f"Cues play audio no OWN manifest records: {unused[:5]}")
    packages = [wave["package"] for wave in waves]
    require(len(packages) == len(set(packages)), "Two source WAVs map to one Unreal package")

    expected = {wave["object_path"]: "SoundWave" for wave in waves}
    for bus in buses:
        expected[object_path(class_path(bus["id"]))] = "SoundClass"
        expected[object_path(submix_path(bus["id"]))] = "SoundSubmix"
    for mix in mixes:
        expected[object_path(mix_path(mix["trigger"]))] = "SoundMix"
    expected[object_path(LIMITER_PATH)] = "SubmixEffectDynamicsProcessorPreset"
    return {
        "buses": buses,
        "mixes": mixes,
        "waves": waves,
        "expected": expected,
        "cc0_records": cc0_records,
    }


def gain_close(actual, expected_db):
    return math.isclose(actual, db_to_gain(expected_db), rel_tol=1e-4, abs_tol=1e-6)
