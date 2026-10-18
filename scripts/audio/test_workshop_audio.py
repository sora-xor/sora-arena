"""Bounded workshop source contract: no Unreal, raw cache, or unrelated asset hydration."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/unreal'))
from sora_audio_spec import resolve_buses, wav_layout  # noqa: E402


class WorkshopAudioTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'Content/Data/audio.json').read_text())
        self.cues = {cue['id']: cue for cue in self.data['cues']}
        self.ledger = json.loads((ROOT / 'Content/SourceArt/Audio/CC0/manifest.json').read_text())
        self.record = next(r for r in self.ledger['records'] if r['asset_id'].endswith('/Anvil'))

    def test_timing_is_sfx_and_fixed_pitch_with_retained_cue_loading(self):
        from sora_audio_spec import LOADING
        cue = self.cues['workshop.hammer.cue']
        self.assertEqual(cue['bus'], 'SFX_Telegraph')
        self.assertEqual(LOADING[cue['bus']], 'RETAIN_ON_LOAD')
        self.assertEqual(cue['pitch_cents'], [0, 0])
        self.assertEqual(self.cues['workshop.hammer.hit']['bus'], 'SFX_Foley')
        buses = resolve_buses(self.data)
        self.assertEqual(buses['Content/SourceArt/Audio/CC0/Workshop/cc0_workshop_small_hammer.wav'], 'SFX_Telegraph')
        self.assertEqual(self.data['bindings']['Workshop'], [
            {'when': {'Action': action}, 'cue': cue_id, 'continue': False, 'delay_ms': 0}
            for action, cue_id in [('HammerCue', 'workshop.hammer.cue'), ('HammerHit', 'workshop.hammer.hit'),
                                   ('LoomCall', 'workshop.loom.call')]])

    def test_missing_character_call_is_explicit_and_has_no_substitute(self):
        cue = self.cues['workshop.loom.call']
        self.assertEqual(cue['status'], 'needed')
        self.assertEqual(cue['bus'], 'Voice_Barks')
        self.assertEqual(cue['waves'], [])
        self.assertIn('Okinu', cue['needs'])
        self.assertEqual(cue['caption'], '')  # do not caption a voice that is not playing

    def test_new_derivatives_keep_raw_identity_and_match_pcm_bytes(self):
        raw = json.loads((ROOT / 'scripts/assets/manifests/audio_vcsl.json').read_text())
        source = next(r for r in raw['assets'] if r['asset_id'] == self.record['asset_id'])
        originals = {r['file']: r for r in source['files']}
        self.assertEqual(self.record['tier'], 'PUB-CC0')
        self.assertEqual(self.record['license'], 'CC0-1.0')
        self.assertEqual(self.record['origin_url'], source['origin_url'])
        self.assertEqual(self.record['storage'], 'repo-lfs')
        self.assertEqual(len(self.record['files']), 2)
        for row in self.record['files']:
            data = (ROOT / row['file']).read_bytes()
            self.assertEqual(len(data), row['bytes'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), row['sha256'])
            rate, channels, bits, frames, loops = wav_layout(data, row['file'])
            self.assertEqual((rate, channels, bits, loops), (48000, 2, 24, []))
            self.assertLessEqual(frames / rate, .42)
            self.assertEqual(row['qa']['fail'], [])
            self.assertLessEqual(row['qa']['true_peak_dbtp'], -5)
            for span in row['derived_from']:
                self.assertEqual(span['sha256'], originals[span['file']]['sha256'])
                self.assertEqual(span['asset_id'], source['asset_id'])


if __name__ == '__main__':
    unittest.main()
