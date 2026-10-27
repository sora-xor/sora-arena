# Workshop stations and continuous exit — 27 October 2026

The four functional workshop benches and their status marks now belong to the
chapter. Completing final inspection leaves the player and camera in place;
the route through the yard and side passage into the notice square is walked.
Temporary duplicate benches and generic crate output are removed. A retry
still restores the square's saved entry, rebuilds exactly four station
components and clears the transient action. Recipe timing, output and awards
are unchanged. The existing 120 × 80 × 80 cm collision stays pending integration
of Claude's measured craft geometry.

Signed `94eb18bbfbbf7b4bb807f0099e3357701b2af738`, tree
`b816260c31d9f13e51d1451ae8c6a659545492ef`, builds in UE 5.8.3 in 17.41 seconds
and passes all **70 selected native tests**, with zero selected errors or
warnings. The strengthened recipe case checks identical component lifetime,
position and camera preservation, a mapped walked exit, real death/retry and
checkpoint reconstruction. The assisted campaign also walks that exit before
its destination check, temporarily holding opponents and restoring their tick
states afterward. It completes all eight chapters and 126 required beats,
including eleven held objectives. This does not establish ordinary stealth
balance, rendered hand contact or full release acceptance.

Archive: `Saved/Qualification/2026-10-27/workshop-lifetime-runtime-94eb18bb-attempt1`.
Run finished after natural EOF at `2026-10-27T03:45:39.998270+00:00`.
Independent review SHA-256:
`1f5504062c91eeef087b25e6fa3f0e85599d0d6acc435cf6b67d56bd1f4b38f7`.
Status SHA-256:
`04987c8d79c12670cd5a30d2cf3fab987c887d360b032d7b14199f66bc4c9e14`.
The review verifies exact selection, twenty original files, natural exits and
unchanged source, native libraries, Config and Generated assets.

The first run at `e86386b4` built in 28.01 seconds and passed 69/70. All new
workshop checks passed. Only the assisted campaign failed: its old assertion
expected the player already in the square immediately after inspection.
The successor changes only that fixture to walk the route; the destination
assertion remains. The original failed run is retained at
`Saved/Qualification/2026-10-27/workshop-lifetime-runtime-e86386b4-attempt1`,
with independent review SHA-256
`25398c6c8b16258020ef9479aea96a3d4b8773d32336ebdf5e29247210df693f`.

The 22 compiled workshop source checks passed while preparing `e86386b4`;
those checks do not compile the Unreal actors. The last authenticated CI125
is at predecessor `98e881be`; a fresh source run follows publication.

The [action interface](../art-direction/workshop-action-view.md) is ready for
integration with chapter-owned craft props. Paw assets, poses and a world-space
presenter remain separate work. No new art is adopted. Native bridge remains
`10ad7dad`; Mac package remains older `c655b6b`. The authored roof/drone/squeeze
routes, blackout staging, final art, ordinary play, platform packages,
performance and network release criteria remain open.
