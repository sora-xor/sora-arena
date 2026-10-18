//! Research UDP mesh for every admitted evidence peer of one offline match.
//!
//! Each peer owns one UDP socket and one durable journal. It runs the signed
//! X25519 handshake with every other roster slot and then exchanges signed,
//! encrypted `WireFrame`s over each pairwise channel. A channel is a
//! sliding window with selective acknowledgement: at most `SEND_WINDOW`
//! sealed frames are in flight, the receiver opens frames strictly in
//! sequence order and holds authenticated fragments of up to
//! `REORDER_WINDOW` later frames until a gap fills. Its HMAC-authenticated
//! ACK reports three things: every frame before one sequence is durable (or
//! can be obtained again after a restart), every frame before another has
//! been accepted, and which later frames it holds. The sender drops durable
//! frames and resends a reported gap after one short delay, any other frame
//! the receiver lacks after the retransmission timeout, and the oldest held
//! frame when its ACK of durability is overdue. Lost,
//! duplicated, reordered or damaged datagrams therefore cost retransmissions,
//! never a different history.
//!
//! Journal records are group-committed. A background writer syncs everything
//! accepted since its previous write at most once per `SYNC_INTERVAL` (one
//! batch at 60 Hz), then syncs the receipt into a separate `ReceiptLog`. No
//! frame, ACK or handshake answer that depends on a record leaves the process
//! before that. Every peer assembles certificates itself
//! (`protocol::FrontierAssembler`), gathers checkpoint signatures, and after
//! a handshake replaces a channel it resends what a restarted peer may have
//! lost with its process.
//!
//! When the evidence stops advancing, `run_headless` stops combat with a
//! journaled interrupt, keeps exchanging certificates and openings, and
//! finishes once no certified frontier awaits an opening. A frontier whose
//! missing opening only a dropped peer holds needs a consensus deadline.
//!
//! Admission must be offline with zero bond. Addresses are loopback unless
//! the caller explicitly chooses `NetworkScope::ResearchLan`, which admits
//! private and link-local addresses only. There is no matchmaking, NAT
//! traversal, consensus deadline adapter, execution proof or settlement.
use std::{
    cell::OnceCell,
    collections::{BTreeMap, VecDeque},
    fs::{File, OpenOptions},
    io::{self, Read, Seek, SeekFrom, Write},
    net::{IpAddr, SocketAddr, UdpSocket},
    path::Path,
    sync::mpsc,
    thread::{self, JoinHandle},
    time::{Duration, Instant},
};

use ed25519_dalek::SigningKey;

use crate::{
    Error, MAX_PLAYERS, TICK_RATE,
    encrypted_wire::{EncryptedReceiver, EncryptedSender, FragmentDelivery},
    fragmented_wire::MAX_DATAGRAM_BYTES,
    handshake::{self, HandshakeKind, Initiator, OFFER_PACKET_BYTES, PairwiseKeys},
    protocol::{
        BATCH_TICKS, CertifiedFrontiers, CommitmentSet, EvidenceLog, FrontierAssembler, Hash,
        MAX_ASSEMBLY_FRONTIERS, MAX_OUTSTANDING_FRONTIERS, Phase, Reveal, SlotSignature,
        commitment_due,
    },
    recovery::{
        DurableSession, GroupWriter, MAX_REVEAL_GROUP, Receipt, RecoveryError, StagedRecords,
    },
    rollback::{CertifiedCheckpoint, Checkpoint, MAX_PREDICTION_TICKS, RollbackSession},
    simulation::Input,
    wire::{WireFrame, WireMessage},
};

const ACK_MAGIC: &[u8] = b"SORA-ARENA-MACK";
const ACK_VERSION: u16 = 1;
/// Magic, version, the acknowledged sender's slot, the durable and received
/// sequence floors and the bitmap of held later frames.
const ACK_HEADER_BYTES: usize = ACK_MAGIC.len() + 2 + 1 + 8 + 8 + 8;
const ACK_PACKET_BYTES: usize = ACK_HEADER_BYTES + 32;
const RECEIPT_LOG_MAGIC: &[u8] = b"SORA-ARENA-RECEIPT-LOG\x01";
const RECEIPT_ENTRY_BYTES: usize = 4 + 32;
const BATCH: u32 = BATCH_TICKS as u32;
const ASSEMBLY_TICKS: u32 = (MAX_ASSEMBLY_FRONTIERS * BATCH_TICKS) as u32;
/// Sealed frames one channel may have in flight before an acknowledgement.
pub const SEND_WINDOW: usize = 32;
/// Later frames a receiver holds while it waits for a missing one: the width
/// of the ACK bitmap.
pub const REORDER_WINDOW: u64 = 64;
/// Fragments held for one later frame; a twelve-player certificate has two.
const MAX_HELD_FRAGMENTS: usize = 4;
/// Frames queued for one remote, sealed or not. A batch adds about four.
pub const MAX_OUTBOUND: usize = 512;
/// Queue space kept free for the frames of the batch being committed.
const OUTBOUND_HEADROOM: usize = 16;
/// Authenticated messages from one remote that arrived ahead of this peer.
/// A remote certifies at most one assembly window beyond this peer and
/// commits one more window ahead, so its commitments and endorsements for
/// later windows fit in 64, leaving room for certificates and checkpoints.
const MAX_DEFERRED_PER_PEER: usize = 128;
/// Checkpoint ticks with signatures still being gathered.
const MAX_CHECKPOINT_VOTES: usize = 16;
/// Openings of assembled but not yet certified frontiers.
const MAX_EARLY_OPENINGS: usize = MAX_ASSEMBLY_FRONTIERS * MAX_PLAYERS;
/// Own signatures resent to a restarted peer.
const OWN_VOTES_KEPT: usize = 4;
/// Confirmed ticks between gathered checkpoints: two seconds.
pub const CHECKPOINT_INTERVAL_TICKS: u32 = 2 * TICK_RATE;
/// At most one journal sync per batch at 60 Hz.
pub const SYNC_INTERVAL: Duration =
    Duration::from_nanos(1_000_000_000 * BATCH_TICKS as u64 / TICK_RATE as u64);
/// First retransmission timeout for a frame the receiver does not hold. The
/// receiver reports accepted frames at once, before they are durable, so
/// this only has to cover the round trip and both peers' loop latency.
pub const RETRANSMIT_INITIAL: Duration = Duration::from_millis(60);
const RETRANSMIT_MAX: Duration = Duration::from_millis(800);
/// A frame the receiver reports missing behind frames it holds is resent
/// once this long after its last send, before the timeout. It exceeds the
/// research impairment's 8 ms reordering hold.
const GAP_RESEND_AFTER: Duration = Duration::from_millis(15);
/// A held frame still not durable after this long is resent once more, so a
/// lost ACK of durability is repeated. It covers a sync interval and slow
/// contended syncs.
const DURABLE_PROBE_AFTER: Duration = Duration::from_millis(400);
const OFFER_RETRY: Duration = Duration::from_millis(100);
/// Unanswered sends of one offer before a fresh one replaces it, in case the
/// responder accepted it before a crash and now refuses it as a replay.
const OFFER_ATTEMPTS: u32 = 20;
const MAX_DRAIN: usize = 512;
const HELD_DATAGRAM: Duration = Duration::from_millis(8);
const WRITER_POLL: Duration = Duration::from_millis(1);

#[derive(Debug)]
pub enum MeshError {
    Io(io::Error),
    Evidence(Error),
    Journal(RecoveryError),
    /// An authenticated peer sent evidence this peer cannot accept.
    Peer {
        slot: usize,
        error: Error,
    },
    /// Combat stopped, and `pending` certified frontiers still lacked an
    /// opening when the resolve limit passed. The journal keeps the
    /// interrupt and every pending frontier; only a consensus deadline, which
    /// this transport cannot produce, can close them. `detail` is the peer's
    /// `describe()` at that moment.
    Unresolved {
        confirmed: u32,
        pending: usize,
        detail: String,
    },
    /// The caller stopped the peer before the match ended.
    Stopped {
        confirmed: u32,
    },
}

impl std::fmt::Display for MeshError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(error) => error.fmt(f),
            Self::Evidence(error) => error.fmt(f),
            Self::Journal(error) => error.fmt(f),
            Self::Peer { slot, error } => write!(f, "peer {slot}: {error}"),
            Self::Unresolved {
                confirmed,
                pending,
                detail,
            } => write!(
                f,
                "combat stopped at confirmed tick {confirmed}; {pending} certified frontiers await openings only a consensus deadline can forfeit\n{detail}"
            ),
            Self::Stopped { confirmed } => {
                write!(f, "peer stopped at confirmed tick {confirmed}")
            }
        }
    }
}
impl std::error::Error for MeshError {}
impl From<io::Error> for MeshError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}
impl From<Error> for MeshError {
    fn from(error: Error) -> Self {
        Self::Evidence(error)
    }
}
impl From<RecoveryError> for MeshError {
    fn from(error: RecoveryError) -> Self {
        Self::Journal(error)
    }
}
type Result<T> = std::result::Result<T, MeshError>;

fn blame(slot: usize) -> impl FnOnce(Error) -> MeshError {
    move |error| MeshError::Peer { slot, error }
}

fn blame_journal(slot: usize) -> impl FnOnce(RecoveryError) -> MeshError {
    move |error| match error {
        RecoveryError::Evidence(error) => MeshError::Peer { slot, error },
        other => MeshError::Journal(other),
    }
}

/// Which addresses a mesh may use.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NetworkScope {
    /// Loopback only: tests and single-machine research.
    Loopback,
    /// Private, link-local or loopback addresses on a research LAN, chosen
    /// explicitly. Admission must still be offline with zero bond.
    ResearchLan,
}

impl NetworkScope {
    fn admits(self, address: SocketAddr) -> bool {
        let ip = address.ip();
        if ip.is_unspecified() || ip.is_multicast() || address.port() == 0 {
            return false;
        }
        match (self, ip) {
            (_, ip) if ip.is_loopback() => true,
            (Self::Loopback, _) => false,
            (Self::ResearchLan, IpAddr::V4(ip)) => ip.is_private() || ip.is_link_local(),
            (Self::ResearchLan, IpAddr::V6(ip)) => {
                ip.is_unique_local() || ip.is_unicast_link_local()
            }
        }
    }
}

/// Research-only damage to this peer's outgoing datagrams, chosen by a
/// seeded generator: drop one, send it twice, hold it behind later
/// datagrams, or flip one byte. Rates are per mille. Handshake packets and
/// ACKs are impaired like evidence.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Impairment {
    pub drop_per_mille: u16,
    pub duplicate_per_mille: u16,
    pub reorder_per_mille: u16,
    pub corrupt_per_mille: u16,
    pub seed: u64,
}

/// Counters for one peer process. Byte and datagram counts include every
/// handshake, frame, retransmission and ACK.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct MeshStats {
    pub datagrams_sent: u64,
    pub datagrams_received: u64,
    pub bytes_sent: u64,
    pub bytes_received: u64,
    pub send_errors: u64,
    /// Frames sealed and sent for the first time on a channel.
    pub frames_sent: u64,
    /// Frames accepted in order and handed to the protocol.
    pub frames_received: u64,
    /// Datagrams resent, for a reported gap or after a timeout.
    pub retransmitted: u64,
    pub timeouts: u64,
    /// Frames resent early because the receiver reported them missing
    /// behind frames it holds.
    pub fast_retransmits: u64,
    /// Held frames resent because their durability was not acknowledged.
    pub probes: u64,
    pub acks_sent: u64,
    pub acks_received: u64,
    /// Authenticated fragments of frames already accepted.
    pub duplicates: u64,
    /// Authenticated fragments beyond the next expected sequence: held when
    /// within `REORDER_WINDOW`, dropped beyond it.
    pub out_of_order: u64,
    /// Datagrams that failed authentication, framing or source checks.
    pub rejected: u64,
    /// Authenticated next frames this peer could not verify yet, such as an
    /// opening of a frontier it has not assembled. They are not ACKed, so
    /// the sender retransmits them.
    pub unready: u64,
    /// New frames refused while this peer held too many early messages.
    pub backpressured: u64,
    pub offers_sent: u64,
    /// Authenticated channels installed, including replacements after an
    /// unanswered offer expires or a peer restarts.
    pub handshakes: u64,
    /// Installations that replaced an already established channel.
    pub replaced_channels: u64,
    /// Openings verified against an assembled set before certification.
    pub early_openings: u64,
    /// Messages held until this peer caught up.
    pub deferred: u64,
    pub relayed_certificates: u64,
    pub checkpoints_retained: u64,
    /// Complete checkpoints that fell out of the boundary window first.
    pub checkpoints_missed: u64,
    pub journal_syncs: u64,
    pub journal_sync_micros: u64,
    pub journal_sync_max_micros: u64,
    pub receipt_syncs: u64,
    pub receipt_sync_micros: u64,
    pub receipt_sync_max_micros: u64,
    pub records_synced: u64,
    pub bytes_synced: u64,
    pub impaired_dropped: u64,
    pub impaired_duplicated: u64,
    pub impaired_reordered: u64,
    pub impaired_corrupted: u64,
}

/// An append-only log of journal receipts beside the journal, synced after
/// each group write and before anything depending on it is released. Like
/// `localhost_transport::ReceiptFiles` it is a test-harness artifact, not an
/// independently trusted rollback anchor.
pub struct ReceiptLog {
    file: File,
    latest: Receipt,
}

impl ReceiptLog {
    /// A new log whose first entry is the journal's admission receipt.
    pub fn create(path: &Path, genesis: Receipt) -> io::Result<Self> {
        let mut file = OpenOptions::new()
            .read(true)
            .write(true)
            .create_new(true)
            .open(path)?;
        file.try_lock().map_err(io::Error::from)?;
        let mut bytes = RECEIPT_LOG_MAGIC.to_vec();
        bytes.extend(entry(genesis));
        file.write_all(&bytes)?;
        file.sync_all()?;
        #[cfg(unix)]
        File::open(
            path.parent()
                .filter(|parent| !parent.as_os_str().is_empty())
                .unwrap_or(Path::new(".")),
        )?
        .sync_all()?;
        Ok(Self {
            file,
            latest: genesis,
        })
    }

    /// Reopen after a restart. A torn or non-increasing entry fails closed.
    pub fn open(path: &Path) -> io::Result<Self> {
        let mut file = OpenOptions::new().read(true).write(true).open(path)?;
        file.try_lock().map_err(io::Error::from)?;
        let mut bytes = Vec::new();
        file.read_to_end(&mut bytes)?;
        let corrupt = |reason| io::Error::new(io::ErrorKind::InvalidData, reason);
        let entries = bytes
            .strip_prefix(RECEIPT_LOG_MAGIC)
            .ok_or_else(|| corrupt("receipt log magic differs"))?;
        if entries.is_empty() || !entries.len().is_multiple_of(RECEIPT_ENTRY_BYTES) {
            return Err(corrupt("receipt log entry is torn"));
        }
        let mut latest: Option<Receipt> = None;
        for chunk in entries.chunks(RECEIPT_ENTRY_BYTES) {
            let receipt = Receipt {
                records: u32::from_le_bytes(chunk[..4].try_into().expect("four bytes")),
                digest: chunk[4..].try_into().expect("digest bytes"),
            };
            if latest.is_some_and(|previous| receipt.records <= previous.records) {
                return Err(corrupt("receipt log is not increasing"));
            }
            latest = Some(receipt);
        }
        file.seek(SeekFrom::End(0))?;
        Ok(Self {
            file,
            latest: latest.expect("at least one entry"),
        })
    }

    pub fn latest(&self) -> Receipt {
        self.latest
    }

    pub fn append(&mut self, receipt: Receipt) -> io::Result<()> {
        if receipt.records <= self.latest.records {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "receipt log only grows",
            ));
        }
        self.file.write_all(&entry(receipt))?;
        self.file.sync_all()?;
        self.latest = receipt;
        Ok(())
    }
}

fn entry(receipt: Receipt) -> [u8; RECEIPT_ENTRY_BYTES] {
    let mut bytes = [0; RECEIPT_ENTRY_BYTES];
    bytes[..4].copy_from_slice(&receipt.records.to_le_bytes());
    bytes[4..].copy_from_slice(&receipt.digest);
    bytes
}

struct WriteDone {
    result: std::result::Result<Receipt, RecoveryError>,
    journal: Duration,
    receipts: Duration,
    bytes: usize,
}

/// Background journal writer: one write and sync of the journal, then one
/// append and sync of the receipt log, per hand-off.
struct Writer {
    requests: Option<mpsc::Sender<StagedRecords>>,
    done: mpsc::Receiver<WriteDone>,
    busy: bool,
    thread: Option<JoinHandle<()>>,
}

