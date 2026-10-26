"""Compiled charge timing plus authored metadata rejection; no Unreal claims."""
import copy
import json
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
            subprocess.run([str(binary)],check=True,env=env)

    def test_authored_contract_and_rejections(self):
        chapter=json.loads((ROOT/'Content/Data/campaign/chapter_03.json').read_text())
        self.assertTrue(square.notice_valid(chapter))
        for key in square.contract():
            c=copy.deepcopy(chapter);r=next(r for r in c['space']['beats'] if r['beat']=='ch03.b10')
            r['terminal_charge'][key][0]+=1
            self.assertFalse(square.notice_valid(c),key)
        for change in ('missing','unexpected','objective','lamp','zone','anchor'):
            c=copy.deepcopy(chapter);r=next(r for r in c['space']['beats'] if r['beat']=='ch03.b10')
            if change=='missing':del r['terminal_charge']
            elif change=='unexpected':c['space']['beats'][0]['terminal_charge']=square.contract()
            elif change=='objective':r['objectives'][2]=[0,0]
            elif change=='lamp':next(l for l in r['fieldcraft']['lamps'] if l['id']=='terminal_glow_b10')['at']=[0,0]
            elif change=='zone':c['space']['zones'][r['zone']]['rect'][0]-=1
            else:r['anchor'][0]-=1
            self.assertFalse(square.notice_valid(c),change)


if __name__=='__main__':unittest.main()
