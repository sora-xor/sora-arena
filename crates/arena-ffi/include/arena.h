#ifndef SORA_ARENA_H
#define SORA_ARENA_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* First-release ABI 4. No legacy decoder or fallback. All spatial values are mm.
 * Coordinates: X forward, Y right, Z up. Yaw is 0..65535 / full turn.
 * Pitch is signed -16384..16384. APIs never authorize ledger spending.
 * Status: 0 OK, 1 invalid argument, 2 simulation rejected, 3 panic contained.
 * One owning thread must serialize access to each handle. Rules and numbers:
 * docs/combat-rules.md. Absent slots, weapons, classes and teams are ARENA_NONE. */
#define ARENA_ABI_VERSION 4u
#define ARENA_NONE 0xFFFFFFFFu
typedef struct ArenaHandle ArenaHandle;
/* Query arena_abi_version() and require exactly ARENA_ABI_VERSION before using
 * this layout. ABI 3 and earlier layouts are rejected; there is no compatibility
 * mode. mode: 0 free-for-all, 1 Control, 2 Payload (team 0 attacks), 3 Melee.
 * 1-12 participants: at most 8 in modes 0 and 3, at most 6 per team in 1 and 2.
 * offline 1 is zero-stake practice: base_bond and every bond are 0. offline 0
 * is staked: base_bond > 0 and divisible by 10, and each bond is base_bond, or
 * 2 * base_bond for a special weapon (12-17) without special_entitled. */
typedef struct {
    uint32_t abi_version, mode, map_id, max_ticks;
    uint64_t base_bond;
    uint32_t player_count, offline;
} ArenaConfig;
/* Slot i is the i-th entry. team 0 or 1; class 0-5; weapon 2c, 2c+1 or 12+c;
 * Melee mode admits only melee weapons. reserved must be 0. */
typedef struct {
    uint32_t slot, team, class_id, weapon_id;
    uint64_t bond;
    uint32_t special_entitled, reserved;
} ArenaParticipant;
#define ARENA_BUTTON_FIRE 1u
#define ARENA_BUTTON_MELEE 2u
#define ARENA_BUTTON_BLOCK 4u
#define ARENA_BUTTON_JUMP 8u
#define ARENA_BUTTON_ABILITY 16u
#define ARENA_BUTTON_RELOAD 32u
/* With LOADOUT a dead player requests class move_x (0-5) and loadout move_y
 * (0 ranged 2c+1, 1 melee 2c, 2 the admitted special 12+c) for its next
 * respawn. Living players ignore the bit and still move by move_x/move_y. */
#define ARENA_BUTTON_LOADOUT 64u
/* move_x/y range -127..127. Input array must contain exactly one per slot, in
 * slot order. Any other button bit or out-of-range value rejects the whole step
 * with status 2 and changes nothing. */
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
/* tick counts completed input ticks. deposited never changes and always equals
 * remaining + earnings. event_count is the number of events of the last step. */
typedef struct {
    uint32_t abi_version, tick, player_count, terminal;
    uint32_t proof_qualified, event_count;
    uint64_t deposited, remaining, earnings;
} ArenaSnapshot;
/* Arena data (docs/combat-rules.md section 7): bounds, static walls, the Control
 * circle, the axis-aligned payload route with its three checkpoint distances
 * and push radius, and the hazard volumes. */
