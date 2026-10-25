# The drawn yumi and the reticle: a whole-stave study

**Status:** CPU and source only (2026-10-25), done while root held the
engine lane. Nothing here is captured, admitted or a contract change.

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

| nock, cm right of the eye | bow in the disc | bow clearance, half-heights |
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

## The physical reading, an open question for root

It depends on where the first-person eye point is. The code does not say.

- **The eye point is between the eyes:** the right pupil is about 3.2 cm
  right of it. A nock 6.0 cm right is then about 2.8 cm right of the right
  pupil, 4.5 cm below it and 5.8 cm behind it. The shaft passes about 2.7 cm
  right of the pupil at the eye plane: beside the cheekbone, on an anchor
  drawn back along the cheek toward the ear. That is plausible.
- **The eye point is the right eye itself:** 6 cm further right is past the
  cheek. The cant variant (5 cm, 10°, 1.5 cm lower) is then the closer
  compromise.
- **Kyudo's own aim** lets the bow cover part of the target, the stave just
  left of the line of sight. That is what right_cheek's capture shows. So a
  clear reticle is a stylisation for play, and the authentic form intrudes.

## What would confirm it

**A capture with the lane returned,** with the exit hand-off and the run-up
candidate in place:
`holds=right_cheek,right_cheek_clear,...`, with IDs.
- `right_cheek_clear` is solved from the posed sockets by `cheek_hold`
  (`render_yumi_fp_review.py`), under the same solve gate as right_cheek.
- Its ID pass must show 0 pixels of every part in the disc. The analysis
  then records it beside the sockets' math.
- The fur run-up comparison (`runup=4` against `runup=auto`, in separate
  output directories, `fur_capture_noise.py --compare`) can share that lane
  time.

**Tests:**
- `test_yumi_fp_raster`: the camera, disc and clip; the CPU rig against the
  review's nock; right_cheek's intrusion; the candidate's clearance by at
  least 5 px.
- `test_yumi_fp_holds.CheekHold`: the construction, the cant's direction,
  and the study's candidate from the committed sockets.
