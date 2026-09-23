"""Exact first-release C ABI bindings for local integration verification.

The canonical declarations remain crates/arena-ffi/include/arena.h. Missing
exports reject an outdated binary; this module does not stage or sign anything.
"""
import ctypes

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
    _fields_=[(name,ctypes.c_int32) for name in ['min_x','min_y','max_x','max_y','floor_z']]+[('wall_count',ctypes.c_uint32)]+[(name,ctypes.c_int32) for name in ['player_radius','player_height','eye_height']]
class MapWall(ctypes.Structure):
    _fields_=[(name,ctypes.c_int32) for name in ['min_x','min_y','min_z','max_x','max_y','max_z']]
class Presentation(ctypes.Structure):
    _fields_=[('yaw',ctypes.c_uint16),('pitch',ctypes.c_int16),('cooldown_ticks',ctypes.c_uint32),('max_health',ctypes.c_int32),('guarding',ctypes.c_uint32),('spawn_protection_ticks',ctypes.c_uint32),('ability_cooldown_ticks',ctypes.c_uint32)]+[(name,ctypes.c_uint32) for name in ['ammo','magazine','reload_ticks']]
class Weapon(ctypes.Structure):
    _fields_=[('id',ctypes.c_uint32),('kind',ctypes.c_uint32),('damage',ctypes.c_int32),('range_mm',ctypes.c_int32),('cooldown_ticks',ctypes.c_uint32)]+[(name,ctypes.c_int32) for name in ['stamina_cost','projectile_mm_tick','blast_mm','arming_mm']]+[(name,ctypes.c_uint32) for name in ['charge_ticks','magazine','reload_ticks']]
class Event(ctypes.Structure):
    _fields_=[(name,ctypes.c_uint32) for name in ['tick','kind','actor_slot','target_slot','weapon_id']]+[(name,ctypes.c_int32) for name in ['x','y','z','value']]
class Projectile(ctypes.Structure):
    _fields_=[(name,ctypes.c_uint32) for name in ['id','owner_slot','weapon_id']]+[(name,ctypes.c_int32) for name in ['x','y','z']]
assert [ctypes.sizeof(t) for t in (MapInfo,MapWall,Presentation,Weapon,Event,Projectile)]==[36,24,36,48,36,24]

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
    if lib.arena_abi_version()!=2:
        raise RuntimeError('Wrong kernel ABI; exactly ABI 2 is required')
    lib.arena_create.argtypes=[ctypes.POINTER(Config),ctypes.POINTER(Participant),ctypes.c_size_t];lib.arena_create.restype=ctypes.c_void_p
    lib.arena_step.argtypes=[ctypes.c_void_p,ctypes.POINTER(Input),ctypes.c_size_t];lib.arena_step.restype=ctypes.c_int32
    lib.arena_snapshot.argtypes=[ctypes.c_void_p,ctypes.POINTER(Snapshot)];lib.arena_snapshot.restype=ctypes.c_int32
    lib.arena_destroy.argtypes=[ctypes.c_void_p];lib.arena_destroy.restype=None
    lib.arena_state_hash.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint8),ctypes.c_size_t];lib.arena_state_hash.restype=ctypes.c_int32
    for export,parameters in {
        'arena_player':[ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(Player)],
        'arena_map_info':[ctypes.c_uint32,ctypes.POINTER(MapInfo)],
        'arena_map_wall':[ctypes.c_uint32,ctypes.c_uint32,ctypes.POINTER(MapWall)],
        'arena_player_presentation':[ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(Presentation)],
        'arena_weapon_spec':[ctypes.c_uint32,ctypes.POINTER(Weapon)],
        'arena_event':[ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(Event)],
        'arena_projectile_count':[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)],
        'arena_projectile':[ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(Projectile)],
    }.items():
        function=getattr(lib,export)  # Missing new export rejects stale binaries before copying.
        function.argtypes=parameters;function.restype=ctypes.c_int32
    return lib
