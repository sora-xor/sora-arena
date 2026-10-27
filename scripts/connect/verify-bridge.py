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


ACTIONS = ('OpenGameSessionV1', 'JoinGameSessionV1', 'ClaimGamePayoutV1',
           'StakeGameItemV1', 'OfferNftV1', 'BuyNftV1', 'CancelNftOfferV1')
ABI_VERSION = 30


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def fixture_cases(directory):
    """Use complete native vectors, including marketplace and returnable resources."""
    files = {name: directory / (name + '.json') for name in
             ('game-v1-codec', 'nft-market-v1-codec', 'game-resource-v1-codec')}
    contents = {name: path.read_bytes() for name, path in files.items()}
    fixtures = {name: json.loads(data) for name, data in contents.items()}

    def vector(family, name, unique=True):
        found = [item['value'] for item in fixtures[family]['vectors'] if item['name'] == name]
        if not found or (unique and len(found) != 1):
            raise RuntimeError(f'Expected an unambiguous {name} in {files[family]}')
        return found[0]

    game_authority = vector('game-v1-codec', 'GameAdmissionBodyV1', False)['participants'][0]['account']
    offer = vector('nft-market-v1-codec', 'BuyNftV1')['offer']
    owner = vector('game-resource-v1-codec', 'GameResourceReservationRecordV1', False)['original_owner']
    cases = []
    for action in ACTIONS:
        family = 'game-v1-codec' if action in ACTIONS[:4] else 'nft-market-v1-codec'
        value = vector(family, action)
        network = fixtures[family]['network_id'] if family == 'game-v1-codec' else offer['network_id']
        authority = game_authority if family == 'game-v1-codec' else (
            offer['reserved_buyer'] if action == 'BuyNftV1' else offer['seller'])
        asset = vector('game-v1-codec', 'OpenGameSessionV1')['asset_definition']
        cases.append((action, family, network, authority, asset, action, value))
    resource = vector('game-resource-v1-codec', 'JoinGameSessionV1')
    if not resource['resources'] or any(item['policy'] != {
            'kind': 'return_to_original_owner_at_terminal', 'value': None} for item in resource['resources']):
        raise RuntimeError('Resource fixture must contain returnable equipment reservations.')
    cases.append(('JoinGameSessionV1.returnable_resources', 'game-resource-v1-codec',
                  fixtures['game-resource-v1-codec']['network_id'], owner,
                  resource['expected_asset_definition'], 'JoinGameSessionV1', resource))
    requests = []
    for label, family, network, authority, asset, action, value in cases:
        # Deliberately above IEEE-754's exact integer range and with a fractional part.
        # No native quantity or payment value may be routed through a float.
        fee = {'payer': 'authority', 'value': {'charge_limits': [
            {'kind': {'kind': 'nexus', 'value': None}, 'asset_definition_id': asset,
             'max_amount': '9007199254740993.125'}], 'gas_limit': 9000000}}
        requests.append((label, family, {'network_id': network, 'authority': authority,
                        'creation_time_ms': 1234, 'time_to_live_ms': 60000, 'fee_payment': fee,
                        'instruction': {'name': action, 'value': value}}))
    return requests, {name: {'path': str(path.resolve()),
                             'sha256': hashlib.sha256(contents[name]).hexdigest()}
                      for name, path in files.items()}


