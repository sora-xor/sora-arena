# b09 lantern workshop: craft asset proposal (CPU design, for root's integration)

Chapter 03 beat b09 (提灯を張れ / Make the lanterns) needs physical craft assets at its four stations. Root asked
(Coordination 232, 2026-10-26) for a CPU-only design first: asset roles, bounds, pivots, sockets and craft pose
clearances, proposed before integration. Root owns state, accounting and collision.

**Status: a proposal, with one diagnostic engine pass (s144–s148, 2026-10-27, §11).** Nothing is adopted.
- **Built and imported:** Blender built the candidates (s145), and Unreal imported them as separate candidate assets.
  The import, s147, failed its exact triangle-count contract, and the failure stands.
- **Captured:** s148's 15 captures are a diagnostic of that failed candidate. Root's review: the structure and
  sockets read, but the production look is rejected.
- **Since then,** the geometry those captures exposed is fixed on the CPU (§11). It is not yet rebuilt or recaptured.
- **The CPU previews are presentation only.** They show shape, layout and framing as a geometric estimate. They do
  not establish Unreal framing, materials, light, or hand and tool contact.

**Source of truth:**
- `scripts/art/b09_workshop_craft.py` builds every mesh, socket and check in numpy. It writes
  `docs/art-direction/data/b09_workshop_craft_spec.json`, the machine-readable form of this document.
- `scripts/art/test_b09_workshop_craft.py` tests it.

## 1. Inputs and root's decisions

The design reads root's tree at commit `c096eb98`, each file pinned by its git blob in `INPUTS`.
`scripts/art/check_b09_root_inputs.py` verifies the pins and the constants, read-only. Its latest run (v9):
- no problems, and no pinned file changed at root's head `c096eb98`;
- it also checks FView's `LastAction` (`FAction`: Serial, Step, Unit, AgeMs) and `ActionPresentationMs` = 1200;
- it now also compares the room's solids with the header box by box: centre, size and surface. The module's copy
  leaves out the ground slab;
- the earlier pins stay recorded: `c1f0b5af` (v1), and `2a846a6a` (v2 and v4; v3 read the wrong tree and failed,
  empty).

**From `102c18d9` to `541c61ae`** (Coordinations 242, 243 and 248), the full diff read, four pinned files changed, all
additively:
- `SoraWorkshopCraftRules.h` adds `ActionPresentationMs` = 1200 and `FView.LastAction`;
- `SoraCampaignWorkshopCraft.cpp` records it on each credited unit;
- `SoraWorldBuilder.h` adds the station marks;
- `SoraPlayerCharacter.cpp` stops crouching on a ladder.

The action contract (`workshop-action-view.md`) is pinned with them.

**From `541c61ae` to `c096eb98`** (Coordination 256), only `SoraPlayerCharacter.cpp` changed. It refuses the guard and
taking up an arm while the hands are stowed. Timing, eligibility, the trace, the stations, the recipe, the capsule and
the eye are unchanged throughout.

**From `2a846a6a` to `fcf3ffb5`,** only `chapter_03.json` changed, for b10's ground routes in `ch03_lantern_ward`. The
`ch03.b09` beat is identical.

**From `fcf3ffb5` to `102c18d9`** (Coordination 240), two pinned files changed:
- `SoraLanternWorkshopRules.h` shortens the east yard wall to end at Y −400, opening the main street. Its box is now
  (3700, −1450, 100), 2100 cm long; `SOLIDS` follows it.
- `SoraWorldBuilder.h` gives `Lanterns` a notice-square argument.
The stations, recipe, state and eligibility are unchanged.

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
| Hoops (輪骨) | six bamboo strips 4 × 1.6 mm, evenly spaced between the rims (radii 13.5–15.0 cm). Each is hooked into its notch at one end and wound on as the form turns (385°); its ends are scarfed and lap by 25° within the strip's thickness. |
| Washi | four gores, each a quarter of the round plus 4° at each seam (8° of overlap per seam), over the hoops |
| Rims (口輪) | top and bottom, 2.0 cm tall and 0.8 cm thick, black lacquer. Each sits **on** its mouth, its face against the paper's edge and the boards' ends (centred across the mouth, they crossed the paper and the boards). |
| Bail | an iron arc set on the top rim's upper face, rising 9 cm, with a ring at its crown **across** the arc's plane, so a hook in the arc's plane threads it. The ring's top is the **hang point**, (0, 0, 34.2) from the centre. |
| Form (型) | a spindle, two collars and eight notched radial boards just inside the hoops; it turns on its spindle as each strip winds on. A collapsed state (boards at 40%) for drawing it out. |

