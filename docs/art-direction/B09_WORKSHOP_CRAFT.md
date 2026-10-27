# b09 lantern workshop: craft asset proposal (CPU design, for root's integration)

Chapter 03 beat b09 (提灯を張れ / Make the lanterns) needs physical craft assets at its four stations. Root asked
(Coordination 232, 2026-10-26) for a CPU-only design first: asset roles, bounds, pivots, sockets and craft pose
clearances, proposed before integration. Root owns state, accounting and collision.

**Status: a proposal.**
- Nothing is built in Blender or imported into Unreal, and nothing is adopted.
- The CPU previews are presentation only. They show shape, layout and framing as a geometric estimate. They do not
  establish Unreal framing, materials, light or hand and tool contact.

**Source of truth:**
- `scripts/art/b09_workshop_craft.py` builds every mesh, socket and check in numpy. It writes
  `docs/art-direction/data/b09_workshop_craft_spec.json`, the machine-readable form of this document.
- `scripts/art/test_b09_workshop_craft.py` tests it.

## 1. Inputs and root's decisions

The design reads root's tree at commit `2a846a6a`, each file pinned by its git blob in `INPUTS`.
`scripts/art/check_b09_root_inputs.py` verifies the pins and the constants, read-only. Its record is
`Saved/W18Rebuild/b09_root_inputs_check_v2.json`:
- no problems, and no pinned file changed at root's head `d0488603`;
- the first pin, at `c1f0b5af`, stays recorded in `b09_root_inputs_check.json`.

**From `c1f0b5af` to `2a846a6a`,** two pinned files changed, both additively:
- `SoraWorkshopCraftRules.h` gained `FView`;
- `SoraCampaignWorkshopCraft.cpp` gained `WorkshopCraftView()` and the failed-strip serial;
- `SoraWorldBuilder.h`, newly pinned, carries `FSoraKitView::LanternCraft`.
Timing, counts, eligibility and the station trace are unchanged.

**The stations** (`SoraLanternWorkshopRules.h`), in world cm:

| Station | Point | Floor | Steps |
|---|---|---|---|
| `st_b09_rib_form` | (2100, −620), the front of the plank floor | 45 | bend ×6 |
| `st_b09_paste_bench` | (2100, −950), the middle of the floor | 45 | paste ×4; assemble the rims ×1 |
| `st_b09_oil_rack` | (2100, −1300), by the yard door | 45 | paste the perilla oil ×1 |
| `st_b09_shell_bench` | (2790, −2050), the yard, under the storehouse's west eaves | 0 | assemble ×3 shells; inspect the fuse ×1 |

**The recipe and the rules:**
- bends release in 800 ms ±160 ms; pastes, including the oil, are 1.5 s holds;
- the output is 40 lanterns: the whole workshop's night of work, not 40 manual actions;
- a station is worked from within 260 cm (2D), the feet within 8 cm of its floor;
- a Visibility trace runs from the capsule's centre (floor +88) to the station point (floor +110);
- the capsule is 34 cm in radius with an 88 cm half-height, and the standing eye is at the capsule's centre +64 cm.

**The hero's camera** draws the world at **94°** across (`FieldOfView`), held at every aspect. 70° is its first-person
field of view, used only by first-person primitives (the viewmodel). These props are world meshes, so 94° applies.
- **The v1–v3 previews** used 70°, which was wrong for world meshes.
- **The checks:** 16:9, and 21:9 as the stress case. At 21:9 the frame keeps 94° across and loses height.

**Weapon 7:** an 84 cm bamboo tube with a 5.6 cm bore in a 7.6 cm culm.
- Its mesh runs from −20 to +64 cm along its bore.
- The muzzle is at +64, and the fuse at (0.2, −1.2, 6.0) cm.

**History** (chapter-03.md §4.3): separate hoops (輪骨) hooked onto a form (the continuous spiral is later), perilla
oil (荏油), and simple hanging lanterns for 1623. A lantern-craft historian should still verify this.

