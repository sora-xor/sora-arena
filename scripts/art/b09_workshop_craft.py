"""The chapter-03 b09 lantern workshop's craft assets, proposed on the CPU: parts, bounds, pivots, sockets, states and
pose clearances for root's integration. Root owns state, accounting and collision; this module owns the art's shape.

**Inputs** (root's tree at INPUTS["root_commit"], each file pinned by its git blob in INPUTS):
- **The four stations and their floors:** SoraLanternWorkshopRules.h.
  - Stations: rib form (2100, -620), paste bench (2100, -950), oil rack (2100, -1300), all on the 45 cm plank floor;
    shell bench (2790, -2050), in the yard under the storehouse's west eaves.
  - Steps by station: 0, 1, 1, 2, 3, 3.
- **The six steps** (chapter_03.json ch03.b09):
  1. bend x6: 800 ms release, +-160 ms;
  2. paste x4: 1.5 s holds;
  3. assemble the top and bottom rims (1);
  4. paste perilla oil (1);
  5. assemble x3 shells;
  6. inspect the fuse (1).
  Output: 40 lanterns, the whole workshop's night of work.
- **Working a station** (SoraCampaignWorkshopCraft.cpp, SoraCampaignReach.h, SoraCharacterBase.cpp):
  - feet within 8 cm of the station's floor, within 260 cm (2D);
  - a Visibility trace from the capsule's centre (floor + 88 cm; capsule radius 34, half-height 88) to the station
    point at floor + 110 cm;
  - the standing eye at the capsule's centre + (4, 0, 64) cm (SoraPlayerCharacter.cpp).
- **Weapon 7** (build_record.json): an 84 cm bamboo tube with a 5.6 cm bore in a 7.6 cm culm. Its mesh runs from
  -20 to +64 cm along its bore (X), and its muzzle is at +64. Fuse socket (0.2, -1.2, 6.0) cm in Unreal axes.
- **History** (chapter-03.md 4.3): separate hoops (輪骨) hooked onto a form, perilla oil (荏油), and simple hanging
  lanterns for 1623.

**Frames.** Unreal centimetres: X, Y, Z with Z up, and Unreal's left-handed axes. A station's frame has its origin at
the station point on its floor, (X, Y, FloorAt(X, Y)), and the world's axes (yaw 0). That is where the world builder's
Floor() puts its bench today. The hero works each station from its west side, facing +X. The craftspeople (X 2250)
face back across the benches.

**The lantern** (lantern frame: origin at its centre):
- a barrel 44 cm tall and 30 cm across, with 18 cm openings: a superellipse profile, exponent LANTERN_P;
- six bamboo hoops (輪骨), evenly spaced between the rims;
- four washi gores, each a quarter of the round plus 4 deg of overlap at each seam;
- top and bottom rims (口輪) and an iron bail.
At the rib form and paste bench its centre sits at the station point (floor + 110). It hangs at the same height on the
oil rack, and from the drying poles in the rafters.

**Collision.** Every mesh here is visual only. Root keeps or replaces the world builder's boxes, which this module
proposes as COLLISION proxies:
- each is under 86 cm, below the 88 cm start of every station ray, so no proxy can block a station's Visibility trace;
- the taller parts carry no collision (rack posts, form spindle, gauge, poles, lanterns).

**What this module gives** (all deterministic):
- meshes (numpy), with per-vertex attributes for root's material progress;
- sockets, with optional X and Z axes;
- the state each view field drives;
- AABB bounds;
- clearance checks: the hero at each work stand, the eye's line to the work, every eligible station ray against the
  proxies, the hanging lanterns against the hero's head, the shells against the bore;
- spec(), the JSON proposal: docs/art-direction/data/b09_workshop_craft_spec.json;
- previews: a CPU shaded rasteriser and a plan, presentation only.

Run (host, /usr/bin/python3: numpy and PIL):
  /usr/bin/python3 scripts/art/b09_workshop_craft.py --spec docs/art-direction/data/b09_workshop_craft_spec.json
  /usr/bin/python3 scripts/art/b09_workshop_craft.py --previews <new folder>
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# --- Root's inputs, pinned ----------------------------------------------------------------------------------------------
INPUTS = {
    # Re-pinned from c1f0b5af to root's 2a846a6a: two files changed, both additively. SoraWorkshopCraftRules.h gained
    # FView; SoraCampaignWorkshopCraft.cpp gained WorkshopCraftView() and the failed-strip bookkeeping. The timing,
    # eligibility and station trace are unchanged. SoraWorldBuilder.h carries FSoraKitView::LanternCraft.
    # Re-pinned to fcf3ffb5 (Coordination 239): of these files only chapter_03.json changed, for b10's ground routes
    # in ch03_lantern_ward. The ch03.b09 beat is identical.
    # Re-pinned to 102c18d9 (Coordination 240). SoraLanternWorkshopRules.h shortens the east yard wall to end at
    # Y -400, opening the main street; SOLIDS follows it. SoraWorldBuilder.h gives Lanterns a notice-square argument.
    # The stations, recipe, state and eligibility are unchanged.
    # Re-pinned to 541c61ae (Coordinations 242, 243 and 248), the full diff from 102c18d9 read. Four files changed,
    # all additively. SoraWorkshopCraftRules.h adds ActionPresentationMs = 1200 and FView.LastAction (FAction: Serial,
    # Step, Unit, AgeMs). SoraCampaignWorkshopCraft.cpp records it on each credited unit. SoraWorldBuilder.h adds the
    # station marks. SoraPlayerCharacter.cpp stops crouching on a ladder. The timing, eligibility, trace, stations,
    # recipe, capsule and eye are unchanged. The action contract (workshop-action-view.md) is pinned with them.
    # Re-pinned to c096eb98 (Coordination 256), its diff from 541c61ae read: of these files only
    # SoraPlayerCharacter.cpp changed, refusing the guard and taking up an arm while the hands are stowed. The eye and
    # every b09 contract are unchanged.
    # Re-pinned to 5b45dc86 (Coordination 265), its diff from c096eb98 read: root's standing-only rule.
    # AtWorkshopStation refuses IsCrouched and bWantsToCrouch (SoraCampaignWorkshopCraft.cpp); a crouch press cancels
    # workshop craft before the capsule lowers (SoraPlayerCharacter.cpp); the action contract adds the standing
    # requirement and the presenter's serial consumption. The eye, capsule, timing, stations and recipe are unchanged.
    # Re-pinned to 1b6dfadc (Coordination 271), the full diff from 5b45dc86 read. Two pinned files changed.
    # SoraPlayerCharacter.cpp loads the control profile only if its save slot exists. The action contract records
    # Coordinations 268 and 269: physical sheet placement, the contact-driven oil finish, a supported tilting cradle,
    # and the 15 cm / +-10 cm / +-10 deg prototype region. The eye, capsule, crouch, timing, stations and recipe are
    # unchanged.
    # Re-pinned to b6ba3c11 (Coordination 276), its diff from 1b6dfadc read: none of these files changed (eight
    # scripts/docs paths outside them did).
    "root_commit": "b6ba3c111abf088124d758ef195b8a47e85ed8ca",
    "blobs": {
        "Source/SoraArena/Public/SoraLanternWorkshopRules.h": "c7aa71efafc72ecfdd085f67bedbdf84899c4b51",
        "Source/SoraArena/Public/SoraWorkshopCraftRules.h": "132697936dcd8676fe0a2657990265ea264d089e",
        "Source/SoraArena/Public/SoraWorldBuilder.h": "d844f7e305bb8769d884accd6e6b15dd36207e45",
        "Source/SoraArena/Private/Game/SoraCampaignReach.h": "96ede9639f397714300be52c4a0b5e5b2520418f",
        "Source/SoraArena/Private/Game/SoraCampaignWorkshopCraft.cpp": "e213d66377966ae8c2c95301909453cc58543718",
        "Source/SoraArena/Private/Characters/SoraCharacterBase.cpp": "3221fa817a15e57d94f0426b202409e8d56289b2",
        "Source/SoraArena/Private/Characters/SoraPlayerCharacter.cpp": "b64a1c4460df55d1072bf2bd5770d395ad1a1c4b",
        "docs/art-direction/workshop-action-view.md": "b55c8def0fb595cff5a9df36c1d3a7b8c7d730a8",
        "docs/campaign/chapter-03.md": "4141dcc335b4ecf24e9d3ad626b55f1325f3647d",
        "Content/Data/campaign/chapter_03.json": "75874ff583570026946b889c31e075dcedd07e79",
        "Content/SourceArt/Weapons/Runtime/W07_GrenadeLauncher/build_record.json": "95f796814125b324f8a5325a92c2b537307d502b",
    },
}
STATIONS = (("st_b09_rib_form", (2100.0, -620.0)), ("st_b09_paste_bench", (2100.0, -950.0)),
            ("st_b09_oil_rack", (2100.0, -1300.0)), ("st_b09_shell_bench", (2790.0, -2050.0)))
STEP_STATIONS = (0, 1, 1, 2, 3, 3)
STEPS = (("bend", 6), ("paste", 4), ("assemble", 1), ("paste", 1), ("assemble", 3), ("inspect", 1))
BEND_MS, BEND_TOL_MS, PASTE_MS = 800, 160, 1500
ACTION_PRESENTATION_MS = 1200                # FView.LastAction.AgeMs saturates here: every press clip ends by it
OUTPUT_LANTERNS = 40
REACH_CM = 260.0
FEET_TOL_CM = 8.0
CAPSULE_R, CAPSULE_HALF = 34.0, 88.0
EYE = (4.0, 0.0, 64.0)                       # from the capsule's centre, in the hero's facing frame
RAY_FROM_Z, RAY_TO_Z = 88.0, 110.0           # the station trace: capsule centre -> station point (above the floor)
# Standing only. AtWorkshopStation starts the trace at the actor's centre and does not forbid crouching, and a crouched
# capsule's half-height is 44 cm (root, Coordination 236). The ray and proxy proof below covers the standing capsule;
# crouched and native coverage are root's. clearance() reports a crouched CPU estimate, labelled as one.
CROUCH_HALF = 44.0
HEAD_TOP_CM = 195.0                          # feet to ear tips, a conservative head clearance for hanging work
# The hero's camera draws the world at 94 deg (horizontal, held at every aspect). 70 deg is its first-person field of
# view, for first-person primitives (the viewmodel) only (SoraPlayerCharacter.cpp). The props here are world meshes.
WORLD_HFOV_DEG = 94.0
ASPECTS = {"16:9": 16 / 9, "21:9": 21 / 9}    # 21:9 keeps 94 deg across and loses height: the stress case
CEILING_Z = 430.0                            # the room's ceiling underside (the 20 cm slab at z 440)
WEAPON7 = {"bore_cm": 5.6, "culm_cm": 7.6, "x_range_cm": (-20.0, 64.0), "half_width_cm": 6.11,
           "z_range_cm": (-11.54, 6.81), "muzzle_cm": (64.0, 0.0, 0.0), "fuse_cm": (0.2, -1.2, 6.0),
           # Measured on SM_Weapon_07.fbx (LOD0, sha ce7a08f7): the oak plug's collar and the bare bamboo at the muzzle
           # are clean cylinders, (x from, x to, radius) cm. Between them the straw rope (nawa) wraps the culm to about
           # 4.3 cm with loose fibre cards to 6.2, and a fuse cord hangs to -11.5 at x 54-60. The cradle holds the two
           # clean cylinders.
           "collar_cm": (-2.0, 0.0, 4.02), "muzzle_bare_cm": (60.4, 64.0, 3.80), "handle_end_r_cm": 2.12,
           "fbx": "Content/SourceArt/Weapons/Runtime/W07_GrenadeLauncher/SM_Weapon_07.fbx"}


def floor_at(x, y):
    """SoraLanternWorkshopRules::FloorAt."""
    if 1780 <= x <= 2320 and -1500 <= y <= -400:
        return 45.0
    if (1710 <= x < 1780 and -1494 <= y <= -406) or (1830 <= x <= 1970 and -1570 <= y < -1500):
        return 22.5
    return 0.0


def _solids():
    """SoraLanternWorkshopRules::Solids, as (centre, size) boxes in world cm (the ground slab left out).
    check_b09_root_inputs.py compares them, box by box, with the pinned header."""
    b = [(2050, -950, 22.5, 540, 1100, 45), (1745, -950, 11.25, 70, 1088, 22.5), (1900, -1535, 11.25, 140, 70, 22.5),
         (1600, -950, 215, 12, 1100, 430), (2320, -950, 215, 12, 1100, 430), (1960, -400, 215, 720, 12, 430),
         (1715, -1500, 215, 230, 12, 430), (2145, -1500, 215, 350, 12, 430), (1900, -1500, 345, 140, 12, 170),
         (1960, -950, 440, 750, 1130, 20), (2860, -650, 210, 1080, 500, 420),
         (1600, -1850, 100, 12, 700, 200), (1755, -2200, 100, 310, 12, 200), (2495, -2200, 100, 810, 12, 200),
         (3400, -1375, 80, 12, 450, 160), (3700, -1450, 100, 12, 2100, 200)]
    for s in (-1, 1):
        b += [(2600 + s * 65, -1400, 40, 30, 160, 80), (2600, -1400 + s * 65, 40, 100, 30, 80)]
    b += [(3400, -1900, 319, 16, 600, 638), (3150, -1600, 319, 500, 16, 638), (3150, -2200, 319, 500, 16, 638),
          (2900, -2095, 319, 16, 210, 638), (2900, -1705, 319, 16, 210, 638), (2900, -1900, 444, 16, 180, 388),
          (3050, -1900, 644, 700, 640, 12)]
    return [(np.array(c[:3], float), np.array(c[3:], float)) for c in b]


SOLIDS = _solids()
# Each box's ESurface in the header (Wood unless named): the yard's east wall, the well curb and the storehouse are
# Stone.
SOLID_SURFACES = ["Wood"] * 15 + ["Stone"] * 5 + ["Stone"] * 6 + ["Wood"]
FLOOR_SLABS = (0, 1, 2)                     # the plank floor and its two steps: walked on, not walls

# --- The lantern ----------------------------------------------------------------------------------------------------
LANTERN_H, LANTERN_R, LANTERN_RIM_R, LANTERN_P = 44.0, 15.0, 9.0, 2.2
WORK_Z = 110.0                               # the station point's height above its floor (the trace's target)
# The lantern's centre at each lantern station. At 110, the station point's height, the lower shoulder of a seam or
# stroke hides behind the lantern's belly from standing eye height (152). At 130, chest height, the front seam shows
# in full (first_person()). The rib form keeps 110, where every hoop shows.
# The paste and oil lanterns stand below the eye (Coordination 252, 257): from the craft stand a lantern whose top is at
# eye height spans 55 deg of height, more than 21:9's 45.4 deg, so the brush's contact left the frame. At 110 and 116
# every stroke sample but the one at the bottom mouth is in frame and unoccluded at 16:9 and 21:9 (b09_craft_poses
# .contact_view); the paste's left hold and the oil's steady move to 245 deg for the wrist.
LANTERN_Z = {0: 127.0, 1: 110.0, 2: 114.0}
# The craft layout (Coordination 241): each station's work comes toward the hero (-X), so both paws reach the whole
# continuous action from one supported stand (b09_craft_poses.py). The rib form also rises to 120, so its lowest hoop
# is in reach (it was 110). The paste bench's 27.5 keeps its pedestal on the bench. The shell bench's work instead
# stands on a raised stand at its front edge (station_parts).
WORK_SHIFT = {0: 28.5, 1: 27.5, 2: 29.0}
# The working region's layouts (Coordinations 259, 268, 269, 271; b09_craft_region.py). From every admitted stand, 15 cm
# deep, +-10 cm and +-10 deg, a paw's contact must lie 18-30 cm ahead of the natural stop's axis (24-30 below 130 cm
# high) at z 112-144; a brush tip 24-36 cm ahead at z 104-144 (the body, the far corners' reach and 21:9's height). So
# each station's work comes to the front of its proxy, on supports, and its matching proxy has a notch.
NOTCH = {"depth_cm": 10.0, "half_cm": 28.1, "post_cm": 8.0}
OIL_PROXY_FRONT = -36.0                      # the rack's proxy face (station x); the natural stop is CAPSULE_R before it
RIB_BENCH = (62.0, 100.0, 75.0)              # the rib form bench: depth, width, top
# The paste bench: its frame lies on a tilting spindle cradle (Coordination 268), rolled toward the hero's left and
# pitched toward the hero, so a whole seam, rim line to rim line, lies inside the region's reach and 21:9's height.
# No supported posture passed 15/10/10 (the searches in Saved/Qualification/2026-10-27/b09-craft-region); this one
# passes the paste's own 10/10/10 region (b09_craft_region.REGION_BY_STATION).
PASTE_PROXY_FRONT = -37.0
# The paste frame on its cradle (paste_vis2, Saved/Qualification/2026-10-27/b09-craft-region): its axis rolled -65 deg
# about +X (the top to the hero's right) and pitched 55 deg (the top away), the worked seam turned -50 deg about the
# axis so it faces up toward the hero, and the laid gore wrapping from it toward the hero's left and up, where the eye
# sees the left paw's hold. Pitched toward the hero (PASTE_FIRST_POSE) the frame's lower half and the gore faced away
# and the hold was hidden at every stand (view 0 of 198); of 27,648 frames round this pose, 21 pass the search's
# visibility, reach and framing at 10/10/10 and none at 12/10/10 or 15/10/10 (the brush's reach to the seam's far end:
# 98.9 and 102.6 % at their best).
PASTE_FIRST_POSE = {"centre": (40.5, 0.0, 112.0), "roll_deg": 45.0, "pitch_deg": -15.0, "seam_turn_deg": -15.0,
                    "hold_turn_deg": 40.0, "hold_s_cm": 8.0}                          # for the record
PASTE = {"centre": (42.5, 4.0, 112.0),       # the frame's centre: ahead of the natural stop, lateral, height
         "roll_deg": -65.0, "pitch_deg": 55.0, "seam_turn_deg": -50.0,
         "hold_turn_deg": -58.8, "hold_s_cm": -10.0,     # the hold on the laid gore: 0.6 of its 98 deg round, 10 cm down its axis
         "dip": (30.0, 29.0, 101.0),
         # The sheets hang lengthwise from a rail running away from the hero, the near end of each toward the paw: hung
         # by their height they passed through the frame's lower end, and further left left the frame of view from the
         # near left stand turned right.
         "rack_y": -16.6, "rail_top": 151.0, "sheet_near_u": 27.0,
         "rim_rest": (66.0, -24.0, 156.0),   # the top rim lies on a shelf of the left standard (the rims step re-tilts the frame)
         "stroke_up": True,                  # the seam is brushed from the lower rim line (the frame's bottom mouth) up
         "square": 0.5, "square_cm": 4.0,    # the bristle edge turned halfway square to each rim line, relaxing over square_cm
         "stroke_tilt": 0.2,
         "rim_steady": (160.0, 0.0)}         # the right paw's fingertips on the frame while the left seats the rim


def _frame_cols(z):
    """A rotation (columns) taking a local frame's Z to z."""
    z = np.asarray(z, float) / np.linalg.norm(z)
    x = np.cross([0.0, 1.0, 0.0], z) if abs(z[1]) < 0.9 else np.cross([1.0, 0.0, 0.0], z)
    x /= np.linalg.norm(x)
    return np.stack([x, np.cross(z, x), z], 1)


PASTE_BRUSH_W = 6.0                          # the paste brush's flat bristles


def flat_sheet(name):
    """A pre-cut washi gore before it is laid: flat, in its own frame (X across its width, Z up its height, its near
    edge's middle at the origin), each height's width the gore's arc there (90 + 2 x GORE_OVERLAP_DEG of paper_r)."""
    zs = np.linspace(-LANTERN_H / 2, LANTERN_H / 2, 23)
    w = np.radians(90.0 + 2 * GORE_OVERLAP_DEG) * paper_r(zs)
    wmax = float(w.max())
    v, t = [], []
    for k, (z, wk) in enumerate(zip(zs, w)):
        x0_ = (wmax - wk) / 2.0
        v += [[x0_, 0.0, z], [x0_ + wk, 0.0, z], [x0_, 0.05, z], [x0_ + wk, 0.05, z]]
        if k:
            a_, b_ = 4 * (k - 1), 4 * k
            t += [[a_, b_, a_ + 1], [a_ + 1, b_, b_ + 1], [a_ + 2, a_ + 3, b_ + 2], [a_ + 3, b_ + 3, b_ + 2],
                  [a_, a_ + 2, b_], [a_ + 2, b_ + 2, b_], [a_ + 1, b_ + 1, a_ + 3], [a_ + 3, b_ + 1, b_ + 3]]
    n = len(zs) - 1
    t += [[0, 1, 2], [1, 3, 2], [4 * n, 4 * n + 2, 4 * n + 1], [4 * n + 1, 4 * n + 2, 4 * n + 3]]
    return Mesh(name, np.array(v, float), np.array(t), "M_B09_Washi")


def paste_axes():
    """The paste frame's axes in the station frame (columns: the lantern frame's X, Y, Z): Z the frame's axis, from the
    bottom mouth to the top; the lantern frame's -X (azimuth 180, its seam 1) toward the worked seam, d. The frame
    turns about its axis by -90 deg per pasted panel, so each next seam comes to d."""
    al, be, ph = (math.radians(PASTE[k]) for k in ("roll_deg", "pitch_deg", "seam_turn_deg"))
    rx = np.array([[1, 0, 0], [0, math.cos(al), -math.sin(al)], [0, math.sin(al), math.cos(al)]])
    ry = np.array([[math.cos(be), 0, math.sin(be)], [0, 1, 0], [-math.sin(be), 0, math.cos(be)]])
    a = ry @ rx @ np.array([0.0, 0.0, 1.0])
    d0 = np.array([-1.0, 0.0, 0.0]) - (-a[0]) * a
    d0 /= np.linalg.norm(d0)
    b0 = np.cross(a, d0)
    d = math.cos(ph) * d0 - math.sin(ph) * b0
    return np.stack([-d, np.cross(d, a), a], 1)


