# Notice-square night readability — October 28

The two ladder flights, canopy exit and ridge marksman now remain visible in
four directed night views, inspected separately in METAL_SM6 and METAL_SM5 on
the M2 Ultra. This resolves the fixed-camera visibility failure recorded in
[the physical roof checkpoint](notice-roof-route-2026-10-28.md). Final art is
still rejected: flat roof slabs, repetitive box wood, plain plaster, unfinished
characters, an empty sky and missing rain dressing remain visible.

The qualified implementation is signed `5bccf5f1d4142782319ca1157490d11657bc4e82`,
tree `b0443de68859ef1883b73851f2ae608aa4280896`. It uses the existing world rig
for ch03.b10–b12: a 3-lux, 9000 K key at 35° elevation with a 12° source angle,
without an atmospheric sun; dim diffuse sky at intensity 0.08; and blue fog
inscattering `(0.006, 0.008, 0.014)`. Auto-exposure brightness is limited to
0.48–0.96, a one-stop range, with the existing −0.3 compensation. If extended
EV100 units are enabled, the bounds are converted using the engine's lens
attenuation. The captured configuration uses linear brightness units.
Leaving the square restores the map defaults. This does not implement the
remaining Chapter 3 beats' authored lighting.

Two shutter windows provide 1900 K, 180-lumen, shadowed point lights with
450 cm attenuation radii. The new non-colliding frames and lattice preserve
the validated roof, ladder and drone clearances. They use existing generated
materials. The diffuse sky reuses `T_NyaagyuOvercast`, already recorded as
`kloofendal_overcast_puresky` by Greg Zaal in the Poly Haven asset ledger;
no new external image or mesh was imported.

Guard perception reads these actual light actors. The native fixture measures
canopy illumination at 540/1000 with the windows visible and 120/1000 with
them hidden; the distant alley and ridge remain 120/1000 in both cases.
This is the existing coarse intensity/radius proxy, not rendered-pixel
luminance or a shadow-occlusion simulation. Ordinary all-seven-guard stealth
balance still needs play review.

The later [live encounter rehearsal](notice-live-encounter-2026-10-28.md)
completes both routes with keyboard and controller and all seven guards live
at the saved start. Its fixed departure timings and retained failures do not
close ordinary-play or timing-robustness acceptance.

All 24 selected native tests pass with zero selected errors/warnings,
including both mapped-input roof routes, the live ridge marksman's takedown,
pause/return/retry, missing support, drone and ground patrols, charge,
ladder/landing regressions, campaign spaces and the assisted campaign test.
All 66 gameplay source checks pass. Each of the two rendered tests passes
with zero selected errors/warnings. All eight original 1280×720 images were
displayed and inspected without image edits or upscaling. Only the HUD was
hidden; the weapon remains visible.

Every screenshot has one successfully drained GPU exposure observation paired
to its actual screenshot frame. SM6 exposure scales are 1.1203 at the canopy,
1.1631 at the lower flight, and 1.6922 at the ridge and street facade; SM5 is
1.1173, 1.1655, and 1.6922 respectively. Both shader-platform metadata values
are confirmed in the original logs. This is M2 editor-game evidence, not a
new Nanite geometry test, actual-M1 run, Windows run, current package or
performance qualification.

## Corrections and rejected iterations

The old art-review stand trace queried only WorldStatic objects. The canopy
is a blocking WorldDynamic cube, so the old `CanopyFlight` frame was actually
captured from street height, camera Z154.15. An exposure diagnostic at
`e8055f34` established this. The new trace includes both object types, checks
the expected surface height, rejects unwalkable normals and allows for rounded
capsule contact on slopes. The current canopy surface is Z320 and camera
Z474.15; the ridge camera is Z884.04. The old canopy frame is not a matched
view from the canopy. Its rejection and original files are retained.

The old roof test's separate capsule-clearance sweeps also queried only
WorldStatic. They now include WorldDynamic and pass. Its six visibility
surface traces and real-input traversal cases already used the physical
roof and remain valid within their stated scope.

The diagnostic's first wrapper failed while collecting sidecars from an
incorrect assumed directory. The rendered test itself passed. Its original
failed wrapper is unchanged; a separate recovery authenticates the four
sidecars at their acknowledged session paths. Subsequent wrappers use those
logged paths and require one session, four screenshot pairs and zero failed
frames.

The first lighting implementation, `2d2223cc`, passed 24 native and 66 source
checks but failed visual review: its 0.06–0.12 exposure bounds and inherited
daytime fog made the scene too bright. All four originals are retained. The
current exposure/fog repair removes the washed-out horizon while preserving
readable route silhouettes. It does not establish photoreal acceptance.

Evidence is under `Saved/Qualification/2026-10-28/` in isolated SOURCE.
Reviews authenticate 20 originals per native run and 30 per current capture,
including four GPU sidecars. Processes reach natural EOF; source, native
inputs, Config, Generated and frozen ROOT remain unchanged during each run.
Raw pre-initialization engine diagnostics remain in the logs.

| Independent review | SHA-256 |
| --- | --- |
| Recovered `e8055f34` exposure diagnostic | `9bf83b2b183075cba40c16198b566c8245681caaa233e1a06486e7b87a98dec6` |
| `2d2223cc` native 24/24 | `4651b294333bd73646b2577c2c1d7e02b99c8d4806f44ed8556f6d368ee37b56` |
| `2d2223cc` source 66/66 | `e8be9029103fed499a1da49e80504581de970a4497cd92eecb6ac08a3e5ac132` |
| `2d2223cc` SM6 capture | `d35f4dfde92aab0f7f8fa0676b23334464c25b985f64f493cbd6883ed521a1ef` |
| `2d2223cc` visual rejection | `acee9929ee5aeb4812e7f03e3dd2803fc7d958e63ec2389814bc2ee2fe89a295` |
| `5bccf5f1` native 24/24 | `04d1ea7172f4862cde5ba7215b01a9a3f7ecd340f52022876e0b7b101eed5b32` |
| `5bccf5f1` source 66/66 | `f56989e360f4a625a6ffb72d5dfaeb5f649a68be2ae8d8ccf9420c79fcb49f7f` |
| `5bccf5f1` SM6 capture | `46a8a9f348a16a8d3c58f74ae98c04c129bb9df671d025ff83bc00b08b603a34` |
| `5bccf5f1` SM5 capture | `f4ff8b7b0e4ef5dd40beafa1612c6227316ed36409ad4ae22b865b7039bf683b` |
| Eight-original `5bccf5f1` visual review | `cce92f89fe0b09ebc7c825c24b2f2331df09fe789032190594abb0d99fb60a6e` |

ROOT remains frozen at `b6ba3c11`; the preserved package remains `1b6dfadc`.
No user-game input, exit or restart was issued. Final art, normal encounter
play, current-source packaging and platform/performance gates remain open.
