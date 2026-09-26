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
from kernel_abi import ABI_VERSION, NONE, LOADOUT, BOT_NOVICE, BOT_STANDARD, BOT_VETERAN, BOT_MASTER, Config, Participant, Input, Snapshot, Player, MapInfo, MapWall, MapPoint, MapHazard, Presentation, Weapon, Event, Projectile, Entity, Objective, load_kernel
lib=load_kernel(source)
for map_id in range(4):
    info=MapInfo();assert lib.arena_map_info(map_id,ctypes.byref(info))==0
    assert info.min_x<info.max_x and info.min_y<info.max_y and 0<info.wall_count<=64
    assert info.player_radius>0 and info.player_height>info.eye_height>0
    for index in range(info.wall_count):
        wall=MapWall();assert lib.arena_map_wall(map_id,index,ctypes.byref(wall))==0
        assert wall.min_x<wall.max_x and wall.min_y<wall.max_y and wall.min_z<wall.max_z
    assert info.min_x<info.control_x<info.max_x and info.min_y<info.control_y<info.max_y and info.control_radius>0
    assert 0<info.checkpoint_0<info.checkpoint_1<info.checkpoint_2<info.route_length and info.push_radius>0
    route=[]
    for index in range(info.route_point_count):
        point=MapPoint();assert lib.arena_map_route_point(map_id,index,ctypes.byref(point))==0
        assert info.min_x<point.x<info.max_x and info.min_y<point.y<info.max_y;route.append((point.x,point.y))
    assert len(route)>=2 and sum(abs(b[0]-a[0])+abs(b[1]-a[1]) for a,b in zip(route,route[1:]))==info.route_length
    assert lib.arena_map_route_point(map_id,info.route_point_count,ctypes.byref(MapPoint()))!=0
    for index in range(info.hazard_count):
        hazard=MapHazard();assert lib.arena_map_hazard(map_id,index,ctypes.byref(hazard))==0
        assert 1<=hazard.kind<=3 and hazard.damage>0 and hazard.period>0 and hazard.min_z==0<hazard.max_z
    assert lib.arena_map_hazard(map_id,info.hazard_count,ctypes.byref(MapHazard()))!=0
assert lib.arena_map_info(4,ctypes.byref(MapInfo()))!=0
for weapon_id in range(18):
    spec=Weapon();assert lib.arena_weapon_spec(weapon_id,ctypes.byref(spec))==0
    assert spec.id==weapon_id and spec.kind<=2 and spec.range_mm>0 and spec.cooldown_ticks>0
    assert (spec.magazine==0)==(spec.kind==0) and (spec.reload_ticks==0)==(spec.kind==0)
config=Config(ABI_VERSION,0,0,60,0,1,1);participant=Participant(0,0,0,1,0,0,0)
handle=lib.arena_create(ctypes.byref(config),ctypes.byref(participant),1)
assert handle,'The actual kernel rejected the offline diagnostic session'
try:
    controls=Input(0,0,32,0,0,0)
    for tick in range(60): assert lib.arena_step(handle,ctypes.byref(controls),1)==0,f'Kernel failed at tick {tick}'
    state=Snapshot();assert lib.arena_snapshot(handle,ctypes.byref(state))==0
    assert state.abi_version==ABI_VERSION and state.tick==60 and state.player_count==1
    assert state.deposited==state.remaining==state.earnings==0,'Offline diagnostic moved simulated stake'
    digest=(ctypes.c_uint8*32)();assert lib.arena_state_hash(handle,digest,32)==0
    # An out-of-domain loadout request rejects the whole step atomically.
    before=bytes(digest);assert lib.arena_step(handle,ctypes.byref(Input(0,LOADOUT,6,0,0,0)),1)==2
    assert lib.arena_state_hash(handle,digest,32)==0 and bytes(digest)==before
    print(f'Actual kernel: ABI {ABI_VERSION}, {state.tick} offline ticks, proof_qualified={bool(lib.arena_proof_qualified())}, state_hash={bytes(digest).hex()}')
