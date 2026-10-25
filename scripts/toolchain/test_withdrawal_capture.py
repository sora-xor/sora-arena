"""Reject incomplete or substituted live withdrawal screenshots/observations."""
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

SPEC = importlib.util.spec_from_file_location('capture_report', Path(__file__).with_name('verify-capture-report.py'))
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)
RULES = VERIFY.withdrawal_capture_validation


def observations():
    data = dict(schema=RULES.SCHEMA, scope=RULES.SCOPE, passed=True, ordinary_clock=True,
                profiles_preserved=True, mappings_preserved=True, temporary_slot_deleted=True,
                viewport=[1280,720], completions=1, survivor_shots=0, down_before=0, down_at_completion=0,
                defense_ms=150003, defense_world_s=151.2, defense_wall_s=151.3,
                walked_cm=12000, gate_clear_world_s=2.6, gate_clear_wall_s=2.61, frames=[])
    for i, phase in enumerate(RULES.PHASES):
        people = [dict(actor=f'Enemy{n}', position=[[-300,-700,-2300,-2300][i]+n*10, n*10,90],
                       screen=[350+n*60,360], at_approach=(i>=2),feet_z=0,grounded=True) for n in range(6)]
        data['frames'].append(dict(phase=phase,file=phase+'.png',request_frame=9100+i*120,processed_frame=9100+i*120,
            world_s=[151.2,153.2,160.2,160.3][i],wall_s=[151.3,153.31,160.31,160.41][i],walked_cm=[0,2400,12000,12000][i],
            defense_ms=150003,paused=False,hud_drawn=(i<3),english=True,
            camera=[-500,-3400,1900] if i<3 else [-2220,0,1200],
            camera_rotation=[math.degrees(math.atan2(-1800,3400)),90,0] if i<3 else [math.degrees(math.atan2(-1110,80)),180,0],
            camera_fov=75 if i<3 else 45,survivors=people,
            cue='ch02.b02.enforcer.009' if i<2 else 'ch02.b06.kohagi.006'))
    return data


class WithdrawalCaptureTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name).resolve()
        self.project=self.root/'game with spaces';self.folder=self.project/'Saved/Screenshots/SoraWithdrawal/1280x720/unique'
        self.folder.mkdir(parents=True)
        def chunk(kind, payload):
            return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload))
        self.png=(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1280,720,8,2,0,0,0))+
                  chunk(b'IDAT',zlib.compress((b'\0'+b'\x10\x20\x30'*1280)*720))+chunk(b'IEND',b''))
        self.paths=[self.folder/(p+'.png') for p in RULES.PHASES]
        for p in self.paths:p.write_bytes(self.png)
        self.start=min(p.stat().st_mtime_ns for p in self.paths)-1
        self.sidecar=self.folder/'capture.json';self.data=observations();self.write();self.serial=0
        self.report={'tests':[{'fullTestPath':'SoraCapture.HorseWithdrawal.Live'}]}

    def write(self):self.sidecar.write_text(json.dumps(self.data,indent=2)+'\n')
    def log(self, paths=None):
        return '\n'.join('LogTemp: Display: SORA_WITHDRAWAL_FRAME '+str(p) for p in (self.paths if paths is None else paths))
    def archive(self, log=None):
        self.serial+=1;out=self.root/f'archive{self.serial}'
        return out,VERIFY.archive_frames(self.log() if log is None else log,self.report,self.project,self.root,out,self.start,1280,720)
    def verify(self):RULES.verify_sequence(self.data,[p.name for p in self.paths],1280,720)

    def test_preserves_original_bytes_and_exact_sidecar(self):
        out,frames=self.archive();raw=self.sidecar.read_bytes()
        self.assertEqual([f['withdrawal_phase'] for f in frames],list(RULES.PHASES))
        self.paths[0].write_bytes(b'later run');self.sidecar.write_text('later run')
        for f in frames:
            self.assertEqual((out/f['path']).read_bytes(),self.png)
            self.assertEqual(f['sha256'],hashlib.sha256(self.png).hexdigest())
            self.assertEqual((out/f['observations']).read_bytes(),raw)
            self.assertEqual(f['capture_kind'],RULES.SCOPE)

    def test_rejects_missing_reordered_duplicate_and_replayed_originals(self):
        for log in ('',self.log(self.paths[:-1]),self.log(list(reversed(self.paths))),self.log(self.paths+self.paths[:1]),
                    self.log().replace('LogTemp: Display:','LogAutomationController: Display:')+' [log]'):
            with self.subTest(log=log[:50]),self.assertRaises(ValueError):self.archive(log)

    def test_rejects_other_runs_stale_and_escaped_metadata(self):
        self.report={'tests':[{'fullTestPath':'SoraCapture.HorseWithdrawal.Other'}]}
        with self.assertRaisesRegex(ValueError,'matching'):self.archive()
        self.report={'tests':[{'fullTestPath':'SoraCapture.HorseWithdrawal.Live'}]}
        os.utime(self.sidecar,ns=(self.start-1,self.start-1))
        with self.assertRaisesRegex(ValueError,'stale'):self.archive()
        self.sidecar.unlink();outside=self.root/'outside.json';outside.write_text(json.dumps(self.data));self.sidecar.symlink_to(outside)
        with self.assertRaisesRegex(ValueError,'escaped'):self.archive()

    def test_failed_semantics_still_preserve_all_actual_pixels(self):
        self.data['passed']=False;self.write()
        with self.assertRaises(VERIFY.WithdrawalCaptureEvidenceError) as caught:self.archive()
        frames=caught.exception.frames;self.assertEqual(len(frames),4)
        for f in frames:
            self.assertEqual((self.root/'archive1'/f['path']).read_bytes(),self.png)
            self.assertEqual((self.root/'archive1'/f['observations']).read_bytes(),self.sidecar.read_bytes())

    def test_rejects_compressed_clocks_kill_credit_and_missing_cleanup(self):
        original=copy.deepcopy(self.data)
        cases=[('schema','old'),('scope','ordinary defense'),('completions',2),('survivor_shots',1),('down_at_completion',1),
               ('defense_ms',149999),('defense_world_s',30),('defense_wall_s',30),('gate_clear_world_s',.2),
               ('gate_clear_wall_s',.2),('walked_cm',0),('viewport',[True,720])]
        for key in ('passed','ordinary_clock','profiles_preserved','mappings_preserved','temporary_slot_deleted'):
            cases.extend((key,bad) for bad in (False,1,None))
        for key,bad in cases:
            with self.subTest(key=key,bad=bad):
                self.data=copy.deepcopy(original);self.data[key]=bad
                with self.assertRaises(ValueError):self.verify()

    def test_rejects_frame_substitution_hidden_hud_and_fake_arrival(self):
        original=copy.deepcopy(self.data)
        mutations=[lambda r:r.update(processed_frame=1),lambda r:r.update(world_s=float('nan')),
                   lambda r:r.update(paused=True),lambda r:r.update(english=1),lambda r:r.update(hud_drawn=False),
                   lambda r:r.update(cue='cinematic'),lambda r:r.update(camera=[0,0,0]),
                   lambda r:r['survivors'].pop(),lambda r:r['survivors'][0].update(actor='replacement'),
                   lambda r:r['survivors'][0].update(position=[-1000,0,90]),
                   lambda r:r['survivors'][0].update(at_approach=1),lambda r:r['survivors'][0].update(feet_z=300),
                   lambda r:r['survivors'][0].update(grounded=False),lambda r:r['survivors'][0].update(screen=[-1,360])]
        for i,mutate in enumerate(mutations):
            with self.subTest(mutation=i):
                self.data=copy.deepcopy(original);mutate(self.data['frames'][2])
                with self.assertRaises(ValueError):self.verify()
        self.data=copy.deepcopy(original);self.data['frames'][1]['survivors']=copy.deepcopy(self.data['frames'][0]['survivors'])
        with self.assertRaisesRegex(ValueError,'displacement'):self.verify()

    def test_detail_cannot_replace_hud_evidence_or_reuse_wide_camera(self):
        original=copy.deepcopy(self.data)
        mutations=[lambda r:r.update(camera=[-500,-3400,1900]),lambda r:r.update(camera_rotation=[0,180,0]),
                   lambda r:r.update(camera_fov=75),lambda r:r.update(camera_fov=float('nan')),
                   lambda r:r.update(hud_drawn=True),lambda r:r.update(hud_drawn=0),
                   lambda r:r.update(cue='cinematic'),lambda r:r.update(request_frame=9340,processed_frame=9340),
                   lambda r:r['survivors'][0].update(grounded=False),
                   lambda r:r['survivors'][0].update(actor='replacement'),
                   lambda r:r['survivors'][0].update(position=[-1000,0,90])]
        for i,mutate in enumerate(mutations):
            with self.subTest(mutation=i):
                self.data=copy.deepcopy(original);mutate(self.data['frames'][3])
                with self.assertRaises(ValueError):self.verify()
        for phase in range(3):
            with self.subTest(hidden_overview=phase):
                self.data=copy.deepcopy(original);self.data['frames'][phase]['hud_drawn']=False
                with self.assertRaises(ValueError):self.verify()


if __name__=='__main__':unittest.main()
