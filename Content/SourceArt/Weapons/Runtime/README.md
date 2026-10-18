# Runtime weapon meshes (SM_Weapon_00 to SM_Weapon_20)

Editable, measured source art for every catalog weapon: the 18 arena weapons
and the campaign yumi, yari and naginata. Each weapon folder holds the LOD0,
LOD1 and LOD2 FBX files, the baked 2048 x 2048 texture set, the Blender
source (named, editable parts in the `RW_Source` collection plus the exported
LOD objects) and a `build_record.json`. `Renders/` has three Blender Cycles
images per weapon: `_Neutral_1m` (35 mm lens, camera 1.0 m from the focus
point, neutral grey studio), `_Estate_1m` (camera 1.0 m, lying on the Estate's
timber boards under the Estate's own overcast sky, `kloofendal_overcast_puresky`)
and `_Profile` (orthographic side view over a ruler with 1 cm or 10 cm ticks).

These are Blender renders, not Unreal captures. Nothing here is imported by
`scripts/toolchain/import-mac.sh` yet, and nothing is admitted by the photoreal
gate (`docs/art-direction/photoreal-acceptance.md`) or reviewed by a historian.
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
  `Charge`, `Magazine`, `Chain_Anchor`, `Fundo`, `String_Upper/Lower`; the saya
  has `Koiguchi` and `Kurikata`; the ya has `Nock` and `Tip`).
- One material slot per mesh. `T_Weapon_XX_BaseColor` (sRGB),
  `T_Weapon_XX_NormalDX` (tangent space, DirectX green-down, baked on the
  exported triangulation), `T_Weapon_XX_ORM` (R ambient occlusion, G roughness,
  B metallic) and `T_Weapon_XX_Mask` (R hamon or emissive, G lacquer/edge wear,
  B cavity). Emissive weapons record their glow colour in `build_record.json`
  (League glows are warm; only alien arms are cyan).
- UV channel 0 (`UV0`) is a unique non-overlapping atlas for the baked maps;
  channel 1 (`UVMetric`) keeps continuous metre-scale coordinates for detail
  tiling. Saya and ya share their weapon's atlas.
- LOD1 and LOD2 are decimated from LOD0 (about 42 % and 16 % of its triangles;
  LOD2 drops parts of a few millimetres). Suggested screen sizes 1.0 / 0.35 / 0.12.

## Design notes

- **Nihontō (0, 4, 10).** Blades are lofted along a circular mune arc with the
  measured nagasa and sori: shinogi-zukuri with iori-mune, a crisp yokote,
  ko-shinogi and a fukura drawn as a tangent arc (katana, wakizashi), or
  hira-zukuri with a thick yoroidōshi kasane and slight uchizori (tantō).
  The katana has a gold-foiled habaki with file marks, seppa, a maru iron tsuba
  with a raised rim, kogai and kozuka hitsu-ana and small SORA-mon inlays,
  shakudō fuchi and kashira, SORA-mon menuki, a bamboo mekugi, and two
  hineri-maki ito strands (40-degree diagonals crossing over and under on the
  omote and ura, twisting at the mune and ha edges) over samegawa. The
  wakizashi is the plain ch03 travel mount; the tantō is an aikuchi with
  black-lacquered same. Hamon (notare-gunome with nie and a turned-back
  bōshi; suguha variants) is an original procedural mask in `Mask` R.
- **Polearms (19, 20, 12, 17).** Sankaku su-yari with kerakubi, habaki,
  kuchigane, lacquered 千段巻 and iron ishizuki; naginata-zukuri blades that
  widen toward the fukura with a naginata-hi groove, small tsuba, dōgane and
  long ishizuki on an oval ebu. The monofilament filament is bound along the
  edge by silk wraps. The healing lance is fictional (bronze needle, caged
  glass reservoir flagged emissive, vermillion shaft, cotton grip wraps).
- **Kanabō (6) and forge hammer (8).** Octagonal oak body with 88 forged
  pyramidal studs, bands, domed cap and leather-wrapped grip; 向こう鎚 head with
  mushroomed faces on a kashi handle with an iron wedge.
