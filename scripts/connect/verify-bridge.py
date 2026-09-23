#!/usr/bin/env python3
"""Run actual ABI/crypto/strict-JSON smoke checks before staging a Connect bridge."""
import argparse
import base64
import copy
import ctypes as c
import hashlib
import json
from pathlib import Path
import re
import sys

U8 = c.c_uint8
UL = c.c_ulong  # Not c_uint64: Windows' C unsigned long is 32 bits.
PTR = c.POINTER(U8)
OUT = c.POINTER(PTR)
LEN = c.POINTER(UL)


def verify_ciphertext(api, app_public, app_private, sid):
    """Exercise native X25519/HKDF and authenticated envelopes with ephemeral keys."""
    wallet_public, wallet_private = (U8 * 32)(), (U8 * 32)()
    app_out, wallet_out, app_peer, wallet_peer = [(U8 * 32)() for _ in range(4)]
    derive_keys = api.connect_norito_connect_derive_keys
    derive_keys.argtypes = [PTR, PTR, PTR, PTR, PTR]
    derive_keys.restype = c.c_int32

    def blob(function, *arguments):
        output, size = PTR(), UL()
        code = function(*arguments, c.byref(output), c.byref(size))
        try:
            if code or not output or not 0 < size.value <= 1024 * 1024:
                raise RuntimeError('Native envelope construction failed.')
            return c.string_at(output, size.value)
        finally:
            if output:
                api.connect_norito_free(output)

    def array(data):
        return (U8 * len(data)).from_buffer_copy(data)

    try:
        if api.connect_norito_connect_generate_keypair(wallet_public, wallet_private):
            raise RuntimeError('Native wallet-side ephemeral key generation failed.')
        if derive_keys(app_private, wallet_public, sid, app_out, wallet_out) or derive_keys(wallet_private, app_public, sid, app_peer, wallet_peer):
            raise RuntimeError('Native direction-key derivation failed.')
        if bytes(app_out) != bytes(app_peer) or bytes(wallet_out) != bytes(wallet_peer) or bytes(app_out) == bytes(wallet_out):
            raise RuntimeError('Native peer/direction key binding failed.')
        encode = api.connect_norito_encode_envelope_sign_request_tx
        encode.argtypes = [c.c_uint64, PTR, UL, OUT, LEN]
        encode.restype = c.c_int32
        # Opaque test data only: never sent to a wallet or node, never a transaction fixture.
        test_payload = b'local-connect-encryption-smoke-check'
        envelope = blob(encode, 42, array(test_payload), len(test_payload))
        encrypt = api.connect_norito_connect_encrypt_envelope
        encrypt.argtypes = [PTR, PTR, U8, PTR, UL, OUT, LEN]
        encrypt.restype = c.c_int32
        ciphertext = blob(encrypt, app_out, sid, 0, array(envelope), len(envelope))
        decode_frame = api.connect_norito_decode_control_kind
        decode_frame.argtypes = [PTR, UL, PTR, PTR, c.POINTER(c.c_uint64), c.POINTER(c.c_uint16)]
        decode_frame.restype = c.c_int32
        frame_sid, direction, seq, kind = (U8 * 32)(), U8(), c.c_uint64(), c.c_uint16()
        if decode_frame(array(ciphertext), len(ciphertext), frame_sid, c.byref(direction), c.byref(seq), c.byref(kind)) or bytes(frame_sid) != bytes(sid) or direction.value != 0 or seq.value != 42 or kind.value != 100:
            raise RuntimeError('Ciphertext frame identity, direction, or sequence mismatch.')
        decrypt = api.connect_norito_connect_decrypt_ciphertext
        decrypt.argtypes = [PTR, PTR, UL, OUT, LEN]
        decrypt.restype = c.c_int32
        if blob(decrypt, app_peer, array(ciphertext), len(ciphertext)) != envelope:
            raise RuntimeError('Native authenticated envelope round trip failed.')
        tampered = bytearray(ciphertext)
        tampered[-1] ^= 1
        for key, wire in [(wallet_peer, ciphertext), (app_peer, bytes(tampered)), (app_peer, ciphertext + b'\x00')]:
            output, size = PTR(), UL()
            result = decrypt(key, array(wire), len(wire), c.byref(output), c.byref(size))
            try:
                if result == 0:
                    raise RuntimeError('Native admission accepted a wrong key, altered ciphertext, or trailing bytes.')
            finally:
                if output:
                    api.connect_norito_free(output)
    finally:
        for secret in (app_private, wallet_private, app_out, wallet_out, app_peer, wallet_peer):
            c.memset(c.addressof(secret), 0, c.sizeof(secret))


