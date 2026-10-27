"""Authored placement and one-shot policy; no engine/render acceptance."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from campaign_canisters import AUTHORED, LOCAL_CM, contract, canisters_valid

ROOT = Path(__file__).resolve().parents[2]


class CanisterData(unittest.TestCase):
    def setUp(self):
        self.chapter = json.loads((ROOT/'Content/Data/campaign/chapter_07.json').read_text())

    def test_three_authored_positions_use_existing_hangar_frame_only_on_b08(self):
        self.assertTrue(canisters_valid(self.chapter))
        beat, record = self.chapter['beats'][7], self.chapter['space']['beats'][7]
        self.assertEqual(beat['ext']['hazards'], AUTHORED)
        self.assertEqual(record['fuel_canisters'], contract(beat, record))
        self.assertEqual([x['floor_cm'] for x in record['fuel_canisters']['items']],
                         [[40800, -1050, 0], [43200, -1050, 0], [42000, 1550, 0]])
        for index, row in enumerate(self.chapter['space']['beats']):
            self.assertEqual('fuel_canisters' in row, index == 7)
        # Each body has genuine open floor, including the mouth-side canister.
        for x, y in LOCAL_CM:
            self.assertTrue(30 < x < 7970 and 30 < y < 4470)
            self.assertFalse(any(abs(x-sx) < 930 and 1770 < y < 3230 for sx in (1500, 4000, 6500)))

    def test_authored_rate_radius_ids_and_trigger_drift_fail_closed(self):
        for key in AUTHORED[0]:
            for wrong in (None, True, False, 80.0, '80', [], {}):
                if wrong is True and key == 'hurts_player': continue
                beat, record = copy.deepcopy(self.chapter['beats'][7]), self.chapter['space']['beats'][7]
                beat['ext']['hazards'][0][key] = wrong
                with self.subTest(key=key, wrong=wrong), self.assertRaises((ValueError, TypeError)):
                    contract(beat, record)
        for mutate in (
            lambda r: r['fuel_canisters']['items'].pop(),
            lambda r: r['fuel_canisters']['items'][0].update(id='fc_02'),
            lambda r: r['fuel_canisters']['items'][0].update(floor_cm=[40800, -1050, 70]),
            lambda r: r['fuel_canisters']['items'][2].update(floor_cm=[42000, 250, 0]),
            lambda r: r['fuel_canisters'].update(damage=80.0),
            lambda r: r['fuel_canisters'].update(trigger='any_damage'),
            lambda r: r.update(height_cm=0.0),
            lambda r: r['wind'].update(origin=[38000, 0])):
            chapter = copy.deepcopy(self.chapter); mutate(chapter['space']['beats'][7])
            self.assertFalse(canisters_valid(chapter))
        chapter = copy.deepcopy(self.chapter)
        chapter['space']['beats'][8]['fuel_canisters'] = chapter['space']['beats'][7]['fuel_canisters']
        self.assertFalse(canisters_valid(chapter))
        chapter = copy.deepcopy(self.chapter); del chapter['space']['beats'][7]['fuel_canisters']
        self.assertFalse(canisters_valid(chapter))

    def test_actual_cpp_trigger_latches_before_callbacks_and_keeps_standard_blast_rules(self):
        code = r'''
#include "SoraFuelCanisterRules.h"
#include <cassert>
#include <limits>
#include <initializer_list>
using namespace SoraFuelCanisterRules;
using namespace SoraCombatRules;
int main() {
    static_assert(Count==3 && Damage==80 && BlastRadiusCm==360);
    static_assert(LocalFeetCm[0].X==2800 && LocalFeetCm[0].Y==1200);
    static_assert(LocalFeetCm[1].X==5200 && LocalFeetCm[1].Y==1200);
    static_assert(LocalFeetCm[2].X==4000 && LocalFeetCm[2].Y==3800);
    FState s;
    for(EHit kind:{EHit::Melee,EHit::Blast,EHit::Beam,EHit::Scripted,EHit::Hazard})
        assert(!s.Shot(kind,999,true) && !s.Burst);
    for(float amount:{0.f,-1.f,std::numeric_limits<float>::quiet_NaN(),std::numeric_limits<float>::infinity()})
        assert(!s.Shot(EHit::Ranged,amount,true) && !s.Burst);
    assert(!s.Shot(EHit::Ranged,1,false) && !s.Burst);
    assert(s.Shot(EHit::Ranged,.1f,true) && s.Burst);
    for(int i=0;i<100;++i) assert(!s.Shot(EHit::Ranged,95,true)); // callback re-entry/repeated shot
    FState retry; assert(!retry.Burst && retry.Shot(EHit::Ranged,13,true));
    assert(BlastReaches(true,false,360,BlastRadiusCm,true)); // shooter included
    assert(!BlastReaches(true,false,361,BlastRadiusCm,true));
    assert(!BlastReaches(false,true,200,BlastRadiusCm,false)); // actual cover remains authoritative
    assert(!BlastReaches(false,false,200,BlastRadiusCm,true)); // allies excluded
    assert(!BlastDefensible(true));
    assert(ShieldStops(EHit::Blast,1000,500,false));
    assert(!ShieldStops(EHit::Blast,-1000,500,false));
    assert(EnemyVulnerabilityDamage(80,EHit::Blast,EEnvironmentalRate::None,true,-1000,1500)>80);
}
'''
        compiler = os.environ.get('CXX') or shutil.which('clang++') or shutil.which('c++')
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory(prefix='sora-canister-') as directory:
            cpp, binary = Path(directory)/'canister.cpp', Path(directory)/'canister'
            cpp.write_text(code)
            built = subprocess.run([compiler, '-std=c++17', '-UNDEBUG', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=undefined', '-fsanitize-trap=undefined', '-I', str(ROOT/'Source/SoraArena/Public'),
                            str(cpp), '-o', str(binary)], capture_output=True, text=True, timeout=30)
            self.assertEqual(built.returncode, 0, built.stdout+built.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)


if __name__ == '__main__': unittest.main()
