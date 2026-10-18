#!/usr/bin/env python3
"""Fail closed on the isolated rendered startup report, log and untouched frame."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import struct
import sys
import zlib

TEST = 'SoraStartup.RenderedFreshLaunch'
MARKER = 'SORA_FRESH_STARTUP title=1 menu=1 focus=SSoraFrontEnd catalog=1 arena=1 paused=1 rendered=1'


def frame_size(frame):
    data = frame.read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('startup frame is not a PNG')
    at, size, image, ended, row_bytes = 8, None, bytearray(), False, 0
    while at + 12 <= len(data):
        length = struct.unpack('>I', data[at:at+4])[0]
        kind = data[at+4:at+8]
        payload = data[at+8:at+8+length]
        crc = data[at+8+length:at+12+length]
        if len(crc) != 4 or struct.unpack('>I', crc)[0] != zlib.crc32(kind + payload):
            raise ValueError('startup PNG is truncated or has a bad chunk CRC')
        if kind == b'IHDR':
            if length != 13 or size is not None:
                raise ValueError('startup PNG has an invalid header')
            width, height, bits, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color, 0)
            if not width or not height or bits not in (1, 2, 4, 8, 16) or not channels or compression or filtering or interlace:
                raise ValueError('startup PNG has unsupported image encoding')
            size = width, height
            row_bytes = (width * channels * bits + 7) // 8
        elif kind == b'IDAT':
            image.extend(payload)
        elif kind == b'IEND':
            ended = True
            break
        at += length + 12
    if not ended or not size or not image:
        raise ValueError('startup PNG has no complete image data')
    decoder = zlib.decompressobj()
    pixels = decoder.decompress(image) + decoder.flush()
    stride = row_bytes + 1
    if (not decoder.eof or decoder.unused_data or len(pixels) != stride * size[1]
            or any(pixels[row * stride] > 4 for row in range(size[1]))):
        raise ValueError('startup PNG scanlines are incomplete or invalid')
    return size


def problems(report, log, status, frame, width, height):
    issues = []
    if status:
        issues.append(f'fresh startup exited {status}')
    tests = report.get('tests', [])
    if len(tests) != 1 or tests[0].get('fullTestPath') != TEST:
        issues.append('fresh startup did not run exactly its one dedicated test')
    found = re.findall(r"Found (\d+) automation tests based on '([^']*)'", log)
    if found != [('1', TEST)]:
        issues.append('fresh startup discovery is not the isolated exact selection')
    if any(report.get(key, 0) for key in ('failed', 'notRun', 'inProcess')):
        issues.append('fresh startup report contains failed or unfinished work')
    for test in tests:
        events = [entry.get('event', {}) for entry in test.get('entries', [])]
        if (test.get('state') != 'Success' or test.get('errors', 0) or test.get('warnings', 0)
                or any(event.get('type') in ('Error', 'Warning') for event in events)):
            issues.append('fresh startup did not pass without errors or warnings')
        expected = f'{MARKER} width={width} height={height}'
        if sum(event.get('message') == expected for event in events) != 1:
            issues.append('fresh startup lacks its unmodified Title/focus/rendered-state evidence')
    if re.search(r'Fatal error|=== Critical error|Assertion failed|Ensure condition failed|LogOutputDevice: Error', log):
        issues.append('fresh startup logged a fatal, assertion or ensure')
    try:
        if frame_size(frame) != (width, height):
            issues.append('untouched startup frame has the wrong dimensions')
    except (OSError, ValueError, zlib.error) as error:
        issues.append(f'untouched startup frame is invalid: {error}')
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path); parser.add_argument('log', type=Path)
    parser.add_argument('status', type=int); parser.add_argument('frame', type=Path)
    parser.add_argument('width', type=int); parser.add_argument('height', type=int)
    args = parser.parse_args()
    try:
        issues = problems(json.loads(args.report.read_text(encoding='utf-8-sig')),
            args.log.read_text(errors='replace'), args.status, args.frame, args.width, args.height)
        if issues:
            raise ValueError('; '.join(issues))
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f'FAIL rendered fresh startup: {error}', file=sys.stderr)
        return 1
    print(f'PASS rendered fresh startup: untouched Title and Slate focus; frame {args.frame}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