typedef struct {
    int32_t min_x, min_y, max_x, max_y, floor_z;
    uint32_t wall_count;
    int32_t player_radius, player_height, eye_height;
    int32_t control_x, control_y, control_radius;
    uint32_t route_point_count;
    int32_t route_length, checkpoint_0, checkpoint_1, checkpoint_2, push_radius;
    uint32_t hazard_count;
} ArenaMapInfo;
typedef struct { int32_t min_x, min_y, min_z, max_x, max_y, max_z; } ArenaMapWall;
typedef struct { int32_t x, y; } ArenaMapPoint;
#define ARENA_HAZARD_FIRE 1u
#define ARENA_HAZARD_SLAG 2u
#define ARENA_HAZARD_SHREDDER 3u
/* Deals damage every period ticks to a player whose feet are inside the box. */
typedef struct {
    uint32_t kind;
    int32_t damage;
    uint32_t period;
    int32_t min_x, min_y, min_z, max_x, max_y, max_z;
} ArenaMapHazard;
typedef struct {
    uint16_t yaw;
    int16_t pitch;
    uint32_t cooldown_ticks;
    int32_t max_health;
    uint32_t guarding, spawn_protection_ticks, ability_cooldown_ticks;
    uint32_t ammo, magazine, reload_ticks; /* Reload state is authoritative. */
    uint32_t charge_ticks_current, charge_ticks_required; /* Current selected windup. */
    uint32_t guard_ticks; /* Held guard ticks; a parry needs at most 8 and 20 stamina. */
    uint32_t ability_cooldown_total; /* Full cooldown of the current class. */
    uint32_t stance_ticks, marked_ticks; /* Samurai stance; Teppo mark on this player. */
    uint32_t pending_class, pending_weapon; /* Requested respawn loadout, or ARENA_NONE. */
    uint32_t admitted_special; /* Special weapon frozen at admission, or ARENA_NONE. */
} ArenaPlayerPresentation;
typedef struct {
    uint32_t id, kind; /* kind: 0 melee, 1 hitscan, 2 projectile */
    int32_t damage, range_mm;
    uint32_t cooldown_ticks;
    int32_t stamina_cost, projectile_mm_tick, blast_mm, arming_mm;
    uint32_t charge_ticks, magazine, reload_ticks;
} ArenaWeaponSpec;
/* Event kinds. 1-5 keep their ABI 3 meaning; 6-19 export every other kernel event. */
#define ARENA_EVENT_SHOT 1u
#define ARENA_EVENT_DAMAGE 2u
#define ARENA_EVENT_DEATH 3u
#define ARENA_EVENT_RESPAWN 4u
#define ARENA_EVENT_TERMINAL 5u
#define ARENA_EVENT_GUARDED 6u
#define ARENA_EVENT_HEALED 7u
#define ARENA_EVENT_ABILITY 8u
#define ARENA_EVENT_MARKED 9u
#define ARENA_EVENT_RIPOSTE 10u
#define ARENA_EVENT_ENTITY_SPAWNED 11u
#define ARENA_EVENT_ENTITY_DAMAGED 12u
#define ARENA_EVENT_ENTITY_REPAIRED 13u
#define ARENA_EVENT_ENTITY_DESTROYED 14u
#define ARENA_EVENT_HAZARD_DAMAGE 15u
#define ARENA_EVENT_OBJECTIVE_CAPTURED 16u
#define ARENA_EVENT_OVERTIME 17u
#define ARENA_EVENT_CHECKPOINT 18u
#define ARENA_EVENT_MATCH_WINNER 19u
#define ARENA_ENTITY_DECOY 1u
#define ARENA_ENTITY_BARRICADE 2u
#define ARENA_ENTITY_FIRE_ZONE 3u
#define ARENA_ENTITY_WARD 4u
#define ARENA_REMOVAL_EXPIRED 0u
#define ARENA_REMOVAL_DESTROYED 1u
#define ARENA_REMOVAL_REPLACED 2u
#define ARENA_REMOVAL_OWNER_DIED 3u
#define ARENA_REMOVAL_OWNER_EXHAUSTED 4u
#define ARENA_WINNER_NONE 0u
#define ARENA_WINNER_TEAM 1u
#define ARENA_WINNER_SLOT 2u
#define ARENA_WINNER_DRAW 3u
/* Events are replaced by EVERY step, in kernel emission order. Read before
 * advancing again. tick is the zero-based input tick just executed. Positions
 * are read after the step; player positions are feet. Unused fields are
 * ARENA_NONE (slots, weapon) or 0. These are presentation events, not proofs.
 *  1 shot: actor, weapon, actor eye.  2 damage: actor attacker, target victim,
 *    value amount.  3 death: target victim, actor killer or none; detail 1
 *    when it exhausted the victim's reserve.  4 respawn: target; weapon and
 *    detail (class) after any loadout change.  5 terminal: always last.
 *  6 guarded: actor attacker, target victim, weapon, value prevented; detail 1
 *    parry or stance negation, 0 guard.  7 healed: actor healer, target,
 *    weapon 17 (lance) or none, value restored.  8 ability: actor, detail
 *    class.  9 marked, 10 riposte: actor, target.
 *  11-14 entity spawned, damaged, repaired, destroyed: target owner,
 *    entity_id, entity_kind and the entity's floor position; actor is the
 *    owner, attacker, repairer or destroying slot (none for other removals);
 *    value the amount; detail the ARENA_REMOVAL cause.
 *  15 hazard damage: target victim, value amount, detail hazard index.
 *  16 captured (detail team) and 17 overtime, at the Control centre.
 *  18 checkpoint: detail index 0-2, value route distance, at the payload.
 *  19 match winner: detail ARENA_WINNER kind, value team or slot (0 for a
 *    draw); always immediately before terminal. */
