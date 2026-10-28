"""Compiled charge timing plus authored metadata rejection; no Unreal claims."""
import copy
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest
import campaign_notice_square as square

ROOT=Path(__file__).resolve().parents[2]


class TerminalChargeTests(unittest.TestCase):
    def test_compiled_boundaries_interruption_and_frame_partitions(self):
        env=os.environ.copy();flags=[];compiler=shutil.which('clang++') or shutil.which('c++')
        if platform.system()=='Darwin':
            pins=json.loads((ROOT/'scripts/toolchain/versions.json').read_text())
            env['DEVELOPER_DIR']=env.get('SORA_DEVELOPER_DIR') or str(Path(pins['default_macos_xcode']).expanduser())
            compiler=subprocess.check_output(['xcrun','--find','clang++'],env=env,text=True).strip()
            flags=['-isysroot',subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],env=env,text=True).strip()]
        if not compiler:raise RuntimeError('C++ compiler required')
        with tempfile.TemporaryDirectory(prefix='sora-terminal-charge-') as directory:
            binary=Path(directory)/'charge'
            subprocess.run([compiler,'-std=c++20','-UNDEBUG','-Wall','-Wextra','-Werror',
                '-fsanitize=undefined','-fsanitize-trap=undefined',*flags,'-I',str(ROOT/'Source/SoraArena/Public'),
                str(ROOT/'scripts/unreal/terminal_charge_rules_driver.cpp'),'-o',str(binary)],check=True,env=env)
            compiled=json.loads(subprocess.check_output([str(binary)],env=env,text=True))
        chapter=json.loads((ROOT/'Content/Data/campaign/chapter_03.json').read_text())
        record=next(r for r in chapter['space']['beats'] if r['beat']=='ch03.b10')
        self.assertEqual(compiled['patrols'],record['patrols'][2:])
        self.assertEqual(compiled['patrols'],square.ground_patrols())
        self.assertEqual(compiled['periods_ms'],[60000,60000,45000,45000,70000])
        self.assertEqual(compiled['drone'],record['patrols'][1])
        self.assertEqual(compiled['drone'],square.DRONE)
        self.assertEqual(compiled['drone_contract'],square.contract()['drone_circuit_cm_ms'])
        # Independently check the analytic circle, chord error and required
        # physical speed; agreement between two copied tables is insufficient.
        for i,a in enumerate(compiled['drone']):
            angle=2*math.pi*i/32
            self.assertLessEqual(math.dist(a,[540*math.cos(angle),540*math.sin(angle)]),.71)
            b=compiled['drone'][(i+1)%32]
            mid=[(a[j]+b[j])/2 for j in range(2)]
            self.assertLess(abs(math.hypot(*mid)-540),3)
            self.assertLess(math.dist(a,b)/(36/32),110)
        enemies={e['id']:e for e in json.loads((ROOT/'Content/Data/enemies.json').read_text())['archetypes']}
        types=['enforcer_rifle']*2+['bound_conscript']*2+['blade_retainer']
        for route,period,kind in zip(compiled['patrols'],compiled['periods_ms'],types,strict=True):
            seconds=period/len(route)/1000
            for a,b in zip(route,route[1:]+route[:1]):
                self.assertLess(math.dist(a,b)/seconds,enemies[kind]['speed_cm_s'])
        for index,spacing in ((0,4000),(2,3000)):
            self.assertEqual(compiled['patrols'][index+1],compiled['patrols'][index][-1:]+compiled['patrols'][index][:-1])
            self.assertEqual(compiled['periods_ms'][index]//len(compiled['patrols'][index]),spacing)

    def test_authored_contract_and_rejections(self):
        chapter=json.loads((ROOT/'Content/Data/campaign/chapter_03.json').read_text())
        self.assertTrue(square.notice_valid(chapter))
        for key in square.contract():
            c=copy.deepcopy(chapter);r=next(r for r in c['space']['beats'] if r['beat']=='ch03.b10')
            r['terminal_charge'][key][0]+=1
            self.assertFalse(square.notice_valid(c),key)
        for change in ('missing','unexpected','objective','lamp','zone','anchor','patrol','pair_phase','authored_period','authored_extent','authored_offset','guard_type','drone_point','drone_count','drone_radius','drone_height','drone_period','roof_missing','roof_base','roof_kind','roof_guards','roof_post','roof_noise','authored_roof'):
            c=copy.deepcopy(chapter);r=next(r for r in c['space']['beats'] if r['beat']=='ch03.b10')
            if change=='missing':del r['terminal_charge']
            elif change=='unexpected':c['space']['beats'][0]['terminal_charge']=square.contract()
            elif change=='objective':r['objectives'][2]=[0,0]
            elif change=='lamp':next(l for l in r['fieldcraft']['lamps'] if l['id']=='terminal_glow_b10')['at']=[0,0]
            elif change=='zone':c['space']['zones'][r['zone']]['rect'][0]-=1
            elif change=='authored_period':next(p for p in c['layout']['patrols'] if p['id']=='pt_b10_p1')['loop_s']=61
            elif change=='authored_extent':next(p for p in c['layout']['patrols'] if p['id']=='pt_b10_p2')['points_cm'][1][1]=1500
            elif change=='authored_offset':c['beats'][9]['params']['guards'][3]['x_patrol_offset_s']=3
            elif change=='guard_type':c['beats'][9]['task']['guards'][4]['type']='enforcer_rifle'
            elif change=='patrol':r['patrols'][6][1][0]=3200
            elif change=='pair_phase':r['patrols'][3]=copy.deepcopy(r['patrols'][2])
            elif change=='drone_point':r['patrols'][1][0][0]+=1
            elif change=='drone_count':r['patrols'][1].pop()
            elif change=='drone_radius':next(p for p in c['layout']['patrols'] if p['id']=='pt_b10_d')['circle_cm']['radius']=1200
            elif change=='drone_height':next(p for p in c['layout']['patrols'] if p['id']=='pt_b10_d')['alt_cm']=599
            elif change=='drone_period':next(p for p in c['layout']['patrols'] if p['id']=='pt_b10_d')['loop_s']=35
            elif change=='roof_missing':r['fieldcraft']['ladders'].pop()
            elif change=='roof_base':r['fieldcraft']['ladders'][1]['base_height_cm']=0
            elif change=='roof_kind':r['fieldcraft']['ladders'][1]['world_roof']='notice_pent'
            elif change=='roof_guards':r['fieldcraft']['ladders'][1]['guards']=[]
            elif change=='roof_post':r['patrols'][0][0][1]=1200
            elif change=='roof_noise':next(s for s in r['fieldcraft']['surfaces'] if s['kind']=='board_roof')['height_cm']=540
            elif change=='authored_roof':c['beats'][9]['ext']['ladders'][1]['base_height_cm']=0
            else:r['anchor'][0]-=1
            self.assertFalse(square.notice_valid(c),change)


if __name__=='__main__':unittest.main()
