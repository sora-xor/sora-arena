#!/usr/bin/env python3
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from campaign_helm import place_helm
from build_campaign_data import BuildError, fail
ROOT=Path(__file__).resolve().parents[2]
class HelmTests(unittest.TestCase):
 def setUp(self):
  self.data=json.loads((ROOT/'Content/Data/campaign/chapter_07.json').read_text())
 def test_authored_contract_and_reachable_floor(self):
  b=self.data['beats'][13];r=self.data['space']['beats'][13];h=r['helm'];z=self.data['space']['zones'][r['zone']]
  self.assertEqual(h['threshold_permille'],[250,500,750]);self.assertEqual(h['deadline_ms'],[200000,150000,130000])
  self.assertEqual((h['work_ms'],h['grace_ms'],h['decay_permille']),(2000,8000,20))
  self.assertEqual(h['size'],[600,1600]);self.assertEqual(h['wheel'],[h['center'][0],h['center'][1]-500])
  for point in (h['wheel'],h['beacon'],h['center']):
   self.assertTrue(z['rect'][0]+100<point[0]<z['rect'][2]-100 and z['rect'][1]+100<point[1]<z['rect'][3]-100)
   for x,y,sx,sy,_ in z['cover']:self.assertTrue(abs(x-point[0])>sx/2+100 or abs(y-point[1])>sy/2+100)
  records=copy.deepcopy(self.data['space']['beats']);place_helm(self.data['beats'],records,self.data['space']['zones'],fail)
  self.assertEqual(records,self.data['space']['beats'])
 def test_malformed_authored_values_rejected(self):
  for group,key,value in [('trim_events','at_progress',[.25,.25,.75]),('trim_events','at_progress',[True,.5,.75]),('trim_events','grace_s',1),('trim_events','interact_s',0),('trim_events','interact_point','wrong'),('trim_events','decay_per_s_if_ignored',0),('fail_timer','normal_s',60),('fail_timer','hard_s',None),('fail_timer','hard_s',float('inf')),('fail_timer','on_expire','continue')]:
   d=copy.deepcopy(self.data);d['beats'][13]['ext'][group][key]=value
   with self.subTest(group=group,key=key),self.assertRaises(BuildError):place_helm(d['beats'],d['space']['beats'],d['space']['zones'],fail)
 def test_other_beats_unchanged(self):
  for i,r in enumerate(self.data['space']['beats']):self.assertEqual('helm' in r,i==13)
 def test_real_rules_driver(self):
  with tempfile.TemporaryDirectory() as temp:
   binary=Path(temp)/'helm'
   subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-pedantic','-I',str(ROOT/'Source/SoraArena/Public'),str(ROOT/'scripts/unreal/helm_rules_driver.cpp'),'-o',str(binary)],check=True)
   subprocess.run([str(binary)],check=True)
if __name__=='__main__':unittest.main()
