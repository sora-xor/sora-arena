# Readable credits — October 27 source checkpoint

The failed `541c61ae` package's credits displayed the complete asset audit:
generator commands, storage fields, schema migration notes and acceptance
policy appeared among the source acknowledgements. The original captures and
failed package remain unchanged.

The ledger generator now produces `ThirdPartyNotices/CREDITS.md` alongside
the existing `ASSETS.md`. The credits view keeps source titles, authors,
licenses, source links, required attribution, changes and mirror dataset
credits. Original titles, including `قط شوارع.jpg`, remain intact. Older
manifest acknowledgements retain their complete license statements and links;
they are not silently dropped or presented as migrated records. Some original
change notices contain technical detail and remain verbatim for attribution.
Acknowledging a source does not admit its art into production.

The menu requires the generated credits view and then reads separate license
notices. It no longer displays the audit. The full audit is byte-identical to
the parent checkpoint, and the QRCodeGen and NotoNaskhArabicUI notices are
unchanged. Existing NonUFS directory staging includes both generated files
and the separate licenses. Generator `--check` rejects either missing or stale
output. Repository asset-ledger instructions describe this two-file contract.

The Mac candidate verifier now compares the staged Arabic face against source,
alongside the Japanese face and notices. Previously the build staged the Arabic
font, but the verifier omitted it from the source comparison and only recorded
whatever bytes were in the finished bundle. All 18 package-provenance tests
pass, including rejection of substituted or missing Arabic font and credits
bytes, followed by acceptance after restoring the exact source bytes. Actual
fresh package staging remains pending.

CPU validation in the isolated source worktree:

- All 32 asset-ledger/notices tests pass, including complete attribution,
  original Arabic title, legacy notices and independent stale/missing outputs.
- Both generated outputs are current; `git diff --check` passes.
- Source content validation passes, including the bundled font glyph coverage
  for all staged notices and credits.

The native frontend navigation test now requires the readable acknowledgements
and rejects audit headings/fields. The existing CreditsFontCoverage test still
requires the original Arabic title and the bundled Arabic face. Both pass in
the exact 42-case native selection at signed `558df255` with zero errors or
warnings. The isolated SOURCE editor build succeeds in 45.50 seconds; natural
EOF is `2026-10-27T05:28:35.111035Z`. The native review digest is
`c436d059225e19fa8d3cdf71847486d28a93b4f5e07dcfba56dcfc0fe046f237`.

The subsequent `SoraArena.UIRendered.FrontEndScreens` run also passes with zero
errors/warnings, using Metal Bindless SM6 on the M2 Ultra at 1280×720. Its outer
collection wrapper fails because the generic capture tool does not recognize
UI-tour frame markers and archives zero frames. That failed status and empty
generic manifest are preserved. A separate review authenticates all 19 original
PNGs against 19 engine screenshot acknowledgements, exact dimensions, fresh
timestamps and hashes. No rerender or image modification was used to recover
them. Recovery review digest:
`946f42ac861f877598b63dcef750a2eeba3ff6140e5976acfc5bef2a81c4a245`.

The top and scrolled credits are visually reviewed: notices are readable,
scrolling stays inside the panel, Back and footer remain visible, and the audit
instructions/storage table are gone. The other 17 frames are authenticated but
not visually reviewed here. The Arabic title passes native font selection and
shaping; it is outside these two sampled scroll positions. Visual review digest:
`39004404bf6a8d81f7e564c04da2002eb534933ef0989d5e966fd5e1f49b0c5e`.

Both runs preserve source/native/Config/Generated inputs and the frozen ROOT
checkout at `c096eb98`. Evidence is under SOURCE's ignored
`Saved/Qualification/2026-10-27/credits-stance-runtime-558df255-attempt1` and
`credits-rendered-558df255-ui-review`. These are editor results; fresh packaged
staging/runtime remain pending. The full lane returned to Claude under
Coordination 263 after terminal processes and an empty inventory were verified.

The collector now recognizes the menu tour's original `LogCore` screenshot
acknowledgements and binds all 19 names to the run's committed source inventory.
It rejects incomplete, duplicate, reordered, replayed or wrong-size records,
and stale, missing, corrupt or symlinked originals, retaining authenticated
frames when a tour fails. All 54 capture-report host tests pass. A CPU replay
against the preserved `558df255` capture archives all 19 original PNGs with
hashes identical to the independent recovery above; 41 original evidence and
image files remain unchanged. Replay review digest:
`37fba23ff4638687af8166ab48bff0b5f8555c61ccf848fce7d8bb8a2b78a617`.
This fixes future collection without changing the original failed wrapper or
claiming another engine run, visual approval, or packaged qualification.
