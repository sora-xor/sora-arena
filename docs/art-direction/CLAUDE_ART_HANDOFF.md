# Prompt for Claude: SORA Arena photoreal art production

Copy the prompt below into Claude with this repository available. Attach the
original user-supplied Nyaakoto image to that conversation if available: the old
temporary clipboard path no longer exists. Repository concept images are useful
secondary references but are not the original character reference.

---

You are taking over art production for **SORA Arena: Nyaagyu Rebellion**, an
Unreal first-person samurai/sci-fi game. The user's central requirement is
**photorealistic AAA+ visual quality**. Existing assets have not achieved that
standard. Your job is to do the modeling, sculpting, UV work, texture authoring,
grooming, rigging, animation, lighting, Unreal integration and visual iteration
needed to materially improve the actual playable game. Deliver editable assets
and inspect their rendered results. A plan or attractive concept image alone
does not fulfill this assignment.

Repository: `/Users/takemiyamakoto/soramitsudev/sora-arena`
Application identifier: `org.sora.soraarena`.

## Start from the recovered work

Inspect Git status and recent commits before editing. Read applicable repository
instructions. Preserve unrelated work and unfinished source. Work from the
integrated `master`; if recovery is still in progress, inspect
`codex/claude-recovery-2026-10-18` and coordinate before switching the shared
checkout. Use a dedicated art branch/worktree if other workers are active.

Read these first:

- `docs/recovery/claude-2026-10-18/INTEGRATION.md`
- `docs/recovery/claude-2026-10-18/README.md` and `art-inventory.json`
- `docs/art-direction/NYAAKOTO_PHOTOREAL_TARGET.md`
- `docs/art-direction/photoreal-acceptance.md`
- `docs/art-research/nyaakoto-real-cat-scan-acquisition.md`
- `Content/SourceArt/Characters/CatBaseV6/README.md`
- `docs/render-qualification/estate-lumen-nanite.md`
- `docs/mesh-terrain-nyaagyu.md`, `docs/cc0-environment-library.md`
- `scripts/toolchain/versions.json` and `docs/toolchain.md`
- `scripts/assets/README.md` and the relevant provenance ledgers.

The current engine pin is **UE 5.8.3, CL 58210709**, installed at
`/Users/Shared/Epic Games/UE_5.8`; use the recorded project pin. Older art notes
still mention 5.8.2 and are stale on that point. Inspect installed capabilities
and official documentation before depending on a feature. The current Blender
pin is 5.2.2. Keep toolchain changes project-specific.

Recovered assets need judgment, not blind regeneration:

- **CatBaseV6 round 9:** the latest head/bust and first-person paw `.blend`
  files and textures are preserved, but only 11 of 21 review frames completed.
  The manifest still describes round 8. No round passed visual acceptance.
  `create_cat_base_v11.py` produced round 9; `create_cat_base_v12.py` is a later
  generator whose output was not found. Neither is a finished runtime character.
- **Runtime weapons:** all 21 folders exist under
  `Content/SourceArt/Weapons/Runtime/`. IDs 3, 11, 13 and 16 are explicitly
  withheld blockouts. W14 PlasmaMatchlock was interrupted: its neutral preview
  is truncated and seven recorded output hashes disagree. Top-level manifests
  are stale. Inspect actual meshes and materials before deciding what to keep.
- **Historical studies:** `Weapons/NyaagyuYumi/HistoricalStudy/` and
  `Horses/NyaagyuAbumiTazunaStudy/` contain textures and generators, but no
  completed generated study meshes were found during recovery.
- The current game still uses earlier imported character and weapon assets.
  Source-only improvements are not automatically visible in gameplay.
- The full asset ledger currently reports 216 stale Runtime records and 12
  unrecorded blockout renders. Repair provenance after actually rebuilding and
  inspecting outputs; changing hashes alone is not visual or geometry validation.

