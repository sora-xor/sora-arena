# Archive room source candidate

Chapter six b09/b10 previously used a generic 36 by 26 metre room with eight
low cover boxes. The authored archive is 26 by 18 metres with a six-metre
ceiling and four keyaki posts at (9,6), (17,6), (9,12), (17,12) metres. Those
posts must obstruct blade reach inside the duel ring. The candidate replaces
the generic collision with that footprint and four full-height posts, keeps
the following zones in place, and moves the duel/pledge anchors into the room.
The wall racks occupy the authored 1.2-metre strips; a proxy family slate is
on the east rack. Runtime validation checks the room and its post contract.

Two archive host tests and the five moat tests pass. Campaign generation and
schema validation pass all 133 beats and reject the existing 65 malformed
fixtures. The climb/flood integration baseline remains unchanged. A prepared
Unreal fixture counts the four real posts and commits a mapped katana strike
through one post, followed by a clear-line damage control beside it. It freezes
opponent AI and is not a duel-balance test. It has not compiled or run yet.

This is collision and placement work, not final art. Posts, racks, doors and
ceiling use proxies. The north stair connection to the press catwalk remains
unbuilt; both door faces remain on the closed room walls. Ordinary traversal,
the actual duel, save/reload, rendering and packages still need qualification.

The first engine run at `1248987` exposed a fixture error: it equipped weapon
3 (the needle gun) while labelling it a katana. Both required swing-count
assertions failed, so the post check was not accepted. The correction equips
weapon 0, asserts its identity, and waits through the real equip recovery
before mapped attack input. Runtime rerun remains pending.

The same run passed the assisted 133-beat campaign and ValAmort boss fixture,
but `Campaign.Spaces` still required the removed generic relay pedestal.
It now requires the actual floor at zero and standing capsule clearance for
that relay site, while preserving the raised-base check for ordinary sites.
All 20 evidence files rehashed; editor/wrapper exited naturally with 3/1;
source, native, config and generated inputs were unchanged. Failed-run review:
`e6858f5a78f3d24e6acf9b922f939c011d6894e37706b5fafc3cd08d523e28a4`.
The next run includes ToranosukeSteel, the boss specific to this archive.
