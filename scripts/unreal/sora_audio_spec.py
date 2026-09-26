"""What the audio import builds: shared by import_audio.py and validate_audio_import.py.

Pure Python, no ``unreal``, so the host check and the editor scripts read one
definition. Its sources:

* the bus tree, default levels, user sliders, submix routing and ducking come
  from the runtime audio data (``Content/Data/audio.json``, built by
  scripts/audio/build_audio_data.py; docs/audio.md section 2). The two
  telegraph buses keep a volume floor, so their submixes feed Master directly
  while their sound classes stay under their parents;
* the SoundWaves are the WAV records of the two OWN manifests
  (``Original/manifest.json`` and ``Music/manifest.json``) and of the CC0
  derivatives' ledger (``CC0/manifest.json``, built by
  scripts/audio/build_cc0_audio.py), each checked against its SHA-256, its
  byte size and its own RIFF chunks. CC0 audio enters the repository only as
  those derivatives: every raw ``scripts/assets/manifests/audio_*.json``
  record stays ``storage: local-private``, ``committed: false``.

Every SoundWave takes the bus of the cues it plays in (section 3), and every
music piece's wave the Music bus. A wave that several ready cues share keeps
their common bus; one shared with a cue still needing its own sound (a
placeholder) takes the bus of its ready cue.
"""

import hashlib
import json
import math
import struct
from pathlib import Path


SOURCE = "Content/SourceArt/Audio"
DATA = "Content/Data/audio.json"
OWN_MANIFESTS = (f"{SOURCE}/Original/manifest.json", f"{SOURCE}/Music/manifest.json")
CC0_MANIFEST = f"{SOURCE}/CC0/manifest.json"
READY = ("ready-own", "ready-cc0")
AUDIO_LEDGERS = "scripts/assets/manifests"
GENERATED = "/Game/Generated/Audio"
BUSES = f"{GENERATED}/Buses"
SAMPLE_RATE = 48000

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


def check_raw_cc0_stays_local(root):
    """Count the raw CC0 audio records and refuse any committed: the repository
    takes only their derivatives (CC0_MANIFEST)."""
    records = 0
    for path in sorted((root / AUDIO_LEDGERS).glob("audio_*.json")):
        ledger = read_json(path)
        require(ledger.get("raw_committed") is False,
                f"{path.name}: raw audio is declared committed")
        for record in ledger["assets"]:
            records += 1
            require(record.get("committed") is False and record.get("storage") == "local-private",
                    f"{path.name}: raw {record.get('asset_id')} is committed; the repository takes only "
                    f"its derivatives ({CC0_MANIFEST}, scripts/audio/build_cc0_audio.py)")
    return records


def wave_records(root):
    """(manifest, record) of every WAV the OWN manifests and the CC0 derivatives' ledger list."""
    rows = []
    for manifest_path in OWN_MANIFESTS:
        manifest = read_json(root / manifest_path)
        require(manifest.get("schema_version") == 2 and manifest.get("tier") == "OWN",
                f"{manifest_path} is not a schema-2 OWN manifest")
        rows += [(manifest_path, record) for record in manifest["files"]]
    derivatives = read_json(root / CC0_MANIFEST)
    require(derivatives.get("schema_version") == 2 and derivatives.get("tier") == "PUB-CC0",
            f"{CC0_MANIFEST} is not a schema-2 PUB-CC0 ledger")
    for record in derivatives["records"]:
        require(record.get("tier") == "PUB-CC0" and record.get("storage") == "repo-lfs",
                f"{CC0_MANIFEST}: {record.get('asset_id')} is not a PUB-CC0 derivative in repo LFS")
        rows += [(CC0_MANIFEST, row) for row in record["files"]]
    return [(path, row) for path, row in rows if row["file"].endswith(".wav")]


def source_of(wave):
    """audio.json names a wave by its path under both roots; this is its WAV."""
    return f"{SOURCE}/{wave}.wav"


