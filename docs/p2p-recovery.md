# Local P2P evidence recovery

`arena_core::recovery::DurableSession` wraps the rollback session in an append-only
first-release version-2 journal. This is local evidence storage, not the Iroha transaction
format, an execution proof, a signed payout, or authority to resolve a missing
reveal. There are no legacy decoders.

The caller supplies an independently authenticated admission: network, session,
manifest, permanent ordered gameplay keys, match configuration, exact deposits
and equipment. The header binds those terms, the reference rules version and the
initial deterministic state. Restore compares them byte-for-byte rather than
trusting self-declared terms in a recovered file. The chain adapter that supplies
this authenticated admission is still required.

Every accepted commitment certificate, individual reveal, signed checkpoint,
signed handshake offer, interruption and local finish is length bounded,
sequenced and hash chained.
Certificates and checkpoints are checked with every original Ed25519 key. Each
reveal must open its exact certified input commitment. Every player commits
exactly `BATCH_TICKS = 2` canonical controls per batch. This is a fixed protocol
contract, including the final batch; shorter batches are rejected. Only all
matching reveals advance the confirmed simulation; individual reveals stay
durable during withholding. Retrying the exact retained partial reveal is
idempotent. Already-received reveals may be grouped into one durable record and
one sync; the caller must not wait for a withholding peer to fill a group. An
invalid group is rejected atomically, so its valid members must be resubmitted
individually or in a valid group. Predicted state is never stored as confirmed
evidence and is discarded on interruption.

If all received openings authenticate but the reference simulation cannot execute
the complete batch, the openings remain durable. `resolution_fault()` exposes
the execution error, the session enters resolution, and its confirmed combat
state does not advance. Local finish remains blocked by the unresolved certified
frontier. A native dispute verifier must decide that outcome.

The writer validates a candidate state before writing, appends its record, calls
`sync_all`, and only then acknowledges the operation and adopts that state. An
uncertain write poisons the open handle so it cannot blindly retry. Creation uses
`create_new` and an exclusive advisory file lock; opening a second writer fails.
Unix creation also syncs the parent directory. Torn, oversized, reordered,
altered, unknown or trailing record bytes fail recovery without truncating or
rewriting the original evidence. Recovering damaged storage from authenticated
peer/ledger copies remains an integration task.

`recovery::inspect_prefix` provides a separate read-only dispute inspection path.
It opens the file read-only, acquires a shared advisory lock, bounds reads to the
same file limit, checks the caller's exact admission, and replays the same
canonical record decoder and certificate checks as full restore. A cooperative
active writer prevents inspection. The result contains the last fully verified
receipt, exclusive prefix byte end, observed file size, confirmed session,
pending certificate, partial openings, accepted handshake offer digests, and
any resolution fault. It retains
no file handle and exposes no writer or repair operation.

An externally retained minimum receipt must occur inside that verified prefix;
otherwise inspection returns an error without exposing an authenticated prefix.
If corruption follows the minimum, `failure()` identifies the failing record's
absolute zero-based start and verification location. A truncated field reports
the exact first missing byte and expected field end. A bad sequence or size
reports that field's start; a hash mismatch reports the digest field; a decode
or semantic failure reports the payload start. Cryptography cannot determine
which original byte was changed from a digest mismatch, so the latter locations
are verification boundaries, not claims to identify a tampered byte. Inspection
does not skip a bad record, silently truncate, or permit writer continuation.
A prefix with no partial final record cannot detect a missing whole suffix
beyond the caller's minimum receipt.

Each successful call yields a receipt with the record count and chain digest.
Restore requires a previously trusted receipt and rejects a file that no longer
contains it. A receipt retained only inside the same file cannot detect removal
of a whole suffix. The transport/chain integration must retain the receipt
independently before relying on a frontier; this is explicit in the API. The
journal contains controls, salts, public signatures and signed ephemeral public
offers, never wallet, gameplay or ephemeral private keys. It is not encrypted at rest.

A match may end during the first tick of a certified two-tick batch. The complete
input batch stays in the transcript, but controls after the first terminal
transition have no gameplay effect. The combat clock records the actual terminal
tick and the evidence clock records the end of the revealed batch. No new batch
is accepted after the combat state becomes terminal.

The current file limit is 64 MiB and the individual record limit is 4 KiB. The
largest 12-player two-tick batch with one certificate, twelve separate reveals,
and one full checkpoint occupies 3,250 bytes (2,788 bytes with a single grouped
reveal record); 18,000 such batches plus admission fit the file bound. Immutable
history uses shared 64-batch chunks so transactional candidates do not copy all
prior controls and signatures for every append. A signed offer record is 158
bytes; the full 1,024-offer allowance for all twelve responder slots adds at
most 1,941,504 bytes. The full-clock journal and handshake capacity are not a
measured simultaneous workload.