# The gores go on in this order, the frame turning +90 deg about its axis per panel, so each laid gore wraps from the
# worked seam toward the hero's left and its leading edge meets the gore before it at the seam (panel_turn_deg).
PASTE_ORDER = (1, 4, 3, 2)


def panel_turn_deg(panel):
    """The frame's turn about its axis while panel `panel` (1..4) is laid: gore PASTE_ORDER[panel - 1] spans cradle
    azimuth 86..184 deg, from the seam (180) toward the hero's left."""
    return 90.0 * (panel - 2)


def paste_frame(points, panel=None):
    """Lantern-frame points placed on the paste cradle (station frame): as the frame stands while panel `panel` is laid,
    or, with no panel, in the cradle's own frame (the worked seam at azimuth 180, which the frame turns under)."""
    rz = np.eye(3) if panel is None else _rot_z(panel_turn_deg(panel))
    x0 = PASTE_PROXY_FRONT - CAPSULE_R
    c = np.array(PASTE["centre"]) + [x0, 0.0, 0.0]
    return np.asarray(points, float) @ (paste_axes() @ rz).T + c
RIB_PROXY_FRONT = -32.0
RIB = {"form_ahead_cm": 37.5, "form_z": 127.0,
       "press_az_deg": 192.0,                # the left paw on the wound strip (at 200 the far stands bent its wrist to 88 deg)
       "steady_az_deg": 203.0,               # the left paw steadying the form while the right hooks the strip
       "carry_out_cm": 1.5, "carry_lift_cm": 6.0,    # the carry lifts the strip this far toward the form and up first,
       "carry_bow_cm": 5.0,                  # and comes onto the notch from this far on the hero's side
       "wait_off_cm": 1.0,                   # the left paw waits this far off the form while the right hooks the strip,
       "wait_toward_middle": 0.3,            # and this far from the hoop's height toward the form's middle
       "look_down_deg": 0.0,                 # the look point below the contacts' vertical middle (look_point_for)
       "guide_cm": 3.0,                      # the guiding paw on the free strip, this far along it (at 3.5 its knuckles left
                                             # the 21:9 frame's right edge from the near stands turned left)
       "grip_off_cm": 1.8,                   # the hooking and guiding knuckles off the strip, the digits curled round it
       "leave_az_deg": 180.0,                # where the strip leaves the form (station azimuth), heading off its tangent
       "rack_front": (-37.5, 22.0, 125.0)}   # the strips' ends (station x, y) and the rack's arm top
OIL = {"lantern_ahead_cm": 41.0, "lantern_z": 114.0,
       "dish": (36.0, 22.0, 118.0),          # the dip point on the dish's floor: ahead of the natural stop, lateral, height
       "steady_az_deg": 200.0, "steady_s_cm": 12.0, "steady_fingers_deg": 0.0,   # fingertips (b09_craft_poses.steady)
       "carry_lift_cm": -4.0}                # the carry from the dish to the swath's top sags this much at its middle
OIL_SWATH = {"az_deg": 175.0, "s_cm": (22.0, 0.0), "offset_cm": 0.7, "half_width_cm": 2.5, "contact_cm": 1.5,
             "square_cm": 4.0, "square": 1.0,   # the bristle edge square along the rim line, relaxing over 4 cm
             "tilt": 0.1}                        # the stroke's handle lean toward the surface normal
OIL_DISH_R = 6.0                            # the dish's rim radius; it is 1.4 cm deep
OIL_BRUSH_W = 5.0
OIL_DIP_TILT = 0.4                           # the dip's handle lean toward the surface normal (b09_craft_poses.brush)


def look_point_for(points, x0, ahead=26.0, az_deg=None, el_offset_deg=0.0):
    """A station's fixed look point: ahead cm before the natural stop's eye (x0 + EYE), at the vertical and lateral
    angular middle of the work's contacts as that eye sees them (or, with az_deg, on that bearing from the eye: the
    shell bench's is its centre line), el_offset_deg below the vertical middle where the region's near stands need it.
    Root's runtime admission measures the facing band about the bearing to it (Coordination 271); nothing moves it."""
    eye = np.array([x0 + EYE[0], 0.0, CAPSULE_HALF + EYE[2]])
    P_ = np.asarray(points, float)
    el = np.arctan2(P_[:, 2] - eye[2], np.hypot(P_[:, 0] - eye[0], P_[:, 1] - eye[1]))
    az = np.arctan2(P_[:, 1] - eye[1], P_[:, 0] - eye[0])
    e, a = 0.5 * (el.min() + el.max()), 0.5 * (az.min() + az.max())
    if az_deg is not None:
        a = math.radians(az_deg)
    e -= math.radians(el_offset_deg)
    return eye + ahead * np.array([math.cos(a), math.sin(a), 0.0]) + [0.0, 0.0, ahead * math.tan(e)]


def lantern_centre(i):
    """The lantern's (or the rib form's) centre at a lantern station, in the station frame."""
    return np.array([-WORK_SHIFT[i], 0.0, LANTERN_Z[i]])
HOOP_W, HOOP_T = 0.40, 0.16                  # bamboo strip (ひご): width along the lantern's axis, radial thickness
HOOP_LAP_DEG = 25.0                          # the strip's ends overlap by this much at the hook
PAPER_GAP = 0.06                             # washi sits this far outside the hoops
GORE_OVERLAP_DEG = 4.0                       # each gore runs this far past its quarter at each seam
RIM_H, RIM_T = 2.0, 0.8                      # 口輪: height, radial thickness
BAIL_RISE = 9.0                              # the bail's crown above the top rim's upper face
BAIL_RING_R, BAIL_WIRE_R = 0.6, 0.1          # the ring at the crown, across the bail's plane, and its wire
HOOK_WIRE_R, HOOK_BEND_R = 0.35, 0.9         # the rack hook's iron and the radius of its U
HOOK_GAP = 0.05                              # the bail ring's wire over the hook's, within the 1.2 mm contact
SLOT_HOOK_WIRE_R, SLOT_HOOK_BEND_R = 0.18, 0.9   # the rafters' slot hooks
FLEX_STAGES = (0.0, 0.25, 0.5, 0.75, 1.0)


def profile_r(z):
    """The lantern's radius at height z (lantern frame, -22..22)."""
    h = LANTERN_H / 2.0
    s = np.clip(np.abs(np.asarray(z, float)) / h, 0.0, 1.0)
    return LANTERN_RIM_R + (LANTERN_R - LANTERN_RIM_R) * (1.0 - s ** LANTERN_P) ** (1.0 / LANTERN_P)


def hoop_z():
    """The six hoops' heights, evenly spaced between the rims (lantern frame)."""
    h = LANTERN_H / 2.0
    return np.array([-h + LANTERN_H * k / 7.0 for k in range(1, 7)])


def hoop_r():
    return profile_r(hoop_z()) + HOOP_T / 2.0


def hang_point():
    """Where the lantern hangs (lantern frame): the top of its bail's ring, which rests in the rack hook's bend."""
    return np.array([0.0, 0.0, LANTERN_H / 2.0 + RIM_H + BAIL_RISE + 2.0 * BAIL_RING_R])


# --- Meshes ---------------------------------------------------------------------------------------------------------
@dataclass
class Mesh:
    name: str
    verts: np.ndarray
    tris: np.ndarray
    slot: str
    attrs: dict = field(default_factory=dict)
    collision: str = "none (visual only)"
    tri_slots: object = None                 # per-triangle material slots, where a mesh has more than one
    tri_uv0: object = None                   # per-corner UV0 (n_tris, 3, 2) in metres, from its construction (box_uv)

    def slots(self):
        return np.asarray(self.tri_slots, object) if self.tri_slots is not None else np.full(len(self.tris), self.slot, object)

    def moved(self, offset=(0.0, 0.0, 0.0), rot=None, name=None):
        v = self.verts @ np.asarray(rot, float).T if rot is not None else self.verts.copy()
        return Mesh(name or self.name, v + np.asarray(offset, float), self.tris.copy(), self.slot,
                    {k: a.copy() for k, a in self.attrs.items()}, self.collision,
                    None if self.tri_slots is None else np.asarray(self.tri_slots, object).copy(),
                    None if self.tri_uv0 is None else np.asarray(self.tri_uv0, float).copy())

    def bounds(self):
        return self.verts.min(0), self.verts.max(0)


def merge(name, meshes, slot=None):
    """One mesh from several, each triangle keeping its part's material slot (an early version kept only the first
    part's, which turned the gauge's band and ticks into its face)."""
    v, t, ts, off = [], [], [], 0
    for m in meshes:
        v.append(m.verts)
        t.append(m.tris + off)
        ts.append(m.slots())
        off += len(m.verts)
    tri_slots = np.concatenate(ts)
    primary = slot or meshes[0].slot
    uv = None
    if any(m.tri_uv0 is not None for m in meshes):         # each part keeps its own mapping (box parts their projection)
        uv = np.concatenate([np.asarray(box_uv(m), float) for m in meshes])
    return Mesh(name, np.concatenate(v), np.concatenate(t), primary, {}, "none (visual only)",
                None if (tri_slots == primary).all() else tri_slots, uv)


def box(name, lo, hi, slot):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    c = np.array([[x, y, z] for z in (0, 1) for y in (0, 1) for x in (0, 1)], float)
    v = lo + c * (hi - lo)
    t = np.array([[0, 2, 1], [1, 2, 3], [4, 5, 6], [5, 7, 6], [0, 1, 4], [1, 5, 4], [2, 6, 3], [3, 6, 7],
                  [0, 4, 2], [2, 4, 6], [1, 3, 5], [3, 7, 5]])
    return Mesh(name, v, t, slot)


def _frames(path, closed):
    """Rotation-minimising frames along a polyline: (tangents, normals, binormals)."""
    p = np.asarray(path, float)
    d = np.roll(p, -1, 0) - np.roll(p, 1, 0) if closed else np.gradient(p, axis=0)
    tg = d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-12)
    ref = np.array([0.0, 0.0, 1.0]) if abs(tg[0, 2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    n0 = np.cross(tg[0], ref)
    n0 /= np.linalg.norm(n0)
    ns = [n0]
    for k in range(1, len(p)):
        n = ns[-1] - np.dot(ns[-1], tg[k]) * tg[k]
        ns.append(n / max(np.linalg.norm(n), 1e-12))
    ns = np.array(ns)
    return tg, ns, np.cross(tg, ns)


def sweep(name, path, slot, radius=None, rect=None, closed=False, segments=8, up=None):
    """A tube along a polyline: round (radius) or rectangular (rect = (width along `up` or the binormal, thickness
    along the normal)). Open tubes are capped."""
    p = np.asarray(path, float)
    tg, nrm, bin_ = _frames(p, closed)
    if up is not None:                       # a fixed width direction (a strip's width along the lantern's axis)
        bin_ = np.repeat(np.asarray(up, float)[None], len(p), 0)
        nrm = np.cross(bin_, tg)
        nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    if rect is not None:
        w, th = rect
        # (along the normal, along the binormal), counter-clockwise like the round section, so the tube and its caps
        # all face out. Before, the rect ran clockwise and the round tube's faces ran inward: each swept part had
        # mixed winding (found closing the notched form).
        sec = [(-th / 2, -w / 2), (th / 2, -w / 2), (th / 2, w / 2), (-th / 2, w / 2)]
    else:
        sec = [(radius * math.cos(2 * math.pi * k / segments), radius * math.sin(2 * math.pi * k / segments))
               for k in range(segments)]
    m = len(sec)
    v = np.array([p[i] + a * nrm[i] + b * bin_[i] for i in range(len(p)) for a, b in sec])
    rows = len(p) if not closed else len(p) + 1
    # UV0 (m): u is the arc length along the path, v the distance round the section, so grain runs along a strip.
    run = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(np.vstack([p, p[:1]]) if closed else p, axis=0), axis=1))])
    sv = np.concatenate([[0.0], np.cumsum([math.dist(sec[k], sec[(k + 1) % m]) for k in range(m)])])
    t, uv = [], []
    for i in range(rows - 1):
        i0, i1 = i % len(p), (i + 1) % len(p)
        u0, u1 = run[i] / 100.0, run[i + 1] / 100.0
        for k in range(m):
            a, b = i0 * m + k, i0 * m + (k + 1) % m
            c, d = i1 * m + k, i1 * m + (k + 1) % m
            va, vb = sv[k] / 100.0, sv[k + 1] / 100.0
            t += [[a, b, c], [b, d, c]]
            uv += [[(u0, va), (u0, vb), (u1, va)], [(u0, vb), (u1, vb), (u1, va)]]
    if not closed:
        for i0, flip in ((0, True), (len(p) - 1, False)):
            ctr = len(v)
            v = np.vstack([v, p[i0]])
            for k in range(m):
                a, b = i0 * m + k, i0 * m + (k + 1) % m
                ka, kb = (np.asarray(sec[k]) / 100.0, np.asarray(sec[(k + 1) % m]) / 100.0)
                t.append([ctr, b, a] if flip else [ctr, a, b])
                uv.append([(0.0, 0.0), tuple(kb), tuple(ka)] if flip else [(0.0, 0.0), tuple(ka), tuple(kb)])
    return Mesh(name, v, np.array(t), slot, tri_uv0=np.array(uv, float))


def revolve(name, zr, slot, az0=0.0, az1=360.0, n_az=48, cap=False):
    """A surface of revolution about Z from (z, r) samples, azimuths az0..az1 (deg).

    A sample on the axis (r = 0) is a pole: one vertex, met by a fan. A ring stands for it only if Unreal would keep
    the ring's triangles. A 1e-4 cm pole ring has corners 2e-5 cm apart, within THRESH_POINTS_ARE_SAME, so Unreal's
    build dropped 128 slivers from each shell (s147).

    Attributes: height fraction (0 at the lowest sample, 1 at the highest) and azimuth fraction across the patch (0 at
    a pole). (It was once 0 at the first sample and 1 at the last, which runs to 2e12 on a profile that ends where it
    began, as a rim's does.)"""
    zr = np.asarray(zr, float)
    if (zr[:, 1] < 0).any():
        raise ValueError(f"{name}: a negative radius")
    full = abs((az1 - az0) - 360.0) < 1e-9
    cols = n_az if full else n_az + 1
    a = np.radians(az0 + (az1 - az0) * np.arange(cols) / n_az)
    hf_of = (zr[:, 0] - zr[:, 0].min()) / max(np.ptp(zr[:, 0]), 1e-12)
    v, hf, af, first = [], [], [], []
    for i, (z, r) in enumerate(zr):
        first.append(len(v))
        if r == 0.0:                                             # a pole
            v.append([0.0, 0.0, z])
            hf.append(hf_of[i])
            af.append(0.0)
        else:
            v += [[r * math.cos(t), r * math.sin(t), z] for t in a]
            hf += [hf_of[i]] * cols
            af += list(np.arange(cols) / n_az)
    t, uv = [], []
    # UV0 (m): u round the widest radius, v along the profile, so paper fibre and wood grain wrap the part.
    r_ref = max(float(zr[:, 1].max()), 1e-6)
    ua = (az1 - az0) * np.arange(n_az + 1) / n_az * math.pi / 180.0 * r_ref / 100.0
    vrow = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(zr[:, 0]), np.diff(zr[:, 1])))]) / 100.0
    for i in range(len(zr) - 1):
        pole_a, pole_b = zr[i, 1] == 0.0, zr[i + 1, 1] == 0.0
        for j in range(n_az):
            if pole_a and pole_b:
                break
            um = 0.5 * (ua[j] + ua[j + 1])
            if pole_a:                                           # [p, q, r] of the quad, with p = q at the pole: dropped
                t.append([first[i], first[i + 1] + (j + 1) % cols, first[i + 1] + j])
                uv.append([(um, vrow[i]), (ua[j + 1], vrow[i + 1]), (ua[j], vrow[i + 1])])
            elif pole_b:                                         # [q, s, r] of the quad, with s = r at the pole: dropped
                t.append([first[i] + j, first[i] + (j + 1) % cols, first[i + 1]])
                uv.append([(ua[j], vrow[i]), (ua[j + 1], vrow[i]), (um, vrow[i + 1])])
            else:
                p, q = first[i] + j, first[i] + (j + 1) % cols
                r_, s_ = first[i + 1] + j, first[i + 1] + (j + 1) % cols
                t += [[p, q, r_], [q, s_, r_]]
                uv += [[(ua[j], vrow[i]), (ua[j + 1], vrow[i]), (ua[j], vrow[i + 1])],
                       [(ua[j + 1], vrow[i]), (ua[j + 1], vrow[i + 1]), (ua[j], vrow[i + 1])]]
    mesh = Mesh(name, np.array(v, float), np.array(t), slot, {"height_frac": np.array(hf), "azimuth_frac": np.array(af)},
                tri_uv0=np.array(uv, float))
    if cap and full:                                             # close an end ring with a centre vertex
        for i, flip in ((0, True), (len(zr) - 1, False)):
            if zr[i, 1] == 0.0:
                continue
            ctr = len(mesh.verts)
            mesh.verts = np.vstack([mesh.verts, [0.0, 0.0, zr[i, 0]]])
            for k in range(n_az):
                p, q = first[i] + k, first[i] + (k + 1) % cols
                mesh.tris = np.vstack([mesh.tris, [ctr, q, p] if flip else [ctr, p, q]])
                cap = [(0.0, 0.0), tuple(mesh.verts[q][:2] / 100.0), tuple(mesh.verts[p][:2] / 100.0)]   # planar (x, y)
                mesh.tri_uv0 = np.vstack([mesh.tri_uv0, [cap if flip else [cap[0], cap[2], cap[1]]]])
            for key in mesh.attrs:
                mesh.attrs[key] = np.append(mesh.attrs[key], mesh.attrs[key][first[i]])
    return mesh


def sphere(name, r, slot, n=24):
    """A sphere of radius r with true poles (one vertex each, met by a fan)."""
    zr = [(r * math.cos(math.pi * (1 - k / n)), 0.0 if k in (0, n) else r * math.sin(math.pi * k / n)) for k in range(n + 1)]
    return revolve(name, zr, slot, n_az=2 * n)


def brush(name, width, bristle=4.0, handle=18.0):
    """A flat brush (刷毛): its bristles' tip at the origin, the bristles along +Y, then the handle."""
    return merge(name, [box(name, (-width / 2, 0.0, -0.5), (width / 2, bristle, 0.5), "M_B09_Bristle"),
                        box(name, (-1.0, bristle, -0.6), (1.0, bristle + handle, 0.6), "M_B09_TimberBench")])


