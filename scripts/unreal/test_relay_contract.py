"""Reject drift in the authored relay controls and the normalized room.

Host data tests only. Runtime collision, traversal, AI and timing integration
are covered separately by the Unreal relay fixtures.
"""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from campaign_relay import contract, relay_valid

ROOT=Path(__file__).resolve().parents[2]


class RelayContract(unittest.TestCase):
    def setUp(self):
        self.chapter=json.loads((ROOT/'Content/Data/campaign/chapter_06.json').read_text())
        self.beat=self.chapter['beats'][3]
        self.record=self.chapter['space']['beats'][3]
        self.room=self.record['relay_room']

    def test_authored_room_and_upper_control_are_preserved(self):
        self.assertTrue(relay_valid(self.chapter))
        x,y=self.room['origin_cm']
        self.assertEqual(self.room['nodes_cm'],[[x+920,y+500,120],[x+1080,y+500,120],[x+1000,y+580,520]])
        self.assertEqual([p[2] for p in self.room['work_cm']],[0,0,400])
        self.assertEqual(self.beat['task']['objective_hold_ms'],[3000,3000,3000,0])

    def test_clock_type_drift_and_nonfinite_values_fail(self):
        for key,original in tuple(self.room.items()):
            if type(original) is not int:continue
            for value in (True,None,str(original),original+1,float('inf'),float('nan')):
                with self.subTest(key=key,value=value):
                    self.room[key]=value
                    self.assertFalse(relay_valid(self.chapter))
            self.room[key]=original

    def test_missing_extra_duplicate_and_reordered_contracts_fail(self):
        for key in tuple(self.room):
            value=self.room.pop(key);self.assertFalse(relay_valid(self.chapter));self.room[key]=value
        self.room['extra']=1;self.assertFalse(relay_valid(self.chapter));del self.room['extra']
        for key in ('nodes_cm','work_cm'):
            original=copy.deepcopy(self.room[key])
            for value in (original[::-1],original[:2],original+[original[0]],[original[0]]*3):
                self.room[key]=value;self.assertFalse(relay_valid(self.chapter))
            self.room[key]=original
        self.chapter['space']['beats'][0]['relay_room']=copy.deepcopy(self.room)
        self.assertFalse(relay_valid(self.chapter))

    def test_nodes_cannot_move_to_floor_or_behind_other_side(self):
        for key in ('nodes_cm','work_cm'):
            for node in range(3):
                for axis in range(3):
                    self.room[key][node][axis]+=1
                    self.assertFalse(relay_valid(self.chapter),(key,node,axis))
                    self.room[key][node][axis]-=1

    def test_floor_entry_exit_and_spawn_contracts_cannot_drift(self):
        for row in [self.record['exit'],*self.record['volumes']]:
            for value in (None,True,400):
                row['floor_cm']=value;self.assertFalse(relay_valid(self.chapter))
            row['floor_cm']=0
        for key in ('entry','anchor','spawns'):
            saved=copy.deepcopy(self.record[key]);self.record[key]=[]
            self.assertFalse(relay_valid(self.chapter));self.record[key]=saved
        self.record['volumes']=[];self.assertFalse(relay_valid(self.chapter))

    def test_lamps_keep_authored_switches_and_no_relight(self):
        for field,value in (('at',[0,0]),('kind','die'),('snuff','shot'),('hold_ms',0),('relight_ms',1000),('radius_cm',701)):
            lamp=self.record['fieldcraft']['lamps'][0];old=lamp[field];lamp[field]=value
            self.assertFalse(relay_valid(self.chapter));lamp[field]=old

    def test_authored_sensor_wave_patrol_and_effects_cannot_be_ignored(self):
        changes=(lambda b:b['ext']['sensors'][0].update(gap_s=5),
                 lambda b:b['params']['waves'][0]['enemies'][0].update(delay_s=0),
                 lambda b:b['params']['waves'][0]['enemies'][0].update(count=3),
                 lambda b:b['params']['guards'][1].update(patrol='spl_relay_2f_loop_50s'),
                 lambda b:b['params']['guards'][2].update(investigates='none'),
                 lambda b:b['params']['noise_surfaces'].clear(),
                 lambda b:b['params']['light_sources'][0].update(suspicion_delay_s=4),
                 lambda b:b['ext']['on_complete_effects'].clear(),
                 lambda b:b['task']['objective_hold_ms'].__setitem__(2,0))
        for change in changes:
            beat=copy.deepcopy(self.beat);change(beat)
            with self.assertRaises(ValueError):contract(beat,self.room['origin_cm'])


if __name__=='__main__':unittest.main()
