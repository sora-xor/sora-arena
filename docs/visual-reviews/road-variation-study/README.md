# Estate road scan-variation study — packaged Mac relative visual pass

The first [integrated gravel and inset-stone candidate](../integrated-roji/README.md) failed the fixed-camera Mac art gate: bright gravel and sharp polygon stone perimeters were conspicuous at player height. It remains source-only.

This second, unplaced ArtReview material keeps the original, hash-pinned [Poly Haven Grey Stone Path](https://polyhaven.com/a/grey_stone_path) photograph and its matched albedo, DirectX normal, ARM, and displacement maps. The photographed dirt, moss, weathered stone faces, and buried edges therefore remain coherent. `scripts/unreal/import_nyaagyu_road_variation_art_review.py` connects the pinned UE 5.8 `TextureVariation` function to 180 cm world-space UVs, uses its height-guided shifted UVs for every map, passes clean derivatives to the texture samples, and uses `TextureVariation_RotateNormals` for tangent-space consistency. Its material is imported under `/Game/Generated/Environment/ArtReview/RojiTextureVariation` without changing the main terrain palette or WorldBuilder.

The importer and actual function pin signatures were checked in an isolated UE 5.8.3 temporary project. In the diagnostic SORA checkout the import completed with `NYAAGYU_ROAD_VARIATION_ART_REVIEW_IMPORTED`; a 1011-package Mac cook compiled this material's `METAL_SM5` and `METAL_SM6` shader maps without a failed material. The diagnostic game build and archive stage succeeded, and the staged bundle identity was `org.sora.soraarena`. The release project remains pinned to UE 5.8.2.

The same packaged build ran baseline and candidate with identical lighting, content, `-SoraArtReview` camera hook, and Mac preset. The only candidate switch was `-SoraReviewRoadVariation`; the runtime logged all eight central Mac terrain tiles using the candidate. The entrance camera was `(−2696, 0, 154.15)` cm with zero rotation in both runs. The close hook used the same player location, downward rotation, and 65° field of view in both runs. These PNGs are **unedited packaged frames**, not source previews:

| Resolution/view | Baseline | Scan variation |
| --- | --- | --- |
| 1280×720 Estate entrance | [baseline](UE583_Estate_RoadVariation_Baseline_Entrance.png) | [candidate](UE583_Estate_RoadVariation_Candidate_Entrance.png) |
| 1280×720 player-height road close | [baseline](UE583_Estate_RoadVariation_Baseline_Close.png) | [candidate](UE583_Estate_RoadVariation_Candidate_Close.png) |
| 1920×1080 Estate entrance | [baseline](UE583_Estate_RoadVariation_Baseline_Entrance_1080p.png) | [candidate](UE583_Estate_RoadVariation_Candidate_Entrance_1080p.png) |
| 1920×1080 player-height road close | [baseline](UE583_Estate_RoadVariation_Baseline_Close_1080p.png) | [candidate](UE583_Estate_RoadVariation_Candidate_Close_1080p.png) |

SHA-256, in table order from left to right and top to bottom:

```
629a405b0184a51766f916e765f7f0c1afa410c182733d6fc1b11ba152af194e  UE583_Estate_RoadVariation_Baseline_Entrance.png
d46a8d2a32d7d12851779fdbb2a746f8f73df25cb1d4305741cbf88ae1282f3b  UE583_Estate_RoadVariation_Candidate_Entrance.png
b72eeb19595a781118e6187fb8b8c3f88a158dba3aad2e4483ccf355da85aa0e  UE583_Estate_RoadVariation_Baseline_Close.png
3bc469ee096dffdb8f53d244fac65547c1e442e4b1738a6dcce65b01574f8070  UE583_Estate_RoadVariation_Candidate_Close.png
0ab84a43441d9dea49bbdd6791f53b5454d30a96e9b0a7dae515a726de5adb8e  UE583_Estate_RoadVariation_Baseline_Entrance_1080p.png
cb6f5fefb384c652e920661fae194d0d37c3c5614230633dab98b75e49cfdf6f  UE583_Estate_RoadVariation_Candidate_Entrance_1080p.png
7327adceb5611e9221f1f2820637a1af1fb2a16dcccfcfbd5de11dd8300ecccb  UE583_Estate_RoadVariation_Baseline_Close_1080p.png
78cb84f1497e38d8bab3adbd2f78d34554f7b88011898d17baaaf758e73f8750  UE583_Estate_RoadVariation_Candidate_Close_1080p.png
```

At native 1080p, the candidate **materially reduces the conspicuous threefold repeated stone cluster** in the close frame and the repeated broad pattern across the approach. It retains the photographed dark sediment and weathered stone contacts, with no thin polygon cutouts or bright gravel. I do not see a new obvious tile seam or normal-direction break in these two fixed views. This is an **incremental relative visual pass**, not a AAA photoreal certification: the 5 m-wide paved strip, sparse surrounding Estate, missing asset depth, and broader art direction remain unfinished.

A limited frame-counter observation from the packaged 1080p runs gives 668 frames over 11.328 s for baseline (about 59.0 fps) and 683 over 11.317 s for candidate (about 60.4 fps), measured between the entrance and close screenshot requests. Those intervals include camera teleports and screenshot overhead and give neither GPU frame-time percentiles nor representative combat. They show no obvious coarse regression in this one offscreen route, but **do not establish the 60 fps performance target**. A dedicated warmed, representative combat profile and Windows 1440p run remain required.

One candidate launch stopped before Unreal startup with a macOS sandbox-extension error; an immediate retry of the same package and arguments completed normally. No material shader or in-game runtime error appeared in the completed candidate log. The diagnostic C++ material switch was restored after capture.

The later runtime promotion binds a production copy of this exact material graph to the existing stone terrain slots. The ArtReview importer and these frames remain as the original A/B evidence; they do not establish an exact UE 5.8.2 release cook or a representative combat performance pass.
