# Notice-square roof route — October 28

Later correction: [night readability and camera support](notice-night-readability-2026-10-28.md)
records that the original canopy frame stood at street height and the separate
capsule-clearance sweep omitted WorldDynamic objects. Both queries are repaired
and requalified there. The original evidence and visual rejection below are
preserved; do not treat the old canopy image as a view from the canopy.

The later [live encounter rehearsal](notice-live-encounter-2026-10-28.md)
adds complete saved-start approaches with all seven guards initially active,
both inputs, the charge and escape. It preserves the earlier fixture scope
below and still leaves ordinary play and timing robustness open.

Chapter 3's former floating platform is replaced with a closed money-changer
building, pitched roof and supported board canopy. The authored amendment
retains the wall footprint X600–1320, Y400–1300 cm and east-west ridge at
Y800, Z750 cm. Both slopes have rise/run 0.475. Visible building triangles
and convex collision share vertices; roof collision follows the top planes.
This is functional architecture using primitives and existing materials,
not completed photoreal art or authored Nanite beams/tiles.

The board canopy spans X450–600, Y900–1500 at Z320 cm, on four grounded posts.
The lower ladder starts at (500,1600,0), facing south, and exits at
(500,1450,320). The upper flight starts at (500,1250,320), facing east, and
exits at (650,1250,540). The actual pitched surface there is Z536.25; the
capsule's rounded contact and normal floor clearance supply the standing
offset. Both flights retain 150 cm/s swept movement. Neither uses endpoint
teleports. The marksman stands at the actual (900,800,750) ridge post.

The route crosses toward (1100,1000), then approaches the west-facing
marksman from the east. The return reverses those roof segments and descends
both flights to the street. Only the board canopy receives the 1.5× board
footstep multiplier; the tile roof uses its actual local height for roof/fall
tracking. Fieldcraft does not create a duplicate floating slab. Retry
reconstructs exactly two building collision halves and both flights.

The conflicting northeast legacy house, two covers and one lamp are removed.
P1's affected corner detours via (1020,300), (440,300), (440,700), preserving
its 60 s period and 4 s pair offset. Later square beats' unused default patrol
rectangle also stays west of the building. The central street remains open.

Signed source `eafb433b937aab439895892e76e25ac4bdb7d64c`, tree
`d48906c3a3ce615b41cc126870c3582c1a4b627a`, passes all 23 selected native
tests with zero selected errors or warnings. The new cases cover real
keyboard and controller input from one initial street fixture, pause, both
flights, continuous grounded roof walking, the live scanning marksman's rear
takedown, return, death and checkpoint retry. Six other guards are removed
for these directed route cases; they do not establish ordinary encounter
difficulty. Ladder steps measure at most 2.5 cm per 1/60 s frame.

The separate guard-free support fixture removes the actual upper roof. The
hero remains held at (650,1250,542.15), with no arrival or release event; the
remaining building surface is 22.259 cm below the floor query. Restoring the
roof completes the climb exactly once. Six surface traces match the specified
roof/canopy heights; standing-capsule sweeps clear both ladder segments.

The 23 cases also include the actual drone circuit with all seven guards
live under a hidden observer, ground patrols, street routes, obstructions,
charge/escape/retry, malformed metadata, existing ladders and landing flights,
campaign spaces and the assisted campaign playthrough. All 66 gameplay source
gates pass at the same commit. These are scoped automation results, not an
ordinary full campaign playthrough or performance measurement.

The first native run at `69d57458` remains failed, 21/23. Two later-beat patrol
points lay inside the building. The keyboard fixture also mixed missing-roof
support with a live marksman and failed its held-state and takedown checks.
The repair corrects those patrol points and separates guard-free support
removal from the live takedown routes. The original failures are preserved;
no collision, deadline, speed or arrival threshold was relaxed.

Four original 1280×720 offscreen views were captured and inspected separately
in METAL_SM6 and METAL_SM5 on the M2 Ultra. Both rendered tests pass with zero
selected errors/warnings, and logs confirm the requested shader platforms.
All eight images **fail final-art and route-visibility acceptance**: the
ladder side, canopy approach and ridge are nearly black. The street facade
is visible but plainly a blockout. Night lighting must make the physical
route readable without contradicting stealth illumination. Tiles, ridge and
eave craft, timber, joinery and dressing remain unfinished. Only the HUD was
hidden; the first-person weapon remains visible. These captures do not prove
new Nanite geometry or actual-M1 compatibility.

Evidence lives under `Saved/Qualification/2026-10-28/` in the isolated SOURCE
worktree. Each native review authenticates 20 original files; each capture
review authenticates 26. All processes reach natural EOF. Source, native
libraries, Config, Generated and frozen integration ROOT stay unchanged
through every run. The raw engine pre-initialization diagnostics are retained.

| Evidence | SHA-256 of independent review |
| --- | --- |
| `notice-roof-runtime-69d57458-attempt1` (21/23) | `d32c6370f0ab171be187ff96313a3850a835a8ad752cfadb3a15ea7456f9bc27` |
| `notice-roof-runtime-eafb433b-attempt1` (23/23) | `be3cfce4f4d10a266e91b8da78f0001cbf6583fa0b6a069f215aad635ce878a9` |
| `notice-roof-source-eafb433b-attempt1` (66/66) | `39bfcb6a30a0239a0d9f3b5ad810b5ba144b495bc789476699fc85a8d2aeac11` |
| `notice-roof-capture-eafb433b-attempt1` (SM6) | `9d25687b6a564942d74c7c35431c7c0c7c55e700d7f05a41fed545371d53a90e` |
| `notice-roof-capture-eafb433b-sm5-attempt1` (SM5) | `4ae567611c348a196e49f0c898c57166f80cad5535c61bd5ad9ec0587b4bfd79` |
| Eight-original visual review (rejected) | `4254d51b4c6bb072e43d02275fe32a824b910f6f4306dd496b4527e598cb34bd` |

No new package was produced. ROOT remains frozen at `b6ba3c11`; the preserved
package remains `1b6dfadc`. Final art, ordinary seven-guard stealth play,
actual-M1/Windows, current-source packaging and performance remain open.