**Stages:**
- **frame:** the form and six hoops;
- **papered:** the frame and the gores;
- **rimmed:** the papered lantern and the rims;
- **finished:** the form drawn out and the bail fitted.

**Pivots.** The lantern's parts (form, hoops and their flex stages, gores, bail, the finished lantern) share the
**lantern frame**, whose origin is its centre.

**Lantern height by station** (`LANTERN_Z`). The station point stays at the trace's 110.
- **The rib form: 120,** so its lowest hoop is in reach from the craft stand.
- **The paste bench: 110; the oil rack: 116** (the view repair, Coordinations 252 and 257).
  - From the craft stand, a lantern whose top is at eye height spans 55° of height, more than 21:9's 45.4°.
  - At these heights every stroke sample is in frame and unoccluded at 16:9 and 21:9, except the one at the bottom
    mouth (`B09_CRAFT_PAWS.md` §6.1).
  - The earlier 130, chosen from the old framing stand at −80, no longer holds at the craft stand.

## 4. Stations

**Every station passes these:**
- `clearance()` on a 10 cm grid of hero positions: no proposed proxy blocks a **standing** station ray, and the
  stand is eligible with its own ray clear. Crouching is not covered (§6).
- `first_person()` at 94°, 16:9 and 21:9, from the stand, looking at the work: the required elements are in frame with
  a 2° margin and unoccluded.
- The same check from every eligible working-side position (in front of the bench, within 60° of the approach, on a
  20 cm grid), with the share that passes recorded.

Measured from the **craft stand**, the capsule 1 cm off the proxy (the stand the craft poses work from):

| Station | Capsule gap to the parts | Eye to work, pitch | At the craft stand (16:9 and 21:9) | Working side that passes |
|---|---|---|---|---|
| rib form | 3 cm | 57.7 cm, −33.7° | dial and hoops pass | dial 93 %, hoops 100 % (152 positions) |
| paste bench | −4.6 cm: the lantern frame overhangs its proxy (reported) | 58.3 cm, −46.0° | seam passes; its bottom end at the rim is hidden, reported only | seam 100 %; the bottom end 69 %, reported only (153) |
| oil rack | 2 cm | 61.6 cm, −35.8° | **front stroke FAILS, open:** its bottom socket hides under the lower bulge | **front stroke 78 %, open** (under the required 90 %; it was 97 % at z 130); side strokes 23 %, reported only (149) |
| shell bench | 3 cm | 58.0 cm, −43.6° | shells and fuse pass | 100 % (129) |

These element checks are separate from the active-contact view of each stroke (`B09_CRAFT_PAWS.md` §6.1).

**Shell bench:** of its 1,336 eligible positions, 386 lie inside the storehouse. Their trace already meets its wall
today, by design.

### 4.1 Rib form (型台), `st_b09_rib_form`

All positions below are in the station frame, cm. The spec (`docs/art-direction/data/b09_workshop_craft_spec.json`)
is the source of truth.

**Static parts:**
- `SM_B09_RibFormBench`: top 60 × 100 cm at 75.
- `SM_B09_FormBase`: a turned pedestal, centred at (−15, 0).
- `SM_B09_FlexGauge`.
- `SM_B09_StripQuiver` at (−22, 38), with `SM_B09_StripStock`: twelve strips standing in it.
- **The turning form** `SM_B09_RibForm` is its own asset. It is placed at `LanternCentre` (−15, 0, 120) and turned
  by `wind_deg` × (Committed[0] + the flex stage of HeldMs), with `wind_deg` = 385.

**The flex gauge:**
- **Placement:** a dial on a post at the bench's front-left (−Y), facing the hero, its pivot at (−19, −34, 128). The
  one-ended winding's free strip leaves toward the hero's right, so it never sweeps the gauge. At pivot height 142
  the dial's upper half left the 21:9 frame from the craft stand.
