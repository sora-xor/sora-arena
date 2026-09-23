"""Headless native practice/replay checks; not an Unreal runtime verification.

Uses the actual staged Rust library. Checks every map and class/loadout, repeat
execution hashes, zero asset movement, rejected-input atomicity, terminal state,
new presentation exports and the same bounded clock compiled into the game mode.
"""
from pathlib import Path
import ctypes
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import tempfile

from kernel_abi import Config, Participant, Input, Snapshot, Player, Presentation, Event, load_kernel

ROOT=Path(__file__).resolve().parents[2]
system=platform.system()
if system not in ('Darwin','Windows'):
    raise SystemExit('Run on a supported target platform against its staged native kernel.')
source=ROOT/'Binaries'/('Mac/libarena_ffi.dylib' if system=='Darwin' else 'Win64/arena_ffi.dll')
lib=load_kernel(source)
assert lib.arena_proof_qualified()==0, 'Reassess this verification gate when proof qualification changes.'

def digest(handle):
    value=(ctypes.c_uint8*32)()
    assert lib.arena_state_hash(handle,value,32)==0
    return bytes(value).hex()

def roster(class_id,weapon_slot):
    people=(Participant*6)()
    for slot in range(6):
        cat=class_id if slot==0 else slot
        weapon=(12+cat if weapon_slot==2 else cat*2+weapon_slot) if slot==0 else cat*2+1
        people[slot]=Participant(slot,slot%2,cat,weapon,0,0,0)
    return people

def controls(tick):
    frame=(Input*6)()
    for slot in range(6):
        # A fixed canonical transcript, shared by two independent handles.
        phase=(tick+slot*73)%360
        yaw=(32768,0,49152,16384,40960,8192)[slot]
        buttons=(1 if phase<260 else 0)|(8 if phase==20 else 0)|(16 if phase==170 else 0)|(4 if phase>310 else 0)
        frame[slot]=Input(slot,buttons,90 if phase<180 else -50,55 if phase%120<60 else -55,yaw,0)
    return frame

records=[]
shots=damage_events=respawns=0
for map_id in range(4):
    for class_id in range(6):
        for weapon_slot in range(3):
            config=Config(3,0,map_id,600,0,6,1)
            people=roster(class_id,weapon_slot)
            a=lib.arena_create(ctypes.byref(config),people,6)
            b=lib.arena_create(ctypes.byref(config),people,6)
            assert a and b, (map_id,class_id,weapon_slot)
            try:
                before=digest(a);invalid=controls(0);invalid[0].move_x=128
                assert lib.arena_step(a,invalid,6)!=0 and digest(a)==before
                for tick in range(600):
                    frame=controls(tick)
                    assert lib.arena_step(a,frame,6)==0 and lib.arena_step(b,frame,6)==0
                    state=Snapshot();assert lib.arena_snapshot(a,ctypes.byref(state))==0
                    assert state.abi_version==3 and state.tick==tick+1 and state.deposited==state.remaining==state.earnings==0
                    for index in range(state.event_count):
                        event=Event();assert lib.arena_event(a,index,ctypes.byref(event))==0
                        assert event.tick==tick
                        shots+=event.kind==1;damage_events+=event.kind==2;respawns+=event.kind==4
                    if tick%60==59:
                        assert digest(a)==digest(b),'Canonical transcript replay diverged'
                        for slot in range(6):
                            player=Player();visual=Presentation()
                            assert lib.arena_player(a,slot,ctypes.byref(player))==0
                            assert lib.arena_player_presentation(a,slot,ctypes.byref(visual))==0
                            assert player.initial_bond==player.remaining_bond==player.earnings==0
                            assert player.health<=visual.max_health and 0<=player.stamina<=100
                            assert 0<=visual.charge_ticks_current<=visual.charge_ticks_required<=600
                assert state.terminal==1
                final=digest(a)
                assert lib.arena_step(a,controls(600),6)!=0 and digest(a)==final
                records.append({'map':map_id,'class':class_id,'weapon_slot':weapon_slot,'ticks':600,'state_hash':final})
            finally:
                lib.arena_destroy(a);lib.arena_destroy(b)

