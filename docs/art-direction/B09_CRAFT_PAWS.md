# b09 craft paws: projection, reach and contact (CPU design, for root's decisions)

Root's integration audit makes the authored craft paws, arm poses and believable hand-tool contact Claude's work
(`Saved/Qualification/2026-10-27/b09-integration-review.json`). The presenter, state and collision stay root's.

**Status: a CPU design proposal.**
- No paw is built, posed or imported, and nothing is adopted.
- The station props it reads are b09's candidates (`B09_WORKSHOP_CRAFT.md`, spec `b3222418`).

**Source of truth:**
- `scripts/art/b09_craft_reach.py`, tested by `scripts/art/test_b09_craft_reach.py`.
- `b09_workshop_craft.py`, which supplies the sockets, paths and proxies.

## 1. Projection: world-space paws at the world's 94°

**The decision:** the craft paws are world-space parts, drawn at the world's 94° in the same depth buffer as the
props they touch. They are not 70° first-person primitives.
- **The 70° primitive doesn't line up.** The hero's camera draws the world at 94° and first-person primitives at 70°
  (`SoraPlayerCharacter.cpp`).
  - A primitive drawn at 70° appears tan 47° / tan 35° = **1.53 times** larger on screen than the same point at 94°.
  - A paw point 12 cm right and 25 cm ahead of the eye lands about **228 px** from its world contact at 1920 wide.
- **No correction helps here.**
  - `FirstPersonScale` (0.6) moves geometry along the view rays only, so it changes nothing on screen.
  - Root's `TransformFirstPersonToWorld` corrects a direction (the drawn bow's arrow), not a contact point.
  - Correcting a primitive to meet a world point would squash it 0.65× across the view: a visibly distorted paw.
- **World-space parts meet their props exactly,** and their contact can be gated triangle-exactly
  (`mesh_clearance.py`), as the props' own clearances are.
- **What it costs:** world-space paws can clip into world geometry, so every craft pose needs a clearance gate
  against its station's props. That is the same kind of gate as the b09 strip/paper clearance.

## 2. Reach: the hero can't reach the work as laid out

**The hero** (Unreal cm):
- the standing eye is at the capsule's centre + (4, 0, 64), with capsule radius 34 and half-height 88;
- the shoulders are (−4, ±27.7, −24.5) from the eye (production body, `runtime_skin_manifest.json`);
- upper arm 29.05 cm and forearm 25.00 cm, so reach is at most 98 % of shoulder to wrist: **52.97 cm**.

**Stands.** The stand nearest the work is the capsule touching the front of the station's proposed proxy: x −66, −71,
−72 and −71 at the four stations. The framing stand of the first-person checks is at −80.

**From the nearest stand, no station's contacts are within reach.** Shortfalls against 52.97 cm:

| Station | Required contacts | Short by |
|---|---|---|
| rib form | the strip held to the form, and guided, at each hoop's front | up to 9.0 cm (hoop 1, lowest) |
| rib form | today's two-ended bend: the strip's ends at flex 0.25–1 | 31–43 cm. The ends pass behind the form (reported) |
| paste bench | the brush along seam 1, `Seam1_0..8` | 2.3 cm in the middle, 11–13 cm at the ends |
| paste bench | the rims' seats, at the lantern's top and bottom | up to 22.1 cm |
| oil rack | the brush along `OilStroke0_0..8` | 3.2 cm in the middle, up to 13.8 cm at the ends |
| shell bench | cores, wrap spot, shell seats, fuse inspection | 19–36 cm |

The rests and stock at the backs of the benches are 18–62 cm short. They are reported, since a presentation could
stage them nearer.

**Why.** The 34 cm capsule holds the shoulder about 36 cm behind a bench's front edge. A 75 cm bench top lies 52.5 cm
below the 127.5 cm shoulder. So a 53 cm arm can't reach even the bench's front edge, and the work must come forward
and up to chest height.
- **Stretched first-person arms would need about 92 cm** to reach the shell bench's fuse, 1.7× the anatomical arm.
  That isn't credible.
- **A body lean** would move the first-person camera, and root keeps the camera player-controlled.

## 3. Proposed layout changes (root's decision)

**The smallest moves of each station's whole work group** that bring every required contact within reach, with
3 cm to spare (`layout_shift`; the proxies stay as proposed):