def bench(name, depth, width, top, slot="M_B09_TimberBench", leg=6.0, thick=4.0):
    """A plain workbench: a top over four legs and two stretchers, origin on the floor at its centre."""
    hx, hy = depth / 2.0, width / 2.0
    parts = [box(name, (-hx, -hy, top - thick), (hx, hy, top), slot)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * (hx - leg), sy * (hy - leg)
            parts.append(box(name, (cx - leg / 2, cy - leg / 2, 0), (cx + leg / 2, cy + leg / 2, top - thick), slot))
    for sy in (-1, 1):
        cy = sy * (hy - leg)
        parts.append(box(name, (-hx + leg, cy - 2, 14), (hx - leg, cy + 2, 19), slot))
    return merge(name, parts, slot)


# --- The lantern's parts (lantern frame) ------------------------------------------------------------------------------
WIND_DEG = 360.0 + HOOP_LAP_DEG              # a hoop's wrap, its lap included


def form_yaw_deg(n, flex=0.0):
    """The rib form's turn (deg, from +X toward +Y) with n hoops wound and the next at flex. Each hoop winds 385 deg
    of turn. The presentation turns the form by it, from root's state: n is Committed[0] and flex is
    flex_stage(HeldMs). The timing and counts are root's, unchanged."""
    return WIND_DEG * (n + flex)


def hoop_hook_deg(k):
    """Where hoop k's end hooks into its notch, in the form's frame. It is at RIB["leave_az_deg"] (station azimuth;
    the front was 180) as the form stands when that hoop starts, after k - 1 hoops."""
    return (RIB["leave_az_deg"] - form_yaw_deg(k - 1)) % 360.0


def hoop_path(k, flex=1.0, segments=192):
    """Strip k's centreline as it winds on, in the FORM's frame: (points, outward normals, arc parameter s, end).

    **One-ended winding** (Coordination 241). The strip's end hooks into the form's notch at hoop_hook_deg(k), and
    the form turns (form_yaw_deg) as the strip winds on. So the strip always leaves the form at station azimuth
    RIB["leave_az_deg"], heading off its tangent toward the hero's right, where the right paw guides it. The left
    paw presses the wound strip to the form just past that point. (Left at the front, 180, the straight strip ran 25
    cm ahead of the hero's chest and met it from the region's right side; at 160 it heads 20 deg away.)
    - s runs from the hooked end (0) to the free end (the strip's length, constant at every flex).
    - flex is the wound share of the 385 deg wrap.
    - end is -1 on the hooked end's scarf and +1 on the free end's, which laps over it when the hoop closes."""
    z, r = hoop_z()[k - 1], hoop_r()[k - 1]
    length = r * math.radians(WIND_DEG)
    lap = r * math.radians(HOOP_LAP_DEG)
    s = np.linspace(0.0, length, segments + 1)
    wound = flex * length
    beta = math.radians(hoop_hook_deg(k))
    pts, nrm = [], []
    for si in s:
        th = beta - min(si, wound) / r                          # clockwise from the hook, in the form's frame
        on = np.array([r * math.cos(th), r * math.sin(th), z])
        if si <= wound:
            pts.append(on)
        else:                                                   # straight on from the point where it leaves the form
            pts.append(on + np.array([math.sin(th), -math.cos(th), 0.0]) * (si - wound))
        nrm.append([math.cos(th), math.sin(th), 0.0])
    end = np.where(s <= lap + 1e-9, -1, np.where(s >= length - lap - 1e-9, 1, 0))
    return np.array(pts), np.array(nrm), s, end


def to_station(points, yaw_deg, centre):
    """Form-frame points turned by the form's yaw about its spindle, then placed at its centre (station frame)."""
    a = math.radians(yaw_deg)
    rz = np.array([[math.cos(a), -math.sin(a), 0.0], [math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0]])
    return np.asarray(points, float) @ rz.T + np.asarray(centre, float)


def hoop(k, flex=1.0, segments=192):
    """Hoop k (1..6) as its strip bends (hoop_path).

    **The ends are scarfed (削ぎ):** each is shaved to half thickness over the lap, the leading end on the outer half
    and the trailing end on the inner half. Closed, the lap is flush within the strip's own thickness, so the washi
    clears it as it clears the rest. s148 showed the earlier lap, the leading end riding a full thickness out, and its
    outward hook tip piercing the paper. The hoops sit in the form boards' notches, so a hoop needs no hook of its
    own (the notches are not modelled)."""
    pts, nrm, s, end = hoop_path(k, flex, segments)
    name = f"SM_B09_Hoop{k}" + ("" if flex >= 1.0 else f"_Flex{int(round(flex * 100)):03d}")
    i_trail = int(np.nonzero(end == -1)[0].max())                # the last sample of the trailing scarf
    i_lead = int(np.nonzero(end == 1)[0].min())                  # the first of the leading scarf
    runs = [(slice(0, i_trail + 1), -1), (slice(i_trail, i_lead + 1), 0), (slice(i_lead, len(s)), 1)]
    parts = []
    for sl, e in runs:
        off = e * HOOP_T / 4                                     # a scarf's centre: a quarter thickness in or out
        th = HOOP_T if e == 0 else HOOP_T / 2 - 2 * SCARF_INSET  # inset, so its edges do not lie on the middle run's
        parts.append(sweep(name, pts[sl] + nrm[sl] * off, "M_B09_Bamboo", rect=(HOOP_W, th), up=(0.0, 0.0, 1.0)))
    return merge(name, parts)


SCARF_INSET = 0.001                          # cm: separate runs never share an edge (the closed check found 4-way edges)


def split_strip(k=6):
    """A failed strip, split lengthwise along 60% of its length and splayed, lying flat (frame: its middle)."""
    r = hoop_r()[k - 1]
    length = r * math.radians(360.0 + HOOP_LAP_DEG)
    n = 40
    halves = []
    for side in (-1, 1):
        pts = []
        for i in range(n + 1):
            x = -length / 2 + length * i / n
            split = max(0.0, (x - (-length / 2 + 0.4 * length)) / (0.6 * length))
            pts.append([x, side * (HOOP_W / 4 + 3.0 * split ** 1.5), HOOP_T / 2 + 0.3 * split * (side + 1)])
        halves.append(sweep("SM_B09_SplitStrip", pts, "M_B09_Bamboo", rect=(HOOP_W / 2 - 2 * SCARF_INSET, HOOP_T), up=(0, 1, 0)))
    return merge("SM_B09_SplitStrip", halves)


RIB_RAMP = 0.6                               # cm: the washi returns from a rib to its profile over this height


def paper_r(z):
    """The washi's radius at height z. It rests on the ribs, as pasted paper does: PAPER_GAP outside a strip's outer
    face wherever a strip lies under it, easing back over RIB_RAMP. Between the ribs it is HOOP_T + PAPER_GAP outside
    the profile.

    A strip's face is upright (its width along the axis), so on the lantern's shoulders, where the profile slopes
    0.26, its narrow-side edge stood outside paper that followed only the profile. s148 showed the end hoops crossing
    it."""
    z = np.asarray(z, float)
    out = profile_r(z) + HOOP_T + PAPER_GAP
    for zk, rk in zip(hoop_z(), hoop_r()):
        over = rk + HOOP_T / 2 + PAPER_GAP                       # PAPER_GAP outside the strip's outer face
        d = np.abs(z - zk) - HOOP_W / 2
        w = np.clip(1.0 - d / RIB_RAMP, 0.0, 1.0)                # 1 over the strip, 0 beyond the ramp
        out = np.maximum(out, out + (over - out) * w)
    return out


def gore(k, n_z=48, n_az=32):
    """Washi gore k (1..4): a quarter of the round plus GORE_OVERLAP_DEG at each seam, resting on the hoops (paper_r).
    It is sampled at every strip's edges and ramp ends, so the paper lies over each strip's full width. Attributes for
    root's paste progress: height_frac (0 at the bottom rim, 1 at the top) and azimuth_frac (0 at its leading seam)."""
    h = LANTERN_H / 2.0
    edges = [zk + sgn * e for zk in hoop_z() for sgn in (-1, 1) for e in (HOOP_W / 2, HOOP_W / 2 + RIB_RAMP)]
    zs = np.unique(np.round(np.concatenate([np.linspace(-h, h, n_z + 1), edges]), 9))
    zr = np.stack([zs, paper_r(zs) + 0.02 * (k - 1)], 1)       # later gores lie over earlier ones
    a0 = 180.0 + 90.0 * (k - 1) - GORE_OVERLAP_DEG
    return revolve(f"SM_B09_Washi{k}", zr, "M_B09_Washi", a0, a0 + 90.0 + 2 * GORE_OVERLAP_DEG, n_az)


def rim(which):
    """A rim (口輪), centred on its own pivot (the ring's centre); it moves between Rim*Rest and Rim*Seat."""
    zc = 0.0
    r_in = LANTERN_RIM_R - RIM_T / 2
    pts = [(zc - RIM_H / 2, r_in), (zc - RIM_H / 2, r_in + RIM_T), (zc + RIM_H / 2, r_in + RIM_T),
           (zc + RIM_H / 2, r_in), (zc - RIM_H / 2, r_in)]
    return revolve(f"SM_B09_Rim{which}", pts, "M_B09_RimLacquer", n_az=96)


def bail():
    """The iron bail: an arc set on the top rim's upper face at the rim's mean radius, rising BAIL_RISE, with a ring at
    its crown across the arc's plane. The rack's hook lies in the arc's plane, so it threads the ring; a ring in the
    hook's own plane would run through it (the clash gate found that, 134 crossing pairs)."""
    h = LANTERN_H / 2.0 + RIM_H                                  # the top rim's upper face (its seat is on the mouth)
    leg = 0.4                                                    # each foot rises straight, so its end sits flat
    pts = ([[LANTERN_RIM_R, 0.0, h]]
           + [[LANTERN_RIM_R * math.cos(t), 0.0, h + leg + (BAIL_RISE - leg) * math.sin(t)] for t in np.linspace(0, math.pi, 25)]
           + [[-LANTERN_RIM_R, 0.0, h]])
    c = h + BAIL_RISE + BAIL_RING_R
    ring = [[0.0, BAIL_RING_R * math.cos(t), c + BAIL_RING_R * math.sin(t)] for t in np.linspace(0, 2 * math.pi, 24, endpoint=False)]
    return merge("SM_B09_Bail", [sweep("SM_B09_Bail", pts, "M_B09_Iron", radius=0.12, segments=10),
                                 sweep("SM_B09_Bail", ring, "M_B09_Iron", radius=BAIL_WIRE_R, closed=True, segments=10)])


NOTCH_D = 0.10                               # a board's edge stands this proud of the hoops' inner faces
NOTCH_CLEAR = 0.03                           # each notch is the strip's width plus this on either side
NOTCH_SEAT = 0.01                            # a notch's bottom lies this under its hoop's inner face: a seat, not a cut


def board_outline(collapsed=False):
    """A form board's outer edge, (r, z) from the bottom up. It stands NOTCH_D proud of the profile, cut down to each
    hoop's inner face across the hoop's width plus NOTCH_CLEAR. The hoops seat in the notches, their inner faces on
    the notch bottoms. Collapsed, the edge folds to 40 % of its reach beyond the spindle, as when the form is drawn
    out of a pasted lantern."""
    h = LANTERN_H / 2.0
    notches = [(zk - HOOP_W / 2 - NOTCH_CLEAR, zk + HOOP_W / 2 + NOTCH_CLEAR, rk - HOOP_T / 2 - NOTCH_SEAT)
               for zk, rk in zip(hoop_z(), hoop_r())]
    zs = sorted(set(np.round(np.linspace(-h, h, 45), 9)) | {round(z, 9) for lo, hi, _ in notches for z in (lo, hi)})
    out = []
    for z in zs:
        proud = float(profile_r(z)) + NOTCH_D
        for lo, hi, bottom in notches:
            if abs(z - lo) < 1e-9:                               # into a notch: the proud edge, then the bottom
                out += [(proud, z), (bottom, z)]
                break
            if abs(z - hi) < 1e-9:                               # out of it
                out += [(bottom, z), (proud, z)]
                break
            if lo < z < hi:
                out.append((bottom, z))
                break
        else:
            out.append((proud, z))
    pts = np.array(out)
    if collapsed:
        pts[:, 0] = 1.3 + 0.4 * (pts[:, 0] - 1.3)
    return pts


def _outward(board, outline, c, s_, n, m):
    """A board's triangles turned to face out of it. Each face knows its outward direction:
    - a side: along the board's thickness;
    - the outer edge: the outline's outward normal in (r, z), notch walls included;
    - the inner edge: toward the spindle;
    - an end: down or up."""
    radial, lat, up = np.array([c, s_, 0.0]), np.array([-s_, c, 0.0]), np.array([0.0, 0.0, 1.0])
    v, t = board.verts, board.tris.copy()
    want = np.zeros((len(t), 3))
    side = lambda k: 0 if k < n + m else 1  # noqa: E731
    local = lambda k: k % (n + m)  # noqa: E731
    for i, tri in enumerate(t):
        sides = {side(k) for k in tri}
        ks = [local(k) for k in tri]
        if len(sides) == 1:                                   # a side face
            want[i] = lat if sides == {1} else -lat
        elif all(k < n for k in ks):                          # the outer edge: two outline points, along it
            k0 = min(ks)
            dr, dz = outline[k0 + 1][0] - outline[k0][0], outline[k0 + 1][1] - outline[k0][1]
            want[i] = dz * radial - dr * up
        elif all(k >= n for k in ks):                         # the inner edge
            want[i] = -radial
        else:                                                 # an end: the outline's first or last point
            want[i] = -up if min(k for k in ks if k < n) == 0 else up
    nrm = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
    flip = (nrm * want).sum(1) < 0
    t[flip] = t[flip][:, [0, 2, 1]]
    board.tris = t
    return board


def form(collapsed=False, boards=8):
    """The collapsible, notched form (型), in its own frame: a spindle, two collars and radial boards. The boards'
    edges carry a notch for each hoop (board_outline). The rib form turns on its spindle as each strip winds on
    (form_yaw_deg)."""
    h = LANTERN_H / 2.0
    parts = [sweep("SM_B09_Form", [[0, 0, -h - 8], [0, 0, h + 16]], "M_B09_TimberForm", radius=1.25, segments=20)]
    for zc in (-h - 1.0, h + 1.0):
        parts.append(revolve("SM_B09_Form", [(zc - 1, 0.0), (zc - 1, 3.0), (zc + 1, 3.0), (zc + 1, 0.0)],
                             "M_B09_TimberForm", n_az=48))
    outline = board_outline(collapsed)
    levels = sorted({round(float(z), 9) for _, z in outline})
    at = {z: [k for k, (_, zz) in enumerate(outline) if abs(zz - z) < 1e-9] for z in levels}
    for b in range(boards):
        th = math.radians(22.5 + 360.0 * b / boards)
        c, s_ = math.cos(th), math.sin(th)
        place = lambda rad, z, side: [rad * c - side * s_, rad * s_ + side * c, z]  # noqa: E731
        v = []
        for side in (-0.4, 0.4):                                  # per side: the outline, then the inner edge's levels
            v += [place(rad, z, side) for rad, z in outline]
            v += [place(1.3, z, side) for z in levels]
        n, m = len(outline), len(levels)
        o = lambda f, k: f * (n + m) + k  # noqa: E731               the outline's k-th point on side f
        inner = lambda f, j: f * (n + m) + n + j  # noqa: E731       the inner edge at level j
        t = []
        for f, flip in ((0, False), (1, True)):                   # each side face, band by band between levels
            for j in range(m - 1):
                lo, hi = at[levels[j]], at[levels[j + 1]]
                exiting = len(lo) == 2 and outline[lo[0]][0] < outline[lo[1]][0]   # bottom, then proud: out of a notch
                entering = len(hi) == 2 and outline[hi[0]][0] > outline[hi[1]][0]  # proud, then bottom: into one
                if exiting and entering:
                    raise ValueError("a band between two notch steps: sample the outline between them")
                if exiting:                                       # share the notch bottom: fan from the upper inner
                    tri = [[inner(f, j + 1), inner(f, j), o(f, lo[0])], [inner(f, j + 1), o(f, lo[0]), o(f, lo[1])],
                           [inner(f, j + 1), o(f, lo[1]), o(f, hi[0])]]
                elif entering:                                    # share the notch bottom: fan from the lower inner
                    tri = [[inner(f, j), o(f, lo[-1]), o(f, hi[0])], [inner(f, j), o(f, hi[0]), o(f, hi[1])],
                           [inner(f, j), o(f, hi[1]), inner(f, j + 1)]]
                else:
                    a_, b_, c_, d = inner(f, j), o(f, lo[-1]), o(f, hi[0]), inner(f, j + 1)
                    tri = [[a_, b_, c_], [a_, c_, d]]
                t += [[x[0], x[2], x[1]] if flip else x for x in tri]
        for k in range(n - 1):                                    # the outer edge, notch walls included
            t += [[o(0, k), o(0, k + 1), o(1, k)], [o(1, k), o(0, k + 1), o(1, k + 1)]]
        for j in range(m - 1):                                    # the inner edge, by the spindle
            t += [[inner(0, j), inner(1, j), inner(0, j + 1)], [inner(1, j), inner(1, j + 1), inner(0, j + 1)]]
        for j, k, flip in ((0, 0, True), (m - 1, n - 1, False)):  # the board's bottom and top ends
            q = [[inner(0, j), o(0, k), inner(1, j)], [o(0, k), o(1, k), inner(1, j)]]
            t += [[x[0], x[2], x[1]] for x in q] if flip else q
        parts.append(_outward(Mesh("SM_B09_Form", np.array(v), np.array(t), "M_B09_TimberForm"), outline, c, s_, n, m))
    return merge("SM_B09_Form" + ("_Collapsed" if collapsed else ""), parts, "M_B09_TimberForm")


def lantern(stage):
    """The lantern at a stage: "frame" (form and six hoops), "papered" (+ four gores), "rimmed" (+ rims), "finished"
    (form drawn out, bail fitted: the oil rack's and the rafters' lantern). Lantern frame."""
    parts = [hoop(k) for k in range(1, 7)]
    if stage in ("frame", "papered", "rimmed"):
        parts.append(form())
    if stage in ("papered", "rimmed", "finished"):
        parts += [gore(k) for k in range(1, 5)]
    if stage in ("rimmed", "finished"):                          # each rim on its mouth, against the paper's edge
        parts += [rim("Top").moved((0.0, 0.0, LANTERN_H / 2 + RIM_H / 2)), rim("Bottom").moved((0.0, 0.0, -LANTERN_H / 2 - RIM_H / 2))]
    if stage == "finished":
        parts.append(bail())
    return parts


# --- Stations -------------------------------------------------------------------------------------------------------
WORK_STAND = (-80.0, 0.0)                    # the earlier framing stand, kept as a reference; the hero works at craft_stand
WORK_OBJECT = {"SM_B09_Form", "SM_B09_FormBase"} | {f"SM_B09_Hoop{k}" for k in range(1, 7)}
# The work the eye's line to the look point may end in (clearance): the shell bench's look point lies at its wrapping
# post's top, under the paper, where the shells are wrapped.
SIGHT_WORK = {3: {"SM_B09_WrapPost", "SM_B09_WrapPaper"}}
# The flex gauge: a dial on a post at the bench's front-left (the hero's left, -Y), its face toward the hero (-X).
# - The one-ended winding's free strip leaves the form toward the hero's right, so it never sweeps the gauge.
# - Its pivot stands at 128, low enough that the whole dial stays in frame from the craft stand at 16:9 and 21:9 (at
#   142 its upper half left the 21:9 frame).
# - The face is cream, the release band green (fixed: the 640-960 ms window), the ticks dark, the needle vermilion.
#   Root's review of v2 (2026-10-26 23:53) found the old gauge, low at the front-left in one colour, partly outside the
#   frame and with no readable band.
# - Angles are measured in the dial's plane from upright (+Z) toward the hero's right (+Y).
# - The needle sweeps the whole half-dial, -90 to +90 deg, over 0-960 ms, so the 640-960 ms release band spans 60 deg
#   (+30 to +90). The band then reads above 2 deg from the far edge of reach; a 40 deg band did not past about 2 m.
# The flex gauge stands on the rib bench's front edge left of the form, its dial facing the hero (scaled 0.7 from the
# first design, which stood at (-19, -34, 128) with a 13.5 cm face: no part of the form's side was clear for it).
GAUGE = {"pivot": (-28.0, -26.0, 127.0), "radius": 7.7, "band_r": (5.6, 8.4), "face_r": 9.5,
         "angles_deg": (-90.0, 90.0), "full_ms": BEND_MS + BEND_TOL_MS, "ticks_ms": (0, 400, 800)}


def dial_point(angle_deg, radius, depth=0.0):
    """A point on the gauge's dial (station frame): its angle from upright toward +Y, its radius, and its depth toward
    the hero (-X) in front of the face."""
    g = np.array(GAUGE["pivot"])
    a = math.radians(angle_deg)
    return g + [-depth, radius * math.sin(a), radius * math.cos(a)]


def _sector(name, r0, r1, a0, a1, depth, thick, slot, n=24):
    """An annular sector of the dial, raised `thick` toward the hero from `depth` in front of the face: a closed solid,
    each face wound to its known outward direction (it had no ends and wound inward: the closed check found it)."""
    v, t = [], []
    angles = np.linspace(a0, a1, n + 1)
    for a in angles:
        for d in (depth, depth + thick):
            for r in (r0, r1):
                v.append(dial_point(a, r, d))
    v = np.array(v)

    def put(quad, out):
        a_, b_, c_, d_ = quad
        for tri in ([a_, b_, c_], [b_, d_, c_]):
            nrm = np.cross(v[tri[1]] - v[tri[0]], v[tri[2]] - v[tri[0]])
            t.append(tri if float(nrm @ out) >= 0.0 else [tri[0], tri[2], tri[1]])

    hero = np.array([-1.0, 0.0, 0.0])
    for i in range(n):
        q = [4 * i + j for j in range(8)]
        am = math.radians((angles[i] + angles[i + 1]) / 2)
        radial = np.array([0.0, math.sin(am), math.cos(am)])
        put((q[0], q[1], q[4], q[5]), -hero)                     # the back
        put((q[2], q[3], q[6], q[7]), hero)                      # the front
        put((q[0], q[2], q[4], q[6]), -radial)                   # the inner edge
        put((q[1], q[3], q[5], q[7]), radial)                    # the outer edge
    for k, sgn in ((0, -1.0), (n, 1.0)):                        # the two ends
        a = math.radians(angles[k])
        put((4 * k, 4 * k + 1, 4 * k + 2, 4 * k + 3), sgn * np.array([0.0, math.cos(a), -math.sin(a)]))
    return Mesh(name, v, np.array(t), slot)


def gauge_mesh(top):
    """The flex gauge (station frame): a foot and post from the bench top, the dial's face (an upper half-disc), the
    scale's dark rim, the green release band, and dark ticks at 0, 400 and 800 ms and at the band's edges."""
    g = np.array(GAUGE["pivot"])
    lo_b, hi_b = GAUGE["band_r"]
    band = (gauge_angle(BEND_MS - BEND_TOL_MS), gauge_angle(BEND_MS + BEND_TOL_MS))
    parts = [box("SM_B09_FlexGauge", (g[0] - 3, g[1] - 4, top), (g[0] + 3, g[1] + 4, top + 1.5), "M_B09_TimberBench"),
             # The post stands behind the face and carries it (it stood 0.8 cm proud of the face, under the needle's hub,
             # and stopped 0.5 cm short of the face's lower edge).
             box("SM_B09_FlexGauge", (g[0] + 0.8, g[1] - 1.2, top + 1.5), (g[0] + 2.4, g[1] + 1.2, g[2] + 4.0), "M_B09_TimberBench"),
             _sector("SM_B09_FlexGauge", 0.05, GAUGE["face_r"], -90.0, 90.0, -0.8, 0.8, "M_B09_GaugeFace", n=96),
             _sector("SM_B09_FlexGauge", hi_b, hi_b + 0.5, *GAUGE["angles_deg"], 0.02, 0.12, "M_B09_GaugeMarks", n=96),
             _sector("SM_B09_FlexGauge", lo_b, hi_b - 2 * SCARF_INSET, *band, 0.02, 0.12, "M_B09_GaugeBand", n=32)]   # off the rim's edge
    for a in sorted({gauge_angle(ms) for ms in GAUGE["ticks_ms"]} | set(band)):
        parts.append(_sector("SM_B09_FlexGauge", lo_b - 0.6, hi_b + 0.5, a - 0.9, a + 0.9, 0.02, 0.16, "M_B09_GaugeMarks", n=2))
    return merge("SM_B09_FlexGauge", parts, "M_B09_GaugeFace")


def gauge_angle(ms):
    """The flex gauge's needle (deg, about its pivot's X axis, 0 upright) at a held bend's elapsed ms."""
    a0, a1 = GAUGE["angles_deg"]
    return a0 + (a1 - a0) * min(max(ms, 0), GAUGE["full_ms"]) / GAUGE["full_ms"]


def flex_stage(ms):
    """The flexing strip's stage (an index into FLEX_STAGES) at a held bend's elapsed ms: fully bent at 800 ms."""
    f = min(max(ms, 0) / BEND_MS, 1.0)
    return int(round(f * (len(FLEX_STAGES) - 1)))


def weapon_rest():
    """Weapon 7, the festival-shell tube the bench's shells are made for (the rack's cups are bored to its bore), standing
    upright in its socket block on the bench behind the board's middle (station frame): its bore up (local +X along +Z),
    the handle end in the block at SHELL_LAYOUT["tube_foot_z"], its touch-hole side (local +Z) toward the hero (-X).

    It is a prop the arms clear, not a contact. Standing at the board's right with its touch-hole fuse 30 cm ahead
    (SHELL_FUSE_FIRST), its handle, holder and culm stood where the right elbow swings when the hero stands near and
    turned left (b09_craft_region: 63 of 72 boundary samples failed), and the measured arm sweep leaves no upright
    column clear of every arm within the far corners' reach: clear columns start 42-44 cm ahead (the middle) or 46 cm
    to the right, and a fuse there is 35 cm or more ahead. The inspection checks the shells' own fuse cords instead."""
    x_axis, z_axis = np.array([0.0, 0.0, 1.0]), np.array([-1.0, 0.0, 0.0])
    y_axis = np.cross(z_axis, x_axis)
    rot = np.stack([x_axis, y_axis, z_axis], 1)
    u, y = SHELL_LAYOUT["tube"]
    return np.array([SHELL_PROXY_FRONT - CAPSULE_R + u, y, SHELL_LAYOUT["tube_foot_z"] - WEAPON7["x_range_cm"][0]]), rot


# The shell bench (Coordinations 241, 269): a board on a stand overhangs the bench's front edge, carrying the shells'
# work in one row 23-31 cm ahead of the natural stop, where both paws reach from the whole region: the rack's three
# cups on the left, the wrapping paper, the core tray, and weapon 7 standing upright on the right, its fuse toward
# the hero. (Its first layout, the stand at the bench's edge and the weapon lying on cradles, was 43-46 cm ahead.)
SHELL_PROXY_FRONT = -37.0
SHELL_LAYOUT = {"board": (23.0, 44.0, -23.5, 15.6), "top": 110.0,      # ahead from/to, lateral from/to, its top face
                # (at 118 the rack's seated shells and the core tray stood in the forearms' way to the wrapping post)
                "paper": (25.0, 33.0, -4.0, 3.5), "wrap": (29.0, -0.25),
                "wrap_post_top": 124.0,              # the paper waits on a wrapping post (at 127 the holding forearm, its palm
                                                     # on the shell's side toward the hero, passed 0-0.5 cm over the sheet)
                "wrap_lift_cm": 7.0,                 # the wrapped shell is lifted this far off the paper to be twisted, in the
                                                     # air: grips at the board's height ran the forearms up through its edge
                "tray": (28.7, 9.5), "tray_r": 5.9, "core_r": 2.85,                # the cores 120 deg apart, clear
                "cup_r": 3.1, "rack_plank_cm": 0.7,
                # a row stepped ahead to the left: the far cup of a triangle was out of reach, and a straight row's left
                # cup stood under the left forearm carrying a shell to the inner two
                "cups": ((26.8, -7.6), (28.0, -13.8), (29.2, -20.0)),
                "coil": (39.0, -2.0),
                "tube": (50.0, 0.0), "tube_foot_z": 74.0}              # weapon 7's axis (ahead, lateral) and its handle end
SHELL_FUSE_FIRST = (30.0, 21.0, 128.0)       # weapon 7's touch-hole fuse as a contact at the board's right, for the record
SHELL_STAND = {"lo": (-35.0, -50.0), "hi": (-12.0, 30.0), "top": 106.0}     # the first layout, kept for the record
SHELL_WEAPON_ORIGIN = (-29.0, 40.0, 112.0)


def v_cradle(name, x0, x1, r, axis_y, axis_z, base, slot="M_B09_TimberBench", gap=0.03):
    """A V-block from x0 to x1 that carries a cylinder of radius r lying along X at (axis_y, axis_z): its faces at 45 deg,
    gap off the cylinder below its axis (so the cylinder's polygon, whose corners lie on its circle, cannot cross
    them), on a post from base. Returns the parts."""
    apex = axis_z - (r + gap) * math.sqrt(2.0)
    top = axis_z - 1.5                                       # the faces stop here, clear of the cylinder above the contact
    half_v = top - apex                                      # the notch's half-width at the top (45 deg faces)
    w = half_v + 1.0
    bottom = apex - 2.0
    sec = [(-w, bottom), (w, bottom), (w, top), (half_v, top), (0.0, apex), (-half_v, top), (-w, top)]   # (y, z), CCW
    ring = len(sec)
    v = [[x, axis_y + y, z] for x in (x0, x1) for y, z in sec]
    t = []
    for k in range(ring):                                    # the sides, facing out (CCW seen from +X)
        a, b = k, (k + 1) % ring
        t += [[a, b, ring + b], [a, ring + b, ring + a]]
    cap = [(0, 1, 4), (1, 3, 4), (1, 2, 3), (0, 4, 5), (0, 5, 6)]   # the section, under and beside the notch
    t += [[c, b_, a_] for a_, b_, c in cap] + [[ring + a_, ring + b_, ring + c] for a_, b_, c in cap]
    block = Mesh(name, np.array(v, float), np.array(t), slot)
    post = box(name, (x0, axis_y - 2.0, base), (x1, axis_y + 2.0, bottom), slot)
    return [block, post]


def _stand(name, lo, hi, top, base, slot="M_B09_TimberBench", leg=3.0):
    """A small stand (a top on four legs) on a surface at height base: its top's upper face at top."""
    (x0, y0), (x1, y1) = lo, hi
    parts = [box(name, (x0, y0, top - 2.0), (x1, y1, top), slot)]
    for x in (x0 + leg / 2, x1 - leg / 2):
        for y in (y0 + leg / 2, y1 - leg / 2):
            parts.append(box(name, (x - leg / 2, y - leg / 2, base), (x + leg / 2, y + leg / 2, top - 2.0), slot))
    return merge(name, parts, slot)


CRAFT_STAND_CLEAR_CM = 1.0


def centre_stop(proxies):
    """The natural stop on a station's centre line: the capsule's axis (station x) where walking along +X at y = 0 first
    meets a proxy, the capsule touching it. The working region's nearest boundary (b09_craft_region.natural_stop)."""
    def hits(x):
        return any(circle_hits_box2d(np.array([x, 0.0]), CAPSULE_R, lo, hi) for lo, hi in proxies
                   if lo[2] < 2 * CAPSULE_HALF and hi[2] > 0.0)
    lo, hi = -400.0, 0.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if not hits(mid) else (lo, mid)
    return lo


def notch(front_x, top, slot="M_B09_TimberBench"):
    """The matching proxy's notch (b09_craft_region): two cheek posts standing NOTCH["depth_cm"] proud of a proxy face
    at station x front_x, their inner faces NOTCH["half_cm"] off the centre line. A capsule walking in slides round a
    cheek's corner and stops at the face within 3.9 cm of the centre line. Returns (the posts' mesh, their proxies);
    each post stands 0.5 cm inside its proxy."""
    d, h, w = NOTCH["depth_cm"], NOTCH["half_cm"], NOTCH["post_cm"]
    posts, prox = [], []
    for sgn in (-1.0, 1.0):
        y0, y1 = sorted((sgn * (h + 0.5), sgn * (h + 0.5 + w)))
        posts.append(box("SM_B09_NotchPost", (front_x - d + 0.5, y0, 0.0), (front_x - d + 0.5 + w, y1, top), slot))
        y0, y1 = sorted((sgn * h, sgn * (h + w + 1.0)))
        prox.append((np.array([front_x - d, y0, 0.0]), np.array([front_x, y1, top])))
    return merge("SM_B09_NotchPost", posts, slot), prox
PASTE_POT = [(108.0, 0.0), (108.0, 5.0), (108.6, 6.0), (114.5, 6.2), (115.0, 5.6), (109.0, 5.3), (109.0, 0.0)]   # (z, r)
OIL_DISH_RIM = (6.5, 7.0)                    # the oil dish's flat rim, inner and outer radius, 0.4 cm over its centre


def _rot_z(deg):
    a = math.radians(deg)
    return np.array([[math.cos(a), -math.sin(a), 0.0], [math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0]])


def brush_in_pot(pot, inset=3.5, gap=0.03, lip=None, floor=None):
    """A brush's rest in a pot or cup: its bristles' tip on the floor, inset cm toward the hero from the axis, leaning
    away from the hero with its handle's underside on the far lip, where the handle's sides cross it (a flat handle on
    a round lip touches at its edges), gap over it (the lip's 48 sides lie up to 0.12 mm inside its circle). lip is
    (z, r) and floor a height; both default to the paste pot's. Returns the socket: the tip, the brush's local X (across
    the bristles) and Z."""
    lip_z, lip_r = PASTE_POT[4] if lip is None else lip
    floor = PASTE_POT[5][0] if floor is None else floor
    half_w, bristle_t, handle_t = 1.0, 0.5, 0.6                 # brush(): the handle's half-width and half-thicknesses
    reach = math.sqrt(lip_r ** 2 - half_w ** 2)                  # the lip under the handle's edges
    th = math.atan2(lip_z - floor, reach + inset)                # a first guess, refined below
    for _ in range(50):
        tip_z = floor + bristle_t * math.cos(th)                 # the tip face's lower edge on the floor
        dx = reach + inset - handle_t * math.sin(th)
        dz = lip_z + gap - tip_z + handle_t * math.cos(th)
        th = math.atan2(dz, dx)
    y_ax = np.array([math.cos(th), 0.0, math.sin(th)])           # along the brush, from the tip
    x_ax = np.array([0.0, 1.0, 0.0])
    z_ax = np.cross(x_ax, y_ax)
    tip = np.array([pot[0] - inset, pot[1], floor + bristle_t * math.cos(th)])
    return (tip, x_ax, z_ax)


def station_parts(i):
    """Each station's meshes in its frame, its sockets {name: (point, x_axis | None, z_axis | None)}, its collision
    proxies [(lo, hi)], and the work point the hero looks at. The work comes to the hero's side of each bench, at
    chest height where the paws work (WORK_SHIFT, Coordination 241). Anything the paws take from stands on a
    supported stand there."""
    sockets, proxies = {}, []
    if i == 0:
        # The rib form (Coordinations 241, 269): the form turns on a spindle whose post stands at the bench's front
        # edge, RIB["form_ahead_cm"] ahead of the natural stop; the strips lie in a rack on the right with their ends
        # toward the hero; the flex gauge stands on the left, its dial in the frame from the whole region.
        lc = lantern_centre(0)
        depth, width, top = RIB_BENCH
        parts = [bench("SM_B09_RibFormBench", depth, width, top)]
        base_top = lc[2] - LANTERN_H / 2 - 8.0                   # the spindle's plate 8 cm below the form
        # The foot plate runs flush to the bench's front edge; the post (2.4 cm) stands inside it.
        foot = box("SM_B09_FormBase", (-depth / 2, lc[1] - 7.0, top), (lc[0] + 14.0, lc[1] + 7.0, top + 2.5), "M_B09_TimberForm")
        post = revolve("SM_B09_FormBase", [(top + 2.5, 0.0), (top + 2.5, 2.4), (base_top - 3.5, 2.4), (base_top - 3.0, 6.5),
                                           (base_top, 6.5), (base_top, 0.0)], "M_B09_TimberForm", n_az=64).moved((lc[0], lc[1], 0.0))
        parts.append(merge("SM_B09_FormBase", [foot, post], "M_B09_TimberForm"))
        proxies.append((np.array([RIB_PROXY_FRONT, -width / 2 - 2, 0.0]), np.array([depth / 2 + 2, width / 2 + 2, top + 3])))
        sockets["LanternCentre"] = (lc, np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))
        for k, (z, r) in enumerate(zip(hoop_z(), hoop_r()), 1):
            sockets[f"HoopSeat{k}"] = (lc + [0.0, 0.0, z], None, None)
        # The form turns on the post's spindle (SM_B09_RibForm, placed at LanternCentre and turned by form_yaw_deg).
        # The winding's contacts stay at its front for every hoop:
        # - WindPress{k}: the left paw's fingertips on the wound strip, RIB["press_az_deg"] round to the hero's left;
        # - WindGuide{k}: the right paw on the free strip, RIB["guide_cm"] out toward the hero's right.
        sockets["FormSpindle"] = (np.array([lc[0], lc[1], base_top]), np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))
        for k, (z, r) in enumerate(zip(hoop_z(), hoop_r()), 1):
            a = math.radians(RIB["press_az_deg"])
            ro = r + HOOP_T / 2
            slope = float(profile_r(z + 0.01) - profile_r(z - 0.01)) / 0.02      # dr/dz: 0.26 at the end hoops
            n = np.array([math.cos(a), math.sin(a), -slope]) / math.sqrt(1.0 + slope * slope)   # the form's normal there
            sockets[f"WindPress{k}"] = (lc + [ro * math.cos(a), ro * math.sin(a), z], n, np.array([0.0, 0.0, 1.0]))
            # WindSteady{k}: where the left paw waits while the right hooks the strip: round to the hero's left of the
            # press and part way toward the form's middle (at the top hoop's own height it topped the 21:9 frame).
            a_s = math.radians(RIB["steady_az_deg"])
            z_s = z * (1.0 - RIB["wait_toward_middle"])
            ro_s = float(profile_r(z_s)) + HOOP_T / 2
            sl_s = float(profile_r(z_s + 0.01) - profile_r(z_s - 0.01)) / 0.02
            n_s = np.array([math.cos(a_s), math.sin(a_s), -sl_s]) / math.sqrt(1.0 + sl_s * sl_s)
            sockets[f"WindSteady{k}"] = (lc + [ro_s * math.cos(a_s), ro_s * math.sin(a_s), z_s], n_s, np.array([0.0, 0.0, 1.0]))
            la = math.radians(RIB["leave_az_deg"])
            tang = np.array([math.sin(la), -math.cos(la), 0.0])             # the free strip's heading off the form
            sockets[f"WindGuide{k}"] = (lc + [r * math.cos(la), r * math.sin(la), z] + tang * RIB["guide_cm"], tang,
                                        np.array([0.0, 0.0, 1.0]))
        parts.append(gauge_mesh(top))
        sockets["GaugePivot"] = (np.array(GAUGE["pivot"]), np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))
        # The strip rack: two posts on the bench's right carry cross-arms; the strips lie along +X on them, their
        # ends RIB["rack_front"] toward the hero, where the right paw takes the nearest.
        rx, ry, rz = RIB["rack_front"]
        rack = []
        for x_arm in (RIB_PROXY_FRONT + 4.0, depth / 2 - 4.0):
            rack.append(box("SM_B09_StripRack", (x_arm - 1.0, ry - 1.0, top), (x_arm + 1.0, ry + 1.0, rz - 0.6), "M_B09_TimberBench"))
            rack.append(box("SM_B09_StripRack", (x_arm - 1.0, ry - 4.0, rz - 0.6), (x_arm + 1.0, ry + 4.0, rz), "M_B09_TimberBench"))
            rack.append(box("SM_B09_StripRack", (x_arm - 1.0, ry - 4.6, rz), (x_arm + 1.0, ry - 4.0, rz + 1.4), "M_B09_TimberBench"))
            rack.append(box("SM_B09_StripRack", (x_arm - 1.0, ry + 4.0, rz), (x_arm + 1.0, ry + 4.6, rz + 1.4), "M_B09_TimberBench"))
        parts.append(merge("SM_B09_StripRack", rack))
        length = float(hoop_r().max()) * math.radians(WIND_DEG) + 6.0          # the longest hoop's strip, with spare
        stock = []
        for j in range(12):
            y = ry - 3.6 + (j % 6) * 1.3 + 0.1
            z = rz + 0.02 + HOOP_T * (j // 6) + 0.001 * (j // 6)
            stock.append(box("SM_B09_StripStock", (rx, y, z), (rx + length, y + HOOP_W, z + HOOP_T), "M_B09_Bamboo"))
        parts.append(merge("SM_B09_StripStock", stock))
        # The top layer's right-hand strip end, taken first: the right paw pinches it from above, its forearm coming in
        # beside the stock (reaching the left-hand end, it lay over the stock's other strips).
        sockets["StripStock"] = (np.array([rx, ry - 3.6 + 5 * 1.3 + 0.1 + HOOP_W / 2, rz + 0.02 + 2 * HOOP_T + 0.001]),
                                 np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))
        # The split strip (91 cm) lies on the bench behind the form, clear of the rack and the gauge.
        sockets["SplitStripRest"] = (np.array([12.0, -6.0, top]), np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0]))
        x0 = RIB_PROXY_FRONT - CAPSULE_R
        contacts = [sockets[f"WindPress{k}"][0] for k in (1, 6)] + [sockets[f"WindGuide{k}"][0] for k in (1, 6)]
        contacts += [sockets[f"WindGuide{k}"][0] - [2.5, 0.0, 0.0] for k in (1, 6)]      # the guiding paw's knuckles
        contacts += [sockets["StripStock"][0]] + [dial_point(a, GAUGE["face_r"]) for a in GAUGE["angles_deg"]]
        # 2 deg below the contacts' vertical middle: from the near stands turned off-axis, perspective put the lowest
        # hoop's knuckles 6 % past the 21:9 frame's foot while the top hoop kept 12 % spare.
        sockets["LookPoint"] = (look_point_for(contacts, x0, el_offset_deg=RIB["look_down_deg"]), None, None)
        work = sockets["LookPoint"][0]
    elif i == 1:
        depth, width, top = 70.0, 110.0, 75.0
        x0 = PASTE_PROXY_FRONT - CAPSULE_R
        parts = [bench("SM_B09_PasteBench", depth, width, top)]
        proxies.append((np.array([PASTE_PROXY_FRONT, -width / 2 - 2, 0.0]), np.array([depth / 2 + 2, width / 2 + 2, top + 3])))
        A = paste_axes()
        c = np.array(PASTE["centre"]) + [x0, 0.0, 0.0]
        lc = c
        ax = A[:, 2]
        frame = [Mesh(m.name, paste_frame(m.verts), m.tris, m.slot) for m in lantern("frame")]
        parts += frame
        # The cradle: the form's spindle (local z -30 to +38) turns in two bearings, one on a post from the bench
        # under its lower end, one on an arm from a post at the bench's left under its upper end.
        lo_end, hi_end = c + ax * (-LANTERN_H / 2 - 8.0), c + ax * (LANTERN_H / 2 + 16.0)
        cradle = []
        for end_, post_x in ((lo_end, max(lo_end[0] + 4.5, -depth / 2 + 2.0)), (hi_end, max(hi_end[0] + 4.5, -depth / 2 + 2.0))):
            bear = revolve("SM_B09_PasteCradle", [(-2.0, 1.3), (-2.0, 2.6), (2.0, 2.6), (2.0, 1.3), (-2.0, 1.3)], "M_B09_Iron", n_az=32)
            bv = bear.verts @ _frame_cols(ax).T + end_
            cradle.append(Mesh("SM_B09_PasteCradle", bv, bear.tris, "M_B09_Iron"))
            cradle.append(box("SM_B09_PasteCradle", (post_x - 1.6, end_[1] - 1.6, top), (post_x + 1.6, end_[1] + 1.6, end_[2] - 2.6), "M_B09_TimberBench"))
            if abs(post_x - end_[0]) > 2.0:                           # the arm from the post forward to the bearing
                cradle.append(box("SM_B09_PasteCradle", (end_[0] + 1.6, end_[1] - 1.0, end_[2] - 4.4), (post_x - 1.6, end_[1] + 1.0, end_[2] - 2.4),
                                  "M_B09_TimberBench"))
        parts.append(merge("SM_B09_PasteCradle", cradle))
        sockets["LanternCentre"] = (c, A[:, 0], A[:, 2])
        sockets["CradleAxis"] = (c, A[:, 0], A[:, 2])
        for k, (z, r) in enumerate(zip(hoop_z(), hoop_r()), 1):
            sockets[f"HoopSeat{k}"] = (c + ax * z, None, None)
        # The seam brushed (seam 1's meridian as the frame stands for each panel), rim line to rim line, 0.6 cm out.
        for j, z in enumerate(np.linspace(-LANTERN_H / 2, LANTERN_H / 2, 9)):
            r = float(paper_r(z)) + 0.6
            sockets[f"Seam_{j}"] = (paste_frame([[-r, 0.0, z]])[0], None, None)
        # The left paw's hold on the laid sheet, PASTE["hold_turn_deg"] round toward the hero's left of the seam.
        th = math.radians(180.0 + PASTE["hold_turn_deg"])
        hs = PASTE["hold_s_cm"]
        rh = float(paper_r(hs)) + 0.1
        slope = float(paper_r(hs + 0.05) - paper_r(hs - 0.05)) / 0.1
        n_loc = np.array([math.cos(th), math.sin(th), -slope]) / math.sqrt(1 + slope * slope)
        hold_p = paste_frame([[rh * math.cos(th), rh * math.sin(th), hs]])[0]
        sockets["SheetHold"] = (hold_p, A @ n_loc, None)
        # The left standard: a post on the bench at the sheet rail's far end carries the rail and the rim shelf.
        ry, rail_top, near_u = PASTE["rack_y"], PASTE["rail_top"], PASTE["sheet_near_u"]
        length = LANTERN_H                                        # a sheet's length, hung along the rail
        stand_xy = np.array([x0 + near_u + length + 1.6, ry + 1.0])
        gz = rail_top
        # The rail, its top at rail_top; the four sheets hang from it, 0.1 cm apart, sheet 4 against it.
        rack = [box("SM_B09_SheetRack", (x0 + near_u - 1.0, ry + 0.6, rail_top - 1.5), (stand_xy[0] - 1.6, ry + 1.4, rail_top + 0.5), "M_B09_TimberBench"),
                box("SM_B09_SheetRack", (stand_xy[0] - 1.6, stand_xy[1] - 1.6, top), (stand_xy[0] + 1.6, stand_xy[1] + 1.6, rail_top + 0.5),
                    "M_B09_TimberBench")]
        parts.append(merge("SM_B09_SheetRack", rack))
        for j in range(1, 5):                                     # sheet 1 outermost, taken first; sheet 4 against the rail
            # flat_sheet's frame: X across its width (here down from the rail), Z along its length (here along +X).
            sockets[f"WashiSheet{j}"] = (np.array([x0 + near_u + length / 2, ry + 0.55 - 0.1 * (5 - j), rail_top - 1.5]),
                                         np.array([0.0, 0.0, -1.0]), np.array([1.0, 0.0, 0.0]))
        w_sheet = float((np.radians(90.0 + 2 * GORE_OVERLAP_DEG) * paper_r(np.linspace(-LANTERN_H / 2, LANTERN_H / 2, 23))).max())
        # The paw takes sheet 1 by its near end, halfway down it.
        sockets["SheetTake"] = (np.array([x0 + near_u, ry + 0.55 - 0.4, rail_top - 1.5 - w_sheet / 2]), np.array([1.0, 0.0, 0.0]),
                                np.array([0.0, 0.0, 1.0]))
        # The paste pot sits in a ring on an arm from the cradle's lower post, beside the frame's lower end.
        du, dy, dz = PASTE["dip"]
        pot = np.array([x0 + du, dy])
        pz = dz - 4.0 - PASTE_POT[5][0]                          # lift the pot so its floor is 4 cm under the dip
        prof = [(z + pz, r) for z, r in PASTE_POT]
        parts.append(revolve("SM_B09_PastePot", prof, "M_B09_Ceramic", n_az=48).moved((pot[0], pot[1], 0.0)))
        foot_z, foot_r = prof[1]
        ring = revolve("SM_B09_PotBracket", [(foot_z - 0.8, 0.0), (foot_z - 0.8, foot_r + 0.8), (foot_z, foot_r + 0.8),
                                             (foot_z, 0.0)], "M_B09_Iron", n_az=48).moved((pot[0], pot[1], 0.0))
        pp = np.array([-depth / 2 + 2.0, pot[1]])               # its post on the bench's front, under the frame's near side
        arm = box("SM_B09_PotBracket", (pot[0], pot[1] - 1.0, foot_z - 1.6), (pp[0] - 1.6, pot[1] + 1.0, foot_z - 0.8), "M_B09_Iron")
        post = box("SM_B09_PotBracket", (pp[0] - 1.6, pp[1] - 1.6, top), (pp[0] + 1.6, pp[1] + 1.6, foot_z - 0.8), "M_B09_TimberBench")
        parts.append(merge("SM_B09_PotBracket", [ring, arm, post]))
        sockets["PasteDip"] = (np.array([pot[0], pot[1], dz]), None, np.array([0.0, 0.0, 1.0]))
        sockets["BrushRest"] = brush_in_pot(pot, lip=prof[4], floor=prof[5][0])
        # The top rim lies flat on a round shelf on an arm from the left standard, above the sheet rail.
        ru, ryy, rz = PASTE["rim_rest"]
        post_xy = stand_xy
        shelf_c = np.array([x0 + ru, ryy])
        shelf = [revolve("SM_B09_RimShelf", [(rz - 1.2 - RIM_H / 2, 0.0), (rz - 1.2 - RIM_H / 2, LANTERN_RIM_R + 0.6), (rz - RIM_H / 2, LANTERN_RIM_R + 0.6),
                                             (rz - RIM_H / 2, 0.0)], "M_B09_TimberBench", n_az=48).moved((shelf_c[0], shelf_c[1], 0.0)),
                 box("SM_B09_RimShelf", (shelf_c[0] + 2.0, min(shelf_c[1], post_xy[1]) - 1.0, rz - RIM_H / 2 - 2.2),
                     (post_xy[0] - 1.6, max(shelf_c[1], post_xy[1]) + 1.0, rz - RIM_H / 2 - 1.2), "M_B09_TimberBench"),
                 box("SM_B09_RimShelf", (post_xy[0] - 1.6, post_xy[1] - 1.6, gz + 0.5), (post_xy[0] + 1.6, post_xy[1] + 1.6, rz - RIM_H / 2 - 1.2),
                     "M_B09_TimberBench")]
        parts.append(merge("SM_B09_RimShelf", shelf))
        sockets["RimTopRest"] = (np.array([shelf_c[0], shelf_c[1], rz]), np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))
        # The bottom rim is fitted to the frame's lower mouth from the start (its rest is its seat); the rims step
        # seats the top rim on the upper mouth, along the frame's axis.
        for which, sgn in (("Bottom", -1.0), ("Top", 1.0)):
            sockets[f"Rim{which}Seat"] = (c + ax * sgn * (LANTERN_H / 2 + RIM_H / 2), A[:, 0], A[:, 2])
        sockets["RimBottomRest"] = sockets["RimBottomSeat"]
        contacts = [sockets[f"Seam_{j}"][0] for j in range(9)] + [hold_p, sockets["PasteDip"][0], sockets["SheetTake"][0]]
        sockets["LookPoint"] = (look_point_for(contacts, x0), None, None)
        work = sockets["LookPoint"][0]
    elif i == 2:
        # The oil rack (Coordinations 268, 269): the lantern hangs OIL["lantern_ahead_cm"] ahead of the natural stop, a
        # prepared batch workpiece coated all over but for one remaining swath, which the brush finishes by contact.
        x0 = OIL_PROXY_FRONT - CAPSULE_R                          # the natural stop on the centre line
        lc = lantern_centre(2)
        hp = hang_point()
        hook_top = lc[2] + hp[2]                                # the ring's top rests in the hook's bend
        bar = hook_top + 13.0
        top = bar + 10.0
        parts = []
        for y in (-45.0, 45.0):
            parts.append(box("SM_B09_OilRack", (-3.0, y - 3, 5.0), (3.0, y + 3, top), "M_B09_TimberBench"))
            parts.append(box("SM_B09_OilRack", (-35.0, y - 3, 0.0), (35.0, y + 3, 5.0), "M_B09_TimberBench"))
        parts.append(box("SM_B09_OilRack", (-2.5, -48.0, bar), (2.5, 48.0, bar + 5.0), "M_B09_TimberBench"))
        # The low shelf, its front under the lantern for the drip tray, on four legs.
        shelf_lo, shelf_hi = (OIL_PROXY_FRONT - 5.0, -42.0), (20.0, 42.0)
        parts.append(box("SM_B09_OilRack", (shelf_lo[0], shelf_lo[1], 18.0), (shelf_hi[0], shelf_hi[1], 20.5), "M_B09_TimberBench"))
        for x in (shelf_lo[0] + 1.5, shelf_hi[0] - 1.5):
            for y in (shelf_lo[1] + 1.5, shelf_hi[1] - 1.5):
                parts.append(box("SM_B09_OilRack", (x - 1.5, y - 1.5, 0.0), (x + 1.5, y + 1.5, 18.0), "M_B09_TimberBench"))
        parts = [merge("SM_B09_OilRack", parts)]
        # The hook leaves the bar's face on an iron arm and bends down into a U in the bail's plane. The bail's ring,
        # across that plane, rests with its top wire on the U's bottom: LanternHang is the ring's top (hang_point).
        u_bottom = hook_top - (HOOK_WIRE_R + BAIL_WIRE_R + HOOK_GAP)  # the ring's wire just over the U's: hung, not fused
        arm_z = bar + 2.5
        bend = [[lc[0] + HOOK_BEND_R * math.cos(a), 0.0, u_bottom + HOOK_BEND_R + HOOK_BEND_R * math.sin(a)]
                for a in np.linspace(math.pi, 2.0 * math.pi, 13)]
        parts.append(sweep("SM_B09_RackHook", [[-2.5, 0.0, arm_z], [lc[0] - HOOK_BEND_R, 0.0, arm_z]] + bend
                           + [[lc[0] + HOOK_BEND_R, 0.0, u_bottom + HOOK_BEND_R + 1.6]], "M_B09_Iron", radius=HOOK_WIRE_R, segments=10))
        # The oil dish sits in the ring of a turned stand on the low shelf, beside the lantern's lower right, where the
        # brush dips with its handle leaning back toward the hand (OIL_DIP_TILT). (A notch post carried it; the feet
        # reach 27-30 cm ahead and 22 to the side, so no floor post may stand inside 36.7 cm of the axis.)
        dish = np.array([x0 + OIL["dish"][0], OIL["dish"][1], OIL["dish"][2]])
        fz = dish[2] - 0.4                                       # the dish's floor, under the dipped tip
        rim_r = OIL_DISH_R
        base_z = fz - 0.8                                        # the dish's flat foot
        stand = revolve("SM_B09_DishStand", [(20.5, 0.0), (20.5, 4.5), (22.0, 4.5), (23.0, 1.2), (base_z - 1.2, 1.2),
                                             (base_z - 0.4, 0.0)], "M_B09_TimberBench", n_az=32)
        # Two iron straps cross under the foot (the dish rests on them) and carry a ring round its lower wall, clear of it.
        spokes = [box("SM_B09_DishStand", (-rim_r - 0.4, -0.4, base_z - 0.4), (rim_r + 0.4, 0.4, base_z), "M_B09_Iron"),
                  box("SM_B09_DishStand", (-0.4, -rim_r - 0.4, base_z - 0.4), (0.4, rim_r + 0.4, base_z), "M_B09_Iron"),
                  box("SM_B09_DishStand", (-0.6, -0.6, base_z - 1.2), (0.6, 0.6, base_z - 0.4), "M_B09_Iron")]
        ring = revolve("SM_B09_DishStand", [(base_z, rim_r - 0.7), (base_z, rim_r + 0.4), (base_z + 0.8, rim_r + 0.4),
                                            (base_z + 0.8, rim_r - 0.7), (base_z, rim_r - 0.7)], "M_B09_Iron", n_az=48)
        parts.append(merge("SM_B09_DishStand", [stand, ring] + spokes).moved((dish[0], dish[1], 0.0)))
        parts.append(revolve("SM_B09_OilDish", [(fz - 0.8, 0.0), (fz - 0.8, rim_r - 1.8), (fz + 0.2, rim_r - 0.6), (fz + 1.0, rim_r),
                                                (fz + 1.0, rim_r - 0.5), (fz, rim_r - 2.0), (fz, 0.0)], "M_B09_Ceramic",
                             n_az=48).moved((dish[0], dish[1], 0.0)))
        parts.append(revolve("SM_B09_OilJar", [(20.5, 0.0), (20.5, 6.0), (24.0, 8.8), (34.0, 9.0), (41.0, 6.5), (43.5, 4.2),
                                               (44.5, 4.6), (44.5, 3.6), (36.0, 3.2), (36.0, 0.0)], "M_B09_Ceramic", n_az=64).moved((10.0, 24.0, 0.0)))
        parts.append(revolve("SM_B09_DripTray", [(0.0, 0.0), (0.0, 10.0), (2.0, 11.0), (2.0, 10.3), (0.6, 9.6), (0.6, 0.0)],
                             "M_B09_Ceramic", n_az=64).moved((lc[0], 0.0, 20.5)))
        # The proxy is a wall to the capsule (above UE's default 45 cm step height, which root keeps) and stays under
        # the station ray's start (RAY_FROM_Z), as the benches' proxies do: the station point is inside its plan.
        proxies.append((np.array([OIL_PROXY_FRONT, -52.0, 0.0]), np.array([36.0, 52.0, 78.0])))
        sockets["LanternHang"] = (np.array([lc[0], 0.0, hook_top]), None, None)
        sockets["OilDip"] = (dish, None, np.array([0.0, 0.0, 1.0]))
        # The brush lies across the dish on its rim at both sides, its bristles over the near rim, its handle back
        # over the dish.
        sockets["BrushRest"] = (np.array([dish[0] - rim_r - 0.2, dish[1], fz + 1.0 + 0.6]), np.array([0.0, -1.0, 0.0]),
                                np.array([0.0, 0.0, 1.0]))
        sockets["OilJar"] = (np.array([10.0, 24.0, 44.5]), None, None)
        # The remaining swath: the brush's path down the paper from the top rim line to the belly, OIL_SWATH["offset_cm"]
        # out from the washi, at OIL_SWATH["az_deg"]; the bristles sweep OIL_SWATH["half_width_cm"] to either side.
        a = math.radians(OIL_SWATH["az_deg"])
        for j, z in enumerate(np.linspace(*OIL_SWATH["s_cm"], 9)):
            r = float(paper_r(z)) + OIL_SWATH["offset_cm"]
            sockets[f"OilSwath_{j}"] = (lc + [r * math.cos(a), r * math.sin(a), z], None, None)
        al, s_st = math.radians(OIL["steady_az_deg"]), OIL["steady_s_cm"]
        slope = float(paper_r(s_st + 0.05) - paper_r(s_st - 0.05)) / 0.1
        n_st = np.array([math.cos(al), math.sin(al), -slope]) / math.sqrt(1.0 + slope * slope)   # the washi's normal there
        sockets["LanternSteady"] = (lc + np.array([math.cos(al), math.sin(al), 0.0]) * (float(paper_r(s_st)) + 0.1) + [0.0, 0.0, s_st],
                                    n_st, None)
        contacts = [sockets[f"OilSwath_{j}"][0] for j in range(9)] + [dish, sockets["LanternSteady"][0]]
        sockets["LookPoint"] = (look_point_for(contacts, x0), None, None)
        work = sockets["LookPoint"][0]
    else:
        top = 72.0
        L_ = SHELL_LAYOUT
        x0 = SHELL_PROXY_FRONT - CAPSULE_R
        X = lambda u: x0 + u  # noqa: E731
        parts = [bench("SM_B09_ShellBench", 70.0, 120.0, top)]
        proxies.append((np.array([SHELL_PROXY_FRONT, -62.0, 0.0]), np.array([37.0, 62.0, top + 3])))
        # The board: 3 cm thick, its front cantilevered from four legs on the bench.
        u0, u1, y0, y1 = L_["board"]
        t2 = L_["top"]
        stand = [box("SM_B09_ShellStand", (X(u0), y0, t2 - 3.0), (X(u1), y1, t2), "M_B09_TimberBench")]
        for xl in (-33.5, X(u1) - 2.5):
            for yl in (y0 + 0.5, y1 - 3.5):
                stand.append(box("SM_B09_ShellStand", (xl, yl, top), (xl + 3.0, yl + 3.0, t2 - 3.0), "M_B09_TimberBench"))
        parts.append(merge("SM_B09_ShellStand", stand))
        origin, rot = weapon_rest()
        # The tube's holder: a turned socket block on the bench top, the handle end standing in its bore on the bore's
        # floor, and an iron ring round the clean collar on an arm from a post behind.
        hz = origin[2] + WEAPON7["x_range_cm"][0]                          # the handle end's height
        hr = WEAPON7["handle_end_r_cm"]
        holder = [revolve("SM_B09_WeaponCradle", [(top, 0.0), (top, 4.6), (hz + 6.0, 4.6), (hz + 6.0, hr + 0.06), (hz, hr + 0.06),
                                                  (hz, 0.0)], "M_B09_TimberBench", n_az=48).moved((origin[0], origin[1], 0.0))]
        c0, c1, cr = WEAPON7["collar_cm"]
        ring_z = origin[2] + 0.5 * (c0 + c1)
        holder.append(revolve("SM_B09_WeaponCradle", [(ring_z - 0.7, cr + 0.04), (ring_z - 0.7, cr + 1.0), (ring_z + 0.7, cr + 1.0),
                                                      (ring_z + 0.7, cr + 0.04), (ring_z - 0.7, cr + 0.04)], "M_B09_Iron", n_az=48)
                      .moved((origin[0], origin[1], 0.0)))
        post_x = origin[0] + 9.0
        holder.append(box("SM_B09_WeaponCradle", (post_x - 1.5, origin[1] - 1.5, top), (post_x + 1.5, origin[1] + 1.5, ring_z + 1.0), "M_B09_TimberBench"))
        holder.append(box("SM_B09_WeaponCradle", (origin[0] + cr + 0.9, origin[1] - 0.8, ring_z - 0.6), (post_x - 1.5, origin[1] + 0.8, ring_z + 0.6),
                          "M_B09_Iron"))
        parts.append(merge("SM_B09_WeaponCradle", holder))
        sockets["WeaponRest"] = (origin, rot[:, 0], rot[:, 2])
        sockets["Muzzle"] = (origin + rot @ np.array(WEAPON7["muzzle_cm"]), rot[:, 0], rot[:, 2])
        sockets["TubeFuse"] = (origin + rot @ np.array(WEAPON7["fuse_cm"]), rot[:, 0], rot[:, 2])   # the touch hole (a prop)
        # The rack: a thin plank with three cups bored to the weapon's bore (0.8 cm lower than its first 1.5 cm plank: a
        # seated shell's fuse cord stood 0.4996 cm under the left forearm carrying the next one past it).
        cu = L_["cups"]
        cr_ = L_["cup_r"] + 0.2
        pk = L_["rack_plank_cm"]
        rack = [box("SM_B09_ShellRack", (X(min(c[0] for c in cu) - cr_), min(c[1] for c in cu) - cr_, t2),
                    (X(max(c[0] for c in cu) + cr_), max(c[1] for c in cu) + cr_, t2 + pk), "M_B09_TimberBench")]
        for k, (u, y) in enumerate(cu, 1):
            rack.append(revolve("SM_B09_ShellRack", [(t2 + pk, 0.0), (t2 + pk, L_["cup_r"]), (t2 + pk + 2.5, L_["cup_r"]),
                                                     (t2 + pk + 2.5, WEAPON7["bore_cm"] / 2), (t2 + pk + 0.5, WEAPON7["bore_cm"] / 2),
                                                     (t2 + pk + 0.5, 0.0)], "M_B09_TimberBench", n_az=48)
                        .moved((X(u), y, 0.0)))
            sockets[f"ShellSeat{k}"] = (np.array([X(u), y, t2 + pk + 0.5 + SHELL["wrapped_cm"] / 2]), None, np.array([0.0, 0.0, 1.0]))
            # The seated shell's fuse cord's tip (shell(): the cord leaves the neck's top and leans 0.5 cm along +X).
            sockets[f"FuseCheck{k}"] = (sockets[f"ShellSeat{k}"][0] + [0.5, 0.0, SHELL_FUSE_TIP_CM], None, np.array([0.0, 0.0, 1.0]))
        parts.append(merge("SM_B09_ShellRack", rack))
        tu, ty = L_["tray"]
        tr = L_["tray_r"]
        parts.append(revolve("SM_B09_ShellTray", [(t2, 0.0), (t2, tr - 0.6), (t2 + 2.4, tr), (t2 + 2.4, tr - 0.6), (t2 + 0.8, tr - 1.2), (t2 + 0.8, 0.0)],
                             "M_B09_TimberBench", n_az=64).moved((X(tu), ty, 0.0)))
        for k in (1, 2, 3):                                       # 120 deg apart on the tray's floor, taken from the right
            a = math.radians(60.0 + 120.0 * (k - 1))              # (the right forearm lies over the right of the core it takes)
            cr = L_["core_r"]
            sockets[f"ShellCore{k}"] = (np.array([X(tu) + cr * math.cos(a), ty + cr * math.sin(a), t2 + 0.8 + SHELL["core_cm"] / 2]), None, None)
        wu, wy = L_["wrap"]
        pt = L_["wrap_post_top"]
        post = [revolve("SM_B09_WrapPost", [(t2, 0.0), (t2, 3.0), (t2 + 1.0, 3.0), (t2 + 1.5, 1.2), (pt - 1.4, 1.2), (pt - 0.9, 3.4),
                                            (pt, 3.4), (pt, 0.0)], "M_B09_TimberBench", n_az=48).moved((X(wu), wy, 0.0))]
        parts.append(merge("SM_B09_WrapPost", post))
        parts.append(box("SM_B09_WrapPaper", (X(wu) - 3.2, wy - 3.2, pt), (X(wu) + 3.2, wy + 3.2, pt + 0.2), "M_B09_ShellPaper"))
        sockets["WrapPaper"] = (np.array([X(wu), wy, pt + 0.2 + SHELL["wrapped_cm"] / 2]), None, None)   # the core laid on it
        sockets["WrapSpot"] = (np.array([X(wu), wy, pt + 0.2 + SHELL["wrapped_cm"] / 2 + L_["wrap_lift_cm"]]), None, None)
        cxu, cyy = L_["coil"]
        coil = [[X(cxu) + (1.2 + 0.2 * t) * math.cos(t), cyy + (1.2 + 0.2 * t) * math.sin(t), t2 + 0.25] for t in np.linspace(0, 5 * math.pi, 90)]
        parts.append(sweep("SM_B09_FuseCoil", coil, "M_B09_FuseCord", radius=0.25, segments=10))
        sockets["FuseCoil"] = (np.array([X(cxu), cyy, t2 + 0.5]), None, None)
        contacts = [sockets[n][0] for n in ("ShellCore1", "ShellCore2", "ShellCore3", "ShellSeat1", "ShellSeat2", "ShellSeat3", "WrapSpot",
                                            "FuseCheck1", "FuseCheck2", "FuseCheck3")]
        # On the bench's centre line (the wrapping post, the tube behind it): the cups reach 20 cm left and the tray 12
        # right, and the contacts' lateral middle (3 cm left) turned the far right stands' facing band to 26 deg, past
        # the left paw's reach to the paper.
        sockets["LookPoint"] = (look_point_for(contacts, x0, az_deg=0.0), None, None)
        work = sockets["LookPoint"][0]
    sockets["StationPoint"] = (np.array([0.0, 0.0, WORK_Z]), None, None)      # the trace's target, wherever the work sits
    stand = np.array([centre_stop(proxies), 0.0, 0.0])
    sockets["WorkStand"] = (stand, np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))
    return parts, sockets, proxies, work


