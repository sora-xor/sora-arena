# Chapter-six copying desks

At signed `4fa637fec37e8e760d1cbc614d72ab0de645c2a6`, the Mac editor builds
in 21.87 seconds and passes `SoraArena.Campaign.CopyDesks`,
`SoraArena.Fieldcraft.Candle` and `SoraArena.Campaign.Playthrough` together.
All three have zero selected errors or warnings. Editor and wrapper exit zero
with stream EOF; source, native inputs, Config and Content/Generated remain
unchanged. This is directed NullRHI evidence, not rendered or packaged acceptance.

## Behavior

`ch06.b08` now preserves `desk_tagata`, `desk_machikata` and `desk_shokukata`
as three distinct 30-second interactions. Its previous normalized form lost
those points and credited one 90-second hold at the generic anchor.

Each copy requires held, mapped Interact at that desk while grounded. Release,
leaving, damage, pause or blocking dialogue frees the hands. Each desk retains
its partial progress until checkpoint retry; time cannot spill to another desk.
An observing/alarmed guard pauses work, as does a living enemy within the
active desk's interaction reach on the same floor. Cupping the carried candle
halves the work rate. Copying occupies the hands; it cannot fire, reload or
switch arms. Only all three finished copies complete the beat. The objective
selects the nearest unfinished desk, and each proxy ledger shows its own state.

The ordinary volume hold used for the chapter-three cook fires remains intact.
Current data and loader checks reject a collapsed chapter-six timer or wrong
desk names/times; they do not introduce a legacy interpretation.

## Evidence and retained failures

Host progression passes all 133 authored tasks and both routes through eight
chapters. Content validation rejects 65 malformed variants, including missing,
duplicate or shortened copies and disabled guard interruption. Rule checks
exercise per-desk fractional work, six frame rates, interruption, overflow,
reset and refusal to complete from a forged aggregate timer.

The directed Unreal test resets guard awareness and freezes the guards away
from work, retaining one positioned living enemy for the physical-contest case.
It verifies remapping through the controls menu, the old key's refusal, occupied
hands, release/leave, pause, death/retry and completion in order 3, 1, 2. Actual
mapped walking and collision connect the desk interactions. Candle separately
checks open versus cupped work rates. The assisted campaign records eight
completed chapters, 133 beats, 120 checkpoint reads and 61 reloads.

Three preceding failed runs remain preserved:

- `025cb32`: build and Candle pass; the desk fixture tries to rebind outside
  the controls menu and correctly receives a refusal.
- `1cadec0`: build and Candle pass; the mapped-hold assertion and campaign
  approach fail, requiring more specific diagnostics.
- `c67742a`: diagnostics show copying/held/hidden true, watched true and zero
  work because frozen controllers retain their last sight sample. The walk
  helper requests an initial waypoint already under the player, but navigation
  requires a path with two points. The fixture resets patrol awareness and
  skips only already-reached waypoints. Production behavior is unchanged.

Local evidence is under `Saved/Qualification/2026-10-25/`, with one immutable
`copy-desks-<commit>-runtime-attempt1` directory per run. The passing run's
20 archived files independently rehash; its root review digest is
`6086d0dd3cf545bb07d79d176513e22bd1ad8ff040fdb149195d0dc2fae96a0c`.

CI `40204853855` at `025cb32` separately fails the stale timber campaign
binding. Regenerating it changes only the chapter-six content hash; timber
geometry, placement, manifests and coverage are identical. Binding checks and
tests pass. The new `4fa637f` CI run remains pending independent review.

## Remaining work

The desks are functional proxy geometry in the existing generated hall. The
authored hall layout, patrol placement, normal stealth difficulty, final art,
writing animation, rendered bilingual readability and current packages are
not established by these tests. No complete-game or release acceptance is claimed.