- **Kusarigama (2).** Kashi handle, kurouchi sickle with a bright single bevel,
  a 2.7 m chain of alternating oval links from the butt ring to three loops in
  the left paw, and an octagonal fundō.
- **Yumi (18) and ya.** The braced shape is integrated from a curvature
  profile solved so both tips meet the string line at the brace height; black
  urushi stave with groups of lacquered rattan bindings, deerskin nigiri, horn
  hazu, a resin-coated hemp string with nakajikake. The ya has a tapered yadake
  shaft with four nodes, horn hazu, three red vanes, silk bindings and a
  yanagi-ba point.
- **League firearms (5, 9, 1, 7, 15).** The coil matchlock follows the
  tanegashima pattern with an alien coil sleeve grafted over the breech; the
  repeater, arc carbine, rope-bound bamboo hand-mortar (after the Edo 手筒花火)
  and bronze micro-mortar are fictional League weapons in timber, urushi,
  bronze, iron and rattan, with the SORA mon where the story places it.
- **Alien arms (14, 3, 13, 11, 16).** Chamfered graphite and titanium plates,
  black glass, hex fasteners, rails, louvred vents, cables, sparse cyan ledger
  lines and the ledger sigil (a ring of tally notches, unlike the SORA mon).

## Materials and licences

Geometry, masks and bakes are original (project-owned, see `manifest.json`).
The authoring materials read these third-party CC0 inputs, all recorded in the
asset ledger and listed with their SHA-256 in `sources_manifest.json`:

- wood: Poly Haven `japanese_cedar_planks` (photo scan), cut at its plank
  seams, tone-matched and cross-faded into a seamless straight-grain board, then
  re-toned per weapon;
- iron and steel breakup: Poly Haven `rusty_metal_02` (photo scan, committed
  Estate palette); polished blade steel, hamon, nie, hada, file marks, nanako,
  tsuchime and lacquer are original procedural masks, because no CC0 polished
  steel scan is in the local library;
- fabric and cord: Poly Haven `crepe_satin` and `rough_linen` (photo scans);
  ambientCG `Fabric001` (surface-approximated), `Rope001` and `Rope002` (upstream
  procedural);
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