def resolve_buses(data):
    """Return {source file: bus} from the cues and the music pieces."""
    uses = {}
    for cue in data["cues"]:
        for wave in cue["waves"]:
            uses.setdefault(source_of(wave), []).append((cue["status"], cue["bus"], cue["id"]))
    for name, piece in data["music"]["pieces"].items():
        for wave in [piece["intro"], piece["full"], *piece["stems"].values()]:
            if wave:
                uses.setdefault(source_of(wave), []).append(("ready-own", "Music", f"music:{name}"))
    buses = {}
    for file, cues in uses.items():
        ready = {bus for status, bus, _ in cues if status in READY}
        candidates = ready or {bus for _, bus, _ in cues}
        require(len(candidates) == 1,
                f"{file} plays on several buses {sorted(candidates)} in "
                f"{sorted(cue for _, _, cue in cues)}; give it one")
        buses[file] = candidates.pop()
    return buses


def bus_tree(data):
    """Validate the data's buses and ducking; return (buses, ducking mixes)."""
    buses = data["buses"]
    names = [bus["id"] for bus in buses]
    require(len(names) == len(set(names)), "Duplicate bus in the audio data")
    by_name = {bus["id"]: bus for bus in buses}
    roots = [bus["id"] for bus in buses if not bus["parent"]]
    require(roots == ["Master"], f"The bus tree needs Master as its only root: {roots}")
    for bus in buses:
        require(not bus["parent"] or (bus["parent"] in by_name
                                      and names.index(bus["parent"]) < names.index(bus["id"])),
                f"Bus {bus['id']} has no parent listed before it")
        require(bus["default_db"] <= 0.0, f"Bus {bus['id']} would boost its sounds")
        # A telegraph bus keeps a floor under its parent's slider, so its
        # submix feeds Master; every other submix follows the class tree.
        if bus["floor_of"]:
            require(bus["submix_parent"] == "Master" and bus["floor_db"] < 0.0
                    and by_name.get(bus["floor_of"], {}).get("slider"),
                    f"Floored bus {bus['id']} must feed Master with a floor below 0 dB of a slider bus")
        else:
            require(bus["submix_parent"] == bus["parent"],
                    f"Bus {bus['id']} routes its submix past its parent without a floor")
    sliders = tuple(bus["id"] for bus in buses if bus["slider"])
    require(sorted(sliders) == sorted(USER_SLIDERS)
            and all(by_name[name]["slider"] == name for name in USER_SLIDERS),
            f"The user sliders must be the ESoraAudioBus buses {USER_SLIDERS}: {sliders}")
    for name in list(LOADING) + list(ALWAYS_PLAY) + list(UI_SOUND) + list(MUSIC):
        require(name in by_name, f"Audio policy names an unknown bus {name}")

    def ancestors(name):
        chain = []
        while by_name[name]["parent"]:
            name = by_name[name]["parent"]
            chain.append(name)
        return chain

    protected = set(NEVER_DUCKED)
    for name in NEVER_DUCKED:
        protected.update(ancestors(name))
    mixes = {}
    for rule in data["ducking"]:
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
    data = read_json(root / DATA)
    require(data["sample_rate_hz"] == SAMPLE_RATE, "The audio data changed its sample rate")
    buses, mixes = bus_tree(data)
    bus_of = resolve_buses(data)
    unknown = sorted(set(bus_of.values()) - {bus["id"] for bus in buses})
    require(not unknown, f"Audio is routed to buses the tree lacks: {unknown}")
    raw_cc0_records = check_raw_cc0_stays_local(root)

    waves = []
    for manifest_path, record in wave_records(root):
        relative = record["file"]
        require(relative.startswith(SOURCE + "/"), f"Audio outside {SOURCE}: {relative}")
        path = root / relative
        require(path.is_file(), f"Missing audio: {relative}")
        data = path.read_bytes()
        require(len(data) == record["bytes"]
                and hashlib.sha256(data).hexdigest() == record["sha256"],
                f"Audio does not match {manifest_path}: {relative}")
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
    require(not unused, f"Cues play audio no OWN manifest or CC0 ledger records: {unused[:5]}")
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
        "raw_cc0_records": raw_cc0_records,
        "cc0_waves": sum(1 for wave in waves if wave["source"].startswith(f"{SOURCE}/CC0/")),
    }


def gain_close(actual, expected_db):
    return math.isclose(actual, db_to_gain(expected_db), rel_tol=1e-4, abs_tol=1e-6)
