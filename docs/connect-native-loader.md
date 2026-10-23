# Native bridge loader qualification

`SoraArena.Connect.NativeLoader` runs in both Unreal EditorContext and
ClientContext. It constructs an uninitialized, test-only wallet subsystem and
calls its private production `LoadNativeBridge()`. It does not add a Blueprint,
menu action or other product flow. Missing libraries, ABI mismatches or missing
required exports fail the test rather than skipping it.

The production resolver still selects `SORA_CONNECT_BRIDGE` when configured,
otherwise the current project's platform-specific `Binaries` path. This test
requires the override to be unset so an external development library cannot
stand in for the staged artifact. It reports the resolved absolute path and
editor/client context. The normal loader requires ABI 30 and all mandatory
bindings; qualification additionally requires the feature-negotiated research
builder and non-authorizing Join-inspector exports. Their availability is
reported separately and neither endpoint is called by this test.

The only native operations invoked are ABI reporting, strict canonical JSON,
BLAKE3 hashing and buffer release. A harmless nested JSON object must become
exact sorted compact bytes, match the separate hash export, preserve its digest
under key/whitespace permutation and change its digest when a value changes.
Top-level and nested duplicate keys and trailing data must be rejected without
an output buffer or stale digest. Allocated buffers are released before the
library handle is closed.

The test checks that the six-action Arena allowlist still excludes NFT wagering,
unrelated transfer/batch instructions and case variants. Join and Buy continue
to require the unavailable qualified terms review: loading the builder or
read-only inspector never enables either signing path. No pairing, HTTP,
WebSocket, key generation, wallet approval, scaffold construction, signing or
submission is attempted. The subsystem is never initialized, so no recovery file
is read and no session ticker is installed; the test also asserts these objects
and signing payloads remain absent and both state machines remain idle.

After staging the verified ABI 30 library and building a current candidate, run
these as separate editor and packaged checks:

```sh
env -u SORA_CONNECT_BRIDGE scripts/toolchain/run-automation-mac.sh SoraArena.Connect.NativeLoader
env -u SORA_CONNECT_BRIDGE scripts/toolchain/test-packaged-mac.sh /absolute/archive/directory SoraArena.Connect.NativeLoader
```

The editor wrapper builds the editor module. The packaged wrapper requires an
already staged package and runs its own binary, not the editor's. Preserve each
run's automation report and log alongside the staged library's hash and build
provenance. A successful editor result establishes only that process's loader
and local calls; it does not establish packaged or Windows loading, research
builder semantics, live wallet interoperability, transaction approval,
submission or finality. The source addition itself is not execution evidence.