| Station | Toward the hero | Up | Notes |
|---|---|---|---|
| rib form | 15 cm | 0 | With a **one-ended winding** (below). Today's two-ended bend can't be reached from in front at any shift. |
| paste bench | 28 cm | 0 | The lantern's centre comes to x −28, over the bench's front edge (−35) on the turntable's pedestal. The rims' seats set the shift. |
| oil rack | 19 cm | 0 | The hook comes forward on an arm from the rack's bar. |
| shell bench | 40 cm | 11 cm | A rigid move leaves the bench. Instead, the work goes to the bench's front edge, raised: a wrapping tray on a block about 11 cm high, and weapon 7 brought forward with its fuse toward the hero. |

**The one-ended winding** replaces today's two-ended bend (`hoop_path`), which carries both of the strip's ends round
the form at once:
- the strip's end hooks into the form's notch, which the form's boards gain (notches, §11 of the workshop doc);
- the form turns on its spindle as the strip winds on, 385° over the bend;
- the left paw presses the wound strip to the form at the front, and the right paw guides the free strip in.
- Both paws stay at the form's front for every hoop. With the 15 cm move, every hoop is in reach.
- Root's bend contract is unchanged: `HeldStep == 0`, with `HeldMs` setting `flex_stage`. The form's turn is
  presentation, derived from the same flex.

**A layout move touches the first-person checks** (`first_person()`): the dial's band, the seam and the strokes must
stay in frame and clear of the paws. The CPU checks are rerun for any layout root accepts.

## 4. The craft actions and their contacts

Each pose is a paw target: the palm centre, palm normal and finger direction in the station frame. The pads on the
part are gated triangle-exactly: in contact within 0.1 mm to 1.2 mm, never through it. That is the yumi paw's
convention: a 1.2 mm squeeze, carved back to a 0.15 mm gap.

| Step (root's FView) | Left paw | Right paw | Driven by |
|---|---|---|---|
| bend ×6 (`HeldStep 0`, `HeldMs`) | presses the wound strip to the form at the front | guides the free strip; at a split, lets go | `flex_stage(HeldMs)`; the split strip lies at `SplitStripRest` for `FailedStripAgeMs` |
| paste ×4 (`HeldStep 1`, `HeldMs`) | flat on the panel beside the seam, holding it | the paste brush up seam n+1, `Seam{n+1}_0..8`, bottom to top | `HeldMs / 1500` |
| rims ×1 (a press) | the bottom rim onto its seat | the top rim onto its seat | **needs a short action clip:** root's state commits on the press |
| oil ×1 (`HeldStep 3`, `HeldMs`) | steadies the lantern at its bottom rim | the oil brush down the front stroke, `OilStroke0_0..8` | `HeldMs / 1500` |
| shells ×3 (presses) | holds the core in the paper | wraps, twists the neck, ties, then seats it on the rack | **needs a short action clip** |
| inspect ×1 (a press) | steadies weapon 7 | the pad of the index digit on the fuse (`FuseInspect`) | **needs a short action clip** |

**The press-committed steps.** Rims, shells and inspection have no hold to drive their poses. Root's audit already
names the need: a read-only last-action serial and age in the view (as `FailedStripSerial` and `FailedStripAgeMs` are
for the split), so a clip of about 0.6–1.2 s plays after the press. The clip would delay and duplicate no
accounting.

## 5. Decisions for root

1. **World-space craft paws at 94° (§1),** with a clearance gate per pose.
2. **The layout moves (§3)**, or another arrangement that meets the same reach.
3. **The one-ended winding** for the bend's presentation.
4. **A last-action serial and age** in `SoraWorkshopCraftRules::FView` for the press steps.

## 6. Next, once root decides

- **The layout:** move the work groups, add the form's notches and the turning form, then rerun every CPU gate. The
  gates cover reach, the paper and strip clearances, first person and the short edges.
- **The paws:** a craft paw pair from the production anatomy (`nyaakoto_fp_paws.py`: pads, digits, dewclaw).
  - It would use a rig like the bokuto viewmodel's 15 bones (forearm, wrist, four digits and thumb per paw).
  - Each pose is two-bone IK from the shoulders, gated for reach (98 %), pad contact and clearance against the
    station's props.
- **The poses,** keyed per action phase, with contact checked at each key.
- **Then** an Unreal capture of the paws at the stands, in its own bounded sequence.

The craftspeople's animation stays open.