- Pending rebuild (2026-09-26, stopped when the data volume fell below the
  lane's 30 GiB floor): the current outputs of 0, 4 and 10 predate the
  builder edits that extend the tsuka-ito under the fuchi and kashira,
  thicken those fittings to a 1.9 mm wall, retone the suaka copper and darken
  the kuro-same; 6 predates the darker oak and iron; 5 predates the fix that
  puts the lockplate on the right (-Y) side; 15 predates the iron bands with
  nailed straps and the cast mon wrapped onto the barrel. Rebuild them with
  `--only 0,4,10,6,5,15`. Weapons 3, 11, 13 and 16 are not built yet (see
  the table).

- Unreal import, material instances, LOD screen sizes and socket use in
  `USoraViewmodelComponent`, and first-person paw fitting.
- Packaged-game A/B captures, Mac/Windows frame cost and the photoreal gate.
- Historian and practitioner review of the nihontō mounts, hamon, yari and
  naginata sections, the yumi's braced profile, shigetō binding layout and ya,
  the tanegashima lock and the kusarigama configuration. Kanabō, kusarigama,
  mukōzuchi and tantō sizes are period design values, not museum records.
- Chain physics, bowstring and arrow rigging, and charge/pulse emissive states.
- Fletching is solid geometry (no alpha); the kurikata and sageo tie are
  simplified; the polished blade steel has no photographic scan source.

## Weapons

| ID | Weapon | Faction / use | LOD0 / LOD1 / LOD2 triangles | Texel density p05 (px/m) | Metric validation |
|---:|---|---|---|---:|---|
| 0 | 刀 Katana (`SM_Weapon_00`) | League hero (Nyaakoto) | 56494 / 23726 / 9038 (+ Saya: 12360 / 5190 / 1976) | 3081 | pass |
| 1 | アーク・カービン Arc Carbine (`SM_Weapon_01`) | League-built (Tetsugorō, ch05; SORA mon on the receiver cheeks) | 16312 / 6850 / 2608 | 2735 | pass |
| 2 | 鎖鎌 Kusarigama (`SM_Weapon_02`) | League (Otane's farm sickle on a chain) | 29726 / 12484 / 4756 | 2965 | pass |
| 4 | 脇差 Wakizashi (`SM_Weapon_04`) | League (ch03 travel mount) | 40538 / 17024 / 6486 (+ Saya: 10120 / 4250 / 1618) | 3750 | pass |
| 5 | コイル火縄銃 Coil Matchlock (`SM_Weapon_05`) | League village gun with an alien coil breech (ch04; no SORA mon) | 19170 / 8050 / 3066 | 1881 | pass |
| 6 | 金棒 Kanabō (`SM_Weapon_06`) | League (Kōzō's gate breaker, ch08) | 38324 / 16096 / 6130 | 2412 | pass |
| 7 | 擲弾筒 Grenade Launcher (`SM_Weapon_07`) | League (Tamakichi's 花火筒 hand-mortar, ch03) | 36758 / 15438 / 5880 | 1590 | pass |
| 8 | 鍛冶槌 Forge Hammer (`SM_Weapon_08`) | League (向こう鎚 striker's sledge, ch05) | 3556 / 1492 / 568 | 5099 | pass |
| 9 | 連発銃 Repeater (`SM_Weapon_09`) | League foundry-built (bronze, iron, timber; SORA mon) | 18324 / 7696 / 2930 | 2495 | pass |
| 10 | 短刀 Tantō (`SM_Weapon_10`) | Toranosuke's pledge (ch06) | 9226 / 3872 / 1476 (+ Saya: 8360 / 3510 / 1336) | 7098 | pass |
| 12 | 単分子薙刀 Monofilament Naginata (`SM_Weapon_12`) | League special (Kōzō and Okinu, ch08) | 19058 / 8004 / 3048 | 3662 | pass |
| 14 | プラズマ火縄銃 Plasma Matchlock (`SM_Weapon_14`) | Alien-built, captured (ch07) | 22032 / 9252 / 3524 | 2519 | pass |
| 15 | 小型迫撃砲 Micro-Mortar (`SM_Weapon_15`) | League siege train (Tamakichi, ch08; cast SORA mon) | 10380 / 4358 / 1660 | 2257 | pass |
| 17 | 治癒の槍 Healing Lance (`SM_Weapon_17`) | League special (Okuzu the apothecary, ch08) | 16442 / 6904 / 2630 | 3662 | pass |
| 18 | 和弓 Yumi (`SM_Weapon_18`) | Nyaakoto (shigetō war bow) | 30600 / 12852 / 4896 (+ Ya: 3902 / 1638 / 624) | 3138 | pass |
| 19 | 槍 Yari (`SM_Weapon_19`) | Nyaakoto (su-yari) | 12054 / 5062 / 1928 | 3806 | pass |
| 20 | 薙刀 Naginata (`SM_Weapon_20`) | Okinu's mother's naginata (ch05) | 16750 / 7034 / 2680 | 3909 | pass |

**Not built yet:** 3 Needle SMG, 11 Pulse Carbine, 13 Phantom SMG, 16 Shock Emitter. Their builders and specs are in place; run `python3 scripts/art/create_runtime_weapon_build_all.py --only 3,11,13,16` when the data volume has room (the lane keeps at least 30 GiB free).

## Measured checks

Values in metres (mass in kg, grip position as a fraction of the stave). *reference*: a museum record or rule cited in the repo; *period*: a common period proportion used as a design value; *derived*: follows from other measured parts; *design*: fictional or undocumented.

| Weapon | Check | Measured | Target +- tol | Basis | Source |
|---|---|---:|---:|---|---|
| Katana | nagasa | 0.7267 | 0.7270 +- 0.0030 | reference | docs/historical-arms.md: Met Edo katana (638804) 72.7 cm cutting edge |
| Katana | sori | 0.0147 | 0.0150 +- 0.0020 | period | docs/art-research/free-asset-acquisition-plan.md section 3.8: Met 24378 curvature 0.9 cm; shallow Keichō-shintō sori chosen |
| Katana | mounted_length | 1.0071 | 0.9980 +- 0.0150 | reference | docs/historical-arms.md: Met Edo katana (638804) 99.8 cm overall |
| Katana | tsuka_length | 0.2424 | 0.2424 +- 0.0030 | period | 8 sun uchigatana tsuka (fuchi face to kashira end) |
| Katana | tsuba_height | 0.0730 | 0.0730 +- 0.0020 | period | maru-gata iron tsuba |
| Katana | tsuba_width | 0.0760 | 0.0760 +- 0.0020 | period | maru-gata iron tsuba |
| Katana | saya_length | 0.7840 | 0.7860 +- 0.0120 | derived | habaki + nagasa + kojiri clearance |
| Arc Carbine | overall_length | 0.8700 | 0.8600 +- 0.0150 | design | fictional League carbine |
| Kusarigama | handle_length | 0.4500 | 0.4500 +- 0.0040 | period | farm-sickle handle 1.5 shaku, butt cap to ferrule (design value) |
| Kusarigama | blade_overall | 0.1970 | 0.1970 +- 0.0060 | period | 17.5 cm below the handle plus 2.2 cm set into its head (design value) |
| Kusarigama | chain_length | 2.6645 | 2.7000 +- 0.0800 | period | 9 shaku chain (design value) |
| Wakizashi | nagasa | 0.4478 | 0.4480 +- 0.0030 | reference | docs/art-research/free-asset-acquisition-plan.md section 3.8: Met 21880 wakizashi blade 44.8 cm |
| Wakizashi | tsuka_length | 0.1667 | 0.1667 +- 0.0030 | period | 5.5 sun wakizashi tsuka |
| Wakizashi | tsuba_height | 0.0650 | 0.0650 +- 0.0020 | period | plain iron maru tsuba |
| Coil Matchlock | overall_length | 1.0408 | 1.0380 +- 0.0120 | reference | docs/art-research/free-asset-acquisition-plan.md section 3.8: Met 22492 tanegashima overall 103.8 cm |
| Coil Matchlock | barrel_length | 0.7300 | 0.7300 +- 0.0060 | reference | docs/art-research/free-asset-acquisition-plan.md section 3.8: Met 22492 barrel 73 cm |
| Coil Matchlock | bore | 0.0160 | 0.0160 +- 0.0008 | reference | docs/art-research/free-asset-acquisition-plan.md section 3.8: Met 22492 16 mm bore |
| Kanabō | overall_length | 1.5200 | 1.5200 +- 0.0100 | design | docs/art-research/free-asset-acquisition-plan.md section 3.8: kanabō dimensions are a documented gap (TNM F-15962/3, F-16879 have no size data) |
| Kanabō | head_across_flats | 0.0879 | 0.0880 +- 0.0030 | design | octagonal oak body |
| Grenade Launcher | overall_length | 0.8400 | 0.8400 +- 0.0150 | design | rope-bound bamboo hand tube after the Edo 手筒花火 (design) |
| Grenade Launcher | bore | 0.0560 | 0.0560 +- 0.0020 | design | festival-shell bore |
| Forge Hammer | handle_length | 0.7999 | 0.8000 +- 0.0060 | period | mukōzuchi handle (design value) |
| Forge Hammer | head_length | 0.1650 | 0.1650 +- 0.0030 | period | mukōzuchi head ~3.7 kg steel (design value) |
| Forge Hammer | head_mass_kg | 4.0075 | 3.9000 +- 0.5000 | period | 7.85 g/cm3 steel |
| Repeater | overall_length | 1.1213 | 1.1200 +- 0.0150 | design | fictional League repeater |
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
