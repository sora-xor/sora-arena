//! Test-only, loopback UDP transport for two admitted evidence peers.
//!
//! A fresh authenticated X25519 exchange provides pairwise directional keys.
//! Complete signed frames are journaled before transmission, and received
//! frames are journaled before being returned. Prepared datagrams may be
//! retransmitted byte-for-byte by a bounded ACK scheduler. There is no
//! matchmaking, NAT traversal, chain settlement, or production peer recovery.
//! A restarted process must restore its journal against an independently
//! retained receipt and negotiate *new* keys; it cannot resume old channels.

use std::{
    collections::VecDeque,
    fs::{self, File, OpenOptions},
    io::{self, Read, Write},
    net::{SocketAddr, UdpSocket},
    path::{Path, PathBuf},
    time::{Duration, Instant},
};

use ed25519_dalek::SigningKey;

use crate::{
    Error,
    encrypted_wire::{EncryptedReceiver, EncryptedSender, FragmentDelivery},
    fragmented_wire::MAX_DATAGRAM_BYTES,
    handshake::{Initiator, PairwiseKeys},
    protocol::{Context, Reveal},
    recovery::{DurableSession, Receipt, RecoveryError},
    wire::{WireFrame, WireMessage},
};

const RECEIPT_MAGIC: &[u8] = b"SORA-ARENA-LOCAL-RECEIPT\x01";
const ACK_MAGIC: &[u8] = b"SORA-ARENA-ACK";
const ACK_VERSION: u16 = 1;
const ACK_HEADER_BYTES: usize = ACK_MAGIC.len() + 2 + 1 + 8;
const ACK_TAG_BYTES: usize = 32;
const ACK_PACKET_BYTES: usize = ACK_HEADER_BYTES + ACK_TAG_BYTES;
const MAX_RECEIVE_DATAGRAMS: usize = 64;
const MAX_QUEUED_FRAMES: usize = 8;
const MAX_PEER_TIMEOUT: Duration = Duration::from_secs(5);
pub const MAX_SEND_ATTEMPTS: usize = 4;

#[derive(Debug)]
pub enum TransportError {
    Io(io::Error),
    Evidence(Error),
    Journal(RecoveryError),
    Timeout,
    UnexpectedSource,
    OversizedDatagram,
    InboxFull,
    Closed,
}

impl std::fmt::Display for TransportError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(error) => error.fmt(f),
            Self::Evidence(error) => error.fmt(f),
            Self::Journal(error) => error.fmt(f),
            Self::Timeout => f.write_str("loopback peer did not respond before timeout"),
            Self::UnexpectedSource => f.write_str("datagram source differs from admitted peer"),
            Self::OversizedDatagram => f.write_str("datagram exceeds transport MTU"),
            Self::InboxFull => f.write_str("reliable receive queue is full"),
            Self::Closed => f.write_str("local transport closed after persistence failure"),
        }
    }
}
impl std::error::Error for TransportError {}
impl From<io::Error> for TransportError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}
impl From<Error> for TransportError {
    fn from(error: Error) -> Self {
        Self::Evidence(error)
    }
}
impl From<RecoveryError> for TransportError {
    fn from(error: RecoveryError) -> Self {
        Self::Journal(error)
    }
}
type Result<T> = std::result::Result<T, TransportError>;

/// A separate, synced test-harness artifact for each journal receipt. Its
/// location alone does not make it an independently trusted rollback anchor.
pub struct ReceiptFiles {
    directory: PathBuf,
}

impl ReceiptFiles {
    pub fn new(directory: impl Into<PathBuf>) -> Result<Self> {
        let directory = directory.into();
        fs::create_dir_all(&directory)?;
        Ok(Self { directory })
    }

    pub fn directory(&self) -> &Path {
        &self.directory
    }

    pub fn persist(&self, receipt: Receipt) -> Result<()> {
        let path = self
            .directory
            .join(format!("receipt-{:010}.bin", receipt.records));
        let mut bytes = Vec::with_capacity(RECEIPT_MAGIC.len() + 4 + 32);
        bytes.extend(RECEIPT_MAGIC);
        bytes.extend(receipt.records.to_le_bytes());
        bytes.extend(receipt.digest);
        match OpenOptions::new().write(true).create_new(true).open(&path) {
            Ok(mut file) => {
                file.write_all(&bytes)?;
                file.sync_all()?;
                #[cfg(unix)]
                File::open(&self.directory)?.sync_all()?;
                Ok(())
            }
            Err(error) if error.kind() == io::ErrorKind::AlreadyExists => {
                let mut existing = Vec::new();
                File::open(path)?.read_to_end(&mut existing)?;
                if existing == bytes {
                    Ok(())
                } else {
                    Err(TransportError::Evidence(Error::InvalidEvidence(
                        "external receipt conflicts with journal",
                    )))
                }
            }
            Err(error) => Err(error.into()),
        }
    }
}

/// Keeps the exact encrypted fragment bytes for retransmission after loss.
/// Re-sealing the same sequence would create a different AEAD nonce and is
/// forbidden by `EncryptedSender`.
pub struct PreparedEvidence {
    pub sequence: u64,
    fragments: Vec<Vec<u8>>,
}

