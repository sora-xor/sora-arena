# Bamboo/rill first-person visual gate — failed

The original water-court source generated a smaller foliage-and-shallow-rill subset for one Estate composition test. The full canopy and stone basin were excluded because solid visual geometry without matching combat collision would create false cover. The candidate was placed only in the isolated UE **5.8.3** diagnostic worktree at world `(−1000, −1100, 2)` cm, yaw 180°. Its rotated bounds were X `[−1261, −761]` cm and Y `[−1405, −1054]` cm. It cleared the ±330 cm central route by at least 724 cm and did not overlap an existing cargo collision box.

The [before](UE583_Estate_Before.png) and [candidate after](UE583_Estate_BambooRill_FailedGate.png) are unedited 1280×720 packaged Mac screenshots from the same fixed `SoraArtReview_Estate_Entrance_NoHUD` camera: world `(−2696, 0, 154.15)` cm, level rotation. The before capture predates this candidate's import; other content work happened between package runs, so this is a visual composition comparison rather than a controlled pixel diff. The [close route frame](UE583_Estate_BambooRill_Path_Close_FailedGate.png) is also unedited.

The candidate's bamboo appears only as a small dark patch at the far left, mostly hidden behind the foreground torii/building and existing cover. Its low rill is not legible at all. The Estate remains sparse and stylized. **The placement failed the first-person improvement gate and was removed from the diagnostic WorldBuilder. It was never added to the main runtime.** The full water court remains source-only too. No AAA photoreal quality claim follows from either the Blender source render or this package.

The isolated UE 5.8.3 import reported `NYAAGYU_BAMBOO_RILL_READY` with eight material bindings, Nanite source data, and a full conventional Mac fallback. The Mac cook reported zero errors and warnings, and UAT staged the package successfully. These checks establish that the candidate loaded and rendered on M1 Ultra; they do not qualify UE 5.8.2, Windows, performance, or the asset's visual quality. The candidate package archive is `/tmp/sora-arena-mac-bamboo-rill-review`; `/tmp` is diagnostic storage, not a release artifact.

SHA-256 of the three frames, in filename order:

```text
d655362164be0884286e2dcfa142977bd733262b29d5f3af7385d5fda4fa059c  UE583_Estate_BambooRill_FailedGate.png
41271f75906752de974dd0f72696dedee89a3f1082fe298117d4939b2ef26912  UE583_Estate_BambooRill_Path_Close_FailedGate.png
cf99c4b974ec89c14338b24aad47666bf8e447217f7edb3a09d15f435355d58f  UE583_Estate_Before.png
```