impl Writer {
    fn spawn(mut journal: GroupWriter, mut receipts: ReceiptLog) -> io::Result<Self> {
        let (requests, jobs) = mpsc::channel::<StagedRecords>();
        let (finished, done) = mpsc::channel();
        let thread = thread::Builder::new()
            .name("arena-journal-writer".into())
            .spawn(move || {
                for staged in jobs {
                    let started = Instant::now();
                    let written = journal.write(&staged);
                    let journal_time = started.elapsed();
                    let started = Instant::now();
                    let result = written.and_then(|receipt| {
                        receipts.append(receipt)?;
                        Ok(receipt)
                    });
                    let failed = result.is_err();
                    let report = WriteDone {
                        result,
                        journal: journal_time,
                        receipts: started.elapsed(),
                        bytes: staged.len(),
                    };
                    if finished.send(report).is_err() || failed {
                        break;
                    }
                }
            })?;
        Ok(Self {
            requests: Some(requests),
            done,
            busy: false,
            thread: Some(thread),
        })
    }

    fn submit(&mut self, staged: StagedRecords) -> Result<()> {
        self.requests
            .as_ref()
            .and_then(|requests| requests.send(staged).ok())
            .ok_or(MeshError::Journal(RecoveryError::Poisoned))?;
        self.busy = true;
        Ok(())
    }
}

impl Drop for Writer {
    fn drop(&mut self) {
        self.requests.take();
        if let Some(thread) = self.thread.take() {
            let _ = thread.join();
        }
    }
}

/// The socket plus research impairment of outgoing datagrams.
struct Net {
    socket: UdpSocket,
    blocking: bool,
    impairment: Impairment,
    random: u64,
    held: VecDeque<(Instant, SocketAddr, Vec<u8>)>,
}

impl Net {
    fn next_random(&mut self) -> u64 {
        // SplitMix64: a fixed, seedable stream for reproducible damage.
        self.random = self.random.wrapping_add(0x9e37_79b9_7f4a_7c15);
        let mut z = self.random;
        z = (z ^ (z >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
        z ^ (z >> 31)
    }

    fn roll(&mut self, per_mille: u16) -> bool {
        per_mille > 0 && self.next_random() % 1000 < u64::from(per_mille)
    }

    fn send(&mut self, to: SocketAddr, bytes: &[u8], stats: &mut MeshStats) {
        let impairment = self.impairment;
        if self.roll(impairment.drop_per_mille) {
            stats.impaired_dropped += 1;
            return;
        }
        let mut damaged = None;
        if self.roll(impairment.corrupt_per_mille) {
            let mut copy = bytes.to_vec();
            let index = (self.next_random() % copy.len() as u64) as usize;
            copy[index] ^= 1 << (self.next_random() % 8);
            damaged = Some(copy);
            stats.impaired_corrupted += 1;
        }
        let bytes = damaged.as_deref().unwrap_or(bytes);
        if self.roll(impairment.reorder_per_mille) {
            self.held
                .push_back((Instant::now() + HELD_DATAGRAM, to, bytes.to_vec()));
            stats.impaired_reordered += 1;
            return;
        }
        self.raw_send(to, bytes, stats);
        if self.roll(impairment.duplicate_per_mille) {
            self.raw_send(to, bytes, stats);
            stats.impaired_duplicated += 1;
        }
        // A held datagram now trails at least one later datagram.
        if let Some(position) = self.held.iter().position(|(_, held, _)| *held == to) {
            let (_, to, bytes) = self.held.remove(position).expect("held datagram");
            self.raw_send(to, &bytes, stats);
        }
    }

    fn release_held(&mut self, now: Instant, stats: &mut MeshStats) {
        while self.held.front().is_some_and(|(due, _, _)| *due <= now) {
            let (_, to, bytes) = self.held.pop_front().expect("held datagram");
            self.raw_send(to, &bytes, stats);
        }
    }

    /// UDP is lossy: a full buffer or an ICMP refusal from a restarting peer
    /// loses this datagram, and retransmission covers it. A persistent
    /// failure shows up as a stall.
    fn raw_send(&self, to: SocketAddr, bytes: &[u8], stats: &mut MeshStats) {
        debug_assert!(bytes.len() <= MAX_DATAGRAM_BYTES);
        match self.socket.send_to(bytes, to) {
            Ok(sent) if sent == bytes.len() => {
                stats.datagrams_sent += 1;
                stats.bytes_sent += sent as u64;
            }
            _ => stats.send_errors += 1,
        }
    }

    fn recv(
        &mut self,
        wait: Option<Duration>,
        buffer: &mut [u8],
    ) -> io::Result<Option<(usize, SocketAddr)>> {
        match wait {
            None if self.blocking => {
                self.socket.set_nonblocking(true)?;
                self.blocking = false;
            }
            Some(wait) => {
                if !self.blocking {
                    self.socket.set_nonblocking(false)?;
                    self.blocking = true;
                }
                self.socket
                    .set_read_timeout(Some(wait.max(Duration::from_micros(100))))?;
            }
            None => {}
        }
        match self.socket.recv_from(buffer) {
            Ok(received) => Ok(Some(received)),
            Err(error)
                if matches!(
                    error.kind(),
                    io::ErrorKind::WouldBlock
                        | io::ErrorKind::TimedOut
                        | io::ErrorKind::ConnectionReset
                        | io::ErrorKind::ConnectionRefused
                        | io::ErrorKind::Interrupted
                ) =>
            {
                Ok(None)
            }
            Err(error) => Err(error),
        }
    }
}

/// A handshake answer this peer sent as responder, kept to answer a
/// retransmitted offer with the same bytes.
struct Answered {
    offer: [u8; OFFER_PACKET_BYTES],
    response: [u8; handshake::RESPONSE_PACKET_BYTES],
    /// Journal records (the accepted offer) that must be durable first.
    requires: u32,
    unsent: bool,
}

enum Link {
    /// Waiting for the remote's offer.
    Waiting,
    Offering {
        initiator: Box<Initiator>,
        offer: [u8; OFFER_PACKET_BYTES],
        sent: Option<Instant>,
        attempts: u32,
    },
    Up {
        sender: Box<EncryptedSender>,
        receiver: Box<EncryptedReceiver>,
        answered: Option<Box<Answered>>,
    },
}

struct Outbound {
    message: WireMessage,
    /// Journal records that must be durable before this frame may leave.
    requires: u32,
    sealed: Option<Vec<Vec<u8>>>,
    sequence: u64,
    sent_at: Option<Instant>,
    /// The receiver's latest ACK reports holding it; it waits only to
    /// become durable there.
    received: bool,
    /// Already resent once for a gap the receiver reported.
    gap_resent: bool,
}

impl Outbound {
    fn new(message: WireMessage, requires: u32) -> Self {
        Self {
            message,
            requires,
            sealed: None,
            sequence: 0,
            sent_at: None,
            received: false,
            gap_resent: false,
        }
    }
}

/// When an accepted frame may be acknowledged.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum AckGate {
    /// Nothing to journal, or the sender can resend it after a restart.
    Ready,
    /// Once this many journal records are durable.
    Durable(u32),
    /// Once the pending group of received openings is journaled and durable.
    Group,
}

struct Remote {
    slot: usize,
    address: SocketAddr,
    link: Link,
    /// Frames not yet acknowledged on the current channel, oldest first; the
    /// first `in_flight` are sealed.
    outbound: VecDeque<Outbound>,
    in_flight: usize,
    next_sequence: u64,
    rto: Duration,
    /// The highest received floor the receiver reported: every earlier
    /// frame was accepted in order.
    reported_floor: u64,
    /// The highest sequence the receiver reported holding beyond a gap.
    highest_held: Option<u64>,
    /// Accepted frames not yet acknowledged as durable, in sequence order.
    pending_acks: VecDeque<(u64, AckGate)>,
    /// The newest frame acknowledged as durable.
    acked: Option<u64>,
    ack_due: bool,
    /// Authenticated fragments of later frames, until the gap before them
    /// fills.
    held: BTreeMap<u64, Vec<Vec<u8>>>,
    /// The durable floor, received floor and bitmap last acknowledged.
    last_ack: Option<(u64, u64, u64)>,
    deferred: usize,
    /// Resend retained state once the next channel is up.
    resend: bool,
}

impl Remote {
    fn reset_channel(&mut self) {
        for entry in &mut self.outbound {
            entry.sealed = None;
            entry.sent_at = None;
            entry.received = false;
            entry.gap_resent = false;
        }
        self.in_flight = 0;
        self.next_sequence = 0;
        self.rto = RETRANSMIT_INITIAL;
        self.reported_floor = 0;
        self.highest_held = None;
        self.pending_acks.clear();
        self.acked = None;
        self.ack_due = false;
        self.held.clear();
        self.last_ack = None;
    }
}

/// A reveal's frontier from this peer's own evidence: a certified set, or
/// failing that the set it assembled itself. An opening checked against an
/// assembled set is only held until the set is certified.
struct KnownFrontiers<'a> {
    log: &'a EvidenceLog,
    assembler: &'a FrontierAssembler,
    assembled: OnceCell<Option<CommitmentSet>>,
}

impl CertifiedFrontiers for KnownFrontiers<'_> {
    fn certified_frontier(&self, start_tick: u32) -> Option<&CommitmentSet> {
        self.log.certified_frontier(start_tick).or_else(|| {
            self.assembled
                .get_or_init(|| self.assembler.assembled(start_tick))
                .as_ref()
                .filter(|set| set.start_tick == start_tick)
        })
    }
}

enum Applied {
    Done(AckGate),
    Deferred(WireMessage),
}

/// An authenticated UDP socket, every admitted address and one journal.
pub struct MeshAdmission {
    pub socket: UdpSocket,
    /// Every roster slot's admitted address, this peer's own included.
    pub addresses: Vec<SocketAddr>,
    pub local_slot: usize,
    pub identity: SigningKey,
    pub journal: DurableSession,
    pub receipts: ReceiptLog,
    pub scope: NetworkScope,
    pub impairment: Impairment,
}

/// One peer of the mesh. Drive it with `commit`, `predict` and `pump`, or
/// hand it to `run_headless`.
pub struct MeshPeer {
    net: Net,
    local: usize,
    identity: SigningKey,
    journal: DurableSession,
    writer: Writer,
    remotes: Vec<Remote>,
    assembler: FrontierAssembler,
    next_commit: u32,
    /// Own endorsements of sets not yet certified, to resend.
    endorsed: BTreeMap<u32, (CommitmentSet, SlotSignature)>,
    early: BTreeMap<(u32, usize), Reveal>,
    deferred: VecDeque<(usize, WireMessage)>,
    reveal_group: Vec<Reveal>,
    votes: BTreeMap<u32, Vec<Option<(Checkpoint, SlotSignature)>>>,
    own_votes: VecDeque<(Checkpoint, SlotSignature)>,
    signed_through: u32,
    finish_records: Option<u32>,
    /// Research only: own commitments from this tick on are never opened.
    withhold_from: Option<u32>,
    last_write: Option<Instant>,
    last_datagram: Instant,
    stats: MeshStats,
    buffer: Vec<u8>,
}

impl MeshPeer {
    /// Join a new match from an empty journal. Lower slots offer keys to
    /// higher ones.
    pub fn start(admission: MeshAdmission) -> Result<Self> {
        Self::admit(admission, false)
    }

    /// Continue from a journal restored after a crash. This peer offers fresh
    /// keys to every slot and resends its retained state on each channel.
    pub fn resume(admission: MeshAdmission) -> Result<Self> {
        Self::admit(admission, true)
    }

    fn admit(admission: MeshAdmission, restored: bool) -> Result<Self> {
        let MeshAdmission {
            socket,
            addresses,
            local_slot: local,
            identity,
            mut journal,
            receipts,
            scope,
            impairment,
        } = admission;
        let session = journal.session();
        let evidence = session.evidence();
        let context = evidence.context.clone();
        let world = session.confirmed();
        if addresses.len() != context.roster.len() || local >= addresses.len() {
            return Err(Error::InvalidConfig("mesh addresses differ from the roster").into());
        }
        if context.roster[local] != identity.verifying_key().to_bytes() {
            return Err(Error::InvalidEvidence("mesh identity does not own its slot").into());
        }
        if socket.local_addr()? != addresses[local] {
            return Err(
                Error::InvalidConfig("mesh socket is not bound to its admitted address").into(),
            );
        }
        for (index, address) in addresses.iter().enumerate() {
            if !scope.admits(*address) {
                return Err(Error::InvalidConfig(match scope {
                    NetworkScope::Loopback => {
                        "mesh addresses must be loopback unless research LAN is chosen"
                    }
                    NetworkScope::ResearchLan => {
                        "research LAN admits only private, link-local or loopback addresses"
                    }
                })
                .into());
            }
            if addresses[..index].contains(address) {
                return Err(Error::InvalidConfig("mesh addresses must be distinct").into());
            }
        }
        if !world.config.offline
            || world.config.base_bond != 0
            || world.accounts.iter().any(|account| account.initial != 0)
        {
            return Err(Error::InvalidConfig(
                "mesh transport requires offline zero-bond admission",
            )
            .into());
        }
        if evidence.phase == Phase::Terminal {
            return Err(Error::InvalidEvidence("journal already finished").into());
        }
        if restored {
            if receipts.latest().records > journal.receipt().records {
                return Err(Error::InvalidEvidence("receipt log is ahead of the journal").into());
            }
        } else if journal.receipt().records != 0 || receipts.latest() != journal.receipt() {
            return Err(Error::InvalidConfig(
                "a new mesh match needs an empty journal and its receipt log",
            )
            .into());
        }

        let mut assembler = FrontierAssembler::following(evidence);
        let mut next_commit = evidence.certified_tick;
        let sealed = journal
            .sealed_openings()
            .filter(|opening| opening.start_tick >= evidence.certified_tick)
            .cloned()
            .collect::<Vec<_>>();
        for opening in sealed {
            let commitment = opening.commitment(&context, evidence.epoch)?;
            assembler.add_commitment(local, evidence.epoch, opening.start_tick, commitment)?;
            next_commit = next_commit.max(opening.start_tick + BATCH);
        }
        let signed_through = session
            .last_checkpoint()
            .map_or(0, |checkpoint| checkpoint.checkpoint.tick);
        let mut remotes = Vec::with_capacity(addresses.len() - 1);
        for (slot, address) in addresses.iter().enumerate() {
            if slot == local {
                continue;
            }
            let link = if restored || slot > local {
                let (initiator, offer) = Initiator::start(context.clone(), local, slot, &identity)?;
                Link::Offering {
                    initiator: Box::new(initiator),
                    offer,
                    sent: None,
                    attempts: 0,
                }
            } else {
                Link::Waiting
            };
            remotes.push(Remote {
                slot,
                address: *address,
                link,
                outbound: VecDeque::new(),
                in_flight: 0,
                next_sequence: 0,
                rto: RETRANSMIT_INITIAL,
                reported_floor: 0,
                highest_held: None,
                pending_acks: VecDeque::new(),
                acked: None,
                ack_due: false,
                held: BTreeMap::new(),
                last_ack: None,
                deferred: 0,
                resend: restored,
            });
        }
        let group = journal.group_commit()?;
        let writer = Writer::spawn(group, receipts)?;
        socket.set_nonblocking(true)?;
        Ok(Self {
            net: Net {
                socket,
                blocking: false,
                impairment,
                random: impairment.seed ^ (local as u64).wrapping_mul(0xa076_1d64_78bd_642f),
                held: VecDeque::new(),
            },
            local,
            identity,
            journal,
            writer,
            remotes,
            assembler,
            next_commit,
            endorsed: BTreeMap::new(),
            early: BTreeMap::new(),
            deferred: VecDeque::new(),
            reveal_group: Vec::new(),
            votes: BTreeMap::new(),
            own_votes: VecDeque::new(),
            signed_through,
            finish_records: None,
            withhold_from: None,
            last_write: None,
            last_datagram: Instant::now(),
            stats: MeshStats::default(),
            buffer: vec![0; MAX_DATAGRAM_BYTES + 1],
        })
    }

    pub fn local_slot(&self) -> usize {
        self.local
    }
    pub fn session(&self) -> &RollbackSession {
        self.journal.session()
    }
    pub fn journal(&self) -> &DurableSession {
        &self.journal
    }
    pub fn stats(&self) -> &MeshStats {
        &self.stats
    }
    /// The certified checkpoint gathered at the end of combat, once retained.
    pub fn final_checkpoint(&self) -> Option<&CertifiedCheckpoint> {
        let session = self.session();
        session.last_checkpoint().filter(|checkpoint| {
            session.confirmed().terminal && checkpoint.checkpoint.tick == session.confirmed().tick
        })
    }

    /// First tick of the next batch this peer commits.
    pub fn next_commit_tick(&self) -> u32 {
        self.next_commit
    }

    /// Whether the pipeline and every outbound queue have room for the next
    /// batch's commitment.
    pub fn can_commit(&self) -> bool {
        let session = self.session();
        let evidence = session.evidence();
        evidence.phase == Phase::Live
            && !session.confirmed().terminal
            && self.next_commit < session.confirmed().config.max_ticks
            && self.next_commit < evidence.certified_tick + ASSEMBLY_TICKS
            && self
                .remotes
                .iter()
                .all(|remote| remote.outbound.len() + OUTBOUND_HEADROOM <= MAX_OUTBOUND)
    }

