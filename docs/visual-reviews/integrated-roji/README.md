# Integrated Estate road: packaged Mac A/B — failed visual gate

These four PNGs are unedited 1280×720 frames from the same offscreen packaged UE **5.8.3** Mac build on the M1 Ultra. The package used the diagnostic-only `-SoraArtReview` hook and a `-SoraReviewRoji` command-line switch; the latter replaced only the eight central Estate presentation terrain tiles. Baseline and candidate shared all other content, camera code, lighting, engine build, and package. The entrance camera log reports world `(−2696, 0, 154.15)` cm, rotation `(0, 0, 0)` in both runs. The close view uses the same fixed downward player-camera hook. The fern review spawn was disabled for both runs. Art review used a transient in-memory chapter-one save; it did not touch a player save or wallet.

| View | Baseline | Candidate |
| --- | --- | --- |
| Estate entrance | [baseline](UE583_Estate_Roji_Baseline_Entrance.png) | [candidate](UE583_Estate_Roji_Candidate_Entrance.png) |
| Player-height downward road | [baseline](UE583_Estate_Roji_Baseline_Close.png) | [candidate](UE583_Estate_Roji_Candidate_Close.png) |

SHA-256 values, in the table's left-to-right, top-to-bottom order:

- baseline entrance: `994c5d8000c3faaa5f6194ece80edafff704b941b81164c9f7938b9c56d8395f`
- candidate entrance: `c761b2bffa6ba4ea648e4f42c7b35825a63ef67ac31bf1af0b49d028ec36a160`
- baseline close: `4eff2f0dbf1c6f408552798c6b82a1c280b4a870882324bdd52c515b7951c09d`
- candidate close: `9657dd00ca8ea2145498da0bc22010cfac48e786812f37d8ade2c5b60309d701`

The source import completed with `NYAAGYU_INTEGRATED_ROJI_IMPORTED`; the candidate runtime logged every `SM_NyaagyuIntegratedRoji_MAC_X0–3_Y1–2` tile. The Mac game build, 987-package cook, and archive stage succeeded. The cook showed no failed material shader maps. These are diagnostic UE 5.8.3 results, **not** UE 5.8.2 release qualification, Windows Nanite proof, or a frame-time measurement.

The A/B **fails the photoreal visual gate**. The repeated cobble photograph disappears, but the new road becomes a brighter, more uniform gravel strip at entrance distance. At close range the stones look like flat polygon cutouts with dark, very clean perimeters and little embedded sediment; color and contact differ visibly from surrounding soil. That weakness is more damaging than the motif it replaced. The candidate remains source-only and the main WorldBuilder retains the baseline terrain. The diagnostic C++ switch and prior fern-hook change were restored after capture; only unreferenced imported candidate assets remain in the isolated checkout.

Further art would need more believable stone volume, weathered buried edges, less regular silhouette and density, accumulated sediment at contacts, and color/roughness transitions measured under the game's actual Estate lighting. The comparison should be repeated after any such changes before considering runtime placement.