typedef struct {
    uint32_t tick, kind, actor_slot, target_slot, weapon_id;
    int32_t x, y, z, value;
    uint32_t entity_id, entity_kind, detail;
} ArenaEvent;
typedef struct {
    uint32_t id, owner_slot, weapon_id;
    int32_t x, y, z;
} ArenaProjectileSnapshot;
/* A live ability entity, in ascending id order. Ids start at 1 and are never
 * reused. Position is the floor centre; half_x/half_y are the barricade
 * half-extents, the radius of fire zones and wards, and the body radius of
 * decoys. It is removed when age reaches lifetime. max_health is 0 for kinds
 * that cannot be damaged. */
typedef struct {
    uint32_t id, kind, owner_slot, team;
    int32_t x, y, z;
    uint32_t yaw;
    int32_t health, max_health;
    uint32_t age, lifetime;
    int32_t half_x, half_y, height;
} ArenaEntitySnapshot;
/* Objective state after the last step. Objectives change nothing on tick
 * indices below unlock_tick. Control: progress in -capture..capture, negative
 * favours team 0; owner is a team or ARENA_NONE; team_0/team_1 count living
 * players on the point. Payload: team 0 pushes along the route; attackers and
 * defenders count living players within the push radius; rollback starts when
 * payload_idle reaches payload_rollback_delay. contested applies to the mode's
 * objective. Fields of the other objective are 0 (owner ARENA_NONE). The winner
 * is fixed on the terminal tick: kind ARENA_WINNER, value team or slot. */
typedef struct {
    uint32_t mode, unlock_tick;
    uint32_t score_0, score_1, score_target;
    uint32_t control_owner;
    int32_t control_progress, control_capture;
    uint32_t control_team_0, control_team_1;
    uint32_t contested, overtime;
    int32_t payload_progress, payload_length;
    uint32_t payload_checkpoints, payload_idle, payload_rollback_delay;
    int32_t payload_x, payload_y, payload_z;
    uint32_t payload_attackers, payload_defenders;
    uint32_t winner_kind, winner_value;
} ArenaObjectiveSnapshot;
uint32_t arena_abi_version(void);
ArenaHandle* arena_create(const ArenaConfig*, const ArenaParticipant*, size_t count);
void arena_destroy(ArenaHandle*);
int32_t arena_step(ArenaHandle*, const ArenaInput*, size_t count);
int32_t arena_snapshot(const ArenaHandle*, ArenaSnapshot*);
int32_t arena_player(const ArenaHandle*, uint32_t slot, ArenaPlayerSnapshot*);
int32_t arena_state_hash(const ArenaHandle*, uint8_t* output32, size_t length);
int32_t arena_map_info(uint32_t map_id, ArenaMapInfo*);
int32_t arena_map_wall(uint32_t map_id, uint32_t index, ArenaMapWall*);
int32_t arena_map_route_point(uint32_t map_id, uint32_t index, ArenaMapPoint*);
int32_t arena_map_hazard(uint32_t map_id, uint32_t index, ArenaMapHazard*);
int32_t arena_player_presentation(const ArenaHandle*, uint32_t slot, ArenaPlayerPresentation*);
int32_t arena_weapon_spec(uint32_t weapon_id, ArenaWeaponSpec*);
int32_t arena_event(const ArenaHandle*, uint32_t index, ArenaEvent*);
int32_t arena_projectile_count(const ArenaHandle*, uint32_t*);
int32_t arena_projectile(const ArenaHandle*, uint32_t index, ArenaProjectileSnapshot*);
int32_t arena_entity_count(const ArenaHandle*, uint32_t*);
int32_t arena_entity(const ArenaHandle*, uint32_t index, ArenaEntitySnapshot*);
int32_t arena_objective(const ArenaHandle*, ArenaObjectiveSnapshot*);
#define ARENA_BOT_NOVICE 0u
#define ARENA_BOT_STANDARD 1u
#define ARENA_BOT_VETERAN 2u
#define ARENA_BOT_MASTER 3u
/* Practice bots (crates/arena-bots): not rules and outside the state hash. A bot
 * plans the input for slot on the next arena_step from the current state, as a
 * player at a controller would; pass it to arena_step or replace it. It plans
 * once per tick: repeated calls before the next step return the same input.
 * Its memory lives in the handle. Difficulty tiers differ only by fixed
 * reaction delays, aim-error patterns and answer cadences; every choice is
 * integer and deterministic, never random. Zero-stake handles only (offline 1):
 * a staked handle, a slot out of range or an unknown difficulty returns 1, and
 * a terminal match returns 2. */
int32_t arena_bot_input(ArenaHandle*, uint32_t slot, uint32_t difficulty, ArenaInput* out);
/* Always zero until a reviewed compiled FPS relation is actually qualified. */
uint32_t arena_proof_qualified(void);
#ifdef __cplusplus
}
#endif
#endif