    /// Seal this peer's controls for the next batch under a fresh random salt
    /// and queue the commitment to every peer. It leaves only once the
    /// opening is durable.
    pub fn commit(&mut self, inputs: [Input; BATCH_TICKS]) -> Result<Hash> {
        if !self.can_commit() {
            return Err(Error::InvalidEvidence("commitment pipeline is full").into());
        }
        let mut salt = [0; 32];
        getrandom::getrandom(&mut salt)
            .map_err(|_| Error::InvalidConfig("operating system random source unavailable"))?;
        let start_tick = self.next_commit;
        let (commitment, receipt) = self.journal.seal(Reveal {
            start_tick,
            slot: self.local,
            inputs: inputs.to_vec(),
            salt,
        })?;
        let epoch = self.session().evidence().epoch;
        self.assembler
            .add_commitment(self.local, epoch, start_tick, commitment)?;
        self.broadcast(
            WireMessage::Commitment {
                epoch,
                start_tick,
                commitment,
            },
            receipt.records,
        )?;
        self.next_commit += BATCH;
        Ok(commitment)
    }

    pub fn can_predict(&self) -> bool {
        let session = self.session();
        let (confirmed, predicted) = (session.confirmed(), session.predicted());
        session.evidence().phase == Phase::Live
            && !confirmed.terminal
            && predicted.tick < confirmed.config.max_ticks
            && (predicted.tick.saturating_sub(confirmed.tick) as usize) < MAX_PREDICTION_TICKS
    }

    /// Present one speculative tick. Never evidence.
    pub fn predict(&mut self, controls: Vec<Input>) -> Result<()> {
        Ok(self.journal.predict(controls)?)
    }

    /// Each slot's last confirmed control, to predict remote players with.
    pub fn last_confirmed_controls(&self) -> Vec<Input> {
        let evidence = self.session().evidence();
        let count = evidence.context.roster.len();
        evidence
            .batches
            .len()
            .checked_sub(1)
            .and_then(|index| evidence.batches.get(index))
            .map_or_else(
                || vec![Input::default(); count],
                |batch| {
                    batch
                        .openings
                        .iter()
                        .map(|opening| {
                            opening
                                .as_ref()
                                .map_or(Input::default(), |opening| opening.inputs[BATCH_TICKS - 1])
                        })
                        .collect()
                },
            )
    }

    /// Research only: never open this peer's commitment in a frontier
    /// starting at or after `start_tick`, like a peer that withholds its
    /// controls. It still seals, endorses, certifies and relays. Nothing is
    /// journaled, so a restarted peer opens everything it sealed.
    pub fn withhold_openings_from(&mut self, start_tick: u32) {
        self.withhold_from = Some(start_tick);
    }

    /// Stop combat on a dropout: journal an interrupt, after which this peer
    /// commits, endorses and predicts nothing new, even after a restart.
    /// Certified frontiers, every opening received and the last certified
    /// checkpoint stay, and certificates and openings are still accepted.
    /// Every pending certificate and the last certified checkpoint go to
    /// every peer once more, so survivors that gathered different evidence
    /// before the dropout retain the same frontiers, each open its own
    /// commitment in them, and keep the latest checkpoint any of them has.
    pub fn interrupt(&mut self) -> Result<()> {
        let session = self.session();
        if session.evidence().phase != Phase::Live || session.confirmed().terminal {
            return Ok(());
        }
        let receipt = self.journal.interrupt()?;
        let session = self.session();
        let mut shared = session
            .evidence()
            .pending
            .iter()
            .map(|frontier| WireMessage::CommitmentCertificate {
                set: frontier.set.clone(),
                signatures: frontier.signatures.clone(),
            })
            .collect::<Vec<_>>();
        if let Some(checkpoint) = session.last_checkpoint() {
            shared.push(WireMessage::Checkpoint {
                checkpoint: checkpoint.checkpoint.clone(),
                signatures: checkpoint.signatures.clone(),
            });
        }
        for message in shared {
            self.broadcast(message, receipt.records)?;
        }
        Ok(())
    }

    /// Journal the end of this peer's evidence without a final certified
    /// checkpoint: after combat ended but a peer never signed its last
    /// boundary, or after an interrupt once no certified frontier awaits an
    /// opening. The terminal outcome follows from the evidence alone, so a
    /// missing signature cannot erase it. Refused while combat is live or
    /// an interrupted match still has pending frontiers.
    pub fn finish(&mut self) -> Result<()> {
        if self.finish_records.is_none() {
            self.finish_records = Some(self.journal.finish()?.records);
        }
        Ok(())
    }

    /// This peer's own outcome is complete: its finish record is durable,
    /// normally after the final certified checkpoint.
    pub fn is_complete(&self) -> bool {
        self.finish_records
            .is_some_and(|records| self.journal.durable_receipt().records >= records)
            && !self.writer.busy
    }

    /// Frames still waiting for an acknowledgement.
    pub fn unacknowledged(&self) -> usize {
        self.remotes
            .iter()
            .map(|remote| remote.outbound.len())
            .sum()
    }

    /// Complete, and every frame this peer queued has been acknowledged, so
    /// every peer holds all it sent, its last checkpoint signature included.
    pub fn is_finished(&self) -> bool {
        self.is_complete() && self.unacknowledged() == 0
    }

    /// Time since the last datagram arrived.
    pub fn quiet_for(&self) -> Duration {
        self.last_datagram.elapsed()
    }

    /// Exchange datagrams and advance the protocol until `until`.
    pub fn pump(&mut self, until: Instant) -> Result<()> {
        loop {
            self.poll_writer()?;
            self.drain(None)?;
            self.progress()?;
            self.start_write()?;
            self.transmit()?;
            let now = Instant::now();
            if now >= until {
                return Ok(());
            }
            let mut wake = until;
            if self.writer.busy {
                wake = wake.min(now + WRITER_POLL);
            }
            if let Some(timer) = self.next_timer(now) {
                wake = wake.min(timer);
            }
            if wake > now {
                self.drain(Some(wake - now))?;
            }
        }
    }

    /// A one-screen summary of this peer's evidence, pipeline and channels,
    /// for diagnosing a stall.
    pub fn describe(&self) -> String {
        use std::fmt::Write as _;
        let evidence = self.session().evidence();
        let mut out = format!(
            "slot={} closed={} certified={} next_commit={} assembler={} deferred={} early={} votes={:?} records={}/{} durable\n",
            self.local,
            evidence.next_tick,
            evidence.certified_tick,
            self.next_commit,
            self.assembler.next_tick(),
            self.deferred.len(),
            self.early.len(),
            self.votes.keys().collect::<Vec<_>>(),
            self.journal.durable_receipt().records,
            self.journal.receipt().records,
        );
        for frontier in &evidence.pending {
            let _ = writeln!(
                out,
                "  pending tick={} opened={:?}",
                frontier.set.start_tick,
                frontier
                    .openings
                    .iter()
                    .map(Option::is_some)
                    .collect::<Vec<_>>()
            );
        }
        for remote in &self.remotes {
            let link = match &remote.link {
                Link::Waiting => "waiting",
                Link::Offering { .. } => "offering",
                Link::Up { .. } => "up",
            };
            let _ = writeln!(
                out,
                "  remote={} link={link} queued={} in_flight={} next_sequence={} acked={:?} unacked={} deferred={}",
                remote.slot,
                remote.outbound.len(),
                remote.in_flight,
                remote.next_sequence,
                remote.acked,
                remote.pending_acks.len(),
                remote.deferred,
            );
        }
        let _ = write!(out, "  {:?}", self.stats);
        out
    }

    fn poll_writer(&mut self) -> Result<()> {
        if !self.writer.busy {
            return Ok(());
        }
        let done = match self.writer.done.try_recv() {
            Ok(done) => done,
            Err(mpsc::TryRecvError::Empty) => return Ok(()),
            Err(mpsc::TryRecvError::Disconnected) => {
                self.journal.poison();
                return Err(MeshError::Journal(RecoveryError::Poisoned));
            }
        };
        self.writer.busy = false;
        let receipt = match done.result {
            Ok(receipt) => receipt,
            Err(error) => {
                self.journal.poison();
                return Err(error.into());
            }
        };
        let records = receipt.records - self.journal.durable_receipt().records;
        self.journal.mark_durable(receipt)?;
        let stats = &mut self.stats;
        let journal = done.journal.as_micros() as u64;
        let receipts = done.receipts.as_micros() as u64;
        stats.journal_syncs += 1;
        stats.journal_sync_micros += journal;
        stats.journal_sync_max_micros = stats.journal_sync_max_micros.max(journal);
        stats.receipt_syncs += 1;
        stats.receipt_sync_micros += receipts;
        stats.receipt_sync_max_micros = stats.receipt_sync_max_micros.max(receipts);
        stats.records_synced += u64::from(records);
        stats.bytes_synced += done.bytes as u64;
        Ok(())
    }

    fn start_write(&mut self) -> Result<()> {
        if self.writer.busy
            || self
                .last_write
                .is_some_and(|last| last.elapsed() < SYNC_INTERVAL)
        {
            return Ok(());
        }
        let Some(staged) = self.journal.take_staged() else {
            return Ok(());
        };
        self.writer.submit(staged)?;
        self.last_write = Some(Instant::now());
        Ok(())
    }

    fn next_timer(&self, now: Instant) -> Option<Instant> {
        let mut next: Option<Instant> = None;
        let mut consider = |at: Instant| next = Some(next.map_or(at, |next| next.min(at)));
        for remote in &self.remotes {
            match &remote.link {
                Link::Offering { sent, .. } => consider(sent.map_or(now, |at| at + OFFER_RETRY)),
                Link::Up { .. } => {
                    for (position, entry) in
                        remote.outbound.iter().take(remote.in_flight).enumerate()
                    {
                        if entry.received && position > 0 {
                            continue;
                        }
                        let Some(at) = entry.sent_at else {
                            continue;
                        };
                        let gap = !entry.gap_resent
                            && remote.highest_held.is_some_and(|h| entry.sequence < h);
                        consider(
                            at + match (entry.received, gap) {
                                (true, _) => DURABLE_PROBE_AFTER,
                                (false, true) => GAP_RESEND_AFTER,
                                (false, false) => remote.rto,
                            },
                        );
                    }
                }
                _ => {}
            }
        }
        if !self.writer.busy
            && self.journal.receipt().records > self.journal.durable_receipt().records
        {
            consider(self.last_write.map_or(now, |last| last + SYNC_INTERVAL));
        }
        if let Some((at, _, _)) = self.net.held.front() {
            consider(*at);
        }
        next
    }

    fn drain(&mut self, wait: Option<Duration>) -> Result<()> {
        let mut wait = wait;
        for _ in 0..MAX_DRAIN {
            let Some((count, source)) = self.net.recv(wait.take(), &mut self.buffer)? else {
                break;
            };
            self.stats.datagrams_received += 1;
            self.stats.bytes_received += count as u64;
            self.last_datagram = Instant::now();
            if count > MAX_DATAGRAM_BYTES {
                self.stats.rejected += 1;
                continue;
            }
            let datagram = self.buffer[..count].to_vec();
            self.handle_datagram(&datagram, source)?;
        }
        self.stage_reveal_group()
    }

    fn handle_datagram(&mut self, bytes: &[u8], source: SocketAddr) -> Result<()> {
        let Some(index) = self
            .remotes
            .iter()
            .position(|remote| remote.address == source)
        else {
            self.stats.rejected += 1;
            return Ok(());
        };
        if bytes.starts_with(ACK_MAGIC) {
            self.handle_ack(index, bytes);
            Ok(())
        } else if let Some((kind, initiator, responder)) = handshake::packet_header(bytes) {
            self.handle_handshake(index, kind, initiator, responder, bytes)
        } else {
            self.handle_fragment(index, bytes)
        }
    }

    fn handle_ack(&mut self, index: usize, bytes: &[u8]) {
        let remote = &mut self.remotes[index];
        let Link::Up { sender, .. } = &remote.link else {
            self.stats.rejected += 1;
            return;
        };
        if bytes.len() != ACK_PACKET_BYTES
            || bytes[ACK_MAGIC.len()..ACK_MAGIC.len() + 2] != ACK_VERSION.to_le_bytes()
            || bytes[ACK_MAGIC.len() + 2] as usize != self.local
            || sender
                .verify_ack_tag(&bytes[..ACK_HEADER_BYTES], &bytes[ACK_HEADER_BYTES..])
                .is_err()
        {
            self.stats.rejected += 1;
            return;
        }
        let field = |offset: usize| {
            let at = ACK_MAGIC.len() + 3 + offset * 8;
            u64::from_le_bytes(bytes[at..at + 8].try_into().expect("fixed ACK field"))
        };
        let (durable, received, held) = (field(0), field(1), field(2));
        if durable > received || received > remote.next_sequence {
            self.stats.rejected += 1;
            return;
        }
        self.stats.acks_received += 1;
        let mut progress = false;
        while remote.in_flight > 0
            && remote
                .outbound
                .front()
                .is_some_and(|entry| entry.sequence < durable)
        {
            remote.outbound.pop_front();
            remote.in_flight -= 1;
            progress = true;
        }
        // Frames below the received floor were accepted in order and stay
        // received. The bitmap is only the receiver's current view: it counts
        // a frame of which one fragment arrived, and it drops a held frame
        // that could not be opened yet, so a frame it stops reporting is
        // resent again. An ACK older than the newest floor tells nothing new
        // about later frames.
        let current = received >= remote.reported_floor;
        remote.reported_floor = remote.reported_floor.max(received);
        for entry in remote.outbound.iter_mut().take(remote.in_flight) {
            let holds = if entry.sequence < remote.reported_floor {
                true
            } else if current {
                entry
                    .sequence
                    .checked_sub(received + 1)
                    .is_some_and(|bit| bit < REORDER_WINDOW && held >> bit & 1 == 1)
            } else {
                entry.received
            };
            progress |= holds && !entry.received;
            entry.received = holds;
        }
        if held != 0 {
            let highest = received + REORDER_WINDOW - u64::from(held.leading_zeros());
            remote.highest_held = Some(remote.highest_held.map_or(highest, |h| h.max(highest)));
        }
        if progress {
            remote.rto = RETRANSMIT_INITIAL;
        }
    }

    fn handle_handshake(
        &mut self,
        index: usize,
        kind: HandshakeKind,
        initiator: usize,
        responder: usize,
        bytes: &[u8],
    ) -> Result<()> {
        let slot = self.remotes[index].slot;
        match kind {
            HandshakeKind::Offer => {
                if initiator != slot || responder != self.local {
                    self.stats.rejected += 1;
                    return Ok(());
                }
                match &mut self.remotes[index].link {
                    // The initiator lost the answer; send the same bytes.
                    Link::Up {
                        answered: Some(answered),
                        ..
                    } if answered.offer[..] == *bytes => {
                        answered.unsent = true;
                        return Ok(());
                    }
                    // Crossed offers: the lower slot's offer wins.
                    Link::Offering { .. } if self.local < slot => return Ok(()),
                    _ => {}
                }
                let (keys, response, receipt) = match self.journal.accept_handshake_offer(
                    slot,
                    self.local,
                    &self.identity,
                    bytes,
                ) {
                    Ok(accepted) => accepted,
                    Err(RecoveryError::Evidence(_)) => {
                        self.stats.rejected += 1;
                        return Ok(());
                    }
                    Err(error) => return Err(error.into()),
                };
                let answered = Answered {
                    offer: bytes.try_into().expect("accepted offer length"),
                    response,
                    requires: receipt.records,
                    unsent: true,
                };
                self.install(index, keys, Some(Box::new(answered)))
            }
            HandshakeKind::Response => {
                if initiator != self.local || responder != slot {
                    self.stats.rejected += 1;
                    return Ok(());
                }
                let link = &mut self.remotes[index].link;
                let Link::Offering { initiator, .. } = link else {
                    // A duplicate of an answer this peer already used.
                    self.stats.duplicates += 1;
                    return Ok(());
                };
                if initiator.check(bytes).is_err() {
                    self.stats.rejected += 1;
                    return Ok(());
                }
                let Link::Offering { initiator, .. } = std::mem::replace(link, Link::Waiting)
                else {
                    unreachable!("checked offering link");
                };
                let keys = initiator.finish(bytes)?;
                self.install(index, keys, None)
            }
        }
    }