- **Post:** it stands behind the face and carries it. It had stood 0.8 cm in front of the face, under the needle's
  hub, and stopped short of it.
- **Needle and band:** the needle's hub sits on its pin. The needle sweeps −90° to +90° over 0–960 ms. The release
  band (640–960 ms) is +30° to +90°.

**State meshes:**
- `SM_B09_Hoop1..6` (the form's frame).
- `SM_B09_Hoop{k}_Flex000/025/050/075`: hooked at one end, wound on as the form turns, the free end straight toward
  the hero's right.
- `SM_B09_SplitStrip`: it lies along the bench's back at (20, 0). Its 91 cm used to lie across the gauge's foot and
  overhang the bench by 25 cm.
- `SM_B09_GaugeNeedle`.

**Sockets:**
- `StationPoint`, `WorkStand` (the craft stand, −67), `LanternCentre`, `FormSpindle`, `HoopSeat1..6`;
- `WindPress1..6`: the left paw's press, its normal the form's own, tilted with the profile;
- `WindGuide1..6`;
- `GaugePivot`, `StripStock`, `SplitStripRest`.

**Proxy:** 64 × 104 × 78 cm.

### 4.2 Paste bench (糊台), `st_b09_paste_bench`

**Static parts:**
- `SM_B09_PasteBench`: top 70 × 110 cm at 75.
- `SM_B09_FormBase`: a plinth turntable at (−27.5, 0), its plate at 80.
- `SM_B09_PaperStand`: (−35, −52)–(−7, −22), top at 114. It carries the whole sheet stack, which overhung it by 5 cm.
- `SM_B09_PotStand`: (−35, 22)–(−7, 55), top at 108. It carries the paste pot at (−28.5, 29) and the top rim's rest
  at (−16.6, 44.5). The rim's rest used to run through the pot.
- `SM_B09_PasteFrame`, a separate asset: the form and six hoops. It is placed at `LanternCentre` (−27.5, 0, 110) and
  turned −90° × n by the turntable.

**State meshes:**
- `SM_B09_Washi1..4`;
- `SM_B09_WashiSheet1..4` at (−21, −37), stacked;
- `SM_B09_RimTop` and `SM_B09_RimBottom`. The bottom rim's rest is its seat: it is fitted to the frame before the
  paper. The rims step seats the top rim.
- `SM_B09_PasteBrush`: its `BrushRest` is in the pot. The bristles' tip is on the pot's floor, and the handle leans
  back on the far lip with a 0.3 mm stand-off; its rotation is in the socket.

**Sockets:** `StationPoint`, `WorkStand` (−72), `LanternCentre`, `Turntable`, `HoopSeat1..6`, `Seam1..4_0..8`,
`PasteDip`, `BrushRest`, `RimTopRest`, `RimTopSeat`, `RimBottomRest` (its seat), `RimBottomSeat`, `WashiSheet1..4`.

**Proxy:** 74 × 114 × 78 cm. **Overhang, reported:** the lantern frame's front reaches up to 5.6 cm past the proxy,
at least 17.4 cm from the standing torso (`proxy_overhangs`).

### 4.3 Oil rack (油掛け), `st_b09_oil_rack`

**Static parts:**
- `SM_B09_OilRack`: two posts, a crossbar, sled feet and a low shelf.
- `SM_B09_RackHook`: it leaves the crossbar's face and bends down into a U in the bail's plane. The bail's ring,
  across that plane, rests with its top wire 0.5 mm over the U's. The old hook and ring lay in one plane and crossed
  (134 pairs).
- `SM_B09_DishBracket`: the arm squares off the post's face, then runs to its ring. The ring's profile is now closed.
- `SM_B09_OilDish` at (−30.5, 24, 118).
- `SM_B09_OilJar`, `SM_B09_DripTray`.

**State meshes:**
- `SM_B09_LanternFinished`, its centre at (−19, 0, 116), hung from its hang point at `LanternHang`;
- `SM_B09_OilBrush`: its `BrushRest` lies across the dish on the rim at both sides, the handle back over the dish.

**Proxy:** 76 × 104 × 24 cm.

### 4.4 Tamakichi's shell bench (玉台), `st_b09_shell_bench`

**Static parts:**
- `SM_B09_ShellBench`: top 70 × 120 cm at 72.
- `SM_B09_ShellStand`: (−35, −50)–(−12, 30), top at 106.
- `SM_B09_ShellRack`: a plank with three cups bored to weapon 7's 5.6 cm bore, at y −42, −34 and −26. The old solid
  block sank the shells 2 cm into it.
- `SM_B09_ShellTray` at (−26.4, 19), with the cores 120° apart on its floor. They had overlapped and floated 5 mm.
- `SM_B09_WrapPaper`, `SM_B09_FuseCoil`.
- `SM_B09_WeaponCradle`: two V-blocks on posts from the bench. They hold weapon 7's two clean cylinders, measured on
  `SM_Weapon_07.fbx` (LOD0): the oak collar (r 4.02) and the bare muzzle end (r 3.80), each with a 0.3 mm stand-off.
  The old blocks were sized to the bare culm and stood inside the real rope wrap.

**Weapon 7** is the existing `SM_Weapon_07`, placed at `WeaponRest`:
- origin (−29, 40, 112): the bore along +X, away from the hero, the fuse up and its cord hanging;
- `FuseInspect` (−28.8, 38.8, 118), `Muzzle` (35, 40, 112);
- **reported:** its handle reaches 14 cm past the bench's front edge and 12 cm past the proposed proxy. It stays at
  least 10 cm from the standing torso. With a horizontal weapon, nothing else on this bench keeps the fuse in reach
  without covering the shells' work.

**State meshes:**
- `SM_B09_ShellCore`: 4.8 cm, with its fuse stub.
- `SM_B09_ShellWrapped`: 5.4 cm. Its gathered paper is a solid bunch, with the twine drawn into it. As an open skirt
  it showed its back through the one-sided paper material.

**Proxy:** 74 × 124 × 75 cm.

## 5. The hanging output (rafters)

- **The poles:** four bamboo drying poles (⌀ 4 cm) at Y −560, −820, −1080 and −1340.
  - They span X 1795–2305, inside the walls' inner faces.
  - They sit at Z 395, hung by cords from the ceiling (its underside at 430).
- **The hooks:** ten per pole, 50 cm apart, giving **40 slots**.
  - Each slot hook is an S: an arc resting on the pole 0.2 mm off, a shank down outside it, and a U.
  - The old hook began inside its pole (72 crossing pairs each).
  - The lantern's ring rests in the U with a 0.5 mm stand-off.
- **Lantern yaw:** each lantern faces +X or −X (90° or 270°, alternating). The ring threads a hook only lying across
  the hook's plane; the earlier free yaw jitter ran rings through hooks.
- **Clearances:** every lantern bottom stays well above a 195 cm head on its floor; neighbours are 20 cm apart.
- **The player's lantern** takes slot 36: pole 4, nearest the oil rack. It hangs there once `Committed[3] == 1`.
- **The fill is root's.**

## 6. Collision and the station trace

- **Every mesh here is visual only.** This follows the dojo kit's pattern: the world builder keeps its boxes as
  collision.
- **The proxies:** each station gets one box under its bench or sled, each under 86 cm. A standing station ray starts
  at 88 cm, so no proxy can block a standing trace from any position.
- **Tested, standing only:** on a 10 cm grid of eligible positions at every station, no standing ray meets a proxy.
- **Crouching:** root's standing-only rule (SOURCE `d52d428c`, Coordinations 257–258) refuses crafting while
  crouched or requesting crouch. `clearance()` still reports a crouched CPU estimate, labelled as one. Native
  collision coverage is root's.
- **The working region and matching proxies are open** (`B09_CRAFT_PAWS.md` §6.3). The proxies here are proposals
  that the next iteration will reshape with the region.
- **Tall parts carry no collision:** the dial, the spindles, the pedestal, the rack's posts, the poles and the lanterns.
- **Root decides,** after its own trace and traversal review. The current generic boxes are not an approved footprint.

## 7. First-person view

The camera is player-controlled. During bend, paste and oil, the director hides the weapon viewmodel, so the view
shows the station's props being worked.

- **The checks** (§4) take the world's 94°, at 16:9 and 21:9, looking at the work from the stand and from the working
  side.
- **They are geometric estimates of framing.** They are not Unreal framing; actual Unreal captures from these
  positions are the next step (§10).
- **No shipped first-person paws work the props.** The pose targets (`b09_craft_poses.py`: `WindPress`, `WindGuide`,
  the seam and stroke paths along the paper, `WrapSpot`, `FuseInspect`) are gated designs only. Paw meshes, rig, keys
  and the craftspeople's animation remain production work.

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

**The candidate masters,** both built by `import_b09_workshop_candidates.py`:
- **`M_B09_PropCandidate`** serves every opaque slot. It takes albedo × Tint, the normal map, and ORM (AO, roughness
  × RoughnessScale, metallic × MetallicScale), all at UV0 × UVScale. UV0 is in metres and follows each part's
  construction (`box_uv`):
  - along a strip, so bamboo grain runs with it;
  - round a turned part, so paper fibre and wood grain wrap it;
  - a box projection only on boxes.
  So each slot's UVScale is 100 / its tile.
- **`M_B09_WashiCandidate`** is two-sided foliage, with the fibre contrast stretched and the oil darkening,
  glossing and passing light.

s147 bound these slots to the furred character's `M_Nyaakoto_PBR`, and its timber to `wood_planks_dirt` (a
weathered plank scan) tiled once a metre against a 2 m scan. Root's s148 review read that as broad blurry mottling.