def malformed_requests(request):
    """Remove each required top-level/action term and corrupt typed nested terms."""
    def changed(path, value=None, remove=False):
        bad = copy.deepcopy(request)
        parent = bad
        for key in path[:-1]:
            parent = parent[key]
        if remove:
            del parent[path[-1]]
        else:
            parent[path[-1]] = value
        return bad

    for key in request:
        yield 'missing.' + key, changed([key], remove=True)
    for key in ('name', 'value'):
        yield 'missing.instruction.' + key, changed(['instruction', key], remove=True)
    for key in request['instruction']['value']:
        yield 'missing.instruction.value.' + key, changed(['instruction', 'value', key], remove=True)
    for label, path, value in (
            ('extra_request', ['ignored'], None),
            ('extra_instruction', ['instruction', 'ignored'], None),
            ('extra_value', ['instruction', 'value', 'ignored'], None),
            ('malformed_value', ['instruction', 'value'], []),
            ('malformed_authority', ['authority'], 'not-an-account'),
            ('malformed_network', ['network_id'], 'not-a-network'),
            ('malformed_fee', ['fee_payment'], {}),
            ('extra_fee', ['fee_payment', 'value', 'ignored'], None),
            ('fee_quantity_number', ['fee_payment', 'value', 'charge_limits', 0, 'max_amount'], 9007199254740993),
            ('zero_ttl', ['time_to_live_ms'], 0),
            ('negative_creation_time', ['creation_time_ms'], -1),
            ('unsupported_action', ['instruction', 'name'], 'SettleGameSessionV1'),
            ('batch', ['instruction'], [request['instruction']])):
        yield label, changed(path, value)
    for key in ('charge_limits', 'gas_limit'):
        yield 'missing.fee.' + key, changed(['fee_payment', 'value', key], remove=True)
    for key in ('kind', 'asset_definition_id', 'max_amount'):
        yield 'missing.fee.charge.' + key, changed(['fee_payment', 'value', 'charge_limits', 0, key], remove=True)

    def nested_terms(value, path):
        for key, child in value.items():
            if key in ('stake', 'expected_stake', 'amount', 'price'):
                if not isinstance(child, str):
                    raise RuntimeError('Native quantity fixture is not a string: ' + '.'.join(map(str, path + [key])))
                yield 'numeric.' + '.'.join(map(str, path + [key])), changed(path + [key], 1)
            if isinstance(child, dict):
                for required in child:
                    yield 'missing.' + '.'.join(map(str, path + [key, required])), changed(path + [key, required], remove=True)
                yield from nested_terms(child, path + [key])
            elif isinstance(child, list):
                for index, item in enumerate(child):
                    if isinstance(item, dict):
                        for required in item:
                            yield 'missing.' + '.'.join(map(str, path + [key, index, required])), changed(path + [key, index, required], remove=True)
                        yield from nested_terms(item, path + [key, index])
    yield from nested_terms(request['instruction']['value'], ['instruction', 'value'])


