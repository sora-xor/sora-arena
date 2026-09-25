# SORA Arena combat rules: `sora-arena-first-release-7`

This document specifies the rules owned by the deterministic Rust kernel
(`crates/arena-core`). Unreal practice collects inputs and displays snapshots.
Animation completion and local wall-clock timers cannot refill a magazine,
authorize a shot, change health, or move an objective. The offline campaign
prototype has separate gameplay code and is not proof-qualified.

Every outcome-affecting value below is an exact integer. Distances are
millimetres (X forward, Y right, Z up), angles are 16-bit turns (65536 per full
turn), and times are 60 Hz simulation ticks. There is no randomness and no
platform floating point. A change to any rule or number in this document
changes the rules identity (`RULES_VERSION`) and the canonical state hash.

## 1. Identity and implementation status

- Rules identity: `sora-arena-first-release-7`. It replaces
  `sora-arena-first-release-6` without a compatibility mode. Replays, fixtures
  and journals recorded under an earlier identity are rejected, not converted.
- Native presentation ABI: exactly 3 in this revision. ABI 3's layout, its
  input domain and its exported event kinds 1–5 do not change (see §4.3 and
  §10). ABI 4 will expose the new events, entities, objective state and the
  loadout request.
- Match limits: at most 12 permanent slots, at most 8 in free-for-all and Melee,
  at most 6 per team in Control and Payload, and at most 36,000 ticks (ten
  minutes). Nothing, including overtime, extends a match past its configured
  `max_ticks`.

Every section of this revision is implemented by the kernel. Its numbers are
provisional pending human playtests (§14), so fixtures recorded under this
identity are regression baselines, not balance evidence.

| Section | Status |
| --- | --- |
| §2 phase order; §2.1–§2.7 admission, inputs and their commitment, integer geometry, movement, attacks, projectiles and deaths | Implemented |
| §3 damage: origin, guard-origin fix, parry stagger, modifier order, kill and environmental credit | Implemented |
| §4 events; ABI 3 filtering | Implemented |
| §5 entities, §6 class abilities, §6.7 rocket designation | Implemented |
| §7 arena data, map digest, lane digest and export | Implemented |
| §8 Control, Payload, FFA and Melee results | Implemented |
| §9 environmental hazards | Implemented |
| §10 respawn and loadout selection, including its input encoding and commitment | Implemented in the kernel and the evidence protocol; ABI 3 rejects the loadout bit until ABI 4 |
| §12 state hash | Implemented (`reference-state:v2`) |
| §13 classes, weapon catalog, weapon handling and balance baseline | Implemented; catalog unchanged from first-release-6 except the rocket's name |

## 2. Tick order

`World::step` takes exactly one canonical input per permanent slot (§2.2). An
input outside the canonical bounds, a list of the wrong length, or a step on a
terminal match rejects the whole step, and neither time nor any state advances.
Otherwise one tick runs these phases in this order:

1. **Validate and clear.** Validate every input; clear the event list.
2. **Player phase** (slots ascending).
   - An exhausted player (spectator) is skipped.
   - A dead player applies a loadout request (§10), counts down
     `ability_cooldown` and `respawn_ticks`, and respawns when `respawn_ticks`
     reaches zero (§10).
   - A living player updates yaw and pitch, attack cooldown, reload progress or
     interruption, ability cooldown, spawn protection, stance and mark timers
     (§6.1, §6.3), guard state and stamina, and then moves. A player in stance
     neither guards, jumps nor moves horizontally. Movement collides with
     static walls and live barricades (§5.4) and is clamped to the arena
     bounds.
3. **Assist window.** Damage records older than `ASSIST_TICKS` (300) are
   dropped. A record from tick `t` survives while `tick − t ≤ 300`.
4. **Ability phase** (slots ascending, §6). Every ability resolves before any
   attack is gathered, so an ability's position change, stance, mark or new
   entity has the same effect on this tick's attacks whatever the slot order.
5. **Attack gather** (slots ascending). Reload requests, charge windup, and ray
   attacks resolve against one pre-damage snapshot. Projectiles are launched.
6. **Projectile phase** (list order). Projectiles move, collide and detonate.
7. **Entity phase** (entity id order). Entities age; fire zones pulse; expired
   entities are removed (§5).
8. **Hazard phase** (slots ascending). Hazard pulses (§9).
9. **Healing** (queue order). Heals never revive and never exceed class health.
10. **Player damage batch** (queue order, §3). Samurai ripostes are appended to
    the end of the batch.
11. **Entity damage and repair batch** (queue order). Entities it empties are
    removed after it, in id order (§5.2).
12. **Deaths** (slots ascending): kill credit, bond transfer, entity cleanup.
13. **Objectives** (§8).
14. **Clock and result.** `tick` increments. If a terminal condition holds
    (§8.4), the result is fixed and `MatchWinner` then `Terminal` are emitted.

The damage queue order is fixed: ray and melee hits in gather order, then
blasts in projectile order, then fire-zone pulses in entity id order, then
hazard pulses in slot order, then ripostes. Every ray, blast and pulse reads the
same pre-damage state, so simultaneous kills are possible.

### 2.1 Match configuration and admission

A match is created from a configuration (mode, arena, `max_ticks`, base bond
`B`, offline flag) and an ordered roster of permanent slots. The mode byte is
0 FFA, 1 Control, 2 Payload and 3 Melee. Creation fails, and no match exists,
unless all of these hold:

- the arena id is 0–3 (§7) and `1 ≤ max_ticks ≤ 36,000`;
- there are 1–12 participants, at most 8 in FFA and Melee, and at most 6 per
  team in Control and Payload;
- every participant has class 0–5, team 0 or 1, and a weapon of its class
  (§13.1). In Melee mode that weapon must be melee;
- an offline (practice) match has `B = 0` and every bond 0. A staked match has
  a positive `B` divisible by 10, and every bond is exactly `B`, or `2B` for a
  special weapon without a recognised weapon NFT (§11).

Every mode records each participant's team; only Control and Payload use it.
Each player starts at its first spawn (§10), facing the spawn yaw with pitch 0,
with class health, 100 stamina, a full magazine, every timer and cooldown at 0,
no spawn protection, no charge (`charge_weapon = 255`), not guarding, and
`admitted_special` set to its weapon if that is a special. Each account starts
with `initial = remaining = bond`. The match starts at tick 0 with no
projectiles, entities or damage history, `next_entity_id = 1`, no objective
progress and no winner.

### 2.2 Inputs, encoding and commitment

| Field | Type | Canonical values |
| --- | --- | --- |
| `buttons` | u32 | Any combination of `FIRE` 1, `MELEE` 2, `BLOCK` 4, `JUMP` 8, `ABILITY` 16, `RELOAD` 32 and `LOADOUT` 64; no other bit |
| `move_x` | i16 | −127…127, forward; with `LOADOUT`, the class 0–5 |
| `move_y` | i16 | −127…127, right; with `LOADOUT`, the loadout index 0–2 |
| `yaw` | u16 | Any value; 0 faces +X and 16384 faces +Y |
| `pitch` | i16 | −16,384…16,384; positive looks up |

**Encoding.** An input is exactly eight bytes: `buttons` as u16 little-endian,
`move_x` and `move_y` as one signed byte each, `yaw` as u16 LE and `pitch` as
i16 LE. Slot and tick come from the containing batch. Decoding validates the
result, so every accepted byte string is canonical and
`decode(encode(i)) = i`. A string outside the domain, such as button bit 128
or 256 or a loadout class byte of 6, is rejected, never clamped. A bare
`LOADOUT` request for class `c` and index `k` with yaw `y` and pitch `p`
encodes as the hex bytes `40 00 c k y_lo y_hi p_lo p_hi`.

**Commitment.** Peers commit their inputs before revealing them, in fixed
batches of `BATCH_TICKS = 2` inputs per slot (docs/p2p-recovery.md). A slot's
commitment is SHA-256 over:

1. the evidence context: `"sora-arena:p2p-evidence:v1\0"`, u32 tag length and
   the tag `inputs`, the 32-byte network, session and manifest hashes, u32
   roster count and each 32-byte roster key;
2. epoch u64, the batch's first tick u32, the parent history root, slot u32,
   u32 input count 2, and the two encoded inputs;
3. the 32-byte salt.

Each input is validated before it is committed. A reveal must open its
certified commitment exactly, and the transcript root then chains every
certified commitment set and every revealed input. A loadout request (§10) is
therefore fixed at commitment time exactly like movement and triggers: no peer
can change its selection after seeing the others' commitments, and an
out-of-range request can be neither committed nor decoded from a wire packet
or a durable journal.

### 2.3 Integer geometry

- **Sine.** For a u16 angle `a` (65536 per turn), let `x = a − 32768` and
  `s = −1` if `a > 32768`, else `x = a` and `s = 1`. With
  `q = x × (32768 − x)`,
  `sin_q15(a) = s × 16 × q × 32767 / (5 × 32768² − 4 × q)` in 64-bit integers.
- **Direction.** `direction(yaw, pitch)` is
  `(sin_q15(yaw + 16384) × c / 32767, sin_q15(yaw) × c / 32767, sin_q15(pitch))`
  with `c = sin_q15(pitch + 16384)`; angle sums wrap modulo 65536 and a
  negative pitch is read as its u16 two's complement. Cardinal directions are
  exact, for example `direction(0, 0) = (32767, 0, 0)`.
- **Scaling.** `scale_q15(v, L)` replaces each component `v_i` with
  `v_i × L / 32767`.
- **Boxes** are closed: containment and overlap include the boundary, and
  `expanded(h, v)` grows a box by `h` in x and y and by `v` in z on both sides.
- **Segment tests** return the entry point as a Q20 fraction `t` of the
  segment (0 … 2^20), by the slab method. Start with `near = 0` and
  `far = 2^20`. On an axis along which the segment does not move, the start
  must lie within the box's range. On every other axis, with
  `delta = end − start`, `a = ((min − start) << 20) / delta` and
  `b = ((max − start) << 20) / delta`, set `near = max(near, min(a, b))` and
  `far = min(far, max(a, b))`. The segment misses if `near > far` at any
  point and otherwise hits at `near`, so a segment that starts inside a box
  hits at 0. The nearest of several hits is the smallest `t`.
- **Bodies.** A player at position `p` (the centre of its feet) occupies
  `[p.x − 350, p.x + 350] × [p.y − 350, p.y + 350] × [p.z, p.z + 1700]`. Its
  eye is `p + (0, 0, 1400)` and its blast centre `p + (0, 0, 900)`.

Every division here and below truncates toward zero, and every distance test
compares squared distances in 64-bit integers; a horizontal distance ignores z.

### 2.4 Player phase

A living player's step, in this order:

1. `yaw` and `pitch` take the input's values; `attack_cooldown` decrements
   (saturating at 0).
2. `BLOCK` or `MELEE` pressed: `reload_ticks = 0`, discarding progress.
   Otherwise a running reload decrements, and on reaching 0 refills the
   equipped weapon's magazine.
3. `ability_cooldown` and `spawn_protection` decrement (saturating).
4. A running stance decrements, and on reaching 0 sets
   `attack_cooldown = max(attack_cooldown, 30)` (the whiff, §6.1).
   `marked_ticks` decrements (saturating).
5. **Guard.** `guarding` is true when the player is not in stance, `BLOCK` is
   pressed and `stamina > 0`. `guard_ticks` counts consecutive guarding ticks
   (saturating) and is 0 otherwise. Guarding costs 1 stamina per tick (floor
   0); otherwise stamina regenerates 1 per tick (cap 100).
