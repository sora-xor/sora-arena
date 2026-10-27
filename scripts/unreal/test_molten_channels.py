"""Typed authored data and actual C++ time/contact rules; no GPU/runtime claim."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from campaign_molten import contract, molten_valid

ROOT = Path(__file__).resolve().parents[2]


class MoltenTests(unittest.TestCase):
    def setUp(self):
        self.chapter = json.loads((ROOT/'Content/Data/campaign/chapter_05.json').read_text())

    def test_authored_and_interpreted_fields_are_explicit(self):
        self.assertTrue(molten_valid(self.chapter))
        b, r = self.chapter['beats'][14], self.chapter['space']['beats'][14]
        self.assertEqual(r['molten_channels'], contract(b, r))
        self.assertEqual(r['molten_channels']['burn_rate_interpretation'], 'same_as_contact_nonstacking_refresh')
        self.assertTrue(r['molten_channels']['provisional_placement'])
        self.assertEqual(len(r['molten_channels']['channels']), 4)
        self.assertTrue(all('molten_channels' not in x for i, x in enumerate(self.chapter['space']['beats']) if i != 14))

    def test_source_contract_drift_is_rejected(self):
        b, r = self.chapter['beats'][14], self.chapter['space']['beats'][14]
        for key in b['ext']['hazards']['molten_channels']:
            for wrong in (None, True, 1.0, '35', [], 0):
                changed = copy.deepcopy(b); changed['ext']['hazards']['molten_channels'][key] = wrong
                with self.subTest(key=key, wrong=wrong), self.assertRaises((ValueError, TypeError)):
                    contract(changed, r)
        changed = copy.deepcopy(b); changed['ext']['environmental_kills_count'] = False
        with self.assertRaises(ValueError): contract(changed, r)

    def test_missing_mistyped_or_moved_channels_fail_closed(self):
        for field in self.chapter['space']['beats'][14]['molten_channels']:
            c = copy.deepcopy(self.chapter); del c['space']['beats'][14]['molten_channels'][field]
            self.assertFalse(molten_valid(c), field)
            c = copy.deepcopy(self.chapter); c['space']['beats'][14]['molten_channels'][field] = None
            self.assertFalse(molten_valid(c), field)
        for mutate in (
            lambda r: r['molten_channels']['channels'].pop(),
            lambda r: r['molten_channels']['channels'][0].update(center=[68056, 780]),
            lambda r: r['molten_channels'].update(player_dps=35.0),
            lambda r: r['molten_channels'].update(burn_dps=70),
            lambda r: r.update(height_cm=100)):
            c = copy.deepcopy(self.chapter); mutate(c['space']['beats'][14]); self.assertFalse(molten_valid(c))
        c = copy.deepcopy(self.chapter); c['space']['beats'][15]['molten_channels'] = c['space']['beats'][14]['molten_channels']
        self.assertFalse(molten_valid(c))

    def test_integrated_cpp_phase_crossings_burn_geometry_and_damage_policy(self):
        code = r'''
#include "SoraMoltenRules.h"
#include "SoraCombatRules.h"
#include <cassert>
#include <random>
using namespace SoraMoltenRules;
int main() {
    assert(Phase(0)==EPhase::Warning && Phase(1999)==EPhase::Warning);
    assert(Phase(2000)==EPhase::Flow && Phase(6999)==EPhase::Flow);
    assert(Phase(7000)==EPhase::Cooling && Phase(12000)==EPhase::Warning);
    FSpan full{0,12000}; FBody b;
    auto r=Tick(b,EBody::Player,0,12000,&full,1);
    assert(r.Damage==245 && r.ContactMs==5000 && b.BurnLeftMs==0 && !r.Destroy);
    b={}; r=Tick(b,EBody::Enemy,0,12000,&full,1); assert(r.Damage==300 && b.BurnLeftMs==0);
    b={}; r=Tick(b,EBody::Automaton,0,1999,&full,1); assert(!r.Destroy);
    r=Tick(b,EBody::Automaton,1999,2,&full,1); assert(r.Destroy && r.ContactMs==1);
    b={}; FSpan contact{0,1000}; r=Tick(b,EBody::Player,2000,1000,&contact,1);
    assert(r.Damage==35 && b.BurnLeftMs==2000);
    assert(Tick(b,EBody::Player,3000,1000,nullptr,0).Damage==35 && b.BurnLeftMs==1000); // airborne burn
    const auto before=b; assert(Tick(b,EBody::Player,4000,0,nullptr,0).Damage==0);
    assert(b.BurnLeftMs==before.BurnLeftMs && b.Remainder==before.Remainder); // pause
    assert(Tick(b,EBody::Player,4000,1000,&contact,1).Damage==35 && b.BurnLeftMs==2000); // refresh, not stack
    assert(Tick(b,EBody::Player,5000,5000,nullptr,0).Damage==70 && b.BurnLeftMs==0);
    b={}; assert(Tick(b,EBody::Player,2000,1000,nullptr,0).Damage==0); // new airborne crossing
    FSpan overlapping[]={{0,1000},{100,900},{300,600}}; b={};
    assert(Tick(b,EBody::Player,2000,1000,overlapping,3).Damage==35); // union, not per-strip stacking
    FSpan crossing;
    assert(Cross(0,-200,0,200,-100,-40,100,40,1000,crossing) && crossing.Begin==400 && crossing.End==600);
    assert(!Cross(200,-200,200,200,-100,-40,100,40,1000,crossing));
    assert(Cross(0,0,0,0,-100,-40,100,40,1000,crossing)&&crossing.Begin==0&&crossing.End==1000);
    // Large deltas crossing many cycles/contact boundaries equal independent
    // 1 ms stepping, including retained fractions, all three body types.
    std::mt19937 rng(42);
    for(int trial=0;trial<120;++trial) {
        int clock=rng()%12000,dt=1000+rng()%50000;
        FSpan spans[]={{int(rng()%1000),int(1000+rng()%10000)},{12000,25000},{30000,32000},{33000,34000}};
        for(auto& s:spans) { s.Begin=std::min(s.Begin,dt); s.End=std::min(s.End,dt); }
        for(EBody kind:{EBody::Player,EBody::Enemy,EBody::Automaton}) {
            FBody large{int(rng()%2001),int(rng()%1000)},small=large;
            const auto got=Tick(large,kind,clock,dt,spans,4); int damage=0,contactMs=0;bool destroyed=false;
            for(int ms=0;ms<dt;++ms) {
                bool touching=false; for(const auto& s:spans) touching|=ms>=s.Begin&&ms<s.End;
                FSpan one{0,1};const auto step=Tick(small,kind,(clock+ms)%12000,1,touching?&one:nullptr,touching?1:0);
                damage+=step.Damage;contactMs+=step.ContactMs;destroyed|=step.Destroy;
            }
            assert(got.Damage==damage && got.ContactMs==contactMs && got.Destroy==destroyed);
            assert(large.BurnLeftMs==small.BurnLeftMs && large.Remainder==small.Remainder);
        }
    }
    using namespace SoraCombatRules;
    assert(EnemyVulnerabilityDamage(60,EHit::Hazard,EEnvironmentalRate::MoltenChannel,true,-1000,1500)==60);
    for(EHit kind:{EHit::Melee,EHit::Ranged,EHit::Blast,EHit::Beam,EHit::Scripted,EHit::Hazard}) {
        assert(EnemyVulnerabilityDamage(60,kind,EEnvironmentalRate::None,true,-1000,1500)==RearDamage(StaggeredDamage(60,true),-1000,1500));
        if(kind!=EHit::Hazard) assert(EnemyVulnerabilityDamage(60,kind,EEnvironmentalRate::MoltenChannel,true,-1000,1500)>60);
    }
}
'''
        compiler = os.environ.get('CXX') or shutil.which('clang++') or shutil.which('c++')
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory(prefix='sora-molten-') as directory:
            cpp, binary = Path(directory)/'molten.cpp', Path(directory)/'molten'
            cpp.write_text(code)
            subprocess.run([compiler, '-std=c++17', '-UNDEBUG', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=undefined', '-fsanitize-trap=undefined', '-I', str(ROOT/'Source/SoraArena/Public'),
                            str(cpp), '-o', str(binary)], check=True, capture_output=True, text=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)


if __name__ == '__main__': unittest.main()