**Root's integration decisions (2026-10-27):**
- Keep the six player-bent hoops and four panels; visual density does not change gameplay counts.
- The turntable and hanging-slot mapping are retained as candidate presentation. They do not authorize recipe or
  registry changes.
- Root reviews the proposed collision proxies against the real traces and the traversable room before adopting any.
- Every station must visibly show actual progress and reset, with the rib release band and needle fully visible at
  the proposed working stand.
- The camera stays player-controlled; no forced cinematic camera.
- First-person craft paws and strip and brush contact remain production work. Sockets alone do not close them.
- Materials, final detail and actual Unreal captures remain required.

## 2. Frames, conventions, and the view contract

- **Units and axes:** Unreal centimetres, Z up, Unreal's left-handed axes. Blender holds a point at (x, −y, z) / 100 m,
  with each triangle's winding reversed (the Y flip mirrors).
- **The FBX convention** is `fbx_socket_export.SOCKET_FBX`, the Inventory drone's: Blender's own axes (Y forward, Z
  up), which are UE 5.8's FBX import axes, with the unit baked in. Interchange then converts nothing, and each socket
  imports on its own axes at scale 1.
  - The weapon kit's −Y forward would import the vertices and socket positions the same, but would turn every
    socket 180° about Y (`fbx_unreal_sockets.py`, measured on root's import of the drone).
  - The first draft of the build script used it. It was corrected before any run.
- **A station's frame:** its origin is the station point on its floor, (X, Y, FloorAt), with the world's axes. That is
  where `Floor()` puts the generic bench today.
- **The working side:** the hero works each station from its west side, facing +X. The four craftspeople (X 2250)
  work across the benches.
- **The work stand** is at (−80, 0, 0) in the station's frame, facing +X. It is a reference for framing, not a gate.
- **Sockets** are points, with X and Z axes where orientation matters. They are `SOCKET_` empties, imported as
  static-mesh sockets. Their points and axes are checked twice:
  - on the host, as Interchange will import them (`check_b09_candidates_fbx.py`);
  - in Unreal's readback (`import_b09_workshop_candidates.py`).
- **Material slots** are `M_B09_*` (§9), stored per triangle, so a merged mesh keeps each part's slot.
  - An earlier merge kept only the first part's slot. That turned the gauge's band and ticks into its face, which is
    part of why root saw no release band in v2.

**The view the presentation reads** is root's `SoraWorkshopCraftRules::FView`, as `FSoraKitView::LanternCraft`:
- `Active`, `RecipeComplete`, `Assist`, `Step`;
- `Committed[6]`, in recipe order;
- `HeldStep` (−1 idle) and `HeldMs`;
- `FailedStripSerial` and `FailedStripAgeMs` (−1 absent).

The art keeps no state of its own and never advances the view. Root's state handles every reset: a new press clears
the split pose, pause or cancel clears held work, and a retry clears the failure.

| View | Shows (every station) |
|---|---|
| `!Active && !RecipeComplete` | every station at its start, and the suggested 24 craftspeople's lanterns |
| `RecipeComplete` (later checkpoints) | every station finished, and all 40 slots filled |

## 3. The lantern

| | |
|---|---|
| Body | a barrel 44 cm tall and 30 cm across, with 18 cm openings (superellipse profile, exponent 2.2) |
| Hoops (輪骨) | six bamboo strips 4 × 1.6 mm, evenly spaced between the rims (radii 13.5–15.0 cm). Each overlaps its ends by 25° with a small hook. |
| Washi | four gores, each a quarter of the round plus 4° at each seam (8° of overlap per seam), over the hoops |
| Rims (口輪) | top and bottom, 2.0 cm tall and 0.8 cm thick, black lacquer |
| Bail | an iron arc rising 9 cm above the top rim. Its ring is the **hang point**, (0, 0, 32) from the centre. |
| Form (型) | a spindle, two collars and eight radial boards just inside the hoops. A collapsed state (boards at 40%) for drawing it out. |

**Stages:**
- **frame:** the form and six hoops;
- **papered:** the frame and the gores;
- **rimmed:** the papered lantern and the rims;
- **finished:** the form drawn out and the bail fitted.

**Pivots.** The lantern's parts (form, hoops and their flex stages, gores, bail, the finished lantern) share the
**lantern frame**, whose origin is its centre.

**Lantern height by station** (`LANTERN_Z`). The station point stays at the trace's 110.
- **The rib form:** the lantern's centre is at 110, where all six hoops show from the stand.
- **The paste bench and the oil rack:** it is at **130**, chest height.
- **Why 130:** at 110, the lower shoulder of a seam or stroke hid behind the lantern's belly from standing eye height
  (152). At 130 the front seam shows in full.

## 4. Stations

**Every station passes these:**
- `clearance()` on a 10 cm grid of hero positions: no proposed proxy blocks a station ray, and the stand is eligible
  with its own ray clear.
- `first_person()` at 94°, 16:9 and 21:9, from the stand, looking at the work: the required elements are in frame with
  a 2° margin and unoccluded.
- The same check from every eligible working-side position (in front of the bench, within 60° of the approach, on a
  20 cm grid), with the share that passes recorded.

| Station | Capsule gap at the stand | Eye to work, pitch | Stand (16:9 and 21:9) | Working side that passes |
|---|---|---|---|---|
| rib form | 16 cm | 86.8 cm, −28.9° | dial and hoops pass | dial 92%, hoops 100% (152 positions) |
| paste bench | 11 cm | 79.1 cm, −16.1° | seam passes | seam 100% (153) |
| oil rack | 11 cm | 79.1 cm, −16.1° | front stroke passes | front stroke 100%; side strokes 66%, reported only (149) |
| shell bench | 11 cm | 96.9 cm, −48.0° | shells and fuse pass | 100% (129) |

**Shell bench:** of its 1,336 eligible positions, 386 lie inside the storehouse. Their trace already meets its wall
today, by design.

### 4.1 Rib form (型台), `st_b09_rib_form`

**Static parts** (station frame):
- `SM_B09_RibFormBench`: top 60 × 100 cm at 75.
- `SM_B09_FormBase`.
- `SM_B09_Form`, its lantern centre at 110.
- `SM_B09_FlexGauge`.
- `SM_B09_StripStock`: twelve strips at the back edge.

**The flex gauge.** Root's v2 review found the old gauge low at the front-left, partly outside the frame, in one colour
and with no readable band. The new gauge:
- **Placement:** a dial on a post at the bench's right (the hero's right, +Y), facing the hero. Its pivot is at (−4, 34,
  132): above the highest hoop and beside the form, so the bending strip's free ends never sweep through it.