6. **Jump and gravity.** Not in stance, with `JUMP` pressed and `z = 0`:
   `velocity_z = 180`. Then `velocity_z = max(velocity_z − 8, −500)`.
7. **Walking.** The intent `(mx, my)` is `(0, 0)` in stance and
   `(move_x, move_y)` otherwise. `speed` is the class speed (§13.1), halved by
   integer division while guarding. With `f = direction(yaw, 0)`,
   `r = direction(yaw + 16384, 0)` and `n = max(|mx| + |my|, 127)`:
   `dx = (f.x × mx + r.x × my) × speed / (32767 × n)` and
   `dy = (f.y × mx + r.y × my) × speed / (32767 × n)`. The L1 normalisation
   prevents diagonal speed gain without square roots.
8. **Motion.** The desired point is `old + (dx, dy, velocity_z)`. The x step
   and then the y step are tried separately: the coordinate is clamped to the
   arena bounds shrunk by 350 mm, and the step is taken unless some solid (a
   static wall or live barricade), expanded by 350 mm horizontally and 850 mm
   vertically, contains the candidate point at height `old.z + 850` or
   intersects the segment to it from the current point at that height. Then
   `z = max(desired z, 0)`, and `velocity_z = 0` whenever `z = 0`.

A dead player's step is described in §2 phase 2 and §10.

### 2.5 Attack gather

Every living player, in ascending slot order:

1. In stance: charge is cleared (`charge = 0`, `charge_weapon = 255`) and
   nothing else happens.
2. `RELOAD` without `BLOCK` or `MELEE`, with a firearm (magazine above 0) that
   is not full and not reloading, starts a reload of the weapon's full
   duration.
3. While reloading or guarding: charge is cleared; no attack.
4. Neither `FIRE` nor `MELEE` pressed: charge is cleared; no attack.
5. `attack_cooldown > 0`: no attack; charge is kept.
6. The attack weapon is the class melee weapon `2c` if `MELEE` is pressed, and
   the equipped weapon otherwise. If it differs from `charge_weapon`, charge
   restarts at 0 tagged with it.
7. A firearm with no ammunition starts its reload and clears charge; no
   attack.
8. `stamina` below the weapon's stamina cost: no attack; charge is kept.
9. `charge` below the weapon's charge ticks: `charge` increments; no attack.
10. **Release.** Charge is cleared, the stamina cost is paid, a firearm spends
    one round, `attack_cooldown` becomes the weapon's cooldown, spawn
    protection ends, and `Shot { slot, weapon }` is emitted. The attack starts
    at the eye along `d = direction(yaw, pitch)`.
    - Melee and hitscan: the ray to `eye + scale_q15(d, range)` stops as §5.3
      says. A player stop queues damage of the weapon's amount (kind ray,
      origin the eye, penetrating for weapon 14), except that a Healing lance
      stop on an ally in a team mode queues a heal of 15 instead. An entity
      stop is an entity hit (§5.3, §6.5); a wall stop or no stop does nothing.
    - Projectile: while fewer than 128 projectiles exist, one is appended with
      id `tick × 12 + slot`, the eye as position, velocity
      `scale_q15(d, speed)`, and `traveled = age = 0`. At the limit the shot
      is spent (round, cooldown, `Shot`) and launches nothing.

### 2.6 Projectiles and blasts

Every projectile, in list order and including those launched this tick:

1. `step = min(speed, range − traveled)`. The displacement is
   `velocity × step / speed` per component; `next = position + displacement`,
   `traveled += step` and `age += 1`.
2. The hit fraction `t` is the nearest segment hit (§2.3) against static
   walls, live barricades, decoys that are enemies of the owner, and the body of
   every living player other than the owner, allies and spawn-protected
   players included.
3. It expires when `traveled ≥ range`, `age ≥ 300`, `next.z ≤ 0`, or `next`
   lies outside the closed arena bounds in x or y.
4. On a hit or expiry it stops at `position + (next − position) × t / 2^20`
   per component, with `t = 2^20` when nothing was hit, so an expired
   projectile stops at `next`, even below the floor. `traveled` becomes the
   previous travel plus `step × t / 2^20`. The projectile detonates only if
   `traveled` reaches the weapon's arming distance: every living player
   without spawn protection that is an enemy of the owner, or the owner
   itself, whose blast centre lies within the blast radius of the detonation
   point (3D, closed) with a line of sight to it (§5.3 occlusion), takes a
   blast hit of the weapon's damage with the detonation point as origin, in
   ascending slot order. Enemy entities follow (§5.3). An unarmed stop does
   nothing. Either way the projectile is removed.
5. Otherwise the projectile moves to `next` and stays in the list.

A player's own blast hits them without mark, directional defense or ward, and a
death from it is a suicide (§3.4).

### 2.7 Deaths

The death phase visits slots in ascending order. A player that is alive with
health at or below zero dies:

1. The killer is fixed by §3.4. When there is one, the assists are every
   other enemy of the victim with a damage record against it, on the killer's
   team in team modes; each assist weighs its summed recorded damage.
2. In team modes the killer's teammates share (§11) goes to every other slot on
   the killer's team that was not exhausted before this death phase began.
3. The transfer applies (§11). The victim's `deaths` count increments on every
   death, and the killer's `kills` on a credited one.
4. The victim becomes dead with `respawn_ticks = 480` (8 seconds); charge,
   reload, stance and mark are cleared, and every damage record against the
   victim is removed. Guard state, ammunition and cooldowns stay as they were
   until respawn.
5. `Death { victim, killer, awards }` is emitted, followed by the entity
   cleanup of §5.2. `awards` lists each nonzero transfer by ascending slot.

## 3. Damage

### 3.1 Pending damage

Each hit is queued as pending damage with:

- `source`: a player slot, or a hazard index for environmental damage;
- `victim`: a player slot;
- `amount`: the weapon, ability or hazard damage;
- `weapon`: the weapon id (255 for fire zones and hazards);
- `origin`: the point the hit came from, used only by directional defense
  (none for fire zones and hazards);
- `kind`: ray (melee or hitscan), blast, zone, hazard or riposte;
- `penetrating`: true only for a charged Plasma matchlock (weapon 14) direct
  hitscan hit.

### 3.2 Damage origin and directional defense

Guard, parry and the Samurai stance are directional. They test where the damage
came from, not where the attacking player stands:

| Damage kind | Origin |
| --- | --- |
| Melee and hitscan rays | The attacker's eye point when the ray was gathered |
| Blasts (grenade, rocket, shock) | The projectile's detonation point |
| Samurai riposte | The Samurai's eye point |
| Fire zones and hazards | None: not directional, never guarded |

A hit is **frontal** when `facing.x·dx + facing.y·dy > 0`, where
`facing = direction(victim.yaw, 0)` and `(dx, dy)` is the horizontal offset
from the victim's position to the origin. A zero offset (a detonation directly
above or inside the victim) is not frontal.

**Guard-origin fix.** Up to first-release-6, blast guarding used the attacker's
position, so a grenade that exploded behind a guarding player was blocked if its
thrower stood in front, and a grenade that exploded in front was not blocked if
its thrower stood behind. Rules 7 use the detonation point. Rays are unchanged
in practice, because the attacker's position does not change between gather and
resolution within a tick.

Directional defense applies to frontal hits from another player (never
self-damage) that are not penetrating:

1. **Samurai stance** (§6.1) negates a frontal ray hit completely.
2. **Parry.** While guarding with `guard_ticks ≤ 8` (the first eight held
   ticks) and `stamina ≥ 20`: amount 0, stamina −20.
3. **Guard.** Otherwise, while guarding with `stamina ≥ 10`: amount
   `(amount + 1) / 2`, stamina −10.
4. With less than 10 stamina a guard has no effect.

Each application of stance, parry or guard emits `Guarded`, with
`prevented = amount before − amount after`.

**Parry stagger.** A parry (rule 2, not the stance) of a melee ray hit adds 30
ticks to the attacker's `attack_cooldown` (saturating). Every parry by a
Samurai, whatever the parried weapon, also reduces the Samurai's own
`ability_cooldown` by 120 ticks (saturating at zero).

### 3.3 Modifier order

Each pending damage entry resolves in this order:

1. If the victim's health is already zero this tick, skip it.
2. **Mark:** if the victim is marked (§6.3) and the source is a player enemy of
   the victim, `amount += amount / 4`.
3. **Directional defense** (§3.2).
4. **Ward:** if the victim stands inside a live ward that protects them (§6.6)
   and the source is not the victim, `amount −= amount × 35 / 100`.
5. `dealt = min(amount, health)`; health decreases by `dealt`.
6. If `dealt > 0`, emit `Damage` (player source) or `EnvironmentalDamage`
   (hazard). Player damage by another player is recorded for assists.
7. If health reaches zero, fix the kill credit (§3.4).

Integer division truncates toward zero; every amount here is nonnegative.

### 3.4 Kill credit, assists and environmental credit

- **Suicide:** a player-sourced hit where source equals victim credits no one.
  This holds even if an enemy dealt qualifying damage earlier.
- **Enemy kill:** a hit from an enemy credits that enemy.
- **Environmental death:** a hazard death credits the most recent enemy damage
  record for that victim still inside the assist window. With no such record,
  no one is credited. This is the rule that §9 hazards make reachable.
- **Assists:** every other enemy of the victim, on the credited killer's team
  in team modes, with a surviving damage record against the victim.
  The assist weight is the recorded damage.
- A death with no credited killer moves no value: an unassisted environmental
  death or a suicide pays nothing (§11).

## 4. Events

Events are replaced on every step and describe only the tick just executed.
They are presentation data, not proofs. The kernel records all kinds below;
`world.events` keeps them in emission order.

### 4.1 Event kinds

| Event | Fields | Emitted when | ABI 3 kind |
| --- | --- | --- | --- |
| `Shot` | slot, weapon | An attack is released | 1 |
| `Damage` | attacker, victim, amount | A player loses health to a player source | 2 |
| `Death` | victim, killer, awards | A player dies (§3.4, §11) | 3 |
| `Respawn` | slot | A dead player respawns | 4 |
| `Terminal` | — | The match ends; always the last event | 5 |
| `Guarded` | attacker, victim, weapon, parried, prevented | Stance, parry or guard applies (§3.2) | internal |
| `Healed` | healer, target, amount, weapon | Health is restored; `amount > 0`; weapon 17 for the lance, none for an ability | internal |
| `AbilityUsed` | slot, class | An ability activates and its cooldown starts (§6) | internal |
| `Marked` | marker, target | A Teppō mark lands (§6.3) | internal |
| `Riposte` | slot, target | A Samurai riposte is queued (§6.1) | internal |
| `EntitySpawned` | id, kind, owner | An entity is created (§5) | internal |
| `EntityDamaged` | id, attacker, amount | A decoy or barricade loses health | internal |
| `EntityRepaired` | id, repairer, amount | A barricade is repaired; `amount > 0` | internal |
| `EntityDestroyed` | id, kind, owner, cause | An entity is removed; cause from §5.2 | internal |
| `EnvironmentalDamage` | victim, hazard, amount | A hazard deals damage (§9) | internal |
| `ObjectiveCaptured` | team | Control ownership changes (§8.1) | internal |
| `OvertimeStarted` | — | Control overtime begins (§8.1) | internal |
| `CheckpointReached` | index | The payload passes a checkpoint (§8.2) | internal |
| `MatchWinner` | winner | Immediately before `Terminal` (§8.4) | internal |

Objective progress is continuous state, not an event: it is read from the
snapshot every tick. `EnvironmentalDamage.hazard` indexes the arena's hazard
list (§7), `CheckpointReached.index` is 0, 1 or 2, and `MatchWinner.winner` is
`Team(t)`, `Slot(s)` or `Draw` (§8.4).