STATE_CONTRACT = {
    "common": {
        "reads": "FView only (Active, Step, Committed[6], HeldStep, HeldMs, FailedStripSerial/AgeMs, LastAction); it "
                 "never advances a hold, credits a unit or imposes a cooldown",
        "Idle": "not Active, or not admitted at the station: the station's props in Committed's state, the paws free",
        "Ready": "admitted (b09_craft_region.admitted), the step active, not held: the paws in the first working pose of "
                 "the next unit, after its preparation clip",
        "Held": "HeldStep == the step: the pose and props are a function of HeldMs alone",
        "Committed": "Committed[step] advanced: the completion clip, then Ready for the next unit or the next step",
        "Cancelled": "a timed hold ends uncredited (early release, ineligible, or a bend outside 640-960 ms): the presenter "
                     "returns to Ready from where it is; work already shown by contact stays shown",
        "Retry": "the next press after the release (root's WaitRelease): HeldMs restarts at 0",
        "press_steps": "steps 2, 4, 5 are credited at the press; their clip is a function of LastAction.AgeMs for the "
                       "matching Step and Unit; leaving, crouching or combat mid-clip only stops presenting it (nothing "
                       "rolls back, nothing to retry); a reset or reload clears the record and the presenter's cursor",
    },
    "st_b09_rib_form": {
        "step": 0, "kind": "timed hold, released within BendMs 800 +- 160",
        "Ready": "hoop n+1 prepared (about 900 ms): the right paw takes the top layer's right-hand strip end (StripStock), "
                 "lifts it out and carries it round the form's right to the notch and hooks it (the left paw waits off "
                 "the form at WindSteady{n+1}); then the left comes in to press the hooked strip (WindPress{n+1}) as the "
                 "right slides out along it to the guide (WindGuide{n+1})",
        "Held": "HeldMs 0-800: the strip at flex_stage(HeldMs), the form turned by form_yaw_deg(n, flex), the needle at "
                "gauge_angle(HeldMs); the left paw presses, the right holds the free strip as it draws through its grip",
        "Committed": "Committed[0] = n+1: the hoop seats; the right paw lets the strip's end go into its lap; the next "
                     "hoop's preparation follows (none after hoop 6)",
        "Cancelled": "a release outside 640-960 ms or an early release: the split strip at SplitStripRest while "
                     "FailedStripAgeMs < SPLIT_SHOW_MS, then a fresh strip's preparation",
        "timing_conflict": "a re-press sooner than the preparation's ~900 ms after a commit or a split cuts the "
                           "preparation short; with no cooldown the presenter must blend from where the paws are to the "
                           "Held pose (measured, to be agreed with root)",
    },
    "st_b09_paste_bench": {
        "steps": [1, 2], "kind": "step 1 a timed hold (PasteMs 1500) per panel; step 2 a press",
        "Ready": "panel n+1: the frame turned by panel_turn_deg(n + 1) so its seam faces the hero; the left paw has "
                 "taken sheet n+1 by its near end from the rail (SheetTake); the brush dipped at PasteDip",
        "Held": "HeldMs 0-400: the left paw lays the sheet on the frame (gore PASTE_ORDER[n], wrapping from the seam "
                "toward the hero's left) and holds it by its fingertips at SheetHold; the brush to the lower rim line. "
                "400-1500: the stroke from the lower rim line to the upper (Seam_0..8), the bristle edge turned square "
                "at each rim line; paste only where the bristles have swept",
        "Committed": "Committed[1] = n+1: the left paw lets go, the cradle turns the frame +90 deg, the left takes the "
                     "next sheet and the brush re-dips (about 800 ms)",
        "Cancelled": "an early release: after 400 ms the sheet stays laid and held with the paste swept so far, the "
                     "brush back to the pot; before 400 ms the paw keeps the sheet and returns to Ready",
        "Retry": "the stroke from the lower rim line again (already pasted washi stays as it is)",
        "timing_conflict": "a re-press sooner than the completion's ~800 ms (turn, next sheet, re-dip) leaves that "
                           "preparation unfinished; with no cooldown the presenter must compress it (measured, to be "
                           "agreed with root)",
        "rims": "step 2's press seats the top rim from RimTopRest on the upper mouth (RimTopSeat). Measured conflict: "
                "on the paste pose the upper mouth is out of reach (151 %); proposed: the cradle re-tilts the frame for "
                "the rims (a two-axis cradle bringing the upper mouth to the front, as PASTE_FIRST_POSE did)",
        "open": "the stroke's last sample at the upper rim line: hidden behind the laid gore from some stands, and "
                "reach 98.1-99.8 % / wrist 76-78 deg at the far-left and near-right stands (b09_craft_region)",
    },
    "st_b09_oil_rack": {
        "step": 3, "kind": "timed hold, PasteMs 1500",
        "Ready": "the left paw's fingertips steady the hanging lantern (LanternSteady); the right brush dipped at OilDip",
        "Held": "HeldMs 0-300: the carry from the dish to the swath's top (OilSwath_0, sagging OIL carry_lift_cm); "
                "300-1500: the stroke down the remaining swath (OilSwath_0..8); the washi is wet only where the bristles "
                "have swept (the swept footprint, a monotone union)",
        "Committed": "Committed[3] = 1: the brush back to BrushRest; the lantern leaves the rack for PLAYER_SLOT",
        "Cancelled": "early release: the wetness swept so far stays; the brush returns to the dish (Ready)",
        "Retry": "the stroke from the swath's top again; already-wet washi stays as it is",
    },
    "st_b09_shell_bench": {
        "steps": [4, 5], "kind": "press steps (credited at the press)",
        "Committed[4]": "each press: a clip of at most 1200 ms over LastAction.AgeMs: take core k, to the paper, wrap and "
                        "twist, to the rack, seat it (five phases, about 240 ms each)",
        "Committed[5]": "the Inspect press (Coordination 277): a clip of at most 900 ms; the left paw passes over the "
                        "three seated shells' fuse cord tips, FuseCheck3 to FuseCheck1, its elbow raised over them; "
                        "nothing is lit, loaded or discharged; recipe counts, timing, reward and b10's charge fuse are "
                        "unchanged; weapon 7 stays in its block, clear of the hand path",
        "cancellation": "as every press step: credited at the press, so leaving or crouching mid-clip only stops "
                        "presenting it; nothing to retry",
    },
}


