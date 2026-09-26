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
        cls.proposal = json.loads((ROOT / spec.PROPOSAL).read_text(encoding="utf-8"))

    def refused(self, message, call, *args):
        with self.assertRaises(RuntimeError) as caught:
            call(*args)
        self.assertIn(message, str(caught.exception))

    def test_project_sources_pass(self):
        audio = spec.load(ROOT)
        self.assertEqual(len(audio["waves"]), 149)
        self.assertEqual(sum(wave["loop"] for wave in audio["waves"]), 19)
        self.assertEqual(len(audio["expected"]), 149 + 14 + 14 + 3 + 1)
        buses = {wave["source"].rsplit("/", 1)[1]: wave["bus"] for wave in audio["waves"]}
        self.assertEqual(buses["mus_sting_site_restored.wav"], "Music")
        self.assertEqual(buses["mus_sting_duel_point.wav"], "UI")
        self.assertEqual(buses["shd_barrier_regen.wav"], "SFX_Telegraph")
        self.assertEqual(buses["mel_parry_layer_body_01.wav"], "SFX_Melee")
        voice = next(mix for mix in audio["mixes"] if mix["trigger"] == "Voice")
        self.assertEqual(voice["sources"], ["Voice", "Voice_Barks"])
        self.assertEqual(voice["targets"], [("Music", -6.0), ("Ambience", -4.0)])

    def test_ducking_a_telegraph_ancestor_is_refused(self):
        proposal = copy.deepcopy(self.proposal)
        proposal["ducking"].append({"trigger": "Voice", "target": "SFX", "db": -3.0,
                                    "attack_ms": 80, "release_ms": 450})
        self.refused("would lower a telegraph bus", spec.bus_tree, proposal)

    def test_one_trigger_needs_one_timing(self):
        proposal = copy.deepcopy(self.proposal)
        proposal["ducking"][1]["release_ms"] = 900
        self.refused("one attack and release", spec.bus_tree, proposal)

    def test_sliders_must_match_the_settings_enum(self):
        proposal = copy.deepcopy(self.proposal)
        next(bus for bus in proposal["buses"] if bus["id"] == "UI").pop("user_slider")
        self.refused("user sliders", spec.bus_tree, proposal)

    def test_a_wave_on_two_ready_buses_is_refused(self):
        proposal = copy.deepcopy(self.proposal)
        cue = next(cue for cue in proposal["cues"] if cue["id"] == "ui.click")
        proposal["cues"].append(dict(cue, id="ui.click.copy", bus="SFX_Foley"))
        self.refused("plays on several buses", spec.resolve_buses, proposal)

    def test_a_stale_override_is_refused(self):
        proposal = copy.deepcopy(self.proposal)
        cue = next(cue for cue in proposal["cues"] if cue["id"] == "site.restored")
        cue["bus"] = "Music"
        self.refused("is stale", spec.resolve_buses, proposal)

    def test_wav_layout_reads_the_smpl_loop(self):
        self.assertEqual(spec.wav_layout(wav(480, (0, 479)), "loop"), (48000, 2, 24, 480, [(0, 479)]))
        self.assertEqual(spec.wav_layout(wav(480), "one-shot")[4], [])
        self.refused("Not a RIFF WAVE", spec.wav_layout, b"RIFX" + wav(4)[4:], "bad")

    def test_cc0_admitted_to_the_repository_is_refused(self):
        with tempfile.TemporaryDirectory(prefix="sora-audio-spec-") as temp:
            ledgers = Path(temp) / spec.AUDIO_LEDGERS
            ledgers.mkdir(parents=True)
            record = {"asset_id": "kenney/test", "committed": True, "storage": "repo-lfs"}
            (ledgers / "audio_test.json").write_text(json.dumps({"raw_committed": False, "assets": [record]}))
            self.refused("admitted to the repository", spec.check_ledger_admits_no_cc0, Path(temp))


if __name__ == "__main__":
    unittest.main()
