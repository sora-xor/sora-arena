#!/usr/bin/env python3
"""Compile-check UE dynamic function-pointer declarations against the actual C header.

This verifies C type compatibility without a full Unreal SDK. It does not compile
the UObject, run the native library, or establish wire/runtime interoperability.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--header', type=Path, default=root.parent / 'iroha-arena/crates/connect_norito_bridge/include/connect_norito_bridge.h')
    parser.add_argument('--compiler', default=os.environ.get('CXX', 'clang++'))
    args = parser.parse_args()
    source = (root / 'Source/SoraArena/Private/ArenaWalletSubsystem.cpp').read_text()
    declarations = source.split('struct FArenaConnectNative\n{', 1)[1].split('    ~FArenaConnectNative()', 1)[0]
    pairs = re.findall(r'ARENA_BIND\((\w+), "(\w+)"\)', source)
    pairs += [('Abi', 'connect_norito_bridge_abi_version'),
              ('BuildTransaction', 'connect_norito_native_transaction_scaffold_build_v1')]
    body = '#include <cstdint>\n#include <type_traits>\n'
    body += '#include ' + '"' + str(args.header.resolve()).replace('\\', '\\\\').replace('"', '\\"') + '"\n'
    for bits in (8, 16, 32, 64):
        body += f'using uint{bits} = std::uint{bits}_t;\n'
    body += 'using int32 = std::int32_t;\nstruct FDeclarations {\n' + declarations + '\n};\n'
    for field, symbol in pairs:
        body += f'static_assert(std::is_same_v<decltype(FDeclarations::{field}), decltype(&{symbol})>, "ABI mismatch: {field}");\n'
    with tempfile.TemporaryDirectory(prefix='sora-connect-abi-') as tmp:
        test = Path(tmp) / 'check.cpp'
        test.write_text(body)
        subprocess.run([args.compiler, '-std=c++17', '-fsyntax-only', str(test)], check=True)
    print(f'Checked {len(pairs)} dynamic function-pointer types against {args.header.resolve()}')


if __name__ == '__main__':
    main()
