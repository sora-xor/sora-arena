"""Validate the audio packages that import_audio.py builds.

Run in the pinned UE editor with ``-ExecutePythonScript=<this file>`` after
import_audio.py. For the host check of the sources alone (hashes, WAV loop
chunks, bus tree, ducking and cue routing), run ``python3
scripts/unreal/validate_audio_import.py --source-only``; it cannot establish
that any Unreal package exists.

The editor check fails unless /Game/Generated/Audio holds exactly the expected
packages and each has the expected class, and:

* every submix and sound class sits in the bus tree of docs/audio.md section
  2 (the telegraph buses' submixes feed Master for their floor), with unity
  submix levels, the Master limiter and nothing else in an effect chain;
* every sound class carries its bus's default level, flags, loading
  behaviour, submix and passive ducking mixes;
* every ducking mix lowers exactly its targets over its attack and release;
* every SoundWave is in its bus's class with no submix of its own, and loops
  if and only if its manifest marks it a loop, with the loop region Unreal
  read from the WAV's smpl chunk spanning the whole file.
"""

from pathlib import Path
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sora_audio_spec as spec  # noqa: E402

require = spec.require


def names(objects):
    return [item.get_path_name() if item is not None else None for item in objects]


def validate_buses(unreal, audio):
    load = unreal.EditorAssetLibrary.load_asset
    buses = audio["buses"]
    children = {bus["id"]: [child["id"] for child in buses if child["parent"] == bus["id"]]
                for bus in buses}
    submix_children = {bus["id"]: [child["id"] for child in buses if child["submix_parent"] == bus["id"]]
                       for bus in buses}
    limiter = load(spec.object_path(spec.LIMITER_PATH))
    settings = limiter.get_editor_property("settings")
    expected_limiter = {
        "dynamics_processor_type": unreal.SubmixEffectDynamicsProcessorType.LIMITER,
        "peak_mode": unreal.SubmixEffectDynamicsPeakMode.PEAK,
        "link_mode": unreal.SubmixEffectDynamicsChannelLinkMode.PEAK,
        "analog_mode": False,
        "bypass": False,
    }
    for name, value in expected_limiter.items():
        require(settings.get_editor_property(name) == value,
                f"Master limiter {name} is {settings.get_editor_property(name)}, expected {value}")
    for name, value in (("threshold_db", spec.MASTER_LIMITER["threshold_db"]),
                        ("knee_bandwidth_db", spec.MASTER_LIMITER["knee_db"]),
                        ("look_ahead_msec", spec.MASTER_LIMITER["look_ahead_ms"]),
                        ("attack_time_msec", spec.MASTER_LIMITER["attack_ms"]),
                        ("release_time_msec", spec.MASTER_LIMITER["release_ms"]),
                        ("input_gain_db", 0.0), ("output_gain_db", 0.0)):
        require(math.isclose(settings.get_editor_property(name), value, abs_tol=1e-4),
                f"Master limiter {name} is {settings.get_editor_property(name)}, expected {value}")

    passive = {bus["id"]: [] for bus in buses}
    for mix_spec in audio["mixes"]:
        for source in mix_spec["sources"]:
            passive[source].append(spec.object_path(spec.mix_path(mix_spec["trigger"])))

    for bus in buses:
        name = bus["id"]
        parent = bus["parent"]
        submix = load(spec.object_path(spec.submix_path(name)))
        routed_parent = bus["submix_parent"]
        expected_parent = spec.object_path(spec.submix_path(routed_parent)) if routed_parent else None
        actual_parent = submix.get_editor_property("parent_submix")
        require((actual_parent.get_path_name() if actual_parent else None) == expected_parent,
                f"SMX_{name} parent is {actual_parent}, expected {expected_parent}")
        require(sorted(names(submix.get_editor_property("child_submixes")))
                == sorted(spec.object_path(spec.submix_path(child)) for child in submix_children[name]),
                f"SMX_{name} children differ from the submix routing")
        chain = names(submix.get_editor_property("submix_effect_chain"))
        require(chain == ([limiter.get_path_name()] if name == "Master" else []),
                f"SMX_{name} effect chain is {chain}")
        level = submix.get_editor_property("output_volume_modulation").get_editor_property("value")
        require(math.isclose(level, 0.0, abs_tol=1e-4), f"SMX_{name} output is {level} dB, expected 0 dB")

        sound_class = load(spec.object_path(spec.class_path(name)))
        expected_parent = spec.object_path(spec.class_path(parent)) if parent else None
        actual_parent = sound_class.get_editor_property("parent_class")
        require((actual_parent.get_path_name() if actual_parent else None) == expected_parent,
                f"SC_{name} parent is {actual_parent}, expected {expected_parent}")
        require(names(sound_class.get_editor_property("child_classes"))
                == [spec.object_path(spec.class_path(child)) for child in children[name]],
                f"SC_{name} children differ from the bus tree")
        properties = sound_class.get_editor_property("properties")
        require(spec.gain_close(properties.get_editor_property("volume"), bus["default_db"]),
                f"SC_{name} volume {properties.get_editor_property('volume')} is not {bus['default_db']} dB")
        require(math.isclose(properties.get_editor_property("pitch"), 1.0), f"SC_{name} pitch changed")
        for flag, members in (("always_play", spec.ALWAYS_PLAY), ("is_ui_sound", spec.UI_SOUND),
                              ("is_music", spec.MUSIC)):
            require(bool(properties.get_editor_property(flag)) == (name in members),
                    f"SC_{name} {flag} is {properties.get_editor_property(flag)}")
        require(not properties.get_editor_property("apply_effects"), f"SC_{name} routes to the EQ submix")
        loading = getattr(unreal.SoundWaveLoadingBehavior, spec.LOADING.get(name, "INHERITED"))
        require(properties.get_editor_property("loading_behavior") == loading,
                f"SC_{name} loads {properties.get_editor_property('loading_behavior')}, expected {loading}")
        routed = properties.get_editor_property("default_submix")
        require(routed is not None and routed.get_path_name() == spec.object_path(spec.submix_path(name)),
                f"SC_{name} routes to {routed}, expected SMX_{name}")
        modifiers = sound_class.get_editor_property("passive_sound_mix_modifiers")
        require([modifier.get_editor_property("sound_mix").get_path_name() for modifier in modifiers]
                == passive[name],
                f"SC_{name} passive ducking differs from the ducking table")
        for modifier in modifiers:
            require(modifier.get_editor_property("min_volume_threshold") == 0.0
                    and modifier.get_editor_property("max_volume_threshold") == 10.0,
                    f"SC_{name} ducking only reacts to part of the volume range")

    for mix_spec in audio["mixes"]:
        mix = load(spec.object_path(spec.mix_path(mix_spec["trigger"])))
        adjusters = mix.get_editor_property("sound_class_effects")
        require(len(adjusters) == len(mix_spec["targets"]),
                f"SMIX_Duck_{mix_spec['trigger']} adjusts {len(adjusters)} buses")
        for adjuster, (target, db) in zip(adjusters, mix_spec["targets"]):
            require(adjuster.get_editor_property("sound_class_object").get_path_name()
                    == spec.object_path(spec.class_path(target))
                    and spec.gain_close(adjuster.get_editor_property("volume_adjuster"), db)
                    and math.isclose(adjuster.get_editor_property("pitch_adjuster"), 1.0)
                    and adjuster.get_editor_property("apply_to_children"),
                    f"SMIX_Duck_{mix_spec['trigger']} does not lower {target} by {db} dB")
        # Unreal keeps the fades as 32-bit floats.
        timing = [mix.get_editor_property(name) for name in
                  ("fade_in_time", "fade_out_time", "duration", "initial_delay")]
        expected = [mix_spec["attack_ms"] / 1000.0, mix_spec["release_ms"] / 1000.0, -1.0, 0.0]
        require(all(math.isclose(actual, value, abs_tol=1e-6) for actual, value in zip(timing, expected))
                and not mix.get_editor_property("apply_eq"),
                f"SMIX_Duck_{mix_spec['trigger']} fades in, out, lasts and waits {timing}, expected {expected}")


