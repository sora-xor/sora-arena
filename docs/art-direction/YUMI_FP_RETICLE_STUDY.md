# The drawn yumi and the reticle: a whole-stave study

**Status:** a CPU and source study (2026-10-25), then confirmed in capture
v4's ID pass (two runs, `Saved/YumiFP/v4_runup_auto` and `v4_runup_4`).
It is a capture and pose diagnostic: not art acceptance, an admission or a
contract change.

- **Not changed:** root's `viewmodels.json`, the runtime pose contract and
  the 0.12 disc.
- **Added:** a candidate hold, `right_cheek_clear`, in
  `data/yumi_fp_hold_study.json`. A capture can take it as a review hold.

## The problem

Capture v3 (`Saved/YumiFP/v3`, a run that failed at exit after its marker)
showed that the sockets' clear line is not enough. Its line clears the
reticle's 0.12 radius in both aiming holds, yet the stave covers the disc:

| hold | the line, half-heights | bow pixels in the 13,200-pixel disc |
| --- | --- | --- |
| root (the control) | 0.187 | 1,330 (10.1 %) |
| right_cheek | 0.219 | 4,956 (37.5 %) |

The line is a socket line. The stave has width, and the string bends round
the nock.

## The CPU model (`scripts/art/yumi_fp_raster.py`)

**What it rasterises:**
- the bow, as the rig's own skinned mesh at full draw (`yumi_draw.skinned`,
  string included);
- the committed arrow, nocked at the posed Grip_R and laid through the
  Muzzle;
- the bow paw's skin and kote, at a 2 mm step in the Grip_L frame.

**How:** each part is placed as `yumi_fp_holds` places sockets, clipped at
the 10 cm near plane, projected with the capture's 70° 16:9 eye camera, and
rasterised at 1920 x 1080 with whole-pixel coverage.

**Validated against capture v3's ID images:**

| hold | bow in the disc, rasterised / captured | union of all parts, IoU | pixels, rasterised / captured |
| --- | --- | --- | --- |
| rest | 0 / 0 | 0.972 | 179,966 / 178,921 |
| root | 1,309 / 1,330 | 0.983 | 145,286 / 144,444 |
| right_cheek | 5,025 / 4,956 | 0.987 | 156,279 / 155,463 |

- The posed Grip_R matches the capture's to 1e-4 cm.
- **Per part the overlap is lower:** bow IoU 0.90 to 0.91, paw 0.73 to
  0.95. The CPU counts each part alone, so a part hidden behind another
  still counts, while an ID image shows only the front one.
  - In `right_cheek`, 84 % of the bow pixels the CPU adds are where the
    capture shows the paw. In `rest`, 66 % are where it shows the arrow.
  - Only 3 % to 5 % fall on the background.
  - Nothing overlaps in the disc, so there the two agree within 1.6 %.
- **Evidence:** `Saved/W18Rebuild/s14_raster_validation_v3.json`.

## The search

**The family of holds:** the right_cheek construction
(`yumi_fp_holds.cheek_hold`). The posed nock is put on a target, the arrow
line goes through the aim point (2000, 0, 0) cm, and an optional cant turns
the bow about that line. The aim is exact in every hold: the worst miss is
6e-14 cm.

The sweep covered 462 holds (`Saved/W18Rebuild/s14_hold_sweep.json`), with
the nock at the control's depth, -5.77 cm:
- lateral +3 to +8 cm;
- height -8 to -3 cm;
- cant -15° to +15°.

**What clears the disc is the nock's lateral offset.** With the nock height
and depth at right_cheek's, and no cant:

| nock, cm right of the viewpoint | bow in the disc | bow clearance, half-heights |
| --- | --- | --- |
| 3.11 (right_cheek) | 5,025 | 0.020 |
| 4.0 | 2,793 | 0.057 |
| 5.0 | 636 | 0.097 |
| 5.5 | 26 | 0.118 |
| **6.0 (right_cheek_clear)** | **0** | **0.138** |
| 6.5 | 0 | 0.158 |

- Each centimetre right moves the stave about 0.04 half-heights away from the
  centre.
- Height barely matters without a cant.
- **A cant helps only one way.** Tilting the bow's top to the archer's right
  helps, and more with a lower nock. With 10° and the nock 1.5 cm lower, it
  clears from 5.0 cm right (clearance 0.136). Tilting the top left makes it
  worse.

## The candidates