- **Face and marks:** a cream half-disc (radius 13.5). A dark scale rim, and dark ticks at 0, 400 and 800 ms and at
  the band's edges.
- **The needle** sweeps the whole half-dial, **−90° to +90° over 0–960 ms**, so the band spans 60°. Root turns it to
  point along (0, sin a, cos a), with a = `gauge_angle(HeldMs)`. At rest (`HeldStep` −1) it points to −90°.
- **The release band** is fixed and green, the 640–960 ms window: **+30° to +90°**, radii 8.0–12.0 cm.
- **Measured at the stand:** 28.7° off the dial's face, and the band subtends 6.2°: about 130 px at 1920 across.
- **Measured from the working side:** it reads from 92% of positions. The rest are at the far edge of reach, where the
  band falls under 2° or the dial is seen too far from its face (over 65°).

**State meshes:**
- `SM_B09_Hoop1..6` (lantern frame).
- `SM_B09_Hoop{k}_Flex000/025/050/075`, the strip being bent: straight and tangent to the form on the hero's side at 0,
  wrapping outward to the closed hoop at 1. Its length is the same at every stage (tested).
- `SM_B09_SplitStrip`.
- `SM_B09_GaugeNeedle`, its hinge at the origin.

| View | Shows |
|---|---|
| `Committed[0]` = n (0..6) | `Hoop1..n` |
| `HeldStep == 0`, `HeldMs` | hoop n+1's strip at `flex_stage(HeldMs)` (fully bent at 800 ms); the needle at `gauge_angle(HeldMs)` |
| `HeldStep == −1` | the needle at rest; no strip on the form |
| `FailedStripAgeMs ≥ 0` | `SplitStrip` at its rest while under 1,200 ms (a suggestion), then a fresh strip; a new press clears it |
| `Assist` | the same; the strip completes at 800 ms, as the rules' assist does |

