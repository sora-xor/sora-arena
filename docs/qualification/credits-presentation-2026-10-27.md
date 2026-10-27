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
requires the original Arabic title and the bundled Arabic face. Those native
tests have not run at this source. Native font shaping, both credits capture
positions, menu scrolling, and fresh packaged staging/runtime remain pending.
No Unreal, Blender, build or render process was launched for this source work;
Claude retains the full engine lane under Coordination 256.