# Parts that reach past their station's proposed proxy, by design, with the reason (proxy_overhangs measures them).
# Root's collision is root's; these are reported for its proxy decision.
PROXY_OVERHANG_OK = {
    "st_b09_rib_form": ({"SM_B09_FormBase", "SM_B09_StripStock"},
                        "the form's foot flush with the bench's front edge and the strips' front ends toward the hero; "
                        "the long strips also run out past the bench's back"),
    "st_b09_paste_bench": ({"SM_B09_Form", "SM_B09_PasteCradle", "SM_B09_SheetRack", "SM_B09_PastePot", "SM_B09_PotBracket"}
                           | {f"SM_B09_Hoop{k}" for k in range(1, 7)},
                           "the frame on its tilted cradle, its lower end past the bench's front edge, and the pot and "
                           "the sheet rail's near end in front of it, all at chest height (the region's work)"),
    "st_b09_oil_rack": ({"SM_B09_OilRack", "SM_B09_DishStand", "SM_B09_OilDish", "SM_B09_DripTray"},
                        "the low shelf, the dish on its stand and the drip tray, toward the hero"),
    "st_b09_shell_bench": ({"SM_B09_ShellStand", "SM_B09_ShellRack", "SM_B09_ShellTray", "SM_B09_WrapPost", "SM_B09_WrapPaper"},
                           "the board cantilevered over the bench's front edge with the shells' work on it"),
}
# The working region brings each station's work over its bench's front edge at chest height, above the proxies' tops.
# These parts are reported for root's proxy decision; the hero's body is kept BODY_CLEAR_CM off every prop by the
# region's body gate (b09_craft_region.body_gate).
TORSO_FRONT_CM, TORSO_HALF_CM = 12.0, 17.0   # the torso's front and half-width from the stand (b09_craft_poses.TORSO)


