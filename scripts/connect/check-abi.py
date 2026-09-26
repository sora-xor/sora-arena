#!/usr/bin/env python3
"""Compile-check UE dynamic function-pointer declarations against the actual C headers.

Checks the Connect bridge loader against connect_norito_bridge.h and the arena
kernel loader against arena.h: every loaded symbol's pointer type, that the
kernel loader resolves every ABI 4 export, and every arena.h structure layout
against scripts/unreal/kernel_abi.py. This verifies C type compatibility without
a full Unreal SDK. It does not compile the UObject, run the native library, or
establish wire/runtime interoperability.
"""
import argparse
import ctypes
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def include(path):
    return '#include ' + '"' + str(path.resolve()).replace('\\', '\\\\').replace('"', '\\"') + '"\n'


def syntax_check(compiler, prefix, body):
    with tempfile.TemporaryDirectory(prefix=prefix) as tmp:
        test = Path(tmp) / 'check.cpp'
        test.write_text(body)
        subprocess.run([compiler, '-std=c++17', '-fsyntax-only', str(test)], check=True)


def check_kernel(root, compiler):
    sys.path.insert(0, str(root / 'scripts/unreal'))
    import kernel_abi
    header = root / 'crates/arena-ffi/include/arena.h'
    source = (root / 'Source/SoraArena/Private/ArenaKernelSubsystem.cpp').read_text()
    declarations = source.split('struct FKernelRuntime\n{', 1)[1].split('    ArenaHandle* Practice', 1)[0]
    pairs = [(member, symbol) for member, symbol in re.findall(r'LOAD_KERNEL\((\w+),\s*(\w+)\)', source)
             if symbol.startswith('arena_')]
    exported = set(re.findall(r'^\s*(?:uint32_t|int32_t|void|ArenaHandle\*)\s+(arena_[a-z0-9_]+)\(',
                              header.read_text(), re.MULTILINE))
    loaded = {symbol for _, symbol in pairs}
    if loaded != exported:
        raise SystemExit(f'Unreal kernel loader and arena.h differ: unloaded={sorted(exported - loaded)} unknown={sorted(loaded - exported)}')
    layouts = {
        'ArenaConfig': kernel_abi.Config, 'ArenaParticipant': kernel_abi.Participant,
        'ArenaInput': kernel_abi.Input, 'ArenaSnapshot': kernel_abi.Snapshot,
        'ArenaPlayerSnapshot': kernel_abi.Player, 'ArenaMapInfo': kernel_abi.MapInfo,
        'ArenaMapWall': kernel_abi.MapWall, 'ArenaMapPoint': kernel_abi.MapPoint,
        'ArenaMapHazard': kernel_abi.MapHazard, 'ArenaPlayerPresentation': kernel_abi.Presentation,
        'ArenaWeaponSpec': kernel_abi.Weapon, 'ArenaEvent': kernel_abi.Event,
        'ArenaProjectileSnapshot': kernel_abi.Projectile, 'ArenaEntitySnapshot': kernel_abi.Entity,
        'ArenaObjectiveSnapshot': kernel_abi.Objective,
    }
    body = '#include <cstddef>\n#include <type_traits>\n' + include(header)
    body += 'struct FKernelRuntime {\n' + declarations + '};\n'
    for member, symbol in pairs:
        body += f'static_assert(std::is_same_v<decltype(FKernelRuntime::{member}), decltype(&{symbol})>, "Loader mismatch: {member}");\n'
    body += f'static_assert(ARENA_ABI_VERSION == {kernel_abi.ABI_VERSION}u, "ABI version");\n'
    fields = 0
    for name, host in layouts.items():
        body += f'static_assert(sizeof({name}) == {ctypes.sizeof(host)} && alignof({name}) == {ctypes.alignment(host)}, "{name} size");\n'
        for field, _ in host._fields_:
            body += f'static_assert(offsetof({name}, {field}) == {getattr(host, field).offset}, "{name}.{field}");\n'
            fields += 1
    syntax_check(compiler, 'sora-kernel-abi-', body)
    print(f'Checked {len(pairs)} kernel loader pointer types and {len(layouts)} layouts ({fields} field offsets) against {header.resolve()}')


def check_connect(root, compiler, header):
    source = (root / 'Source/SoraArena/Private/ArenaWalletSubsystem.cpp').read_text()
    declarations = source.split('struct FArenaConnectNative\n{', 1)[1].split('    ~FArenaConnectNative()', 1)[0]
    pairs = re.findall(r'ARENA_BIND\((\w+), "(\w+)"\)', source)
    pairs += [('Abi', 'connect_norito_bridge_abi_version'),
              ('BuildTransaction', 'connect_norito_native_transaction_scaffold_build_v1'),
              ('JoinTermsInspect', 'connect_norito_arena_join_terms_inspect_v1')]
    body = '#include <cstdint>\n#include <type_traits>\n' + include(header)
    for bits in (8, 16, 32, 64):
        body += f'using uint{bits} = std::uint{bits}_t;\n'
    body += 'using int32 = std::int32_t;\nstruct FDeclarations {\n' + declarations + '\n};\n'
    for field, symbol in pairs:
        body += f'static_assert(std::is_same_v<decltype(FDeclarations::{field}), decltype(&{symbol})>, "ABI mismatch: {field}");\n'
    syntax_check(compiler, 'sora-connect-abi-', body)
    print(f'Checked {len(pairs)} dynamic function-pointer types against {header.resolve()}')


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--header', type=Path, default=root.parent / 'iroha-arena/crates/connect_norito_bridge/include/connect_norito_bridge.h')
    parser.add_argument('--compiler', default=os.environ.get('CXX', 'clang++'))
    args = parser.parse_args()
    check_kernel(root, args.compiler)
    check_connect(root, args.compiler, args.header)


if __name__ == '__main__':
    main()
