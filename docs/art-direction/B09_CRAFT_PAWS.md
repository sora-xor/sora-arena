# b09 craft paws: projection, same-stand poses, contact and view (CPU design, for root's decisions)

Root's integration audit makes the authored craft paws, arm poses and believable hand-tool contact Claude's
(`Saved/Qualification/2026-10-27/b09-integration-review.json`). The presenter, state and collision stay root's.

**Status: a signed CPU work in progress, not an admission.**
- No paw is built, posed or imported, and nothing is adopted.
- The gates below pass where stated. The open items (§6) are failures, kept as expected failures in the tests; they
  are not accepted exceptions.

**Source of truth:**
- `scripts/art/b09_craft_poses.py` (the same-stand pose gate), tested by `test_b09_craft_poses.py`;
- `scripts/art/b09_prop_clash.py` (props through props, and supports), tested by `test_b09_prop_clash.py`;
- `b09_workshop_craft.py`, which supplies the layout, sockets and proxies.

The first reach study (`b09_craft_reach.py`, in `3c6b3f70`) let every contact choose its own stand and sometimes its
paw. Root's correction (Coordination 241) retired it: both paws and every sample of an action must work from one
stand.

## 1. Projection: world-space paws at the world's 94°

**The decision (root, Coordination 241):** the craft paws are world-space parts, drawn at the world's 94° in the same
depth buffer as the props they touch. They are not 70° first-person primitives.
- A primitive drawn at 70° appears tan 47° / tan 35° = 1.53 times larger on screen than the same point at 94°. A paw
  point 12 cm right and 25 cm ahead of the eye would land about 228 px from its world contact at 1920 wide.
- `FirstPersonScale` and `TransformFirstPersonToWorld` do not correct a contact point.
- World-space parts meet their props exactly, and their contact is gated triangle-exactly, as below.

## 2. The hero and the paw

| | |
|---|---|
| Standing eye | capsule centre + (4, 0, 64); capsule radius 34, half-height 88 (`SoraPlayerCharacter.cpp`) |
| Shoulders | (−4, ±27.7, −24.5) from the eye (`runtime_skin_manifest.json`) |
| Arm | upper arm 29.05 cm, forearm 25.00 cm; reach at most 98 % of shoulder to wrist |
| Paw (`nyaakoto_fp_paws.py`) | the carpus 4.1 cm behind the knuckle line; palm half-thickness 1.05 cm; the metacarpal pad under the knuckles |
| Sleeve (kote) | the upper arm a 4.5 cm tube; the forearm a cone from 3.8 cm at the elbow to 3.0 cm at the cuff, 2 cm short of the wrist |

The earlier study put the wrist 6 cm behind the palm. That understated the reach by about 2 cm; the shell bench was
then at 100.1–100.9 % of the arm, and its work moved 4–5 cm toward the hero and up 4 cm.

**Targets follow the part:**
- **press:** the pads flat on a surface, along its own normal. The rib form's press tilts with the profile, which
  slopes 0.26 at the end hoops.
- **grip:** round a strip, a rim's edge or a paper's edge.
- **claw:** a small part taken from above. The palm is clear of the core's fuse stub (5.45 cm over its centre) or the
  wrapped shell's tied neck (7.35 cm), and the digits reach down round it.
- **brush:** held as a pencil is. The digits pinch it 6 cm up from the bristles; the handle is 35° from the fingers.
  As a dagger grip, it bent the wrist 80°.

## 3. The gate: one stand, both paws, every sample

**The stand** is the craft stand: the capsule 1 cm clear of the station's proposed proxy, facing +X.

**Every sample** of every phase and transition, for both paws, is checked against:
- **reach:** two-bone IK at most 98 %;
- **elbow:** flexion at most 145°, and the elbow outside the torso;
- **wrist:** at most 75° from the forearm;
- **clearance, triangle-exact:** the sleeves 0.5 cm from every prop; the palm 0.5 cm from the parts it does not work,
  and never into those it works; the two arms 0.5 cm apart;
- **continuity:** the elbow moves at most 5 cm between samples.

Each phase keeps one elbow swivel. A transition turns it from the phase before to the phase after. Where that fails a
gate, the elbow swings out of the way and back smoothly, by a swivel of b · sin(πu).

**The props are those each phase shows:**
- **the rib form,** turned for the hoops wound, with the next hoop at the flex stage of the sample's HeldMs;
- **the shell bench,** with its cores and seated shells as the clip has them;
- **weapon 7,** as its real LOD0 mesh: the rope, the fibre cards and the cord included.

**Result (current bytes; rerun on the signed bytes):** every action passes at every station.

| Station | Highest reach | Highest wrist | Least clearance | Largest elbow step |
|---|---|---|---|---|
| rib form (6 hoops) | 88.7 % | 58.8° | 1.73 cm | 3.9 cm |
| paste bench (paste, rims) | 88.2 % | 64.7° | 0.74 cm | 2.7 cm |
| oil rack | 89.5 % | 65.1° | 2.33 cm | 2.2 cm |
| shell bench (3 shells, inspection) | 94.5 % | 52.9° | 0.73 cm | 3.7 cm |

