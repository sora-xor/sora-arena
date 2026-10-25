# Chapter 6 archive reveal (b09, the family page): art direction, slice 1

**Status (2026-10-25):** direction for root's implementation, from the art
lane. It is based on:
- root's six 602b862 originals (`ArchiveReveal_5ECD6476264527544F26BDAD25DE906E`;
  01_Wide `c3a3dd30…`, 02_RackImpact `2a20fb12…`, 03_FirstLine `7709548f…`,
  04_FamilyPage `6bf13780…`, 05_Reaction `56fbe43a…`, 06_Return `c31cef8c…`;
  root's review `f328ecbd…`). They supersede the 4f3fe61f set
  (`ArchiveReveal_5662A814…`) for layout;
- `docs/campaign/chapter-06.md`: §1.3 L6 (the archive), §1.4 (its lighting),
  §2.6 (the slate's text), and the b09 and b10 lines.

Root owns the archive's C++ and the text layout (602b862 is the layout fix).
This document sets the look, and the values and checks to reach it. Its
targets are design values, to be confirmed in a capture. It is not art
acceptance.

**Root's first pass, as root plans it** (23:3x UTC):
- shelf bays, edge-out slates, dark plaster and local rack lights;
- the exposure isolated to the archive's beats;
- the collision preserved;
- then six frames.

## What the six frames show

| frame | mean luminance (sRGB) | median | p95 | p99 | clipped (any channel at least 250) |
| --- | --- | --- | --- | --- | --- |
| 01_Wide | 0.446 | 0.436 | 0.880 | 0.973 | 1.84 % |
| 02_RackImpact | 0.439 | 0.423 | 0.877 | 0.963 | 1.43 % |
| 03_FirstLine | 0.414 | 0.373 | 0.876 | 0.926 | 0.00 % |
| 04_FamilyPage | 0.412 | 0.371 | 0.871 | 0.921 | 0.00 % |
| 05_Reaction | 0.401 | 0.373 | 0.870 | 0.937 | 0.36 % |
| 06_Return | 0.202 | 0.143 | 0.652 | 0.853 | 0.19 % |

**Fixed by 602b862** (root's font-measured layout):
- the whole record is readable, 買取価格 30 and 単位：石 included;
- both close-ups leave the subtitles clear;
- the text is near-white on the slate's dark face.

The rest of this list stands.

- **The racks are flat cyan walls.** Each long wall is one bright plane, lit
  by a wash that clips near its top. The light reads as a lit wall, not as
  records.
- **The room is a brick box.** The walls read as brick, the 6 m ceiling and
  its beams are unseen, and the floor is the only period surface.
- **The 鷲尾家 slate is a black panel hung on the cyan wall.** It is not a
  record in a rack. Its text now reads.
- **The characters are proxies:**
  - they stand arms-down, with bows and quivers floating beside them;
  - the rival's katana sticks out horizontally from his chest. Root traced
    this to the weapon root hanging from the eye, not a hand (see "The grip
    contract").
- **Nothing is in shadow.** The frame is one level of cyan. A moonless-night
  archive should be mostly dark, with its light in the records and one cold
  rim.

## The look

A converted Edo-period book store (文庫) on a moonless night.
- The room is plaster, dark timber and old boards, its beams overhead.
- Deep timber racks run along both long walls. They hold thousands of small
  alien slates, each glowing faintly cyan along its edge: the room's light
  is its records.
- One high north window lets in cold starlight, which rims the duellists and
  shows the dust that the posts shake from the beams.
- The centre of the room is dark.
- When the 鷲尾家 slate lights, it becomes the brightest thing in the room.
  It is the key on Toranosuke's face, and the other racks dim around it.

## 1. Tonal targets (measurable, per frame)

| measure | wide shots (01, 02, 06) | slate shots (03, 04) | reaction (05) |
| --- | --- | --- | --- |
| mean luminance (sRGB) | 0.10-0.16 | 0.12-0.20 | 0.10-0.18 |
| median | at most 0.10 | at most 0.12 | at most 0.10 |
| p99 | 0.70-0.85 | 0.85-0.95 (the slate's text) | 0.75-0.90 |
| clipped pixels | at most 0.05 % | at most 0.2 %, in the slate's strokes only | at most 0.05 % |

- **The racks:** their slate edges average 0.20-0.35 in the wides. The rack
  timber is 0.02-0.06. No wall or plaster plane is brighter than 0.12.
- **The characters:** readable from the rim and the racks' bounce, their
  bodies averaging 0.12-0.25 in the wides. In 03-05 the slate brings
  Toranosuke's face to 0.30-0.45.
- **The exposure is manual**, set once for the room. The reveal is made by
  the lights, not by re-exposing.

The script that measured the table above measures these too: mean, median,
p99 and the clipped share of a frame's PNG. For the regions, root's capture
can add masks, as the first-person review's ID pass does.

## 2. The racks: records, not a wall

See `data/archive_reveal_rack_bay.png` (two bays, front elevation).

**The layout** (per the spec): racks on both long walls, x 0-1.2 and
24.8-26 m, 1.2 m deep, from 0.6 m to 17.4 m along y. The 鷲尾家 slate is on
the east rack at (25, 9, 1.5).

**The bays:**
- one ken (1.82 m) wide, between 12 cm uprights of dark aged timber;
- six shelves from 0.30 to 2.90 m, 0.44 m apart, on a 0.30 m plinth;
- above 3.0 m, the plaster and the beams stay dark.

**The slates are stored edge-out, like books:**
- each is about 30 x 22 cm and 2-3 cm thick, a black glass-like body
  (albedo about 0.03, roughness about 0.15);
- only its edge faces the room;
- each edge glows cyan (7,000-9,000 K, the ledger aisles' range in §1.4), at
  a per-instance brightness of 0.35-1.0;
- about 6 % are dead (dark);
- a few breathe slowly, never in step.

The wall then reads as thousands of thin vertical lines of light with depth
and rhythm, not as a plane.
- **Face-out slates** (with numerals) are rare, one or two per bay, using
  §1.4's data-driven material: "per-instance random household balances" that
  must "not form a readable repeating pattern".
- **The emissive budget:** the light is in the edges and numerals, not whole
  faces. That keeps a rack's average low while it sparkles.

**The light the racks cast:**
- the slates' emissive is picked up by Lumen at low strength;
- for local light on the floor, one hidden soft rect light per bay, inside
  the rack: cyan, about 2 m attenuation, set so the floor's pool in front of
  a bay reads 0.10-0.15;
- these replace the broad wash;
- shadows only on the 2-4 bays nearest the action (the Mac budget, at most 8
  shadowed lights; §1.4's fallback column for the aisles).

## 3. The room

See `data/archive_reveal_plan.png` (the plan from §1.3 L6).

- **Walls:** 漆喰 plaster (off-white, albedo about 0.6, dim in this light)
  between exposed posts (柱) every ken, with horizontal tie-beams (貫 or
  長押). Board wainscot (腰板) to 0.9 m. Not brick.
- **Ceiling:** 6 m, with exposed rough-hewn beams (梁) across x. They must be
  visible in the wides, catching the window's rim and the racks' cyan.
- **Floor:** the current old boards, darker (albedo 0.15-0.25), low gloss
  (roughness 0.6-0.7), so the racks reflect only faintly. Dust in the
  corners.
- **The duel ring's four 欅 posts** at (9, 6), (17, 6), (9, 12) and (17, 12):
  24 cm square, dark aged keyaki. When a blade hits a post, dust shakes from
  the beam above it (§1.4).
- **The high window:**
  - on the north wall, its sill at about 4.2 m and its frame about
    0.9 x 0.6 m, with a wooden lattice (格子);
  - the spec gives no x; the plan proposes 19.5 m, so that its rim crosses
    the ring diagonally;
  - it reads as a dark blue rectangle with a faint sky.

## 4. Lights

| light | type | colour | target | shadows |
| --- | --- | --- | --- | --- |
| ambient, sky | none: Lumen from the emissives and these lights | - | the room's centre falls to 0.02-0.05 | - |
| starlight rim | one rect light the size of the window, down and south across the ring | about 10,000 K | rim highlights on heads and shoulders at 0.35-0.50; a faint shaft in very thin fog (density about 0.003, height falloff) | soft |
| rack bays | one rect light per bay, inside the rack | cyan (the slates' own) | a floor pool of 0.10-0.15 in front of each bay | the nearest 2-4 only |
| the 鷲尾家 reveal | the slate's emissive, plus a rect light the slate's size on its face | 6,500 K near-white cyan | Toranosuke's face at 0.30-0.45 | yes |

**The reveal, in time:**
1. The duel event fires.
2. The slate slides 8-10 cm out of its rack and its text ramps to full over
   0.6 s. Its face glows faintly behind the text.
3. Over the next 1.0 s, every other rack dims by 30 %, so the room narrows to
   the slate.
4. On 06_Return, the racks come back over 1.5 s.

There is no warm source in this beat. The warm-against-cold rule of §1.4
belongs to the palace.

## 5. The slate

**It is a record from the rack**, the face-out slate of its bay, not a
separate panel on a wall.
- **Its size** stays 602b862's tested 75 x 100 cm for this pass (root's
  readability and camera layout). A smaller record would need its own
  readability and camera review.
- **Its place:** centred at 1.5 m (§1.3 L6, (25, 9, 1.5)) in a niche cut
  through two shelves of its bay (`data/archive_reveal_rack_bay.png`), the
  edge-out slates continuing around it.
- **Its material:** a black glass face (0.03-0.06) in a thin dark metal
  bezel, set in the niche's dark timber frame.

**The text, per §2.6, in this hierarchy:**
1. 武家方記録 (small), then 鷲尾家 (the largest line);
2. 元本 120, 利息 22, 延滞金 36, 手数料 52, 返済 △40, with right-aligned
   figures;
3. 残高 190, larger than the rows;
4. 買取価格 30, set apart from the ledger: the Credit House's purchase is a
   stamp, in its amber, over the record.

The reveal is that the house was bought for thirty (b09
`nyaakoto.003`), so this row must never be clipped or hidden by a subtitle.

**The colours:**
- the text is near-white cyan, 0.85-0.95, on a 0.03-0.06 face: a contrast of
  at least 10:1, as 602b862's text is close to;
- the amber stamp is about (1.0, 0.62, 0.30), at 0.70-0.85.

**The font:** the shipped Japanese font, as root's 4f3fe61f uses, laid out by
root's measured layout.

## 6. The six shots

These are framing notes for the existing shot list. Root owns the camera
code.

- **01_Wide:**
  - establish the room: camera about 1.2 m up, a 24-28 mm equivalent;
  - both racks recede as converging lines of light, the beams overhead and
    the window high on the north wall;
  - the duellists in the ring between the posts, and most of the frame dark.
- **02_RackImpact:**
  - the rival meets the east rack;
  - the slates shake, a few flicker, and dust falls from the beam;
  - camera at his side, the rack filling a third of the frame.
- **03_FirstLine:**
  - over Toranosuke's shoulder onto the slate as it slides out and lights;
  - it is the brightest element, and his face is half-lit by it.
- **04_FamilyPage:**
  - the slate, readable, framed by its bay (the edge-out slates soft around
    it);
  - the subtitle band sits clear of its text.
- **05_Reaction:**
  - Toranosuke's face, keyed by the slate from the front, low;
  - the window's rim behind him, his blade lowered (in his hands: see the
    contract).
- **06_Return:**
  - back to the duel, wider;
  - the racks recovering, and both in stance.

## 7. The grip contract (third-person weapons)

This follows in its own signed note: the sockets, axes and poses root can
bind and test for the rival's katana, the bows and the quivers. It is drawn
from the rig, weapon and attachment facts in root's branch. This room and
lighting slice does not depend on it.

**For this pass:** floating weapons stay as they are, or are hidden from the
archive's shots. No new offset is guessed (root's 23:08 note).
