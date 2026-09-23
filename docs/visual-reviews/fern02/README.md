# Fern 02 packaged Estate A/B — failed release art gate

These three PNGs are **unedited** frames from an isolated Mac UE **5.8.3** diagnostic package. They are not UE 5.8.2 release qualification. The branch's release project remains pinned to 5.8.2, and its WorldBuilder/gameplay has no fern placement. The diagnostic package was built with Xcode 26.1.1, cooked 940 packages including `/Game/Generated/ArtReview/Fern02`, staged as `org.sora.soraarena`, and ran offscreen with `-SoraArtReview`. The source importer reported `NYAAGYU_FERN02_ART_REVIEW_READY`; the cook reported no shader-map errors.

The fixed entrance camera was X −2696, Y 0, Z 154.15 cm, yaw/pitch 0°, at 1280×720. The baseline frame was flushed before eight visual-only scan actors spawned. Candidate and baseline used the same camera, sun, post process, map, and Mac rendering path (`r.Nanite=0` with the full conventional mesh fallback). An extra close view placed the camera around X −2220, Y +385 cm, eye Z ≈154 cm, pitch −20°, 65° field of view. All ferns were outside the central stone path and established cargo-cover collision. The diagnostic actors explicitly disabled collision and overlaps.

| Frame | SHA-256 |
| --- | --- |
| `UE583_Estate_Fern02_Baseline.png` | `ddeba3a1f0e175b09793b330de8ace0570cee074d75b93413d804d401b7fb793` |
| `UE583_Estate_Fern02_Candidate.png` | `c791dcd03471fb6760dee486d02a4d8931022d669bb3b9c419f892e3209557ad` |
| `UE583_Estate_Fern02_Close.png` | `488b46809ccf22d9a5716669bcf54a3cd9ff6f225e88e566353b8ae70c157a84` |

The close frame confirms that the scanned frond silhouettes and opacity mask render in the packaged Mac game. At the entrance, the eight plants occupy only small patches around the gateposts. Against the fixed baseline, pixels with any RGB channel differing by over 16 occur in **6.0%** of the left-shoulder review rectangle (225×100 pixels) and **5.3%** of the right-shoulder rectangle (235×110 pixels). The center-path and upper-gate control regions have **0.0%** above that threshold. This shows the ferns appear off the route, while their contribution to the full view is small. Enemy motion and minor temporal effects can also change pixels, so these fractions are a visibility check, not an objective art score.

Visual verdict: **retain the authored scan and isolated importer, but do not integrate this placement into the main Estate.** The ferns improve local vegetation detail in the close frame, yet the entrance remains sparse, the ground reads as a flat texture, and the cutout clumps remain visibly card-like. This is not an unequivocal move toward the requested photoreal AAA+ whole-scene bar. Windows Nanite visual quality, frame time, species appropriateness, and UE 5.8.2 behavior remain untested.

The first diagnostic capture had a false-negative harness bug: the temporary actor called `SetStaticMesh` while its component mobility was Static, so no fern mesh was assigned. The packaged log exposed eight warnings. The final frames above were taken **after** the diagnostic component was made Movable before mesh assignment; no such warning appeared. That harness fix is isolated and is not release gameplay code.