    /// Replace the channel to one remote with fresh keys. Unacknowledged
    /// frames are sealed again on the new channel; after a replacement or a
    /// restart the retained state is queued ahead of them.
    fn install(
        &mut self,
        index: usize,
        keys: PairwiseKeys,
        answered: Option<Box<Answered>>,
    ) -> Result<()> {
        let context = self.session().evidence().context.clone();
        let slot = self.remotes[index].slot;
        let sender = EncryptedSender::new(
            context.clone(),
            self.local,
            keys.channel_binding,
            keys.send_key,
            None,
        )?;
        let receiver =
            EncryptedReceiver::new(context, slot, keys.channel_binding, keys.receive_key, None)?;
        let replaced = matches!(self.remotes[index].link, Link::Up { .. });
        let resend = replaced || self.remotes[index].resend;
        let retained = if resend {
            self.retained_messages()?
        } else {
            Vec::new()
        };
        let requires = self.journal.receipt().records;
        let remote = &mut self.remotes[index];
        remote.link = Link::Up {
            sender: Box::new(sender),
            receiver: Box::new(receiver),
            answered,
        };
        remote.reset_channel();
        remote.resend = false;
        // Retained state goes first: the certificates it starts with let the
        // remote verify the openings queued behind them.
        let unacknowledged = std::mem::take(&mut remote.outbound);
        if retained.len() + unacknowledged.len() > MAX_OUTBOUND {
            return Err(Error::InvalidEvidence("outbound queue is full").into());
        }
        remote.outbound = retained
            .into_iter()
            .map(|message| Outbound::new(message, requires))
            .chain(unacknowledged)
            .collect();
        self.stats.handshakes += 1;
        self.stats.replaced_channels += u64::from(replaced);
        Ok(())
    }

    /// Everything a peer that restarted may have acknowledged without making
    /// durable, or never received: pending certificates, this peer's recent
    /// openings, uncertified commitments and endorsements, and its latest
    /// checkpoint signatures. Receivers ignore what they already hold.
    fn retained_messages(&self) -> Result<Vec<WireMessage>> {
        let evidence = self.session().evidence();
        let mut messages = Vec::new();
        for frontier in &evidence.pending {
            messages.push(WireMessage::CommitmentCertificate {
                set: frontier.set.clone(),
                signatures: frontier.signatures.clone(),
            });
        }
        // A remote closes a frontier only after this peer certified it, so
        // its closed tick trails at most one full pipeline behind.
        let closed = evidence.batches.len();
        for index in closed.saturating_sub(MAX_OUTSTANDING_FRONTIERS)..closed {
            let batch = evidence.batches.get(index).expect("closed batch");
            if let Some(opening) = &batch.openings[self.local] {
                messages.push(WireMessage::Reveal {
                    set: batch.set.clone(),
                    reveal: opening.clone(),
                });
            }
        }
        for frontier in &evidence.pending {
            if let Some(opening) = &frontier.openings[self.local] {
                messages.push(WireMessage::Reveal {
                    set: frontier.set.clone(),
                    reveal: opening.clone(),
                });
            }
        }
        for opening in self
            .journal
            .sealed_openings()
            .filter(|opening| opening.start_tick >= evidence.certified_tick)
        {
            messages.push(WireMessage::Commitment {
                epoch: evidence.epoch,
                start_tick: opening.start_tick,
                commitment: opening.commitment(&evidence.context, evidence.epoch)?,
            });
        }
        for (set, signature) in self.endorsed.values() {
            messages.push(WireMessage::SetSignature {
                set: set.clone(),
                signature: signature.clone(),
            });
        }
        for (checkpoint, signature) in &self.own_votes {
            messages.push(WireMessage::CheckpointSignature {
                checkpoint: checkpoint.clone(),
                signature: signature.clone(),
            });
        }
        Ok(messages)
    }

    /// Open fragments strictly in sequence order. A fragment of a later
    /// frame is held until every earlier frame has been accepted.
    fn handle_fragment(&mut self, index: usize, bytes: &[u8]) -> Result<()> {
        let remote = &mut self.remotes[index];
        let Link::Up { receiver, .. } = &remote.link else {
            self.stats.rejected += 1;
            return Ok(());
        };
        let Ok(sequence) = receiver.fragment_sequence(bytes) else {
            self.stats.rejected += 1;
            return Ok(());
        };
        let expected = receiver.sequence_floor().map_or(0, |floor| floor + 1);
        if sequence < expected {
            // A retransmission of an accepted frame: its ACK was lost.
            self.stats.duplicates += 1;
            remote.ack_due = true;
            return Ok(());
        }
        if sequence > expected {
            self.stats.out_of_order += 1;
            remote.ack_due = true;
            if sequence - expected <= REORDER_WINDOW {
                let fragments = remote.held.entry(sequence).or_default();
                if fragments.len() < MAX_HELD_FRAGMENTS
                    && !fragments.iter().any(|held| held == bytes)
                {
                    fragments.push(bytes.to_vec());
                }
            }
            return Ok(());
        }
        self.open_in_order(index, bytes)?;
        // Frames held behind the gap follow as far as they are complete.
        loop {
            let remote = &mut self.remotes[index];
            let Link::Up { receiver, .. } = &remote.link else {
                return Ok(());
            };
            let floor = receiver.sequence_floor();
            let expected = floor.map_or(0, |floor| floor + 1);
            remote.held.retain(|sequence, _| *sequence >= expected);
            let Some(fragments) = remote.held.remove(&expected) else {
                return Ok(());
            };
            for fragment in fragments {
                self.open_in_order(index, &fragment)?;
            }
            let Link::Up { receiver, .. } = &self.remotes[index].link else {
                return Ok(());
            };
            if receiver.sequence_floor() == floor {
                return Ok(());
            }
        }
    }

    fn open_in_order(&mut self, index: usize, bytes: &[u8]) -> Result<()> {
        let slot = self.remotes[index].slot;
        let frame = {
            let evidence = self.journal.session().evidence();
            let remote = &mut self.remotes[index];
            let Link::Up { receiver, .. } = &mut remote.link else {
                return Ok(());
            };
            let frontiers = KnownFrontiers {
                log: evidence,
                assembler: &self.assembler,
                assembled: OnceCell::new(),
            };
            let accept_new =
                remote.deferred < MAX_DEFERRED_PER_PEER && self.early.len() < MAX_EARLY_OPENINGS;
            match receiver.open_fragment_or_replay_with_capacity(bytes, &frontiers, accept_new) {
                Ok(FragmentDelivery::Frame(frame)) => frame,
                Ok(FragmentDelivery::Pending) => return Ok(()),
                Ok(FragmentDelivery::AcceptedReplay(_)) => {
                    self.stats.duplicates += 1;
                    remote.ack_due = true;
                    return Ok(());
                }
                Ok(FragmentDelivery::AtCapacity) => {
                    self.stats.backpressured += 1;
                    return Ok(());
                }
                Err(_) => {
                    self.stats.unready += 1;
                    return Ok(());
                }
            }
        };
        self.stats.frames_received += 1;
        let gate = match self.apply(slot, frame.message)? {
            Applied::Done(gate) => gate,
            Applied::Deferred(message) => {
                self.defer(index, slot, message);
                AckGate::Ready
            }
        };
        self.remotes[index]
            .pending_acks
            .push_back((frame.sequence, gate));
        Ok(())
    }

    fn defer(&mut self, index: usize, slot: usize, message: WireMessage) {
        self.deferred.push_back((slot, message));
        self.remotes[index].deferred += 1;
        self.stats.deferred += 1;
    }

    fn index(&self, slot: usize) -> usize {
        if slot < self.local { slot } else { slot - 1 }
    }

    /// Apply one authenticated message from `slot`, or hand it back when this
    /// peer is not far enough along to use it yet.
    fn apply(&mut self, slot: usize, message: WireMessage) -> Result<Applied> {
        let evidence = self.journal.session().evidence();
        let finished = evidence.phase == Phase::Terminal;
        let horizon = self.assembler.next_tick() + ASSEMBLY_TICKS;
        match message {
            WireMessage::Commitment {
                epoch,
                start_tick,
                commitment,
            } => {
                if start_tick >= horizon {
                    return Ok(Applied::Deferred(WireMessage::Commitment {
                        epoch,
                        start_tick,
                        commitment,
                    }));
                }
                self.assembler
                    .add_commitment(slot, epoch, start_tick, commitment)
                    .map_err(blame(slot))?;
                Ok(Applied::Done(AckGate::Ready))
            }
            WireMessage::SetSignature { set, signature } => {
                if set.start_tick >= horizon {
                    return Ok(Applied::Deferred(WireMessage::SetSignature {
                        set,
                        signature,
                    }));
                }
                self.assembler
                    .add_endorsement(&set, signature)
                    .map_err(blame(slot))?;
                Ok(Applied::Done(AckGate::Ready))
            }
            WireMessage::CommitmentCertificate { set, signatures } => {
                self.relayed_certificate(slot, set, signatures)
            }
            WireMessage::Reveal { reveal, .. } => {
                if finished {
                    return Ok(Applied::Done(AckGate::Ready));
                }
                if evidence.certified_frontier(reveal.start_tick).is_some() {
                    if evidence.retains(&reveal) || self.reveal_group.contains(&reveal) {
                        return Ok(Applied::Done(AckGate::Ready));
                    }
                    self.reveal_group.push(reveal);
                    return Ok(Applied::Done(AckGate::Group));
                }
                // Checked against the set this peer assembled; the sender
                // cannot close that frontier before this peer certifies it,
                // so it resends the opening if this process is lost first.
                match self.early.get(&(reveal.start_tick, reveal.slot)) {
                    Some(existing) if *existing == reveal => {}
                    Some(_) => {
                        return Err(MeshError::Peer {
                            slot,
                            error: Error::InvalidEvidence("conflicting early opening"),
                        });
                    }
                    None => {
                        self.early.insert((reveal.start_tick, reveal.slot), reveal);
                        self.stats.early_openings += 1;
                    }
                }
                Ok(Applied::Done(AckGate::Ready))
            }
            WireMessage::CheckpointSignature {
                checkpoint,
                signature,
            } => self.vote(slot, checkpoint, signature),
            WireMessage::Checkpoint {
                checkpoint,
                signatures,
            } => self.shared_checkpoint(checkpoint, signatures),
        }
    }

    fn relayed_certificate(
        &mut self,
        slot: usize,
        set: CommitmentSet,
        signatures: Vec<SlotSignature>,
    ) -> Result<Applied> {
        let session = self.journal.session();
        let evidence = session.evidence();
        if evidence.phase == Phase::Terminal || session.confirmed().terminal {
            return Ok(Applied::Done(AckGate::Ready));
        }
        if set.start_tick < evidence.certified_tick {
            if evidence.certified_frontier(set.start_tick) == Some(&set) {
                return Ok(Applied::Done(AckGate::Ready));
            }
            return Err(MeshError::Peer {
                slot,
                error: Error::InvalidEvidence("certificate conflicts with a certified frontier"),
            });
        }
        if set.start_tick > evidence.certified_tick
            || evidence.pending.len() >= MAX_OUTSTANDING_FRONTIERS
        {
            return Ok(Applied::Deferred(WireMessage::CommitmentCertificate {
                set,
                signatures,
            }));
        }
        let receipt = self
            .journal
            .certify(set.clone(), signatures.clone())
            .map_err(blame_journal(slot))?;
        self.assembler.sync(self.journal.session().evidence());
        self.endorsed
            .retain(|tick, _| *tick >= certified_tick(&self.journal));
        self.stats.relayed_certificates += 1;
        // This peer never re-endorses a frontier it certified this way. If it
        // lost that endorsement in a crash before it reached every peer, the
        // certificate is what lets them catch up.
        let message = WireMessage::CommitmentCertificate { set, signatures };
        for remote in &mut self.remotes {
            if remote.slot == slot {
                continue;
            }
            if remote.outbound.len() >= MAX_OUTBOUND {
                return Err(Error::InvalidEvidence("outbound queue is full").into());
            }
            remote
                .outbound
                .push_back(Outbound::new(message.clone(), receipt.records));
        }
        Ok(Applied::Done(AckGate::Durable(receipt.records)))
    }

    fn vote(
        &mut self,
        slot: usize,
        checkpoint: Checkpoint,
        signature: SlotSignature,
    ) -> Result<Applied> {
        let retained = self
            .session()
            .last_checkpoint()
            .map_or(0, |checkpoint| checkpoint.checkpoint.tick);
        if checkpoint.tick <= retained {
            return Ok(Applied::Done(AckGate::Ready));
        }
        if !self.votes.contains_key(&checkpoint.tick) && self.votes.len() >= MAX_CHECKPOINT_VOTES {
            return Ok(Applied::Deferred(WireMessage::CheckpointSignature {
                checkpoint,
                signature,
            }));
        }
        let count = self.session().evidence().context.roster.len();
        let votes = self
            .votes
            .entry(checkpoint.tick)
            .or_insert_with(|| vec![None; count]);
        match &votes[slot] {
            None => votes[slot] = Some((checkpoint, signature)),
            Some((existing, _)) if *existing == checkpoint => {}
            Some(_) => {
                return Err(MeshError::Peer {
                    slot,
                    error: Error::InvalidEvidence("conflicting checkpoint signature"),
                });
            }
        }
        Ok(Applied::Done(AckGate::Ready))
    }

    /// Retain a complete checkpoint that a peer shared when it stopped
    /// combat, if it is later than this peer's own and at a boundary this
    /// peer confirmed. Every roster key signed it, this peer's included.
    fn shared_checkpoint(
        &mut self,
        checkpoint: Checkpoint,
        signatures: Vec<SlotSignature>,
    ) -> Result<Applied> {
        let session = self.session();
        let retained = session
            .last_checkpoint()
            .map_or(0, |checkpoint| checkpoint.checkpoint.tick);
        if checkpoint.tick <= retained {
            return Ok(Applied::Done(AckGate::Ready));
        }
        if checkpoint.tick > session.confirmed().tick {
            return Ok(Applied::Deferred(WireMessage::Checkpoint {
                checkpoint,
                signatures,
            }));
        }
        let tick = checkpoint.tick;
        match self.journal.checkpoint(checkpoint, signatures) {
            Ok(receipt) => {
                self.stats.checkpoints_retained += 1;
                self.votes.retain(|later, _| *later > tick);
                Ok(Applied::Done(AckGate::Durable(receipt.records)))
            }
            // Already outside this peer's boundary window.
            Err(RecoveryError::Evidence(_)) => {
                self.stats.checkpoints_missed += 1;
                Ok(Applied::Done(AckGate::Ready))
            }
            Err(error) => Err(error.into()),
        }
    }

    fn stage_reveal_group(&mut self) -> Result<()> {
        if self.reveal_group.is_empty() {
            return Ok(());
        }
        let group = std::mem::take(&mut self.reveal_group);
        let mut records = self.journal.receipt().records;
        for chunk in group.chunks(MAX_REVEAL_GROUP) {
            records = self.journal.reveal_many(chunk.to_vec())?.records;
        }
        for remote in &mut self.remotes {
            for (_, gate) in &mut remote.pending_acks {
                if *gate == AckGate::Group {
                    *gate = AckGate::Durable(records);
                }
            }
        }
        Ok(())
    }

    fn broadcast(&mut self, message: WireMessage, requires: u32) -> Result<()> {
        if self
            .remotes
            .iter()
            .any(|remote| remote.outbound.len() >= MAX_OUTBOUND)
        {
            return Err(Error::InvalidEvidence("outbound queue is full").into());
        }
        for remote in &mut self.remotes {
            remote
                .outbound
                .push_back(Outbound::new(message.clone(), requires));
        }
        Ok(())
    }

    /// Endorse, certify, open, sign and retain until nothing changes.
    fn progress(&mut self) -> Result<()> {
        loop {
            let mut changed = self.retry_deferred()?;
            changed |= self.endorse_assembled()?;
            changed |= self.certify_assembled()?;
            changed |= self.reveal_own()?;
            changed |= self.sign_checkpoints()?;
            changed |= self.retain_checkpoints()?;
            self.finish_when_complete()?;
            if !changed {
                return Ok(());
            }
        }
    }

    fn retry_deferred(&mut self) -> Result<bool> {
        let mut changed = false;
        for _ in 0..self.deferred.len() {
            let (slot, message) = self.deferred.pop_front().expect("counted deferred message");
            let index = self.index(slot);
            self.remotes[index].deferred -= 1;
            match self.apply(slot, message)? {
                Applied::Deferred(message) => {
                    self.deferred.push_back((slot, message));
                    self.remotes[index].deferred += 1;
                }
                Applied::Done(_) => changed = true,
            }
        }
        Ok(changed)
    }

    fn endorse_assembled(&mut self) -> Result<bool> {
        let session = self.session();
        if session.evidence().phase != Phase::Live || session.confirmed().terminal {
            return Ok(false);
        }
        let sets = self.assembler.unendorsed(self.local);
        let changed = !sets.is_empty();
        for set in sets {
            let (signature, receipt) = self.journal.endorse(&set, self.local, &self.identity)?;
            self.assembler.add_endorsement(&set, signature.clone())?;
            self.endorsed
                .insert(set.start_tick, (set.clone(), signature.clone()));
            self.broadcast(
                WireMessage::SetSignature { set, signature },
                receipt.records,
            )?;
        }
        Ok(changed)
    }

    fn certify_assembled(&mut self) -> Result<bool> {
        let mut changed = false;
        loop {
            let session = self.session();
            if session.confirmed().terminal
                || session.evidence().phase == Phase::Terminal
                || session.evidence().pending.len() >= MAX_OUTSTANDING_FRONTIERS
            {
                break;
            }
            let Some((set, signatures)) = self.assembler.take_certified() else {
                break;
            };
            self.journal.certify(set, signatures)?;
            let certified = certified_tick(&self.journal);
            self.endorsed.retain(|tick, _| *tick >= certified);
            changed = true;
        }
        Ok(changed)
    }