/// Existing, externally authenticated offline admission and one loopback
/// endpoint. The constructor does not decide who belongs in the roster.
pub struct LocalPeerAdmission {
    pub socket: UdpSocket,
    pub remote: SocketAddr,
    pub local_slot: usize,
    pub remote_slot: usize,
    pub identity: SigningKey,
    pub journal: DurableSession,
    pub receipts: ReceiptFiles,
    pub timeout: Duration,
}
impl PreparedEvidence {
    pub fn fragment_count(&self) -> usize {
        self.fragments.len()
    }
}

/// One live pairwise channel and one durable evidence journal. This accepts
/// only packets from the exact admitted loopback address.
pub struct LocalhostPeer {
    socket: UdpSocket,
    remote: SocketAddr,
    local_slot: usize,
    identity: SigningKey,
    journal: DurableSession,
    receipts: ReceiptFiles,
    sender: EncryptedSender,
    receiver: EncryptedReceiver,
    timeout: Duration,
    queued: VecDeque<WireFrame>,
    closed: bool,
    #[cfg(test)]
    drop_next_ack: bool,
    #[cfg(test)]
    fail_next_ack: bool,
}

enum ReceivedDatagram {
    Ack(u64),
    Evidence(WireFrame),
    Incomplete,
}

impl LocalhostPeer {
    /// The caller supplies an already admitted and locked journal. A timeout
    /// requires a new offer with a fresh ephemeral secret, not reuse of this
    /// one-use initiator after process restart.
    pub fn initiate(admission: LocalPeerAdmission) -> Result<Self> {
        configure_socket(&admission.socket, admission.remote, admission.timeout)?;
        require_offline(&admission.journal)?;
        admission.receipts.persist(admission.journal.receipt())?;
        let context = admission.journal.session().evidence().context.clone();
        let (initiator, offer) = Initiator::start(
            context,
            admission.local_slot,
            admission.remote_slot,
            &admission.identity,
        )?;
        send_datagram(&admission.socket, admission.remote, &offer)?;
        let response = read_datagram(&admission.socket, admission.remote)?;
        let keys = initiator.finish(&response)?;
        Self::from_keys(admission, keys)
    }

    /// The accepted offer is synced into the journal, then its receipt into a
    /// separate file, before the signed response is put on the network.
    pub fn respond(mut admission: LocalPeerAdmission) -> Result<Self> {
        configure_socket(&admission.socket, admission.remote, admission.timeout)?;
        require_offline(&admission.journal)?;
        admission.receipts.persist(admission.journal.receipt())?;
        let offer = read_datagram(&admission.socket, admission.remote)?;
        let (keys, response, receipt) = admission.journal.accept_handshake_offer(
            admission.remote_slot,
            admission.local_slot,
            &admission.identity,
            &offer,
        )?;
        admission.receipts.persist(receipt)?;
        send_datagram(&admission.socket, admission.remote, &response)?;
        Self::from_keys(admission, keys)
    }

    fn from_keys(admission: LocalPeerAdmission, keys: PairwiseKeys) -> Result<Self> {
        let LocalPeerAdmission {
            socket,
            remote,
            local_slot,
            remote_slot,
            identity,
            journal,
            receipts,
            timeout,
        } = admission;
        let context: Context = journal.session().evidence().context.clone();
        let sender = EncryptedSender::new(
            context.clone(),
            local_slot,
            keys.channel_binding,
            keys.send_key,
            None,
        )?;
        let receiver = EncryptedReceiver::new(
            context,
            remote_slot,
            keys.channel_binding,
            keys.receive_key,
            None,
        )?;
        Ok(Self {
            socket,
            remote,
            local_slot,
            identity,
            journal,
            receipts,
            sender,
            receiver,
            timeout,
            queued: VecDeque::new(),
            closed: false,
            #[cfg(test)]
            drop_next_ack: false,
            #[cfg(test)]
            fail_next_ack: false,
        })
    }

    pub fn journal(&self) -> &DurableSession {
        &self.journal
    }

    pub fn local_addr(&self) -> Result<SocketAddr> {
        Ok(self.socket.local_addr()?)
    }

    /// Journal and externally record local evidence before constructing bytes
    /// that may leave this machine. Keep this returned object for retries.
    pub fn prepare(&mut self, frame: &WireFrame) -> Result<PreparedEvidence> {
        if self.closed {
            return Err(TransportError::Closed);
        }
        if frame.sender != self.local_slot {
            return Err(Error::InvalidEvidence("outbound sender differs from local slot").into());
        }
        let receipt = match append_message(&mut self.journal, &frame.message) {
            Ok(receipt) => receipt,
            Err(error) => {
                self.closed = true;
                return Err(error.into());
            }
        };
        if let Err(error) = self.receipts.persist(receipt) {
            self.closed = true;
            return Err(error);
        }
        let fragments = match self.sender.seal_fragments(frame, &self.identity) {
            Ok(fragments) => fragments,
            Err(error) => {
                self.closed = true;
                return Err(error.into());
            }
        };
        Ok(PreparedEvidence {
            sequence: frame.sequence,
            fragments,
        })
    }

