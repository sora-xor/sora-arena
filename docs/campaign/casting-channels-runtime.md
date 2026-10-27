# Casting-floor channels (ch05.b15)

The authored contract is in `chapter-05.md` §5 b15 (lines 608–609) and the
embedded beat YAML (`x_ext.hazards.molten_channels`): four east–west channels,
a 12-second cycle, a two-second amber warning, five seconds of flow, player
contact at 35 HP/s plus a two-second burn, automata destroyed on contact, other
enemies taking 60 HP/s, and environmental kills counting toward the waves.

The source previously retained this only in unconsumed `ext` data. The
generator now emits a checked `space.beats[].molten_channels` contract; the
catalog refuses missing, mistyped, misplaced or changed contract values.

Implementation decisions, distinct from the authored text:

- The unspecified residual burn rate uses the only authored player rate,
  35 HP/s. Contact refreshes one two-second burn; the burn and contact never
  charge the same interval twice. The explicit `burn_dps` and
  `burn_rate_interpretation` fields make this decision reviewable.
- All four channels start together with warning at beat admission, then flow
  during seconds 2–7 and cool during seconds 7–12. Their clock pauses with
  gameplay, including menu and blocking dialogue.
- Provisional nonblocking strips occupy x=66950–69450 cm, at y=-1000, -350,
  350 and 1000 cm, each 80 cm wide on z=0. These are functional positions in
  the existing 36×26 m casting-floor blockout, not final geometry. Walls,
  floor collision, cover, spawns and the adjacent Tarifa arena are unchanged.
- Grounded foot points within 8 cm of the channel floor create contact.
  Swept foot-point intervals catch walking across a strip between ticks;
  jumps and elevated walkways cannot acquire fresh contact. Jumping does not
  extinguish an existing burn. Time integration splits at both spatial and
  cycle boundaries and retains fractional HP across frames.
- Other enemies have contact damage only. The typed molten environmental
  rate bypasses rear/stagger bonuses only; normal invulnerability, shields,
  barriers, subdual, defeated-state and campaign admission stay in effect.
  No other attack or hazard receives this marker. Damage uses the existing
  actor damage/death path, so each registered enemy credits its own wave.
- Burn/contact state and warning lights stop on defeat and clear on retry,
  encounter teardown and world teardown. Pending damage cannot cross a
  synchronous encounter re-stage.

The host test compiles the actual pure C++ rules and checks large deltas
against millisecond stepping, warning/flow boundaries, burn refresh,
overlapping strips, swept crossings and negative damage-policy cases.
`SoraArena.Campaign.CastingChannelTraversal` exercises mapped walking and
jumping, airborne safety, damage, pause and death/retry.
`SoraArena.Campaign.CastingChannelEnemyCredit` exercises registered opponents,
enemy rates, airborne controls and exactly-once environmental wave credit.
Both fixtures disclose checkpoint/health/actor-placement assistance and frozen
enemy AI. Source/host checks are not an engine, rendering, lure-AI, performance
or difficulty pass. This is offline campaign logic, not a native practice rule.