### 4.2 Guard and heal details

`Guarded` is emitted during the damage batch, before any `Damage` event for the
same hit. A parry prevents the whole amount, so no `Damage` follows it. A
halved hit of one point prevents nothing, but still emits `Guarded` because
guard stamina was spent.

`Healed` reports the health actually restored. A lance shot absorbed by a
full-health ally, or a Kusushi pulse on a full-health player, emits no `Healed`.
Healing never revives the dead.

### 4.3 ABI 3 export

ABI 3 exports exactly event kinds 1–5 with their first-release-6 meaning.
`arena_snapshot.event_count` counts only exported events, and `arena_event`
indexes only exported events, in their original relative order. Internal events
are skipped: they do not appear, do not shift the index of exported events, and
do not change the event stream an ABI 3 caller observes. ABI 4 will add new kind
numbers for the internal events and expose them. It will be a new layout that
callers must require exactly, with no ABI 3 compatibility mode.

## 5. Entities

### 5.1 The entity list

`World.entities` holds the live ability entities in ascending id order.
`World.next_entity_id` starts at 1 and increments with every spawn; ids are
never reused. Spawns happen in the ability phase in slot order, so ids are
deterministic. Each entity records:

| Field | Meaning |
| --- | --- |
| `id` | u32, unique within the match |
| `kind` | 1 decoy, 2 barricade, 3 fire zone, 4 ward |
| `owner`, `team` | The owning slot and its team at spawn time |
| `position` | Floor-level centre: x and y from the ability, z = 0 |
| `yaw` | Facing at spawn |
| `health` | Current health; 0 for kinds that cannot be damaged |
| `age` | Entity-phase ticks since spawn |
| `half_x`, `half_y` | Barricade half-extents; radius for zones and wards; 350 for decoys |

Decoys spawn with 60 health and barricades with 250; fire zones and wards have
0 and cannot be damaged. The entity list, every field of every entity, and
`next_entity_id` are part of the canonical state hash (§12). Each owner has at
most one live entity of each kind; a new spawn of the same kind first destroys
the old one with cause `Replaced`. A player who changes class at respawn keeps
entities of the old class, so an owner can hold one entity of each of the four
kinds and the list holds at most 48 entities (`MAX_ENTITIES`).

An entity is an **enemy** of a player when, in team modes, its team differs
from the player's, and in FFA and Melee, when another player owns it.

### 5.2 Lifetime and removal

In the entity phase each entity, in id order, increases its `age` by one, then
pulses if it is a fire zone due to pulse (§6.4), and is then removed if `age`
has reached its lifetime (decoy 300, fire zone 300, ward 300, barricade 1800).
An entity with lifetime L spawned at tick T is therefore present for the rays,
projectiles and blasts of ticks T … T + L − 1, and in the damage batches of
ticks T … T + L − 2: the entity phase of tick T + L − 1 removes it.

An entity is removed with `EntityDestroyed` and one of these causes:

- `Expired`: `age` reaches its lifetime;
- `Destroyed(by)`: its health reaches zero in the entity damage batch; `by` is
  the slot of the hit that emptied it. Entities emptied by a batch are removed
  after the whole batch, in id order. Later entries for an emptied or removed
  entity are skipped, so a repair cannot restore it;
- `Replaced`: its owner spawned another entity of the same kind; emitted just
  before the new entity's `EntitySpawned`;
- `OwnerDied`: when its owner dies, the owner's decoy is removed right after the
  owner's `Death` event;
- `OwnerExhausted`: when a death exhausts the owner's reserve and they become a
  spectator, every entity of that owner is removed instead, in id order, right
  after the `Death` event.

Barricades, fire zones and wards outlive their owner's death. Entities never
change team. A match is a single round: the tick that makes it terminal leaves
the entities in the final state, and no step follows, so there is no separate
round-end cleanup.

### 5.3 Targeting rules

- **Rays** (melee, hitscan, the Healing lance, the Teppō mark) stop at the
  nearest of: a static wall, any live barricade, an enemy decoy, or a valid
  player target. Valid player targets are living enemies without spawn
  protection and, for the Healing lance in team modes, living allies. Melee
  rays test player bodies and decoys expanded by 180 mm horizontally; walls and
  barricades are never expanded. Ties go to walls, then lower entity ids, then
  lower slots. Allied decoys do not stop rays.
- An enemy ray that stops on a decoy or barricade deals its weapon damage to
  that entity (§6.2, §6.5). An allied ray stops on a barricade harmlessly,
  except for the forge-hammer repair. The Teppō mark deals no damage.
- **Projectiles** detonate on the nearest static wall, live barricade, decoy
  that is an enemy of the projectile's owner, or living player other than the
  owner along their step. Only an armed detonation blasts; a projectile deals no
  separate impact damage to an entity.
- **Blasts** damage an enemy decoy whose centre (position + 900 mm z) is within
  the blast radius, and an enemy barricade whose centre (position + 1000 mm z)
  is within the blast radius, in id order. The path from the detonation point
  to that centre must not be blocked by a static wall or another barricade (the
  target barricade itself is ignored). A decoy never occludes a blast.
- **Occlusion:** from rules 7, the blast line-of-sight test (`blocked`) treats
  live barricades as walls, including the same closed-face rule.
- Fire zones and hazards damage players only. Allies' attacks never damage an
  allied entity, and a player's own blast never damages its own entities.

### 5.4 Barricade collision

A live barricade is a dynamic AABB. It blocks movement for every player on
either team exactly like a static wall, and it blocks rays, projectiles and
blast line of sight for everyone. A barricade takes effect as soon as the
ability phase that creates it ends: it stops that tick's rays, projectiles and
blasts, and it blocks movement from the next tick's player phase.

Abilities resolve in slot order, and each sees the entities that lower slots
spawned earlier in the same ability phase. A barricade placed by a lower slot
therefore already blocks a higher slot's Shinobi dash, Teppō mark, fire-pot
throw and barricade placement in that phase.

## 6. Class abilities

The ability button is input bit 16. An ability activates when its owner is alive
and not exhausted, `ability_cooldown == 0`, and the class precondition holds.
Only the Karakuri has a precondition (§6.5). Activation sets the class
cooldown, ends spawn protection and emits `AbilityUsed`, followed by the
ability's own events in the order it produces them. A failed precondition
changes nothing: no cooldown and no event. Cooldowns keep counting through
death and respawn.

| Class | Ability | Cooldown (ticks) | Summary |
| --- | --- | ---: | --- |
| 0 Samurai | Kage-no-kamae counter stance | 480 | 24-tick frontal stance that negates melee and hitscan and ripostes once for 90 |
| 1 Shinobi | Utsusemi decoy | 600 | Leaves a 60-HP decoy, dashes 2000 mm forward |
| 2 Teppō | Mato-ire marking shot | 720 | 45 m ray; marked enemy takes +25% player damage for 300 ticks |
| 3 Hanabi | Kaen-tsubo fire pot | 720 | 2500 mm floor zone; after 30 ticks, 8 damage every 20 ticks until tick 300 |
| 4 Karakuri | Karakuri-tate barricade | 720 | 250-HP, 2000 mm-high dynamic cover for 1800 ticks; repaired by the forge hammer |
| 5 Kusushi | Yakuen ward | 900 | Heals 35 within 6000 mm, then a 4000 mm ward for 300 ticks: −35% damage |

All numbers are provisional sidegrade tuning pending human playtests. None is
multiplied by NFT rarity.

### 6.1 Samurai: Kage-no-kamae (counter stance)

- Activation sets `stance_ticks = 24`, ends guarding (`guarding = false`,
  `guard_ticks = 0`) and clears charge and reload progress. The player phase
  counts `stance_ticks` down, so the stance is active in the damage batches of
  the activation tick and the next 23 ticks.
- While in stance, the Samurai cannot move horizontally, jump, guard, attack or
  reload. Attack and reload requests are ignored, and charge and reload progress
  are cleared. Gravity and stamina regeneration continue.
- A frontal ray hit (melee or hitscan) from an enemy that is not penetrating is
  negated completely, with no stamina cost, and emits
  `Guarded { parried: true }`. Blasts, fire zones, hazards, ripostes and
  Plasma direct hits are not negated.
- The first negated hit of a stance queues one **riposte** if the attacker is
  still alive (health above zero at that point of the batch), the horizontal
  distance between the two eye points is at most 3000 mm, and the segment
  between them is not blocked by walls or barricades. Only the first negated
  hit can riposte: if it fails these conditions, no later hit in the batch
  ripostes instead. The riposte is 90 damage with weapon 0, kind riposte,
  origin at the Samurai's eye. It is appended to the end of the current damage
  batch, and `Riposte` is emitted. It passes through the normal modifier order
  (§3.3).
- A stance that negated a hit ends at the end of that damage batch
  (`stance_ticks = 0`), and every frontal ray hit in that same batch is also
  negated. A stance whose countdown reaches zero in the player phase negated
  nothing: it is a whiff, and `attack_cooldown = max(attack_cooldown, 30)`,
  set after that tick's attack-cooldown decrement. Death ends a stance without
  a whiff.

### 6.2 Shinobi: Utsusemi (decoy)

- Precondition: none. The decoy spawns on the floor at the Shinobi's x and y
  before the dash, with the Shinobi's yaw, 60 health, and a 300-tick
  lifetime.
- The Shinobi then dashes 2000 mm along `direction(yaw, 0)` using the normal
  collision-safe motion, as in first-release-6.
- The decoy's body is a player-sized AABB (350 mm radius, 1700 mm height). It is
  stationary and does not collide with movement. It intercepts enemy rays and
  projectiles; enemy rays that stop on it deal their weapon damage to it, and
  enemy blasts deal their blast damage (§5.3). Its damage never enters the
  assist history. It is removed when its owner dies (§5.2).

### 6.3 Teppō: Mato-ire (marking shot)

- The Teppō casts a ray from its eye along `direction(yaw, pitch)` for
  45,000 mm, with the §5.3 ray rules and the hitscan player targets: living
  enemies without spawn protection stop it, and allies and spawn-protected
  enemies do not.
- If the nearest stop is an enemy player, that player becomes marked:
  `marked_ticks = 300`, refreshed if already marked, and `Marked` is emitted.
  The ability is used even if the ray stops on a wall, barricade or decoy, or
  on nothing.
- Marked players take `amount + amount / 4` from every player enemy source,
  starting with the activation tick's damage batch (§3.3). The player phase
  counts `marked_ticks` down, so the mark covers the damage batches of the
  activation tick and the next 299 ticks. The mark does not count as damage or
  as an assist. Death and respawn clear it.

### 6.4 Hanabi: Kaen-tsubo (fire pot)

**Placement.** Let `eye = position + (0, 0, 1400)` and
`end = eye + scale_q15(direction(yaw, pitch), 9000)`.

- `t_wall` is the smallest Q20 intersection of the segment with static walls and
  live barricades, if any.
- `t_floor = (eye.z << 20) / (eye.z − end.z)` when `end.z < 0`; otherwise none.
- If the wall comes first (`t_wall ≤ t_floor`, or there is no floor hit),
  `t = max(0, t_wall − 46603)`. This pulls the centre back about 400 mm from
  the wall face. If the floor comes first, `t = t_floor`. With neither,
  `t = 1 << 20`.
- The centre is `eye + (end − eye) × t / 2^20`, truncating each component
  toward zero, with `z = 0`.

