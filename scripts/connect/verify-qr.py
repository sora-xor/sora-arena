#!/usr/bin/env python3
"""Compile the vendored C encoder and decode synthetic QR images with macOS Vision.

All payloads are synthetic and local. No wallet URI is accepted on the command
line, no network request is made, and temporary images are removed on exit.
This does not test the Unreal renderer or a live wallet.
"""
import ctypes as c
import hashlib
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import tempfile
from urllib.parse import urlencode
import zlib


def png(data, width):
    def chunk(kind, payload):
        return struct.pack('!I', len(payload)) + kind + payload + struct.pack('!I', zlib.crc32(kind + payload))
    rows = b''.join(b'\0' + data[y * width:(y + 1) * width] for y in range(width))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', width, width, 8, 0, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


def main():
    if platform.system() != 'Darwin':
        raise SystemExit('This independent QR decoder check uses macOS Vision; run it on a Mac with Xcode.')
    root = Path(__file__).resolve().parents[2]
    vendor = root / 'Source/SoraArena/Private/ThirdParty/QrCodeGen'
    manifest = json.loads((vendor / 'upstream.json').read_text())
    for name, metadata in manifest['files'].items():
        if hashlib.sha256((vendor / name).read_bytes()).hexdigest() != metadata['sha256']:
            raise SystemExit('Vendored QR encoder differs from the recorded upstream hash.')
    build_env = dict(os.environ)
    if not build_env.get('DEVELOPER_DIR'):
        candidates = [Path.home() / 'Applications/SORAToolchain/Xcode_26.1.1.app/Contents/Developer',
                      Path('/Applications/Xcode_26.1.1.app/Contents/Developer'), Path('/Applications/Xcode.app/Contents/Developer')]
        build_env['DEVELOPER_DIR'] = str(next(p for p in candidates if p.is_dir()))
    sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], env=build_env, text=True).strip()
    build_env['SDKROOT'] = sdk
    with tempfile.TemporaryDirectory(prefix='sora-qr-verify-') as directory:
        temp = Path(directory)
        library = temp / 'qrcodegen.dylib'
        subprocess.run(['xcrun', 'clang', '-isysroot', sdk, '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror', '-dynamiclib',
                        str(vendor / 'qrcodegen.c'), '-o', str(library)], env=build_env, check=True)
        api = c.CDLL(str(library))
        byte = c.c_uint8
        pointer = c.POINTER(byte)
        api.qrcodegen_encodeText.argtypes = [c.c_char_p, pointer, pointer, c.c_int, c.c_int, c.c_int, c.c_int, c.c_bool]
        api.qrcodegen_encodeText.restype = c.c_bool
        api.qrcodegen_getSize.argtypes = [pointer]
        api.qrcodegen_getSize.restype = c.c_int
        api.qrcodegen_getModule.argtypes = [pointer, c.c_int, c.c_int]
        api.qrcodegen_getModule.restype = c.c_bool
        # Deliberately public synthetic values; no real network or bearer tokens.
        fields = {'sid': 'A' * 43, 'network_id': 'hash:' + '0' * 63 + '1#C50E',
                  'app_pk': 'B' * 43, 'nonce': 'C' * 22, 'node': 'https://torii.example',
                  'v': '1', 'role': 'wallet', 'token': 'D' * 43, 'relay': 'E' * 43}
        normal = 'iroha://connect?' + urlencode(fields)
        fields['node'] = 'https://' + ('long-hostname-' * 14) + '.example:443'
        long_uri = 'iroha://connect?' + urlencode(fields)
        fixtures = [normal, long_uri, 'iroha://connect?' + urlencode({'name': '猫柳生', 'node': 'https://torii.example'})]
        cases = []
        for index, text in enumerate(fixtures):
            scratch, code = (byte * 3918)(), (byte * 3918)()
            if not api.qrcodegen_encodeText(text.encode(), scratch, code, 1, 1, 40, -1, True):
                raise SystemExit('QR encoder rejected a supported fixture.')
            modules = api.qrcodegen_getSize(code)
            # Same four-module quiet zone and nearest-neighbor layout as the UE texture.
            scale, border = 3, 4
            side = (modules + border * 2) * scale
            pixels = bytearray([255]) * (side * side)
            for y in range(modules):
                for x in range(modules):
                    if api.qrcodegen_getModule(code, x, y):
                        for dy in range(scale):
                            offset = ((y + border) * scale + dy) * side + (x + border) * scale
                            pixels[offset:offset + scale] = bytes(scale)
            image = temp / f'fixture-{index}.png'
            image.write_bytes(png(pixels, side))
            cases.append({'path': str(image), 'text': text})
        case_file = temp / 'cases.json'
        case_file.write_text(json.dumps(cases))
        swift = temp / 'decode.swift'
        swift.write_text('''import Foundation
import Vision
struct Fixture: Decodable { let path: String; let text: String }
let cases = try JSONDecoder().decode([Fixture].self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
for (index, fixture) in cases.enumerated() {
    let request = VNDetectBarcodesRequest()
    request.symbologies = [.qr]
    try VNImageRequestHandler(url: URL(fileURLWithPath: fixture.path)).perform([request])
    let values = (request.results ?? []).compactMap { $0.payloadStringValue }
    guard values == [fixture.text] else {
        fputs("Independent Vision decoder did not reproduce fixture \\(index) exactly.\\n", stderr)
        exit(1)
    }
}
print("Independent Vision decoder recovered all \\(cases.count) local QR fixtures exactly.")
''')
        subprocess.run(['xcrun', 'swift', '-sdk', sdk, '-module-cache-path', str(temp / 'module-cache'), str(swift), str(case_file)], env=build_env, check=True)
    print('QR encoder source hashes and strict C99 compile passed; Unreal display and live wallet scan remain unverified.')


if __name__ == '__main__':
    main()
