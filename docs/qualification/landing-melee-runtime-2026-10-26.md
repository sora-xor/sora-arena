# Landing, drone melee and ward brazier runtime evidence

These directed UE 5.8.3 tests use the pinned Xcode 26.1.1 toolchain on the M2
Ultra. They run with NullRHI. They establish collision, mapped-input behavior
and bounded regressions; they do not establish visual quality, ordinary
stealth/combat difficulty, packaging or performance.

All evidence paths below are under `Saved/Qualification/2026-10-26` in the
isolated integration worktree. Original failures are retained. Every launched
root editor reached natural stdout EOF; no timeout or signal ended a run.
Each runtime attempt records source/tree/native pins, the build artifact,
test report and before/after input hashes. Its twenty recorded evidence files
were independently hash-verified. Config and Content/Generated did not change.

| Source | Evidence directory | Result |
| --- | --- | --- |
| `53967094` | `landing-space-53967094-runtime-attempt1` | 13/15 pass; WaterEdge and Solids fail; editor exit 3. |
| `febc3900` | `landing-space-febc3900-runtime-attempt1` | All seven landing-space cases pass; editor exit 0. |
| `63175381` | `melee-ward-63175381-runtime-attempt1` | Build fails on ambiguous fixture helper `Freeze`; no editor starts. |
| `25789bc5` | `melee-ward-runtime-attempt2` | 9/10 pass; DroneMelee fixture fails; editor exit 3. |
| `72d94e39` | `drone-melee-72d94e39-runtime-attempt1` | DroneMelee passes; DroneMeleeYari fails at checkpoint setup; editor exit 3. |
| `497ea0e7` | `drone-melee-yari-runtime-attempt2` | DroneMeleeYari passes; editor exit 0. |

The first landing run exposed a real obstruction: the east gangplank reached
bank height 100 cm inland, meeting the bank face 40 cm below its top. The
correction aligns its walking surface to the edge. The solids fixture had
queried only WorldStatic despite the runtime components' BlockAllDynamic
profile. It now includes WorldDynamic and probes three points along the
plank without weakening height or clearance expectations. All three mapped
routes then reached the real exit. Combat is frozen in those route fixtures.

The melee helper removes movement-sphere contacts before the world query and
merges actual imported hull contacts with cover and weak-point overlaps.
Its fixture covers all three weapon sweep radii, positive hull contact,
empty-space misses, intervening cover, contacts beyond the body and earlier
overlaps. The original fixture mistakenly tried to select the yari in a
wakizashi-only landing. The corrected landing case preserves that restriction;
the separate yari case uses its actual lesson checkpoint. An intermediate
attempt selected non-checkpoint ch02.b04 and failed before combat. The final
case uses ch02.b03, retaining the same mapped hit/miss assertions.

The nine passing cases at `25789bc5` are WardGateBrazier, DroneBody, the three
LandingDrone tests, ClassMeleeCommitted, GuardAndParryEveryMelee,
CollateralConstruct and assisted Playthrough. Later changes through `497ea0e7`
touch only the melee fixture file. The prior landing run also passes
DroneCrossing, LedgerPatrols and HorseShellClockAndImpact at `53967094`.
These results belong to their listed revisions, not one combined rerun.

Source/data authoring passed all 62 gameplay gates at `b91674cf` before
integration. The current complete source-check inventory contains 120 gates;
listing that inventory is not a test result.

Full ward-gate geometry, scanner/wicket bindings, ordinary route play, final
character/environment/weapon art, audio, current packages, Windows/M1 and
performance qualification remain open. Claude's separate `e8d5b587` character
checkpoint is not adopted: its s108 import was manually terminated after a
crash, and four reviewed originals still show smooth white paws and faceting.
The engine lane was explicitly returned to Claude at 13:05 UTC for further
readback and art work. The shared checkout was not used for builds or tracked edits.