**Zone.** The zone has radius 2500 mm and a lifetime of 300 ticks. It pulses at
ages 30, 50, 70, … 290, for at most 14 pulses. Each pulse queues 8 damage
(kind zone, weapon 255, no origin) for every living enemy player of the owner
that meets all of these:

- no spawn protection;
- horizontal distance to the centre at most 2500 mm;
- feet `z ≤ 1000`;
- the segment from `centre + (0, 0, 300)` to `position + (0, 0, 300)` is not
  blocked by walls or barricades.

Zones never damage the owner, allies or entities. Zone damage is ordinary
player damage for kill credit and assists.

### 6.5 Karakuri: Karakuri-tate (barricade) and repair

**Placement.** Let `f = direction(yaw, 0)` and
`c = position + scale_q15(f, 1500)`, taking x and y only. If
`|f.x| ≥ |f.y|`, the half-extents are `(200, 1200)`; otherwise `(1200, 200)`.
The box is `[c.x − hx, c.x + hx] × [c.y − hy, c.y + hy] × [0, 2000]`. Its
2000 mm height is above the 1936 mm apex of a jump, so no player can jump over
a barricade or land inside one. Placement is valid only if all of these hold
(overlap is a closed test: boxes that only touch overlap):

- both of its floor corners lie inside the closed arena bounds;
- it does not overlap any static wall, live barricade, or living player's
  body;
- it does not overlap any of the arena's 24 team and FFA spawn bodies
  expanded by 500 mm horizontally;
- it does not overlap any of the arena's hazard volumes;
- the segment from `position + (0, 0, 800)` to `c + (0, 0, 800)` is not blocked
  by walls or barricades, so a barricade cannot be placed through a wall.

The owner's own live barricade, which a valid placement replaces, is ignored by
the overlap and path tests, so a Karakuri can redeploy in place. An invalid
placement is a failed precondition. A valid one spawns a barricade with 250
health and an 1800-tick lifetime, replacing the owner's previous one.

**Damage and repair.**

- Enemy rays that stop on a barricade deal their weapon damage to it. Enemy
  blasts deal their blast damage (§5.3).
