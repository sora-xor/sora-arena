"""Host tests for sora_audio_spec.py: the real sources pass, and each refusal fires.

Run: python3 scripts/unreal/test_audio_spec.py
"""
import copy
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sora_audio_spec as spec  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def wav(frames, loop=None):
    """A 48 kHz 24-bit stereo WAV of silence, with an optional smpl loop."""
    data = bytes(frames * 6)
    body = b"WAVE" + b"fmt " + struct.pack("<IHHIIHH", 16, 1, 2, 48000, 48000 * 6, 6, 24)
    body += b"data" + struct.pack("<I", len(data)) + data
    if loop is not None:
        smpl = struct.pack("<9I", 0, 0, 20833, 60, 0, 0, 0, 1, 0) + struct.pack("<6I", 0, 0, *loop, 0, 0)
        body += b"smpl" + struct.pack("<I", len(smpl)) + smpl
    return b"RIFF" + struct.pack("<I", len(body)) + body


class AudioSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / spec.DATA).read_text(encoding="utf-8"))

    def refused(self, message, call, *args):
        with self.assertRaises(RuntimeError) as caught:
            call(*args)
        self.assertIn(message, str(caught.exception))

    def test_project_sources_pass(self):
        audio = spec.load(ROOT)
        self.assertEqual(audio["cc0_waves"], 88)
        self.assertEqual(len(audio["waves"]), 149 + 88)
        self.assertEqual(sum(wave["loop"] for wave in audio["waves"]), 19 + 6)
        self.assertEqual(len(audio["expected"]), 149 + 88 + 14 + 14 + 3 + 1)
        buses = {wave["source"].rsplit("/", 1)[1]: wave["bus"] for wave in audio["waves"]}
        self.assertEqual(buses["mus_sting_site_restored.wav"], "Music")
        self.assertEqual(buses["mus_sting_duel_point.wav"], "UI")
        self.assertEqual(buses["shd_barrier_regen.wav"], "SFX_Telegraph")
        self.assertEqual(buses["mel_parry_layer_body_01.wav"], "SFX_Melee")
        self.assertEqual(buses["cc0_wpn_repeater_fire_01.wav"], "SFX_Weapons")
        self.assertEqual(buses["cc0_fol_step_earth_01.wav"], "SFX_Foley")
        self.assertEqual(buses["cc0_amb_estate_day_loop.wav"], "Ambience")
        self.assertEqual(buses["cc0_workshop_small_hammer.wav"], "SFX_Telegraph")
        self.assertEqual(buses["cc0_workshop_sledge.wav"], "SFX_Foley")
        estate = next(wave for wave in audio["waves"] if wave["source"].endswith("cc0_amb_estate_day_loop.wav"))
        self.assertEqual((estate["package"], estate["loop"]), ("/Game/Generated/Audio/CC0/Ambience/cc0_amb_estate_day_loop", True))
        routing = {bus["id"]: bus["submix_parent"] for bus in audio["buses"]}
        self.assertEqual((routing["SFX_Telegraph"], routing["Voice_Barks"], routing["SFX_Weapons"]),
                         ("Master", "Master", "SFX"))
        voice = next(mix for mix in audio["mixes"] if mix["trigger"] == "Voice")
        self.assertEqual(voice["sources"], ["Voice", "Voice_Barks"])
        self.assertEqual(voice["targets"], [("Music", -6.0), ("Ambience", -4.0)])

    def test_ducking_a_telegraph_ancestor_is_refused(self):
        data = copy.deepcopy(self.data)
        data["ducking"].append({"trigger": "Voice", "target": "SFX", "db": -3.0,
                                "attack_ms": 80, "release_ms": 450})
        self.refused("would lower a telegraph bus", spec.bus_tree, data)

    def test_one_trigger_needs_one_timing(self):
        data = copy.deepcopy(self.data)
        data["ducking"][1]["release_ms"] = 900
        self.refused("one attack and release", spec.bus_tree, data)

    def test_sliders_must_match_the_settings_enum(self):
        data = copy.deepcopy(self.data)
        next(bus for bus in data["buses"] if bus["id"] == "UI")["slider"] = ""
        self.refused("user sliders", spec.bus_tree, data)

    def test_a_wave_on_two_ready_buses_is_refused(self):
        data = copy.deepcopy(self.data)
        cue = next(cue for cue in data["cues"] if cue["id"] == "ui.click")
        data["cues"].append(dict(cue, id="ui.click.copy", bus="SFX_Foley"))
        self.refused("plays on several buses", spec.resolve_buses, data)

    def test_a_submix_may_skip_its_parent_only_for_a_floor(self):
        data = copy.deepcopy(self.data)
        next(bus for bus in data["buses"] if bus["id"] == "SFX_Weapons")["submix_parent"] = "Master"
        self.refused("past its parent without a floor", spec.bus_tree, data)

    def test_a_floored_bus_feeds_master(self):
        data = copy.deepcopy(self.data)
        next(bus for bus in data["buses"] if bus["id"] == "SFX_Telegraph")["submix_parent"] = "SFX"
        self.refused("must feed Master", spec.bus_tree, data)

    def test_wav_layout_reads_the_smpl_loop(self):
        self.assertEqual(spec.wav_layout(wav(480, (0, 479)), "loop"), (48000, 2, 24, 480, [(0, 479)]))
        self.assertEqual(spec.wav_layout(wav(480), "one-shot")[4], [])
        self.refused("Not a RIFF WAVE", spec.wav_layout, b"RIFX" + wav(4)[4:], "bad")

    def test_raw_cc0_committed_to_the_repository_is_refused(self):
        with tempfile.TemporaryDirectory(prefix="sora-audio-spec-") as temp:
            ledgers = Path(temp) / spec.AUDIO_LEDGERS
            ledgers.mkdir(parents=True)
            record = {"asset_id": "kenney/test", "committed": True, "storage": "repo-lfs"}
            (ledgers / "audio_test.json").write_text(json.dumps({"raw_committed": False, "assets": [record]}))
            self.refused("takes only its derivatives", spec.check_raw_cc0_stays_local, Path(temp))

    def test_a_cc0_derivative_outside_repo_lfs_is_refused(self):
        with tempfile.TemporaryDirectory(prefix="sora-audio-spec-") as temp:
            for manifest in spec.OWN_MANIFESTS:
                (Path(temp) / manifest).parent.mkdir(parents=True, exist_ok=True)
                (Path(temp) / manifest).write_text(json.dumps({"schema_version": 2, "tier": "OWN", "files": []}))
            ledger = Path(temp) / spec.CC0_MANIFEST
            ledger.parent.mkdir(parents=True, exist_ok=True)
            record = {"asset_id": "opengameart/test", "tier": "PUB-CC0", "storage": "local-private", "files": []}
            ledger.write_text(json.dumps({"schema_version": 2, "tier": "PUB-CC0", "records": [record]}))
            self.refused("not a PUB-CC0 derivative in repo LFS", spec.wave_records, Path(temp))

    def test_a_ready_cc0_cue_sets_the_bus_of_a_shared_wave(self):
        data = copy.deepcopy(self.data)
        cue = next(cue for cue in data["cues"] if cue["id"] == "foot.earth")
        self.assertEqual(cue["status"], "ready-cc0")
        data["cues"].append(dict(cue, id="foot.earth.placeholder", bus="SFX_Impacts", status="needed"))
        self.assertEqual(spec.resolve_buses(data)[spec.source_of(cue["waves"][0])], "SFX_Foley")


if __name__ == "__main__":
    unittest.main()