| Slot | Use | Source (in the tree) | Tile |
|---|---|---|---|
| `M_B09_TimberBench` | benches, rack, cradles, posts, brush handles | planed wood, the cargo stack's original procedural maps | 100 cm |
| `M_B09_TimberForm` | the form, its base and pedestal | the yari's procedural ash wood, lightened toward a planed hinoki | 50 cm |
| `M_B09_Bamboo` | hoops, strips, poles | Poly Haven `bamboo_veneer` (CC0), its grain along each strip | 40 cm |
| `M_B09_Washi` | gores and sheets; paste and oil read UV1 | `paper_0017`. **Measured transmission is required** (chapter-03 §5) | 30 cm |
| `M_B09_RimLacquer` | rims | the yari's procedural black urushi | 30 cm |
| `M_B09_Iron` | bail, hooks, the needle's hub | the yari's procedural patinated iron | 30 cm |
| `M_B09_Bristle`, `M_B09_Cord`, `M_B09_Twine` | brushes, cords, twine | the cargo stack's procedural straw | 6–10 cm |
| `M_B09_Ceramic` | paste pot, oil jar, drip tray | a dark glaze (a tint on neutral maps) | — |
| `M_B09_GaugeFace`, `M_B09_GaugeBand`, `M_B09_GaugeMarks`, `M_B09_GaugeNeedle` | the dial: cream face, green band, dark ticks, vermilion needle | tints on neutral maps | — |
| `M_B09_ShellPaper`, `M_B09_ShellCore`, `M_B09_FuseCord` | shells and fuse | tints on neutral maps | — |

