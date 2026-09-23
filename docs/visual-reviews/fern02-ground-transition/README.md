# Fern ground-transition packaged A/B — failed visual gate

These four PNGs are **unedited** frames from an isolated Mac UE **5.8.3** diagnostic package. That interim engine build is not release qualification: the release source remains pinned to UE 5.8.2. The strict 5.8.2 importer was temporarily adapted only inside the diagnostic checkout. The packaged game used Xcode 26.1.1, cooked 957 packages with zero reported cook errors or warnings, and retained the `org.sora.soraarena` bundle identity. The import reported `NYAAGYU_FERN_GROUND_TRANSITION_ART_REVIEW_READY`; the package logged a successful single visual-only actor spawn, with no mesh-assignment warnings. No gameplay, save, map, or main WorldBuilder code was changed.

The entrance pair used the fixed X −2696, Y 0, Z 154.15 cm camera at yaw/pitch 0°, 1280×720. The first frame completed before the candidate actor spawned at X −1950, Y +335 cm. The close pair used one camera near X −2220, Y +385 cm, eye Z ≈154 cm, pitch −20°, 65° field of view. The close candidate was captured first; the actor was then destroyed and, 0.75 seconds later, the close baseline was captured without moving the camera. The authored footprint is approximately X [−2103, −1777] and Y [+272, +396] cm, clear of known torii, lantern, and cargo collision, and the diagnostic component disabled collision and overlap events.

| Unedited frame | SHA-256 |
| --- | --- |
| `UE583_Estate_FernGround_EntranceBaseline.png` | `ce60bd0404cb4f84ff49d7d7e6fd19ce6e22ac2f5e376db544539d52f0bb81cd` |
| `UE583_Estate_FernGround_EntranceCandidate.png` | `e5cf46ed26a8a1c9986d092f4516e304cb19e9ef40bdcb3b3e9127ad21058ab6` |
| `UE583_Estate_FernGround_CloseBaseline.png` | `546025ba51dba932e8835ad7b0e3d1947ed125c2592f907fbdeb3af4adc6fb8b` |
| `UE583_Estate_FernGround_CloseCandidate.png` | `2bcf16ce3f931b0388bb728d5a6503dc159a21d919f218386d5ea8e3b322b0e1` |

Pixel-difference visibility checks use max per-channel RGB difference above 16, not an art-quality score. At the entrance, **6.25%** of the 220×125 right-shoulder rectangle (x 775–995, y 420–545) changed; the left-shoulder and center-path control rectangles had **0%** above that threshold. The right torii post occludes most of the new cluster, so the overall entrance scene barely changes. In the close pair, **48.54%** of the 410×420 candidate rectangle (x 240–650, y 300–720) changed, while a far-shoulder control changed **0.01%**. Moving characters and temporal rendering may cause small differences; these numbers only confirm visibility and framing.

Visual verdict: **retain source and ArtReview importer only; reject runtime placement.** Fern bases are better grounded than the earlier individual cutouts, but the scanned soil appears much paler than the underlying dark terrain, its perimeter reads as a sharp applied strip, and it visually crowds the stone route in the close view. Stones and roots do not hide that seam. From the entrance, the small area visible beside the gate is insufficient to improve the whole scene. This is not the requested photoreal AAA+ result. No Windows Nanite visual/performance measurement or UE 5.8.2 package test was made for this candidate.