finally: lib.arena_destroy(handle)
projectile_config=Config(ABI_VERSION,0,0,60,0,1,1)
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
    assert (visual.charge_ticks_current,visual.charge_ticks_required)==(0,0)
    event=Event();assert lib.arena_event(handle,0,ctypes.byref(event))==0
    assert (event.tick,event.kind,event.actor_slot,event.target_slot,event.weapon_id,event.entity_id)==(0,1,0,NONE,7,0)
    count=ctypes.c_uint32();assert lib.arena_projectile_count(handle,ctypes.byref(count))==0 and count.value==1
    projectile=Projectile();assert lib.arena_projectile(handle,0,ctypes.byref(projectile))==0
    assert (projectile.id,projectile.owner_slot,projectile.weapon_id)==(0,0,7)
    shot.buttons=0;assert lib.arena_step(handle,ctypes.byref(shot),1)==0
    assert lib.arena_snapshot(handle,ctypes.byref(state))==0 and state.event_count==0
    assert lib.arena_event(handle,0,ctypes.byref(event))!=0,'Events must expire on the next step'
    shot.buttons=32;assert lib.arena_step(handle,ctypes.byref(shot),1)==0
    assert lib.arena_player_presentation(handle,0,ctypes.byref(visual))==0
    assert (visual.ammo,visual.magazine,visual.reload_ticks)==(4,5,144)
    print('Practice ABI verified: 4 reference maps with objectives and hazards, 18 weapons, player presentation, current-tick events and stable projectile IDs.')
finally: lib.arena_destroy(handle)
# A Karakuri barricade in a two-player Control match: the ability and entity
# events, the entity query and the locked objective snapshot.
control=Config(ABI_VERSION,1,0,60,0,2,1)
pair=(Participant*2)(Participant(0,0,4,9,0,0,0),Participant(1,1,0,1,0,0,0))
handle=lib.arena_create(ctypes.byref(control),pair,2)
assert handle,'Control practice admission failed'
try:
    frame=(Input*2)(Input(0,16,0,0,0,0),Input(1,0,0,0,32768,0))
    assert lib.arena_step(handle,frame,2)==0
    state=Snapshot();assert lib.arena_snapshot(handle,ctypes.byref(state))==0
    kinds=[]
    for index in range(state.event_count):
        event=Event();assert lib.arena_event(handle,index,ctypes.byref(event))==0;kinds.append(event.kind)
    assert kinds==[8,11],kinds
    count=ctypes.c_uint32();assert lib.arena_entity_count(handle,ctypes.byref(count))==0 and count.value==1
    entity=Entity();assert lib.arena_entity(handle,0,ctypes.byref(entity))==0
    assert (entity.id,entity.kind,entity.owner_slot,entity.health,entity.max_health,entity.age,entity.lifetime)==(1,2,0,250,250,1,1800)
    visual=Presentation();assert lib.arena_player_presentation(handle,0,ctypes.byref(visual))==0
    assert (visual.ability_cooldown_ticks,visual.ability_cooldown_total,visual.pending_class,visual.admitted_special)==(720,720,NONE,NONE)
    objective=Objective();assert lib.arena_objective(handle,ctypes.byref(objective))==0
    assert (objective.mode,objective.unlock_tick,objective.control_owner,objective.control_capture,objective.score_target,objective.winner_kind)==(1,600,NONE,480,10800,0)
finally: lib.arena_destroy(handle)
kanabo=Participant(0,0,3,6,0,0,0)
handle=lib.arena_create(ctypes.byref(projectile_config),ctypes.byref(kanabo),1)
assert handle,'Kanabo windup diagnostic admission failed'
try:
    visual=Presentation();assert lib.arena_player_presentation(handle,0,ctypes.byref(visual))==0
    assert (visual.charge_ticks_current,visual.charge_ticks_required)==(0,18)
    held=Input(0,1,0,0,0,0)
    for tick in range(18):
        assert lib.arena_step(handle,ctypes.byref(held),1)==0
        assert lib.arena_player_presentation(handle,0,ctypes.byref(visual))==0
        assert (visual.charge_ticks_current,visual.charge_ticks_required)==(tick+1,18)
        state=Snapshot();assert lib.arena_snapshot(handle,ctypes.byref(state))==0 and state.event_count==0
    assert lib.arena_step(handle,ctypes.byref(held),1)==0
    assert lib.arena_player_presentation(handle,0,ctypes.byref(visual))==0
    assert (visual.charge_ticks_current,visual.charge_ticks_required)==(0,18)
    state=Snapshot();assert lib.arena_snapshot(handle,ctypes.byref(state))==0 and state.event_count==1