- Allied rays stop on it harmlessly, with one exception: a Karakuri forge hammer
  strike (weapon 8, melee) that stops on a barricade that is not its enemy (its
  own, or an ally's in team modes) repairs it by `min(45, 250 − health)` and
  emits `EntityRepaired` when that is positive. Repairs resolve in the entity
  batch, in queue order with the damage entries. That strike consumes its
  normal stamina and cooldown.

### 6.6 Kusushi: Yakuen (heal and ward)

- **Heal:** the Kusushi and, in team modes, every living ally within 6000 mm
  (3D distance) gain 35 health, up to their class maximum. This is the
  first-release-6 heal, applied immediately in the ability phase. Each non-zero
  heal emits `Healed` with no weapon, in slot order.
- **Ward:** a ward entity then spawns on the floor at the Kusushi's x and y
  with radius 4000 mm and a lifetime of 300 ticks. Damage to a protected player
  inside it (horizontal distance ≤ 4000 mm) is reduced by `amount × 35 / 100`
  (§3.3), unless the player inflicted it on themselves. Protected players are the
  owner's team in team modes and only the owner in FFA and Melee. Wards do not
  stack.

### 6.7 Hanabi rockets

The plan gives Hanabi "grenades, rockets, and area denial". First-release-7
keeps the arsenal at 12 standard weapons (ids 0–11) and 6 special sidegrades
(ids 12–17), and assigns the roles like this:

- **Grenades:** the Grenade launcher (7, standard).
- **Rockets:** special weapon 15 is the **Bō-hiya rocket** (棒火矢, an Edo-period
  rocket arrow), renamed from "Micro-mortar". Kernel projectiles already fly in
  straight lines at constant velocity with no gravity, so the weapon's
  simulation is unchanged: 85 blast damage, 420 mm per tick, 3400 mm blast
  radius, 4500 mm arming distance, a 15-tick ignition windup, a 3-round
  magazine and a 168-tick reload. It is the plan's "explosive coverage versus
  arming distance" sidegrade.
- **Area denial:** the Kaen-tsubo ability (§6.4).

The rename changes only the catalog name. The Unreal catalog display name
belongs to the Unreal lane.

## 7. Arenas

### 7.1 Data model and identity

Each of the four arenas is versioned integer data (`arena-map-v1`):

- **Bounds:** the playable rectangle. Movement clamps player centres to the
  bounds shrunk by the 350 mm radius. A projectile whose next position lies
  outside the closed bounds rectangle in x or y expires there, like one that
  reaches the floor.
- **Walls:** static AABBs, each at least 2000 mm high (§7.2). The first four
  are the perimeter, each 1000 mm thick outside the bounds. They are followed by
  interior pieces in point-mirror pairs. This order is canonical: it is the
  ABI 3 `arena_map_wall` index order and part of the map digest.
- **Spawns:** six per team and twelve FFA, each `(x, y, yaw)`.
- **Control point:** centre and radius.
- **Payload route:** axis-aligned waypoints and three checkpoint distances.
- **Hazards:** floor volumes with a kind, damage and pulse period.
- **Lanes:** `north`, `mid` and `south` guidance polylines for bots and
  presentation. They are not rules data.

The **map digest** is SHA-256 over this little-endian encoding:

1. `"sora-arena:arena-map:v1\0"`;
2. u8 arena id;
3. i32 bounds `min_x, min_y, max_x, max_y`;
4. u32 wall count, then each wall as six i32 (`min x, y, z, max x, y, z`);
5. the six team 0 spawns, then the six team 1 spawns, then u32 FFA count and
   the FFA spawns, each as i32 x, i32 y, u16 yaw;
6. the control point as i32 x, y, radius;
7. u32 route point count, then each point as i32 x, y;
8. three u32 checkpoints;
9. u32 hazard count, then each hazard as u8 kind (1 fire, 2 slag, 3 shredder),
   six i32 volume, i32 damage, u16 period.

The digest of the configured arena replaces the first-release-6 wall list in the
state hash. Lanes have a separate digest that is not part of the state hash, so
editing bot guidance cannot change a match outcome: SHA-256 over
`"sora-arena:arena-lanes:v1\0"`, u8 arena id, u32 lane count, then each lane in
`north`, `south`, `mid` order as u32 name length, the name bytes, u32 point
count and each point as i32 x, y. ABI 3 serves the new bounds and
walls through the existing `arena_map_info` and `arena_map_wall` without a
layout change. Its consumers accept at most 64 walls, and every arena here has
at most 42.

Each `arena-data` block below has one record per line, and `#` starts a
comment. The records are:

- `arena <id> <slug>`;
- `bounds <min_x> <min_y> <max_x> <max_y>`;
- `wall <min_x> <min_y> <min_z> <max_x> <max_y> <max_z>`, in canonical order;
- `spawn team0|team1|ffa <x> <y> <yaw>`, in canonical order within each set;
- `control <x> <y> <radius>`;
- `route <x> <y>`, in path order;
- `checkpoints <d1> <d2> <d3>`, as distances along the route;
- `hazard <kind> <min_x> <min_y> <min_z> <max_x> <max_y> <max_z> <damage> <period>`;
- `lane <name> <x>,<y> ...`.

The blocks are machine-readable on purpose. The implementation test parses
them and compares them with the kernel's tables, so the document and the kernel
cannot drift apart.

### 7.2 Invariants

The data below was generated and checked by an authoring validator. The
implementation must reproduce the data exactly and check the same invariants in
a Rust test:

1. The bounds lie inside ±24,000 and are point-symmetric about the origin. The
   interior walls lie inside the bounds, and every wall has positive extent,
   `min.z = 0` and `max.z ≥ 2000`.
2. The interior wall set and the hazard set are closed under the point mirror
   `(x, y) → (−x, −y)`. Team 1 spawns mirror team 0 spawns, with yaw turned
   32768. FFA spawns come in mirrored pairs, `ffa[2k+1] = mirror(ffa[2k])`.
3. Each arena has at least 24 interior walls and at most 64 walls in total.
4. Every spawn body expanded by 150 mm is clear of every wall. Every spawn
   position lies on or outside each hazard rectangle grown by 3000 mm on every
   side. FFA spawns are at least 6000 mm apart.
5. The control point is at the origin. A player body at its centre expanded by
   1000 mm is clear of every wall, no hazard overlaps the square around its
   radius, and every team spawn is at least radius + 8000 mm away.
6. The payload route is axis-aligned, with no zero-length or collinear
   segments. It starts within 3000 mm ahead of team 0's spawns and ends within
   3000 mm ahead of team 1's. Every segment's corridor, 600 mm either side of
   the route line and a player's height, is clear of every wall and lies inside
   the bounds. The route never crosses a wall; it may cross a hazard (Silk
   Foundry's slag channel). The three checkpoints strictly increase and are
   less than the route length.
7. Every hazard is a floor volume with top `z ≤ 1000` that overlaps no wall,
   with `1 ≤ damage ≤ 40` and `6 ≤ period ≤ 60`.
8. Lane corridors (450 mm half-width) are clear of walls and hazards. Each lane
   runs from team 0's base to team 1's base, and `south` mirrors `north`.
9. On a 100 mm grid of positions where a player body fits, every spawn, the
   control centre, every route waypoint and every lane point is reachable from
   team 0's first spawn.

Point symmetry makes Control and FFA positionally fair. Payload is asymmetric
by design: team 0 attacks.

**Wall height.** A jump peaks 1936 mm above the floor (take-off velocity 180,
gravity 8 per tick: 172 + 164 + … + 4). Movement has no vertical collision: a
horizontal step is blocked while the feet are at or below a wall's top, and a
fall never tests walls. Every wall is therefore at least 2000 mm high, like a
barricade (§6.5), so no jump clears a wall and no player can land inside one.
The authoring draft had hedges, veranda screens, toro lanterns, stalls, carts,
barrels, rocks, planters, crates, moulds, rails, terminals and presses at
1600–1800 mm; first-release-7 raises each of them to 2000 mm. All of them stay
above the 1400 mm eye height, as they were, so they still block standing shots.

### 7.3 Nyaagyu Estate (arena 0)

A walled samurai estate. Gatehouses with three doorways guard each base. Dojo
halls frame a central courtyard with stone lanterns. Kura storehouses flank the
middle approach, and hedges and pine planters line the side corridors. Burning
storehouse embers (fire) make the northern and southern corridors dangerous
chokepoints. The payload leaves team 0's gate, swings through the south
courtyard past the veranda screens, and ends at team 1's gate.

```arena-data
arena 0 nyaagyu-estate
bounds -22000 -16000 22000 16000
wall -23000 -17000 0 23000 -16000 6000  # perimeter south
wall -23000 16000 0 23000 17000 6000  # perimeter north
wall -23000 -16000 0 -22000 16000 6000  # perimeter west
wall 22000 -16000 0 23000 16000 6000  # perimeter east
wall 14500 -16000 0 15500 -9500 4500  # east gatehouse south wing
wall -15500 9500 0 -14500 16000 4500  # mirror of east gatehouse south wing
wall 14500 -6000 0 15500 -1800 4500  # east gatehouse inner south
wall -15500 1800 0 -14500 6000 4500  # mirror of east gatehouse inner south
wall 14500 1800 0 15500 6000 4500  # east gatehouse inner north
wall -15500 -6000 0 -14500 -1800 4500  # mirror of east gatehouse inner north
wall 14500 9500 0 15500 16000 4500  # east gatehouse north wing
wall -15500 -16000 0 -14500 -9500 4500  # mirror of east gatehouse north wing
wall -7000 8500 0 7000 12500 5500  # north dojo hall
wall -7000 -12500 0 7000 -8500 5500  # mirror of north dojo hall
wall 3000 7000 0 5000 7600 2000  # north veranda screen east
wall -5000 -7600 0 -3000 -7000 2000  # mirror of north veranda screen east
wall -5000 7000 0 -3000 7600 2000  # north veranda screen west
wall 3000 -7600 0 5000 -7000 2000  # mirror of north veranda screen west
wall 2600 2200 0 3200 2800 2000  # toro north-east
wall -3200 -2800 0 -2600 -2200 2000  # mirror of toro north-east
wall 2600 -2800 0 3200 -2200 2000  # toro south-east
wall -3200 2200 0 -2600 2800 2000  # mirror of toro south-east
wall 9500 3000 0 12500 6500 5000  # east kura north
wall -12500 -6500 0 -9500 -3000 5000  # mirror of east kura north
wall 9500 -6500 0 12500 -3000 5000  # east kura south
wall -12500 3000 0 -9500 6500 5000  # mirror of east kura south
wall 9000 1000 0 10200 2200 2000  # east garden rock
wall -10200 -2200 0 -9000 -1000 2000  # mirror of east garden rock
wall 8000 9000 0 8600 13500 2000  # east hedge north
wall -8600 -13500 0 -8000 -9000 2000  # mirror of east hedge north
wall 5000 -4500 0 6500 -3900 2000  # courtyard wall south-east
wall -6500 3900 0 -5000 4500 2000  # mirror of courtyard wall south-east
wall 9500 -14500 0 11000 -13000 2400  # well house
wall -11000 13000 0 -9500 14500 2400  # mirror of well house
wall 12000 8500 0 13200 9700 2000  # pine planter north
wall -13200 -9700 0 -12000 -8500 2000  # mirror of pine planter north
wall 12000 -11500 0 13200 -10300 2000  # pine planter south
wall -13200 10300 0 -12000 11500 2000  # mirror of pine planter south
spawn team0 -19500 -5000 0
spawn team0 -19500 -3000 0
spawn team0 -19500 -1000 0
spawn team0 -19500 1000 0
spawn team0 -19500 3000 0
spawn team0 -19500 5000 0
spawn team1 19500 5000 32768
spawn team1 19500 3000 32768
spawn team1 19500 1000 32768
spawn team1 19500 -1000 32768
spawn team1 19500 -3000 32768
spawn team1 19500 -5000 32768
spawn ffa -18500 -12500 8192
spawn ffa 18500 12500 40960
spawn ffa -18500 12500 57344
spawn ffa 18500 -12500 24576
spawn ffa 0 14500 49152
spawn ffa 0 -14500 16384
spawn ffa -10500 0 0
spawn ffa 10500 0 32768
spawn ffa -4000 -5500 8192
spawn ffa 4000 5500 40960
spawn ffa -11000 -13500 8192
spawn ffa 11000 13500 40960
control 0 0 4000
route -18500 0
route -8000 0
route -8000 -5500
route 8000 -5500
route 8000 0
route 18500 0
checkpoints 16000 32000 40000  # route length 48000
hazard fire 3000 13500 0 5000 15500 600 10 15  # burning storehouse embers
hazard fire -5000 -15500 0 -3000 -13500 600 10 15  # mirror of burning storehouse embers
lane north -18500,3000 -16500,3000 -16500,7750 -7500,7750 -7500,13000 7500,13000 7500,7750 16500,7750 16500,3000 18500,3000
lane south -18500,-3000 -16500,-3000 -16500,-7750 -7500,-7750 -7500,-13000 7500,-13000 7500,-7750 16500,-7750 16500,-3000 18500,-3000
lane mid -18500,0 18500,0
```

### 7.4 Lantern Ward (arena 1)

A lantern-lit merchant street. Three east–west streets (north, main, south) are
separated by rows of machiya townhouses, with narrow alleys between them, and
teahouses and warehouses along the outer edge. Carts, stalls and lantern posts
provide cover. Spilled lantern oil (fire) burns in the north street and, by
mirror, the south street. The payload climbs an alley into the north street,
runs past the lantern tower, and drops back to the main street.

```arena-data
arena 1 lantern-ward
bounds -23000 -14000 23000 14000
wall -24000 -15000 0 24000 -14000 7000  # perimeter south
wall -24000 14000 0 24000 15000 7000  # perimeter north
wall -24000 -14000 0 -23000 14000 7000  # perimeter west
wall 23000 -14000 0 24000 14000 7000  # perimeter east
wall 2000 2500 0 6000 6500 5000  # north row machiya A
wall -6000 -6500 0 -2000 -2500 5000  # mirror of north row machiya A
wall 8000 2500 0 12000 6500 5500  # north row machiya B
wall -12000 -6500 0 -8000 -2500 5500  # mirror of north row machiya B
wall 14000 2500 0 17500 6500 5000  # north row machiya C
wall -17500 -6500 0 -14000 -2500 5000  # mirror of north row machiya C
wall 1000 -6500 0 5000 -2500 5000  # south row machiya A
wall -5000 2500 0 -1000 6500 5000  # mirror of south row machiya A
wall 7000 -6500 0 11000 -2500 5500  # south row machiya B
wall -11000 2500 0 -7000 6500 5500  # mirror of south row machiya B
wall 13000 -6500 0 16500 -2500 5000  # south row machiya C
wall -16500 2500 0 -13000 6500 5000  # mirror of south row machiya C
wall 1000 10500 0 6500 14000 6000  # outer north teahouse
wall -6500 -14000 0 -1000 -10500 6000  # mirror of outer north teahouse
wall 9500 10500 0 15000 14000 6000  # outer north warehouse
wall -15000 -14000 0 -9500 -10500 6000  # mirror of outer north warehouse
wall 3500 -14000 0 8500 -10500 6000  # outer south bathhouse
wall -8500 10500 0 -3500 14000 6000  # mirror of outer south bathhouse
wall 11500 -14000 0 17000 -10500 6000  # outer south merchant house
wall -17000 10500 0 -11500 14000 6000  # mirror of outer south merchant house
wall -400 6600 0 400 7400 2200  # north street lantern tower
wall -400 -7400 0 400 -6600 2200  # mirror of north street lantern tower
wall 4000 6600 0 5200 7400 2000  # north street cart
wall -5200 -7400 0 -4000 -6600 2000  # mirror of north street cart
wall 13000 6600 0 14200 7400 2000  # north street barrels
wall -14200 -7400 0 -13000 -6600 2000  # mirror of north street barrels
wall 9800 1500 0 10600 2300 2200  # main street lantern post
wall -10600 -2300 0 -9800 -1500 2200  # mirror of main street lantern post
wall 2500 800 0 3700 1600 2000  # main street stall
wall -3700 -1600 0 -2500 -800 2000  # mirror of main street stall
wall 11500 -1600 0 12700 -800 2000  # main street cart
wall -12700 800 0 -11500 1600 2000  # mirror of main street cart
wall 19000 7000 0 20000 11000 3500  # east yard fence north
wall -20000 -11000 0 -19000 -7000 3500  # mirror of east yard fence north
wall 19000 -11000 0 20000 -7000 3500  # east yard fence south
wall -20000 7000 0 -19000 11000 3500  # mirror of east yard fence south
spawn team0 -21000 -5000 0
spawn team0 -21000 -3000 0
spawn team0 -21000 -1000 0
spawn team0 -21000 1000 0
spawn team0 -21000 3000 0
spawn team0 -21000 5000 0
spawn team1 21000 5000 32768
spawn team1 21000 3000 32768
spawn team1 21000 1000 32768
spawn team1 21000 -1000 32768
spawn team1 21000 -3000 32768
spawn team1 21000 -5000 32768
spawn ffa -21000 -12000 8192
spawn ffa 21000 12000 40960
spawn ffa -21000 12000 57344
spawn ffa 21000 -12000 24576
spawn ffa -9000 8500 0
spawn ffa 9000 -8500 32768
spawn ffa -8500 0 0
spawn ffa 8500 0 32768
spawn ffa 1250 -12500 16384
spawn ffa -1250 12500 49152
spawn ffa -16000 -8500 8192
spawn ffa 16000 8500 40960
control 0 0 3500
route -19500 0
route -6000 0
route -6000 8500
route 7000 8500
route 7000 0
route 19500 0
checkpoints 22000 35000 43500  # route length 56000
hazard fire 9500 9000 0 11500 10400 600 10 15  # spilled lantern oil
hazard fire -11500 -10400 0 -9500 -9000 600 10 15  # mirror of spilled lantern oil
lane north -19500,3000 -18500,3000 -18500,8000 18500,8000 18500,3000 19500,3000
lane south -19500,-3000 -18500,-3000 -18500,-8000 18500,-8000 18500,-3000 19500,-3000
lane mid -19500,0 19500,0
```

### 7.5 Silk Foundry (arena 2)

An industrial silk works. Twin furnaces stand north and south of a central
casting floor, with open slag channels (slag, 20 damage every 15 ticks) behind
them. The loom hall and reeling machines fill opposite quadrants, and boiler
rooms and coal bunkers guard the bases. The payload runs up the west side
through the reeling machines, crosses the north slag channel on its bridge (a
1200 mm crossing that burns anyone who stops on it), and returns to the east
base.

```arena-data
arena 2 silk-foundry
bounds -20000 -18000 20000 18000
wall -21000 -19000 0 21000 -18000 8000  # perimeter south
wall -21000 18000 0 21000 19000 8000  # perimeter north
wall -21000 -18000 0 -20000 18000 8000  # perimeter west
wall 20000 -18000 0 21000 18000 8000  # perimeter east
wall -2500 5000 0 2500 8000 6500  # north furnace
wall -2500 -8000 0 2500 -5000 6500  # mirror of north furnace
wall 3800 1500 0 4800 2500 2000  # casting mould north-east
wall -4800 -2500 0 -3800 -1500 2000  # mirror of casting mould north-east
wall 3800 -2500 0 4800 -1500 2000  # casting mould south-east
wall -4800 1500 0 -3800 2500 2000  # mirror of casting mould south-east
wall 5000 10500 0 5800 15500 2000  # loom row 1
wall -5800 -15500 0 -5000 -10500 2000  # mirror of loom row 1
wall 8000 10500 0 8800 15500 2000  # loom row 2
wall -8800 -15500 0 -8000 -10500 2000  # mirror of loom row 2
wall 11000 10500 0 11800 15500 2000  # loom row 3
wall -11800 -15500 0 -11000 -10500 2000  # mirror of loom row 3
wall 5000 -15500 0 9000 -14000 2200  # reeling machine A
wall -9000 14000 0 -5000 15500 2200  # mirror of reeling machine A
wall 5000 -11500 0 9000 -10000 2200  # reeling machine B
wall -9000 10000 0 -5000 11500 2200  # mirror of reeling machine B
wall 11500 -15500 0 12500 -10000 2600  # drive shaft housing
wall -12500 10000 0 -11500 15500 2600  # mirror of drive shaft housing
wall 8500 4000 0 9500 5000 7000  # hall pillar north-east
wall -9500 -5000 0 -8500 -4000 7000  # mirror of hall pillar north-east
wall 8500 -5000 0 9500 -4000 7000  # hall pillar south-east
wall -9500 4000 0 -8500 5000 7000  # mirror of hall pillar south-east
wall 13500 4500 0 16500 8000 5000  # east boiler room
wall -16500 -8000 0 -13500 -4500 5000  # mirror of east boiler room
wall 13500 -8000 0 16500 -4500 5000  # east coal bunker
wall -16500 4500 0 -13500 8000 5000  # mirror of east coal bunker
wall 7000 -2400 0 8200 -1200 2000  # crate stack east
wall -8200 1200 0 -7000 2400 2000  # mirror of crate stack east
wall -3500 14200 0 -2500 15200 2000  # crate stack north
wall 2500 -15200 0 3500 -14200 2000  # mirror of crate stack north
wall -1000 10500 0 1000 11300 2000  # bridge rail north
wall -1000 -11300 0 1000 -10500 2000  # mirror of bridge rail north
wall 16500 9500 0 18000 13500 4000  # east dye vats
wall -18000 -13500 0 -16500 -9500 4000  # mirror of east dye vats
spawn team0 -18000 -5000 0
spawn team0 -18000 -3000 0
spawn team0 -18000 -1000 0
spawn team0 -18000 1000 0
spawn team0 -18000 3000 0
spawn team0 -18000 5000 0
spawn team1 18000 5000 32768
spawn team1 18000 3000 32768
spawn team1 18000 1000 32768
spawn team1 18000 -1000 32768
spawn team1 18000 -3000 32768
spawn team1 18000 -5000 32768
spawn ffa -17500 -15500 8192
spawn ffa 17500 15500 40960
spawn ffa -17500 15500 57344
spawn ffa 17500 -15500 24576
spawn ffa -7000 13000 57344
spawn ffa 7000 -13000 24576
spawn ffa -10000 0 0
spawn ffa 10000 0 32768
spawn ffa -3000 -13000 16384
spawn ffa 3000 13000 49152
spawn ffa -11000 -9000 8192
spawn ffa 11000 9000 40960
control 0 0 3500
route -16500 0
route -10500 0
route -10500 12750
route 3500 12750
route 3500 3200
route 12500 3200
route 12500 0
route 16500 0
checkpoints 18750 32750 51300  # route length 58500
hazard slag -6000 8200 0 6000 9400 400 20 15  # slag channel north
hazard slag -6000 -9400 0 6000 -8200 400 20 15  # mirror of slag channel north
lane north -16500,3000 -10500,3000 -10500,12750 3500,12750 3500,16750 12750,16750 12750,3000 16500,3000
lane south -16500,-3000 -12750,-3000 -12750,-16750 -3500,-16750 -3500,-12750 10500,-12750 10500,-3000 16500,-3000
lane mid -16500,0 16500,0
```

### 7.6 Debt Citadel (arena 3)

The alien bank. Security walls with three doorways seal each base. The grand
hall ringed by vault columns holds the control point, and corner vault blocks
and an archive tower anchor the edges. Ledger shredder grates (shredder,
25 damage every 12 ticks) sit north and south of the hall. The payload circles
the hall on its north side, past the shredder, between bond presses.

```arena-data
arena 3 debt-citadel
bounds -23000 -16000 23000 16000
wall -24000 -17000 0 24000 -16000 9000  # perimeter south
wall -24000 16000 0 24000 17000 9000  # perimeter north
wall -24000 -16000 0 -23000 16000 9000  # perimeter west
wall 23000 -16000 0 24000 16000 9000  # perimeter east
wall 16000 -16000 0 17000 -11500 5500  # east security wall south
wall -17000 11500 0 -16000 16000 5500  # mirror of east security wall south
wall 16000 -8500 0 17000 -2500 5500  # east security wall inner south
wall -17000 2500 0 -16000 8500 5500  # mirror of east security wall inner south
wall 16000 2500 0 17000 8500 5500  # east security wall inner north
wall -17000 -8500 0 -16000 -2500 5500  # mirror of east security wall inner north
wall 16000 11500 0 17000 16000 5500  # east security wall north
wall -17000 -16000 0 -16000 -11500 5500  # mirror of east security wall north
wall 4500 3000 0 6500 5000 8000  # vault column north-east
wall -6500 -5000 0 -4500 -3000 8000  # mirror of vault column north-east
wall 4500 -5000 0 6500 -3000 8000  # vault column south-east
wall -6500 3000 0 -4500 5000 8000  # mirror of vault column south-east
wall -1000 5000 0 1000 7000 8000  # vault column north
wall -1000 -7000 0 1000 -5000 8000  # mirror of vault column north
wall 2500 1200 0 3300 2400 2000  # ledger terminal north-east
wall -3300 -2400 0 -2500 -1200 2000  # mirror of ledger terminal north-east
wall 8000 12000 0 13000 16000 7500  # vault block north-east
wall -13000 -16000 0 -8000 -12000 7500  # mirror of vault block north-east
wall 8000 -16000 0 13000 -12000 7500  # vault block south-east
wall -13000 12000 0 -8000 16000 7500  # mirror of vault block south-east
wall -2000 12500 0 2000 16000 7000  # archive tower north
wall -2000 -16000 0 2000 -12500 7000  # mirror of archive tower north
wall 9000 3500 0 11000 5000 2200  # coin counter north-east
wall -11000 -5000 0 -9000 -3500 2200  # mirror of coin counter north-east
wall 9000 -5000 0 11000 -3500 2200  # coin counter south-east
wall -11000 3500 0 -9000 5000 2200  # mirror of coin counter south-east
wall 5000 11200 0 6200 12000 2000  # bond press north
wall -6200 -12000 0 -5000 -11200 2000  # mirror of bond press north
wall -5500 7800 0 -4300 8600 2000  # bond press north-west
wall 4300 -8600 0 5500 -7800 2000  # mirror of bond press north-west
wall 12500 5500 0 14000 7000 2400  # ledger shelf north
wall -14000 -7000 0 -12500 -5500 2400  # mirror of ledger shelf north
wall 12500 -7000 0 14000 -5500 2400  # ledger shelf south
wall -14000 5500 0 -12500 7000 2400  # mirror of ledger shelf south
wall 19500 7000 0 21000 8500 3000  # conduit housing north
wall -21000 -8500 0 -19500 -7000 3000  # mirror of conduit housing north
wall 19500 -8500 0 21000 -7000 3000  # conduit housing south
wall -21000 7000 0 -19500 8500 3000  # mirror of conduit housing south
spawn team0 -20000 -5000 0
spawn team0 -20000 -3000 0
spawn team0 -20000 -1000 0
spawn team0 -20000 1000 0
spawn team0 -20000 3000 0
spawn team0 -20000 5000 0
spawn team1 20000 5000 32768
spawn team1 20000 3000 32768
spawn team1 20000 1000 32768
spawn team1 20000 -1000 32768
spawn team1 20000 -3000 32768
spawn team1 20000 -5000 32768
spawn ffa -20000 -12500 8192
spawn ffa 20000 12500 40960
spawn ffa -20000 12500 57344
spawn ffa 20000 -12500 24576
spawn ffa -5500 13800 57344
spawn ffa 5500 -13800 24576
spawn ffa -9500 0 0
spawn ffa 9500 0 32768
spawn ffa -14000 -9000 8192
spawn ffa 14000 9000 40960
spawn ffa -4000 -13800 16384
spawn ffa 4000 13800 49152
control 0 0 4500
route -19000 0
route -7500 0
route -7500 10000
route 7500 10000
route 7500 0
route 19000 0
checkpoints 21500 36500 46500  # route length 58000
hazard shredder -1500 7600 0 1500 9000 600 25 12  # ledger shredder grate
hazard shredder -1500 -9000 0 1500 -7600 600 25 12  # mirror of ledger shredder grate
lane north -19000,3000 -18500,3000 -18500,10000 18500,10000 18500,3000 19000,3000
lane south -19000,-3000 -18500,-3000 -18500,-10000 18500,-10000 18500,-3000 19000,-3000
lane mid -19000,0 19000,0
```

### 7.7 Export for presentation

`arena_core::arena_export::json()` renders the kernel's arena tables as JSON
(schema `sora-arena-arena-map-v1`): bounds, labelled walls in canonical order,
spawns, the control point, the payload route with its length, checkpoints and
push radius, labelled hazards, lanes, and each arena's map and lane digests.
`cargo run -p arena-cli -- arenas` prints it, and the checked-in copy is
`crates/arena-core/data/arena-map-v1.json`. Presentation builds its visuals on
top of exactly this collision and never adds collision of its own. The
`arena_maps` test regenerates the export, requires the checked-in file to match
it byte for byte, and checks every exported value against the kernel tables and
a live `World`.

## 8. Objectives and results

Control and Payload are team modes. Team membership is fixed at admission.
Only living players count toward an objective. Exhausted players never count,
because they never respawn. Both objectives are inactive on ticks 0–599 (the
index of the tick being executed): on those ticks phase 13 changes no progress,
idle count, owner or score.

### 8.1 Control (king of the hill)

| Constant | Value |
| --- | ---: |
| Unlock | inactive on ticks 0–599 |
| Capture threshold `CAP` | 480 progress units |
| Capture rate | `min(n, 3)` units per tick for `n` uncontested cappers |
| Decay when empty | 1 unit per tick toward the owner's full value, or 0 if unowned |
| Score target | 10,800 owned ticks (3 minutes) |

- A player is on the point when the horizontal distance from their position to
  the arena's control centre is at most its radius. `n0` and `n1` count team 0
  and team 1 players on the point.
- `control_progress` is in `[−CAP, CAP]`; negative values favour team 0.
- Contested (`n0 > 0` and `n1 > 0`): progress does not change.
- Team 0 alone: progress decreases by `min(n0, 3)`, floored at −CAP. Team 1
  alone: progress increases by `min(n1, 3)`, capped at CAP.
- Progress reaching −CAP makes team 0 the owner, and reaching CAP makes team 1
  the owner. Either change emits `ObjectiveCaptured`. Flipping an owned point
  therefore takes `2 × CAP` units.
- After the progress update of each tick, the owner (if any) scores one,
  including on contested ticks. A score never exceeds the target. Ownership
  and score are updated before the overtime check below.
- **Overtime.** When the owner's score equals the target, the owner wins at the
  first tick where the point is not contested and progress is at the owner's
  full value. Until then the match is in overtime: `overtime = true` and
  `OvertimeStarted` is emitted once. If the other team flips the point during
  overtime, it keeps scoring toward its own target. Overtime never extends past
  `max_ticks`.

### 8.2 Payload

| Constant | Value |
| --- | ---: |
| Roles | team 0 attacks, team 1 defends |
| Unlock | inactive on ticks 0–599 |
| Push radius | 3000 mm horizontal from the payload |
| Push speed | 6, 8 or 10 mm per tick for 1, 2 or 3+ uncontested pushers |
| Rollback | after 900 ticks with no attacker in radius, 4 mm per tick |

- The payload position is the floor point at distance `payload_progress`
  along the arena's axis-aligned route; progress starts at 0, the first route
  point. Segment lengths are exact integers. Players count when their
  horizontal distance to that point is at most the push radius.
- Attackers in radius and no defender in radius: progress advances by the push
  speed, capped at the route length, and `payload_idle` resets to 0.
- Attackers and defenders both in radius: no movement, and `payload_idle`
  resets to 0.
- No attacker in radius: `payload_idle` increases, saturating. From 900,
  progress rolls back 4 mm per tick, never below the last reached checkpoint.
- Passing checkpoint `k` (0, 1 or 2) for the first time, that is progress
  reaching its distance, emits `CheckpointReached { index: k }` and makes it
  the rollback floor. `payload_checkpoints` counts the checkpoints passed.
- Reaching the route end wins for team 0 immediately. At `max_ticks`, team 1
  wins. Payload has no overtime, because the ten-minute cap is absolute.

### 8.3 Free-for-all and Melee

FFA and Melee have no objective. The winner is the unique participant with the
most credited kills. A tie goes to the fewest deaths among the tied players; if
they are still tied, the result is a draw. Deaths count every death, credited
or not, including suicides and environmental deaths (§2.7). The winner has no
financial effect, because every transfer is per death (§11).

### 8.4 Terminal conditions and winner

At the end of every tick, after the clock increments, the first matching rule
fixes the result:

1. Payload route completed: team 0.
2. Control target met and the point secured (§8.1): the owner.
3. Staked team match, and one team has no player with a remaining reserve: the
   other team wins. If both teams are out on the same tick, it is a draw.
4. Staked FFA or Melee with fewer than two players holding a reserve: the §8.3
   winner.
5. `tick == max_ticks`. In Control the higher score wins, and equal scores draw.
   In Payload team 1 wins. In FFA and Melee the §8.3 winner.

`World.winner` is `Team(t)`, `Slot(s)` or `Draw`. It is fixed once, emitted as
`MatchWinner`, and followed by `Terminal`. It is part of the state hash.

## 9. Environmental hazards

Hazards are floor volumes from the arena data. They do not block movement,
rays, projectiles or line of sight.

- A living player without spawn protection is inside a hazard when its
  position's x, y and z all lie in the volume's closed ranges. Every volume
  starts at the floor (§7.2), so a player is inside while its feet are at or
  below the volume's top.
- In the hazard phase of every tick whose index (the tick being executed,
  before the clock increments) satisfies `tick % period == 0`, each player
  inside a hazard takes that hazard's damage: kind hazard, no origin, never
  guarded, never marked, reduced by a ward. A player inside two hazards is hit
  by each of them, in hazard order.
- Hazard damage emits `EnvironmentalDamage`. A resulting death uses the
  environmental credit rule (§3.4). The last enemy who damaged the victim within
  the assist window gets the kill, with the usual assists. With no such enemy,
  no one is credited and no value moves.

| Kind | Damage / period | Where |
| --- | --- | --- |
| 1 fire | 10 / 15 ticks | Estate storehouse embers, Lantern Ward spilled oil |
| 2 slag | 20 / 15 ticks | Silk Foundry slag channels |
| 3 shredder | 25 / 12 ticks | Debt Citadel shredder grates |

## 10. Respawn and loadout selection

- **Admission freezes equipment and bond terms.** A participant admitted with a
  special weapon (id ≥ 12) records it as `admitted_special`. Admission requires
  `2B`, or `B` with a recognised weapon NFT (§11). A participant admitted with a
  standard weapon can never select a special weapon in that match.
- **Selection input.** A new input bit `LOADOUT = 64`. With it set, `move_x` is
  the class (0–5) and `move_y` is the loadout index (0–2), and the input is
  structurally invalid if either is out of range. Each slot selects only for
  itself, through its own input in the batch. The request is an ordinary input:
  it is encoded, committed, revealed and journaled like any other (§2.2), so a
  selection is fixed by the certified batch of its tick. Only dead,
  non-exhausted players act on it, before that tick's respawn countdown, so a
  request on the respawn tick still applies. Living players ignore the bit, and
  its `move_x` and `move_y` still steer them.
- **Loadout index.** 0 selects the class ranged weapon `2c + 1`, 1 the class
  melee weapon `2c`, and 2 the admitted special, only if it equals `12 + c`. In
  Melee mode the chosen weapon must be melee. A request that fails these checks
  is ignored and leaves any earlier selection pending; a valid one replaces it
  (`pending_class`, `pending_weapon`).
- **Countdown.** A death sets `respawn_ticks = 480`. On each later tick a dead,
  non-exhausted player applies its loadout request, then `ability_cooldown` and
  `respawn_ticks` decrement (saturating), and the player respawns, emitting
  `Respawn`, once `respawn_ticks` is 0. A player that dies on tick D respawns
  in the player phase of tick D + 480. On that tick it neither turns nor moves,
  but the later phases treat it as alive: it can use its ability and attack
  from the spawn yaw and zero pitch.
- **Respawn** applies and clears a pending selection, then places the player at
  its spawn point (below), facing the spawn yaw with pitch 0, and restores the
  (possibly new) class health, 100 stamina, a full magazine of the (possibly
  new) weapon, 120 ticks of spawn protection and zero vertical velocity. It
  clears guarding and `guard_ticks`, charge, reload, attack recovery, stance
  and mark. The bond, `admitted_special` and the ability cooldown are
  unchanged; a class change keeps the old class's cooldown and entities
  (§5.1).
- **Spawn protection.** While `spawn_protection > 0` a player is not a target
  of enemy rays (§5.3), blasts (§2.6), fire zones (§6.4) or hazards (§9),
  although its body still stops projectiles and allied Healing lance shots
  still heal it. It counts down in the player phase and ends at once when the
  player releases an attack or activates an ability. The first spawn of a match
  grants none.
- **Spawn point.**
  - Team modes: `team_spawns[team][r mod 6]`, where `r` is the slot's rank among
    its team's slots in ascending order.
  - FFA and Melee: the first spawn is `ffa[slot]`. A respawn uses the FFA spawn
    with the largest minimum horizontal distance² to every other living player,
    with ties to the lowest index. With no other living player it uses
    `ffa[slot mod 12]`.
  - Spawn yaw comes from the arena data, at the first spawn and at every
    respawn; a respawn also resets pitch to 0.
- **ABI 3 inputs.** Until ABI 4, `arena_step` keeps its first-release-6 input
  domain: any button bit above `RELOAD` (32) is rejected with status 2,
  exactly as before, so ABI 3 callers cannot submit a loadout request.

## 11. Bonds and death transfers (unchanged)

- Each lobby declares a base bond `B`. It must be positive and divisible by 10
  in atomic units. Offline practice uses zero bonds and moves no value.
- Ordinary equipment requires a deposit of exactly `B`. One selected special
  weapon requires its recognised weapon NFT (deposit `B`) or an additional `B`
  (deposit `2B`).
- Every credited death of a bonded victim transfers exactly 10% of that
  victim's initial total deposit. The tranche is fixed for the whole match.
  Ten paid deaths exhaust the reserve, and the player becomes a spectator; there
  is no rebonding.
- **Team modes:** 60% to the killer, 20% to qualifying damage assists in
  proportion to damage within 5 s, and 20% equally to the killer's other
  participating teammates. With no assists, their 20% goes to the team; with no
  team recipients, the team share goes to the killer.
- **FFA and Melee:** 80% to the killer and 20% to assists, or 100% to the
  killer when there are no assists.
- Shares combine as exact rationals before rounding. Residual atomic units go
  one each to recipients in ascending permanent slot order.
- Earnings are separate from the reserve and are never at risk again in that
  match. Unassisted environmental deaths and suicides transfer nothing. Unused
  reserves return at verified settlement; network fees are disclosed separately,
  with no treasury cut and no minted reward.
- Participation for the team share is frozen before a tick's death batch, so a
  simultaneous exhaustion cannot remove a teammate's award.

## 12. Canonical state hash

The hash is SHA-256 over little-endian fields with the domain
`"sora-arena:reference-state:v2\0"`. First-release-7 fixes this layout.

1. Domain, then the `RULES_VERSION` UTF-8 bytes with no length prefix.
2. Config: mode (§2.1), map, offline (u8 each); max_ticks u32; base_bond
   u64.
3. tick u32; terminal u8; map digest (32 bytes, §7.1).
4. u32 player count. For each player in slot order:
   - u8: team, class, weapon, alive, guarding, `admitted_special` (the
     admitted special weapon id), `pending_class`, `pending_weapon` (each 255
     for none);
   - i32: position x, y, z, velocity_z, health, stamina;
   - u16 yaw, i16 pitch, u32 respawn_ticks, u8 charge_weapon;
   - u16: attack_cooldown, ability_cooldown, charge, ammo, reload_ticks,
     guard_ticks, spawn_protection, stance_ticks, marked_ticks;
   - account: u64 initial, remaining, earnings; u32 kills, deaths, paid_deaths.
5. u32 projectile count. For each projectile in list order: u32 id, u32
   owner, u8 weapon, i32 position x, y, z, velocity x, y, z and traveled, u16
   age (unchanged from first-release-6).
6. u32 entity count. For each entity in id order: u32 id, u8 kind, u32 owner,
   u8 team, i32 position x, y, z, u16 yaw, i32 health, u16 age, i32 half_x,
   half_y. Then u32 `next_entity_id`.
7. u32 damage-record count. For each record in list order: u32 tick,
   attacker, victim and damage (unchanged from first-release-6).
8. Objectives:
   - u32 score[0], score[1];
   - u8 control owner (255 for none), i32 control_progress, u8 overtime;
   - i32 payload_progress, u8 payload checkpoint count, u16 payload_idle.
9. Result: u8 winner tag (0 none, 1 team, 2 slot, 3 draw), then u32 value
   (the team or slot; 0 otherwise).

Booleans are one byte, 0 or 1. Signed fields are two's complement. Events are
not part of the hash.

## 13. Classes, weapons and weapon handling

The class and weapon catalog is unchanged from first-release-6 except the
rocket's name (§6.7). Every number is fixed in the versioned catalog
(`arena_core::catalog`); NFT rarity changes none of them.

### 13.1 Classes and loadouts

Each class `c` owns three weapons: the melee weapon `2c`, the ranged weapon
`2c + 1`, and the special sidegrade `12 + c`, which needs admission (§10, §11).
`MELEE` always attacks with the class melee weapon `2c`; `FIRE` attacks with
the equipped weapon, which may itself be melee.

| Class | Health | Speed mm/tick (guarding) | Melee `2c` | Ranged `2c + 1` | Special `12 + c` |
| --- | ---: | ---: | --- | --- | --- |
| 0 Samurai | 125 | 80 (40) | 0 Katana | 1 Arc carbine | 12 Monofilament naginata |
| 1 Shinobi | 100 | 100 (50) | 2 Kusarigama | 3 Needle SMG | 13 Phantom SMG |
| 2 Teppō | 100 | 75 (37) | 4 Wakizashi | 5 Coil matchlock | 14 Plasma matchlock |
| 3 Hanabi | 150 | 65 (32) | 6 Kanabō | 7 Grenade launcher | 15 Bō-hiya rocket |
| 4 Karakuri | 125 | 75 (37) | 8 Forge hammer | 9 Clockwork repeater | 16 Shock emitter |
| 5 Kusushi | 110 | 80 (40) | 10 Tanto | 11 Pulse carbine | 17 Healing lance |

### 13.2 Weapon catalog

Kind M is melee, H hitscan and P projectile. Cooldown is the attack recovery
after a release. Charge is the number of held ticks before a release, so a
weapon with charge `n` fires on the `n + 1`-th eligible held tick. Melee
weapons have no magazine; hitscan and melee weapons have no projectile speed,
blast or arming distance (shown as —).

| Id | Weapon | Kind | Damage | Range mm | Cooldown | Stamina | Charge | Speed mm/tick | Blast mm | Arming mm | Magazine | Reload ticks |
| ---: | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | Katana | M | 60 | 2300 | 36 | 25 | 0 | — | — | — | — | — |
| 1 | Arc carbine | H | 22 | 45000 | 12 | 0 | 0 | — | — | — | 24 | 96 |
| 2 | Kusarigama | M | 40 | 3000 | 32 | 25 | 0 | — | — | — | — | — |
| 3 | Needle SMG | H | 12 | 26000 | 6 | 0 | 0 | — | — | — | 32 | 102 |
| 4 | Wakizashi | M | 35 | 1800 | 24 | 15 | 0 | — | — | — | — | — |
| 5 | Coil matchlock | H | 65 | 70000 | 42 | 0 | 12 | — | — | — | 5 | 138 |
| 6 | Kanabō | M | 80 | 2100 | 48 | 35 | 18 | — | — | — | — | — |
| 7 | Grenade launcher | P | 65 | 40000 | 48 | 0 | 0 | 350 | 2500 | 2000 | 5 | 144 |
| 8 | Forge hammer | M | 45 | 2000 | 30 | 20 | 0 | — | — | — | — | — |
| 9 | Clockwork repeater | H | 20 | 38000 | 12 | 0 | 0 | — | — | — | 36 | 120 |
| 10 | Tanto | M | 30 | 1700 | 22 | 15 | 0 | — | — | — | — | — |
| 11 | Pulse carbine | H | 18 | 38000 | 10 | 0 | 0 | — | — | — | 22 | 93 |
| 12 | Monofilament naginata | M | 50 | 3400 | 44 | 35 | 0 | — | — | — | — | — |
| 13 | Phantom SMG | H | 10 | 19000 | 5 | 0 | 0 | — | — | — | 22 | 132 |
| 14 | Plasma matchlock | H | 85 | 55000 | 58 | 0 | 24 | — | — | — | 3 | 168 |
| 15 | Bō-hiya rocket | P | 85 | 50000 | 66 | 0 | 15 | 420 | 3400 | 4500 | 3 | 168 |
| 16 | Shock emitter | P | 28 | 22000 | 20 | 0 | 0 | 600 | 1100 | 0 | 18 | 114 |
| 17 | Healing lance | H | 15 | 42000 | 10 | 0 | 0 | — | — | — | 16 | 138 |

The catalog spells weapon 6 `Kanabo` without the macron.

### 13.3 Weapon handling

All ranged weapons start and respawn with a full magazine. Replacement
magazines are unlimited, but every refill takes the weapon's full reload
duration (§13.2; 60 ticks per second). Melee weapons use stamina and have no
ammunition.

**Reload.**

- `RELOAD` requests a whole-magazine refill if the equipped firearm is not
  full. A trigger request on an empty gun starts the same reload once attack
  recovery ends.
- A reload started at tick T with duration N sets its full remaining duration;
  each later tick decrements it, and it completes at T+N, when a held trigger
  may fire if nothing else prevents it. No shot can occur while reload ticks
  remain.
- A block or melee request interrupts the reload before that tick's completion
  check. The existing ammunition is kept and partial progress is discarded.

**Charge.**

- Reloading and guarding clear charge progress. A charged attack uses a round
  only when it actually fires.
- Charge progress is tagged with the selected weapon, so it cannot carry over
  from melee to a charged firearm. The tag is part of the state hash.

**Death and respawn.** Death cancels any pending reload or charge. Respawn
restores the magazine and clears melee defense and attack recovery.

**Kanabō and Plasma.**

- Kanabō strikes need 18 held ticks of windup and land on the 19th held tick.
  Releasing or guarding restarts the windup. Stamina is spent only when the
  strike lands, followed by a 48-tick recovery.
- Plasma matchlock direct hits need a 24-tick charge and penetrate parry,
  guard and the Samurai stance. It keeps its 3-round magazine and long reload.
  Other hits, including projectiles from a player holding Plasma, follow the
  normal defense rules.

**Healing lance.**

- In Control and Payload, the lance's ray stops at the nearest wall,
  barricade, enemy decoy or living player of either team (§5.3); spawn
  protection shields only enemies. A stop on an ally heals it by 15, up to that
  class's maximum, and a stop on an enemy damages it by 15. A full-health ally
  still stops the shot. Dead allies are skipped and cannot be revived.
- In FFA it damages other players. Ammunition and cooldown apply to every shot.
- All shots gather targets from the same pre-damage state. Queued healing
  resolves before ordered damage, which allows a same-tick rescue but no
  resurrection.
- Each non-zero heal emits the internal `Healed` event (weapon 17). ABI 3 does
  not export it, so ABI 3 callers still see only the shot and the next health
  snapshot.

### 13.4 Balance baseline

`cargo run --locked --release -p arena-cli -- balance` runs every weapon
through the 60 Hz kernel in an offline FFA match on Nyaagyu Estate. The
weapon's own class attacks from `(0, 0, 0)` with yaw and pitch 0, holding
`FIRE` every tick, at a stationary, undefended 125-HP Samurai standing at
`(lane, 0, 0)`: 1500 mm for melee and `max(5000, arming + 500)` mm otherwise.
The lane is clear of walls. Seconds are `(death tick + 1) / 60`. The output
recorded for this revision on 2026-09-25 is:

| Weapon | Attacker class | Kind | Lane mm | Death tick | Seconds | Shots | Damage events |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 0 Katana | 0 | Melee | 1500 | 72 | 1.217 | 3 | 3 |
| 1 Arc carbine | 0 | Hitscan | 5000 | 60 | 1.017 | 6 | 6 |
| 2 Kusarigama | 1 | Melee | 1500 | 96 | 1.617 | 4 | 4 |
| 3 Needle SMG | 1 | Hitscan | 5000 | 60 | 1.017 | 11 | 11 |
| 4 Wakizashi | 2 | Melee | 1500 | 72 | 1.217 | 4 | 4 |
| 5 Coil matchlock | 2 | Hitscan | 5000 | 66 | 1.117 | 2 | 2 |
| 6 Kanabō | 3 | Melee | 1500 | 84 | 1.417 | 2 | 2 |
| 7 Grenade launcher | 3 | Projectile | 5000 | 61 | 1.033 | 2 | 2 |
| 8 Forge hammer | 4 | Melee | 1500 | 60 | 1.017 | 3 | 3 |
| 9 Clockwork repeater | 4 | Hitscan | 5000 | 72 | 1.217 | 7 | 7 |
| 10 Tanto | 5 | Melee | 1500 | 88 | 1.483 | 5 | 5 |
| 11 Pulse carbine | 5 | Hitscan | 5000 | 60 | 1.017 | 7 | 7 |
| 12 Monofilament naginata | 0 | Melee | 1500 | 88 | 1.483 | 3 | 3 |
| 13 Phantom SMG | 1 | Hitscan | 5000 | 60 | 1.017 | 13 | 13 |
| 14 Plasma matchlock | 2 | Hitscan | 5000 | 106 | 1.783 | 2 | 2 |
| 15 Bō-hiya rocket | 3 | Projectile | 5000 | 107 | 1.800 | 2 | 2 |
| 16 Shock emitter | 4 | Projectile | 5000 | 87 | 1.467 | 5 | 5 |
| 17 Healing lance | 5 | Hitscan | 5000 | 80 | 1.350 | 9 | 9 |

In summary:

- The six standard ranged weapons kill in 1.017–1.217 seconds.
- Standard melee kills in 1.017–1.617 seconds.
- The specials take 1.017–1.800 seconds; the charged Plasma matchlock
  (1.783 s) and the Bō-hiya rocket (1.800 s) are the slowest.

These ranges are the ones first-release-6 recorded: the new arenas, abilities
and objectives do not change this clear-lane duel.

This is a repeatable mechanical baseline, not evidence of fair duels, readable
effects, map balance or human playtesting. The command's last line,
`scope=offline clear-lane mechanics only; proof_qualified=false`, says the
same.

## 14. Verification status

- Behavioural tests cover the guard-origin fix, `Guarded` and `Healed`
  emission, ABI 3 event filtering, and every first-release-6 rule that is
  unchanged. See the test files under `crates/arena-core/tests` and the
  `arena-ffi` unit tests.
- `class_abilities.rs` drives every class ability through real inputs: the
  Samurai stance (negation of frontal hits only, a single riposte that needs
  range and a clear line, blasts not negated, action lock, whiff recovery),
  parry stagger and refund, the Shinobi decoy against rays, projectiles, blasts
  and its owner's death, the Teppō mark (past allies and spawn-protected
  enemies) and its 300-tick window, fire-pot placement and the 14 fire-zone
  pulses (sparing enemies behind a wall or with feet above 1000 mm), the
  Karakuri barricade against movement, jumps, rays, projectiles and blasts,
  repair, replacement, destruction, expiry and invalid placement (walls, bodies,
  spawns and a path through a wall), and the Kusushi ward in team and FFA modes.
  `ability_entities.rs` covers id order, the per-owner bound and exact replay
  under ability spam, the ability phase ordering, owner death and exhaustion
  cleanup, cooldowns through death, and state-hash coverage of every entity
  field, `next_entity_id`, stance and mark.
- `arena_maps.rs` parses every `arena-data` block above and compares it with
  the kernel tables record for record, including labels and the route-length
  comments; checks every §7.2 invariant, including reachability on the 100 mm
  walk grid; checks that no jump clears or lands inside any wall; walks every
  payload route in 10 mm steps with 250 mm of clearance either side; checks
  every initial spawn and respawn in every mode and arena; checks that the map
  digest binds every rules field and ignores labels and lanes; checks
  projectile expiry at the bounds; and requires the checked-in export to match
  the kernel byte for byte and value for value.
- `objectives.rs` covers the Control unlock, capture rates, contest, decay,
  flips, scoring while contested, the secured win, overtime (including a flip
  during overtime and the clock limit), and the clock-limit results. For both
  objectives it checks that a body left on the point or beside the payload
  counts for neither team. For Payload it covers the push speeds and radius
  edge, contest, the idle count, rollback to the checkpoint floor, checkpoint
  events, staked team elimination and draws, the defenders' clock-limit win, and
  escorts that walk every arena's route with real movement inputs to an attacker
  win. `hazards.rs` covers hazard pulses (period, closed volume, height, spawn
  protection), ward-but-no-guard-or-mark, barricades over hazards, and credited,
  unassisted and lapsed environmental deaths. `modes.rs` covers Melee admission,
  a staked melee duel to exhaustion on every arena, the §8.3 tie-break, and a
  bonded eight-player free-for-all that conserves every unit through
  simultaneous kills and exhaustion. `respawn_loadout.rs` covers team-rank and
  FFA spawn selection, loadout requests, the special and Melee restrictions,
  input bounds, spectators, entity retention across a class change, attacks and
  abilities on the respawn tick, and hash coverage. `loadout_protocol.rs`
  carries loadout requests across every protocol boundary (§2.2): the exact
  eight-byte encoding and the decoder's rejection of out-of-range bytes,
  commitments that bind the class, index, bit and tick, and a scripted Control
  match on Nyaagyu Estate whose certified, wire-framed, rollback-predicted
  batches kill a player, carry its requests while dead (a wrong special, its own
  special, then a class change), reject swapped openings, and respawn it with
  the last valid selection exactly as a direct replay does; a durable journal
  restores the pending selection bit for bit. `full_match_clock.rs` runs a
  staked ten-minute match in every mode to its clock result. The `arena-ffi`
  tests check that ABI 3 serves every arena table exactly, rejects the loadout
  bit, and filters the new events.
- The practice ABI 3 parity fixture and the kill-history V2 projection are
  re-pinned whenever the rules identity changes. Their READMEs and change logs
  record why.
- Every rule in this document enlarges the future `ArenaV1` execution relation.
  No rule here is proof-qualified, and `proof_qualified()` stays false. The
  arenas bring 38–42 static walls where first-release-6 had 3–4, and every
  movement step, ray and blast line of sight tests all of them. Measure proof
  feasibility (the P5 scaling gate) before relying on entities and the larger
  collision sets in a funded match.
- `cargo run --locked --release -p arena-cli -- balance` reproduces the §13.4
  table exactly.
- Balance, readability and map flow need human playtests on Windows and macOS.
  The numbers here are provisional.
