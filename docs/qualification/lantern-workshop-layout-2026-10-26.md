# Lantern workshop layout checkpoint — 2026-10-26

Source: signed `799233e8cbcf0585f969218fb88967c61c965208`, tree `59240726a067cbd6d3cf6f55973d328b7218312f`.

The chapter-three workshop now uses its authored 7.2 × 11 m building and surrounding yard instead of a distant generic hall. The 1.8 m earth passage remains beside the 45 cm raised plank floor. Two 22.5 cm steps provide access from the passage and rear doorway. Four workstations have individual floor heights: three inside and the shell bench outside under the storehouse eaves. Work at this workshop requires standing on the station's floor, so a matching horizontal position on its roof cannot perform the recipe. The storehouse has an accessible ground-floor interior, the heirloom collectible and a distinct 6.5 m roof.

The campaign builder omits the old overlapping house, cover box and lantern, opens its east boundary and extends the street floor to the side passage. The practice arena retains its original construction. The generator and both catalog validators bind the fixed footprint, stations and collectible. The dojo timber campaign binding was regenerated after the chapter data changed.

Ten compiled native geometry tests verify capsule routes, station approaches with actual bench volumes, floor/step heights, roof support and data rejection. Two new Unreal fixtures pass actual collision and mapped traversal. The assisted campaign fixture now places its hero beside each workshop bench at the correct floor height; it still does not establish ordinary play.

## Validation

All 87 local gameplay/asset gates pass at `799233e8`; the independent review checks the exact inventory, all 88 report/log files and clean unchanged source. Report SHA256 `a136cae132b4b469456f447b6bf6658f4c8cf15d870c3d8cbe7bea7272e34e7d`; review `4bfd627362a0957f44527a3bb96c2619444867edd4981f2f7831138207c63cb8`.

Signed `4d1a057e10141b4a966b1b1f02718b0ce44b7106`, tree `7253793f854b818cfdd7e8bc48130b13d6a2a6c4`, builds in UE 5.8.3 and passes all 39 selected runtime cases, with zero selected errors/warnings and natural wrapper/editor exit 0 at 20:33:43.969607 UTC. The selection adds `LanternWorkshop.Solids` and `LanternWorkshop.Routes` to the earlier 37 ward, tenement, landing, campaign, fieldcraft, stealth, localization and audio cases. The route fixture uses mapped walking and interaction through the canal gate, rear step, plank stations, earth passage, street connection and collectible approach. The solids fixture checks built collision and rejects station work from the grounded roof.

Independent review verifies all 20 original recorded files, exact selection, source/tree identities and unchanged source/native/Config/Generated inputs. Status SHA256 `c45c9838511f29be66f2031651632ff695679e278171546fba89fd9e90c722c7`; review `b911476ec5769092aec15097248d21c4337c5ecfb71298e60a229b0156bcff18`. Local archive: `Saved/Qualification/2026-10-26/lantern-workshop-runtime-4d1a057e-attempt1/`.

The first run at `799233e8` remains a retained 38/39 failure. Its roof fixture used `FBeatWorld::Stand`, which moves only XY and had left the hero on the floor. `4d1a057e` changes only that fixture: it explicitly places the hero on the roof and asserts grounded height before input. Production behavior is unchanged. The first run also has one engine HTTP connectivity-probe timeout in the passing CarryDifficulty case. Its independent review is `3fd8abf0f3734807a95243ad8e1441df2676dbd6847d05dc044cf5557f17d743`.

Earlier published `990bb1f0` passes all 123 source CI gates in run [40391639170](https://github.com/sora-xor/sora-arena/actions/runs/40391639170). Tested merge `d1b6b2234e0b09ff0a184ab2a58ce56db3ff0469` has the identical tree `d81335eaf7a6ecf440fcc62986a8852f8c959987`. All five artifact digests, raw logs and exact signed inventories authenticate; strict review `cbd4533dc698930af03fa3881f09c69fbecdff0e7a3c71ab2787796dca9ee14f`. This earlier CI does not include the workshop changes; the current source inventory has 124 gates.

These tests seed campaign checkpoints and isolate opponents. The complete campaign case is an assisted 133-beat traversal. Neither is ordinary-play, final-art or package acceptance. Root returned the full Unreal/Blender lane to Claude at 20:37 UTC after reviewing natural EOF and an empty engine-process inventory.

## Remaining work

Still unfinished: the two-second seal interaction and persistent door state; four sheltered craftspeople; explosion-ignited six-second oil fire and destructible cover; authored street/canal/vault/roof enemy arrivals; the specified paste-hold/craft presentation and warm-window restoration; final art, ordinary play and the preceding authored escort route. Existing generic wave staging is preserved at collision-clear yard/gate positions; the roof is built but the grenadier's authored rooftop behavior is not implemented in this checkpoint. No new package or release acceptance is claimed.