# Clear sightline on the east side of the estate: a stationary matchlock bot
# eliminates slot zero, which must respawn without creating any economic value.
death_config=Config(3,0,0,900,0,6,1);people=roster(0,1)
people[4]=Participant(4,0,2,5,0,0,0)
handle=lib.arena_create(ctypes.byref(death_config),people,6);assert handle
death_count=respawn_count=0
try:
    victim=Player();attacker=Player()
    assert lib.arena_player(handle,0,ctypes.byref(victim))==0
    assert lib.arena_player(handle,4,ctypes.byref(attacker))==0
    yaw=round(math.atan2(victim.y-attacker.y,victim.x-attacker.x)*65536/(2*math.pi))&65535
    frame=(Input*6)(*(Input(slot,1 if slot==4 else 0,0,0,yaw if slot==4 else 0,0) for slot in range(6)))
    for tick in range(900):
        assert lib.arena_step(handle,frame,6)==0
        state=Snapshot();assert lib.arena_snapshot(handle,ctypes.byref(state))==0
        assert state.deposited==state.remaining==state.earnings==0
        for index in range(state.event_count):
            event=Event();assert lib.arena_event(handle,index,ctypes.byref(event))==0
            if event.kind==3 and event.target_slot==0:
                death_count+=1;assert event.actor_slot==4
            if event.kind==4 and event.target_slot==0:respawn_count+=1
    assert death_count>0 and respawn_count>0,'Death/respawn event presentation path was not exercised'
finally:lib.arena_destroy(handle)

clock_source=r'''
#include "SoraPracticeClock.h"
#include <cassert>
#include <limits>
int main() {
    for(int fps: {30,60,120,144,240}) {
        FSoraPracticeClock clock; int count=0;
        for(int frame=0;frame<fps*10;++frame) count+=clock.Advance(1.0/fps);
        assert(count==600); assert(!clock.Slowed);
    }
    FSoraPracticeClock hitch;
    assert(hitch.Advance(4.0)==8 && hitch.Slowed);
    assert(hitch.Advance(0.0)==0 && !hitch.Slowed);
    assert(hitch.Advance(1.0/120.0)==0);
    hitch.Reset(); // menu time never becomes simulation backlog
    assert(hitch.Advance(1.0/120.0)==0);
    assert(hitch.Advance(1.0/120.0)==1);
    assert(hitch.Advance(-1.0)==0);
    assert(hitch.Advance(std::numeric_limits<double>::infinity())==0);
    assert(hitch.Advance(std::numeric_limits<double>::quiet_NaN())==0);
}
'''
clock_checked=False
compiler=shutil.which('clang++') or shutil.which('g++')
if compiler:
    with tempfile.TemporaryDirectory(prefix='sora-practice-clock-') as folder:
        cpp=Path(folder)/'clock.cpp';cpp.write_text('#include <initializer_list>\n'+clock_source)
        binary=Path(folder)/('clock.exe' if system=='Windows' else 'clock')
        environment=os.environ.copy()
        xcode=Path('/Applications/Xcode.app/Contents/Developer')
        if system=='Darwin' and xcode.exists():environment.setdefault('DEVELOPER_DIR',str(xcode))
        subprocess.run([compiler,'-std=c++17','-Wall','-Wextra','-Werror','-I',str(ROOT/'Source/SoraArena/Public'),str(cpp),'-o',str(binary)],check=True,env=environment)
        subprocess.run([str(binary)],check=True)
        clock_checked=True
else:
    raise SystemExit('Native replay passed, but a C++ compiler is required to verify the shared fixed-step clock.')

report={'scope':'native C ABI and shared clock; Unreal runtime remains unverified','library_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'proof_qualified':False,'scenarios':len(records),'replayed_ticks':len(records)*600*2,'shots':shots,'damage_events':damage_events,'respawns':respawns,'targeted_deaths':death_count,'targeted_respawns':respawn_count,'clock_compiled_and_passed':clock_checked,'records':records}
output=ROOT/'Saved/Diagnostics/practice_replay_report.json';output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(report,indent=2)+'\n')
print(f'Practice native checks passed: {len(records)} map/class/loadout scenarios, {report["replayed_ticks"]:,} replayed ticks; zero deposits, repeat hashes, rejected-input atomicity and bounded clock verified.')
print(f'Observed {shots} shots, {damage_events} damage events, {respawns} respawns. Report: {output}')
print(f'Targeted elimination scenario: {death_count} deaths and {respawn_count} respawns, with zero asset movement.')
