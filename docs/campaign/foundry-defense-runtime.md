# Chapter 5 b07 foundry defense

Source implementation, not an engine qualification. The five named Unreal fixtures below have not been built or run in this change. Visual quality, live encounter difficulty, packaged Windows/Mac behavior and performance remain unqualified.

The authored contract in `chapter-05.md` b07 and its YAML is retained: 180 seconds, furnace 1500 HP, Kōzō 300 HP, west/east/north clay tubs each used once for a 3 second / 150 HP repair, Kōzō downable with a 4 second revival and a 25 second loss deadline, grenadiers prioritizing the furnace, and netted bellows crew imposing 5 HP/s until freed. Only b07 gains `foundry_defense`; b06 and generic defense rules retain their existing behavior.

The furnace is an actual stationary character damage target with the existing 180×180×220 cm collision shell. Ordinary opponent projectiles and blasts reach it through `SoraDamage`; the director mirrors its defended-target health. Its destruction uses ordinary checkpoint defeat. Kōzō is the actual detectable/downable companion, with health owned by companion rules; zero means down, and the director owns the rescue deadline. He returns at the existing companion rule's 50% health (150 HP). At survival completion, a downed Kōzō still requires rescue before his deadline. A revival must finish before the deadline; a tie fails. Paused/menu/dialogue time does not count.

Mapped Interact holds own one transaction: revive, free a net, or use clay. Damage to the hero, release, leaving real reach/visibility, menu/dialogue entry, defeat or beat teardown discards partial credit. Occupied hands gate weapon actions and restore the viewmodel on cancellation/completion. No new mandatory sheathing time is imposed. A full furnace refuses clay; a near-full repair is capped at 1500 and consumes one tub. Used tubs persist through pauses within an attempt, while checkpoint retry or a fresh checkpoint load resets all supplies and target health. Partial work is never saved.

Each grenadier uses its normal movement, sight, attack range, telegraph, shell and blast code with the furnace as its quarry. Other archetypes retain normal behavior; Kōzō can be damaged as a nearer exposed companion. b07 bypasses the generic proximity-based siege damage: pressure comes from actual attacks and stopped bellows. The existing netter drones still physically travel, lock, tether and rearm. Cutting a net or killing its tether frees the person. Any number of netted crew impose **5 HP/s total**, with fractional damage carried across frames; there is no drain with all crew free. Fractional debt survives temporary freedom, but resets with the attempt. For a last net cut within a long tick, drain stops at the cut's completion time. Within a normal game step repair completion is applied before the step's drain; deadline failure wins before other work results.

The following choices are provisional because b07 does not specify detailed placements or every interaction duration:

- Reuse the existing b07 flat foundry floor and target positions. Tubs sit at offsets (−380,−380), (+380,−380), (0,+380) cm from the furnace, with real collision and unobstructed approaches checked by the typed validator and runtime fixture walking.
- Two bellows workmates (`bellows_boy`, `bellows_worker`) stand at (−160,+700), (+160,+700) cm. The two authored 90 second wave drones target them separately. Their small functional tread proxies stop moving when their respective worker is netted; bespoke art remains open.
- Reuse b06's existing 800 ms lock and 1000 ms net cut, with no haul-away timer and the existing rearm/grace behavior. Crew are nettable helpers rather than additional health-loss targets. Kōzō is never assigned a net quarry.
- Interactions require 190 cm horizontal reach, a grounded hero and an unobstructed eye-to-work line. A new hold always starts at zero after an interruption.

## Verification

`test_foundry_defense.py` checks exact authored/normalized contracts, malformed types and identities, no b06 contract spill, actual C++ pure rule transactions, cancellation and supply reset, 24.999/25 second boundaries, repeated downs, per-frame fractional drain, and one/two-net completion timing. The ordinary generator and full campaign validator remain required.

Directed actual-input engine fixtures (root execution pending):

- `SoraArena.Campaign.FoundryRepairHolds`: real furnace damage, normal walking and mapped Interact, full-health refusal, partial/release/hit/menu/leave cancellation, weapon reservation, exactly three repairs, repeated-tub refusal, supply persistence, actual hero death/retry and fresh checkpoint load.
- `SoraArena.Campaign.FoundryKozoRescue`: actual companion downing, insufficient partial hold, 4 second revival to 150 HP a later timely rescue, and an outstanding rescue across the actual 180 second completion boundary.
- `SoraArena.Campaign.FoundryKozoDeadline`: actual downing, 24 second survival, failed late hold at 25 seconds, defeat-screen wait and normal Enter retry preserving the pawn.
- `SoraArena.Campaign.FoundryGrenadierPriority`: the authored 40 second wave, live AI, actual shell launch target and blast damage; actual furnace destruction and normal retry.
- `SoraArena.Campaign.FoundryBellowsNets`: actual timed wave spawning and drone approach/locking, two distinct crew nets, 5 HP/s total, partial and full normal-input cuts and stopped drain after rescue.

These fixtures harden the hero and freeze or damage unrelated opponents to isolate mechanics. They do not edit task progress, teleport the hero, inject net/revival credit or skip wave clocks. They are not full unassisted campaign or difficulty acceptance. The root must run them and relevant b06/crank, campaign spaces and assisted playthrough regressions after integrating the additive shared hooks with the current climb/moat lanes.