def verify_game_builder(api, fixture_directory):
    """Exercise all seven native builders; no wallet, signing key, node or submission."""
    requests, fixtures = fixture_cases(fixture_directory)
    builder = api.connect_norito_native_transaction_scaffold_build_v1
    builder.argtypes, builder.restype = [PTR, UL, OUT, LEN, OUT, LEN], c.c_int32
    inspect = api.connect_norito_detached_transaction_scaffold_inspect_v1
    inspect.argtypes, inspect.restype = [PTR, UL, OUT, LEN], c.c_int32
    finalize = api.connect_norito_detached_transaction_scaffold_finalize_ed25519_v1
    finalize.argtypes, finalize.restype = [PTR, UL, PTR, UL, PTR, UL, OUT, LEN, OUT, LEN], c.c_int32
    join_inspector = api.connect_norito_arena_join_terms_inspect_v1
    join_inspector.argtypes, join_inspector.restype = [PTR, UL, OUT, LEN], c.c_int32
    digest = api.connect_norito_blake3_hash
    digest.argtypes, digest.restype = [PTR, UL, OUT, LEN], c.c_int32

    def array(data):
        return (U8 * len(data)).from_buffer_copy(data)

    def blob(function, data, reject=False):
        output, size = PTR(), UL()
        code = function(array(data), len(data), c.byref(output), c.byref(size))
        try:
            if reject:
                if code == 0 or output or size.value:
                    raise RuntimeError('Native inspection accepted invalid input or returned stale outputs.')
                return None
            if code or not output or not 0 < size.value <= 1024 * 1024:
                raise RuntimeError('Native inspection failed or returned invalid output bounds.')
            return c.string_at(output, size.value)
        finally:
            if output:
                api.connect_norito_free(output)

    def build(request):
        data = json_bytes(request)
        scaffold, scaffold_size, review, review_size = PTR(), UL(), PTR(), UL()
        code = builder(array(data), len(data), c.byref(scaffold), c.byref(scaffold_size), c.byref(review), c.byref(review_size))
        try:
            if code:
                if scaffold or scaffold_size.value or review or review_size.value:
                    raise RuntimeError('Native builder returned stale outputs on rejection.')
                return None
            if not scaffold or not review or not 0 < scaffold_size.value <= 1024 * 1024 or not 0 < review_size.value <= 1024 * 1024:
                raise RuntimeError('Native builder returned invalid output bounds.')
            return c.string_at(scaffold, scaffold_size.value), c.string_at(review, review_size.value)
        finally:
            if scaffold:
                api.connect_norito_free(scaffold)
            if review:
                api.connect_norito_free(review)

    def exact_review(request, raw_review):
        review = json.loads(raw_review)
        expected = {key: request[key] for key in ('network_id', 'authority', 'creation_time_ms', 'time_to_live_ms', 'fee_payment')}
        expected['schema'] = 'iroha.detached_transaction_scaffold.v1'
        expected['executable'] = {'kind': 'native_instruction', **request['instruction']}
        if any(json_bytes(review.get(key)) != json_bytes(value) for key, value in expected.items()):
            raise RuntimeError('Native builder changed exact typed terms for ' + request['instruction']['name'])
        payload = base64.b64decode(review.get('payload_bytes_b64', ''), validate=True)
        if not payload or not re.fullmatch(r'[0-9a-f]{64}', review.get('payload_signing_hash_hex', '')):
            raise RuntimeError('Native builder omitted the canonical signing payload or hash.')
        return review, payload

    results = []
    for label, family, request in requests:
        action = request['instruction']['name']
        built = build(request)
        if built is None:
            raise RuntimeError('Native builder rejected canonical ' + label)
        scaffold, raw_review = built
        review, payload = exact_review(request, raw_review)
        if blob(inspect, scaffold) != raw_review:
            raise RuntimeError('Native re-inspection changed the exact transaction review for ' + label)
        for malformed in (b'', scaffold + b'\x00', scaffold[:-1]):
            blob(inspect, malformed, reject=True)
            blob(join_inspector, malformed, reject=True)
        if action == 'JoinGameSessionV1':
            terms = json.loads(blob(join_inspector, scaffold))
            expected = {'schema': 'sora.arena.join_terms_inspection.v1', 'authorization_ready': False,
                        'verification_scope': 'canonical_scaffold_only',
                        'scaffold_blake3_hex': blob(digest, scaffold).hex(),
                        'payload_signing_hash_hex': review['payload_signing_hash_hex'],
                        'join': request['instruction']['value']}
            expected.update({key: request[key] for key in ('network_id', 'authority', 'creation_time_ms', 'time_to_live_ms', 'fee_payment')})
            # Exact field set and types, including false rather than a truthy/falsy substitute.
            if json_bytes(terms) != json_bytes(expected):
                raise RuntimeError('Join inspection changed typed terms, digest, scope, or authorization for ' + label)
        else:
            blob(join_inspector, scaffold, reject=True)
        # A placeholder with an all-zero public key and signature must never authorize.
        signed, signed_size, signed_review, signed_review_size = PTR(), UL(), PTR(), UL()
        code = finalize(array(scaffold), len(scaffold), (U8 * 32)(), 32, (U8 * 64)(), 64,
                        c.byref(signed), c.byref(signed_size), c.byref(signed_review), c.byref(signed_review_size))
        try:
            if code == 0 or signed or signed_size.value or signed_review or signed_review_size.value:
                raise RuntimeError('Native finalizer authorized a placeholder or returned stale outputs for ' + label)
        finally:
            if signed:
                api.connect_norito_free(signed)
            if signed_review:
                api.connect_norito_free(signed_review)
        rejected = []
        for mutation, bad in malformed_requests(request):
            if build(bad) is not None:
                raise RuntimeError(f'Native builder accepted {label}: {mutation}')
            rejected.append(mutation)
        # Prove the nonempty, exact-string fee cap is in the signing payload.
        revised = copy.deepcopy(request)
        revised['fee_payment']['value']['charge_limits'][0]['max_amount'] = '9007199254740993.126'
        changed = build(revised)
        if changed is None:
            raise RuntimeError('Native builder rejected the changed fee-cap binding probe.')
        changed_review, changed_payload = exact_review(revised, changed[1])
        if (changed_payload == payload or changed_review['payload_signing_hash_hex'] == review['payload_signing_hash_hex']
                or blob(inspect, changed[0]) != changed[1]):
            raise RuntimeError('The fee cap is not bound to the canonical signing payload.')
        results.append({'case': label, 'fixture': family, 'action': action,
                        'scaffold_sha256': hashlib.sha256(scaffold).hexdigest(),
                        'payload_signing_hash_hex': review['payload_signing_hash_hex'],
                        'malformed_requests_rejected': rejected})
    return {'canonical_actions': list(ACTIONS), 'canonical_cases': len(results), 'fixtures': fixtures,
            'cases': results, 'malformed_requests_rejected': sum(len(case['malformed_requests_rejected']) for case in results),
            'exact_string_quantities_and_fee_cap_payload_binding': 'passed',
            'unauthorized_placeholder_finalization': 'rejected for all cases with empty outputs',
            'arena_join_terms_inspection': 'exact eleven fields and digest matched for both Joins; authorization false; malformed and all non-Join scaffolds rejected',
            'submission': 'never attempted'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('library', type=Path)
    parser.add_argument('--fixture-dir', required=True, type=Path,
                        help='native fixtures directory containing game, NFT market, and resource codec JSON')
    args = parser.parse_args()
    path = args.library.resolve()
    if not path.is_file():
        sys.exit(f'Native Connect bridge missing: {path}. No wallet approval or transaction verification is available.')
    library_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    api = c.CDLL(str(path))
    api.connect_norito_bridge_abi_version.restype = c.c_uint32
    api.connect_norito_bridge_abi_version.argtypes = []
    if api.connect_norito_bridge_abi_version() != ABI_VERSION:
        sys.exit('Native bridge ABI mismatch: expected 30; library was not used.')
    source = Path(__file__).resolve().parents[2] / 'Source/SoraArena/Private/ArenaWalletSubsystem.cpp'
    if not re.search(r'constexpr uint32 BridgeAbi = 30;', source.read_text()):
        sys.exit('Verifier and Unreal loader disagree on the required ABI.')
    required = ['connect_norito_bridge_abi_version'] + re.findall(r'ARENA_BIND\([^,]+, "([^"]+)"\)', source.read_text())
    required += ['connect_norito_native_transaction_scaffold_build_v1', 'connect_norito_arena_join_terms_inspect_v1']
    if len(required) != 26 or len(set(required)) != 26:
        sys.exit('Expected exactly 26 distinct Connect loader declarations; update ABI verification explicitly.')
    for name in required:
        getattr(api, name)
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
    nonce[0] ^= 1
    for field, label in ((network, 'network'), (pk, 'ephemeral public key')):
        field[0] ^= 1
        changed = derive(network, 32, pk, 32, nonce, 16, changed_sid, 32)
        field[0] ^= 1
        if changed != 0 or bytes(sid) == bytes(changed_sid):
            sys.exit('Session ID failed to bind the exact ' + label + '.')
    for widths in ((31, 32, 16, 32), (32, 31, 16, 32), (32, 32, 15, 32), (32, 32, 16, 31)):
        if derive(network, widths[0], pk, widths[1], nonce, widths[2], changed_sid, widths[3]) == 0:
            sys.exit('Bridge accepted a malformed session identity field width.')
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
    report = {'abi': ABI_VERSION, 'library': str(path), 'sha256': library_hash,
              'required_symbols': len(required), 'native_smoke_checks': 'passed',
              'encrypted_envelope_roundtrip_and_tamper_rejection': 'passed',
              'live_wallet_pairing': 'not tested', 'native_transaction_builder': hasattr(api, 'connect_norito_native_transaction_scaffold_build_v1'),
              'arena_join_terms_inspector': hasattr(api, 'connect_norito_arena_join_terms_inspect_v1')}
    report['native_game_builder'] = verify_game_builder(api, args.fixture_dir.resolve())
    if hashlib.sha256(path.read_bytes()).hexdigest() != library_hash:
        sys.exit('Native library changed during verification; no result is valid for staging.')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
