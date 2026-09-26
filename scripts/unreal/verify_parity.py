"""Verify checked-in canonical practice fixtures on macOS or Windows.

Normal runs are read-only with respect to fixtures. --record-reference is an
explicit baseline-authoring operation, never a fallback for a failing check.
The current reference was recorded on macOS; Windows parity is not implied.
"""
from pathlib import Path
import argparse
import ctypes
import datetime
import hashlib
import json
import math
import platform
import struct
import sys

import kernel_abi as abi
import practice_fixture_bots as bots

ROOT=Path(__file__).resolve().parents[2]
FIXTURE_ID='sora-arena-practice-abi4'
DEFAULT_FIXTURE=Path(__file__).resolve().parent/'fixtures/practice-abi4'
SOURCE_FILES=[
    'Cargo.toml','Cargo.lock','crates/arena-core/Cargo.toml',
    'crates/arena-core/src/lib.rs','crates/arena-core/src/catalog.rs',
    'crates/arena-core/src/economy.rs','crates/arena-core/src/math.rs',
    'crates/arena-core/src/maps.rs','crates/arena-core/src/simulation.rs',
    'crates/arena-core/src/simulation/abilities.rs','crates/arena-core/src/simulation/hazards.rs',
    'crates/arena-core/src/simulation/objectives.rs','crates/arena-core/src/simulation/respawn.rs',
    'crates/arena-ffi/Cargo.toml',
    'crates/arena-ffi/src/lib.rs','crates/arena-ffi/include/arena.h',
]
# The scripted players author the recorded controls; verification replays the
# stored bytes, but a changed author still requires a reviewed re-record.
RUNNER_FILES=['scripts/unreal/kernel_abi.py','scripts/unreal/verify_parity.py','scripts/unreal/practice_fixture_bots.py']
TYPES={name:getattr(abi,name) for name in ('Config','Participant','Input','Snapshot','Player','MapInfo','MapWall','MapPoint','MapHazard','Presentation','Weapon','Event','Projectile','Entity','Objective')}
SCALARS={ctypes.c_uint16:('u16','H'),ctypes.c_int16:('i16','h'),ctypes.c_uint32:('u32','I'),ctypes.c_int32:('i32','i'),ctypes.c_uint64:('u64','Q')}
WIRE=struct.Struct('<HbbHh')
ACTIVE_REPORT=None

def require(condition,message):
    if not condition:raise RuntimeError(message)

def sha(data):return hashlib.sha256(data).hexdigest()