def proxy_overhangs(i):
    """{part: (cm past the proxy in plan, cm from the standing torso's front box at the craft stand)} for each part of
    station i that reaches past its proposed proxy."""
    parts, _, proxies, _ = station_parts(i)
    lo_p, hi_p = proxies[0]
    stand = craft_stand(i)
    t_lo = np.array([stand[0] - 15.0, stand[1] - TORSO_HALF_CM])
    t_hi = np.array([stand[0] + TORSO_FRONT_CM, stand[1] + TORSO_HALF_CM])
    out = {}
    for m in parts:
        lo, hi = m.bounds()
        over = float(max(0.0, *(lo_p[:2] - lo[:2]), *(hi[:2] - hi_p[:2])))
        if over > 1e-6:
            gap = np.maximum(0.0, np.maximum(t_lo - m.verts[:, :2], m.verts[:, :2] - t_hi))
            out[m.name] = (round(over, 2), round(float(np.linalg.norm(gap, axis=1).min()), 2))
    return out


def craft_stand(i):
    """The natural stop (station frame): the capsule's axis where walking along +X on the station's centre line stops
    against its proposed proxy (centre_stop), the near edge of the working region (b09_craft_region), whose gates check
    every admitted stand and facing. The first-person checks look from its eye."""
    return station_parts(i)[1]["WorkStand"][0]


def needle():
    """The flex gauge's needle: its hinge at the origin, pointing upright (+Z), a tapered vermilion blade 0.3 cm in
    front of the face. Root turns it in the dial's plane so it points along (0, sin a, cos a), a = gauge_angle(ms)."""
    r = GAUGE["band_r"][1] - 0.4
    v = np.array([[-0.3, -0.45, -1.2], [-0.3, 0.45, -1.2], [-0.3, 0.12, r], [-0.3, -0.12, r],
                  [-0.6, -0.45, -1.2], [-0.6, 0.45, -1.2], [-0.6, 0.12, r], [-0.6, -0.12, r]])
    t = np.array([[0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6], [0, 4, 5], [0, 5, 1], [1, 5, 6], [1, 6, 2], [2, 6, 7], [2, 7, 3], [3, 7, 4], [3, 4, 0]])
    # The hub sits on the dial's face, on its pin (it floated 0.2 cm in front of it).
    hub = revolve("SM_B09_GaugeNeedle", [(-0.75, 0.0), (-0.75, 0.9), (0.0, 0.9), (0.0, 0.0)], "M_B09_Iron", n_az=24)
    hub.verts = hub.verts[:, [2, 1, 0]]                    # its axis along X
    hub.tris = hub.tris[:, [0, 2, 1]]
    return merge("SM_B09_GaugeNeedle", [Mesh("SM_B09_GaugeNeedle", v, t, "M_B09_GaugeNeedle"), hub], "M_B09_GaugeNeedle")


def needle_at(ms):
    """The needle placed on the dial at a held bend's elapsed ms (station frame)."""
    a = math.radians(gauge_angle(ms))
    rot = np.array([[1.0, 0.0, 0.0], [0.0, math.cos(a), math.sin(a)], [0.0, -math.sin(a), math.cos(a)]])  # +Z -> (0, sin a, cos a)
    return needle().moved(GAUGE["pivot"], rot=rot)


def state_meshes(i):
    """The meshes a station's view state shows, each with its pivot: [(mesh, pivot description, where root places it)]."""
    lf = "the lantern's centre"
    if i == 0:
        rows = [(hoop(k, f), "the form's frame (the rib form's centre)", "LanternCentre, turned by form_yaw_deg")
                for k in range(1, 7) for f in FLEX_STAGES]
        rows += [(split_strip(), "its middle, lying flat", "SplitStripRest"), (needle(), "its hinge", "GaugePivot")]
    elif i == 1:
        rows = [(gore(k), lf, "LanternCentre (the frame on its cradle, turned by panel_turn_deg)") for k in range(1, 5)]
        rows += [(flat_sheet(f"SM_B09_WashiSheet{j}"), "its near edge's middle", f"WashiSheet{j} (hung on the rack; sheet 1, outermost, taken first)")
                 for j in range(1, 5)]
        rows += [(rim(w), "the ring's centre", f"Rim{w}Rest, then Rim{w}Seat") for w in ("Top", "Bottom")]
        rows.append((brush("SM_B09_PasteBrush", PASTE_BRUSH_W), "the bristles' tip", "BrushRest, then along Seam_0..8"))
    elif i == 2:
        rows = [(merge("SM_B09_LanternFinished", lantern("finished")), lf + "; it hangs from its hang point", "LanternHang - hang_point")]
        rows.append((brush("SM_B09_OilBrush", 5.0, 4.0, 16.0), "the bristles' tip", "BrushRest, then along OilStroke*"))
    else:
        rows = [(shell("core"), "its centre", "ShellCore1..3"), (shell("wrapped"), "its centre", "WrapSpot, then ShellSeat1..3")]
    return rows


# --- Shells ---------------------------------------------------------------------------------------------------------
SHELL = {"core_cm": 4.8, "wrapped_cm": 5.4, "neck_cm": 1.6}
SHELL_FUSE_TIP_CM = SHELL["wrapped_cm"] / 2 + SHELL["neck_cm"] + 3.0      # a wrapped shell's fuse cord's tip over its centre


def shell(stage):
    """A festival shell: "core" (the paste-and-paper ball, 4.8 cm, with its fuse stub) or "wrapped" (5.4 cm, its paper
    gathered into a twisted neck and tied). Frame: its centre. The bore is 5.6 cm, so a wrapped shell seats with 1 mm
    clear all round."""
    d = SHELL["core_cm"] if stage == "core" else SHELL["wrapped_cm"]
    parts = [sphere("SM_B09_Shell" + stage.title(), d / 2, "M_B09_ShellPaper" if stage == "wrapped" else "M_B09_ShellCore")]
    top = d / 2
    if stage == "wrapped":
        # The gathered paper is a solid bunch (an open skirt showed its back through the one-sided paper material),
        # its foot sunk into the ball; the twine is drawn 0.02 cm into it, not floating round it.
        neck = [(top - 0.3, 0.0), (top - 0.3, 0.9), (top + 0.4, 0.45), (top + SHELL["neck_cm"] - 0.3, 0.35),
                (top + SHELL["neck_cm"], 0.6), (top + SHELL["neck_cm"], 0.0)]
        parts.append(revolve("SM_B09_ShellWrapped", neck, "M_B09_ShellPaper", n_az=24))
        r_tie = lambda z: 0.45 + (0.35 - 0.45) * (z - (top + 0.4)) / (SHELL["neck_cm"] - 0.7) - 0.02  # noqa: E731
        z0, z1 = top + 0.5, top + 0.8
        parts.append(revolve("SM_B09_ShellWrapped", [(z0, r_tie(z0)), (z0, 0.62), (z1, 0.62), (z1, r_tie(z1)), (z0, r_tie(z0))],
                             "M_B09_Twine", n_az=24))
        fuse_from = top + SHELL["neck_cm"]
    else:
        fuse_from = top
    parts.append(sweep("SM_B09_Shell" + stage.title(), [[0, 0, fuse_from - 0.2], [0.1, 0, fuse_from + 1.8], [0.5, 0, fuse_from + 3.0]],
                       "M_B09_FuseCord", radius=0.18, segments=10))
    return merge("SM_B09_Shell" + stage.title(), parts)


# --- The hanging output -------------------------------------------------------------------------------------------------
POLES_Y = (-560.0, -820.0, -1080.0, -1340.0)
POLE_Z = 395.0
POLE_X = (1795.0, 2305.0)                    # inside the walls (inner faces x 1606 and 2314)
SLOT_X = tuple(1830.0 + 50.0 * i for i in range(10))
PLAYER_SLOT = 36                             # pole 4 (nearest the oil rack), the 7th hook (x 2130)


def slots():
    """The 40 hook slots (world cm): (pole, index, hang point, yaw deg). A lantern hangs by its bail's ring, which lies
    across the bail; the ring threads the slot hook only lying across the hook's plane (the hook hangs over its pole
    in the world's YZ plane), so a lantern faces +X or -X: 90 or 270 deg, alternating along the pole. (A free yaw
    jitter, for varied faces, ran rings through hooks.)"""
    out = []
    for p, y in enumerate(POLES_Y):
        for i, x in enumerate(SLOT_X):
            k = p * 10 + i
            out.append((p, i, np.array([x, y + 2.4, POLE_Z - 4.0]), 90.0 + 180.0 * ((k + p) % 2)))
    return out


def hanging_parts():
    parts = []
    for y in POLES_Y:
        parts.append(sweep("SM_B09_DryingPole", [[POLE_X[0], y, POLE_Z], [POLE_X[1], y, POLE_Z]], "M_B09_Bamboo", radius=2.0, segments=24))
        for x in (POLE_X[0] + 40.0, POLE_X[1] - 40.0):
            parts.append(sweep("SM_B09_PoleHanger", [[x, y, CEILING_Z], [x, y, POLE_Z + 2.0]], "M_B09_Cord", radius=0.35, segments=10))
    hooks = []
    for _, _, hp, _ in slots():
        # Over the pole, then down into a U whose bottom lies under the hang point: the bail's ring, across the hook's
        # plane, rests there with its top wire HOOK_GAP over the U's (it ran through the old hook's tip).
        # An S: an arc resting on the pole (its wire 0.02 cm off), a shank down outside it, the U, and a short tip that
        # stays under the pole. (The earlier hook began inside the pole: the clash gate found 72 crossing pairs.)
        pole_y = hp[1] - 2.4
        r_arc = 2.0 + SLOT_HOOK_WIRE_R + 0.02
        arc = [[hp[0], pole_y + r_arc * math.cos(t), POLE_Z + r_arc * math.sin(t)] for t in np.radians(np.linspace(160.0, -10.0, 12))]
        r_u = SLOT_HOOK_BEND_R
        u_bottom = hp[2] - (SLOT_HOOK_WIRE_R + BAIL_WIRE_R + HOOK_GAP)
        bend = [[hp[0], hp[1] + r_u * math.cos(a), u_bottom + r_u + r_u * math.sin(a)] for a in np.linspace(2.0 * math.pi, math.pi, 13)]
        hooks.append(sweep("SM_B09_SlotHook", arc + bend + [[hp[0], hp[1] - r_u, u_bottom + r_u + 0.8]], "M_B09_Iron",
                           radius=SLOT_HOOK_WIRE_R, segments=10))
    return merge("SM_B09_DryingPoles", parts, "M_B09_Bamboo"), merge("SM_B09_SlotHooks", hooks, "M_B09_Iron")


# --- Checks ---------------------------------------------------------------------------------------------------------
def segment_hits_box(a, b, lo, hi):
    """Whether the segment a-b passes through the open box (lo, hi)."""
    d = b - a
    t0, t1 = 0.0, 1.0
    for k in range(3):
        if abs(d[k]) < 1e-12:
            if a[k] <= lo[k] or a[k] >= hi[k]:
                return False
            continue
        ta, tb = (lo[k] - a[k]) / d[k], (hi[k] - a[k]) / d[k]
        t0, t1 = max(t0, min(ta, tb)), min(t1, max(ta, tb))
        if t0 >= t1:
            return False
    return True


def circle_hits_box2d(c, r, lo, hi):
    q = np.clip(c, lo[:2], hi[:2])
    return float(np.linalg.norm(c - q)) < r


def eligible(i, x, y, proxies_world):
    """Whether the hero could stand at (x, y) to work station i: reach, floor, and a capsule clear of the walls and
    the proxies (in plan)."""
    sx, sy = STATIONS[i][1]
    fz = floor_at(sx, sy)
    if math.hypot(x - sx, y - sy) >= REACH_CM or abs(floor_at(x, y) - fz) > FEET_TOL_CM:
        return False
    c = np.array([x, y])
    for k, (cc, size) in enumerate(SOLIDS):
        if k in FLOOR_SLABS:
            continue
        lo, hi = cc - size / 2, cc + size / 2
        if hi[2] > fz + 2 and lo[2] < fz + 2 * CAPSULE_HALF and circle_hits_box2d(c, CAPSULE_R, lo, hi):
            return False
    for lo, hi in proxies_world:
        if circle_hits_box2d(c, CAPSULE_R, lo, hi):
            return False
    return True


def clearance(i, step=10.0):
    """Station i's clearances: the work stand, the eye's line to the work, and every eligible station ray against the
    proposed proxies (and the room's own solids, which the trace already meets today).

    The rays start at the **standing** capsule's centre (RAY_FROM_Z). The crouched rays, from CROUCH_HALF, are a CPU
    estimate for root: the same plan positions and boxes, not root's crouch or native coverage."""
    parts, sockets, proxies, work = station_parts(i)
    sx, sy = STATIONS[i][1]
    fz = floor_at(sx, sy)
    o = np.array([sx, sy, fz])
    pw = [(lo + o, hi + o) for lo, hi in proxies]
    others = []
    for j, (_, (xj, yj)) in enumerate(STATIONS):
        if j != i:
            oj = np.array([xj, yj, floor_at(xj, yj)])
            others += [(lo + oj, hi + oj) for lo, hi in station_parts(j)[2]]
    stand = o + craft_stand(i)
    ray_end = o + [0.0, 0.0, RAY_TO_Z]
    positions = [(x, y) for x in np.arange(sx - REACH_CM, sx + REACH_CM + 1, step) for y in np.arange(sy - REACH_CM, sy + REACH_CM + 1, step)]
    ok = [(x, y) for x, y in positions if eligible(i, x, y, pw + others)]
    blocked_by_proxy = [(x, y) for x, y in ok if any(segment_hits_box(np.array([x, y, fz + RAY_FROM_Z]), ray_end, lo, hi) for lo, hi in pw)]
    walls = [(cc - size / 2, cc + size / 2) for k, (cc, size) in enumerate(SOLIDS) if k not in FLOOR_SLABS]
    blocked_by_room = [(x, y) for x, y in ok if any(segment_hits_box(np.array([x, y, fz + RAY_FROM_Z]), ray_end, lo, hi) for lo, hi in walls)]
    crouched = [(x, y) for x, y in ok if any(segment_hits_box(np.array([x, y, fz + CROUCH_HALF]), ray_end, lo, hi) for lo, hi in pw)]
    # The hero at the work stand: the capsule's gap to every part, and the eye's line to the work point.
    capsule_gap = min(_capsule_gap(stand, m.moved(o)) for m in parts)
    eye = stand + [EYE[0], EYE[1], CAPSULE_HALF + EYE[2]]
    wp = work + o
    sight = wp - eye
    own = WORK_OBJECT | SIGHT_WORK.get(i, set())
    occluders = sorted({m.name for m in parts if m.name not in own and _segment_meets_mesh(eye, wp, m.moved(o))})
    pitch = math.degrees(math.atan2(sight[2], math.hypot(sight[0], sight[1])))
    return {"posture": "standing: rays from the capsule's centre at 88 cm. Crouched (half-height 44) is not covered by "
                       "this proof; crouched and native coverage are root's",
            "eligible_positions": len(ok), "grid_cm": step,
            "rays_blocked_by_proposed_proxies": len(blocked_by_proxy), "rays_blocked_by_room_today": len(blocked_by_room),
            "crouched_estimate": {"ray_from_cm": CROUCH_HALF, "rays_blocked_by_proposed_proxies": len(crouched),
                                  "note": "a CPU estimate on the same plan positions and boxes, not root's coverage"},
            "work_stand_eligible": eligible(i, stand[0], stand[1], pw),
            "work_stand_ray_clear": not any(segment_hits_box(stand + [0, 0, RAY_FROM_Z], ray_end, lo, hi) for lo, hi in pw + walls),
            "capsule_gap_cm": round(capsule_gap, 2), "eye_to_work_cm": round(float(np.linalg.norm(sight)), 1),
            "eye_pitch_deg": round(pitch, 1), "sight_occluded_by": occluders,
            "proxy_tops_cm": [round(float(hi[2]), 1) for lo, hi in proxies]}