    /// The caller can retransmit the same prepared datagrams after `Timeout`.
    pub fn transmit(&self, packet: &PreparedEvidence) -> Result<()> {
        if self.closed {
            return Err(TransportError::Closed);
        }
        for fragment in &packet.fragments {
            send_datagram(&self.socket, self.remote, fragment)?;
        }
        Ok(())
    }

    /// Stop-and-wait delivery of one already journaled packet. Each attempt
    /// sends the same sealed fragments and waits at most the admitted timeout.
    /// Incoming evidence is durably accepted and queued while waiting. After
    /// the bounded attempts fail, the caller must reconcile the peer's durable
    /// journal; a timeout never proves that the peer rejected the evidence.
    pub fn transmit_reliably(&mut self, packet: &PreparedEvidence) -> Result<()> {
        if self.closed {
            return Err(TransportError::Closed);
        }
        if self.sender.sequence_floor() != Some(packet.sequence) {
            return Err(
                Error::InvalidEvidence("reliable send requires latest prepared sequence").into(),
            );
        }
        let prior_timeout = self.socket.read_timeout()?;
        let outcome = self.transmit_reliably_inner(packet);
        self.socket.set_read_timeout(prior_timeout)?;
        outcome
    }

    fn transmit_reliably_inner(&mut self, packet: &PreparedEvidence) -> Result<()> {
        for _ in 0..MAX_SEND_ATTEMPTS {
            self.transmit(packet)?;
            let deadline = Instant::now() + self.timeout;
            for _ in 0..MAX_RECEIVE_DATAGRAMS {
                let Some(remaining) = deadline.checked_duration_since(Instant::now()) else {
                    break;
                };
                if remaining.is_zero() {
                    break;
                }
                self.socket.set_read_timeout(Some(remaining))?;
                let datagram = match read_datagram(&self.socket, self.remote) {
                    Ok(datagram) => datagram,
                    Err(TransportError::Timeout) => break,
                    Err(error) => return Err(error),
                };
                if self.queued.len() == MAX_QUEUED_FRAMES && !datagram.starts_with(ACK_MAGIC) {
                    return Err(TransportError::InboxFull);
                }
                match self.process_datagram(&datagram)? {
                    ReceivedDatagram::Ack(sequence) if sequence == packet.sequence => return Ok(()),
                    ReceivedDatagram::Evidence(frame) => self.queued.push_back(frame),
                    _ => {}
                }
            }
        }
        Err(TransportError::Timeout)
    }

    /// Complete, authenticated frames are appended to the local journal and
    /// externally recorded before returning them to game code.
    pub fn receive(&mut self) -> Result<WireFrame> {
        if self.closed {
            return Err(TransportError::Closed);
        }
        if let Some(frame) = self.queued.pop_front() {
            return Ok(frame);
        }
        for _ in 0..MAX_RECEIVE_DATAGRAMS {
            let datagram = read_datagram(&self.socket, self.remote)?;
            if let ReceivedDatagram::Evidence(frame) = self.process_datagram(&datagram)? {
                return Ok(frame);
            }
        }
        Err(TransportError::Evidence(Error::InvalidEvidence(
            "too many incomplete datagrams",
        )))
    }

    fn process_datagram(&mut self, datagram: &[u8]) -> Result<ReceivedDatagram> {
        if datagram.starts_with(ACK_MAGIC) {
            return decode_ack(datagram, self.local_slot, &self.sender).map(ReceivedDatagram::Ack);
        }
        let pending = self
            .journal
            .session()
            .evidence()
            .pending
            .as_ref()
            .map(|(set, _)| set);
        match self.receiver.open_fragment_or_replay(datagram, pending)? {
            FragmentDelivery::Pending => Ok(ReceivedDatagram::Incomplete),
            FragmentDelivery::AcceptedReplay(sequence) => {
                // The evidence was already persisted. An ACK write failure
                // cannot undo that receipt; the sender will retry again.
                let _ = self.send_ack(sequence);
                Ok(ReceivedDatagram::Incomplete)
            }
            FragmentDelivery::Frame(frame) => {
                let receipt = match append_message(&mut self.journal, &frame.message) {
                    Ok(receipt) => receipt,
                    Err(error) => {
                        self.closed = true;
                        return Err(error.into());
                    }
                };
                if let Err(error) = self.receipts.persist(receipt) {
                    self.closed = true;
                    return Err(error);
                }
                // The frame is now durable and must be delivered to game code
                // even if this non-authorizing UDP control packet cannot leave.
                let _ = self.send_ack(frame.sequence);
                Ok(ReceivedDatagram::Evidence(frame))
            }
        }
    }

