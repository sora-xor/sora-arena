"""Stage the actual compiled Rust kernel for Unreal. Never builds a substitute."""
import argparse
import hashlib
import platform
import ctypes
import os
import tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('--platform',choices=['Mac','Win64'],default='Mac' if platform.system()=='Darwin' else 'Win64')
args=parser.parse_args()
name='libarena_ffi.dylib' if args.platform=='Mac' else 'arena_ffi.dll'
source=root/'target/release'/name
if not source.is_file(): raise SystemExit(f'Build the real kernel first: cargo build --release -p arena-ffi (missing {source})')
host='Mac' if platform.system()=='Darwin' else 'Win64' if platform.system()=='Windows' else 'Unsupported'
if args.platform!=host: raise SystemExit('Stage on the target platform so ABI and execution can be verified before copying.')
source_bytes=source.read_bytes()
source_hash=hashlib.sha256(source_bytes).digest()
from kernel_abi import Config, Participant, Input, Snapshot, Player, MapInfo, MapWall, Presentation, Weapon, Event, Projectile, load_kernel
lib=load_kernel(source)
for map_id in range(4):
    info=MapInfo();assert lib.arena_map_info(map_id,ctypes.byref(info))==0
    assert info.min_x<info.max_x and info.min_y<info.max_y and 0<info.wall_count<=64
    assert info.player_radius>0 and info.player_height>info.eye_height>0
    for index in range(info.wall_count):
        wall=MapWall();assert lib.arena_map_wall(map_id,index,ctypes.byref(wall))==0
        assert wall.min_x<wall.max_x and wall.min_y<wall.max_y and wall.min_z<wall.max_z
assert lib.arena_map_info(4,ctypes.byref(MapInfo()))!=0
for weapon_id in range(18):
    spec=Weapon();assert lib.arena_weapon_spec(weapon_id,ctypes.byref(spec))==0
    assert spec.id==weapon_id and spec.kind<=2 and spec.range_mm>0 and spec.cooldown_ticks>0
    assert (spec.magazine==0)==(spec.kind==0) and (spec.reload_ticks==0)==(spec.kind==0)
config=Config(2,0,0,60,0,1,1);participant=Participant(0,0,0,1,0,0,0)
handle=lib.arena_create(ctypes.byref(config),ctypes.byref(participant),1)
assert handle,'The actual kernel rejected the offline diagnostic session'
try:
    controls=Input(0,0,32,0,0,0)
    for tick in range(60): assert lib.arena_step(handle,ctypes.byref(controls),1)==0,f'Kernel failed at tick {tick}'
    state=Snapshot();assert lib.arena_snapshot(handle,ctypes.byref(state))==0
    assert state.abi_version==2 and state.tick==60 and state.player_count==1
    assert state.deposited==state.remaining==state.earnings==0,'Offline diagnostic moved simulated stake'
    digest=(ctypes.c_uint8*32)();assert lib.arena_state_hash(handle,digest,32)==0
    print(f'Actual kernel: ABI 2, {state.tick} offline ticks, proof_qualified={bool(lib.arena_proof_qualified())}, state_hash={bytes(digest).hex()}')
finally: lib.arena_destroy(handle)
projectile_config=Config(2,0,0,60,0,1,1)
grenadier=Participant(0,0,3,7,0,0,0)
handle=lib.arena_create(ctypes.byref(projectile_config),ctypes.byref(grenadier),1)
assert handle,'Reference projectile practice admission failed'
try:
    shot=Input(0,1,0,0,32768,0)
    assert lib.arena_step(handle,ctypes.byref(shot),1)==0
    state=Snapshot();assert lib.arena_snapshot(handle,ctypes.byref(state))==0
    assert state.event_count==1 and state.deposited==state.remaining==state.earnings==0
    player=Player();visual=Presentation()
    assert lib.arena_player(handle,0,ctypes.byref(player))==0
    assert lib.arena_player_presentation(handle,0,ctypes.byref(visual))==0
    assert player.weapon_id==7 and visual.yaw==32768 and visual.max_health==player.health and visual.cooldown_ticks>0
    assert (visual.ammo,visual.magazine,visual.reload_ticks)==(4,5,0)
    event=Event();assert lib.arena_event(handle,0,ctypes.byref(event))==0
    assert (event.tick,event.kind,event.actor_slot,event.weapon_id)==(0,1,0,7)
    count=ctypes.c_uint32();assert lib.arena_projectile_count(handle,ctypes.byref(count))==0 and count.value==1
    projectile=Projectile();assert lib.arena_projectile(handle,0,ctypes.byref(projectile))==0
    assert (projectile.id,projectile.owner_slot,projectile.weapon_id)==(0,0,7)
    shot.buttons=0;assert lib.arena_step(handle,ctypes.byref(shot),1)==0
    assert lib.arena_snapshot(handle,ctypes.byref(state))==0 and state.event_count==0
    assert lib.arena_event(handle,0,ctypes.byref(event))!=0,'Events must expire on the next step'
    shot.buttons=32;assert lib.arena_step(handle,ctypes.byref(shot),1)==0
    assert lib.arena_player_presentation(handle,0,ctypes.byref(visual))==0
    assert (visual.ammo,visual.magazine,visual.reload_ticks)==(4,5,144)
    print('Practice ABI verified: 4 reference maps, 18 weapons, player presentation, current-tick events and stable projectile IDs.')
finally: lib.arena_destroy(handle)
if hashlib.sha256(source.read_bytes()).digest()!=source_hash:
    raise SystemExit('The kernel changed while it was being validated. Finish the build, then stage it again.')
dest=root/'Binaries'/args.platform/name
dest.parent.mkdir(parents=True,exist_ok=True)
temporary=None
try:
    with tempfile.NamedTemporaryFile(dir=dest.parent,prefix=name+'.',suffix='.staging',delete=False) as output:
        temporary=Path(output.name)
        output.write(source_bytes);output.flush();os.fsync(output.fileno())
    temporary.chmod(source.stat().st_mode & 0o777)
    os.replace(temporary,dest)
finally:
    if temporary is not None and temporary.exists():temporary.unlink()
assert source_hash==hashlib.sha256(dest.read_bytes()).digest()
print(f'Staged {dest}\nSHA-256 {hashlib.sha256(dest.read_bytes()).hexdigest()}')