def source_identity():
    # Text normalization is explicit so Git CRLF checkout policy does not create
    # a false Windows mismatch. The selected files own the exercised C ABI/World.
    return {name:sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n')) for name in SOURCE_FILES}

def runner_identity():
    return {name:sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n')) for name in RUNNER_FILES}

def layout():
    return {name:{'size':ctypes.sizeof(cls),'alignment':ctypes.alignment(cls),'fields':[
        {'name':field,'type':SCALARS[kind][0],'offset':getattr(cls,field).offset}
        for field,kind in cls._fields_]} for name,cls in TYPES.items()}

def encode(value):
    # Hash named fields in specified little-endian order, never C padding bytes.
    return b''.join(struct.pack('<'+SCALARS[kind][1],getattr(value,name)) for name,kind in value._fields_)

def state_hash(lib,handle):
    data=(ctypes.c_uint8*32)()
    require(lib.arena_state_hash(handle,data,32)==0,'arena_state_hash failed')
    return bytes(data)

def native_data_identity(lib):
    # Weapons keep the v1 encoding; ABI 4 map data adds the objective fields,
    # payload route points and hazard volumes.
    geometry=hashlib.sha256(b'sora-arena-practice-geometry-v2\0')
    weapons=hashlib.sha256(b'sora-arena-practice-weapons-v1\0')
    for map_id in range(4):
        info=abi.MapInfo();require(lib.arena_map_info(map_id,ctypes.byref(info))==0,'map info failed')
        geometry.update(struct.pack('<I',map_id)+encode(info))
        for index in range(info.wall_count):
            wall=abi.MapWall();require(lib.arena_map_wall(map_id,index,ctypes.byref(wall))==0,'map wall failed')
            geometry.update(encode(wall))
        for index in range(info.route_point_count):
            point=abi.MapPoint();require(lib.arena_map_route_point(map_id,index,ctypes.byref(point))==0,'route point failed')
            geometry.update(encode(point))
        for index in range(info.hazard_count):
            hazard=abi.MapHazard();require(lib.arena_map_hazard(map_id,index,ctypes.byref(hazard))==0,'hazard failed')
            geometry.update(encode(hazard))
    for weapon_id in range(18):
        weapon=abi.Weapon();require(lib.arena_weapon_spec(weapon_id,ctypes.byref(weapon))==0,'weapon spec failed')
        weapons.update(encode(weapon))
    return {'reference_geometry_sha256':geometry.hexdigest(),'weapon_specs_sha256':weapons.hexdigest()}

def roster(class_id,weapon_slot):
    return [{'slot':slot,'team':slot%2,'class_id':class_id if slot==0 else slot,
             'weapon_id':(12+class_id if weapon_slot==2 else 2*class_id+weapon_slot) if slot==0 else 2*slot+1,
             'bond':0,'special_entitled':0,'reserved':0} for slot in range(6)]

def config(map_id,ticks):
    return {'abi_version':abi.ABI_VERSION,'mode':0,'map_id':map_id,'max_ticks':ticks,'base_bond':0,'player_count':6,'offline':1}

def expected_case_ids():
    return ([f'map{m}-class{c}-loadout{w}' for m in range(4) for c in range(6) for w in range(3)]
            +['estate-death-respawn']+[scenario.id for scenario in bots.SCENARIOS])

def make_controls(lib):
    exercise=bytearray()
    for tick in range(600):
        for slot in range(6):
            phase=(tick+slot*73)%360
            yaw=(32768,0,49152,16384,40960,8192)[slot]
            buttons=(1 if phase<260 else 0)|(8 if phase==20 else 0)|(16 if phase==170 else 0)|(4 if phase>310 else 0)
            exercise.extend(WIRE.pack(buttons,90 if phase<180 else -50,55 if phase%120<60 else -55,yaw,0))
    # Record the exact canonical aim once. Verification never recalculates aim
    # through a host's floating-point math implementation. On Nyaagyu Estate
    # the slot 2 Teppo (Coil matchlock) and the slot 0 target start at FFA
    # spawns 2 and 0, in clear sight along x = -18500.
    people=roster(0,1)
    native_people=(abi.Participant*6)(*(abi.Participant(**p) for p in people))
    native_config=abi.Config(**config(0,900));handle=lib.arena_create(ctypes.byref(native_config),native_people,6)
    require(bool(handle),'death fixture admission failed')
    try:
        target=abi.Player();attacker=abi.Player()
        require(lib.arena_player(handle,0,ctypes.byref(target))==0,'target query failed')
        require(lib.arena_player(handle,2,ctypes.byref(attacker))==0,'attacker query failed')
        require(attacker.class_id==2 and attacker.weapon_id==5,'death fixture attacker must hold the Coil matchlock')
        yaw=round(math.atan2(target.y-attacker.y,target.x-attacker.x)*65536/(2*math.pi))&65535
    finally:lib.arena_destroy(handle)
    death=b''.join(WIRE.pack(1 if slot==2 else 0,0,0,yaw if slot==2 else 0,0) for _ in range(900) for slot in range(6))
    controls={'exercise.controls':bytes(exercise),'death-respawn.controls':death}
    # Every other case is played by the scripted players, which read the real
    # kernel each tick; the bytes they chose are the recorded controls. A case
    # whose bytes equal an earlier file's (a staked twin) reuses that file.
    ticks={};files={};navigators={}
    for scenario in bots.SCENARIOS:
        data,ticks[scenario.id]=bots.record(lib,scenario,navigators)
        files[scenario.id]=next((name for name,other in controls.items() if other==data),scenario.id+'.controls')
        controls.setdefault(files[scenario.id],data)
    return controls,people,ticks,files

def decode_frame(data,tick,count):
    frame=(abi.Input*count)()
    for slot in range(count):
        buttons,x,y,yaw,pitch=WIRE.unpack_from(data,(tick*count+slot)*WIRE.size)
        require(buttons&~127==0 and -127<=x<=127 and -127<=y<=127 and -16384<=pitch<=16384,'non-canonical controls')
        require(not buttons&abi.LOADOUT or (0<=x<=5 and 0<=y<=2),'non-canonical loadout request')
        frame[slot]=abi.Input(slot,buttons,x,y,yaw,pitch)
    return frame

def check_declaration(case,data):
    """Admission terms and control length, checked for every case before any runs."""
    cfg=abi.Config(**case['config']);bonds=[p['bond'] for p in case['participants']]
    require(cfg.abi_version==abi.ABI_VERSION and cfg.player_count==len(bonds),case['id']+': declared configuration mismatch')
    if cfg.offline:require(cfg.offline==1 and cfg.base_bond==0 and not any(bonds),case['id']+': offline case must be zero-stake practice')
    else:require(cfg.base_bond>0 and cfg.base_bond%10==0 and all(b in (cfg.base_bond,2*cfg.base_bond) for b in bonds),case['id']+': staked case must carry exact admission bonds')
    require(0<case['ticks']<=cfg.max_ticks and len(data)==case['ticks']*cfg.player_count*WIRE.size,case['id']+': control length does not match declared ticks/slots')

def run_case(lib,case,data):
    check_declaration(case,data)
    cfg=abi.Config(**case['config']);count=cfg.player_count;ticks=case['ticks']
    bonds=[p['bond'] for p in case['participants']]
    people=(abi.Participant*count)(*(abi.Participant(**p) for p in case['participants']))
    handle=lib.arena_create(ctypes.byref(cfg),people,count);require(bool(handle),'fixture admission failed')
    states=hashlib.sha256(b'sora-arena-practice-states-v1\0')
    events=hashlib.sha256(b'sora-arena-practice-events-v2\0')
    presentation=hashlib.sha256(b'sora-arena-practice-presentation-v2\0')
    counts={str(kind):0 for kind in abi.EVENT_KINDS};checkpoints=[]
    try:
        initial=state_hash(lib,handle).hex()
        for field,value in (('move_x',128),('buttons',256)):
            invalid=decode_frame(data,0,count);setattr(invalid[0],field,value)
            require(lib.arena_step(handle,invalid,count)!=0 and state_hash(lib,handle).hex()==initial,'invalid input changed state')
        invalid=decode_frame(data,0,count);invalid[0].buttons=abi.LOADOUT;invalid[0].move_x=6;invalid[0].move_y=0
        require(lib.arena_step(handle,invalid,count)!=0 and state_hash(lib,handle).hex()==initial,'invalid loadout request changed state')
        for tick in range(ticks):
            frame=decode_frame(data,tick,count)
            require(lib.arena_step(handle,frame,count)==0,f'step {tick} rejected')
            snapshot=abi.Snapshot();require(lib.arena_snapshot(handle,ctypes.byref(snapshot))==0,'snapshot failed')
            require(snapshot.abi_version==abi.ABI_VERSION and snapshot.player_count==count and snapshot.tick==tick+1,'snapshot identity/tick mismatch')
            require(snapshot.proof_qualified==0,'fixture changed proof qualification')
            require(snapshot.deposited==sum(bonds) and snapshot.remaining+snapshot.earnings==snapshot.deposited,'fixture failed to conserve deposits')
            require(bool(snapshot.terminal)==(tick+1==ticks),f'{case["id"]}: terminal at tick {tick+1}, declared {ticks}')
            digest=state_hash(lib,handle)
            states.update(struct.pack('<I',snapshot.tick)+digest)
            events.update(struct.pack('<II',tick,snapshot.event_count))
            for index in range(snapshot.event_count):
                event=abi.Event();require(lib.arena_event(handle,index,ctypes.byref(event))==0,'event query failed')
                require(event.tick==tick and event.kind in abi.EVENT_KINDS,'event tick/kind mismatch')
                events.update(encode(event));counts[str(event.kind)]+=1
            presentation.update(encode(snapshot))
            for slot in range(count):
                player=abi.Player();visual=abi.Presentation()
                require(lib.arena_player(handle,slot,ctypes.byref(player))==0,'player query failed')
                require(lib.arena_player_presentation(handle,slot,ctypes.byref(visual))==0,'presentation query failed')
                require(player.slot==slot and player.initial_bond==bonds[slot] and player.remaining_bond<=player.initial_bond,'player identity/economy mismatch')
                presentation.update(encode(player)+encode(visual))
            number=ctypes.c_uint32();require(lib.arena_projectile_count(handle,ctypes.byref(number))==0,'projectile count failed')
            presentation.update(struct.pack('<I',number.value))
            for index in range(number.value):
                projectile=abi.Projectile();require(lib.arena_projectile(handle,index,ctypes.byref(projectile))==0,'projectile query failed')
                presentation.update(encode(projectile))
            require(lib.arena_entity_count(handle,ctypes.byref(number))==0,'entity count failed')
            presentation.update(struct.pack('<I',number.value))
            for index in range(number.value):
                entity=abi.Entity();require(lib.arena_entity(handle,index,ctypes.byref(entity))==0,'entity query failed')
                presentation.update(encode(entity))
            objective=abi.Objective();require(lib.arena_objective(handle,ctypes.byref(objective))==0,'objective query failed')
            require(objective.mode==cfg.mode,'objective mode mismatch')
            presentation.update(encode(objective))
            if snapshot.tick%60==0 or snapshot.terminal:
                checkpoint={'tick':snapshot.tick,'state_hash':digest.hex(),'state_stream_sha256':states.hexdigest(),'event_stream_sha256':events.hexdigest(),'presentation_stream_sha256':presentation.hexdigest()}
                checkpoints.append(checkpoint)
                if 'expected' in case:
                    expected=case['expected']['checkpoints'][len(checkpoints)-1]
                    require(checkpoint==expected,f'{case["id"]}: checkpoint mismatch at tick {snapshot.tick}\nexpected {expected}\nobserved {checkpoint}')
        final=state_hash(lib,handle)
        require(lib.arena_step(handle,frame,count)!=0 and state_hash(lib,handle)==final,'terminal input changed state')
        result={'initial_state_hash':initial,'final_state_hash':final.hex(),'state_stream_sha256':states.hexdigest(),'event_stream_sha256':events.hexdigest(),'presentation_stream_sha256':presentation.hexdigest(),
                'event_counts':counts,'winner':{'kind':objective.winner_kind,'value':objective.winner_value},
                'economy':{'deposited':snapshot.deposited,'remaining':snapshot.remaining,'earnings':snapshot.earnings},'checkpoints':checkpoints}
        if 'expected' in case:require(result==case['expected'],case['id']+': final digest mismatch')
        return result
    finally:lib.arena_destroy(handle)

def control_record(name,data):
    return {'file':name,'bytes':len(data),'sha256':sha(data)}

def record_requirements(cases):
    by_id={case['id']:case['expected'] for case in cases}
    kinds={kind for expected in by_id.values() for kind,number in expected['event_counts'].items() if number}
    require(kinds=={str(kind) for kind in abi.EVENT_KINDS},f'fixture does not exercise every exported event kind: {sorted(kinds)}')
    death=by_id['estate-death-respawn']['event_counts']
    require(death['3']>0 and death['4']>0,'death/respawn fixture not exercised')
    overtime=by_id['control4-overtime-estate']
    require(overtime['event_counts']['17']==1 and overtime['winner']=={'kind':1,'value':0},'Control overtime case did not end in a secured win')
    escort=by_id['payload6-escort-estate']
    require(escort['event_counts']['18']==3 and escort['winner']=={'kind':1,'value':0},'Payload escort case did not complete the route')
    duel=by_id['staked-melee2-foundry']
    require(duel['winner']=={'kind':2,'value':0} and duel['economy']['earnings']==1000,'staked duel did not end by exhaustion')
    for case_id in ('staked-ffa8-lantern','staked-control12-citadel'):
        require(by_id[case_id]['economy']['earnings']>0,case_id+': no paid death')

def main():
    global ACTIVE_REPORT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',type=Path,help='Actual target-platform Rust C ABI library; defaults to Binaries/Mac or Binaries/Win64.')
    parser.add_argument('--fixture-dir',type=Path,default=DEFAULT_FIXTURE)
    parser.add_argument('--report',type=Path)
    parser.add_argument('--record-reference',action='store_true',help='Explicitly author/replace reviewed fixture expectations from the loaded native kernel.')
    args=parser.parse_args()
    system=platform.system()
    ACTIVE_REPORT=args.report or ROOT/f'Saved/Diagnostics/parity-{system}-{platform.machine()}.json'
    ACTIVE_REPORT.parent.mkdir(parents=True,exist_ok=True)
    ACTIVE_REPORT.write_text(json.dumps({'status':'running','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'system':system,'machine':platform.machine()},indent=2)+'\n')
    require(system in ('Darwin','Windows'),'parity runner supports macOS and Windows target libraries')
    require(ctypes.sizeof(ctypes.c_void_p)==8 and sys.byteorder=='little','64-bit little-endian target required')
    library=args.library or ROOT/'Binaries'/('Mac/libarena_ffi.dylib' if system=='Darwin' else 'Win64/arena_ffi.dll')
    lib=abi.load_kernel(library);require(lib.arena_proof_qualified()==0,'fixture expects unqualified practice, not money settlement')
    observed_layout=layout();identity=source_identity();runner=runner_identity();native_identity=native_data_identity(lib)
    fixture=args.fixture_dir.resolve();manifest_path=fixture/'manifest.json'
    runtime={'system':system,'machine':platform.machine(),'python':platform.python_version(),'library_sha256':sha(library.read_bytes())}
    if args.record_reference:
        controls,death_roster,ticks,files=make_controls(lib)
        manifest={'schema_version':2,'fixture_id':FIXTURE_ID,'scope':'offline and staked C ABI 4 simulation, event, objective and presentation parity; not network, renderer or execution-proof qualification',
            'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reference_host':runtime,
            'input_encoding':{'bytes_per_slot':8,'format':'<HbbHh','fields':['buttons:u16','forward:i8','right:i8','yaw:u16','pitch:i16'],'endianness':'little','order':'tick-major then permanent slot ascending; no padding, tick and slot implicit','tick_rate':60},
            'source_identity':{'normalization':'replace CRLF with LF in UTF-8 source bytes','scope':'exact files owning the exercised World/geometry/combat/economy/C ABI plus dependency manifests; unrelated transport/proof implementation is excluded','files_sha256':identity},
            'runner_files_sha256':runner,'abi_layout':observed_layout,'native_data_identity':native_identity,'controls':[control_record(name,data) for name,data in controls.items()],
            'digest_encoding':'SHA-256 domain prefixes in verify_parity.py; named C fields encoded individually in declared order as little-endian scalars, excluding padding; event streams include every tick, its count and every event; state streams include every completed tick and native state hash; presentation streams include the snapshot, every player and presentation, projectile, entity and the objective snapshot','cases':[]}
        for map_id in range(4):
            for class_id in range(6):
                for weapon_slot in range(3):
                    manifest['cases'].append({'id':f'map{map_id}-class{class_id}-loadout{weapon_slot}','config':config(map_id,600),'participants':roster(class_id,weapon_slot),'controls':'exercise.controls','ticks':600})
        manifest['cases'].append({'id':'estate-death-respawn','config':config(0,900),'participants':death_roster,'controls':'death-respawn.controls','ticks':900})
        for scenario in bots.SCENARIOS:
            manifest['cases'].append({'id':scenario.id,'config':scenario.config(),'participants':scenario.participants,'controls':files[scenario.id],'ticks':ticks[scenario.id]})
        require([case['id'] for case in manifest['cases']]==expected_case_ids(),'recorded case list differs from the declared cases')
        for case in manifest['cases']:case['expected']=run_case(lib,case,controls[case['controls']])
        record_requirements(manifest['cases'])
        require(source_identity()==identity and runner_identity()==runner and sha(library.read_bytes())==runtime['library_sha256'],'source or library changed during reference recording')
        fixture.mkdir(parents=True,exist_ok=True)
        for name,data in controls.items():(fixture/name).write_bytes(data)
        manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        print(f'Recorded {len(manifest["cases"])} actual native reference cases on {system}/{platform.machine()}; other platforms remain unverified.')
    else:
        manifest=json.loads(manifest_path.read_text())
        require(manifest['schema_version']==2 and manifest['fixture_id']==FIXTURE_ID,'unsupported fixture identity')
        require(manifest['input_encoding']['format']=='<HbbHh' and manifest['input_encoding']['bytes_per_slot']==8 and manifest['input_encoding']['tick_rate']==60,'unexpected input encoding')
        require(identity==manifest['source_identity']['files_sha256'],'source identity changed; review changes before explicitly authoring a new reference fixture')
        require(runner==manifest['runner_files_sha256'],'fixture runner identity changed; review changes before explicitly authoring a new reference fixture')
        require(observed_layout==manifest['abi_layout'],'target C ABI layout diverges from the checked-in reference')
        require(native_identity==manifest['native_data_identity'],'native map/weapon data diverges from reference')
        controls={}
        for record in manifest['controls']:
            name=record['file'];require(Path(name).name==name,'control file must be inside the fixture directory')
            data=(fixture/name).read_bytes()
            require(len(data)==record['bytes'] and sha(data)==record['sha256'],name+': canonical control identity mismatch')
            controls[name]=data
        require([case['id'] for case in manifest['cases']]==expected_case_ids(),'fixture must cover all 72 map/loadouts, the targeted death/respawn and every scripted mode case')
        for case in manifest['cases']:check_declaration(case,controls[case['controls']])
        for case in manifest['cases']:run_case(lib,case,controls[case['controls']])
        require(source_identity()==identity and runner_identity()==runner and sha(library.read_bytes())==runtime['library_sha256'],'source or library changed during verification')
        print(f'PASS: {len(manifest["cases"])} checked-in cases and {sum(c["ticks"] for c in manifest["cases"]):,} canonical ticks match on {system}/{platform.machine()}.')
    report={'status':'pass','verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'operation':'record-reference' if args.record_reference else 'verify','scope':manifest['scope'],'fixture_id':manifest['fixture_id'],'manifest_sha256':sha(manifest_path.read_bytes()),'runtime':runtime,'reference_host':manifest['reference_host'],'source_identity':identity,'native_data_identity':native_identity,'cases':len(manifest['cases']),'ticks':sum(c['ticks'] for c in manifest['cases']),'proof_qualified':False,'platform_claim':'This report verifies only the named runtime host. It does not imply execution on any other platform.'}
    ACTIVE_REPORT.write_text(json.dumps(report,indent=2)+'\n')
    print(f'Report: {ACTIVE_REPORT}')

if __name__=='__main__':
    try:main()
    except (AssertionError,RuntimeError,KeyError,OSError,ValueError,IndexError,AttributeError) as error:
        if ACTIVE_REPORT is not None:
            try:ACTIVE_REPORT.write_text(json.dumps({'status':'fail','failed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'error':str(error)},indent=2)+'\n')
            except OSError:pass
        print(f'PARITY CHECK FAILED: {error}',file=sys.stderr);raise SystemExit(1)