    fn send_ack(&mut self, sequence: u64) -> Result<()> {
        #[cfg(test)]
        if std::mem::take(&mut self.fail_next_ack) {
            return Err(io::Error::other("injected ACK send failure").into());
        }
        #[cfg(test)]
        if std::mem::take(&mut self.drop_next_ack) {
            return Ok(());
        }
        let mut ack = [0; ACK_PACKET_BYTES];
        ack[..ACK_MAGIC.len()].copy_from_slice(ACK_MAGIC);
        ack[ACK_MAGIC.len()..ACK_MAGIC.len() + 2].copy_from_slice(&ACK_VERSION.to_le_bytes());
        ack[ACK_MAGIC.len() + 2] = self.receiver_slot()?;
        ack[ACK_MAGIC.len() + 3..ACK_HEADER_BYTES].copy_from_slice(&sequence.to_le_bytes());
        let tag = self.receiver.ack_tag(&ack[..ACK_HEADER_BYTES]);
        ack[ACK_HEADER_BYTES..].copy_from_slice(&tag);
        send_datagram(&self.socket, self.remote, &ack)
    }

    fn receiver_slot(&self) -> Result<u8> {
        u8::try_from(self.receiver.expected_sender())
            .map_err(|_| Error::InvalidConfig("remote slot exceeds ACK bound").into())
    }
}

fn decode_ack(packet: &[u8], local_slot: usize, sender: &EncryptedSender) -> Result<u64> {
    if packet.len() != ACK_PACKET_BYTES
        || packet[..ACK_MAGIC.len()] != *ACK_MAGIC
        || u16::from_le_bytes(
            packet[ACK_MAGIC.len()..ACK_MAGIC.len() + 2]
                .try_into()
                .expect("fixed ACK version"),
        ) != ACK_VERSION
        || packet[ACK_MAGIC.len() + 2] as usize != local_slot
    {
        return Err(Error::InvalidEvidence("ACK framing or sender differs").into());
    }
    sender.verify_ack_tag(&packet[..ACK_HEADER_BYTES], &packet[ACK_HEADER_BYTES..])?;
    Ok(u64::from_le_bytes(
        packet[ACK_MAGIC.len() + 3..ACK_HEADER_BYTES]
            .try_into()
            .expect("fixed ACK sequence"),
    ))
}

fn append_message(
    journal: &mut DurableSession,
    message: &WireMessage,
) -> std::result::Result<Receipt, RecoveryError> {
    match message {
        WireMessage::CommitmentCertificate { set, signatures } => {
            journal.certify(set.clone(), signatures.clone())
        }
        WireMessage::Reveal { reveal, .. } => journal.reveal(Reveal {
            slot: reveal.slot,
            inputs: reveal.inputs.clone(),
            salt: reveal.salt,
        }),
        WireMessage::Checkpoint {
            checkpoint,
            signatures,
        } => journal.checkpoint(checkpoint.clone(), signatures.clone()),
    }
}

fn configure_socket(socket: &UdpSocket, remote: SocketAddr, timeout: Duration) -> Result<()> {
    if !socket.local_addr()?.ip().is_loopback() || !remote.ip().is_loopback() {
        return Err(Error::InvalidConfig("localhost transport requires loopback addresses").into());
    }
    if timeout.is_zero() || timeout > MAX_PEER_TIMEOUT {
        return Err(Error::InvalidConfig("localhost transport timeout outside bound").into());
    }
    socket.set_read_timeout(Some(timeout))?;
    Ok(())
}

fn require_offline(journal: &DurableSession) -> Result<()> {
    if !journal.session().confirmed().config.offline {
        return Err(Error::InvalidConfig("localhost transport requires offline admission").into());
    }
    Ok(())
}

fn send_datagram(socket: &UdpSocket, remote: SocketAddr, bytes: &[u8]) -> Result<()> {
    if bytes.len() > MAX_DATAGRAM_BYTES {
        return Err(TransportError::OversizedDatagram);
    }
    if socket.send_to(bytes, remote)? != bytes.len() {
        return Err(io::Error::new(io::ErrorKind::WriteZero, "short UDP send").into());
    }
    Ok(())
}

