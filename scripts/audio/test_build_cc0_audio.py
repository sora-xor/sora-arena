#!/usr/bin/env python3
"""Host tests for build_cc0_audio.py's processing: a bed's wrap, take detection and the one-shot ceiling.

Run: python3 scripts/audio/test_build_cc0_audio.py
"""
import copy
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / 'synth'))
import build_cc0_audio as cc0  # noqa: E402
import dsp  # noqa: E402
from qa_audio import wrap_click  # noqa: E402


class CrossfadeLoopTests(unittest.TestCase):
    def test_the_wrap_runs_on_as_the_source_did(self):
        source = np.vstack([np.arange(dsp.n_of(3.0), dtype=float)] * 2)
        loop = cc0.crossfade_loop(source, 2.0, 0.5)
        n = dsp.n_of(2.0)
        self.assertEqual(loop.shape, (2, n))
        # The last sample is the source's sample n - 1 and the first is its sample n: no step at the wrap.
        self.assertEqual(loop[0, -1], n - 1)
        self.assertEqual(loop[0, 0], n)
        # Past the crossfade the head is the source itself.
        self.assertEqual(loop[0, dsp.n_of(0.5)], dsp.n_of(0.5))

    def test_a_noise_bed_passes_the_loop_click_check(self):
        noise = dsp.rng('test-bed').standard_normal((2, dsp.n_of(6.0))) * 0.1
        loop = cc0.crossfade_loop(noise, 5.0, 1.0)
        self.assertFalse(wrap_click(loop, dsp.SR)['loop_click'])

    def test_too_short_a_source_is_refused(self):
        with self.assertRaises(SystemExit):
            cc0.crossfade_loop(np.zeros((2, dsp.n_of(1.0))), 1.0, 0.5)


class EventTests(unittest.TestCase):
    def test_takes_split_on_silence_and_merge_short_gaps(self):
        rate = 48000
        x = np.zeros((1, rate * 3))
        for start, length, level in ((0.2, 0.1, 1.0), (0.35, 0.1, 1.0), (1.5, 0.2, 0.1)):
            a = int(start * rate)
            x[0, a:a + int(length * rate)] = level
        found = cc0.events(x, rate, floor_db=-40.0, gap=0.25)
        self.assertEqual(len(found), 2)
        (s0, e0, p0), (s1, e1, p1) = found
        self.assertAlmostEqual(s0 / rate, 0.2, delta=0.01)
        self.assertAlmostEqual(e0 / rate, 0.45, delta=0.01)
        self.assertAlmostEqual(p0, 0.0, delta=0.01)
        self.assertAlmostEqual(p1, -20.0, delta=0.1)

    def test_the_running_envelope_is_a_centred_moving_average(self):
        power = dsp.rng('test-env').random(1000)
        x = np.sqrt(power)[None, :]
        n = int(0.01 * 1000)
        expected = np.sqrt(np.convolve(power, np.ones(n) / n, mode='same'))
        np.testing.assert_allclose(cc0.envelope(x, 1000, 0.01), expected, atol=1e-9)


class LevelTests(unittest.TestCase):
    def test_one_shots_end_at_or_below_minus_one_dbtp(self):
        r = dsp.rng('test-level')
        clicks = np.zeros((1, dsp.n_of(0.3)))
        clicks[0, ::997] = 1.0
        clicks += r.standard_normal(clicks.shape) * 1e-3
        for target in ({'M': -6.0}, {'P': -1.0, 'limit': 6.0}):
            self.assertLessEqual(dsp.true_peak_db(cc0.level(clicks, target)), -1.0 + 1e-6)

    def test_beds_are_levelled_by_gain_alone(self):
        noise = dsp.rng('test-gain').standard_normal((2, dsp.n_of(4.0))) * 0.01
        out = cc0.level(noise, {'I': -26.0, 'tp': cc0.BED_TP})
        ratio = out / noise
        self.assertAlmostEqual(float(ratio.min()), float(ratio.max()), places=9)


class PartialLedgerTests(unittest.TestCase):
    def setUp(self):
        record = {'asset_id': 'park', 'license': 'CC0-1.0', 'tier': 'PUB-CC0',
                  'files': [{'file': 'birds.wav', 'bytes': 80, 'sha256': 'old'},
                            {'file': 'stream.wav', 'bytes': 20, 'sha256': 'before'}],
                  'used_by': ['birds.object', 'stream.object'], 'layered_into': ['storm.wav']}
        self.existing = {'records': [record, {'asset_id': 'other', 'files': [{'file': 'fire.wav', 'bytes': 50}]}],
                         'total_bytes': 150, 'format': 'old'}
        self.fresh = {'records': [{**copy.deepcopy(record),
                                  'files': [{'file': 'stream.wav', 'bytes': 30, 'sha256': 'after'}],
                                  'used_by': ['stream.object'], 'layered_into': []}], 'format': 'new'}

    def test_partial_rebuild_preserves_siblings_and_unrelated_sources(self):
        before = copy.deepcopy(self.existing)
        merged = cc0.merge_partial(self.existing, self.fresh)
        park = next(r for r in merged['records'] if r['asset_id'] == 'park')
        self.assertEqual(park['files'][0], before['records'][0]['files'][0])
        self.assertEqual(park['files'][1], self.fresh['records'][0]['files'][0])
        self.assertEqual(park['used_by'], before['records'][0]['used_by'])
        self.assertEqual(park['layered_into'], ['storm.wav'])
        self.assertEqual(next(r for r in merged['records'] if r['asset_id'] == 'other'), before['records'][1])
        self.assertEqual(merged['total_bytes'], 160)
        self.assertEqual(self.existing, before)
        self.assertEqual(cc0.merge_partial(merged, self.fresh), merged)

    def test_changed_rights_are_refused_in_a_partial_rebuild(self):
        self.fresh['records'][0]['license'] = 'CC-BY-4.0'
        with self.assertRaisesRegex(SystemExit, 'metadata: license'):
            cc0.merge_partial(self.existing, self.fresh)

    def test_derivative_cannot_silently_move_to_another_source(self):
        self.fresh['records'][0]['asset_id'] = 'replacement'
        with self.assertRaisesRegex(SystemExit, 'upstream owner'):
            cc0.merge_partial(self.existing, self.fresh)

    def test_budget_includes_derivatives_not_rebuilt(self):
        self.fresh['records'][0]['files'][0]['bytes'] = cc0.BUDGET_BYTES - 100
        with self.assertRaisesRegex(SystemExit, 'exceed the audio budget'):
            cc0.merge_partial(self.existing, self.fresh)


if __name__ == '__main__':
    unittest.main()