The inspection needs a 30° elbow swing to clear weapon 7's overhanging handle.

**Findings kept as evidence** (`Saved/Qualification/2026-10-27/b09-craft-gates/`):
- **The first every-sample run failed the inspection:** the elbow jumped 14.8 cm. A per-sample swivel repair caused
  it; the smooth swivel replaced it. The run is `pose-gate-every-sample-first-run.json`.
- **The pose gate before the clearance repairs** is `pose-gate-before.json`.

## 4. The craft actions

| Step | Left paw | Right paw | Driven by |
|---|---|---|---|
| bend ×6 | steadies the form at its front-left, then presses the wound strip, fingers along it | takes a strip from the quiver, hooks its end, slides to the guide, guides it in | `flex_stage(HeldMs)`; the form turns `wind_deg` × (n + flex) |
| paste ×4 | takes a sheet by its near edge, then holds the panel at 245° | dips the brush in the pot, then brushes up the seam along the paper's own profile | `HeldMs / 1500` |
| rims ×1 (clip ≤ 1200 ms) | steadies the frame | sets the top rim on the top mouth; the bottom rim is on the frame from the start | `LastAction` |
| oil ×1 | steadies the lantern at 245° | dips in the dish, then oils down the front | `HeldMs / 1500` |
| shells ×3 (clips ≤ 1200 ms) | holds the shell on the paper, then seats it by its neck | takes the core, then twists the neck | `LastAction` |
| inspect ×1 (clip ≤ 900 ms) | keeps the third shell seated | the index pad on the fuse | `LastAction` |

## 5. The standing-only contract (proposed to root, 05:10 UTC; root's SOURCE `d52d428c` implements 1–3)

1. **Admission:** refuse the craft input unless the hero is standing (not IsCrouched and not bWantsToCrouch) and at
   a working stand. A working stand is inside the station's working region (§6.3), facing +X within its yaw band.
2. **Cancellation:** a crouch request, or leaving the region or the yaw band, cancels a held step at once, with no
   unit. The hands are freed, and a release plus a fresh press is needed. Completed units stay.
3. **Press clips:** a press is refused unless admissible. If the stance becomes invalid during a clip, the credit
   stands, the presenter ends the clip at once and consumes its serial, and nothing replays.
4. **The presenter** never stretches an arm, moves the camera or player, or delays accounting.

**Crouch** fails reach at every station, at 105–192 % of the arm, so no crouched craft pose exists.

## 6. Open: not passing

### 6.1 Active contact at the bottom mouth (both aspects)

**The view repair:**
- the paste lantern is lowered to 110 and the oil lantern to 116;
- the holds move to 245°;
- the bottom rim is fitted to the frame before the paper;
- the strokes follow the paper's own profile. Chords between the seam sockets had cut up to 0.56 cm inside the washi.

**Measured** from the craft stand at the natural look, samples in frame and unoccluded:
- the paste stroke and the oil stroke: 33 of 34 at 16:9 and at 21:9;
- the rim clip: 2 of 2 at both aspects.

The paste seam is whole at 21:9.

**The one sample left** in each stroke is the brush tip exactly at the bottom mouth, under the lantern's lower bulge
from a standing eye. The oil front stroke's bottom socket (`OilStroke0_8`) is hidden for the same reason.

**Proposed convention (root to accept or reject):** the tip's contact stops 1.4 cm above the bottom mouth. The flat
brush's bristles (6 cm paste, 5 cm oil) cover the rim line, and the reveal and wetness still reach the rim per root's
contract. With it every sample is visible. Until root accepts, it stays open.

### 6.2 The original view failures (kept)

Before the repair, from the craft stand:
- **paste:** the seam spanned 55.5° of height against 21:9's 45.4°, and active contact was 23–24 of 34;
- **rims:** the clip was 0 of 2, occluded;
- **oil:** active contact was 29–33 of 34.

### 6.3 The working region (root's Coordination 259)

The admitted stands must include the natural stop reached by walking against the proxy, with practical depth, lateral
room and yaw. Walking moves 8.4–11 cm per 60 Hz frame and 16.8–22 cm at 30 Hz.

**Today it fails.** On a grid to 22 cm deep, ±15 cm lateral and ±15° yaw, 1–10 of 90 stands pass per station:
- the depth at the centre is at most 4 cm;
- the shell bench passes only at its contact stand.

**Proposed target, for root to confirm:** 22 cm deep, ±15 cm, ±15°, tested at the region's corners, edges and
centre and through every intervening pose.

**The repair:** bring each station's work within reach of the whole region, and set its matching proxy so that the
natural stop lies inside the region with the body still clear of the bench. The capsule's 34 cm radius keeps the
shoulders far from a bench whose proxy is at its front edge. This is the next CPU iteration. Its bounds, origins and
axes, yaw band and proxies will come together in the signed spec.

## 7. What comes after root decides

- **The paws:** a craft paw pair from the production anatomy (`nyaakoto_fp_paws.py`).
  - It would use a rig like the bokuto viewmodel's 15 bones.
  - Its poses would be keyed from these targets, and gated again triangle-exactly with the real meshes.
- **Then** an Unreal capture of the paws at the stands, in its own bounded sequence.
