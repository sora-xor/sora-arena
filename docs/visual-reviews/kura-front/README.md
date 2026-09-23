# Nyaagyu kura frontage: packaged first-person gate

This is an isolated **UE 5.8.3** diagnostic, engine revision
`5.8.3-58210709+++UE5+Release-5.8` (CL 58210709) on the available M1 Ultra.
The project still pins UE 5.8.2 for release. No candidate mesh or actor yaw
was placed in the main WorldBuilder. The review used the in-memory first-chapter
`-SoraArtReview` save, `-RenderOffscreen`, a packaged Mac game with bundle ID
`org.sora.soraarena`, and unedited 1280×720 screenshots. Asset import, Mac
build, cook, stage, and package passed. These are visual diagnostics, not
performance measurements or a release qualification.

| View | Baseline | Diagnostic candidate |
| --- | --- | --- |
| Entrance, identical `(−2696, 0, 154.15)` cm/yaw 0°/94° FOV | [original estate](UE583_Estate_Entrance_Baseline.png) | [one Kura candidate, original yaw](UE583_Estate_Entrance_CandidateSameYaw.png) |
| Kura front, identical outward-facing close camera `(−1000, −2410, 154.15)` cm/yaw +90°/pitch +10°/65° FOV | [original doors](UE583_Kura_Close_Baseline.png) | [first import, broken cedar UV](UE583_Kura_Close_CandidateSameYaw.png); [corrected channel-0 UV](UE583_Kura_Close_CandidateUVFixed.png) |
| Entrance, identical camera | [original estate](UE583_Estate_Entrance_Baseline.png) | [all estate building **visual meshes** face inward](UE583_Estate_Entrance_AllBuildingsFaceRoad.png), with corrected Kura candidate on the southern I=1 slot |

The first candidate's cedar face was flat tan because Blender exported the
parent `UVMap` as channel 0, with the boards' atlas `UV0` as channel 1. Unreal's
TextureSample read channel 0, where all 476 cedar polygons were `(0,0)`.
After copying only those polygons' board coordinates into exported channel 0,
the independent FBX roundtrip validator reports U≈0–1 and V≈0–1 and the
packaged close view displays the CC0 cedar grain. This corrected local surface
adds physical board gaps and hardware, yet its warm color and regular straps
still need art direction; it does not establish an AAA facade.

The original WorldBuilder visual yaw is `S>0 ? 0° : 180°`. With the FBX axis
conversion, that points the source's local −Y frontage **away** from the
estate's central road. A separate diagnostic changed **only visual mesh yaw**
to `S>0 ? 180° : 0°` for all Kura/Dojo buildings, leaving the established
`Building()` combat collision proxies and mesh scale/centers unchanged. In the
matched entrance screenshot this exposes some dark timber frontage and steps
under both eaves. The torii, lanterns, cargo cover, and roofs still obscure
most facade detail. The frame remains sparse and stylized, so the candidate
does **not** pass the entrance visual gate. The facing correction is a useful
orientation finding for a separate runtime review, not an admission of this
candidate mesh.

[Side camera](UE583_Kura_Side_RejectedCamera.png) and
[rear camera](UE583_Kura_Rear_RejectedCamera.png) are archived only to show why
they were rejected as frontage A/B cameras. The diagnostic checkout's temporary
WorldBuilder and GameMode changes were restored byte-for-byte after capture;
generated ArtReview assets remain unreferenced there. Main runtime files were
never changed for this review.

The raw diagnostic [baseline, UV-corrected, and final yaw-review logs](logs/)
are archived with [SHA-256 checksums](logs/SHA256SUMS). They record the import,
Mac cook, stage/package, and packaged capture evidence retained before the
reproducible `/tmp` app archives were cleared for disk space.
