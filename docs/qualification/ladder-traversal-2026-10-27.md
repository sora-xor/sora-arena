# Swept ladder traversal — 27 October 2026

Generic ladders now move the standing capsule along a continuous approach,
vertical climb and roof step at 150 cm/s. Every segment sweeps collision;
an obstruction holds progress rather than snapping through it. Arrival needs
actual walkable floor support. The HUD uses the same grounded, height and facing
eligibility as interaction. Jump releases the grip into ordinary gravity;
damage, death and retry clear it. Crouch cannot shrink the capsule while climbing.

Signed `46da7357ee2521806e1bb07b7971b4b9142dea6d`, tree
`197daff787920bb60d086c78c312b0f95c4f8180`, builds in UE 5.8.3 in 18.29 seconds
and passes all **70 selected native tests**, with zero selected errors or
warnings. Natural EOF is `2026-10-27T03:00:08.057989+00:00`.
The selection includes the prior 66 workshop/notice-square/campaign cases,
generic ladders, the new ladder collision case, press catwalk and its patrol.

The new case uses mapped jump input at chapter-three b03 and b10 ladders. It
adds and removes ascent and roof-exit blockers, removes/restores actual roof
collision, checks pause and crouch, blocks descent, releases into a fall,
checks injury and fatal-damage retry, and completes a round trip. Per-frame
displacement is bounded. Initial station placement and encounter suppression
are assisted: this is directed NullRHI coverage, not ordinary traversal or
rendered animation acceptance. The authored multi-roof route remains unfinished.

Archive: `Saved/Qualification/2026-10-27/ladder-runtime-46da7357-attempt1`.
Independent review SHA-256:
`110ec8f76de19e29e020b746c9fe64f27f9dbd66425b6f580a689b483d28b075`.
Status SHA-256:
`18bd05b2e21fa4b1fd3655b2410403e3d807157a48b4ac0e634d62ae91231f1c`.
The review verifies exact selection, twenty original evidence files, natural
process/stream completion and unchanged source, native library, Config and
Generated assets.

The first build at `431efe24960713533d943700fcc72bf053e87112` failed on three
new test counter calls passing `FString` where `const TCHAR*` was required.
No editor or runtime tests launched. `46da7357` corrects those calls.
The failure and its natural completion remain archived; independent review
SHA-256 `35a4bc71d5220fdcdcb202d211c72a4526999865a5f7b253a56daffcb15adfc4`.
Earlier CI125 at `102c18d9` predates this ladder source.

Native bridge remains `10ad7dad`; the Mac package remains older `c655b6b`.
Authored roof/drone geometry, final art, normal play and release gates remain open.