The yari's sets and the cargo maps are project-authored procedural maps with art-estimated values, not measured
scans.

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

## 11. The engine pass (s144–s148, 2026-10-27) and what it exposed

Root returned the full lane (Coordination 234); the sequence was posted first and bounded (two reruns). Every run's
log, outputs and failure are kept.

| Run | Job | Result |
|---|---|---|
| s144 | Blender build | **failed.** It exported one asset, then removing the exported objects left stale view-layer entries. The one file passes the host gate. |
| s145 | Blender rebuild (rerun 1) | **passed.** 54 assets; `check_b09_candidates_fbx.py` found no problems, and root's frozen rerun matched (d262a6c3). |
| s146 | Unreal import | **failed.** Python cannot read `StaticMesh.Sockets`. Its partial assets stay under `/Game/Generated/Candidates/B09Workshop`. |
| s147 | Unreal import (rerun 2, the last) | **failed its exact triangle contract.** Unreal's build dropped 128 pole slivers from each shell, and the failure stands. Every other check passed. `review_b09_import_readback.py` explains the loss exactly; root reproduced it. |
| s148 | Unreal capture | **diagnostic capture of the failed candidate.** 15 socket-pose captures at 94°. Its host check passed. |

**What s148 shows** (socket poses in candidate materials under review light; not hand contact, not acceptance):
- From the stand, the dial (band and needle) sits in frame at 16:9 and 21:9, and it shows from both approach
  positions.