**Sockets:** `StationPoint`, `WorkStand`, `LanternCentre`, `HoopSeat1..6`, `GaugePivot`, `StripStock`,
`SplitStripRest`, `StripHoldL/R` (hand targets for a future first-person pose).

**Proxy:** 64 × 104 × 78 cm. The dial (to 145.5 cm) and the spindle (to 148) are visual only.

### 4.2 Paste bench (糊台), `st_b09_paste_bench`

**Static parts:**
- `SM_B09_PasteBench`: top 70 × 110 cm at 75.
- `SM_B09_FormBase`: a turned pedestal and turntable, bringing the lantern's centre to 130.
- The form with all six hoops: the bends are done before this station.
- `SM_B09_PastePot`.

**State meshes:**
- `SM_B09_Washi1..4` (lantern frame), with per-vertex `height_frac` and `azimuth_frac`.
- `SM_B09_WashiSheet1..4`.
- `SM_B09_RimTop` and `SM_B09_RimBottom`, centred on their rings.
- `SM_B09_PasteBrush`: the bristles' tip at the origin.

| View | Shows |
|---|---|
| `Committed[1]` = n (0..4) | `Washi1..n`; sheets 1..4 − n on the stack (1..3 − n while a paste is held, since its sheet is `Washi{n+1}`); the turntable turns the lantern −90° × n, so seam n+1 faces the hero |
| `HeldStep == 1`, `HeldMs` | `Washi{n+1}` revealed to height_frac ≤ HeldMs / 1500; the brush along `Seam{n+1}_0..8`, bottom to top |
| `Committed[2] == 1` | the rims move from `Rim*Rest` (stacked on the bench) to `Rim*Seat` |

**Sockets:** `StationPoint`, `WorkStand`, `LanternCentre`, `Turntable`, `HoopSeat1..6`, `Seam1..4_0..8`, `BrushRest`,
`Rim*Rest`, `Rim*Seat`, `WashiSheet1..4`.

**Proxy:** 74 × 114 × 78 cm. The pedestal is visual only.

### 4.3 Oil rack (油掛け), `st_b09_oil_rack`

**Static parts:**
- `SM_B09_OilRack`: two posts to 185 cm, a crossbar at 175–180, sled feet and a shelf at 20.
- `SM_B09_RackHook`: its tip at 162, so the lantern's centre hangs at 130.
- `SM_B09_OilJar` (荏油) on the shelf.
- `SM_B09_DripTray`.

**State meshes:** `SM_B09_LanternFinished` (lantern frame, hung from its hang point at `LanternHang`), and
`SM_B09_OilBrush`.

| View | Shows |
|---|---|
| `Committed[2] == 1`, `Committed[3] == 0` | the finished lantern on the rack, dry washi. Before that the rack is empty. |
| `HeldStep == 3`, `HeldMs` | oil wetness to height_frac ≥ 1 − HeldMs / 1500 (top down); the brush along `OilStroke0_0..8` |
| `Committed[3] == 1` | the rack empties; the lantern hangs at slot 36 in the rafters |