def verify_game_builder(api, fixture_path):
    """Inspect public synthetic native fixtures; never authorize or submit them."""
    fixtures = json.loads(fixture_path.read_text())
    vectors = {vector['name']: vector['value'] for vector in fixtures['vectors']}
    authority = vectors['GameAdmissionBodyV1']['participants'][0]['account']
    builder = api.connect_norito_native_transaction_scaffold_build_v1
    builder.argtypes = [PTR, UL, OUT, LEN, OUT, LEN]
    builder.restype = c.c_int32
    inspect = api.connect_norito_detached_transaction_scaffold_inspect_v1
    inspect.argtypes = [PTR, UL, OUT, LEN]
    inspect.restype = c.c_int32
    finalize = api.connect_norito_detached_transaction_scaffold_finalize_ed25519_v1
    finalize.argtypes = [PTR, UL, PTR, UL, PTR, UL, OUT, LEN, OUT, LEN]
    finalize.restype = c.c_int32
    join_inspector = getattr(api, 'connect_norito_arena_join_terms_inspect_v1', None)
    if join_inspector is not None:
        join_inspector.argtypes = [PTR, UL, OUT, LEN]
        join_inspector.restype = c.c_int32

    def array(data):
        return (U8 * len(data)).from_buffer_copy(data)

    def build(request):
        data = json.dumps(request, ensure_ascii=False, separators=(',', ':')).encode()
        scaffold, scaffold_size, review, review_size = PTR(), UL(), PTR(), UL()
        result = builder(array(data), len(data), c.byref(scaffold), c.byref(scaffold_size), c.byref(review), c.byref(review_size))
        try:
            if result:
                return None
            if not scaffold or not review or not 0 < scaffold_size.value <= 1024 * 1024 or not 0 < review_size.value <= 1024 * 1024:
                raise RuntimeError('Builder returned invalid output bounds.')
            return c.string_at(scaffold, scaffold_size.value), c.string_at(review, review_size.value)
        finally:
            if scaffold:
                api.connect_norito_free(scaffold)
            if review:
                api.connect_norito_free(review)

    actions = ['OpenGameSessionV1', 'JoinGameSessionV1', 'ClaimGamePayoutV1']
    rejected = 0
    for action in actions:
        request = {'network_id': fixtures['network_id'], 'authority': authority,
                   'creation_time_ms': 1234, 'time_to_live_ms': 60000,
                   'fee_payment': {'payer': 'authority', 'value': {'charge_limits': [], 'gas_limit': 9000000}},
                   'instruction': {'name': action, 'value': vectors[action]}}
        result = build(request)
        if result is None:
            raise RuntimeError('Native builder rejected canonical ' + action)
        scaffold, raw_review = result
        review = json.loads(raw_review)
        if (review.get('schema') != 'iroha.detached_transaction_scaffold.v1'
                or review.get('authority') != authority or review.get('network_id') != request['network_id']
                or review.get('fee_payment') != request['fee_payment']
                or review.get('executable') != {'kind': 'native_instruction', 'name': action, 'value': vectors[action]}
                or not base64.b64decode(review.get('payload_bytes_b64', ''), validate=True)):
            raise RuntimeError('Native builder changed exact reviewed terms for ' + action)
        reviewed, reviewed_size = PTR(), UL()
        code = inspect(array(scaffold), len(scaffold), c.byref(reviewed), c.byref(reviewed_size))
        try:
            if code or not reviewed or c.string_at(reviewed, reviewed_size.value) != raw_review:
                raise RuntimeError('Native re-inspection changed transaction review.')
        finally:
            if reviewed:
                api.connect_norito_free(reviewed)
        if action == 'JoinGameSessionV1' and join_inspector is not None:
            terms_ptr, terms_len = PTR(), UL()
            code = join_inspector(array(scaffold), len(scaffold), c.byref(terms_ptr), c.byref(terms_len))
            try:
                if code or not terms_ptr or not 0 < terms_len.value <= 128 * 1024:
                    raise RuntimeError('Native Arena Join terms inspection failed.')
                terms = json.loads(c.string_at(terms_ptr, terms_len.value))
                if (terms.get('schema') != 'sora.arena.join_terms_inspection.v1'
                        or terms.get('authorization_ready') is not False
                        or terms.get('verification_scope') != 'canonical_scaffold_only'
                        or terms.get('network_id') != request['network_id']
                        or terms.get('authority') != authority
                        or terms.get('creation_time_ms') != request['creation_time_ms']
                        or terms.get('time_to_live_ms') != request['time_to_live_ms']
                        or terms.get('fee_payment') != request['fee_payment']
                        or terms.get('join') != vectors[action]
                        or terms.get('payload_signing_hash_hex') != review.get('payload_signing_hash_hex')
                        or not re.fullmatch(r'[0-9a-f]{64}', terms.get('scaffold_blake3_hex', ''))):
                    raise RuntimeError('Native Arena Join terms differ from the canonical transaction or claim authorization.')
            finally:
                if terms_ptr:
                    api.connect_norito_free(terms_ptr)
            for malformed in (scaffold + b'\x00', b''):
                rejected_ptr, rejected_len = PTR(), UL()
                code = join_inspector(array(malformed), len(malformed), c.byref(rejected_ptr), c.byref(rejected_len))
                try:
                    if code == 0 or rejected_ptr or rejected_len.value:
                        raise RuntimeError('Native Arena Join inspector accepted a malformed scaffold or returned stale data.')
                finally:
                    if rejected_ptr:
                        api.connect_norito_free(rejected_ptr)
        elif join_inspector is not None:
            rejected_ptr, rejected_len = PTR(), UL()
            code = join_inspector(array(scaffold), len(scaffold), c.byref(rejected_ptr), c.byref(rejected_len))
            try:
                if code == 0 or rejected_ptr or rejected_len.value:
                    raise RuntimeError('Native Arena Join inspector accepted a different game action.')
            finally:
                if rejected_ptr:
                    api.connect_norito_free(rejected_ptr)
        # A placeholder plus zero signature cannot become an authorized transaction.
        signed, signed_size, signed_review, signed_review_size = PTR(), UL(), PTR(), UL()
        code = finalize(array(scaffold), len(scaffold), (U8 * 32)(), 32, (U8 * 64)(), 64,
                        c.byref(signed), c.byref(signed_size), c.byref(signed_review), c.byref(signed_review_size))
        try:
            if code == 0:
                raise RuntimeError('Native finalizer accepted an unauthorized placeholder.')
        finally:
            if signed:
                api.connect_norito_free(signed)
            if signed_review:
                api.connect_norito_free(signed_review)
        for mutation in ('missing_fee', 'extra_field', 'nested_extra', 'missing_nested', 'zero_ttl', 'unsupported', 'batch'):
            bad = copy.deepcopy(request)
            if mutation == 'missing_fee':
                del bad['fee_payment']
            elif mutation == 'extra_field':
                bad['ignored'] = None
            elif mutation == 'nested_extra':
                bad['instruction']['value']['ignored'] = None
            elif mutation == 'missing_nested':
                del bad['instruction']['value']['session_id']
            elif mutation == 'zero_ttl':
                bad['time_to_live_ms'] = 0
            elif mutation == 'unsupported':
                bad['instruction']['name'] = 'SettleGameSessionV1'
            else:
                bad['instruction'] = [bad['instruction']]
            if build(bad) is not None:
                raise RuntimeError('Native builder accepted ' + mutation)
            rejected += 1
    report = {'canonical_actions': actions, 'malformed_requests_rejected': rejected,
              'unauthorized_placeholder_finalization': 'rejected', 'submission': 'never attempted'}
    if join_inspector is not None:
        report['arena_join_terms_inspection'] = 'typed terms matched; authorization false; malformed and non-Join scaffolds rejected'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('library', type=Path)
    parser.add_argument('--game-fixtures', type=Path, help='optional public native game-v1-codec.json fixture file')
    parser.add_argument('--require-arena-join-inspector', action='store_true',
                        help='fail if the native research Join inspector is absent')
    args = parser.parse_args()
    path = args.library.resolve()
    if not path.is_file():
        sys.exit(f'Native Connect bridge missing: {path}. No wallet approval or transaction verification is available.')
    api = c.CDLL(str(path))
    api.connect_norito_bridge_abi_version.restype = c.c_uint32
    api.connect_norito_bridge_abi_version.argtypes = []
    if api.connect_norito_bridge_abi_version() != 23:
        sys.exit('Native bridge ABI mismatch: expected 23; library was not used.')
    source = Path(__file__).resolve().parents[2] / 'Source/SoraArena/Private/ArenaWalletSubsystem.cpp'
    required = re.findall(r'ARENA_BIND\([^,]+, "([^"]+)"\)', source.read_text())
    for name in required:
        getattr(api, name)
    if args.require_arena_join_inspector and not hasattr(api, 'connect_norito_arena_join_terms_inspect_v1'):
        sys.exit('Required Arena Join inspector is absent; library was not staged.')
    if args.require_arena_join_inspector and not args.game_fixtures:
        sys.exit('Arena Join inspector verification requires --game-fixtures.')
    api.connect_norito_free.argtypes = [PTR]
    api.connect_norito_free.restype = None

    keypair = api.connect_norito_connect_generate_keypair
    keypair.argtypes = [PTR, PTR]
    keypair.restype = c.c_int32
    pk, sk = (U8 * 32)(), (U8 * 32)()
    if keypair(pk, sk) != 0 or not any(pk) or not any(sk):
        sys.exit('Native OS-random key generation failed.')
    derive = api.connect_norito_connect_derive_session_id
    derive.argtypes = [PTR, UL, PTR, UL, PTR, UL, PTR, UL]
    derive.restype = c.c_int32
    network = (U8 * 32)(*([0] * 31 + [1]))
    nonce = (U8 * 16)(*range(1, 17))
    sid, changed_sid = (U8 * 32)(), (U8 * 32)()
    if derive(network, 32, pk, 32, nonce, 16, sid, 32) != 0 or not any(sid):
        sys.exit('Native exact-network session ID derivation failed.')
    nonce[0] ^= 1
    if derive(network, 32, pk, 32, nonce, 16, changed_sid, 32) != 0 or bytes(sid) == bytes(changed_sid):
        sys.exit('Session ID failed to bind launch nonce.')
    if derive(network, 31, pk, 32, nonce, 16, changed_sid, 32) == 0:
        sys.exit('Bridge accepted a malformed network identity width.')
    verify_ciphertext(api, pk, sk, sid)

    strict = api.connect_norito_canonical_json_blake3_v1
    strict.argtypes = [PTR, UL, OUT, LEN, PTR, UL]
    strict.restype = c.c_int32
    for data, accepted in [(b'{"a":1}', True), (b'{"a":1,"a":2}', False),
                           (b'{"a":1} trailing', False), (b'{"a":"\xff"}', False)]:
        buf = (U8 * len(data)).from_buffer_copy(data)
        output, size, digest = PTR(), UL(), (U8 * 32)()
        result = strict(buf, len(data), c.byref(output), c.byref(size), digest, 32)
        try:
            if (result == 0) != accepted:
                sys.exit('Native strict JSON admission check failed.')
        finally:
            if output:
                api.connect_norito_free(output)
    report = {'abi': 23, 'library': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'required_symbols': len(required), 'native_smoke_checks': 'passed',
              'encrypted_envelope_roundtrip_and_tamper_rejection': 'passed',
              'live_wallet_pairing': 'not tested', 'native_transaction_builder': hasattr(api, 'connect_norito_native_transaction_scaffold_build_v1'),
              'arena_join_terms_inspector': hasattr(api, 'connect_norito_arena_join_terms_inspect_v1')}
    if args.game_fixtures:
        report['native_game_builder'] = verify_game_builder(api, args.game_fixtures)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