def _capsule_gap(stand, mesh):
    """The plan gap between the hero's capsule at the stand and a mesh's bounds (cm), if the mesh rises into the
    capsule's height. Bounds hold the mesh, so the true gap is at least this."""
    lo, hi = mesh.bounds()
    if hi[2] < stand[2] or lo[2] > stand[2] + 2 * CAPSULE_HALF:
        return float("inf")
    q = np.clip(stand[:2], lo[:2], hi[:2])
    return float(np.linalg.norm(stand[:2] - q) - CAPSULE_R)


def _segment_meets_mesh(a, b, mesh, stop=1.0):
    """Whether the segment a -> a + stop (b - a) crosses any of the mesh's triangles (Moller-Trumbore)."""
    d = (b - a) * stop
    v0, v1, v2 = mesh.verts[mesh.tris[:, 0]], mesh.verts[mesh.tris[:, 1]], mesh.verts[mesh.tris[:, 2]]
    e1, e2 = v1 - v0, v2 - v0
    p = np.cross(d, e2)
    det = (e1 * p).sum(1)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    s = a - v0
    u = (s * p).sum(1) * inv
    q = np.cross(s, e1)
    w = (q * d).sum(1) * inv          # the second barycentric
    t = (e2 * q).sum(1) * inv
    hit = ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 1e-6) & (t < 1.0)
    return bool(hit.any())


# --- First-person view ------------------------------------------------------------------------------------------------
VIEW_MARGIN_DEG = 2.0
DIAL_FACING_DEG = 65.0                       # the dial reads from within this angle of its face's normal
BAND_MIN_DEG = 2.0                           # the release band subtends at least this (about 41 px at 1920 across)


def key_points(i):
    """Each station's elements the hero must see while working it, as station-frame sample points:
    {element: (points, meshes of the element itself)}."""
    if i == 0:
        lift = lantern_centre(0)
        band = (gauge_angle(BEND_MS - BEND_TOL_MS), gauge_angle(BEND_MS + BEND_TOL_MS))
        dial = [dial_point(a, r, 0.1) for a in (*GAUGE["angles_deg"], *band) for r in (GAUGE["band_r"][0], GAUGE["band_r"][1] + 0.5)]
        dial += [dial_point(a, GAUGE["band_r"][1] - 0.4, 0.45) for a in np.linspace(*GAUGE["angles_deg"], 7)]   # the needle's tip
        dial.append(np.array(GAUGE["pivot"]) - [0.45, 0, 0])
        hoops = [lift + [-r - HOOP_T, 0.0, z] for z, r in zip(hoop_z(), hoop_r())]
        return {"gauge": (dial, {"SM_B09_FlexGauge"}), "hoops": (hoops, WORK_OBJECT)}
    if i == 1:
        _, sockets, _, _ = station_parts(1)
        # The worked seam on the tilted frame, rim line to rim line (Seam_0..8).
        return {"seam": ([sockets[f"Seam_{j}"][0] for j in range(9)], WORK_OBJECT)}
    if i == 2:
        _, sockets, _, _ = station_parts(2)
        # The remaining swath the stroke finishes (Coordination 268), from the top rim line down (OilSwath_0..8).
        return {"oil swath": ([sockets[f"OilSwath_{j}"][0] for j in range(9)], set())}
    _, sockets, _, _ = station_parts(3)
    return {"shells": ([sockets[k][0] for k in ("ShellSeat1", "ShellSeat2", "ShellSeat3", "WrapSpot")], {"SM_B09_ShellRack", "SM_B09_WrapPaper"}),
            "fuses": ([sockets[f"FuseCheck{k}"][0] for k in (1, 2, 3)], set())}


# OPEN DEFECTS of the first-person view from the craft stand (station, aspect, element): measured, not passed. Each
# element is required; a failing one is listed here and kept as an expected failure until a layout repair lands.
# Coordination 252: a span over the frame explains a defect; it is not a readability pass. The working region's view
# gate (b09_craft_region.view_gate, every admitted stand and facing) is the stronger requirement.
# The first-person defects open on today's layouts (first_person at a 30 cm step, measured 2026-11-01), each asserted
# as required and failing in test_b09_workshop_craft.ViewDefects:
_GAUGE_OPEN = ("passes at the craft stand (facing 46.7 deg, band 8.66 deg), but from only 44.62 % of the 65 working-side "
               "positions (90 % required): the dial, scaled 0.7 to fit beside the form, shows its 640-960 ms band under "
               "2 deg beyond about 2 m, and from the right the form hides it, the dial standing level with the form's "
               "left side (open: the rib repair)")
_SEAM_OPEN = ("during the last panel's stroke the seam's top end at the upper rim line (Seam_8) hides behind the third "
              "pasted gore (SM_B09_Washi3) from the craft stand, and the seam passes from 63.24 % of the 68 working-side "
              "positions (90 % required); the region's view gate fails on the same sample (open: the paste's top end)")
OPEN_VIEW_DEFECTS = {
    ("st_b09_rib_form", "16:9", "gauge"): _GAUGE_OPEN,
    ("st_b09_rib_form", "21:9", "gauge"): _GAUGE_OPEN,
    ("st_b09_paste_bench", "16:9", "seam"): _SEAM_OPEN,
    ("st_b09_paste_bench", "21:9", "seam"): _SEAM_OPEN,
}
# Withdrawn with the whole-lantern oil stroke (Coordination 268 replaced it by the remaining swath): its record, as last
# measured on signed 0a64ce6b.
WITHDRAWN_VIEW_DEFECTS = {
    ("st_b09_oil_rack", "16:9", "oil front stroke"):
        "its bottom socket, at the bottom mouth (OilStroke0_8), hides under the lantern's lower bulge from the craft "
        "stand's eye (the paste seam's bottom end is reported for the same reason; whether the oil's may be is root's); "
        "from the working side it passes from 77.8 % of positions, under the required 90 % (97 % at z 130, before the "
        "view repair lowered the lantern for 21:9)",
    ("st_b09_oil_rack", "21:9", "oil front stroke"):
        "as at 16:9: its bottom socket hides under the lower bulge. (Its height, 38.6 deg at z 116, now fits 21:9's 45.4.)",
}
# Closed by the view repair (the lanterns at 110 and 116): the paste seam whole at 21:9 (it spanned 55.5 deg).


def frame_height_deg(aspect, hfov=WORLD_HFOV_DEG, margin=VIEW_MARGIN_DEG):
    """The frame's usable height (deg) at an aspect: the hero's camera keeps hfov across."""
    return 2.0 * (math.degrees(math.atan(math.tan(math.radians(hfov / 2)) / aspect)) - margin)


def vertical_span_deg(eye, points):
    """The elevations (deg) the points span, from the eye: no pitch frames them in less."""
    el = [math.degrees(math.atan2(p[2] - eye[2], math.hypot(p[0] - eye[0], p[1] - eye[1]))) for p in points]
    return max(el) - min(el)


def _camera(eye, target):
    f = np.asarray(target, float) - eye
    f /= np.linalg.norm(f)
    r = np.cross([0.0, 0.0, 1.0], f)
    r /= np.linalg.norm(r)
    return f, r, np.cross(f, r)


def in_view(eye, target, points, aspect, hfov=WORLD_HFOV_DEG, margin=VIEW_MARGIN_DEG):
    """Whether every point is inside the camera's frame, `margin` deg in from its edges, looking from eye at target.
    The frame keeps `hfov` across and loses height at wider aspects, as the hero's camera does."""
    f, r, u = _camera(eye, target)
    tx = math.tan(math.radians(hfov / 2 - margin))
    ty = math.tan(math.atan(math.tan(math.radians(hfov / 2)) / aspect) - math.radians(margin))
    for p in points:
        d = np.asarray(p, float) - eye
        z = d @ f
        if z <= 0 or abs(d @ r) / z > tx or abs(d @ u) / z > ty:
            return False
    return True


def view_check(i, eye, meshes, aspect):
    """For each key element of station i (station frame): in the frame looking at the work, unoccluded by the
    station's other meshes, and, for the gauge, facing the eye and large enough to read."""
    _, _, _, work = station_parts(i)
    out = {}
    for name, (points, own) in key_points(i).items():
        others = [m for m in meshes if m.name not in own]
        visible = in_view(eye, work, points, aspect)
        occluded = [m.name for m in others if any(_segment_meets_mesh(eye, eye + (p - eye) * 0.995, m) for p in points)]
        row = {"in_frame": visible, "occluded_by": sorted(set(occluded))}
        if name == "gauge":
            g = np.array(GAUGE["pivot"])
            to_eye = (eye - g) / np.linalg.norm(eye - g)
            row["facing_deg"] = round(math.degrees(math.acos(np.clip(to_eye @ [-1.0, 0.0, 0.0], -1, 1))), 1)
            rm = sum(GAUGE["band_r"]) / 2
            a, b = (dial_point(gauge_angle(ms), rm, 0.1) - eye for ms in (BEND_MS - BEND_TOL_MS, BEND_MS + BEND_TOL_MS))
            row["band_deg"] = round(math.degrees(math.acos(np.clip(a @ b / np.linalg.norm(a) / np.linalg.norm(b), -1, 1))), 2)
            row["ok"] = visible and not occluded and row["facing_deg"] <= DIAL_FACING_DEG and row["band_deg"] >= BAND_MIN_DEG
        else:
            row["ok"] = visible and not occluded
        out[name] = row
    return out


def approach_positions(i, step=10.0):
    """The working side: eligible positions in front of the bench (station frame x <= -40) within 60 deg of the
    approach (-X), in station-frame cm."""
    sx, sy = STATIONS[i][1]
    o = np.array([sx, sy, floor_at(sx, sy)])
    pw = []
    for j, (_, (xj, yj)) in enumerate(STATIONS):
        oj = np.array([xj, yj, floor_at(xj, yj)])
        pw += [(lo + oj, hi + oj) for lo, hi in station_parts(j)[2]]
    out = []
    for lx in np.arange(-REACH_CM, -40.0 + 1e-9, step):
        for ly in np.arange(-REACH_CM, REACH_CM + 1e-9, step):
            if abs(ly) <= math.tan(math.radians(60.0)) * -lx and eligible(i, sx + lx, sy + ly, pw):
                out.append(np.array([lx, ly, 0.0]))
    return out


def first_person(i, step=10.0):
    """Station i's first-person check: at the work stand, and the share of the working side's positions at which each
    element passes, for each aspect."""
    parts, sockets, proxies, work = station_parts(i)
    meshes = list(parts)
    if i == 0:                                                   # mid-bend: three hoops wound, the fourth at 0.75
        yaw = form_yaw_deg(3, 0.75)
        for m in [form()] + [hoop(k) for k in range(1, 4)] + [hoop(4, 0.75)]:
            meshes.append(Mesh(m.name, to_station(m.verts, yaw, lantern_centre(0)), m.tris, m.slot, {}, m.collision, m.tri_slots))
    elif i == 1:
        # The last panel's stroke: the gores already pasted on the tilted frame as it stands for the fourth panel
        # (b09_craft_poses lays them so), the seam's own one aside.
        meshes += [Mesh(f"SM_B09_Washi{k}", paste_frame(gore(k).verts, 4), gore(k).tris, "M_B09_Washi")
                   for k in PASTE_ORDER[:3]]
    elif i == 2:
        meshes += [m.moved(sockets["LanternHang"][0] - hang_point()) for m in lantern("finished")]
    eye_of = lambda pos: pos + [EYE[0], EYE[1], CAPSULE_HALF + EYE[2]]  # noqa: E731
    stand = craft_stand(i)
    out = {"hfov_deg": WORLD_HFOV_DEG, "margin_deg": VIEW_MARGIN_DEG, "stand": {}, "approach": {}}
    positions = approach_positions(i, step)
    out["approach_positions"] = len(positions)
    for label, aspect in ASPECTS.items():
        out["stand"][label] = view_check(i, eye_of(stand), meshes, aspect)
        tally = {}
        for pos in positions:
            for name, row in view_check(i, eye_of(pos), meshes, aspect).items():
                tally.setdefault(name, []).append(row["ok"])
        out["approach"][label] = {name: round(float(np.mean(v)), 4) for name, v in tally.items()}
    return out


def hanging_clearance():
    """The hanging output: every lantern clear of the hero's head over its floor, of the ceiling, of the walls, and of
    its neighbours."""
    hp = hang_point()
    rows, low = [], []
    for p, i, point, yaw in slots():
        centre = point - hp
        bottom = centre[2] - LANTERN_H / 2 - RIM_H / 2
        fz = floor_at(point[0], point[1])
        rows.append({"slot": p * 10 + i + 1, "bottom_above_head_cm": round(bottom - (fz + HEAD_TOP_CM), 1)})
        low.append(bottom - (fz + HEAD_TOP_CM))
    xs = np.array(SLOT_X)
    return {"slots": len(rows), "min_head_clear_cm": round(float(min(low)), 1),
            "hook_top_below_ceiling_cm": round(CEILING_Z - (POLE_Z + 2.0), 1),
            "neighbour_gap_cm": round(float(np.diff(xs).min() - 2 * LANTERN_R), 1),
            "pole_gap_cm": round(float(np.diff(sorted(POLES_Y)).min() - 2 * LANTERN_R), 1),
            "inside_room": bool(POLE_X[0] > 1606 and POLE_X[1] < 2314 and min(POLES_Y) > -1494 and max(POLES_Y) < -406)}


def bore_fit():
    r_clear = (WEAPON7["bore_cm"] - SHELL["wrapped_cm"]) / 2
    return {"bore_cm": WEAPON7["bore_cm"], "wrapped_shell_cm": SHELL["wrapped_cm"], "radial_clear_mm": round(r_clear * 10, 2)}


# --- The spec ---------------------------------------------------------------------------------------------------------
# Root's view (SoraWorkshopCraftRules::FView, read as FSoraKitView::LanternCraft at 2a846a6a): Active, RecipeComplete,
# Assist; Step; Committed[6] in recipe order; HeldStep (-1 idle) and HeldMs; FailedStripSerial and FailedStripAgeMs (-1
# absent). The presentation reads it and never advances it. A new press clears the split pose, pause or cancel clears
# held work, and a retry clears the failure, all in root's state. The art keeps no state of its own.
# At 541c61ae it adds LastAction (Serial, Step, Unit, AgeMs): the latest credited unit, its age saturating at
# ActionPresentationMs. The press clips (rims, shells, inspection) start on a new Serial and end by that age
# (workshop-action-view.md); a presenter may not stretch arms, move the camera or player, or delay accounting.
VIEW_CONTRACT = ("SoraWorkshopCraftRules::FView via FSoraKitView::LanternCraft: Active, RecipeComplete, Assist, Step, "
                 "Committed[6], HeldStep, HeldMs, FailedStripSerial, FailedStripAgeMs, LastAction (Serial, Step, Unit, "
                 "AgeMs; AgeMs saturates at ActionPresentationMs 1200)")
SPLIT_SHOW_MS = 1200                         # a suggestion: how long the split strip lies on the bench (root's choice)
STATES = {
    "st_b09_rib_form": [
        {"view": "Committed[0] = n (0..6)", "shows": "SM_B09_RibForm and SM_B09_Hoop1..n, in the form's frame, at "
                                                     "LanternCentre, turned by form_yaw_deg(n, 0)"},
        {"view": "HeldStep == 0, HeldMs", "shows": "one-ended winding: hoop n+1's strip, hooked in its notch, at "
                                                   "flex_stage(HeldMs) (SM_B09_Hoop{n+1}_Flex000..075, then Hoop{n+1}), "
                                                   "and the form turned by form_yaw_deg(n, flex), so the strip leaves "
                                                   "at the front for the paws (WindPress, WindGuide); the needle along "
                                                   "gauge_angle(HeldMs)"},
        {"view": "HeldStep == -1", "shows": "the needle at rest (gauge_angle(0), -90 deg); no strip on the form"},
        {"view": "FailedStripAgeMs >= 0", "shows": f"SM_B09_SplitStrip at SplitStripRest while FailedStripAgeMs < {SPLIT_SHOW_MS} "
                                                    "(suggested), then a fresh strip; a new press clears it (root's -1)"},
        {"view": "Assist", "shows": "the same gauge; the strip completes at 800 ms (the rules' assist pass)"}],
    "st_b09_paste_bench": [
        {"view": "Committed[0] == 6", "shows": "the frame with all six hoops on its cradle (the bends are done to come here)"},
        {"view": "Committed[1] = n (0..4)", "shows": "SM_B09_Washi for PASTE_ORDER[:n] on the frame, turned by "
                                                     "panel_turn_deg(n + 1) so panel n + 1's seam faces the hero; the "
                                                     "rail keeps sheets n+1..4 (sheet n+1 in the left paw while a paste "
                                                     "is held)"},
        {"view": "HeldStep == 1, HeldMs", "shows": "STATE_CONTRACT: the sheet laid (0-400 ms) and held at SheetHold, "
                                                   "the brush along Seam_0..8 (400-1500 ms); paste only where the "
                                                   "bristles have swept"},
        {"view": "Committed[2] == 1", "shows": "SM_B09_RimTop from RimTopRest to RimTopSeat: a press clip (root's "
                                               "last-action serial and age); the bottom rim is fitted from the start "
                                               "(RimBottomSeat). Open: on the paste pose the upper mouth is out of "
                                               "reach; the cradle must re-tilt the frame for it (STATE_CONTRACT)"}],
    "st_b09_oil_rack": [
        {"view": "Committed[2] == 1, Committed[3] == 0", "shows": "the papered, rimmed lantern (bail fitted, form drawn "
                                                                  "out) on LanternHang, oiled but for its remaining "
                                                                  "swath; before that the rack is empty"},
        {"view": "HeldStep == 3, HeldMs", "shows": "STATE_CONTRACT: the brush from OilDip to the swath's top, then down "
                                                   "OilSwath_0..8; the washi wet only where the bristles have swept; "
                                                   "the other paw's fingertips steady the lantern (LanternSteady)"},
        {"view": "Committed[3] == 1", "shows": "the rack empties; the lantern hangs at PLAYER_SLOT in the rafters"}],
    "st_b09_shell_bench": [
        {"view": "Committed[4] = n (0..3)", "shows": "n wrapped shells seated (ShellSeat1..n) in the rack's cups; 3 - n "
                                                     "cores in the tray. Each press: a clip, the core taken, wrapped "
                                                     "and twisted over the paper (WrapSpot) and seated"},
        {"view": "Committed[5] == 1", "shows": "the fuses checked (Coordination 277): a press clip, the left paw over "
                                               "the three seated shells' fuse cord tips (FuseCheck3 to FuseCheck1); "
                                               "weapon 7, the tube, stands in its block behind the board, clear of "
                                               "the hand path, and is handed over at the beat's end"}],
    "all": [
        {"view": "RecipeComplete (later checkpoints)", "shows": "every station in its finished state and all 40 slots filled"},
        {"view": "!Active && !RecipeComplete", "shows": "every station at its start; the suggested 24 craftspeople's lanterns"}],
}


