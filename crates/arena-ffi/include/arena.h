#ifndef SORA_ARENA_H
#define SORA_ARENA_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* First-release ABI. No legacy decoder or fallback. All spatial values are mm.
 * Coordinates: X forward, Y right, Z up. Yaw is 0..65535 / full turn.
 * Pitch is signed -16384..16384. APIs never authorize ledger spending.
 * Status: 0 OK, 1 invalid argument, 2 simulation rejected, 3 panic contained.
 * One owning thread must serialize access to each handle. */
typedef struct ArenaHandle ArenaHandle;
/* Query arena_abi_version() and require exactly 3 before using this layout.
 * Earlier development layouts are rejected; there is no compatibility mode. */
typedef struct {
    uint32_t abi_version, mode, map_id, max_ticks;
    uint64_t base_bond;
    uint32_t player_count, offline;
} ArenaConfig;
typedef struct {
    uint32_t slot, team, class_id, weapon_id;
    uint64_t bond;
    uint32_t special_entitled, reserved;
} ArenaParticipant;
/* buttons: 1 fire, 2 melee, 4 block, 8 jump, 16 ability, 32 reload.
 * move_x/y range -127..127. Input array must contain exactly one per slot. */
typedef struct {
    uint32_t slot, buttons;
    int16_t move_x, move_y;
    uint16_t yaw;
    int16_t pitch;
} ArenaInput;
typedef struct {
    int32_t x, y, z, health, stamina;
    uint32_t slot, team, class_id, weapon_id, alive, exhausted, respawn_ticks;
    uint64_t initial_bond, remaining_bond, earnings;
    uint32_t kills, deaths;
} ArenaPlayerSnapshot;
typedef struct {
    uint32_t abi_version, tick, player_count, terminal;
    uint32_t proof_qualified, event_count;
    uint64_t deposited, remaining, earnings;
} ArenaSnapshot;
typedef struct {
    int32_t min_x, min_y, max_x, max_y, floor_z;
    uint32_t wall_count;
    int32_t player_radius, player_height, eye_height;
} ArenaMapInfo;
typedef struct { int32_t min_x, min_y, min_z, max_x, max_y, max_z; } ArenaMapWall;
typedef struct {
    uint16_t yaw;
    int16_t pitch;
    uint32_t cooldown_ticks;
    int32_t max_health;
    uint32_t guarding, spawn_protection_ticks, ability_cooldown_ticks;
    uint32_t ammo, magazine, reload_ticks; /* Reload state is authoritative. */
    uint32_t charge_ticks_current, charge_ticks_required; /* Current selected windup. */
} ArenaPlayerPresentation;
typedef struct {
    uint32_t id, kind; /* kind: 0 melee, 1 hitscan, 2 projectile */
    int32_t damage, range_mm;
    uint32_t cooldown_ticks;
    int32_t stamina_cost, projectile_mm_tick, blast_mm, arming_mm;
    uint32_t charge_ticks, magazine, reload_ticks;
} ArenaWeaponSpec;
/* Events are replaced by EVERY step. Read before advancing again. Tick is the
 * zero-based input tick just executed. Absent slots/weapons are UINT32_MAX.
 * kind: 1 shot, 2 damage, 3 death, 4 respawn, 5 terminal. value is damage only;
 * read player snapshots for balances. These are presentation events, not proofs. */
typedef struct {
    uint32_t tick, kind, actor_slot, target_slot, weapon_id;
    int32_t x, y, z, value;
} ArenaEvent;
typedef struct {
    uint32_t id, owner_slot, weapon_id;
    int32_t x, y, z;
} ArenaProjectileSnapshot;
uint32_t arena_abi_version(void);
ArenaHandle* arena_create(const ArenaConfig*, const ArenaParticipant*, size_t count);
void arena_destroy(ArenaHandle*);
int32_t arena_step(ArenaHandle*, const ArenaInput*, size_t count);
int32_t arena_snapshot(const ArenaHandle*, ArenaSnapshot*);
int32_t arena_player(const ArenaHandle*, uint32_t slot, ArenaPlayerSnapshot*);
int32_t arena_state_hash(const ArenaHandle*, uint8_t* output32, size_t length);
int32_t arena_map_info(uint32_t map_id, ArenaMapInfo*);
int32_t arena_map_wall(uint32_t map_id, uint32_t index, ArenaMapWall*);
int32_t arena_player_presentation(const ArenaHandle*, uint32_t slot, ArenaPlayerPresentation*);
int32_t arena_weapon_spec(uint32_t weapon_id, ArenaWeaponSpec*);
int32_t arena_event(const ArenaHandle*, uint32_t index, ArenaEvent*);
int32_t arena_projectile_count(const ArenaHandle*, uint32_t*);
int32_t arena_projectile(const ArenaHandle*, uint32_t index, ArenaProjectileSnapshot*);
/* Always zero until a reviewed compiled FPS relation is actually qualified. */
uint32_t arena_proof_qualified(void);
#ifdef __cplusplus
}
#endif
#endif