finally: lib.arena_destroy(handle)
special=Participant(0,0,3,15,0,1,0)
handle=lib.arena_create(ctypes.byref(projectile_config),ctypes.byref(special),1)
assert handle,'Special weapon windup diagnostic admission failed'
try:
    visual=Presentation();melee=Input(0,2,0,0,0,0)
    for _ in range(18): assert lib.arena_step(handle,ctypes.byref(melee),1)==0
    assert lib.arena_player_presentation(handle,0,ctypes.byref(visual))==0
    assert (visual.charge_ticks_current,visual.charge_ticks_required)==(18,18)
    melee.buttons=1;assert lib.arena_step(handle,ctypes.byref(melee),1)==0
    assert lib.arena_player_presentation(handle,0,ctypes.byref(visual))==0
    assert (visual.charge_ticks_current,visual.charge_ticks_required)==(1,15)
    state=Snapshot();assert lib.arena_snapshot(handle,ctypes.byref(state))==0 and state.event_count==0
finally: lib.arena_destroy(handle)
# Practice bots drive every slot of a six-player minute: each plans once per
# tick, the kernel accepts every input, nothing is ever bonded, and bots refuse
# staked matches and finished ones.
practice=Config(ABI_VERSION,0,2,3600,0,6,1)
six=(Participant*6)(*(Participant(slot,slot%2,slot,2*slot+1,0,0,0) for slot in range(6)))
handle=lib.arena_create(ctypes.byref(practice),six,6)
assert handle,'Bot practice admission failed'
try:
    tiers=(BOT_MASTER,BOT_STANDARD,BOT_NOVICE,BOT_VETERAN,BOT_MASTER,BOT_NOVICE)
    shots=0
    for tick in range(3600):
        frame=(Input*6)()
        for slot,tier in enumerate(tiers):
            assert lib.arena_bot_input(handle,slot,tier,ctypes.byref(frame[slot]))==0,f'bot {slot} tick {tick}'
            again=Input();assert lib.arena_bot_input(handle,slot,tier,ctypes.byref(again))==0
            assert bytes(again)==bytes(frame[slot]),'A bot must plan once per tick'
        assert lib.arena_step(handle,frame,6)==0,f'Kernel rejected bot inputs at tick {tick}'
        state=Snapshot();assert lib.arena_snapshot(handle,ctypes.byref(state))==0
        assert (state.deposited,state.remaining,state.earnings)==(0,0,0)
        for index in range(state.event_count):
            event=Event();assert lib.arena_event(handle,index,ctypes.byref(event))==0;shots+=event.kind==1
    assert state.terminal==1 and shots>100,(state.terminal,shots)
    assert lib.arena_bot_input(handle,0,BOT_STANDARD,ctypes.byref(Input()))==2,'Bots must stop at the terminal tick'
    assert lib.arena_bot_input(handle,0,BOT_MASTER+1,ctypes.byref(Input()))==1,'An unknown tier must be refused'
    print(f'Practice bots verified: six bots, four tiers, {state.tick} ticks, {shots} shots, zero stake.')
finally: lib.arena_destroy(handle)
staked=Config(ABI_VERSION,0,0,60,1000,2,0)
bonded=(Participant*2)(Participant(0,0,0,1,1000,0,0),Participant(1,1,1,3,1000,0,0))
handle=lib.arena_create(ctypes.byref(staked),bonded,2)
assert handle,'Staked diagnostic admission failed'
try: assert lib.arena_bot_input(handle,0,BOT_STANDARD,ctypes.byref(Input()))==1,'Bots must refuse a staked match'
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