def validate_waves(unreal, audio):
    load = unreal.EditorAssetLibrary.load_asset
    for wave in audio["waves"]:
        sound = load(wave["object_path"])
        where = wave["source"]
        sound_class = sound.get_editor_property("sound_class_object")
        require(sound_class is not None
                and sound_class.get_path_name() == spec.object_path(spec.class_path(wave["bus"])),
                f"{where} is in {sound_class}, expected SC_{wave['bus']}")
        require(sound.get_editor_property("sound_submix_object") is None,
                f"{where} overrides its class's submix")
        require(bool(sound.get_editor_property("looping")) == wave["loop"],
                f"{where} looping is {sound.get_editor_property('looping')}, expected {wave['loop']}")
        mode = getattr(unreal.VirtualizationMode, wave["virtualization"])
        require(sound.get_editor_property("virtualization_mode") == mode,
                f"{where} virtualization is {sound.get_editor_property('virtualization_mode')}")
        require(sound.get_editor_property("loading_behavior") == unreal.SoundWaveLoadingBehavior.INHERITED,
                f"{where} overrides its class's loading behaviour")
        require(sound.get_editor_property("num_channels") == wave["channels"],
                f"{where} imported with {sound.get_editor_property('num_channels')} channels")
        duration = sound.get_editor_property("duration")
        require(abs(duration - wave["frames"] / spec.SAMPLE_RATE) < 1e-3,
                f"{where} imported as {duration} s, expected {wave['frames'] / spec.SAMPLE_RATE} s")
        regions = sound.get_loop_regions()
        require(not sound.get_cue_points(), f"{where} imported unexpected cue markers")
        if wave["loop"]:
            start, end = wave["smpl_loop"]
            # Unreal reads the smpl end as exclusive, so the region it keeps
            # is one frame shorter than the file; the wave loops whole.
            require(len(regions) == 1
                    and regions[0].get_editor_property("frame_position") == start
                    and regions[0].get_editor_property("frame_length") == end - start
                    and end == wave["frames"] - 1,
                    f"{where} loop region {[(r.get_editor_property('frame_position'), r.get_editor_property('frame_length')) for r in regions]} "
                    f"does not span its {wave['frames']} frames")
        else:
            require(not regions, f"One-shot {where} imported a loop region")


