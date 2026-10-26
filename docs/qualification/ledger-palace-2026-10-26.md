# Ledger and palace runtime checkpoint — 2026-10-26

The connected ledger-to-palace route is traversable with mapped movement.
The inventory drones still fail the exact authored flight height because their
placeholder humanoid capsules collide with the ceiling. This is an incomplete
gameplay and art checkpoint, not release acceptance.

All runs used UE 5.8.3 / CL 58210709 on the M2 Ultra, pinned Xcode 26.1.1,
and native bridge `10ad7daddf73212e81496620aba628ebf214ab72`.
The tests used NullRHI. No render or package was produced in this cohort.

| Source | Result | Retained evidence under root `Saved/Qualification/2026-10-26/` |
| --- | --- | --- |
| `33d836555cf06a4947b33df3e678ea75eff43f70` | Build failed before editor launch: seven ambiguous `Point` calls exposed by unity compilation. No gameplay tests ran. | `ledger-33d8365-runtime-attempt1` |
| `f46c2c086c5f03945e81a781f89160141b863182` | Build passes after isolating ledger parser helpers. Six tests pass; LedgerRoute fails at a destination occupied by a held rifle guard. | `ledger-f46c2c0-runtime-attempt1` |
| `65f4aaeaf4dda58647fbb8a7b2e9ab8c6d7dc4d3` | Build passes. LedgerRoute passes after walking around the guard's body. LedgerPatrols fails the stricter exact-height check. | `ledger-65f4aae-runtime-attempt1` |

The six passing tests at `f46c2c08` are CopyDesks, LedgerPatrols,
RegistryPatrols, Spaces, Candle and the assisted 133-beat Playthrough.
The ledger patrol fixture observes live guards, lamps, pause, defeat and retry.
Its drone loops complete in 35,000 ms; the palace rifle completes in 40,000 ms.
The later height failure limits that earlier patrol pass as described below.

The mapped route holds guard AI while retaining their colliding bodies. It
visits the annex, all four cross-aisles, the north link, both quiet rooms and
the actual palace vestibule exit. It does not establish ordinary stealth
difficulty, accessible silent-edge movement, sliding fusuma or final art.

## Drone defect

The authored hall is 600 cm high and the drone flight centre is 550 cm. Each
placeholder drone has radius 20.4 cm and capsule half-height 52.8 cm. Its capsule
therefore cannot fit at 550 cm. Physics depenetrates it to 547.077–547.079 cm.
The original 5 cm tolerance accepted this displacement; the revised 0.1 cm
tolerance fails on the first observed frame. A non-overlap assertion alone
cannot establish that the body stays at its authored altitude.

The story bible calls for a floating disc with a cyan eye. A measured disc
body and appropriate collision envelope are assigned to Claude, with runtime
integration and regressions owned by Codex. The hall and flight coordinates
remain unchanged. The humanoid has not been scaled down to hide the defect.

## Evidence checks

All processes exited naturally. The failed build's wrapper exited 1 without
launching an editor; the two runtime cohorts exited editor 3 / wrapper 1 because
of their recorded failed tests. Each selected runtime report has zero warnings.
Source signatures, exact trees, all original output sizes/hashes and unchanged
source/native, Config and Generated input hashes were independently checked.

| Review | SHA-256 of root review JSON |
| --- | --- |
| Failed build, 14 files | `8c22b2c4989bac0555f4357163a18adf9725c28f02f9af74210e12cec2a873d2` |
| Six-pass/one-fail cohort, 20 files | `cc8696b1c8eb7ee9d727d3a0102ceda6fa1895b59a02a59e9f29147f644e9bec` |
| Strict-height cohort, 20 files | `19e8c9af40d9af26872417842917b05a74ea144770c363cff62a07e168f783f3` |

CI 40253701438 separately passes 112 source gates at `33d83655`, with identical
source/tested trees and all five artifact digests and raw logs authenticated.
Its review hash is `415a7463d59852e4eb7b225e448cd0418946c67cb1002366081a36dde74d46d8`.
Source CI does not establish Unreal compilation or behavior.

## Character checkpoint review

Claude's signed `145db735667f6709917107ce2cb6e2517eafba55` remains interim.
Root checked all 25 changed files against Git or their LFS hashes and viewed
all five original Guard/Idle images. The empty paws read as rings; the saya
projects horizontally behind the body; chest rods protrude; and the front
sword tip projects onto the mouth. It is not accepted as final art and has
not been imported or integrated into the root worktree.

The 32 targeted mesh/rig CPU tests pass on frozen signed files. Root's two
independent probes now reject a partly exposed crossing falsely labelled
hidden and a coplanar overlap previously missed. The first root harness run
omitted an unchanged helper module; that harness error is retained separately
from the subsequent passing run. These checks do not replace Blender or
Unreal deformation and visual qualification. The original two-paw grip,
natural empty paws and plausible saya carry remain open.