def spec():
    out = {"schema": 1, "generator": "scripts/art/b09_workshop_craft.py", "inputs": INPUTS,
           "frames": "Unreal cm, Z up. A station's frame: its origin is the station point on its floor (world X, Y, "
                     "FloorAt), with the world's axes. The hero works from -X, facing +X.",
           "view_contract": VIEW_CONTRACT, "states_all": STATES["all"], "state_contract_common": STATE_CONTRACT["common"],
           "inspect_decision": ("Coordination 277: the single Inspect unit checks the three completed festival shells' fuse "
                                "cords (FuseCheck3 to FuseCheck1); nothing is lit, loaded or discharged; recipe counts, "
                                "timing, reward and b10's charge fuse are unchanged; weapon 7 stays visibly supported in "
                                "its block, clear of the hand path. A presentation decision, not a contact-gate waiver"),
           "recipe": {"steps": [{"step": k, "kind": kind, "count": n, "station": STATIONS[STEP_STATIONS[k]][0]}
                                for k, (kind, n) in enumerate(STEPS)], "bend_ms": [BEND_MS, BEND_TOL_MS], "paste_ms": PASTE_MS,
                      "output_lanterns": OUTPUT_LANTERNS},
           "collision": "every mesh is visual only; root keeps or replaces its boxes with the proposed proxies. Each "
                        "proxy is under the standing station trace's 88 cm start, so no standing ray meets one. That "
                        "covers the standing capsule only: crouched (half-height 44) the trace starts at 44 cm, and "
                        "proxy tops of 75-78 cm can block close crouched approaches, as today's generic benches can. "
                        "Crouched and native coverage are root's",
           "lantern": {"height_cm": LANTERN_H, "diameter_cm": 2 * LANTERN_R, "rim_diameter_cm": 2 * LANTERN_RIM_R,
                       "hoop_heights_cm": [round(float(z), 3) for z in hoop_z()], "hoop_radii_cm": [round(float(r), 3) for r in hoop_r()],
                       "hang_point_cm": hang_point().round(3).tolist(), "flex_stages": list(FLEX_STAGES),
                       "wind_deg": WIND_DEG, "form_yaw": "wind_deg * (Committed[0] + FLEX_STAGES[flex_stage(HeldMs)]) "
                                                          "while bending, else wind_deg * Committed[0]",
                       "pivot": "its centre (lantern frame); at the rib form and paste bench it sits at the station point"},
           "camera": {"world_hfov_deg": WORLD_HFOV_DEG, "aspects": list(ASPECTS), "margin_deg": VIEW_MARGIN_DEG,
                      "dial_facing_max_deg": DIAL_FACING_DEG, "band_min_deg": BAND_MIN_DEG,
                      "note": "a CPU geometric estimate of framing from the standing eye; it does not establish Unreal framing, "
                              "materials or hand contact"},
           "lantern_centre_by_station_cm": {STATIONS[k][0]: lantern_centre(k).tolist() for k in LANTERN_Z},
           "gauge": {"pivot_cm": list(GAUGE["pivot"]), "angles_deg": list(GAUGE["angles_deg"]), "full_ms": GAUGE["full_ms"],
                     "band_radii_cm": list(GAUGE["band_r"]), "face_radius_cm": GAUGE["face_r"], "ticks_ms": list(GAUGE["ticks_ms"]),
                     "needle": "points along (0, sin a, cos a) in the station frame, a = gauge_angle(ms)",
                     "green_band_deg": [round(gauge_angle(BEND_MS - BEND_TOL_MS), 2), round(gauge_angle(BEND_MS + BEND_TOL_MS), 2)]},
           "shells": dict(SHELL, bore_fit=bore_fit()),
           # For review captures only: root's solids as (centre, size); collision stays root's.
           "room": {"solids_cm": [np.concatenate([c, s]).round(3).tolist() for c, s in SOLIDS],
                    "floor_slabs": list(FLOOR_SLABS),
                    "ceilings": [k for k, (c, s) in enumerate(SOLIDS) if c[2] - s[2] / 2 >= CEILING_Z],
                    "surfaces": list(SOLID_SURFACES),
                    "source": "SoraLanternWorkshopRules::Solids (the ground slab left out)"},
           "stations": [], "hanging_output": {}}
    for i, (sid, (x, y)) in enumerate(STATIONS):
        parts, sockets, proxies, work = station_parts(i)
        row = {"id": sid, "index": i, "world_cm": [x, y], "floor_cm": floor_at(x, y),
               "steps": [k for k, s in enumerate(STEP_STATIONS) if s == i],
               "work_stand": {"local_cm": craft_stand(i).tolist(), "yaw_deg": 0.0,
                              "note": "the craft stand: the capsule 1 cm clear of the proxy's front (b09_craft_poses.py)"},
               "work_point_cm": [round(float(c), 2) for c in work],
               "parts": [], "sockets": {}, "collision_proxies": [], "states": STATES[sid], "clearance": clearance(i)}
        for m in parts:
            lo, hi = m.bounds()
            row["parts"].append({"name": m.name, "slots": sorted(set(m.slots())), "triangles": int(len(m.tris)),
                                 "bounds_cm": [lo.round(2).tolist(), hi.round(2).tolist()],
                                 "pivot": "station frame origin", "collision": m.collision})
        for name, (p, xa, za) in sorted(sockets.items()):
            row["sockets"][name] = {"cm": np.round(p, 3).tolist()} | ({"x_axis": np.round(xa, 6).tolist()} if xa is not None else {}) | \
                ({"z_axis": np.round(za, 6).tolist()} if za is not None else {})
        for lo, hi in proxies:
            row["collision_proxies"].append({"lo_cm": np.round(lo, 2).tolist(), "hi_cm": np.round(hi, 2).tolist()})
        row["state_meshes"] = []
        for m, pivot, where in state_meshes(i):
            lo, hi = m.bounds()
            row["state_meshes"].append({"name": m.name, "slots": sorted(set(m.slots())), "triangles": int(len(m.tris)), "pivot": pivot,
                                        "placed_at": where, "bounds_cm": [lo.round(2).tolist(), hi.round(2).tolist()],
                                        "attributes": sorted(m.attrs), "collision": m.collision})
        row["first_person"] = first_person(i, step=20.0)
        # The working region, the presenter's states, the contact paths and the supports (Coordinations 268-277).
        import b09_craft_region as R_
        import b09_craft_poses as P_
        import b09_prop_clash as C_
        row["region"] = R_.region_spec(i)
        row["state_contract"] = STATE_CONTRACT[sid]
        row["actions"] = P_.action_summary(i)
        row["supports"] = [{"state": label, "rests": [list(pair) for pair in pairs]} for label, _, pairs in C_.scenes(i)]
        if i == 1:
            row["paste_order"] = list(PASTE_ORDER)
            row["panel_turn_deg"] = [panel_turn_deg(k) for k in (1, 2, 3, 4)]
            row["adhesive_mask"] = ("paste only where the bristles have swept: the union of the brush's bristle edge (its "
                                    "two corners, PASTE_BRUSH_W apart) along Seam_0..8 up to HeldMs; nothing beyond it")
        if i == 2:
            row["wetness_mask"] = {"swath_sockets": [f"OilSwath_{j}" for j in range(9)], "swath": dict(OIL_SWATH),
                                   "rule": "wet only where the bristles have swept: the union of the bristle edge's "
                                           "footprint along OilSwath_0..8 up to HeldMs; the rest of the lantern was "
                                           "oiled before (Committed[2]) and the remaining swath is what the hold finishes"}
        out["stations"].append(row)
    lantern_parts = {}
    for stage in ("frame", "papered", "rimmed", "finished"):
        meshes = lantern(stage)
        lo = np.min([m.bounds()[0] for m in meshes], 0)
        hi = np.max([m.bounds()[1] for m in meshes], 0)
        lantern_parts[stage] = {"meshes": sorted({m.name for m in meshes}), "bounds_cm": [lo.round(2).tolist(), hi.round(2).tolist()]}
    out["lantern"]["stages"] = lantern_parts
    out["hanging_output"] = {"poles_y_cm": list(POLES_Y), "pole_z_cm": POLE_Z, "pole_x_cm": list(POLE_X),
                             "slots": [{"slot": p * 10 + i + 1, "hook_cm": np.round(hp, 2).tolist(), "yaw_deg": round(yaw, 2)}
                                       for p, i, hp, yaw in slots()],
                             "player_slot": PLAYER_SLOT, "lantern_pivot": "its hang point (the bail's ring) on the hook",
                             "clearance": hanging_clearance(),
                             "suggested_fill": "root's, from the completion mask: e.g. 24 of the craftspeople's lanterns from the start, "
                                               "the player's at PLAYER_SLOT once the oil step completes, and all 40 at the beat's end"}
    return out


# --- The candidate assets (create_b09_workshop_craft.py builds them; check_b09_candidates_fbx.py checks them) ---------
STATION_ASSETS = {0: "SM_B09_RibFormStation", 1: "SM_B09_PasteStation", 2: "SM_B09_OilStation", 3: "SM_B09_ShellStation"}


def candidates():
    """The candidate assets in export order: [(name, mesh, sockets {name: (point, x | None, z | None)}, frame,
    lantern_frame)].
    - Each station's static mesh, in the station frame. The paste bench's form and hoops are split out as
      SM_B09_PasteFrame (lantern frame), since the cradle turns them with it.
    - Every state mesh, in its own frame (state_meshes).
    - The drying poles and their 40 hooks, in world cm, placed at the world origin."""
    out = []
    for i, (sid, _) in enumerate(STATIONS):
        parts, sockets, proxies, work = station_parts(i)
        if i == 0:
            out.append(("SM_B09_RibForm", form(), {}, "the form's frame (place at LanternCentre; turned by form_yaw_deg)", True))
        if i == 1:
            frame_names = {"SM_B09_Form"} | {f"SM_B09_Hoop{k}" for k in range(1, 7)}
            frame = [m.moved(-lantern_centre(1)) for m in parts if m.name in frame_names]
            parts = [m for m in parts if m.name not in frame_names]
            out.append(("SM_B09_PasteFrame", merge("SM_B09_PasteFrame", frame), {},
                        "lantern frame (place at LanternCentre; turns about Z)", True))
        name = STATION_ASSETS[i]
        socks = dict(sockets)
        out.append((name, merge(name, parts), socks, f"station frame ({sid})", False))
        for m, pivot, where in state_meshes(i):
            out.append((m.name, m, {}, f"{pivot}; placed at {where}", pivot.startswith("the lantern's centre")))
    poles, hooks = hanging_parts()
    out.append(("SM_B09_DryingPoles", poles, {}, "world cm (place at the world origin)", False))
    out.append(("SM_B09_SlotHooks", hooks, {}, "world cm (place at the world origin)", False))
    return out


def reveal_uv(mesh, lantern_frame):
    """UV1 (`Reveal`) per vertex: the module's (height_frac, azimuth_frac) where the mesh has them; for a lantern-frame
    mesh, its height across the lantern and its azimuth; else zeros. The washi's paste and oil masks read U."""
    if "height_frac" in mesh.attrs:
        return np.stack([mesh.attrs["height_frac"], mesh.attrs["azimuth_frac"]], 1)
    if lantern_frame:
        v = mesh.verts
        h = np.clip((v[:, 2] + LANTERN_H / 2) / LANTERN_H, 0.0, 1.0)
        a = (np.arctan2(v[:, 1], v[:, 0]) / (2 * math.pi)) % 1.0
        return np.stack([h, a], 1)
    return np.zeros((len(mesh.verts), 2))


def box_uv(mesh):
    """UV0 per triangle corner, (n_tris, 3, 2) in the module's corner order, in metres: the mesh's own mapping from its
    construction (sweep: along the path; revolve: round the widest radius) where it has one. Otherwise a box
    projection, each triangle along its normal's dominant axis. The materials scale metres to their tile."""
    if mesh.tri_uv0 is not None:
        return np.asarray(mesh.tri_uv0, float)
    t = mesh.tris
    n = np.cross(mesh.verts[t[:, 1]] - mesh.verts[t[:, 0]], mesh.verts[t[:, 2]] - mesh.verts[t[:, 0]])
    keep = np.array([[1, 2], [0, 2], [0, 1]])[np.argmax(np.abs(n), 1)]
    p = mesh.verts[t] / 100.0
    return np.take_along_axis(p, np.repeat(keep[:, None, :], 3, 1), 2)


# --- Unreal's build ---------------------------------------------------------------------------------------------------
THRESH_POINTS_ARE_SAME = 2e-5                # cm (UnrealMathUtility.h): corners this close in every component are one
MIN_EDGE_CM = 1e-3                           # the host gate: 50 x that, so no candidate edge comes near it


def unreal_degenerate(mesh):
    """Per triangle: two corners within THRESH_POINTS_ARE_SAME in every component (FVector::Equals). Unreal's
    static-mesh build drops such triangles; s147 lost 128 pole slivers from each shell."""
    v = mesh.verts[mesh.tris]
    same = lambda a, b: (np.abs(a - b) <= THRESH_POINTS_ARE_SAME).all(1)  # noqa: E731
    return same(v[:, 0], v[:, 1]) | same(v[:, 1], v[:, 2]) | same(v[:, 2], v[:, 0])


def shortest_edge(mesh):
    v = mesh.verts[mesh.tris]
    return float(np.linalg.norm(v - np.roll(v, -1, axis=1), axis=2).min())


# --- Previews (presentation only) ---------------------------------------------------------------------------------------
COLOURS = {"M_B09_GaugeFace": (0.86, 0.82, 0.70), "M_B09_GaugeBand": (0.16, 0.62, 0.30), "M_B09_GaugeMarks": (0.08, 0.07, 0.07),
           "M_B09_GaugeNeedle": (0.80, 0.20, 0.10),
           "M_B09_TimberBench": (0.42, 0.30, 0.19), "M_B09_TimberForm": (0.70, 0.57, 0.40), "M_B09_Bamboo": (0.78, 0.70, 0.43),
           "M_B09_Washi": (0.93, 0.91, 0.85), "M_B09_RimLacquer": (0.08, 0.07, 0.07), "M_B09_Iron": (0.16, 0.16, 0.17),
           "M_B09_Ceramic": (0.32, 0.22, 0.16), "M_B09_Bristle": (0.62, 0.55, 0.42),
           "M_B09_ShellPaper": (0.72, 0.60, 0.45), "M_B09_ShellCore": (0.55, 0.45, 0.36), "M_B09_Twine": (0.52, 0.40, 0.25),
           "M_B09_FuseCord": (0.20, 0.18, 0.16), "M_B09_Cord": (0.50, 0.42, 0.30), "Proxy": (0.9, 0.2, 0.2)}


def render(meshes, eye, target, fov_deg, size=(1280, 720), light=(-0.4, 0.3, 0.86)):
    """A plain z-buffered, Lambert-shaded raster of the meshes (Unreal axes; +Y is drawn to the right as Unreal does)."""
    w, h = size
    f = np.asarray(target, float) - eye
    f /= np.linalg.norm(f)
    r = np.cross([0.0, 0.0, 1.0], f)            # Unreal's right (left-handed): Z x forward
    r /= np.linalg.norm(r)
    u = np.cross(f, r)
    th = math.tan(math.radians(fov_deg) / 2)
    img = np.full((h, w, 3), 0.18)
    z = np.full((h, w), np.inf)
    L = np.asarray(light, float) / np.linalg.norm(light)
    for m in meshes:
        v = m.verts - eye
        d = v @ f
        x = (v @ r) / np.maximum(d, 1e-3) / th
        y = (v @ u) / np.maximum(d, 1e-3) / th * (w / h)
        px = (x + 1) * 0.5 * w
        py = (1 - y) * 0.5 * h
        tri = m.tris
        nrm = np.cross(m.verts[tri[:, 1]] - m.verts[tri[:, 0]], m.verts[tri[:, 2]] - m.verts[tri[:, 0]])
        nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
        shade = 0.35 + 0.65 * np.abs(nrm @ L)
        bases = np.array([COLOURS.get(sl, (0.6, 0.6, 0.6)) for sl in m.slots()])
        for t_, s_, base in zip(tri, shade, bases):
            if (d[t_] < 1.0).any():
                continue
            xs, ys = px[t_], py[t_]
            x0, x1 = int(max(0, math.floor(xs.min()))), int(min(w - 1, math.ceil(xs.max())))
            y0, y1 = int(max(0, math.floor(ys.min()))), int(min(h - 1, math.ceil(ys.max())))
            if x0 > x1 or y0 > y1:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            (ax, ay), (bx, by), (cx, cy) = zip(xs, ys)
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-12:
                continue
            l0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
            l1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
            l2 = 1 - l0 - l1
            inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
            if not inside.any():
                continue
            depth = l0 * d[t_[0]] + l1 * d[t_[1]] + l2 * d[t_[2]]
            zs = z[y0:y1 + 1, x0:x1 + 1]
            nearer = inside & (depth < zs)
            zs[nearer] = depth[nearer]
            img[y0:y1 + 1, x0:x1 + 1][nearer] = base * s_
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def previews(out):
    from PIL import Image, ImageDraw
    out = Path(out)
    if out.exists():
        raise SystemExit(f"{out} exists")
    out.mkdir(parents=True)
    files = {}
    for i, (sid, (x, y)) in enumerate(STATIONS):
        parts, sockets, proxies, work = station_parts(i)
        meshes = list(parts)
        lift = lantern_centre(i) if i in LANTERN_Z else None
        if i == 0:
            yaw = form_yaw_deg(3, 0.75)
            for m in [form()] + [hoop(k) for k in range(1, 4)] + [hoop(4, 0.75)]:
                meshes.append(Mesh(m.name, to_station(m.verts, yaw, lift), m.tris, m.slot, {}, m.collision, m.tri_slots))
        elif i == 1:
            meshes += [m.moved(lift) for m in lantern("frame")[:6]] + [gore(1).moved(lift), gore(2).moved(lift)]
            sheets = {m.name: m for m, _, _ in state_meshes(1)}
            meshes += [sheets[f"SM_B09_WashiSheet{j}"].moved(sockets[f"WashiSheet{j}"][0]) for j in (1, 2)]   # 4 - 2 left
        elif i == 2:
            hp = sockets["LanternHang"][0]
            meshes += [m.moved(hp - hang_point()) for m in lantern("finished")]
        else:
            origin, rot = weapon_rest()
            # A stand-in for SM_Weapon_07 (the existing asset, placed at WeaponRest): its culm, in previews only.
            culm = sweep("SM_Weapon_07_StandIn", [origin + rot @ [WEAPON7["x_range_cm"][0], 0, 0], origin + rot @ [WEAPON7["x_range_cm"][1], 0, 0]],
                         "M_B09_Bamboo", radius=WEAPON7["culm_cm"] / 2, segments=16)
            meshes.append(culm)
            for k in (1, 2):
                meshes.append(shell("wrapped").moved(sockets[f"ShellSeat{k}"][0]))
            meshes.append(shell("core").moved(sockets["ShellCore3"][0]))
        stand = craft_stand(i)
        eye = stand + [EYE[0], EYE[1], CAPSULE_HALF + EYE[2]]
        if i == 0:
            meshes.append(needle_at(BEND_MS))                    # in the band, at the ideal release
        img = render(meshes, eye, work, WORLD_HFOV_DEG)
        p = out / f"b09_{sid}_hero_eye.png"
        Image.fromarray(img).save(p)
        files[p.name] = p
        if i == 0:
            img = render(meshes, eye, work, WORLD_HFOV_DEG, size=(1680, 720))
            p = out / f"b09_{sid}_hero_eye_21x9.png"
            Image.fromarray(img).save(p)
            files[p.name] = p
            for label, pos in (("front_left", (-150.0, -90.0, 0.0)), ("front_right", (-150.0, 90.0, 0.0))):
                e = np.array(pos) + [EYE[0], EYE[1], CAPSULE_HALF + EYE[2]]
                img = render(meshes, e, work, WORLD_HFOV_DEG)
                p = out / f"b09_{sid}_approach_{label}.png"
                Image.fromarray(img).save(p)
                files[p.name] = p
        img = render(meshes, np.array([-150.0, -170.0, 210.0]), work, 45.0)
        p = out / f"b09_{sid}_three_quarter.png"
        Image.fromarray(img).save(p)
        files[p.name] = p
    # The lantern's stages side by side, and the plan.
    stages = []
    for k, stage in enumerate(("frame", "papered", "rimmed", "finished")):
        stages += [m.moved([0.0, 40.0 * k - 60.0, 0.0]) for m in lantern(stage)]
    img = render(stages, np.array([-150.0, 0.0, 10.0]), np.array([0.0, 0.0, 0.0]), 50.0)
    p = out / "b09_lantern_stages.png"
    Image.fromarray(img).save(p)
    files[p.name] = p
    img = plan()
    p = out / "b09_plan.png"
    img.save(p)
    files[p.name] = p
    return files


def plan(scale=0.4):
    """Top view: the room, the yard's solids, the stations, their benches, reach and stands, and the 40 slots."""
    from PIL import Image, ImageDraw
    x0, x1, y0, y1 = 1450, 3700, -2500, 200
    w, h = int((x1 - x0) * scale), int((y1 - y0) * scale)
    im = Image.new("RGB", (w, h), (34, 32, 30))
    dr = ImageDraw.Draw(im)
    tx = lambda x: (x - x0) * scale  # noqa: E731
    ty = lambda y: (y1 - y) * scale  # noqa: E731
    for k, (c, size) in enumerate(SOLIDS):
        lo, hi = c - size / 2, c + size / 2
        col = (90, 75, 55) if k == 0 else (60, 58, 56) if k in FLOOR_SLABS else (150, 150, 150) if hi[2] < 400 else (110, 110, 125)
        if k == 9:
            continue                         # the ceiling
        dr.rectangle([tx(lo[0]), ty(hi[1]), tx(hi[0]), ty(lo[1])], outline=col, fill=col if k in FLOOR_SLABS else None)
    for p, i, hp, yaw in slots():
        dr.ellipse([tx(hp[0] - LANTERN_R), ty(hp[1] + LANTERN_R), tx(hp[0] + LANTERN_R), ty(hp[1] - LANTERN_R)],
                   outline=(240, 220, 160) if p * 10 + i + 1 != PLAYER_SLOT else (255, 120, 60))
    for i, (sid, (x, y)) in enumerate(STATIONS):
        parts, sockets, proxies, work = station_parts(i)
        dr.ellipse([tx(x - REACH_CM), ty(y + REACH_CM), tx(x + REACH_CM), ty(y - REACH_CM)], outline=(60, 120, 160))
        for lo, hi in proxies:
            dr.rectangle([tx(x + lo[0]), ty(y + hi[1]), tx(x + hi[0]), ty(y + lo[1])], outline=(220, 70, 60))
        cs = craft_stand(i)
        sx, sy = x + cs[0], y + cs[1]
        dr.ellipse([tx(sx - CAPSULE_R), ty(sy + CAPSULE_R), tx(sx + CAPSULE_R), ty(sy - CAPSULE_R)], outline=(120, 220, 120))
        dr.text((tx(x) + 4, ty(y) - 12), sid.replace("st_b09_", ""), fill=(230, 230, 230))
    return im


def main():
    args = sys.argv[1:]
    if args[:1] == ["--spec"]:
        path = Path(args[1])
        path.write_text(json.dumps(spec(), indent=1, ensure_ascii=False) + "\n")
        print("B09_SPEC", path)
    elif args[:1] == ["--previews"]:
        files = previews(args[1])
        print("B09_PREVIEWS", json.dumps(sorted(files)))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