Do not spend the assignment merely adding another numbered generator and
calling its output finished. Choose the modeling method that produces the best
asset. Procedural tools are useful for repeatable detail, but the silhouette,
anatomy, construction and material response require direct visual judgment.

## Character and world identity

The protagonist is **Nyaakoto**, a grey-tabby-and-white samurai cat with a white
muzzle and chest, the distinctive markings and expression of the user's image,
layered dark indigo/blue and vermilion/oxblood armor, a katana and saya, an
asymmetric Japanese yumi, and arrows. Preserve that identity while making the
anatomy, fur and materials physically convincing. He studies
**Nyaagyū Shinkage-ryū** in Nyaagyū. Japanese is the primary language; English
subtitles are supported.

The world is Edo-inspired Japan with a deliberate science-fiction invasion by
alien banker cats. Warm lanterns, weathered timber, lacquer, silk, stone, soil,
rain and vegetation establish the human-scale setting; cold alien machinery
provides the intrusion. Keep the drama serious, with restrained cat humor.
The resistance's fictional monetary premise is production-only XOR; do not
rewrite it or present it as a complete description of real SORA economics.

Use the exact supplied SORA symbol from
`Content/SourceArt/UI/sora_logo_NOtext2.svg` for resistance kamon, armor crests,
banners and relevant architectural or equipment marks. Preserve its geometry.
Integrate it as embroidery, lacquer, relief or metalwork appropriate to the
object, rather than an arbitrary generated approximation.

## First priority: a convincing playable Nyaakoto

Complete the head, body, paws, armor and equipment as a coherent character:

1. Sculpt connected feline anatomy with credible skull, muzzle, eyelids, nose,
   cheeks, ear roots and neck. Inspect front, profile and three-quarter views.
   Resolve the existing spherical forehead, detached facial pads and toy-like
   proportions before spending time on tiny surface detail.
2. Build layered eyes with properly seated lids, corneal depth, plausible iris
   detail and restrained highlights. Give ears thickness, cartilage structure
   and natural furnishings. Root tapered whiskers in the muzzle.
3. Groom fur along anatomical growth directions, with clumping, undercoat,
   guard hairs and silhouette breakup. Preserve recognizable tabby markings.
   Provide performant mesh/card fur for first-person and macOS. Use strand
   grooms only where the target configuration supports them and measured cost
   permits them.
4. Construct the armor as wearable layers: articulated plates, believable
   lacing, cloth beneath armor, cords, knots, stitching and fastening points.
   Show how each piece is supported and how it moves. Avoid intersecting shells
   and uniform plastic gloss.
5. Build first-person paws and forearms that articulate and contact the actual
   katana, yumi and firearms. Check grips, wrist rotation, draw, guard, attack,
   parry, sheathing and bow draw/release through motion at the game's normal FOV.
6. Deliver production topology, UVs, bakes, rig, deformation, LODs and collision
   appropriate to the game. Separate presentation geometry from authoritative
   gameplay collision; do not change balance, weapon reach or hit rules to suit
   a prettier mesh.

## Historically grounded weapons and horses

Research construction, proportions, mounting and use through museum collection
records, documented surviving examples and qualified practitioners where
available. Record object IDs, dates, dimensions, sources and any uncertainty.
Treat generated concepts as design references, never historical evidence.

Model and texture the katana and its fittings/saya, yumi and arrows, yari,
naginata and other historical weapons as distinct functional constructions.
Check the full assembly, carry positions and animation. Preserve established
gameplay dimensions unless a separately reviewed gameplay change is necessary.
Do not copy the inaccurate short bows or inconsistent fittings in older AI
concept images. The fictional Nyaagyū school should draw on researched movement;
do not claim unreviewed animation is an authenticated traditional kata.

Horses require credible anatomy, weight-bearing poses, gait transitions, skin,
coat, mane and tail. Research and construct a coherent Japanese tack assembly:
kura, abumi, tazuna and the associated straps, cords, fittings and contact
points. Verify how the rider is seated and supported, how reins are held and
how the complete rig moves. Texture-only studies do not finish the tack.