- The seam and oil states and the shell bench read.
- Root's review rejects the production look:
  - the strong orange cast of 1900 K lamps without white balance;
  - flat yellow paper with little readable fibre or wetness;
  - blurry wood and faceting;
  - the hoop/paper clash.

**Fixed since, on the CPU:**
- **Poles:** a revolve that meets the axis now ends in one vertex and a fan. A short-edge gate keeps every
  triangle Unreal's build would drop out of the candidates (no two corners within 2e-5 cm; no edge under 1e-3 cm).
- **The strips:**
  - Their lapped ends are scarfed to half thickness, so a closed hoop stays within its own 0.16 cm.
  - The outward hook tip is gone; the form's notches hold the hoops.
  - The washi rests on the ribs, `PAPER_GAP` outside each strip's outer face.
  - A triangle-exact gate holds every strip at least 0.04 cm under the paper; the measured least is 0.052 cm.
- **The gores** are sampled 48 × 32, plus every strip's edges, against the faceting.
- **The ray and proxy proof is labelled standing-only (§6).**

**The corrected pass** (Coordination 240) rebuilds, reimports and recaptures with these fixes and the new materials
(§9), each run in a new folder.
- **Two light sets.** The editor's white balance stays at 6500 K, because no working script sets it.
  - **neutral:** 6500 K lamps, exposure as metered, to judge material colour.
  - **night:** the intended oil-lamp look: about 2200 K, as a tungsten-balanced camera (about 3400 K) shows it. That
    is a 160-mired warm shift, so 3200 K lamps, with exposure 0.7 EV under metered.
- **A per-channel clipping gate** in `check_b09_review_captures.py`: no channel clipped over 2% of a frame. Under it,
  s148's `paste_halfseam` (7.3% red) would have failed.

**Still open:**
- **Neutral material colour and the intended night lighting,** reviewed separately.
- **Paper fibre, wetness and translucency:** measured transmission is required.
- **Wood resolution.**
- **The form's notches.**
- **Authored craft paws and arm poses with believable contact,** at the world's 94° projection. The 70° viewmodel
  cannot be used uncorrected at world contact points.
- **Action presentation** for the press-committed steps.
- **A rebuild and recapture,** in a later lane window.

## 12. The CPU repair pass after s154 (2026-10-27, Coordinations 241–261)

**New gates, all CPU and triangle-exact:**
- **The prop-clash gate** (`b09_prop_clash.py`) tests every station's states and the rafters. No prop may cross or
  contain another, and every resting prop must sit on its support within 1.2 mm.
  - Its crossing test runs twice, jiggled each way, so grid-aligned boxes cannot hide a crossing.
  - The real weapon 7 mesh is read from its FBX.
  - It found the rims through the paper and the form, the rims' rests through the pot and the sheet stack, the bail's
    ring through its hook, the slot hooks through their poles, the shells sunk into a solid rack, overlapping cores,
    the split strip across the gauge's foot, the gauge's post under the needle, the brushes through their rims, and
    weapon 7's real rope inside its cradle.
  - It records the state before repair in `Saved/Qualification/2026-10-27/b09-craft-gates/prop-clash-before.json`.
- **The closed/outward check** now keeps the intentionally open surfaces apart (`OPEN_SURFACES` in
  `check_b09_candidates_fbx.py`): only the washi gores, on the two-sided washi master.
  - It fixed the gauge's sectors (no ends, wound inward), the dish bracket's ring, the shell's neck and twine, and
    the edge-to-edge scarf runs and split-strip halves.
- **The same-stand pose gate** is described in `B09_CRAFT_PAWS.md`.
- **The view repair** is in `B09_CRAFT_PAWS.md` §6.1.

**Still open, as failures:**
- **The bottom-mouth contact sample** (`B09_CRAFT_PAWS.md` §6.1). Its 1.4 cm bristle convention is a design candidate
  until the bristles' real footprint is shown reaching the rim, wetness coverage is physical, and the view gate
  follows that contact (Coordination 261).
- **The working region and its matching proxies** (`B09_CRAFT_PAWS.md` §6.3).
- **The oil front stroke's bottom socket**, hidden under the lower bulge (`OPEN_VIEW_DEFECTS`).
- **Two reported overhangs:** the paste lantern's front and weapon 7's handle.
