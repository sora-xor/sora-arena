"""Pinned river derivative, spatial cue and emitter-validation contract, without Unreal or the raw cache."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/unreal'))
sys.path.insert(0, str(ROOT / 'scripts/assets'))
sys.path.insert(0, str(ROOT / 'scripts/audio'))
from asset_ledger import check_record
from sora_audio_spec import resolve_buses, wav_layout
import validate_audio_data as validator


class StreamAudioTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'Content/Data/audio.json').read_text())
        self.cues = {c['id']: c for c in self.data['cues']}
        ledger = json.loads((ROOT / 'Content/SourceArt/Audio/CC0/manifest.json').read_text())
        self.record = next(r for r in ledger['records'] if r['asset_id'] == 'opengameart/park-ambiences')
        self.row = next(r for r in self.record['files'] if r['cue'] == 'amb.stream')

    def test_pinned_source_and_mono_loop_bytes(self):
        raw = json.loads((ROOT / 'scripts/assets/manifests/audio_opengameart.json').read_text())
        park = next(r for r in raw['assets'] if r['asset_id'] == self.record['asset_id'])
        source = next(r for r in park['downloads'] if r['file'].endswith('park_ambience_river.wav'))
        self.assertEqual(check_record(self.record, 'stream derivative'), [])
        self.assertEqual(self.record['license'], 'CC0-1.0')
        self.assertEqual(self.record['authors'], ['Thimras'])
        span, = self.row['derived_from']
        self.assertEqual((span['file'], span['sha256']), (source['file'], source['sha256']))
        self.assertEqual(span['asset_id'], park['asset_id'])
        self.assertGreaterEqual(span['start_s'], 0)
        self.assertAlmostEqual(span['end_s'] - span['start_s'], 49)
        data = (ROOT / self.row['file']).read_bytes()
        self.assertEqual((len(data), hashlib.sha256(data).hexdigest()), (self.row['bytes'], self.row['sha256']))
        rate, channels, bits, frames, loops = wav_layout(data, self.row['file'])
        self.assertEqual((rate, channels, bits, frames), (48000, 1, 24, 45 * 48000))
        self.assertEqual(loops, [(0, frames - 1)])
        self.assertEqual(self.row['qa']['fail'], [])
        self.assertAlmostEqual(self.row['qa']['integrated_lufs'], -26, delta=.1)
        self.assertLessEqual(self.row['qa']['true_peak_dbtp'], -3)

    def test_authored_spatial_binding_keeps_listening_limit_explicit(self):
        cue = self.cues['amb.stream']
        self.assertEqual(self.data['emitters'], {'ward_culvert': 'amb.stream'})
        self.assertEqual(cue['waves'], ['CC0/Ambience/cc0_amb_stream_loop'])
        self.assertTrue(cue['loop'] and cue['spatial'])
        self.assertEqual(cue['attenuation'], 'ambient_emitter')
        self.assertEqual(cue['unbound'], '')
        self.assertIn('listening', cue['needs'])
        self.assertIn('Adelaide', cue['needs'])
        self.assertEqual(resolve_buses(self.data)[self.row['file']], 'Ambience')
        self.assertIn('amb.stream', validator.played_cues(self.data))

    def test_emitter_refuses_missing_oneshot_nonspatial_or_nonambient_cues(self):
        for cue_id, edit in [('absent', {}), ('amb.stream', {'loop': False}),
                             ('amb.stream', {'spatial': False}), ('amb.stream', {'bus': 'SFX_Foley'})]:
            with self.subTest(cue=cue_id, edit=edit):
                data, cues = copy.deepcopy(self.data), copy.deepcopy(self.cues)
                data['emitters']['ward_culvert'] = cue_id
                if edit:
                    cues[cue_id].update(edit)
                with patch.object(validator, 'error') as error:
                    validator.check_coverage(data, cues)
                self.assertTrue(any('emitter ward_culvert:' in call.args[0] for call in error.call_args_list))


if __name__ == '__main__':
    unittest.main()