    /// Open this peer's commitment in every certified frontier that lacks it,
    /// together with remote openings that arrived before certification.
    fn reveal_own(&mut self) -> Result<bool> {
        let evidence = self.journal.session().evidence();
        if evidence.phase == Phase::Terminal {
            return Ok(false);
        }
        let mut own = Vec::new();
        let mut group = Vec::new();
        for frontier in &evidence.pending {
            let tick = frontier.set.start_tick;
            for (slot, opening) in frontier.openings.iter().enumerate() {
                if opening.is_some() {
                    continue;
                }
                if slot == self.local {
                    if self.withhold_from.is_some_and(|from| tick >= from) {
                        continue;
                    }
                    if let Some(sealed) = self
                        .journal
                        .sealed_openings()
                        .find(|sealed| sealed.start_tick == tick && sealed.slot == slot)
                    {
                        own.push((frontier.set.clone(), sealed.clone()));
                        group.push(sealed.clone());
                    }
                } else if let Some(early) = self.early.remove(&(tick, slot))
                    && early.verify(&evidence.context, &frontier.set).is_ok()
                {
                    group.push(early);
                }
            }
        }
        let certified = evidence.certified_tick;
        self.early.retain(|(tick, _), _| *tick >= certified);
        if group.is_empty() {
            return Ok(false);
        }
        let mut records = self.journal.receipt().records;
        for chunk in group.chunks(MAX_REVEAL_GROUP) {
            records = self.journal.reveal_many(chunk.to_vec())?.records;
        }
        for (set, reveal) in own {
            self.broadcast(WireMessage::Reveal { set, reveal }, records)?;
        }
        Ok(true)
    }

    fn sign_checkpoints(&mut self) -> Result<bool> {
        let session = self.journal.session();
        let confirmed = session.confirmed();
        let mut ticks = Vec::new();
        let mut tick =
            (self.signed_through / CHECKPOINT_INTERVAL_TICKS + 1) * CHECKPOINT_INTERVAL_TICKS;
        while tick <= confirmed.tick {
            ticks.push(tick);
            tick += CHECKPOINT_INTERVAL_TICKS;
        }
        if confirmed.terminal
            && confirmed.tick > self.signed_through
            && ticks.last() != Some(&confirmed.tick)
        {
            ticks.push(confirmed.tick);
        }
        if ticks.is_empty() {
            return Ok(false);
        }
        let context = &session.evidence().context;
        let mut signed = Vec::new();
        for tick in ticks {
            // A boundary already outside the window can no longer be retained.
            if let Some(checkpoint) = session.boundary(tick) {
                let signature = checkpoint.sign(context, self.local, &self.identity)?;
                signed.push((checkpoint.clone(), signature));
            }
        }
        self.signed_through = confirmed.tick;
        let count = context.roster.len();
        let records = self.journal.receipt().records;
        for (checkpoint, signature) in signed {
            self.votes
                .entry(checkpoint.tick)
                .or_insert_with(|| vec![None; count])[self.local] =
                Some((checkpoint.clone(), signature.clone()));
            self.own_votes
                .push_back((checkpoint.clone(), signature.clone()));
            if self.own_votes.len() > OWN_VOTES_KEPT {
                self.own_votes.pop_front();
            }
            self.broadcast(
                WireMessage::CheckpointSignature {
                    checkpoint,
                    signature,
                },
                records,
            )?;
        }
        Ok(true)
    }

    /// Retain each checkpoint that every roster key signed exactly as this
    /// peer confirmed it. A different signed checkpoint is a divergence.
    fn retain_checkpoints(&mut self) -> Result<bool> {
        let mut changed = false;
        let ticks = self.votes.keys().copied().collect::<Vec<_>>();
        for tick in ticks {
            let Some(votes) = self.votes.get(&tick) else {
                continue;
            };
            let Some((own, _)) = votes[self.local].clone() else {
                continue;
            };
            for (slot, vote) in votes.iter().enumerate() {
                if let Some((checkpoint, _)) = vote
                    && *checkpoint != own
                {
                    return Err(MeshError::Peer {
                        slot,
                        error: Error::InvalidEvidence("checkpoint differs from the local boundary"),
                    });
                }
            }
            let Some(signatures) = votes
                .iter()
                .map(|vote| vote.as_ref().map(|(_, signature)| signature.clone()))
                .collect::<Option<Vec<_>>>()
            else {
                continue;
            };
            match self.journal.checkpoint(own, signatures) {
                Ok(_) => self.stats.checkpoints_retained += 1,
                Err(RecoveryError::Evidence(_)) => self.stats.checkpoints_missed += 1,
                Err(error) => return Err(error.into()),
            }
            self.votes.retain(|later, _| *later > tick);
            changed = true;
        }
        Ok(changed)
    }

    fn finish_when_complete(&mut self) -> Result<()> {
        if self.finish_records.is_some() || self.final_checkpoint().is_none() {
            return Ok(());
        }
        self.finish_records = Some(self.journal.finish()?.records);
        Ok(())
    }

    fn transmit(&mut self) -> Result<()> {
        let now = Instant::now();
        let durable = self.journal.durable_receipt().records;
        for remote in &mut self.remotes {
            let address = remote.address;
            match &mut remote.link {
                Link::Waiting => {}
                Link::Offering {
                    initiator,
                    offer,
                    sent,
                    attempts,
                } => {
                    if sent.is_some_and(|at| now.duration_since(at) < OFFER_RETRY) {
                        continue;
                    }
                    if *attempts >= OFFER_ATTEMPTS {
                        let context = self.journal.session().evidence().context.clone();
                        let (fresh, bytes) =
                            Initiator::start(context, self.local, remote.slot, &self.identity)?;
                        **initiator = fresh;
                        *offer = bytes;
                        *attempts = 0;
                    }
                    self.net.send(address, &offer[..], &mut self.stats);
                    *sent = Some(now);
                    *attempts += 1;
                    self.stats.offers_sent += 1;
                }
                Link::Up {
                    sender,
                    receiver,
                    answered,
                } => {
                    if let Some(answer) = answered
                        && answer.unsent
                    {
                        if answer.requires > durable {
                            // The initiator cannot open frames before it has
                            // the answer, so they wait for it.
                            continue;
                        }
                        self.net.send(address, &answer.response, &mut self.stats);
                        answer.unsent = false;
                    }
                    while remote.in_flight < SEND_WINDOW.min(remote.outbound.len()) {
                        let entry = &mut remote.outbound[remote.in_flight];
                        if entry.requires > durable {
                            break;
                        }
                        let frame = WireFrame {
                            sender: self.local,
                            sequence: remote.next_sequence,
                            message: entry.message.clone(),
                        };
                        let fragments = sender.seal_fragments(&frame, &self.identity)?;
                        for fragment in &fragments {
                            self.net.send(address, fragment, &mut self.stats);
                        }
                        entry.sealed = Some(fragments);
                        entry.sequence = remote.next_sequence;
                        entry.sent_at = Some(now);
                        remote.next_sequence += 1;
                        remote.in_flight += 1;
                        self.stats.frames_sent += 1;
                    }
                    // Resend what the receiver does not hold: a reported gap
                    // once after a short delay, anything after the timeout.
                    // The oldest held frame is resent after a longer probe
                    // delay: its duplicate makes the receiver repeat an ACK
                    // of durability that may have been lost.
                    let (rto, highest_held) = (remote.rto, remote.highest_held);
                    let mut timed_out = false;
                    for (position, entry) in remote
                        .outbound
                        .iter_mut()
                        .take(remote.in_flight)
                        .enumerate()
                    {
                        let since = entry
                            .sent_at
                            .map_or(Duration::MAX, |at| now.duration_since(at));
                        if entry.received {
                            if position == 0 && since >= DURABLE_PROBE_AFTER {
                                for fragment in entry.sealed.as_deref().expect("sealed in flight") {
                                    self.net.send(address, fragment, &mut self.stats);
                                }
                                entry.sent_at = Some(now);
                                self.stats.probes += 1;
                            }
                            continue;
                        }
                        let gap = !entry.gap_resent
                            && highest_held.is_some_and(|highest| entry.sequence < highest)
                            && since >= GAP_RESEND_AFTER;
                        if since < rto && !gap {
                            continue;
                        }
                        for fragment in entry.sealed.as_deref().expect("sealed in flight") {
                            self.net.send(address, fragment, &mut self.stats);
                            self.stats.retransmitted += 1;
                        }
                        entry.sent_at = Some(now);
                        if since >= rto {
                            timed_out = true;
                            entry.gap_resent = false;
                        } else {
                            entry.gap_resent = true;
                            self.stats.fast_retransmits += 1;
                        }
                    }
                    if timed_out {
                        remote.rto = (remote.rto * 2).min(RETRANSMIT_MAX);
                        self.stats.timeouts += 1;
                    }
                    while let Some(&(sequence, gate)) = remote.pending_acks.front() {
                        let ready = match gate {
                            AckGate::Ready => true,
                            AckGate::Durable(records) => records <= durable,
                            AckGate::Group => false,
                        };
                        if !ready {
                            break;
                        }
                        remote.pending_acks.pop_front();
                        remote.acked = Some(sequence);
                    }
                    let durable_next = remote.acked.map_or(0, |sequence| sequence + 1);
                    let received_next = receiver.sequence_floor().map_or(0, |floor| floor + 1);
                    let held = remote
                        .held
                        .range(received_next + 1..=received_next + REORDER_WINDOW)
                        .fold(0u64, |bits, (sequence, _)| {
                            bits | 1 << (sequence - received_next - 1)
                        });
                    let state = (durable_next, received_next, held);
                    if (remote.ack_due || remote.last_ack != Some(state))
                        && (received_next > 0 || held != 0)
                    {
                        let mut ack = [0; ACK_PACKET_BYTES];
                        ack[..ACK_MAGIC.len()].copy_from_slice(ACK_MAGIC);
                        ack[ACK_MAGIC.len()..ACK_MAGIC.len() + 2]
                            .copy_from_slice(&ACK_VERSION.to_le_bytes());
                        ack[ACK_MAGIC.len() + 2] = remote.slot as u8;
                        for (offset, value) in
                            [durable_next, received_next, held].into_iter().enumerate()
                        {
                            let at = ACK_MAGIC.len() + 3 + offset * 8;
                            ack[at..at + 8].copy_from_slice(&value.to_le_bytes());
                        }
                        let tag = receiver.ack_tag(&ack[..ACK_HEADER_BYTES]);
                        ack[ACK_HEADER_BYTES..].copy_from_slice(&tag);
                        self.net.send(address, &ack, &mut self.stats);
                        self.stats.acks_sent += 1;
                        remote.last_ack = Some(state);
                    }
                    remote.ack_due = false;
                }
            }
        }
        self.net.release_held(now, &mut self.stats);
        Ok(())
    }
}

fn certified_tick(journal: &DurableSession) -> u32 {
    journal.session().evidence().certified_tick
}

/// Pacing and limits for `run_headless`.
#[derive(Debug, Clone, Copy)]
pub struct Pace {
    /// Presentation ticks per second, or `None` to present as fast as the
    /// pipeline allows.
    pub rate_hz: Option<u32>,
    /// When presentation tick 0 is due. Every peer of a match shares it, so
    /// a restarted peer knows how far behind schedule it is.
    pub start: Instant,
    /// Stop combat when live evidence made no progress for this long: a peer
    /// dropped out or withholds. The interrupt is journaled.
    pub stall_limit: Duration,
    /// Once combat stopped or ended, finish when the evidence made no
    /// progress for this long: with what it proves if no certified frontier
    /// awaits an opening, even without a final checkpoint that some peer
    /// never signed; otherwise give up with `MeshError::Unresolved`.
    pub resolve_limit: Duration,
    /// After finishing, keep answering until no datagram arrived for this
    /// long, so peers that lost an ACK still get one. Keep it above the
    /// largest retransmission timeout, 800 ms.
    pub linger: Duration,
}

/// What the harness watching `run_headless` asks after each step.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Watch {
    /// Count the limits as usual.
    Run,
    /// Count this step as progress: neither the stall nor the resolve limit
    /// passes while the harness holds, however slowly the evidence moves.
    Hold,
    /// Drop the peer like a crash.
    Stop,
}

/// How long a complete peer waits for its last acknowledgements.
const ACK_DRAIN_LIMIT: Duration = Duration::from_secs(10);

/// What the presentation clock saw in this process.
#[derive(Debug, Clone, Default)]
pub struct PresentationStats {
    pub presented: u32,
    /// Ticks presented more than one tick period after they were due.
    pub late_ticks: u32,
    pub max_late: Duration,
    /// Histogram of the confirmed-timeline lag, `predicted - confirmed` in
    /// ticks, sampled once per presented tick.
    pub lag: Vec<u64>,
}

impl PresentationStats {
    pub fn lag_samples(&self) -> u64 {
        self.lag.iter().sum()
    }
    pub fn lag_mean(&self) -> f64 {
        let samples = self.lag_samples();
        if samples == 0 {
            return 0.0;
        }
        self.lag
            .iter()
            .enumerate()
            .map(|(lag, count)| lag as f64 * *count as f64)
            .sum::<f64>()
            / samples as f64
    }
    /// Smallest lag at or below which `per_mille` of the samples fall.
    pub fn lag_quantile(&self, per_mille: u64) -> u32 {
        let target = (self.lag_samples() * per_mille).div_ceil(1000);
        let mut seen = 0;
        for (lag, count) in self.lag.iter().enumerate() {
            seen += count;
            if seen >= target && seen > 0 {
                return lag as u32;
            }
        }
        0
    }
    pub fn lag_max(&self) -> u32 {
        self.lag.iter().rposition(|count| *count > 0).unwrap_or(0) as u32
    }
}

/// The end of one headless peer process.
#[derive(Debug, Clone)]
pub struct HeadlessReport {
    pub outcome: crate::rollback::TerminalOutcome,
    /// The last certified checkpoint this peer retained: the final one, at
    /// `outcome.tick`, unless combat stopped early or a peer never signed
    /// the end.
    pub checkpoint: Option<CertifiedCheckpoint>,
    pub receipt: Receipt,
    pub mesh: MeshStats,
    pub presentation: PresentationStats,
    pub elapsed: Duration,
    /// Frames no peer acknowledged before this process left.
    pub unacknowledged: usize,
}

/// What counts as progress for the stall and resolve limits: the confirmed
/// and certified ticks and the openings held for pending frontiers.
fn progress_mark(peer: &MeshPeer) -> (u32, u32, usize) {
    let evidence = peer.session().evidence();
    let openings = evidence
        .pending
        .iter()
        .map(|frontier| frontier.openings.iter().flatten().count())
        .sum();
    (
        peer.session().confirmed().tick,
        evidence.certified_tick,
        openings,
    )
}