**Side strokes.** The ±45° strokes are reported, not required: their lowest samples, on the bottom shoulder, hide
behind the belly from standing eye height, as a real lantern's do.

**Proxy:** the sled and shelf only, 76 × 104 × 22 cm. The posts, crossbar and lantern are visual only.

### 4.4 Tamakichi's shell bench (玉台), `st_b09_shell_bench`

**Static parts:**
- `SM_B09_ShellBench`: top 70 × 120 cm at 72.
- `SM_B09_WeaponCradle`: two V-blocks.
- `SM_B09_ShellRack`: three seats matched to the bore.
- `SM_B09_ShellTray`.
- `SM_B09_WrapPaper`.
- `SM_B09_FuseCoil`.

**Weapon 7** is the existing `SM_Weapon_07`, placed at `WeaponRest`:
- origin (12, −22, 81.8);
- its bore (X) along +Y, its Z toward −X;
- so its handle lies toward the back, and its fuse faces the hero.
- **Derived sockets:** `Muzzle` (12, 42, 81.8) and `FuseInspect` (6.0, −21.8, 83.0).

**State meshes:**
- `SM_B09_ShellCore`: 4.8 cm.
- `SM_B09_ShellWrapped`: 5.4 cm, its paper gathered into a tied neck. It seats in the 5.6 cm bore with 1.0 mm clear
  all round.

| View | Shows |
|---|---|
| `Committed[4]` = n (0..3) | n wrapped shells in `ShellSeat1..n`; 3 − n cores at `ShellCore*` |
| `Committed[5] == 1` | the fuse inspected (`FuseInspect`); weapon 7 is handed over at the beat's end |

The bench is about 10 m from the oil jars and away from flame.

**Proxy:** 74 × 124 × 75 cm.

## 5. The hanging output (rafters)

- **The poles:** four bamboo drying poles (⌀ 4 cm) at Y −560, −820, −1080 and −1340.
  - They span X 1795–2305, inside the walls' inner faces.
  - They sit at Z 395, hung by cords from the ceiling (its underside at 430).
- **The hooks:** ten per pole, 50 cm apart, giving **40 slots**. Each slot has a fixed yaw.
- **Clearances:**
  - every lantern bottom is at least 96 cm above a 195 cm head (ears included) on its floor;
  - the hooks' tops are 33 cm under the ceiling;
  - neighbours are 20 cm apart, and poles 230 cm.
- **The player's lantern** takes slot 36: pole 4, nearest the oil rack. It hangs there once `Committed[3] == 1`.
- **The fill is root's.** A suggestion: 24 of the craftspeople's lanterns from the start, the player's after the oil,
  and all 40 at `RecipeComplete`.

## 6. Collision and the station trace

- **Every mesh here is visual only.** This follows the dojo kit's pattern: the world builder keeps its boxes as
  collision.
- **The proxies:** each station gets one box under its bench or sled, each under 86 cm. Every station ray starts at
  88 cm, so no proxy can block the trace from any position.
- **Tested:** on a 10 cm grid of eligible positions at every station, no ray meets a proxy.
- **Tall parts carry no collision:** the dial, the spindles, the pedestal, the rack's posts, the poles and the lanterns.
- **Root decides,** after its own trace and traversal review. The current generic boxes are not an approved footprint.

## 7. First-person view

The camera is player-controlled. During bend, paste and oil, the director hides the weapon viewmodel, so the view
shows the station's props being worked.

- **The checks** (§4) take the world's 94°, at 16:9 and 21:9, looking at the work from the stand and from the working
  side.
- **They are geometric estimates of framing.** They are not Unreal framing; actual Unreal captures from these
  positions are the next step (§10).
- **No shipped first-person paws work the props.** `StripHoldL/R`, `BrushRest`, the seam and stroke paths and
  `WrapSpot` are hand targets only. Paws, strip and brush contact, and the craftspeople's animation remain production
  work.

