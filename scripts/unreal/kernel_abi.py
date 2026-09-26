"""Exact first-release C ABI 4 bindings for local integration verification.

The canonical declarations remain crates/arena-ffi/include/arena.h. Missing
exports reject an outdated binary; this module does not stage or sign anything.
"""
import ctypes

ABI_VERSION=4
NONE=0xFFFFFFFF
LOADOUT=64
EVENT_KINDS=range(1,20)  # ARENA_EVENT_SHOT (1) .. ARENA_EVENT_MATCH_WINNER (19)
BOT_EASY,BOT_NORMAL,BOT_HARD=0,1,2  # ARENA_BOT_* practice difficulties

class Config(ctypes.Structure):
    _fields_=[('abi_version',ctypes.c_uint32),('mode',ctypes.c_uint32),('map_id',ctypes.c_uint32),('max_ticks',ctypes.c_uint32),('base_bond',ctypes.c_uint64),('player_count',ctypes.c_uint32),('offline',ctypes.c_uint32)]
class Participant(ctypes.Structure):
    _fields_=[('slot',ctypes.c_uint32),('team',ctypes.c_uint32),('class_id',ctypes.c_uint32),('weapon_id',ctypes.c_uint32),('bond',ctypes.c_uint64),('special_entitled',ctypes.c_uint32),('reserved',ctypes.c_uint32)]
class Input(ctypes.Structure):
    _fields_=[('slot',ctypes.c_uint32),('buttons',ctypes.c_uint32),('move_x',ctypes.c_int16),('move_y',ctypes.c_int16),('yaw',ctypes.c_uint16),('pitch',ctypes.c_int16)]
class Snapshot(ctypes.Structure):
    _fields_=[('abi_version',ctypes.c_uint32),('tick',ctypes.c_uint32),('player_count',ctypes.c_uint32),('terminal',ctypes.c_uint32),('proof_qualified',ctypes.c_uint32),('event_count',ctypes.c_uint32),('deposited',ctypes.c_uint64),('remaining',ctypes.c_uint64),('earnings',ctypes.c_uint64)]
class Player(ctypes.Structure):
    _fields_=[(name,ctypes.c_int32) for name in ['x','y','z','health','stamina']]+[(name,ctypes.c_uint32) for name in ['slot','team','class_id','weapon_id','alive','exhausted','respawn_ticks']]+[(name,ctypes.c_uint64) for name in ['initial_bond','remaining_bond','earnings']]+[('kills',ctypes.c_uint32),('deaths',ctypes.c_uint32)]
class MapInfo(ctypes.Structure):
    _fields_=[(name,ctypes.c_int32) for name in ['min_x','min_y','max_x','max_y','floor_z']]+[('wall_count',ctypes.c_uint32)]+[(name,ctypes.c_int32) for name in ['player_radius','player_height','eye_height','control_x','control_y','control_radius']]+[('route_point_count',ctypes.c_uint32)]+[(name,ctypes.c_int32) for name in ['route_length','checkpoint_0','checkpoint_1','checkpoint_2','push_radius']]+[('hazard_count',ctypes.c_uint32)]
class MapWall(ctypes.Structure):
    _fields_=[(name,ctypes.c_int32) for name in ['min_x','min_y','min_z','max_x','max_y','max_z']]
class MapPoint(ctypes.Structure):
    _fields_=[('x',ctypes.c_int32),('y',ctypes.c_int32)]
class MapHazard(ctypes.Structure):
    _fields_=[('kind',ctypes.c_uint32),('damage',ctypes.c_int32),('period',ctypes.c_uint32)]+[(name,ctypes.c_int32) for name in ['min_x','min_y','min_z','max_x','max_y','max_z']]
class Presentation(ctypes.Structure):
    _fields_=[('yaw',ctypes.c_uint16),('pitch',ctypes.c_int16),('cooldown_ticks',ctypes.c_uint32),('max_health',ctypes.c_int32),('guarding',ctypes.c_uint32),('spawn_protection_ticks',ctypes.c_uint32),('ability_cooldown_ticks',ctypes.c_uint32)]+[(name,ctypes.c_uint32) for name in ['ammo','magazine','reload_ticks','charge_ticks_current','charge_ticks_required','guard_ticks','ability_cooldown_total','stance_ticks','marked_ticks','pending_class','pending_weapon','admitted_special']]
class Weapon(ctypes.Structure):
    _fields_=[('id',ctypes.c_uint32),('kind',ctypes.c_uint32),('damage',ctypes.c_int32),('range_mm',ctypes.c_int32),('cooldown_ticks',ctypes.c_uint32)]+[(name,ctypes.c_int32) for name in ['stamina_cost','projectile_mm_tick','blast_mm','arming_mm']]+[(name,ctypes.c_uint32) for name in ['charge_ticks','magazine','reload_ticks']]