One measured local diagnostic completed 36,000 ticks with 12 players using idle
controls, grouped reveals and shared history: 36,002 records, 34,039,658 bytes,
262,165 ms append time, and 39,716 ms restore time. Restored and original terminal
state hashes matched. This measures this machine's local idle-input journal
I/O/replay only. It does not qualify combat, network latency, concurrent clients,
STARK proving, or power-loss safety. Windows filesystem durability remains
unqualified. Native dispute resolution, complete network transport and financial
settlement remain gated.

Focused tests exercise restarts with missing reveals, terminal completion without
another final signature, exact admission rejection, duplicate writers, corrupted
and torn records, receipt rollback, and a forged signature whose surrounding
record digest was recomputed. Five additional prefix tests check every cut point
of a final reveal record, preserved pending openings, exact diagnostic offsets,
atomic semantic rejection, external-receipt enforcement, file/record bounds,
admission mismatch and active-writer exclusion. The original bytes are compared
after inspection. These tests do not constitute a native FPS proof.

## Encrypted evidence datagrams

`arena_core::encrypted_wire` wraps a signed `WireFrame` in a versioned,
length-bounded ChaCha20-Poly1305 datagram. It does not change the canonical
inner wire bytes or their Ed25519 checks. Each instance is one pairwise,
unidirectional sender-to-receiver channel. The
`arena_core::handshake` module can establish its key and 32-byte channel
binding after both peers have the same authenticated admission `Context`.
The initiator signs a fixed-length X25519 offer with its admitted Ed25519
gameplay key. The responder verifies it, signs a fixed-length response
including the exact offer digest, and both sides derive separate directional
keys and a channel binding with HKDF-SHA256 over the shared secret and full
signed transcript. The transcript includes the network, session, manifest,
ordered roster and initiator/responder slots. Non-contributory public keys,
malformed lengths, invalid signatures and changed contexts are rejected.
X25519 secrets and channel key buffers use zeroizing types. A key is fresh for this
sender, receiver, channel and direction; it is never shared across directions
or sessions. Associated data binds the protocol version, sender, sequence,
96-bit OS-random nonce, exact ciphertext
length, channel binding and independently authenticated admission context.

The sender refuses a sequence at or below its current floor. The receiver
rejects a replay or reordered sequence, then checks the AEAD tag, the signed
inner frame and exact agreement between the outer and inner sender/sequence.
Failed packets do not advance its floor. The receiver's accepted sequence floor
and the sender's emitted sequence floor must be retained outside the datagram
channel and restored after restart. A fresh key can begin with no floor; callers
must not treat constructing a new channel with an old key and an empty floor as
a new session. The 96-bit nonce is generated independently for each packet by
the operating-system random source, including after restart. The probability
of collision is negligible at match packet counts, but the transport still
needs lifecycle limits and rekeying policy before production qualification.

`EncryptedSender::seal_fragments` divides a sealed packet into canonical
datagrams of at most 1,200 bytes; the largest twelve-player certificate takes
two. Each fragment is independently authenticated with HMAC-SHA256 under a
domain-separated derivative of the pairwise channel key. A receiver accepts
out-of-order fragments, retains at most four incomplete packets per peer,
evicts the oldest incomplete sequence for a newer one, rejects conflicting or
malformed fragments, and checks the complete packet's
SHA-256 digest before the ordinary AEAD and Ed25519 checks. Duplicate fragments
do not advance the replay floor. A receiver must call `open_fragment` on the
same channel instance and persist its accepted sequence floor as above. This
framing by itself does not supply retransmission, congestion control, NAT
traversal, peer discovery or a network transport. The separate test-only
localhost transport adds bounded authenticated ACK/retry for already sealed
fragments; see [its current limits](p2p-localhost.md).

The responder's `OfferReplayGuard` rejects an already accepted signed
offer, including when it could generate a fresh local ephemeral secret. Its
accepted offer digests must be persisted with the match evidence before the
caller sends the returned response or uses the keys, then restored across
reconnects. `DurableSession::accept_handshake_offer` verifies the admitted
signature, syncs the exact public offer to the journal, and only then returns
the response and channel keys. Restore and read-only prefix inspection verify
the signature again and reconstruct the responder's replay set. The caller
must retain the returned journal receipt independently before sending the
response; a missing whole suffix cannot be detected from the journal alone.
The guard retains at most 1,024 accepted offers per responder per match and
rejects further offers when full; recovery must preserve the current channel
or end the match under the certified disconnect rules. The initiator
keeps its one-use secret in memory only; an old response cannot complete a new
local offer. After a restart the initiator generates a new offer. The signed
handshake does not establish that the remote human is honest or that an
admission context was selected correctly; those are separate qualification
requirements.

These primitives implement local key agreement and authenticated datagrams.
The localhost research path implements bounded ACK/retry, but neither path
implements peer discovery, NAT traversal, packet relays, production congestion
control, or a live multi-peer network transport. It is not an execution proof or a substitute for the
certified commitment frontier and durable evidence journal.