| | right_cheek_clear (in the study) | the cant variant |
| --- | --- | --- |
| nock target, cm | (-5.77, **6.0**, -4.49) | (-5.77, 5.0, -6.0) |
| cant, top to the right | 0° | 10° |
| bow / arrow / paw clearance, half-heights | 0.138 / 0.259 / 0.280 | 0.136 / 0.271 / 0.297 |
| margin over 0.12 | 0.018 (about 10 px) | 0.016 (about 8 px) |
| Grip_L (the bow hand), cm | (60.0, 4.3, -9.6) | (60.0, 2.5, -10.7) |
| arrow behind the near plane | 23.6 % (as right_cheek) | 23.6 % |

**`right_cheek_clear` is right_cheek with one change,** its nock 2.9 cm
further right. No cant is needed, so it is the smaller departure. Both
candidates lie right of root's left-side Grip_L and Muzzle boxes, as
right_cheek does. That is recorded, not relaxed.

## The viewpoint

**Root's reading (2026-10-25):** the study uses one centred virtual
viewpoint.
- The player's `Eye` component sits at (4, 0, 64) cm on the capsule
  (`SoraPlayerCharacter.cpp:247`, `StandingEyeZ`), on its centre line.
- The review camera stands for it, at the eye-space origin.
- So "right of the eye" in this study means right of that centre line.
  right_cheek_clear's full-draw nock is 6.0 cm right of it, 4.5 cm below it
  and 5.8 cm behind it. right_cheek's, the control's mirrored, is 3.11 cm
  right.

**What this study does not establish:** whether that anchor fits the cat
hero's anatomy. No human eye spacing or pupil position is used for it. The
hero's head, cheek and eyes are its own, and a draw anchor for them is a
character question that this visual study cannot settle.

**Kyudo's own aim** lets the bow cover part of the target, the stave just
left of the line of sight. That is what right_cheek's capture shows. So a
clear reticle is a stylisation for play, and the authentic form intrudes.

## Capture v4: the ID pass confirms it

**The runs:** two runs at `e56651a`, identical but for the HighResShot
run-up, with `holds=rest,root,right_cheek,right_cheek_clear,paw`, IDs on,
at 1920 x 1080.
- Each editor exited by itself: editor 0, wrapper 0.
- Root authenticated both runs independently.
- `right_cheek_clear` was solved from the posed sockets, under the same
  solve gate as right_cheek. It came within 1.1e-6 cm and 4.4e-5° of the
  study's anchor and rotation.

**No part is in the disc, in either run:**

| hold | bow in the disc: CPU / runup=auto / runup=4 | captured clearance, half-heights: bow / arrow / paw |
| --- | --- | --- |
| rest | 0 / 0 / 0 | 0.860 / 0.143 / 0.855 |
| root (the control) | 1,309 / 1,330 / 1,333 | 0.082 / 0.164 / 0.198 to 0.199 |
| right_cheek | 5,025 / 4,956 / 4,951 | 0.021 / 0.196 / 0.215 to 0.217 |
| **right_cheek_clear** | **0 / 0 / 0** | **0.138 / 0.281 / 0.282** |

- The arrow and paw are not in the disc in any hold.
- **The CPU raster agrees** (`yumi_fp_raster.validate_against_capture`,
  `Saved/W18Rebuild/s19_raster_validation_v4.json`):
  - union IoU 0.973 to 0.987 over the four eye-view holds in both runs;
  - right_cheek_clear's bow clearance is 0.138 both rasterised and captured,
    and its paw's 0.280 against 0.282.
  - Its arrow clears by 0.281 captured against 0.259 rasterised, so the
    raster is conservative there.
- **Not settled by it: the art.** Root viewed the same images: the white fur
  stays coarse, blade-like and noisy, and the arrow, fletching and wraps
  read as procedural. The fur run-up comparison of the same two runs is in
  `render_yumi_fp_review.highres_runup`.

**Tests:**
- `test_yumi_fp_raster`:
  - the camera, the disc and the clip;
  - the CPU rig against the review's nock;
  - right_cheek's intrusion, and the candidate's clearance by at least 5 px;
  - validate_against_capture on a synthetic run painted from the raster's
    own masks, and its refusal of an ID image whose bytes are not the
    manifest's.
- `test_yumi_fp_holds.CheekHold`: the construction, the cant's direction,
  and the study's candidate from the committed sockets.