class Event(ctypes.Structure):
    _fields_=[(name,ctypes.c_uint32) for name in ['tick','kind','actor_slot','target_slot','weapon_id']]+[(name,ctypes.c_int32) for name in ['x','y','z','value']]+[(name,ctypes.c_uint32) for name in ['entity_id','entity_kind','detail']]
class Projectile(ctypes.Structure):
    _fields_=[(name,ctypes.c_uint32) for name in ['id','owner_slot','weapon_id']]+[(name,ctypes.c_int32) for name in ['x','y','z']]
class Entity(ctypes.Structure):
    _fields_=[(name,ctypes.c_uint32) for name in ['id','kind','owner_slot','team']]+[(name,ctypes.c_int32) for name in ['x','y','z']]+[('yaw',ctypes.c_uint32),('health',ctypes.c_int32),('max_health',ctypes.c_int32),('age',ctypes.c_uint32),('lifetime',ctypes.c_uint32)]+[(name,ctypes.c_int32) for name in ['half_x','half_y','height']]
class Objective(ctypes.Structure):
    _fields_=[(name,ctypes.c_uint32) for name in ['mode','unlock_tick','score_0','score_1','score_target','control_owner']]+[(name,ctypes.c_int32) for name in ['control_progress','control_capture']]+[(name,ctypes.c_uint32) for name in ['control_team_0','control_team_1','contested','overtime']]+[(name,ctypes.c_int32) for name in ['payload_progress','payload_length']]+[(name,ctypes.c_uint32) for name in ['payload_checkpoints','payload_idle','payload_rollback_delay']]+[(name,ctypes.c_int32) for name in ['payload_x','payload_y','payload_z']]+[(name,ctypes.c_uint32) for name in ['payload_attackers','payload_defenders','winner_kind','winner_value']]
assert [ctypes.sizeof(t) for t in (MapInfo,MapWall,MapPoint,MapHazard,Presentation,Weapon,Event,Projectile,Entity,Objective)]==[76,24,8,36,72,48,48,24,60,96]

def load_kernel(source):
    # The staging/practice diagnostics intentionally contain assertions with
    # native calls. Never permit an optimized interpreter to skip those checks.
    # Keep this inside the entry point so the parity runner can invalidate an
    # earlier success report before reporting failure.
    if not __debug__:
        raise RuntimeError('Native validation requires assertions; Python optimization is unsupported')
    lib=ctypes.CDLL(str(source))
    lib.arena_abi_version.restype=ctypes.c_uint32
    lib.arena_proof_qualified.restype=ctypes.c_uint32
    if lib.arena_abi_version()!=ABI_VERSION:
        raise RuntimeError('Wrong kernel ABI; exactly ABI 4 is required')
    lib.arena_create.argtypes=[ctypes.POINTER(Config),ctypes.POINTER(Participant),ctypes.c_size_t];lib.arena_create.restype=ctypes.c_void_p
    lib.arena_step.argtypes=[ctypes.c_void_p,ctypes.POINTER(Input),ctypes.c_size_t];lib.arena_step.restype=ctypes.c_int32
    lib.arena_snapshot.argtypes=[ctypes.c_void_p,ctypes.POINTER(Snapshot)];lib.arena_snapshot.restype=ctypes.c_int32
    lib.arena_destroy.argtypes=[ctypes.c_void_p];lib.arena_destroy.restype=None
    lib.arena_state_hash.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint8),ctypes.c_size_t];lib.arena_state_hash.restype=ctypes.c_int32
    for export,parameters in {
        'arena_player':[ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(Player)],
        'arena_map_info':[ctypes.c_uint32,ctypes.POINTER(MapInfo)],
        'arena_map_wall':[ctypes.c_uint32,ctypes.c_uint32,ctypes.POINTER(MapWall)],
        'arena_map_route_point':[ctypes.c_uint32,ctypes.c_uint32,ctypes.POINTER(MapPoint)],
        'arena_map_hazard':[ctypes.c_uint32,ctypes.c_uint32,ctypes.POINTER(MapHazard)],
        'arena_player_presentation':[ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(Presentation)],
        'arena_weapon_spec':[ctypes.c_uint32,ctypes.POINTER(Weapon)],
        'arena_event':[ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(Event)],
        'arena_projectile_count':[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)],
        'arena_projectile':[ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(Projectile)],
        'arena_entity_count':[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)],
        'arena_entity':[ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(Entity)],
        'arena_objective':[ctypes.c_void_p,ctypes.POINTER(Objective)],
        'arena_bot_input':[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.POINTER(Input)],
    }.items():
        function=getattr(lib,export)  # Missing new export rejects stale binaries before copying.
        function.argtypes=parameters;function.restype=ctypes.c_int32
    return lib