Use separate, clearly fictional design language for sci-fi weapons. Keep all
six classes and special sidegrades readable; NFT rarity must never alter
combat statistics. Art work must not modify XOR settlement, proofs, custody,
IrohaConnect signing or economic rules.

## Materials and environment

Author calibrated PBR materials with coherent base color, normal, roughness,
metalness, AO and displacement where justified. Use real scale and consistent
texel density. Verify channel packing, color spaces and DirectX normal
orientation in Unreal. Skin/fur, woven cloth, silk cords, lacquer, steel,
ceramic, wood and wet stone must respond differently to the same light.
Put wear where contact, handling and exposure cause it. Avoid generic noise
overlays, baked lighting in base color, repeated stains and uniformly wet gloss.

Bring one playable **Nyaagyū Estate/dojo slice** to the target standard with
the character before spreading effort over every map. Fix roof/eave
construction, shōji, timber joints, ground transitions, vegetation contact,
set dressing and material scale. Establish an art kit that can then support
Lantern Ward, Silk Foundry, Debt Citadel and the campaign chapters. The entire
game's art remains in scope; this is the first production milestone.

Use mesh terrain, Nanite where supported, Lumen, TSR, PCG, Niagara, Control Rig
and Sequencer deliberately. Inspect actual Nanite representation, fallback LODs,
Lumen Scene, Surface Cache, distance fields and indirect-light contribution.
Resolve visible missing coverage or light leaks through geometry/material work.
Feature flags and attractive lighting do not establish successful integration.
Use MegaLights only on supported configurations and keep experimental terrain
features replaceable. Inspect the existing Sensei Terrain research; use it only
if current free access and commercial-use terms are verified. Make no purchases.

## Visual review and delivery

Work in short cycles: inspect the current render, identify the largest visible
defects, change the actual asset, render again with matched cameras and lighting,
and inspect the result. Keep before/after evidence. If a method repeatedly fails
to improve anatomy or material response, change the method.

For each major candidate, provide:

- Editable DCC source with organized objects, materials and usable relative
  paths; export assets, texture sources/bakes and reproducible import steps.
- Neutral studio front/profile/three-quarter and close-up views, plus overcast,
  daylight and lantern lighting. Use the same camera, exposure and framing for
  comparisons. Show normal gameplay distances as well as close-ups.
- Unretouched **Unreal gameplay captures** showing the asset actually loaded,
  including first-person interaction and a short movement/animation sequence.
  Label Blender renders, concept images, editor views and packaged-game captures
  accurately. Do not conceal defects with depth of field, heavy bloom, grading,
  darkness or generated-image retouching.
- Evidence of rig deformation, LOD transitions, texture memory and relevant
  CPU/GPU costs. Target 60 fps at 1080p on the available M1 Ultra Mac preset and
  1440p on an RTX 4070-class Windows machine. Report untested platforms honestly;
  do not claim their results from another platform.
- Updated provenance, licenses, manifests and concise notes stating what
  improved, what remains visibly wrong and what is actually admitted to runtime.
  Use the project's LFS and import conventions. Keep restricted raw assets out
  of distributable source. Retain CC BY credits and statements of changes.

Use custom assets, existing entitlements and free commercially usable resources.
Install necessary free tools within the authorized project scope. Figma may help
with interface design; the character and world still require real 3D assets.
This is a first release: do not add legacy formats or compatibility layers.

Begin by opening the latest character and weapon sources and inspecting the
current Unreal scene. Give a brief concrete assessment, then start improving
the assets immediately. Do not wait for approval for routine reversible art
work. Ask only when a missing reference, account access, license or consequential
design ambiguity actually blocks the next step. Do not self-certify “AAA+” from
a score or a checklist: present the actual playable result for review and keep
working on its visible shortcomings.
