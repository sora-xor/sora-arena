"""Pinned-UE editor script: import the project audio and build its mix buses.

Run by scripts/toolchain/import-mac.sh with the compiled project:
UnrealEditor-Cmd <project> -ExecutePythonScript=<this>

It builds, under /Game/Generated/Audio (docs/audio.md section 2):

* one SoundSubmix per bus, parented as the bus tree except that the two
  telegraph buses feed SMX_Master directly (their volume floor), with the
  -1 dB limiter on SMX_Master (which feeds the engine's main submix);
* one SoundClass per bus, parented alike, carrying the bus's default level,
  its loading behaviour and its submix, so every sound of the class routes
  there;
* one ducking SoundMix per trigger bus (SMIX_Duck_<trigger>), attached as a
  passive modifier to the trigger bus and its sub-buses, so a playing voice,
  telegraph or explosion ducks its targets for as long as it sounds;
* a SoundWave for every OWN WAV (sora_audio_spec.py), in its bus's class,
  looping over the whole file when its manifest marks it a loop.

Re-running replaces the waves from source and re-applies every setting. It
never deletes assets; validate_audio_import.py fails on any it did not make.
"""
from pathlib import Path
import sys

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402
import sora_audio_spec as spec  # noqa: E402

require_running_engine("Audio import")

root = Path(unreal.Paths.project_dir()).resolve()
audio = spec.load(root)
tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.EditorAssetLibrary
link = unreal.SoraAudioImportLibrary
assets.make_directory(spec.BUSES)


def ensure(package, asset_class, factory):
    """Load the asset at package, creating it with factory when absent."""
    if assets.does_asset_exist(package):
        asset = assets.load_asset(package)
    else:
        folder, name = package.rsplit("/", 1)
        asset = tools.create_asset(name, folder, asset_class, factory)
    spec.require(isinstance(asset, asset_class), f"{package} is not a {asset_class.__name__}")
    return asset


# Submixes: the bus tree, then the final limiter on Master.
submixes = {}
for bus in audio["buses"]:
    submixes[bus["id"]] = ensure(spec.submix_path(bus["id"]), unreal.SoundSubmix,
                                 unreal.SoundSubmixFactory())
for bus in audio["buses"]:
    if bus["submix_parent"]:
        spec.require(link.set_submix_parent(submixes[bus["id"]], submixes[bus["submix_parent"]]),
                     f"Cannot parent SMX_{bus['id']} to SMX_{bus['submix_parent']}")

limiter_factory = unreal.SoundSubmixEffectFactory()
limiter_factory.set_editor_property("sound_effect_submix_preset_class",
                                    unreal.SubmixEffectDynamicsProcessorPreset)
limiter = ensure(spec.LIMITER_PATH, unreal.SubmixEffectDynamicsProcessorPreset, limiter_factory)
settings = limiter.get_editor_property("settings")
settings.set_editor_property("dynamics_processor_type", unreal.SubmixEffectDynamicsProcessorType.LIMITER)
settings.set_editor_property("peak_mode", unreal.SubmixEffectDynamicsPeakMode.PEAK)
settings.set_editor_property("link_mode", unreal.SubmixEffectDynamicsChannelLinkMode.PEAK)
settings.set_editor_property("input_gain_db", 0.0)
settings.set_editor_property("threshold_db", spec.MASTER_LIMITER["threshold_db"])
settings.set_editor_property("knee_bandwidth_db", spec.MASTER_LIMITER["knee_db"])
settings.set_editor_property("look_ahead_msec", spec.MASTER_LIMITER["look_ahead_ms"])
settings.set_editor_property("attack_time_msec", spec.MASTER_LIMITER["attack_ms"])
settings.set_editor_property("release_time_msec", spec.MASTER_LIMITER["release_ms"])
settings.set_editor_property("output_gain_db", 0.0)
settings.set_editor_property("analog_mode", False)
settings.set_editor_property("bypass", False)
limiter.set_editor_property("settings", settings)
submixes["Master"].set_editor_property("submix_effect_chain", [limiter])