def main():
    if "--source-only" in sys.argv:
        audio = spec.load(Path(__file__).resolve().parents[2])
        print(f"SORA_AUDIO_SOURCE_CHECK_COMPLETE: {len(audio['expected'])} expected Unreal packages "
              f"({len(audio['waves'])} sound waves)")
        return

    import unreal
    from sora_engine_pin import require_running_engine

    require_running_engine("SORA audio validation")
    audio = spec.load(Path(unreal.Paths.project_dir()).resolve())
    expected = audio["expected"]
    present = set(unreal.EditorAssetLibrary.list_assets(spec.GENERATED, recursive=True, include_folder=False))
    missing = sorted(set(expected) - present)
    extra = sorted(present - set(expected))
    require(not missing and not extra,
            f"/Game/Generated/Audio differs from the import spec: missing {missing[:5]}, extra {extra[:5]}")
    for path, class_name in expected.items():
        asset = unreal.EditorAssetLibrary.load_asset(path)
        require(asset is not None, f"Missing imported audio asset: {path}")
        require(isinstance(asset, getattr(unreal, class_name)),
                f"Wrong Unreal class for {path}: expected {class_name}, got {type(asset).__name__}")
    validate_buses(unreal, audio)
    validate_waves(unreal, audio)
    unreal.log(f"SORA_AUDIO_VALIDATION_COMPLETE: {len(expected)} packages loaded with expected types and routing")


main()