## 8. Previews (presentation only)

The previews are a plain CPU raster: flat material colours, no transmission, no Unreal materials.

| Set | What changed |
|---|---|
| `b09_previews_v1` | first look; 70° (wrong); the gauge outside the hero's view |
| `b09_previews_v2` | the gauge moved onto a post, still 70°. Root archived and reviewed these (Coordination 23:53). |
| `b09_previews_v3` | the paste bench's washi as separate sheets |
| `b09_previews_v4` | the world's 94°, the new dial, the lanterns at chest height, 21:9, and two approach views. Its band was lost to the single-slot merge. |
| `b09_previews_v5` | per-triangle slots: the dial's face, band, ticks and needle read as designed. **The current set.** |

All are kept.

## 9. Materials (slots to bind)

| Slot | Use | Source to start from |
|---|---|---|
| `M_B09_Bamboo` | hoops, strips, poles | the project's bamboo (weapon 7's culm look) |
| `M_B09_TimberBench` | benches, rack, cradles, posts, brush handles | `wood_planks_dirt` (CC0), aged |
| `M_B09_TimberForm` | the form, its base and pedestal | a smoother hinoki |
| `M_B09_Washi` | gores and sheets. Its paste and oil parameters come from the per-vertex fractions. | `MI_LanternWardRain_ChochinPaper` (`texturecan_paper_0017`). **Measured transmission is required** (chapter-03 §5). |
| `M_B09_RimLacquer` | rims | black urushi |
| `M_B09_Iron` | bail, hooks, the needle's hub | the project's blackened iron |
| `M_B09_Ceramic` | paste pot, oil jar, drip tray | a dark glaze |
| `M_B09_GaugeFace`, `M_B09_GaugeBand`, `M_B09_GaugeMarks`, `M_B09_GaugeNeedle` | the dial: cream face, green band, dark ticks, vermilion needle | painted wood and lacquer |
| `M_B09_Bristle`, `M_B09_Cord`, `M_B09_Twine` | brushes, cords, twine | |
| `M_B09_ShellPaper`, `M_B09_ShellCore`, `M_B09_FuseCord` | shells and fuse | |

Photoshop, Illustrator and Topaz may help with source textures and marks, keeping provenance and leaving validation
originals untouched.

## 10. Next, and what remains

- **The engine sequence,** posted to root first and bounded:
  - **s144, Blender** (`create_b09_workshop_craft.py`): the candidate FBXs, with sockets, slots and both UV layers,
    into `Saved/B09Workshop/Candidates/s144`. The host then checks them against the module
    (`check_b09_candidates_fbx.py`), covering:
    - vertices, winding and outward-facing closed parts;
    - socket points and axes as Interchange imports them;
    - UVs and per-triangle materials.
  - **s145, Unreal import** (`import_b09_workshop_candidates.py`): separate candidate assets under
    `/Game/Generated/Candidates/B09Workshop`, with candidate materials. The washi master's paste, oil and glow
    parameters read UV1. A readback records the sockets' points, axes and scale, the bounds, the triangles, the UV
    channels and the bound slots.
  - **s146, Unreal capture** (`render_b09_workshop_review.py`): socket-pose review captures at the world's 94°.
    - The shots are taken from the stands, the approach views and the rafters, at 16:9, plus 21:9 for the
      mid-bend.
    - Each state mesh stands at its socket in the pose its state names, and nothing holds it.
    - These captures are not runtime first-person hand contact.
- **Root's:** adopting proxies, the turntable, the drying-pole fill and any first-person craft pose.
- **Not done:**
  - final modelling detail (notched form boards, ties, paper fibre), textures and the washi transmission measurement;
  - first-person paws and their contact;
  - the craftspeople's animation;
  - the warm windows;
  - the photoreal gate.
- **No adoption and no visual acceptance** is claimed.
