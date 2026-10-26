"""Authored palace desk positions, tier support, and store/registry separation.

CPU/source checks. Real collision, pathfinding and mapped copy input are
qualified separately by Campaign.Spaces and Campaign.CopyDesks in Unreal.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from campaign_palace import palace_valid

ROOT = Path(__file__).resolve().parents[2]


class PalaceContract(unittest.TestCase):
    def setUp(self):
        self.chapter = json.loads((ROOT/'Content/Data/campaign/chapter_06.json').read_text())
        self.store, self.registry = self.chapter['space']['beats'][6:8]
        self.zone = self.chapter['space']['zones'][self.registry['zone']]
        self.origin = self.registry['registry_hall']['origin_cm']

    def test_authored_three_tiers_and_distinct_thirty_second_copies(self):
        self.assertTrue(palace_valid(self.chapter))
        x,y = self.origin
        self.assertEqual(self.registry['registry_hall']['desks_cm'],
                         [[x+1600,y+2900,0],[x+600,y+2900,15],[x-200,y+2900,30]])
        self.assertEqual(self.registry['objectives'],[[x+1600,y+2790],[x+600,y+2790],[x-200,y+2790]])
        self.assertEqual(self.chapter['beats'][7]['task']['objectives'],
                         ['desk_tagata','desk_machikata','desk_shokukata'])
        self.assertEqual(self.chapter['beats'][7]['task']['objective_hold_ms'],[30000]*3)
        self.assertEqual(self.registry['registry_hall']['perimeter_width_cm'],180)
        self.assertEqual(self.registry['volumes'][0]['floor_cm'],15)

    def test_optional_store_has_its_own_cache_and_points_of_interest(self):
        x,y = self.origin
        self.assertEqual(self.store['anchor'],[x+3700,y+2500])
        self.assertEqual(self.store['cache'],[x+3700,y+2600])
        for row in self.store['volumes']:
            px,py = row['center']
            self.assertTrue(x+3000+150<px<x+4400-150)
            self.assertTrue(y+2000+150<=py<=y+3000-150)
        self.assertEqual(self.store['entry'],[x+2600,y+2500,180])
        self.assertEqual(self.registry['entry'],self.store['entry'])
        self.assertEqual(self.chapter['beats'][6]['params']['rewards'],['ch06.c03','ch06.c04','arrows:6'])
        self.assertEqual(self.chapter['beats'][7]['requires'],['ch06.b06'])

    def test_contract_missing_extra_reordered_or_wrong_type_is_rejected(self):
        hall = self.registry['registry_hall']
        for key in tuple(hall):
            saved = hall.pop(key)
            self.assertFalse(palace_valid(self.chapter),key)
            hall[key] = saved
        hall['extra'] = 0
        self.assertFalse(palace_valid(self.chapter))
        del hall['extra']
        saved = copy.deepcopy(hall['desks_cm'])
        for value in (saved[::-1],saved[:2],saved+[saved[0]],[saved[0]]*3):
            hall['desks_cm'] = value
            self.assertFalse(palace_valid(self.chapter))
        hall['desks_cm'] = saved
        for value in (True,None,'180',0,181):
            hall['perimeter_width_cm'] = value
            self.assertFalse(palace_valid(self.chapter),value)
        hall['perimeter_width_cm'] = 180
        hall['desks_cm'][0][2] = False
        self.assertFalse(palace_valid(self.chapter))

    def test_layout_events_and_site_cannot_drift_back_to_flat_room(self):
        changes = (
            lambda c:c['space']['beats'][7]['registry_hall']['desks_cm'][1].__setitem__(2,0),
            lambda c:c['space']['beats'][7]['registry_hall']['origin_cm'].__setitem__(0,0),
            lambda c:c['space']['beats'][7]['objectives'][2].__setitem__(1,0),
            lambda c:c['beats'][7]['task']['objective_hold_ms'].__setitem__(1,0),
            lambda c:c['space']['beats'][7]['volumes'][0].update(floor_cm=0),
            lambda c:c['space']['sites'].__setitem__(1,[0,0]),
            lambda c:c['space']['beats'][6].update(cache=[0,0]),
            lambda c:c['space']['beats'][6]['volumes'].pop(),
            lambda c:c['space']['beats'][7]['patrols'][3][0].__setitem__(1,0),
            lambda c:c['space']['beats'][0].update(registry_hall=copy.deepcopy(self.registry['registry_hall'])),
            lambda c:c['space']['zones'][self.registry['zone']].update(wall_cm=300),
            lambda c:c['space']['zones'][self.registry['zone']]['cover'].append([0,0,100,100,100]))
        for change in changes:
            chapter = copy.deepcopy(self.chapter)
            change(chapter)
            self.assertFalse(palace_valid(chapter))

    def test_zone_expansion_keeps_archive_position_and_clear_gaps(self):
        zones = self.chapter['space']['zones']
        self.assertEqual(self.zone['rect'],[28200,-1835,33200,1835])
        archive = next(z for z in zones if z['place']=='pl_archive')
        self.assertEqual(archive['rect'],[35200,-900,37800,900])
        before = zones[self.registry['zone']-1]
        self.assertGreaterEqual(self.zone['rect'][0]-before['rect'][2],2000)
        self.assertGreaterEqual(archive['rect'][0]-self.zone['rect'][2],2000)

    def test_runtime_floor_rule_keeps_perimeter_level_and_steps_at_two_boundaries(self):
        source = r'''
#include "SoraRegistryRules.h"
#include <cassert>
int main() {
    using namespace SoraRegistryRules;
    for(int x=-550;x<=2150;x+=10) {
        assert(Floor(x,2320)==0);
        assert(Floor(x,2379)==0);
    }
    for(int y=2380;y<=3390;y+=10) {
        assert(Floor(-200,y)==30);
        assert(Floor(600,y)==15);
        assert(Floor(1600,y)==0);
        assert(Floor(199,y)==30&&Floor(200,y)==15);
        assert(Floor(999,y)==15&&Floor(1000,y)==0);
    }
    assert(Floor(2600,2500)==0); // vestibule
    assert(Floor(3700,2500)==0); // store
    assert(Floor(-601,2900)==0&&Floor(-200,3401)==0);
    assert(Floor(-200,2379)==0&&Floor(-200,2380)==30);
    assert(Floor(600,2379)==0&&Floor(600,2380)==15);
}
'''
        compiler = os.environ.get('CXX') or shutil.which('clang++') or shutil.which('c++')
        self.assertIsNotNone(compiler,'Host C++ compiler is required')
        with tempfile.TemporaryDirectory() as tmp:
            cpp, binary = Path(tmp)/'registry.cpp', Path(tmp)/'registry'
            cpp.write_text(source)
            subprocess.run([compiler,'-std=c++17','-I',str(ROOT/'Source/SoraArena/Public'),
                            str(cpp),'-o',str(binary)],check=True,capture_output=True,text=True)
            result = subprocess.run([str(binary)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__':
    unittest.main()
