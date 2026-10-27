# Continuous ward street: source and runtime checkpoint

The chapter-three ward previously ended at X −5600 cm with a closed boundary,
while tenement ground began at X −4700 cm. Its exit advanced the beat before
that gap, so normal progression relocated the hero to the tenement checkpoint.

This source adds a 900 × 720 cm ground connection, splits the ward's east wall
around it and retains solid side boundaries. The ward's spatial extent includes
the street. Its exit volume now lies wholly inside the tenements, with its west
edge 100 cm beyond their boundary. Normal progression therefore uses the
existing same-zone behavior without a relocation exception. The tenement entry
is unchanged for checkpoint loads. The gate, scanner, wicket and culvert retain
their dimensions and interactions.

The host geometry tests compile both construction tables. They check continuous
floor, full capsule clearance across the connector's width, no coplanar overlap
at the join, and every exit corner's membership in the next district. Mutations
restore the old exit, truncate the connector or move the spatial exceptions and
must fail admission. Eleven ward tests, sixteen tenement tests and campaign
validation pass. The validator admits only the exact authored connections; its
general separation and wall-count requirements remain for other places.

The three Unreal route fixtures now measure every movement step across the beat
transition, continue onto the tenement street, and check that retry uses its
checkpoint entry. Additional floor traces cover both joins and the old wall.
The initial source checkpoint preceded Unreal validation. The later runtime
result below validates these fixtures separately from the earlier `ca98e606`
run. Ordinary play, visuals and release acceptance remain open.

All 64 gameplay source gates subsequently pass at signed
`d41c662e7ddeb5a1c004fd7867660e08d0b3ea95`, tree
`07f5b17f3c76e26dc6c98652805e128c4bdde8e6`, with a clean, unchanged checkout.
The source-validation worktree retains
`Saved/Qualification/2026-10-26/ward-street-source/report.json` (SHA-256
`28b0aca891f6659509c081d908e516612fec235a9820c56275a588d4b643f7bb`)
and its separate 64-log/inventory audit `independent-review.json` (SHA-256
`cac9b4123de0383a18055a59e19fa372020d4625fc38eeb812114fbf71b86995`).
These host results do not compile the Unreal code or validate its fixtures.

## Subsequent Unreal result

Signed `bae6e9d4b244f59b8085e70d9d9c71bfb31eeb20`, tree
`a68672e073ca36b9b4827a3cbae33bc9102b4a47`, builds in UE 5.8.3 and passes all
32 tests in the [combined selection](ward-tenement-runtime-2026-10-26.md#exact-runtime-selection).
All three gate routes walk across the street without a relocation at the beat
transition, then continue into the tenements. The culvert route's actual defeat
and retry returns to the authored tenement checkpoint. The assisted full
campaign and all selected regressions also pass.

The integration worktree retains
`Saved/Qualification/2026-10-26/ward-street-runtime-bae6e9d4-attempt1/`, run
18:34:22–18:36:51 UTC. Wrapper and editor reach natural EOF with exit 0; source,
native, Config and Generated inputs stay unchanged. Independent review verifies
all 20 original files, exact test selection and candidate source/tree binding.

| Evidence | SHA-256 |
| --- | --- |
| Runtime `status.json` | `094e14dfadaa9f55097b788f100463eb4e08d2f4beaf86924a5da791e8281ba5` |
| `automation/report/index.json` | `887de7f9d47bffd0a89d2584d7e08cf37c0d7ac7559fcc028b592c92d183e782` |
| Sibling `ward-street-runtime-bae6e9d4-attempt1-review.json` | `378726a8b088ffd65d0bae83dc73c93bb139b19074ada7b884a09669dd68be18` |

These are NullRHI directed fixtures with held threats and an assisted campaign;
they do not establish ordinary stealth/combat difficulty or final visuals. The
latest Mac package stays `c655b6b`, native bridge `10ad7dad`. Root returned the
engine/Blender lane to Claude at 18:37 UTC. The game remains incomplete.