fn read_datagram(socket: &UdpSocket, expected: SocketAddr) -> Result<Vec<u8>> {
    let mut buffer = [0; MAX_DATAGRAM_BYTES + 1];
    let (count, source) = match socket.recv_from(&mut buffer) {
        Ok(datagram) => datagram,
        Err(error)
            if matches!(
                error.kind(),
                io::ErrorKind::TimedOut | io::ErrorKind::WouldBlock
            ) =>
        {
            return Err(TransportError::Timeout);
        }
        Err(error) => return Err(error.into()),
    };
    if source != expected {
        return Err(TransportError::UnexpectedSource);
    }
    if count > MAX_DATAGRAM_BYTES {
        return Err(TransportError::OversizedDatagram);
    }
    Ok(buffer[..count].to_vec())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        sync::atomic::{AtomicU64, Ordering},
        thread,
    };

    use crate::{
        protocol::{CommitmentSet, input_commitment, sign_commitment_set},
        simulation::{Config, Input, Mode, Participant},
    };

    static NEXT_ROOT: AtomicU64 = AtomicU64::new(0);

    struct TestRoot(PathBuf);
    impl TestRoot {
        fn new() -> Self {
            let number = NEXT_ROOT.fetch_add(1, Ordering::Relaxed);
            let path = std::env::temp_dir().join(format!(
                "sora-arena-local-udp-{}-{number}",
                std::process::id()
            ));
            fs::create_dir(&path).unwrap();
            Self(path)
        }
    }
    impl Drop for TestRoot {
        fn drop(&mut self) {
            fs::remove_dir_all(&self.0).unwrap();
        }
    }

    fn setup(players: usize) -> (TestRoot, LocalhostPeer, LocalhostPeer, Vec<SigningKey>) {
        let root = TestRoot::new();
        let keys = (1..=players)
            .map(|n| SigningKey::from_bytes(&[n as u8; 32]))
            .collect::<Vec<_>>();
        let context = Context {
            network: [61; 32],
            session: [62; 32],
            manifest: [63; 32],
            roster: keys
                .iter()
                .map(|key| key.verifying_key().to_bytes())
                .collect(),
        };
        let config = Config {
            mode: Mode::Control,
            map: 0,
            max_ticks: 120,
            base_bond: 0,
            offline: true,
        };
        let participants = (0..players)
            .map(|slot| Participant {
                team: (slot % 2) as u8,
                class: 0,
                weapon: 0,
                bond: 0,
                special_entitled: false,
            })
            .collect::<Vec<_>>();
        let initiator_journal = DurableSession::create(
            &root.0.join("initiator.journal"),
            context.clone(),
            config.clone(),
            &participants,
        )
        .unwrap();
        let responder_journal = DurableSession::create(
            &root.0.join("responder.journal"),
            context,
            config,
            &participants,
        )
        .unwrap();
        let initiator_socket = UdpSocket::bind("127.0.0.1:0").unwrap();
        let responder_socket = UdpSocket::bind("127.0.0.1:0").unwrap();
        let initiator_addr = initiator_socket.local_addr().unwrap();
        let responder_addr = responder_socket.local_addr().unwrap();
        let responder_key = keys[1].clone();
        let responder_receipts = ReceiptFiles::new(root.0.join("responder-receipts")).unwrap();
        let responder_thread = thread::spawn(move || {
            LocalhostPeer::respond(LocalPeerAdmission {
                socket: responder_socket,
                remote: initiator_addr,
                local_slot: 1,
                remote_slot: 0,
                identity: responder_key,
                journal: responder_journal,
                receipts: responder_receipts,
                timeout: Duration::from_secs(2),
            })
        });
        let initiator = LocalhostPeer::initiate(LocalPeerAdmission {
            socket: initiator_socket,
            remote: responder_addr,
            local_slot: 0,
            remote_slot: 1,
            identity: keys[0].clone(),
            journal: initiator_journal,
            receipts: ReceiptFiles::new(root.0.join("initiator-receipts")).unwrap(),
            timeout: Duration::from_secs(2),
        })
        .unwrap();
        let responder = responder_thread.join().unwrap().unwrap();
        assert!(
            root.0
                .join("responder-receipts/receipt-0000000001.bin")
                .exists()
        );
        (root, initiator, responder, keys)
    }

    fn frontier(peer: &LocalhostPeer, keys: &[SigningKey]) -> (CommitmentSet, Vec<Reveal>) {
        let evidence = peer.journal().session().evidence();
        let reveals = keys
            .iter()
            .enumerate()
            .map(|(slot, _)| Reveal {
                slot,
                inputs: vec![Input::default(); 2],
                salt: [slot as u8; 32],
            })
            .collect::<Vec<_>>();
        let set = CommitmentSet {
            epoch: 0,
            start_tick: 0,
            parent: evidence.root,
            commitments: reveals
                .iter()
                .map(|reveal| {
                    input_commitment(
                        &evidence.context,
                        0,
                        0,
                        evidence.root,
                        reveal.slot,
                        &reveal.inputs,
                        reveal.salt,
                    )
                    .unwrap()
                })
                .collect(),
        };
        (set, reveals)
    }

    fn certificate(peer: &LocalhostPeer, keys: &[SigningKey], set: &CommitmentSet) -> WireFrame {
        WireFrame {
            sender: 0,
            sequence: 0,
            message: WireMessage::CommitmentCertificate {
                set: set.clone(),
                signatures: keys
                    .iter()
                    .enumerate()
                    .map(|(slot, key)| {
                        sign_commitment_set(
                            &peer.journal().session().evidence().context,
                            set,
                            slot,
                            key,
                        )
                        .unwrap()
                    })
                    .collect(),
            },
        }
    }

    #[test]
    fn two_admitted_udp_peers_exchange_durable_certificate_and_both_reveals() {
        let (root, mut initiator, mut responder, keys) = setup(2);
        let (set, reveals) = frontier(&initiator, &keys);
        let certified = certificate(&initiator, &keys, &set);
        let outgoing = initiator.prepare(&certified).unwrap();
        assert_eq!(outgoing.fragment_count(), 1);
        initiator.transmit(&outgoing).unwrap();
        assert_eq!(responder.receive().unwrap(), certified);
        assert!(
            root.0
                .join("responder-receipts/receipt-0000000002.bin")
                .exists()
        );

        let other_reveal = WireFrame {
            sender: 1,
            sequence: 0,
            message: WireMessage::Reveal {
                set: set.clone(),
                reveal: reveals[1].clone(),
            },
        };
        let outgoing = responder.prepare(&other_reveal).unwrap();
        responder.transmit(&outgoing).unwrap();
        assert_eq!(initiator.receive().unwrap(), other_reveal);

        let own_reveal = WireFrame {
            sender: 0,
            sequence: 1,
            message: WireMessage::Reveal {
                set,
                reveal: reveals[0].clone(),
            },
        };
        let outgoing = initiator.prepare(&own_reveal).unwrap();
        initiator.transmit(&outgoing).unwrap();
        assert_eq!(responder.receive().unwrap(), own_reveal);
        assert_eq!(
            initiator.journal().session().confirmed().state_hash(),
            responder.journal().session().confirmed().state_hash()
        );
        assert_eq!(initiator.journal().session().evidence().next_tick, 2);
        assert_eq!(responder.journal().session().evidence().next_tick, 2);
    }

    #[test]
    fn lost_datagram_can_be_retransmitted_without_resealing_or_double_journaling() {
        let (_root, mut initiator, mut responder, keys) = setup(2);
        let (set, _) = frontier(&initiator, &keys);
        let frame = certificate(&initiator, &keys, &set);
        let outgoing = initiator.prepare(&frame).unwrap();
        let dropped_socket = UdpSocket::bind("127.0.0.1:0").unwrap();
        for fragment in &outgoing.fragments {
            initiator
                .socket
                .send_to(fragment, dropped_socket.local_addr().unwrap())
                .unwrap();
        }
        responder
            .socket
            .set_read_timeout(Some(Duration::from_millis(25)))
            .unwrap();
        assert!(matches!(responder.receive(), Err(TransportError::Timeout)));
        let before = initiator.journal().receipt();
        initiator.transmit(&outgoing).unwrap();
        assert_eq!(responder.receive().unwrap(), frame);
        assert_eq!(initiator.journal().receipt(), before);
        assert_eq!(responder.journal().receipt().records, 2);
    }

    #[test]
    fn reliable_send_waits_for_durable_ack_without_rejournaling() {
        let (_root, mut initiator, mut responder, keys) = setup(2);
        let (set, _) = frontier(&initiator, &keys);
        let frame = certificate(&initiator, &keys, &set);
        let outgoing = initiator.prepare(&frame).unwrap();
        let retained = initiator.journal().receipt();
        let receiving = thread::spawn(move || {
            assert_eq!(responder.receive().unwrap(), frame);
            responder
        });
        initiator.transmit_reliably(&outgoing).unwrap();
        responder = receiving.join().unwrap();
        assert_eq!(initiator.journal().receipt(), retained);
        assert_eq!(responder.journal().receipt().records, 2);
    }

    #[test]
    fn incoming_evidence_during_ack_wait_is_journaled_and_queued() {
        let (_root, mut initiator, mut responder, keys) = setup(2);
        let (set, reveals) = frontier(&initiator, &keys);
        let certificate = certificate(&initiator, &keys, &set);
        let certified = initiator.prepare(&certificate).unwrap();
        initiator.transmit(&certified).unwrap();
        assert_eq!(responder.receive().unwrap(), certificate);
        let peer_reveal = WireFrame {
            sender: 1,
            sequence: 0,
            message: WireMessage::Reveal {
                set: set.clone(),
                reveal: reveals[1].clone(),
            },
        };
        let peer_packet = responder.prepare(&peer_reveal).unwrap();
        responder.transmit(&peer_packet).unwrap();
        let own_reveal = WireFrame {
            sender: 0,
            sequence: 1,
            message: WireMessage::Reveal {
                set,
                reveal: reveals[0].clone(),
            },
        };
        let own_packet = initiator.prepare(&own_reveal).unwrap();
        let receiving = thread::spawn(move || {
            assert_eq!(responder.receive().unwrap(), own_reveal);
            responder
        });
        initiator.transmit_reliably(&own_packet).unwrap();
        responder = receiving.join().unwrap();
        assert_eq!(initiator.receive().unwrap(), peer_reveal);
        assert_eq!(initiator.journal().session().evidence().next_tick, 2);
        assert_eq!(responder.journal().session().evidence().next_tick, 2);
    }

    #[test]
    fn lost_ack_retries_exact_bytes_and_duplicate_is_only_acknowledged() {
        let (_root, mut initiator, mut responder, keys) = setup(2);
        let (set, _) = frontier(&initiator, &keys);
        let frame = certificate(&initiator, &keys, &set);
        let outgoing = initiator.prepare(&frame).unwrap();
        let exact = outgoing.fragments.clone();
        initiator.timeout = Duration::from_millis(35);
        responder.drop_next_ack = true;
        responder
            .socket
            .set_read_timeout(Some(Duration::from_millis(90)))
            .unwrap();
        let receiving = thread::spawn(move || {
            assert_eq!(responder.receive().unwrap(), frame);
            let accepted = responder.journal().receipt();
            assert!(matches!(responder.receive(), Err(TransportError::Timeout)));
            assert_eq!(responder.journal().receipt(), accepted);
            responder
        });
        initiator.transmit_reliably(&outgoing).unwrap();
        responder = receiving.join().unwrap();
        assert_eq!(outgoing.fragments, exact);
        assert_eq!(initiator.journal().receipt().records, 1);
        assert_eq!(responder.journal().receipt().records, 2);
    }

    #[test]
    fn ack_write_failure_cannot_hide_durably_received_evidence() {
        let (_root, mut initiator, mut responder, keys) = setup(2);
        let (set, _) = frontier(&initiator, &keys);
        let frame = certificate(&initiator, &keys, &set);
        let outgoing = initiator.prepare(&frame).unwrap();
        responder.fail_next_ack = true;
        initiator.transmit(&outgoing).unwrap();
        assert_eq!(responder.receive().unwrap(), frame);
        let accepted = responder.journal().receipt();
        initiator.transmit(&outgoing).unwrap();
        responder
            .socket
            .set_read_timeout(Some(Duration::from_millis(25)))
            .unwrap();
        assert!(matches!(responder.receive(), Err(TransportError::Timeout)));
        assert_eq!(responder.journal().receipt(), accepted);
        let ack = read_datagram(&initiator.socket, initiator.remote).unwrap();
        assert_eq!(
            decode_ack(&ack, initiator.local_slot, &initiator.sender).unwrap(),
            0
        );
        let mut forged = ack.clone();
        forged[ACK_MAGIC.len() + 3] ^= 1;
        assert!(decode_ack(&forged, initiator.local_slot, &initiator.sender).is_err());
        forged = ack;
        forged[ACK_PACKET_BYTES - 1] ^= 1;
        assert!(decode_ack(&forged, initiator.local_slot, &initiator.sender).is_err());
    }

    #[test]
    fn bounded_retry_exhaustion_does_not_claim_peer_rejection() {
        let (_root, mut initiator, responder, keys) = setup(2);
        let (set, _) = frontier(&initiator, &keys);
        let frame = certificate(&initiator, &keys, &set);
        let outgoing = initiator.prepare(&frame).unwrap();
        initiator.timeout = Duration::from_millis(10);
        let before = initiator.journal().receipt();
        assert!(matches!(
            initiator.transmit_reliably(&outgoing),
            Err(TransportError::Timeout)
        ));
        assert_eq!(initiator.journal().receipt(), before);
        assert_eq!(responder.journal().receipt().records, 1);
    }

    #[test]
    fn reordered_and_duplicate_udp_fragments_reassemble_once() {
        let (_root, mut initiator, mut responder, keys) = setup(12);
        let (set, _) = frontier(&initiator, &keys);
        let frame = certificate(&initiator, &keys, &set);
        let outgoing = initiator.prepare(&frame).unwrap();
        assert_eq!(outgoing.fragment_count(), 2);
        let second = &outgoing.fragments[1];
        let first = &outgoing.fragments[0];
        send_datagram(&initiator.socket, initiator.remote, second).unwrap();
        send_datagram(&initiator.socket, initiator.remote, second).unwrap();
        send_datagram(&initiator.socket, initiator.remote, first).unwrap();
        assert_eq!(responder.receive().unwrap(), frame);
        let retained = responder.journal().receipt();
        send_datagram(&initiator.socket, initiator.remote, first).unwrap();
        responder
            .socket
            .set_read_timeout(Some(Duration::from_millis(25)))
            .unwrap();
        assert!(matches!(responder.receive(), Err(TransportError::Timeout)));
        assert_eq!(responder.journal().receipt(), retained);
    }

    #[test]
    fn reordered_fragments_with_lost_ack_are_reacknowledged_once() {
        let (_root, mut initiator, mut responder, keys) = setup(12);
        let (set, _) = frontier(&initiator, &keys);
        let frame = certificate(&initiator, &keys, &set);
        let outgoing = initiator.prepare(&frame).unwrap();
        assert_eq!(outgoing.fragment_count(), 2);
        responder.drop_next_ack = true;
        send_datagram(&initiator.socket, initiator.remote, &outgoing.fragments[1]).unwrap();
        send_datagram(&initiator.socket, initiator.remote, &outgoing.fragments[1]).unwrap();
        send_datagram(&initiator.socket, initiator.remote, &outgoing.fragments[0]).unwrap();
        assert_eq!(responder.receive().unwrap(), frame);
        let accepted = responder.journal().receipt();
        initiator.timeout = Duration::from_millis(50);
        responder
            .socket
            .set_read_timeout(Some(Duration::from_millis(100)))
            .unwrap();
        let pumping = thread::spawn(move || {
            assert!(matches!(responder.receive(), Err(TransportError::Timeout)));
            responder
        });
        initiator.transmit_reliably(&outgoing).unwrap();
        responder = pumping.join().unwrap();
        assert_eq!(responder.journal().receipt(), accepted);
    }

    #[test]
    fn restart_restores_journals_but_requires_fresh_channel_acks() {
        let (root, mut initiator, mut responder, keys) = setup(2);
        let (set, reveals) = frontier(&initiator, &keys);
        let certified = certificate(&initiator, &keys, &set);
        let old_packet = initiator.prepare(&certified).unwrap();
        initiator.transmit(&old_packet).unwrap();
        assert_eq!(responder.receive().unwrap(), certified);
        let stale_ack = read_datagram(&initiator.socket, initiator.remote).unwrap();
        let context = initiator.journal.session().evidence().context.clone();
        let config = initiator.journal.session().confirmed().config.clone();
        let participants = (0..2)
            .map(|slot| Participant {
                team: slot as u8,
                class: 0,
                weapon: 0,
                bond: 0,
                special_entitled: false,
            })
            .collect::<Vec<_>>();
        let initiator_receipt = initiator.journal().receipt();
        let responder_receipt = responder.journal().receipt();
        drop(initiator);
        drop(responder);

        let initiator_journal = DurableSession::restore(
            &root.0.join("initiator.journal"),
            context.clone(),
            config.clone(),
            &participants,
            initiator_receipt,
        )
        .unwrap();
        let responder_journal = DurableSession::restore(
            &root.0.join("responder.journal"),
            context,
            config,
            &participants,
            responder_receipt,
        )
        .unwrap();
        let initiator_socket = UdpSocket::bind("127.0.0.1:0").unwrap();
        let responder_socket = UdpSocket::bind("127.0.0.1:0").unwrap();
        let initiator_addr = initiator_socket.local_addr().unwrap();
        let responder_addr = responder_socket.local_addr().unwrap();
        let responder_key = keys[1].clone();
        let responder_receipts = ReceiptFiles::new(root.0.join("responder-receipts")).unwrap();
        let receiving = thread::spawn(move || {
            LocalhostPeer::respond(LocalPeerAdmission {
                socket: responder_socket,
                remote: initiator_addr,
                local_slot: 1,
                remote_slot: 0,
                identity: responder_key,
                journal: responder_journal,
                receipts: responder_receipts,
                timeout: Duration::from_secs(2),
            })
        });
        initiator = LocalhostPeer::initiate(LocalPeerAdmission {
            socket: initiator_socket,
            remote: responder_addr,
            local_slot: 0,
            remote_slot: 1,
            identity: keys[0].clone(),
            journal: initiator_journal,
            receipts: ReceiptFiles::new(root.0.join("initiator-receipts")).unwrap(),
            timeout: Duration::from_secs(2),
        })
        .unwrap();
        responder = receiving.join().unwrap().unwrap();
        assert!(decode_ack(&stale_ack, 0, &initiator.sender).is_err());
        assert!(
            responder
                .receiver
                .open_fragment(&old_packet.fragments[0], None)
                .is_err()
        );
        let reveal = WireFrame {
            sender: 0,
            sequence: 0,
            message: WireMessage::Reveal {
                set,
                reveal: reveals[0].clone(),
            },
        };
        let fresh_packet = initiator.prepare(&reveal).unwrap();
        let receiving = thread::spawn(move || {
            assert_eq!(responder.receive().unwrap(), reveal);
            responder
        });
        initiator.transmit_reliably(&fresh_packet).unwrap();
        responder = receiving.join().unwrap();
        assert_eq!(
            responder.journal().receipt().records,
            responder_receipt.records + 2
        );
    }

    #[test]
    fn failed_external_receipt_persistence_closes_before_transmission() {
        let (root, mut initiator, mut responder, keys) = setup(2);
        let (set, _) = frontier(&initiator, &keys);
        fs::remove_dir_all(root.0.join("initiator-receipts")).unwrap();
        let frame = certificate(&initiator, &keys, &set);
        assert!(matches!(
            initiator.prepare(&frame),
            Err(TransportError::Io(_))
        ));
        assert!(matches!(
            initiator.prepare(&frame),
            Err(TransportError::Closed)
        ));
        assert!(matches!(responder.receive(), Err(TransportError::Timeout)));
    }

    #[test]
    fn non_offline_admission_cannot_open_a_local_transport() {
        let root = TestRoot::new();
        let keys = [
            SigningKey::from_bytes(&[71; 32]),
            SigningKey::from_bytes(&[72; 32]),
        ];
        let context = Context {
            network: [73; 32],
            session: [74; 32],
            manifest: [75; 32],
            roster: keys
                .iter()
                .map(|key| key.verifying_key().to_bytes())
                .collect(),
        };
        let participants = (0..2)
            .map(|team| Participant {
                team,
                class: 0,
                weapon: 0,
                bond: 1_000,
                special_entitled: false,
            })
            .collect::<Vec<_>>();
        let journal = DurableSession::create(
            &root.0.join("bonded.journal"),
            context,
            Config {
                mode: Mode::Control,
                map: 0,
                max_ticks: 120,
                base_bond: 1_000,
                offline: false,
            },
            &participants,
        )
        .unwrap();
        let socket = UdpSocket::bind("127.0.0.1:0").unwrap();
        let remote = UdpSocket::bind("127.0.0.1:0").unwrap();
        let admission = LocalPeerAdmission {
            socket,
            remote: remote.local_addr().unwrap(),
            local_slot: 0,
            remote_slot: 1,
            identity: keys[0].clone(),
            journal,
            receipts: ReceiptFiles::new(root.0.join("receipts")).unwrap(),
            timeout: Duration::from_millis(50),
        };
        assert!(matches!(
            LocalhostPeer::initiate(admission),
            Err(TransportError::Evidence(Error::InvalidConfig(_)))
        ));
        assert_eq!(fs::read_dir(root.0.join("receipts")).unwrap().count(), 0);
    }
}