# Sound classes: level, flags, loading and routing per bus, then the tree.
classes = {}
for bus in audio["buses"]:
    name = bus["id"]
    sound_class = ensure(spec.class_path(name), unreal.SoundClass, unreal.SoundClassFactory())
    properties = sound_class.get_editor_property("properties")
    properties.set_editor_property("volume", spec.db_to_gain(bus["default_db"]))
    properties.set_editor_property("pitch", 1.0)
    properties.set_editor_property("always_play", name in spec.ALWAYS_PLAY)
    properties.set_editor_property("is_ui_sound", name in spec.UI_SOUND)
    properties.set_editor_property("is_music", name in spec.MUSIC)
    properties.set_editor_property("apply_effects", False)
    properties.set_editor_property("loading_behavior", getattr(
        unreal.SoundWaveLoadingBehavior, spec.LOADING.get(name, "INHERITED")))
    properties.set_editor_property("default_submix", submixes[name])
    sound_class.set_editor_property("properties", properties)
    classes[name] = sound_class
for bus in audio["buses"]:
    if bus["parent"]:
        spec.require(link.set_sound_class_parent(classes[bus["id"]], classes[bus["parent"]]),
                     f"Cannot parent SC_{bus['id']} to SC_{bus['parent']}")

# Ducking: one passive SoundMix per trigger bus. Attack and release are the
# mix's fades; the duration is open because the passive modifier pops the
# mix when the last triggering sound stops.
passive = {bus["id"]: [] for bus in audio["buses"]}
for mix_spec in audio["mixes"]:
    mix = ensure(spec.mix_path(mix_spec["trigger"]), unreal.SoundMix, unreal.SoundMixFactory())
    adjusters = []
    for target, db in mix_spec["targets"]:
        adjuster = unreal.SoundClassAdjuster()
        adjuster.set_editor_property("sound_class_object", classes[target])
        adjuster.set_editor_property("volume_adjuster", spec.db_to_gain(db))
        adjuster.set_editor_property("pitch_adjuster", 1.0)
        adjuster.set_editor_property("apply_to_children", True)
        adjusters.append(adjuster)
    mix.set_editor_property("sound_class_effects", adjusters)
    mix.set_editor_property("apply_eq", False)
    mix.set_editor_property("initial_delay", 0.0)
    mix.set_editor_property("fade_in_time", mix_spec["attack_ms"] / 1000.0)
    mix.set_editor_property("fade_out_time", mix_spec["release_ms"] / 1000.0)
    mix.set_editor_property("duration", -1.0)
    for source in mix_spec["sources"]:
        modifier = unreal.PassiveSoundMixModifier()
        modifier.set_editor_property("sound_mix", mix)
        modifier.set_editor_property("min_volume_threshold", 0.0)
        modifier.set_editor_property("max_volume_threshold", 10.0)
        passive[source].append(modifier)
for name, modifiers in passive.items():
    classes[name].set_editor_property("passive_sound_mix_modifiers", modifiers)

# SoundWaves, imported from source every run.
tasks = []
for wave in audio["waves"]:
    folder, name = wave["package"].rsplit("/", 1)
    assets.make_directory(folder)
    factory = unreal.SoundFactory()
    factory.set_editor_property("auto_create_cue", False)
    task = unreal.AssetImportTask()
    task.filename = str(root / wave["source"])
    task.destination_path = folder
    task.destination_name = name
    task.factory = factory
    task.automated = True
    task.replace_existing = True
    task.save = False
    tasks.append(task)
tools.import_asset_tasks(tasks)
for task, wave in zip(tasks, audio["waves"]):
    spec.require(wave["object_path"] in list(task.imported_object_paths),
                 f"Unreal did not import {wave['source']} as {wave['object_path']}: "
                 f"{list(task.imported_object_paths)}")
    sound = assets.load_asset(wave["object_path"])
    spec.require(isinstance(sound, unreal.SoundWave), f"{wave['source']} is not a SoundWave")
    sound.set_editor_property("sound_class_object", classes[wave["bus"]])
    # The class routes the wave to its submix; a wave-level submix would override it.
    sound.set_editor_property("sound_submix_object", None)
    sound.set_editor_property("looping", wave["loop"])
    sound.set_editor_property("virtualization_mode", getattr(unreal.VirtualizationMode, wave["virtualization"]))
    sound.set_editor_property("loading_behavior", unreal.SoundWaveLoadingBehavior.INHERITED)

assets.save_directory(spec.GENERATED, only_if_is_dirty=False, recursive=True)
loops = sum(1 for wave in audio["waves"] if wave["loop"])
unreal.log(f"SORA_AUDIO_IMPORT_COMPLETE: {len(audio['waves'])} sound waves ({loops} loops), "
           f"{len(classes)} sound classes, {len(submixes)} submixes, {len(audio['mixes'])} ducking mixes; "
           f"{audio['cc0_records']} CC0 audio records stay local-private")
