# Runtime weapon meshes (SM_Weapon_00 to SM_Weapon_20)

Editable, measured source art for every catalog weapon: the 18 arena weapons
and the campaign yumi, yari and naginata. Each weapon folder holds the LOD0,
LOD1 and LOD2 FBX files, the baked 2048 x 2048 texture set, the Blender
source (named, editable parts in the `RW_Source` collection plus the exported
LOD objects) and a `build_record.json`. `Renders/` has three Blender Cycles
images per weapon: `_Neutral_1m` (35 mm lens, camera 1.0 m from the focus
point, neutral grey studio exposed 0.6 EV under the AgX default),
`_Estate_1m` (camera 1.0 m, lying on the Estate's timber boards under the
Estate's own overcast sky, `kloofendal_overcast_puresky`) and `_Profile`
(orthographic side view over a ruler with 1 cm or 10 cm ticks). Because the
pure-sky dome has no horizon or features for polished steel and lacquer to
reflect, both lit renders add three glossy-only reflection cards (a dark
eave, a bright sky strip and a dark tree line; invisible to camera, diffuse
and shadow rays), so blades and urushi show a horizon instead of flat grey.

These are Blender renders, not Unreal captures. Nothing here is imported by
`scripts/toolchain/import-mac.sh` yet, and nothing is admitted by the photoreal
gate (`docs/art-direction/photoreal-acceptance.md`) or reviewed by a historian.
The gate needs in-engine A/B captures; these renders cannot pass it alone.
The viewmodel still loads the old `Content/SourceArt/SM_Weapon_XX` primitives
until the import step switches to these files.

## Conventions

- Units are metres in Blender; the FBX files use `apply_unit_scale`, so Unreal
  imports centimetres. Real-world (human) dimensions; the viewmodel applies
  its own 0.75 scale.
- Axes: +X is the line of action (blade tip, spear point, bore), +Z is up
  (a sword's edge faces -Z), +Y is the wielder's left (Unreal -Y).
- Origin: the dominant paw's hold, which is also `Grip_R`; the yumi's origin
  is the bow hand (`Grip_L`).
- Sockets are `SOCKET_` empties parented to the LOD0 mesh (Unreal imports them
  as static-mesh sockets): `Grip_R`, `Grip_L` and `Muzzle` on every weapon
  (`Muzzle` is the bore exit, the arrow rest, or the striking point/trace end
  of a melee weapon), plus extras where useful (`Pan`, `MatchTip`, `Fuse`,
  `Charge`, `Magazine`, `Chain_Anchor`, `String_Upper/Lower`; the saya has
  `Koiguchi` and `Kurikata`; the ya has `Nock` and `Tip`; the kusarigama chain
  has `Anchor` and `Fundo`).
- One material slot per mesh. `T_Weapon_XX_BaseColor` (sRGB; A is an opacity
  mask where the weapon has alpha cards: the ya's vanes, the hand-mortar's
  straw fibres), `T_Weapon_XX_NormalDX` (tangent space, DirectX green-down,
  baked on the exported triangulation), `T_Weapon_XX_ORM` (R ambient
  occlusion, G roughness, B metallic) and `T_Weapon_XX_Mask` (R hamon or
  emissive, G lacquer/edge wear, B cavity). Emissive weapons record their
  glow colour in `build_record.json` (League glows are warm; only alien arms
  are cyan). `build_record.json` also records the baked microsurface: the
  mean tangent tilt of the NormalDX over all texels and per authoring material.
- UV channel 0 (`UV0`) is a unique non-overlapping atlas for the baked maps;
  channel 1 (`UVMetric`) keeps continuous metre-scale coordinates for detail
  tiling. Extra meshes (saya, ya, chain) share their weapon's atlas.
- LOD1 and LOD2 are decimated from LOD0 (about 42 % and 16 % of its triangles;
  LOD2 drops parts of a few millimetres). Suggested screen sizes 1.0 / 0.35 / 0.12.

## Design notes

- **Nihontō (0, 4, 10).** Blades are lofted along a circular mune arc with the
  measured nagasa and sori: shinogi-zukuri with iori-mune, a crisp yokote,
  ko-shinogi and a fukura drawn as a tangent arc (katana, wakizashi), or
  hira-zukuri with no yokote, a thick yoroidōshi kasane and slight uchizori
  (tantō). The hamon is an original procedural mask (Mask R): gunome heads
  on a noise-modulated spacing and height over a slow notare (katana,
  naginata), suguha with ko-notare, or suguha; a 0.5-1.5 mm nioiguchi, ashi,
  nie and a turned-back bōshi; the ha is hadori-whitened (+13 % value,
  roughness ~0.3) against a near-mirror ji (~0.08) that shows itame hada in
  the normal, and the shinogi-ji and mune are burnished darker and nearly
  mirror (~0.03). The katana has a gold-foiled habaki that tapers toward the
  ha with crossing neko-gaki file marks (roughness ~0.24), seppa, a maru iron
  tsuba (7.6 cm edge-to-spine by 7.3 cm) with tsuchime and a tekkotsu mimi,
  kogai and kozuka hitsu-ana and small SORA-mon inlays, shakudō fuchi and a
  domed oval kashira with shitodome, SORA-mon menuki, a bamboo mekugi, and two
  hineri-maki ito strands that start under the fuchi and cross the kashira
  (kashira-kake) over samegawa of scattered 0.4-1.2 mm nodules with the
  oyatsubu under the omote menuki. The wakizashi is the plain ch03 travel
  mount (suaka copper habaki and seppa under a brown oxide, iron fittings);
  the tantō is an aikuchi with black-lacquered same polished back to the
  nodule crowns and a domed horn kashira. Each saya carries one continuous
  flat braided sageo (~9 mm wide) threaded through the kurikata, crossing
  down the saya to a knot and two tails; the renders show the saya below the
  blade.
- **Polearms (19, 20, 12, 17).** Sankaku su-yari whose blade, bevelled machi
  and kerakubi are one welded loft, carried flat side up with a hi and
  suguha on both edges; habaki, kuchigane, a lacquered 千段巻 cord (pitch
  jitter, lacquer pooling, dielectric) and a roiro shaft tapering to the
  iron ishizuki. Naginata-zukuri blades widen toward the fukura with a
  naginata-hi groove; small tsuba, a dōgane with end rims, a brazed seam and
  mekugi, a semegane band and a 千段巻 run onto an oval ebu that tapers to a
  long ishizuki. The monofilament naginata's 0.5 mm filament stands 1.5 mm
  off the ha on multi-turn dark silk bindings and glows warm amber-white
  (Mask R). The healing lance is fictional: a hollow bronze needle under a
  brown-green patina, a caged glass reservoir (warm honey-gold glow in Mask
  R), a deep shu urushi shaft worn through to its black undercoat where it
  is handled, with fine craquelure, and spiral, shingled indigo cotton
  wraps soiled by handling. The yari, naginata and lance shafts carry the
  craquelure (danmon) of old lacquer.
- **Kanabō (6) and forge hammer (8).** A 1.52 m octagonal oak club that
  tapers by a third from the head to the grip, densely shod with ~230
  hand-forged pyramidal studs in staggered rows every 3.3 cm (each differs in
  size, height, lean and twist), iron-tannate and rust staining bled into the
  oak round every stud and band, iron bands, a domed cap, an iron butt with
  a ring and a braided tekubi cord loop, and a shingled leather grip wrap.
  The 向こう鎚 head is under black forge scale, both striking faces
  mushroomed into a 2-3 mm chipped lip and worked bright (roughness ~0.2),
  on an oval kashi handle that tapers into the eye, with grip grime and an
  iron wedge in the end grain.
- **Kusarigama (2).** Kashi handle with ferrule, rivet, butt cap and chain
  ring; a kataba sickle with a rounded 4.8 mm spine, a black-forged kurouchi
  flat and a 6 mm stone-ground bevel on the omote whose bright hagane band
  (roughness ~0.12) runs under a wavering lamination line. The 2.7 m chain is
  its own runtime mesh (`SM_Weapon_02_Chain`, driven from the handle's
  `Chain_Anchor` in Unreal): ~155 hand-forged links within +-10 % of the
  nominal size, out of round, with forge-weld swellings and their own lean,
  lying as a loose flat coil with the octagonal fundō at its centre.
- **Yumi (18) and ya.** The braced shape is integrated from a curvature
  profile solved so both tips meet the string line at the brace height; a
  rounded-rectangular stave section (2.85 x 2.15 cm at the grip, tapering)
  in black urushi; shigetō bands of flat split rattan wound two-and-a-bit
  turns by hand under lacquer, worn to the golden skin on the crowns; a
  deerskin nigiri wound as a shingled spiral strip; horn hazu; a
  resin-coated hemp string with nakajikake. The ya has a tapered yadake
  shaft with four nodes, horn hazu, silk bindings, a yanagi-ba point and
  three dyed hawk-feather vanes (the red is Nyaakoto's character choice)
  whose barbs, natural barring and ragged trimmed edge are an alpha mask on
  thin vane geometry.
- **League firearms (5, 9, 1, 7, 15).** All share the League's Japanese
  gunsmithing language: a carved dai stock with a slim cheek butt whose
  underline curves down from the wrist, barrels pinned through the forestock
  with mekugi in brass escutcheons, brass karakuri on the right with springs
  and slotted screws, brass triggers without a guard, and brass and bronze
  under their own patina. The coil matchlock follows the tanegashima of Met
  22492 with an alien coil sleeve grafted over the breech and a soft hinawa
  wound round the wrist. The repeater has a two-piece cast bronze karakuri
  box (seam, engraved border, screws), a ribbed bronze side drum with a
  riveted hub and loading gate, and a brass butt cap. The arc carbine is a
  short negoro stock (shu worn through to black) with brass cheek plates
  carrying the SORA mon and a pinned barrel through copper coil stages in a
  bronze cage (warm white arc glow). The hand-mortar is a thick-walled madake
  culm with a node, bound in hairy two-ply rice-straw nawa (hand-laid, loose
  fibre cards, frayed ends) and closed by a turned oak plug handle lashed
  and nailed into its base. The micro-mortar is cast bronze under a
  brown-green patina with casting flash, pits and the cast SORA mon, bedded
  in a carved oak cradle and held by iron capsquare straps nailed to it.
- **Alien arms (14, 3, 13, 11, 16).** Chamfered near-black graphite (albedo
  ~0.04) machined with directional micro-grooves and face-milling swirls,
  brushed titanium, clear black glass, hex fasteners and clamp collars, rails,
  louvred vents, cables, sparse cyan ledger lines and the ledger sigil (a ring
  of tally notches, unlike the SORA mon).

## Materials and licences

Geometry, masks and bakes are original (project-owned, see `manifest.json`).
The authoring materials read these third-party CC0 inputs, all recorded in the
asset ledger and listed with their SHA-256 in `sources_manifest.json`:

- wood: Poly Haven `japanese_cedar_planks` (photo scan), cut at its plank
  seams, tone-matched and cross-faded into a seamless straight-grain board;
  only its grain structure is used, re-toned to measured hardwood colours
  (kashi, gun-stock oak, cherry, smoked oak) with original oak ray fleck,
  vessel pores, grip grime and iron staining;
- iron and steel breakup: Poly Haven `rusty_metal_02` (photo scan, committed
  Estate palette); polished blade steel, hamon, nie, hada, file marks, nanako,
  tsuchime, forge scale, casting pits and lacquer are original procedural
  masks, because no CC0 polished steel scan is in the local library;
- fabric and cord: Poly Haven `crepe_satin` and `rough_linen` (photo scans);
  ambientCG `Rope001` and `Rope002` (upstream procedural);
- straw: ambientCG `ThatchedRoof001A` (the nawa's fibre);
- leather: ambientCG `Leather014` (surface-approximated);
- render environment only: the Estate `kloofendal_overcast_puresky` HDRI and
  `wood_planks_dirt` boards (committed palette).

## Rebuild and validate

```sh
python3 scripts/art/create_runtime_weapon_build_all.py            # all builders, validation, manifests
python3 scripts/art/create_runtime_weapon_build_all.py --only 0   # one weapon
blender -b --factory-startup --python scripts/art/create_runtime_weapon_validation.py
python3 scripts/assets/validate_asset_ledger.py
```

The CC0 inputs come from `python3 scripts/assets/fetch_cc0.py`. The metric
validator re-measures the saved source parts and the re-imported FBX files and
writes `metric_report.json`.

## Open items (not claimed here)

- Unreal import, material instances (masked two-sided for the alpha cards),
  LOD screen sizes and socket use in `USoraViewmodelComponent`, and
  first-person paw fitting.
- Packaged-game A/B captures, Mac/Windows frame cost and the photoreal gate.
- Historian and practitioner review of the nihontō mounts, hamon, yari and
  naginata sections, the yumi's braced profile, shigetō binding layout and ya,
  the tanegashima lock and the kusarigama configuration. Kanabō, kusarigama,
  mukōzuchi and tantō sizes are period design values, not museum records.
- Chain physics, bowstring and arrow rigging, and charge/pulse emissive states.
- The polished blade steel has no photographic scan source.

## Weapons

| ID | Weapon | Faction / use | LOD0 / LOD1 / LOD2 triangles | Texel density p05 (px/m) | Metric validation |
|---:|---|---|---|---:|---|
| 0 | 刀 Katana (`SM_Weapon_00`) | League hero (Nyaakoto) | 65272 / 27414 / 10442 (+ Saya: 25020 / 10508 / 4002) | 3187 | pass |
| 1 | アーク・カービン Arc Carbine (`SM_Weapon_01`) | League-built (Tetsugorō, ch05; SORA mon on the receiver cheeks) | 37860 / 15900 / 6056 | 3717 | fail |
| 2 | 鎖鎌 Kusarigama (`SM_Weapon_02`) | League (Otane's farm sickle on a chain) | 3794 / 1592 / 606 (+ Chain: 35100 / 14742 / 5616) | 2880 | fail |
| 4 | 脇差 Wakizashi (`SM_Weapon_04`) | League (ch03 travel mount) | 49300 / 20706 / 7888 (+ Saya: 19900 / 8358 / 3182) | 3695 | pass |
| 5 | コイル火縄銃 Coil Matchlock (`SM_Weapon_05`) | League village gun with an alien coil breech (ch04; no SORA mon) | 36236 / 15218 / 5797 | 3469 | fail |
| 6 | 金棒 Kanabō (`SM_Weapon_06`) | League (Kōzō's gate breaker, ch08) | 49484 / 20782 / 7916 | 1851 | pass |
| 7 | 擲弾筒 Grenade Launcher (`SM_Weapon_07`) | League (Tamakichi's 花火筒 hand-mortar, ch03) | 53360 / 22410 / 8536 | 1903 | pass |
| 8 | 鍛冶槌 Forge Hammer (`SM_Weapon_08`) | League (向こう鎚 striker's sledge, ch05) | 4408 / 1850 / 704 | 4657 | pass |
| 9 | 連発銃 Repeater (`SM_Weapon_09`) | League foundry-built (bronze, iron, timber; SORA mon) | 29088 / 12216 / 4654 | 3390 | fail |
| 10 | 短刀 Tantō (`SM_Weapon_10`) | Toranosuke's pledge (ch06) | 10908 / 4580 / 1744 (+ Saya: 13820 / 5804 / 2210) | 6545 | pass |
| 12 | 単分子薙刀 Monofilament Naginata (`SM_Weapon_12`) | League special (Kōzō and Okinu, ch08) | 46010 / 19324 / 7360 | 3518 | pass |
| 14 | プラズマ火縄銃 Plasma Matchlock (`SM_Weapon_14`) | Alien-built, captured (ch07) | 23048 / 9680 / 3686 | 2504 | pass |
| 15 | 小型迫撃砲 Micro-Mortar (`SM_Weapon_15`) | League siege train (Tamakichi, ch08; cast SORA mon) | 12194 / 5120 / 1950 | 2159 | fail |
| 17 | 治癒の槍 Healing Lance (`SM_Weapon_17`) | League special (Okuzu the apothecary, ch08) | 38282 / 16078 / 6124 | 2880 | fail |
| 18 | 和弓 Yumi (`SM_Weapon_18`) | Nyaakoto (shigetō war bow) | 61556 / 25852 / 9848 (+ Ya: 4382 / 1840 / 700) | 2900 | pass |
| 19 | 槍 Yari (`SM_Weapon_19`) | Nyaakoto (su-yari) | 12626 / 5302 / 2020 | 3889 | pass |
| 20 | 薙刀 Naginata (`SM_Weapon_20`) | Okinu's mother's naginata (ch05) | 20446 / 8586 / 3270 | 3917 | pass |

**Blockout, not admitted:** 3 Needle SMG, 11 Pulse Carbine, 13 Phantom SMG, 16 Shock Emitter. Their builders still produce blockout-level forms (slab stocks, plain boxes); any local outputs are left out of `manifest.json` and this table until the designs are redone and reviewed.

## Measured checks

Values in metres (mass in kg, grip position as a fraction of the stave). *reference*: a museum record or rule cited in the repo; *period*: a common period proportion used as a design value; *derived*: follows from other measured parts; *design*: fictional or undocumented.

| Weapon | Check | Measured | Target +- tol | Basis | Source |
|---|---|---:|---:|---|---|
| Katana | nagasa | 0.7267 | 0.7270 +- 0.0030 | reference | docs/historical-arms.md: Met Edo katana (638804) 72.7 cm cutting edge |
| Katana | sori | 0.0147 | 0.0150 +- 0.0020 | period | docs/art-research/free-asset-acquisition-plan.md section 3.8: Met 24378 curvature 0.9 cm; shallow Keichō-shintō sori chosen |
| Katana | mounted_length | 1.0096 | 0.9980 +- 0.0150 | reference | docs/historical-arms.md: Met Edo katana (638804) 99.8 cm overall |
| Katana | tsuka_length | 0.2424 | 0.2424 +- 0.0030 | period | 8 sun uchigatana tsuka (fuchi face to kashira end) |
| Katana | tsuba_height | 0.0760 | 0.0760 +- 0.0020 | period | maru-gata iron tsuba, height (edge to spine) >= width |
| Katana | tsuba_width | 0.0730 | 0.0730 +- 0.0020 | period | maru-gata iron tsuba |
| Katana | saya_length | 0.7840 | 0.7860 +- 0.0120 | derived | habaki + nagasa + kojiri clearance |
| Arc Carbine | overall_length | 0.8650 | 0.8600 +- 0.0150 | design | fictional League carbine |
| Kusarigama | handle_length | 0.4500 | 0.4500 +- 0.0040 | period | farm-sickle handle 1.5 shaku, butt cap to ferrule (design value) |
| Kusarigama | blade_overall | 0.1970 | 0.1970 +- 0.0060 | period | 17.5 cm below the handle plus 2.2 cm set into its head (design value) |
| Kusarigama | chain_length | 2.7977 | 2.7000 +- 0.0800 | period | 9 shaku chain (design value) |
| Wakizashi | nagasa | 0.4478 | 0.4480 +- 0.0030 | reference | docs/art-research/free-asset-acquisition-plan.md section 3.8: Met 21880 wakizashi blade 44.8 cm |
| Wakizashi | tsuka_length | 0.1667 | 0.1667 +- 0.0030 | period | 5.5 sun wakizashi tsuka |
| Wakizashi | tsuba_height | 0.0680 | 0.0680 +- 0.0020 | period | plain iron maru tsuba, height (edge to spine) >= width |
| Wakizashi | tsuba_width | 0.0650 | 0.0650 +- 0.0020 | period | plain iron maru tsuba |
| Coil Matchlock | overall_length | 1.0380 | 1.0380 +- 0.0120 | reference | docs/art-research/free-asset-acquisition-plan.md section 3.8: Met 22492 tanegashima overall 103.8 cm |
| Coil Matchlock | barrel_length | 0.7300 | 0.7300 +- 0.0060 | reference | docs/art-research/free-asset-acquisition-plan.md section 3.8: Met 22492 barrel 73 cm |
| Coil Matchlock | bore | 0.0160 | 0.0160 +- 0.0008 | reference | docs/art-research/free-asset-acquisition-plan.md section 3.8: Met 22492 16 mm bore |
| Kanabō | overall_length | 1.5217 | 1.5200 +- 0.0100 | design | docs/art-research/free-asset-acquisition-plan.md section 3.8: kanabō dimensions are a documented gap (TNM F-15962/3, F-16879 have no size data) |
| Kanabō | head_across_flats | 0.0880 | 0.0880 +- 0.0030 | design | octagonal oak body tapering by a third to the grip |
| Grenade Launcher | overall_length | 0.8400 | 0.8400 +- 0.0150 | design | rope-bound bamboo hand tube after the Edo 手筒花火 (design) |
| Grenade Launcher | bore | 0.0560 | 0.0560 +- 0.0020 | design | festival-shell bore |
| Forge Hammer | handle_length | 0.8005 | 0.8000 +- 0.0060 | period | mukōzuchi handle (design value) |
| Forge Hammer | head_length | 0.1666 | 0.1650 +- 0.0030 | period | mukōzuchi head ~3.7 kg steel (design value) |
| Forge Hammer | head_mass_kg | 4.1265 | 3.9000 +- 0.5000 | period | 7.85 g/cm3 steel |
| Repeater | overall_length | 1.1250 | 1.1200 +- 0.0150 | design | fictional League repeater |
| Repeater | bore | 0.0125 | 0.0125 +- 0.0008 | design | reduced-calibre drum repeater |
| Tantō | nagasa | 0.2268 | 0.2273 +- 0.0030 | period | yoroidōshi tantō under 1 shaku; 7.5 sun design value |
| Tantō | kasane | 0.0098 | 0.0098 +- 0.0008 | period | thick yoroidōshi kasane (design value) |
| Tantō | tsuka_length | 0.1061 | 0.1061 +- 0.0030 | period | aikuchi tsuka 3.5 sun |
| Monofilament Naginata | overall_length | 2.3100 | 2.3100 +- 0.0150 | design | Content/SourceArt/Weapons/MonofilamentNaginata (2.31 m source study) |
| Monofilament Naginata | blade_length | 0.5391 | 0.5400 +- 0.0040 | design | fictional special blade |
| Plasma Matchlock | overall_length | 1.3265 | 1.3200 +- 0.0200 | design | long matchlock silhouette (ch07 asset table) |
| Micro-Mortar | overall_length | 0.6400 | 0.6400 +- 0.0150 | design | hand-held bronze mortar after 抱え大筒 (design) |
| Micro-Mortar | bore | 0.0750 | 0.0750 +- 0.0020 | design | mortar bore |
| Healing Lance | overall_length | 1.8510 | 1.8500 +- 0.0150 | design | fictional apothecary lance |
| Yumi | bow_length | 2.2121 | 2.2100 +- 0.0120 | reference | docs/historical-arms.md: All Japan Kyudo Federation standard 221 cm (Cleveland 1921.403: 220.9 cm) |
| Yumi | grip_from_lower_tip | 0.3333 | 0.3333 +- 0.0300 | reference | docs/historical-arms.md: grip about one-third from the lower end |
| Yumi | brace_height | 0.1535 | 0.1500 +- 0.0150 | period | ~15 cm bow-to-string brace (NyaagyuYumi study sources) |
| Yumi | arrow_length | 0.9820 | 0.9800 +- 0.0100 | period | war arrow for a ~90 cm draw (design) |
| Yari | overall_length | 2.1300 | 2.1300 +- 0.0150 | reference | docs/historical-arms.md: Met 1727 foot yari note, foot spears commonly ~7 ft |
| Yari | blade_length | 0.2049 | 0.2060 +- 0.0030 | reference | docs/art-research/free-asset-acquisition-plan.md section 3.8: Met 30843 su-yari blade 20.6 cm |
| Naginata | blade_length | 0.4661 | 0.4670 +- 0.0040 | reference | docs/art-research/free-asset-acquisition-plan.md section 3.8: ColBase F-20202 blade 46.7 cm |
| Naginata | sori | 0.0206 | 0.0210 +- 0.0030 | reference | docs/art-research/free-asset-acquisition-plan.md section 3.8: ColBase F-20202 curvature 2.1 cm |
| Naginata | overall_length | 2.1500 | 2.1500 +- 0.0200 | period | Edo women's naginata (design value) |
