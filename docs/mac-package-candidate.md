# Mac package candidate binding

The Mac qualification wrappers bind a declared game commit and native bridge
commit to the built, cooked and archived files. This is local provenance and
client automation evidence. It does not establish release signing, Windows
support, live wallet/settlement behavior, final art quality or performance.

Prepare the actual imported content, staged kernel and native bridge before
starting. The bridge must have its original adjacent `.dylib.build.json` from
`scripts/connect/build-bridge.sh`, with ABI 30 verification and hashes matching
its current consumer files: the Connect ABI checker, native verifier and
Wallet subsystem, plus `kernel_abi.py`, `arena.h` and `ArenaKernelSubsystem.cpp`.
If the producer also records `build-bridge.sh`, that hash must match too.
Preserve older producer records; a separate
consumer requalification note does not rewrite the original producer record.

On the single Unreal process lane, with clean committed candidate source:

```sh
export SORA_CANDIDATE_SOURCE="$(git rev-parse HEAD)"
# Use the exact clean native source represented by the selected build sidecar.
export SORA_CANDIDATE_NATIVE=10ad7daddf73212e81496620aba628ebf214ab72
scripts/toolchain/build-mac.sh Development Editor
scripts/toolchain/build-mac.sh Development Game
scripts/toolchain/cook-mac.sh
scripts/toolchain/stage-mac.sh Local/Packages/candidate-mac
scripts/toolchain/test-packaged-mac.sh Local/Packages/candidate-mac SoraArena
```

Choose a fresh empty archive directory for each candidate. The native revision
above identifies the current reviewed local bridge source; it is not a claim
that a package using it has passed qualification. The full source IDs are
required at stage/test so an older package cannot acquire a newer checkout's
label. Ordinary development builds/cooks can run without the declarations;
they invalidate their previous qualification receipt and create no new one.

Successful declared builds/cooks write receipts under
`Saved/Qualification/MacArtifacts`. They record clean Git commit/tree identity,
configuration/native/kernel inputs and actual output hashes. Cook also checks
that its editor module came from this source and hashes all project content,
including ignored generated assets. Changes during the run reject the receipt.
An unstamped earlier build or cook must be rerun; timestamps are insufficient.

Before `-skipbuild -skipcook`, staging validates both receipts and their current
files. After UAT, it checks the staged native library against the untouched
producer sidecar, checks non-UFS game data, and compares the game executable
with its built code. Apple's CodeSign removes signatures only from temporary
copies for that comparison, allowing the archive's resource seal to change
without accepting different executable code. Normal strict bundle-signature
verification remains required. `package-candidate.json` beside the archived
app records the final hashes of every bundled file and the input receipts.

Packaged tests verify those files before and after execution and save the
candidate evidence with their report. The existing Japanese startup smoke,
strict signature and cooked material-fallback checks remain. The report must
match the requested discovery, contain no duplicate/missing/unfinished tests,
and have neither error counters nor error events, even if a test says Success.
When the selection includes `SoraArena.Connect.NativeLoader`, exactly that
test must run in client context, name the actual staged library, and report
ABI 30, research builder/Join inspector availability and the existing blocked
Join/Buy signing gates. That test performs only local loading, canonical JSON
and hashing; it does not pair, sign or submit anything.

Host regression checks (no Unreal or Cargo process):

```sh
python3 -m unittest discover -s scripts/toolchain -p test_mac_candidate.py
python3 -m unittest discover -s scripts/toolchain -p test_packaged_report.py
# On macOS only (separate from portable source CI):
python3 -m unittest discover -s scripts/toolchain -p test_mac_codesign.py
bash -n scripts/toolchain/{build,cook,stage,test-packaged}-mac.sh
```

The macOS host test compares differently signed copies of `/usr/bin/true`
without executing them. The remaining tests use temporary fake artifact bytes
to exercise stale source, changed output, substituted bridge evidence and
failed-report rejection; they are not native or packaged runtime evidence.

The editor runner uses the same discovery/error checks with explicit editor
context and its project bridge path. It writes `results.tsv` beside its report
and retains its Config mutation guard. Passing editor automation remains
separate from the source-bound packaged candidate qualification above.