/// Present a scripted peer on the shared clock until its evidence is
/// finished and journaled, normally with the final certified checkpoint.
/// `control(tick)` is this slot's control for
/// combat tick `tick`; it commits each batch when its last control is
/// sampled, `INPUT_DELAY_TICKS` ahead, and predicts remote players with their
/// last confirmed controls. `watch` sees the peer after every step, whether
/// or not a tick was presented: it may hold the limits below, or stop the
/// peer, which drops it like a crash.
///
/// A dropout stops combat after `Pace::stall_limit` without progress. The
/// peer keeps exchanging evidence and, after `Pace::resolve_limit` without
/// progress, finishes with the outcome the evidence proves, or reports
/// `MeshError::Unresolved` while certified frontiers still lack openings.
pub fn run_headless(
    mut peer: MeshPeer,
    pace: Pace,
    control: impl Fn(u32) -> Input,
    mut watch: impl FnMut(&MeshPeer) -> Watch,
) -> Result<HeadlessReport> {
    let started = Instant::now();
    let max_ticks = peer.session().confirmed().config.max_ticks;
    let period = pace
        .rate_hz
        .filter(|rate| *rate > 0)
        .map(|rate| Duration::from_secs(1) / rate);
    let local = peer.local_slot();
    let mut presentation = PresentationStats {
        lag: vec![0; MAX_PREDICTION_TICKS + 1],
        ..PresentationStats::default()
    };
    let mut progress = progress_mark(&peer);
    // Nothing can progress before presentation starts.
    let mut progressed_at = Instant::now().max(pace.start);
    let mut completed_at = None;
    loop {
        let now = Instant::now();
        let mut blocked = false;
        loop {
            let session = peer.session();
            let presented = session.predicted().tick;
            if presented >= max_ticks || session.confirmed().terminal {
                break;
            }
            let due = period.map(|period| pace.start + period * presented);
            if due.is_some_and(|due| now < due) {
                break;
            }
            while peer.next_commit_tick() < max_ticks
                && commitment_due(peer.next_commit_tick()).is_none_or(|due| due <= presented)
            {
                if !peer.can_commit() {
                    blocked = true;
                    break;
                }
                let start = peer.next_commit_tick();
                peer.commit([control(start), control(start + 1)])?;
            }
            if blocked || !peer.can_predict() {
                blocked = true;
                break;
            }
            let mut controls = peer.last_confirmed_controls();
            controls[local] = control(presented);
            peer.predict(controls)?;
            let session = peer.session();
            let lag = (session.predicted().tick - session.confirmed().tick) as usize;
            presentation.lag[lag.min(MAX_PREDICTION_TICKS)] += 1;
            if let (Some(due), Some(period)) = (due, period) {
                let late = now.saturating_duration_since(due);
                if late > period {
                    presentation.late_ticks += 1;
                }
                presentation.max_late = presentation.max_late.max(late);
            }
            presentation.presented += 1;
        }

        let mark = progress_mark(&peer);
        if mark != progress {
            progress = mark;
            progressed_at = now;
        }
        match watch(&peer) {
            Watch::Run => {}
            Watch::Hold => progressed_at = progressed_at.max(now),
            Watch::Stop => {
                return Err(MeshError::Stopped {
                    confirmed: peer.session().confirmed().tick,
                });
            }
        }
        let quiet = now.duration_since(progressed_at);
        if peer.is_complete() {
            let since = *completed_at.get_or_insert(now);
            // Stay while peers still retransmit, so a lost ACK is answered
            // again. A peer that never acknowledges its last frames has
            // almost certainly finished and left; its count is reported.
            if (peer.is_finished() && peer.quiet_for() >= pace.linger)
                || now.duration_since(since) > pace.linger + ACK_DRAIN_LIMIT
            {
                break;
            }
        } else if peer.finish_records.is_none() {
            let session = peer.session();
            let (evidence, confirmed) = (session.evidence(), session.confirmed());
            if evidence.phase == Phase::Live && !confirmed.terminal {
                if quiet > pace.stall_limit {
                    // A peer dropped out or withholds: stop combat.
                    peer.interrupt()?;
                    progressed_at = now;
                }
            } else if quiet > pace.resolve_limit {
                if confirmed.terminal || evidence.pending.is_empty() {
                    peer.finish()?;
                } else {
                    return Err(MeshError::Unresolved {
                        confirmed: confirmed.tick,
                        pending: evidence.pending.len(),
                        detail: peer.describe(),
                    });
                }
            }
        }

        let presenting =
            peer.session().predicted().tick < max_ticks && !peer.session().confirmed().terminal;
        let wake = match period {
            _ if !presenting || blocked => now + Duration::from_millis(2),
            Some(period) => pace.start + period * peer.session().predicted().tick,
            None => now,
        };
        peer.pump(wake)?;
    }
    let session = peer.session();
    let outcome = session.terminal_outcome().ok_or(Error::InvalidEvidence(
        "match finished without terminal evidence",
    ))?;
    Ok(HeadlessReport {
        outcome,
        checkpoint: session.last_checkpoint().cloned(),
        receipt: peer.journal().durable_receipt(),
        mesh: peer.stats().clone(),
        presentation,
        elapsed: started.elapsed(),
        unacknowledged: peer.unacknowledged(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        protocol::Context,
        simulation::{Config, FIRE, Mode, Participant, World},
    };
    use std::{
        fs,
        net::Ipv4Addr,
        path::PathBuf,
        sync::atomic::{AtomicBool, AtomicU64, Ordering},
    };

    static NEXT_ROOT: AtomicU64 = AtomicU64::new(0);

    struct Fixture {
        root: PathBuf,
        context: Context,
        config: Config,
        participants: Vec<Participant>,
        keys: Vec<SigningKey>,
        addresses: Vec<SocketAddr>,
        /// Each slot's first socket, bound when the fixture is made so no
        /// other test can take its port; a restart binds the address again.
        sockets: std::cell::RefCell<Vec<Option<UdpSocket>>>,
    }

    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.root);
        }
    }

    fn control(tick: u32, slot: usize) -> Input {
        let slot = slot as u32;
        Input {
            buttons: if (tick + slot).is_multiple_of(3) {
                FIRE
            } else {
                0
            },
            move_x: if (tick / 20 + slot).is_multiple_of(2) {
                90
            } else {
                -90
            },
            move_y: 40 - 20 * slot as i16,
            yaw: ((tick * 97 + slot * 12_000) % 65_536) as u16,
            pitch: 0,
        }
    }

    fn fixture(players: usize, ticks: u32) -> Fixture {
        let root = std::env::temp_dir().join(format!(
            "sora-arena-mesh-{}-{}",
            std::process::id(),
            NEXT_ROOT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&root).unwrap();
        let keys = (0..players)
            .map(|slot| SigningKey::from_bytes(&[slot as u8 + 81; 32]))
            .collect::<Vec<_>>();
        let sockets = (0..players)
            .map(|_| UdpSocket::bind("127.0.0.1:0").unwrap())
            .collect::<Vec<_>>();
        let addresses = sockets
            .iter()
            .map(|socket| socket.local_addr().unwrap())
            .collect();
        Fixture {
            root,
            context: Context {
                network: [91; 32],
                session: [92; 32],
                manifest: [93; 32],
                roster: keys
                    .iter()
                    .map(|key| key.verifying_key().to_bytes())
                    .collect(),
            },
            config: Config {
                mode: Mode::FreeForAll,
                map: 0,
                max_ticks: ticks,
                base_bond: 0,
                offline: true,
            },
            participants: (0..players)
                .map(|slot| Participant {
                    team: (slot % 2) as u8,
                    class: 0,
                    weapon: 1,
                    bond: 0,
                    special_entitled: false,
                })
                .collect(),
            keys,
            addresses,
            sockets: std::cell::RefCell::new(sockets.into_iter().map(Some).collect()),
        }
    }

    impl Fixture {
        fn journal_path(&self, slot: usize) -> PathBuf {
            self.root.join(format!("peer-{slot}.journal"))
        }
        fn receipts_path(&self, slot: usize) -> PathBuf {
            self.root.join(format!("peer-{slot}.receipts"))
        }

        fn admission(&self, slot: usize, restore: bool, impairment: Impairment) -> MeshAdmission {
            let (journal, receipts) = if restore {
                let receipts = ReceiptLog::open(&self.receipts_path(slot)).unwrap();
                let journal = DurableSession::restore(
                    &self.journal_path(slot),
                    self.context.clone(),
                    self.config.clone(),
                    &self.participants,
                    receipts.latest(),
                )
                .unwrap();
                (journal, receipts)
            } else {
                let journal = DurableSession::create(
                    &self.journal_path(slot),
                    self.context.clone(),
                    self.config.clone(),
                    &self.participants,
                )
                .unwrap();
                let receipts =
                    ReceiptLog::create(&self.receipts_path(slot), journal.receipt()).unwrap();
                (journal, receipts)
            };
            MeshAdmission {
                socket: self.sockets.borrow_mut()[slot]
                    .take()
                    .unwrap_or_else(|| UdpSocket::bind(self.addresses[slot]).unwrap()),
                addresses: self.addresses.clone(),
                local_slot: slot,
                identity: self.keys[slot].clone(),
                journal,
                receipts,
                scope: NetworkScope::Loopback,
                impairment,
            }
        }

        fn reference(&self) -> World {
            let mut world = World::new(self.config.clone(), &self.participants).unwrap();
            while !world.terminal {
                let tick = world.tick;
                let controls = (0..self.participants.len())
                    .map(|slot| control(tick, slot))
                    .collect::<Vec<_>>();
                world.step(&controls).unwrap();
            }
            world
        }
    }

    fn pace(rate_hz: Option<u32>, start: Instant) -> Pace {
        Pace {
            rate_hz,
            start,
            stall_limit: Duration::from_secs(60),
            resolve_limit: Duration::from_secs(60),
            linger: Duration::from_millis(1_200),
        }
    }

    fn run(peer: MeshPeer) -> Result<HeadlessReport> {
        run_paced(peer, pace(None, Instant::now()))
    }

    fn run_paced(peer: MeshPeer, pace: Pace) -> Result<HeadlessReport> {
        let slot = peer.local_slot();
        run_headless(peer, pace, move |tick| control(tick, slot), |_| Watch::Run)
    }

    fn assert_agree(fixture: &Fixture, reports: &[HeadlessReport]) {
        let reference = fixture.reference();
        for report in reports {
            assert!(report.outcome.completed);
            assert_eq!(report.outcome.tick, reference.tick);
            assert_eq!(report.outcome.state_hash, reference.state_hash());
            assert_eq!(report.outcome.history_root, reports[0].outcome.history_root);
            let checkpoint = &report.checkpoint.as_ref().unwrap().checkpoint;
            assert_eq!(checkpoint.tick, reference.tick);
            assert_eq!(checkpoint.state_hash, reference.state_hash());
            // At most one journal sync per batch interval, plus the first.
            let intervals = report.elapsed.as_nanos() / SYNC_INTERVAL.as_nanos() + 1;
            assert!(u128::from(report.mesh.journal_syncs) <= intervals);
            assert_eq!(report.mesh.receipt_syncs, report.mesh.journal_syncs);
        }
    }

    #[test]
    fn three_loopback_peers_confirm_the_reference_match() {
        let fixture = fixture(3, 60);
        let reports = thread::scope(|scope| {
            let handles = (0..3)
                .map(|slot| {
                    let peer =
                        MeshPeer::start(fixture.admission(slot, false, Impairment::default()))
                            .unwrap();
                    scope.spawn(move || run(peer).unwrap())
                })
                .collect::<Vec<_>>();
            handles
                .into_iter()
                .map(|handle| handle.join().unwrap())
                .collect::<Vec<_>>()
        });
        assert_agree(&fixture, &reports);
        for report in &reports {
            // A delayed durable answer can outlast OFFER_ATTEMPTS and cause
            // a fresh offer, even without a crash or injected packet loss.
            assert_eq!(report.mesh.handshakes - report.mesh.replaced_channels, 2);
            assert_eq!(report.mesh.rejected, 0);
            assert!(report.mesh.checkpoints_retained >= 1);
            // Each journal restores to the same terminal outcome.
            assert_eq!(report.presentation.presented, 60);
        }
        let restored = DurableSession::restore(
            &fixture.journal_path(1),
            fixture.context.clone(),
            fixture.config.clone(),
            &fixture.participants,
            ReceiptLog::open(&fixture.receipts_path(1))
                .unwrap()
                .latest(),
        )
        .unwrap();
        assert_eq!(
            restored.session().terminal_outcome().unwrap(),
            reports[1].outcome
        );
    }

    #[test]
    fn a_delayed_durable_answer_can_replace_a_channel_before_the_match_starts() {
        let fixture = fixture(2, 20);
        let mut initiator =
            MeshPeer::start(fixture.admission(0, false, Impairment::default())).unwrap();
        let mut responder =
            MeshPeer::start(fixture.admission(1, false, Impairment::default())).unwrap();

        initiator.transmit().unwrap();
        responder.drain(Some(Duration::from_secs(5))).unwrap();
        let Link::Up {
            answered: Some(answer),
            ..
        } = &responder.remotes[0].link
        else {
            panic!("responder did not accept the first offer");
        };
        let old_offer = answer.offer;
        let old_response = answer.response;
        let first_records = answer.requires;
        assert_eq!(responder.stats.handshakes, 1);
        assert_eq!(responder.stats.replaced_channels, 0);

        // Hold the journal writer rather than sleeping: every response must
        // remain withheld while the initiator exhausts the retry budget.
        for _ in 0..OFFER_ATTEMPTS {
            let Link::Offering { sent, .. } = &mut initiator.remotes[0].link else {
                panic!("initiator used a response before it became durable");
            };
            *sent = Some(Instant::now() - OFFER_RETRY);
            initiator.transmit().unwrap();
            responder.drain(Some(Duration::from_secs(5))).unwrap();
            responder.transmit().unwrap();
            assert_eq!(responder.stats.datagrams_sent, 0);
            assert_eq!(responder.journal.durable_receipt().records, 0);
        }
        assert_eq!(responder.stats.handshakes, 2);
        assert_eq!(responder.stats.replaced_channels, 1);
        let Link::Up {
            answered: Some(answer),
            ..
        } = &responder.remotes[0].link
        else {
            panic!("responder did not accept the fresh offer");
        };
        assert_ne!(answer.offer, old_offer);
        assert!(answer.requires > first_records);
        let fresh_offer = answer.offer;
        let records = responder.journal.receipt().records;

        // Retransmission repeats the current response without installing a
        // new channel. An obsolete offer cannot undo the replacement, and
        // the initiator cannot use an answer bound to its expired offer.
        responder
            .handle_handshake(0, HandshakeKind::Offer, 0, 1, &fresh_offer)
            .unwrap();
        responder
            .handle_handshake(0, HandshakeKind::Offer, 0, 1, &old_offer)
            .unwrap();
        initiator
            .handle_handshake(0, HandshakeKind::Response, 0, 1, &old_response)
            .unwrap();
        assert_eq!(responder.journal.receipt().records, records);
        assert_eq!(responder.stats.handshakes, 2);
        assert_eq!(responder.stats.rejected, 1);
        assert_eq!(initiator.stats.rejected, 1);
        assert!(matches!(initiator.remotes[0].link, Link::Offering { .. }));

        let reports = thread::scope(|scope| {
            let first = scope.spawn(move || run(initiator).unwrap());
            let second = run(responder).unwrap();
            [first.join().unwrap(), second]
        });
        assert_agree(&fixture, &reports);
        for report in &reports {
            assert_eq!(report.mesh.handshakes - report.mesh.replaced_channels, 1);
            assert_eq!(report.mesh.rejected, 1);
        }
        assert!(reports[1].mesh.replaced_channels >= 1);
    }

    #[test]
    fn lost_duplicated_reordered_and_damaged_datagrams_cannot_change_the_outcome() {
        let fixture = fixture(3, 60);
        let reports = thread::scope(|scope| {
            let handles = (0..3)
                .map(|slot| {
                    let impairment = Impairment {
                        drop_per_mille: 100,
                        duplicate_per_mille: 100,
                        reorder_per_mille: 100,
                        corrupt_per_mille: 50,
                        seed: 7 + slot as u64,
                    };
                    let peer = MeshPeer::start(fixture.admission(slot, false, impairment)).unwrap();
                    scope.spawn(move || run(peer).unwrap())
                })
                .collect::<Vec<_>>();
            handles
                .into_iter()
                .map(|handle| handle.join().unwrap())
                .collect::<Vec<_>>()
        });
        assert_agree(&fixture, &reports);
        let total = |field: fn(&MeshStats) -> u64| -> u64 {
            reports.iter().map(|report| field(&report.mesh)).sum()
        };
        assert!(total(|stats| stats.impaired_dropped) > 0);
        assert!(total(|stats| stats.impaired_duplicated) > 0);
        assert!(total(|stats| stats.impaired_reordered) > 0);
        assert!(total(|stats| stats.impaired_corrupted) > 0);
        assert!(total(|stats| stats.retransmitted) > 0);
        assert!(total(|stats| stats.rejected) > 0);
        assert!(total(|stats| stats.duplicates + stats.out_of_order) > 0);
    }

    #[test]
    fn a_stopped_peer_resumes_from_its_journal_with_fresh_channels() {
        // Paced. Presentation runs at most 120 ticks ahead of confirmation,
        // so the peer stops mid-match however slowly frontiers confirm.
        let fixture = fixture(3, 240);
        let shared = pace(Some(60), Instant::now() + Duration::from_millis(200));
        let reports = thread::scope(|scope| {
            let handles = (0..2)
                .map(|slot| {
                    let peer =
                        MeshPeer::start(fixture.admission(slot, false, Impairment::default()))
                            .unwrap();
                    scope.spawn(move || run_paced(peer, shared).unwrap())
                })
                .collect::<Vec<_>>();
            let peer = MeshPeer::start(fixture.admission(2, false, Impairment::default())).unwrap();
            let stopped = run_headless(
                peer,
                shared,
                |tick| control(tick, 2),
                |peer| {
                    if peer.session().confirmed().tick >= 30 {
                        Watch::Stop
                    } else {
                        Watch::Run
                    }
                },
            );
            let Err(MeshError::Stopped { confirmed }) = stopped else {
                panic!("{:?}", stopped.map(|report| report.outcome));
            };
            assert!(confirmed >= 30);
            thread::sleep(Duration::from_millis(300));
            // Records staged after the last sync are lost with the process;
            // the journal keeps everything synced before.
            let admission = fixture.admission(2, true, Impairment::default());
            let restored = admission.journal.session().confirmed().tick;
            assert!(restored <= confirmed);
            assert!(admission.journal.receipt().records > 0);
            // The restored journal cannot join as a new match, and the slot's
            // journal and receipt log cannot be created again.
            assert_eq!(
                refusal(admission),
                Error::InvalidConfig("a new mesh match needs an empty journal and its receipt log")
            );
            assert!(
                DurableSession::create(
                    &fixture.journal_path(2),
                    fixture.context.clone(),
                    fixture.config.clone(),
                    &fixture.participants,
                )
                .is_err()
            );
            assert!(
                ReceiptLog::create(
                    &fixture.receipts_path(2),
                    Receipt {
                        records: 0,
                        digest: [0; 32],
                    }
                )
                .is_err()
            );
            let admission = fixture.admission(2, true, Impairment::default());
            let resumed = run_paced(MeshPeer::resume(admission).unwrap(), shared).unwrap();
            // Presentation resumes from the restored confirmed tick.
            assert!(resumed.presentation.presented <= 240 - restored);
            let mut reports = handles
                .into_iter()
                .map(|handle| handle.join().unwrap())
                .collect::<Vec<_>>();
            reports.push(resumed);
            reports
        });
        assert_agree(&fixture, &reports);
        assert_eq!(
            reports[2].mesh.handshakes - reports[2].mesh.replaced_channels,
            2
        );
        for report in &reports[..2] {
            assert!(report.mesh.replaced_channels >= 1);
        }
    }

    impl Fixture {
        /// A new admission for `slot` from its own fresh journal and receipt
        /// log, named by `tag`, on the slot's admitted address.
        fn fresh_admission(&self, slot: usize, tag: &str) -> MeshAdmission {
            let journal = DurableSession::create(
                &self.root.join(format!("peer-{slot}-{tag}.journal")),
                self.context.clone(),
                self.config.clone(),
                &self.participants,
            )
            .unwrap();
            let receipts = ReceiptLog::create(
                &self.root.join(format!("peer-{slot}-{tag}.receipts")),
                journal.receipt(),
            )
            .unwrap();
            MeshAdmission {
                socket: self.sockets.borrow_mut()[slot]
                    .take()
                    .unwrap_or_else(|| UdpSocket::bind(self.addresses[slot]).unwrap()),
                addresses: self.addresses.clone(),
                local_slot: slot,
                identity: self.keys[slot].clone(),
                journal,
                receipts,
                scope: NetworkScope::Loopback,
                impairment: Impairment::default(),
            }
        }
    }

    fn refusal(admission: MeshAdmission) -> Error {
        match MeshPeer::start(admission) {
            Err(MeshError::Evidence(error)) => error,
            Err(other) => panic!("refused for another reason: {other}"),
            Ok(_) => panic!("admitted"),
        }
    }

    #[test]
    fn admission_requires_its_own_address_scope_and_zero_bond() {
        let lan = |a, b, c, d| SocketAddr::from((Ipv4Addr::new(a, b, c, d), 40_000));
        assert!(NetworkScope::Loopback.admits(lan(127, 0, 0, 1)));
        assert!(!NetworkScope::Loopback.admits(lan(192, 168, 1, 20)));
        for private in [
            lan(10, 0, 0, 5),
            lan(172, 16, 3, 4),
            lan(192, 168, 1, 20),
            lan(169, 254, 7, 7),
        ] {
            assert!(NetworkScope::ResearchLan.admits(private));
        }
        for public in [lan(8, 8, 8, 8), lan(0, 0, 0, 0), lan(224, 0, 0, 1)] {
            assert!(!NetworkScope::ResearchLan.admits(public));
        }
        assert!(!NetworkScope::ResearchLan.admits(SocketAddr::from((Ipv4Addr::LOCALHOST, 0))));
        assert!(NetworkScope::ResearchLan.admits("[fd00::7]:40000".parse().unwrap()));
        assert!(!NetworkScope::ResearchLan.admits("[2001:db8::7]:40000".parse().unwrap()));

        // The unchanged admission is accepted, so each refusal below has
        // exactly one cause.
        let fixture = fixture(2, 20);
        drop(MeshPeer::start(fixture.fresh_admission(0, "admitted")).unwrap());
        // A LAN address among the peers needs the explicit research scope.
        let mut admission = fixture.fresh_admission(0, "lan");
        admission.addresses[1] = lan(192, 168, 1, 20);
        assert_eq!(
            refusal(admission),
            Error::InvalidConfig("mesh addresses must be loopback unless research LAN is chosen")
        );
        // The socket must be bound to the slot's own admitted address.
        let mut admission = fixture.fresh_admission(0, "socket");
        admission.socket = UdpSocket::bind("127.0.0.1:0").unwrap();
        assert_eq!(
            refusal(admission),
            Error::InvalidConfig("mesh socket is not bound to its admitted address")
        );
        // A new match needs the receipt log begun with its own journal.
        let mut admission = fixture.fresh_admission(0, "receipts");
        admission.receipts = ReceiptLog::create(
            &fixture.root.join("foreign.receipts"),
            Receipt {
                records: 0,
                digest: [0; 32],
            },
        )
        .unwrap();
        assert_eq!(
            refusal(admission),
            Error::InvalidConfig("a new mesh match needs an empty journal and its receipt log")
        );
        // Another slot's identity cannot use this slot.
        let mut admission = fixture.fresh_admission(1, "identity");
        admission.identity = fixture.keys[0].clone();
        assert_eq!(
            refusal(admission),
            Error::InvalidEvidence("mesh identity does not own its slot")
        );

        // A bonded admission is refused on loopback and research LAN alike.
        let mut bonded = fixture.config.clone();
        bonded.offline = false;
        bonded.base_bond = 1_000;
        let participants = fixture
            .participants
            .iter()
            .cloned()
            .map(|mut participant| {
                participant.bond = 1_000;
                participant
            })
            .collect::<Vec<_>>();
        for scope in [NetworkScope::Loopback, NetworkScope::ResearchLan] {
            let path = fixture.root.join(format!("bonded-{scope:?}.journal"));
            let journal = DurableSession::create(
                &path,
                fixture.context.clone(),
                bonded.clone(),
                &participants,
            )
            .unwrap();
            let receipts = ReceiptLog::create(
                &fixture.root.join(format!("bonded-{scope:?}.receipts")),
                journal.receipt(),
            )
            .unwrap();
            let socket = UdpSocket::bind("127.0.0.1:0").unwrap();
            let mut addresses = fixture.addresses.clone();
            addresses[0] = socket.local_addr().unwrap();
            assert!(matches!(
                MeshPeer::start(MeshAdmission {
                    socket,
                    addresses,
                    local_slot: 0,
                    identity: fixture.keys[0].clone(),
                    journal,
                    receipts,
                    scope,
                    impairment: Impairment::default(),
                }),
                Err(MeshError::Evidence(Error::InvalidConfig(
                    "mesh transport requires offline zero-bond admission"
                )))
            ));
        }
    }

    /// Two connected peers; the first has sent its commitments of ticks 0,
    /// 2 and 4 as frames 0 to 2. The second is no longer pumped, so only the
    /// ACKs a test makes with `ack_from` reach the first.
    fn three_frames_in_flight(fixture: &Fixture) -> (MeshPeer, MeshPeer) {
        let mut first =
            MeshPeer::start(fixture.admission(0, false, Impairment::default())).unwrap();
        let mut second =
            MeshPeer::start(fixture.admission(1, false, Impairment::default())).unwrap();
        let deadline = Instant::now() + Duration::from_secs(10);
        while !(matches!(first.remotes[0].link, Link::Up { .. })
            && matches!(second.remotes[0].link, Link::Up { .. }))
        {
            assert!(Instant::now() < deadline, "handshake did not complete");
            first
                .pump(Instant::now() + Duration::from_millis(5))
                .unwrap();
            second
                .pump(Instant::now() + Duration::from_millis(5))
                .unwrap();
        }
        // The commitments leave once their seals are durable.
        for start in [0, 2, 4] {
            first
                .commit([control(start, 0), control(start + 1, 0)])
                .unwrap();
        }
        while first.remotes[0].in_flight < 3 {
            assert!(Instant::now() < deadline, "commitments were not sent");
            first
                .pump(Instant::now() + Duration::from_millis(5))
                .unwrap();
        }
        (first, second)
    }

    /// An ACK from `second` to slot 0 with the given durable and received
    /// floors and held bitmap.
    fn ack_from(
        second: &MeshPeer,
        durable: u64,
        received: u64,
        held: u64,
    ) -> [u8; ACK_PACKET_BYTES] {
        let Link::Up { receiver, .. } = &second.remotes[0].link else {
            unreachable!()
        };
        let mut ack = [0; ACK_PACKET_BYTES];
        ack[..ACK_MAGIC.len()].copy_from_slice(ACK_MAGIC);
        ack[ACK_MAGIC.len()..ACK_MAGIC.len() + 2].copy_from_slice(&ACK_VERSION.to_le_bytes());
        ack[ACK_MAGIC.len() + 2] = 0;
        for (offset, value) in [durable, received, held].into_iter().enumerate() {
            let at = ACK_MAGIC.len() + 3 + offset * 8;
            ack[at..at + 8].copy_from_slice(&value.to_le_bytes());
        }
        let tag = receiver.ack_tag(&ack[..ACK_HEADER_BYTES]);
        ack[ACK_HEADER_BYTES..].copy_from_slice(&tag);
        ack
    }

    fn received(peer: &MeshPeer) -> Vec<bool> {
        peer.remotes[0]
            .outbound
            .iter()
            .map(|entry| entry.received)
            .collect()
    }

    #[test]
    fn acknowledgements_are_authenticated_selective_and_bounded_by_what_was_sent() {
        let fixture = fixture(2, 20);
        let (mut first, second) = three_frames_in_flight(&fixture);
        let ack = |durable, received, held| ack_from(&second, durable, received, held);
        let rejected = first.stats.rejected;
        let mut forged = ack(1, 1, 0);
        forged[ACK_PACKET_BYTES - 1] ^= 1;
        first.handle_ack(0, &forged);
        let mut renamed = ack(1, 1, 0);
        renamed[ACK_MAGIC.len() + 2] = 1;
        first.handle_ack(0, &renamed);
        // Frames never sent, or durable before they were received.
        first.handle_ack(0, &ack(0, 4, 0));
        first.handle_ack(0, &ack(2, 1, 0));
        assert_eq!(first.stats.rejected, rejected + 4);
        assert_eq!(first.remotes[0].outbound.len(), 3);
        assert!(
            first.remotes[0]
                .outbound
                .iter()
                .all(|entry| !entry.received)
        );

        // Frames 1 and 2 are held behind a missing frame 0: only frame 0 is
        // resent, once, before the timeout.
        first.handle_ack(0, &ack(0, 0, 0b11));
        assert_eq!(received(&first), [false, true, true]);
        let before = first.stats.retransmitted;
        // A fully backed-off timeout, so a thread that runs late on a loaded
        // machine cannot turn the early resend into a timeout.
        first.remotes[0].rto = RETRANSMIT_MAX;
        let long_ago = Instant::now() - GAP_RESEND_AFTER;
        for entry in &mut first.remotes[0].outbound {
            entry.sent_at = Some(long_ago);
        }
        first.transmit().unwrap();
        first.transmit().unwrap();
        assert_eq!(first.stats.retransmitted, before + 1);
        assert_eq!(first.stats.fast_retransmits, 1);
        assert_eq!(first.stats.timeouts, 0);

        // Received but not yet durable frames stay queued; durable ones go,
        // and a stale ACK after that is harmless.
        first.handle_ack(0, &ack(0, 3, 0));
        assert_eq!(received(&first), [true, true, true]);
        first.handle_ack(0, &ack(2, 3, 0));
        assert_eq!(first.remotes[0].outbound.len(), 1);
        first.handle_ack(0, &ack(3, 3, 0));
        first.handle_ack(0, &ack(1, 3, 0));
        assert!(first.remotes[0].outbound.is_empty());
        assert_eq!(first.remotes[0].in_flight, 0);
        assert_eq!(first.stats.acks_received, 5);
    }

    #[test]
    fn a_frame_the_receiver_stops_reporting_is_resent_after_the_timeout() {
        let fixture = fixture(2, 20);
        let (mut first, second) = three_frames_in_flight(&fixture);
        let ack = |durable, received, held| ack_from(&second, durable, received, held);
        // Frame 0 is missing and one fragment of frame 1 is held. Frame 0
        // then arrives, but frame 1 cannot be opened yet and is dropped, so
        // the next ACK reports neither frame 1 nor frame 2.
        first.handle_ack(0, &ack(0, 0, 0b01));
        assert_eq!(received(&first), [false, true, false]);
        first.handle_ack(0, &ack(1, 1, 0));
        assert_eq!(received(&first), [false, false]);
        // Both are resent once the retransmission timeout passes.
        let past = Instant::now() - 2 * RETRANSMIT_INITIAL;
        for entry in &mut first.remotes[0].outbound {
            entry.sent_at = Some(past);
        }
        let before = first.stats.retransmitted;
        first.transmit().unwrap();
        assert_eq!(first.stats.retransmitted, before + 2);
        assert_eq!(first.stats.timeouts, 1);
        assert_eq!(first.stats.probes, 0);
        // An ACK delayed behind a newer one changes nothing.
        first.handle_ack(0, &ack(1, 1, 0b01));
        assert_eq!(received(&first), [false, true]);
        first.handle_ack(0, &ack(0, 0, 0b01));
        assert_eq!(received(&first), [false, true]);
    }

    impl Fixture {
        /// Emulate a crash of `slot` before its last `count` journal records
        /// were synced: cut them from its journal, and its receipt log back
        /// to the entries at or before the cut. Returns the cut record kinds.
        fn lose_last_records(&self, slot: usize, count: usize) -> Vec<u8> {
            let empty = self.root.join(format!("empty-{slot}.journal"));
            drop(
                DurableSession::create(
                    &empty,
                    self.context.clone(),
                    self.config.clone(),
                    &self.participants,
                )
                .unwrap(),
            );
            let mut at = fs::metadata(&empty).unwrap().len() as usize;
            let bytes = fs::read(self.journal_path(slot)).unwrap();
            let mut starts = Vec::new();
            while at < bytes.len() {
                starts.push(at);
                at +=
                    8 + u32::from_le_bytes(bytes[at + 4..at + 8].try_into().unwrap()) as usize + 32;
            }
            assert_eq!(at, bytes.len());
            let kept = starts.len() - count;
            fs::write(self.journal_path(slot), &bytes[..starts[kept]]).unwrap();
            let log = fs::read(self.receipts_path(slot)).unwrap();
            let mut retained = RECEIPT_LOG_MAGIC.to_vec();
            for entry in log[RECEIPT_LOG_MAGIC.len()..].chunks(RECEIPT_ENTRY_BYTES) {
                if u32::from_le_bytes(entry[..4].try_into().unwrap()) as usize <= kept {
                    retained.extend(entry);
                }
            }
            fs::write(self.receipts_path(slot), retained).unwrap();
            starts[kept..]
                .iter()
                .map(|start| bytes[start + 8])
                .collect()
        }

        fn restore(&self, slot: usize) -> DurableSession {
            let latest = ReceiptLog::open(&self.receipts_path(slot))
                .unwrap()
                .latest();
            DurableSession::restore(
                &self.journal_path(slot),
                self.context.clone(),
                self.config.clone(),
                &self.participants,
                latest,
            )
            .unwrap()
        }
    }

    #[test]
    fn a_finished_peer_answers_a_peer_that_restarts_before_its_final_checkpoint() {
        let fixture = fixture(2, 20);
        let start = Instant::now();
        let (first, restarted, lost) = thread::scope(|scope| {
            let first =
                MeshPeer::start(fixture.admission(0, false, Impairment::default())).unwrap();
            let second =
                MeshPeer::start(fixture.admission(1, false, Impairment::default())).unwrap();
            // The first peer lingers long enough to see the restart.
            let lingering = Pace {
                linger: Duration::from_secs(5),
                ..pace(None, start)
            };
            let first = scope.spawn(move || run_paced(first, lingering).unwrap());
            let second = run_paced(second, pace(None, start)).unwrap();
            assert_eq!(second.checkpoint.unwrap().checkpoint.tick, 20);
            // Its final signature left, but it crashed before its final
            // checkpoint and finish records were durable.
            let lost = fixture.lose_last_records(1, 2);
            assert!(!first.is_finished(), "the finished peer left too early");
            let admission = fixture.admission(1, true, Impairment::default());
            let session = admission.journal.session();
            assert!(session.confirmed().terminal);
            assert!(
                session
                    .last_checkpoint()
                    .is_none_or(|checkpoint| checkpoint.checkpoint.tick < 20)
            );
            let restarted =
                run_paced(MeshPeer::resume(admission).unwrap(), pace(None, start)).unwrap();
            (first.join().unwrap(), restarted, lost)
        });
        assert_eq!(lost, [2, 4]);
        // The finished peer journaled the fresh offer and resent its final
        // signature, so both hold the final certified checkpoint.
        assert_eq!(first.mesh.handshakes - first.mesh.replaced_channels, 1);
        assert!(first.mesh.replaced_channels >= 1);
        assert_eq!(first.mesh.rejected, 0);
        assert_eq!(
            restarted.mesh.handshakes - restarted.mesh.replaced_channels,
            1
        );
        assert_agree(&fixture, &[first, restarted]);
    }

    #[test]
    fn a_restarted_peer_whose_peers_left_finishes_from_its_evidence() {
        let fixture = fixture(2, 20);
        let start = Instant::now();
        let reports = thread::scope(|scope| {
            let handles = (0..2)
                .map(|slot| {
                    let peer =
                        MeshPeer::start(fixture.admission(slot, false, Impairment::default()))
                            .unwrap();
                    scope.spawn(move || run(peer).unwrap())
                })
                .collect::<Vec<_>>();
            handles
                .into_iter()
                .map(|handle| handle.join().unwrap())
                .collect::<Vec<_>>()
        });
        assert_eq!(fixture.lose_last_records(1, 2), [2, 4]);
        // Nobody answers. After the resolve limit the peer finishes with the
        // outcome its evidence proves; the missing final checkpoint cannot
        // erase it.
        let alone = Pace {
            resolve_limit: Duration::from_millis(300),
            linger: Duration::from_millis(100),
            ..pace(None, start)
        };
        let peer = MeshPeer::resume(fixture.admission(1, true, Impairment::default())).unwrap();
        let restarted = run_paced(peer, alone).unwrap();
        assert!(restarted.outcome.completed);
        assert_eq!(restarted.outcome, reports[1].outcome);
        assert!(restarted.checkpoint.is_none());
        assert!(restarted.unacknowledged > 0);
        assert_eq!(
            fixture.restore(1).session().terminal_outcome().unwrap(),
            reports[1].outcome
        );
    }

    /// Every slot's scripted opening of the batch at `start_tick` and the
    /// certificate of their set, chained to `log`'s commitment head.
    fn certificate(
        fixture: &Fixture,
        log: &EvidenceLog,
        start_tick: u32,
    ) -> (CommitmentSet, Vec<SlotSignature>, Vec<Reveal>) {
        let reveals = (0..fixture.keys.len())
            .map(|slot| Reveal {
                start_tick,
                slot,
                inputs: vec![control(start_tick, slot), control(start_tick + 1, slot)],
                salt: [slot as u8; 32],
            })
            .collect::<Vec<_>>();
        let set = CommitmentSet {
            epoch: log.epoch,
            start_tick,
            parent: log.commitment_head,
            commitments: reveals
                .iter()
                .map(|reveal| reveal.commitment(&fixture.context, log.epoch).unwrap())
                .collect(),
        };
        let signatures = fixture
            .keys
            .iter()
            .enumerate()
            .map(|(slot, key)| {
                crate::protocol::sign_commitment_set(&fixture.context, &set, slot, key).unwrap()
            })
            .collect();
        (set, signatures, reveals)
    }

    #[test]
    fn an_interrupt_is_journaled_and_shares_its_certificates_and_checkpoint() {
        let fixture = fixture(3, 20);
        let mut peers = (0..2)
            .map(|slot| {
                MeshPeer::start(fixture.admission(slot, false, Impairment::default())).unwrap()
            })
            .collect::<Vec<_>>();
        // Both peers close the first frontier; only the first retains the
        // checkpoint of its boundary. It then certifies a second frontier.
        let (set, signatures, reveals) = certificate(&fixture, peers[0].session().evidence(), 0);
        for peer in &mut peers {
            peer.journal
                .certify(set.clone(), signatures.clone())
                .unwrap();
            peer.journal.reveal_many(reveals.clone()).unwrap();
            assert_eq!(peer.session().confirmed().tick, 2);
        }
        let checkpoint = peers[0].session().checkpoint();
        let votes = fixture
            .keys
            .iter()
            .enumerate()
            .map(|(slot, key)| checkpoint.sign(&fixture.context, slot, key).unwrap())
            .collect::<Vec<_>>();
        peers[0]
            .journal
            .checkpoint(checkpoint.clone(), votes.clone())
            .unwrap();
        let (next, next_signatures, _) = certificate(&fixture, peers[0].session().evidence(), 2);
        peers[0]
            .journal
            .certify(next.clone(), next_signatures)
            .unwrap();

        let first = &mut peers[0];
        first.interrupt().unwrap();
        let records = first.journal().receipt().records;
        for remote in &first.remotes {
            let shared = remote
                .outbound
                .iter()
                .rev()
                .take(2)
                .map(|entry| {
                    assert_eq!(entry.requires, records);
                    entry.message.clone()
                })
                .collect::<Vec<_>>();
            assert!(matches!(
                &shared[1],
                WireMessage::CommitmentCertificate { set, .. } if *set == next
            ));
            assert!(matches!(
                &shared[0],
                WireMessage::Checkpoint { checkpoint: sent, .. } if *sent == checkpoint
            ));
        }
        // Combat stays stopped, a second interrupt changes nothing, and the
        // pending frontier blocks a local finish.
        assert!(!first.can_commit() && !first.can_predict());
        first.interrupt().unwrap();
        assert_eq!(first.journal().receipt().records, records);
        assert!(first.finish().is_err());
        let deadline = Instant::now() + Duration::from_secs(10);
        while first.journal().durable_receipt().records < records {
            assert!(Instant::now() < deadline, "the interrupt was not synced");
            first
                .pump(Instant::now() + Duration::from_millis(5))
                .unwrap();
        }

        // The other peer retains the shared checkpoint of a boundary it
        // confirmed, and holds one it has not confirmed yet.
        let second = &mut peers[1];
        let later = Checkpoint {
            tick: 4,
            ..checkpoint.clone()
        };
        assert!(matches!(
            second.apply(
                0,
                WireMessage::Checkpoint {
                    checkpoint: later,
                    signatures: votes.clone(),
                }
            ),
            Ok(Applied::Deferred(_))
        ));
        let gate = second.apply(
            0,
            WireMessage::Checkpoint {
                checkpoint: checkpoint.clone(),
                signatures: votes,
            },
        );
        assert!(matches!(gate, Ok(Applied::Done(AckGate::Durable(_)))));
        assert_eq!(
            second.session().last_checkpoint().unwrap().checkpoint,
            checkpoint
        );
        drop(peers);
        let journal = fixture.restore(0);
        assert_eq!(journal.session().evidence().phase, Phase::Resolving);
        assert_eq!(journal.session().evidence().pending.len(), 1);
    }

    /// Slot 2 opens none of its commitments from this tick on, after the
    /// checkpoint at 120.
    const WITHHELD: u32 = 140;
    /// Every peer then certifies one full pipeline of frontiers past it...
    const CERTIFIED: u32 = WITHHELD + (MAX_OUTSTANDING_FRONTIERS * BATCH_TICKS) as u32;
    /// ...and commits one assembly window past that, short of the clock.
    const COMMITTED: u32 = CERTIFIED + ASSEMBLY_TICKS;
    const _: () = assert!(COMMITTED < 240);

    /// How far the peers of a dropout scenario have come, shared with the
    /// watches of their `run_headless`.
    #[derive(Default)]
    struct Dropout {
        settled: [AtomicBool; 3],
        dropped: AtomicBool,
        interrupted: [AtomicBool; 2],
        /// The returned slot 2 has closed every frontier.
        closed: AtomicBool,
    }

    /// Nothing is left for this peer to send before the dropout: it
    /// confirmed up to the withheld openings, certified and committed as far
    /// as the pipeline allows, synced the checkpoint at 120, and every peer
    /// acknowledged every frame it sent. Once each slot was seen settled,
    /// every frame that decides the survivors' evidence has arrived.
    fn settled(peer: &MeshPeer) -> bool {
        let session = peer.session();
        session.confirmed().tick == WITHHELD
            && session.evidence().certified_tick == CERTIFIED
            && peer.next_commit_tick() == COMMITTED
            && session
                .last_checkpoint()
                .is_some_and(|last| last.checkpoint.tick == 120)
            && peer.journal().durable_receipt() == peer.journal().receipt()
            && peer.unacknowledged() == 0
    }

    /// Every frontier the three peers endorsed before the dropout is closed
    /// and synced, and every peer acknowledged every frame this one sent.
    fn closed(peer: &MeshPeer) -> bool {
        let session = peer.session();
        session.confirmed().tick == COMMITTED
            && session.evidence().pending.is_empty()
            && peer.journal().durable_receipt() == peer.journal().receipt()
            && peer.unacknowledged() == 0
    }

    /// Hold the limits, but fail rather than hold forever.
    fn hold(peer: &MeshPeer, deadline: Instant, awaited: &str) -> Watch {
        assert!(
            Instant::now() < deadline,
            "slot {} held too long for {awaited}\n{}",
            peer.local_slot(),
            peer.describe()
        );
        Watch::Hold
    }

    /// A survivor holds its limits until slot 2 is gone, so only the dropout
    /// stops combat however slowly a loaded machine moves the live evidence,
    /// and while its journal still has records to sync. With `returns`, once
    /// it stopped combat it holds until it and the returned slot 2 closed
    /// every frontier.
    fn survivor(
        dropout: &Dropout,
        returns: bool,
        deadline: Instant,
    ) -> impl FnMut(&MeshPeer) -> Watch + '_ {
        let mut released = !returns;
        move |peer: &MeshPeer| {
            let slot = peer.local_slot();
            if settled(peer) {
                dropout.settled[slot].store(true, Ordering::SeqCst);
            }
            if !dropout.dropped.load(Ordering::SeqCst) {
                return hold(peer, deadline, "the dropout");
            }
            if peer.journal().durable_receipt() != peer.journal().receipt() {
                return hold(peer, deadline, "its journal");
            }
            if peer.session().evidence().phase == Phase::Live {
                return Watch::Run;
            }
            dropout.interrupted[slot].store(true, Ordering::SeqCst);
            released = released || (dropout.closed.load(Ordering::SeqCst) && closed(peer));
            if released {
                Watch::Run
            } else {
                hold(peer, deadline, "the returning peer")
            }
        }
    }

    /// Slots 0 and 1 survive. Slot 2 runs on the same clock but withholds its
    /// openings from `WITHHELD` on, so the evidence stops at a known
    /// frontier however fast each peer runs. Once every peer settled there,
    /// slot 2 is dropped like a crash and the survivors' limits start to
    /// count. With `returns`, slot 2 restarts from its journal once both
    /// survivors stopped combat.
    fn drop_slot_two(
        fixture: &Fixture,
        limits: Pace,
        returns: bool,
    ) -> (Vec<Result<HeadlessReport>>, Option<Result<HeadlessReport>>) {
        let dropout = Dropout::default();
        // Only bounds a failing run.
        let deadline = Instant::now() + Duration::from_secs(120);
        thread::scope(|scope| {
            let handles = (0..2)
                .map(|slot| {
                    let peer =
                        MeshPeer::start(fixture.admission(slot, false, Impairment::default()))
                            .unwrap();
                    let watch = survivor(&dropout, returns, deadline);
                    scope.spawn(move || {
                        run_headless(peer, limits, |tick| control(tick, slot), watch)
                    })
                })
                .collect::<Vec<_>>();
            let mut peer =
                MeshPeer::start(fixture.admission(2, false, Impairment::default())).unwrap();
            peer.withhold_openings_from(WITHHELD);
            let stopped = run_headless(
                peer,
                limits,
                |tick| control(tick, 2),
                |peer| {
                    if settled(peer) {
                        dropout.settled[2].store(true, Ordering::SeqCst);
                    }
                    if dropout
                        .settled
                        .iter()
                        .all(|settled| settled.load(Ordering::SeqCst))
                    {
                        Watch::Stop
                    } else {
                        hold(peer, deadline, "every peer to settle")
                    }
                },
            );
            assert!(
                matches!(
                    stopped,
                    Err(MeshError::Stopped {
                        confirmed: WITHHELD
                    })
                ),
                "{:?}",
                stopped.map(|report| report.outcome)
            );
            dropout.dropped.store(true, Ordering::SeqCst);
            let returned = returns.then(|| {
                while !dropout
                    .interrupted
                    .iter()
                    .all(|interrupted| interrupted.load(Ordering::SeqCst))
                {
                    assert!(
                        Instant::now() < deadline,
                        "the survivors never stopped combat"
                    );
                    thread::sleep(Duration::from_millis(5));
                }
                let peer =
                    MeshPeer::resume(fixture.admission(2, true, Impairment::default())).unwrap();
                run_headless(
                    peer,
                    limits,
                    |tick| control(tick, 2),
                    |peer| {
                        if dropout.closed.load(Ordering::SeqCst) || closed(peer) {
                            dropout.closed.store(true, Ordering::SeqCst);
                            Watch::Run
                        } else {
                            hold(peer, deadline, "every frontier to close")
                        }
                    },
                )
            });
            let results = handles
                .into_iter()
                .map(|handle| handle.join().unwrap())
                .collect();
            (results, returned)
        })
    }

    fn dropout_limits() -> Pace {
        Pace {
            stall_limit: Duration::from_millis(1_500),
            resolve_limit: Duration::from_millis(1_500),
            ..pace(Some(60), Instant::now() + Duration::from_millis(200))
        }
    }

    #[test]
    fn a_dropout_stops_combat_and_preserves_the_evidence_for_consensus() {
        let fixture = fixture(3, 240);
        let (results, _) = drop_slot_two(&fixture, dropout_limits(), false);
        for (slot, result) in results.iter().enumerate() {
            // Combat stopped where the dropped peer's openings end. The
            // certified checkpoint, every pending frontier and every opening
            // received stay. Only the dropped peer's openings are missing,
            // and only a consensus deadline can forfeit them.
            let Err(MeshError::Unresolved {
                confirmed, pending, ..
            }) = result
            else {
                panic!(
                    "slot {slot}: {:?}",
                    result.as_ref().map(|report| &report.outcome)
                );
            };
            assert_eq!(
                (*confirmed, *pending),
                (WITHHELD, MAX_OUTSTANDING_FRONTIERS)
            );
            let journal = fixture.restore(slot);
            let session = journal.session();
            let evidence = session.evidence();
            assert_eq!(evidence.phase, Phase::Resolving);
            assert!(!session.confirmed().terminal);
            assert_eq!(session.confirmed().tick, WITHHELD);
            assert_eq!(session.last_checkpoint().unwrap().checkpoint.tick, 120);
            // Both survivors hold the same certified frontiers.
            assert_eq!(evidence.certified_tick, CERTIFIED);
            assert_eq!(evidence.pending.len(), MAX_OUTSTANDING_FRONTIERS);
            for frontier in &evidence.pending {
                let opened = frontier
                    .openings
                    .iter()
                    .map(Option::is_some)
                    .collect::<Vec<_>>();
                assert_eq!(opened, [true, true, false], "slot {slot}");
            }
        }
        // A restarted survivor stays stopped.
        let peer = MeshPeer::resume(fixture.admission(0, true, Impairment::default())).unwrap();
        assert_eq!(peer.session().evidence().phase, Phase::Resolving);
        assert!(!peer.can_commit() && !peer.can_predict());
    }

    #[test]
    fn a_returning_peer_closes_the_frontiers_its_dropout_left_open() {
        let fixture = fixture(3, 240);
        let (results, returned) = drop_slot_two(&fixture, dropout_limits(), true);
        let mut reports = results
            .into_iter()
            .map(|result| result.unwrap())
            .collect::<Vec<_>>();
        reports.push(returned.unwrap().unwrap());
        // The survivors stopped combat before the peer returned. Its openings
        // then closed every frontier its dropout left open, and with them
        // every frontier all three endorsed before it left, with no
        // consensus deadline.
        let outcome = reports[0].outcome.clone();
        assert!(!outcome.completed, "combat did not stop on the dropout");
        assert_eq!(outcome.deadline_frontiers, 0);
        assert_eq!(outcome.tick, COMMITTED);
        let mut world = World::new(fixture.config.clone(), &fixture.participants).unwrap();
        while world.tick < outcome.tick {
            let tick = world.tick;
            world
                .step(&(0..3).map(|slot| control(tick, slot)).collect::<Vec<_>>())
                .unwrap();
        }
        assert_eq!(outcome.state_hash, world.state_hash());
        for report in &reports {
            assert_eq!(report.outcome, outcome);
            assert_eq!(report.checkpoint.as_ref().unwrap().checkpoint.tick, 120);
        }
    }

    #[test]
    fn receipt_log_grows_strictly_and_fails_closed_when_torn() {
        let fixture = fixture(2, 20);
        let path = fixture.root.join("anchor.receipts");
        let genesis = Receipt {
            records: 0,
            digest: [1; 32],
        };
        let mut log = ReceiptLog::create(&path, genesis).unwrap();
        assert!(ReceiptLog::create(&path, genesis).is_err());
        assert!(log.append(genesis).is_err());
        let next = Receipt {
            records: 3,
            digest: [2; 32],
        };
        log.append(next).unwrap();
        // A second writer cannot open the locked log.
        assert!(ReceiptLog::open(&path).is_err());
        drop(log);
        assert_eq!(ReceiptLog::open(&path).unwrap().latest(), next);
        let mut bytes = fs::read(&path).unwrap();
        bytes.pop();
        fs::write(&path, &bytes).unwrap();
        assert!(ReceiptLog::open(&path).is_err());
        let mut bytes = RECEIPT_LOG_MAGIC.to_vec();
        bytes.extend(entry(next));
        bytes.extend(entry(genesis));
        fs::write(&path, &bytes).unwrap();
        assert!(ReceiptLog::open(&path).is_err());
    }
}
