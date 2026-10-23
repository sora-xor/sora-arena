#!/usr/bin/env python3
"""Bind the existing Mac build/cook/stage wrappers to one declared candidate.

These are local provenance receipts, not release signatures or live-network
qualification. Never rewrite the native bridge builder's original sidecar.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[2]
RECEIPTS = Path('Saved/Qualification/MacArtifacts')
BRIDGE = Path('Binaries/Mac/libconnect_norito_bridge.dylib')
SIDECAR = Path(str(BRIDGE) + '.build.json')
KERNEL = Path('Binaries/Mac/libarena_ffi.dylib')
CONSUMERS = ('scripts/connect/check-abi.py', 'scripts/connect/verify-bridge.py',
             'scripts/unreal/kernel_abi.py', 'crates/arena-ffi/include/arena.h',
             'Source/SoraArena/Private/ArenaKernelSubsystem.cpp', 'Source/SoraArena/Private/ArenaWalletSubsystem.cpp')
ALLOWED_CONSUMERS = set(CONSUMERS) | {'scripts/connect/build-bridge.sh'}
SCHEMA = 'sora.mac.artifact.v1'
CANDIDATE = 'sora.mac.package_candidate.v1'
STAGE_CRYPTO = 'Saved/Cooked/Mac/SoraArena/Metadata/Crypto.json'
NON_UFS = ['Content/Data', 'Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf',
           'Content/SourceArt/Fonts/OFL.txt', 'ThirdPartyNotices',
           'crates/arena-core/data/arena-map-v1.json']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def executable_code(path):
    # CodeSign changes the Mach-O signature when UAT adds the resource seal.
    # Compare copies after Apple's tool removes only that signature; never
    # modify the built or staged executable to obtain its identity.
    with tempfile.TemporaryDirectory(prefix='sora-code-identity-') as directory:
        copy = Path(directory) / path.name
        shutil.copyfile(path, copy)
        subprocess.run(['/usr/bin/codesign', '--remove-signature', str(copy)],
                       check=True, capture_output=True)
        return digest(copy)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    temp.replace(path)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def source(root):
    require(not git(root, 'status', '--porcelain=v1', '--untracked-files=all'),
            'Candidate source must be clean and committed, including untracked files.')
    return {'commit': git(root, 'rev-parse', 'HEAD'), 'tree': git(root, 'rev-parse', 'HEAD^{tree}')}


def revision(value):
    require(re.fullmatch('[0-9a-f]{40}', value or ''), 'Declare the full 40-character source and native commit IDs.')
    return value


def files(root, names):
    """Hash actual bytes and internal symlink identities, including cooked data."""
    result = {}
    for name in names:
        start = root / name
        require(start.exists(), f'Missing artifact: {start}')
        paths = [start] if not start.is_dir() else sorted(start.rglob('*'))
        require(paths, f'Empty artifact directory: {start}')
        for path in paths:
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                # Bundled frameworks have internal version links. External links
                # would bind only a path, not a self-contained candidate.
                boundary = start.resolve() if start.is_dir() else root.resolve()
                require(path.resolve().is_relative_to(boundary), f'External artifact symlink: {path}')
                result[relative] = {'link': os.readlink(path)}
                if path.is_file():
                    result[relative].update(sha256=digest(path), bytes=path.stat().st_size)
            elif path.is_file():
                result[relative] = {'sha256': digest(path), 'bytes': path.stat().st_size}
    return result


def native(root):
    manifest = read(root / SIDECAR)
    sha = digest(root / BRIDGE)
    smoke = manifest.get('native_smoke', {})
    builder = smoke.get('native_game_builder', {})
    require(manifest.get('schema') == 'sora.connect.bridge_build.v2' and manifest.get('platform') == 'Mac'
            and manifest.get('source_status') == 'clean', 'Bridge lacks a clean Mac source-bound build sidecar.')
    revision(manifest.get('source_revision'))
    revision(manifest.get('source_tree'))
    require(manifest.get('library_sha256') == sha == smoke.get('sha256'), 'Bridge bytes do not match the original native build evidence.')
    require(smoke.get('abi') == 30 and smoke.get('required_symbols') == 26
            and builder.get('canonical_cases') == 8 and len(builder.get('canonical_actions', [])) == 7
            and smoke.get('arena_join_terms_inspector')
            and 'Checked 26 dynamic function-pointer types ' in manifest.get('abi_check', ''),
            'Bridge evidence lacks the required ABI 30 bindings, research builder or Join inspector.')
    return {'commit': manifest['source_revision'], 'tree': manifest['source_tree'],
            'library_sha256': sha, 'sidecar_sha256': digest(root / SIDECAR)}


def build_inputs(root):
    bridge = native(root)
    evidence = read(root / SIDECAR)
    # A changed consumer needs a fresh verification from build-bridge.sh; do
    # not silently amend an older producer's original evidence.
    checks = evidence.get('consumer_checks_sha256', {})
    require(isinstance(checks, dict) and set(CONSUMERS) <= set(checks) <= ALLOWED_CONSUMERS,
            'Bridge sidecar lacks required Connect/kernel consumer checks or names an unsupported consumer.')
    require(all(expected == digest(root / name) for name, expected in checks.items()),
            'Bridge consumer files differ from its verification sidecar; rerun native verification/staging.')
    return {'native': bridge, 'kernel_sha256': digest(root / KERNEL), 'config': files(root, ['Config'])}


def artifact_paths(phase):
    if phase == 'editor':
        return ['Binaries/Mac/libUnrealEditor-SoraArena.dylib', 'Binaries/Mac/SoraArenaEditor.target',
                'Binaries/Mac/UnrealEditor.modules']
    if phase == 'game':
        return ['Binaries/Mac/SoraArena.app', 'Binaries/Mac/SoraArena.target']
    return ['Saved/Cooked/Mac']


def receipt(root, phase, *, staging=False):
    value = read(root / RECEIPTS / f'{phase}.json')
    require(value.get('schema') == SCHEMA and value.get('phase') == phase, f'Invalid {phase} receipt.')
    require(value['source'] == source(root), f'{phase} receipt belongs to another source; rerun its wrapper.')
    require(value['inputs'] == inputs(root, phase), f'{phase} inputs changed; rerun its wrapper.')
    actual = files(root, artifact_paths(phase))
    # UE 5.8.3 CreatePaks writes this settings cache into the cook metadata
    # directory immediately before UnrealPak (CopyBuildToStagingDirectory,
    # CryptoSettings.Save). It is a staging output, not a changed cooked asset.
    # Permit only its addition during this controlled stage; every recorded
    # file, including a pre-existing cache, must still match exactly.
    if staging and phase == 'cook' and STAGE_CRYPTO not in value['artifacts']:
        actual.pop(STAGE_CRYPTO, None)
    require(value['artifacts'] == actual, f'{phase} artifact bytes changed; rerun its wrapper.')
    return value


def inputs(root, phase):
    result = build_inputs(root)
    if phase == 'cook':
        # Cook executes game code through the editor module; a new cook using
        # an old module must not inherit the current checkout's identity.
        editor = receipt(root, 'editor')
        result['editor_receipt_sha256'] = digest(root / RECEIPTS / 'editor.json')
        result['editor_artifacts'] = editor['artifacts']
        result['content'] = files(root, ['Content'])
    return result


def begin(root, phase, output, configuration='Development', expected_source=None, expected_native=None):
    require(configuration in ('Development', 'DebugGame'), 'Unsupported build configuration.')
    record = {'schema': SCHEMA, 'phase': phase, 'configuration': configuration,
              'source': source(root), 'inputs': inputs(root, phase),
              'started_at': datetime.now(timezone.utc).isoformat()}
    if expected_source is not None or expected_native is not None:
        require(record['source']['commit'] == revision(expected_source), 'Build/cook source differs from declared candidate.')
        require(record['inputs']['native']['commit'] == revision(expected_native), 'Build/cook native differs from declared candidate.')
    # Invalidate the previous receipt before invoking a tool that might fail
    # after replacing only some of its outputs.
    (root / RECEIPTS / f'{phase}.json').unlink(missing_ok=True)
    write(output, record)


def finish(root, start):
    value = read(start)
    phase = value['phase']
    require(value['source'] == source(root), 'Source changed during build/cook; no qualification receipt written.')
    require(value['inputs'] == inputs(root, phase), 'Inputs changed during build/cook; no qualification receipt written.')
    value['artifacts'] = files(root, artifact_paths(phase))
    if phase == 'game':
        value['executable_code_sha256'] = executable_code(root / 'Binaries/Mac/SoraArena.app/Contents/MacOS/SoraArena')
    value['finished_at'] = datetime.now(timezone.utc).isoformat()
    write(root / RECEIPTS / f'{phase}.json', value)
    print(f'Bound {phase} output to source {value["source"]["commit"]}, native {value["inputs"]["native"]["commit"]}')


def stage_begin(root, output, expected_source, expected_native):
    current = source(root)
    require(current['commit'] == revision(expected_source), 'Current source differs from declared candidate.')
    require(native(root)['commit'] == revision(expected_native), 'Native build differs from declared candidate.')
    game, cook = receipt(root, 'game'), receipt(root, 'cook')
    require(game['configuration'] == cook['configuration'] == 'Development', 'Stage requires Development build/cook receipts.')
    write(output, {'source': current, 'native': native(root), 'game': game, 'cook': cook})


def stage_finish(root, start, app, output):
    before = read(start)
    require(before['source'] == source(root), 'Source changed during staging.')
    require(before['native'] == native(root), 'Native inputs changed during staging.')
    # UAT may sign the app executable differently when adding its resource
    # seal; the controlled stage records its final bytes separately. Inputs
    # and the cooked payload must remain those validated before UAT.
    require(before['cook'] == receipt(root, 'cook', staging=True), 'Cook inputs changed during staging.')
    staged = app / 'Contents/UE/SoraArena'
    require(executable_code(app / 'Contents/MacOS/SoraArena') == before['game']['executable_code_sha256'],
            'Staged executable code differs from the source-bound game build.')
    require(files(staged, NON_UFS) == files(root, NON_UFS), 'Staged non-UFS content differs from candidate source.')
    require(native(staged) == before['native'], 'Staged bridge/sidecar differs from declared native build.')
    require(digest(staged / KERNEL) == before['game']['inputs']['kernel_sha256'], 'Staged kernel differs from game build input.')
    value = {'schema': CANDIDATE, 'source': before['source'], 'native': before['native'],
             'build': before['game'], 'cook': before['cook'], 'app_name': app.name,
             'staging_metadata': files(root, [STAGE_CRYPTO]) if (root / STAGE_CRYPTO).exists() else {},
             'app_files': files(app, ['.']), 'staged_at': datetime.now(timezone.utc).isoformat(),
             'evidence': 'local source-bound Mac package candidate; not release or live-network qualification'}
    write(output, value)
    print(f'Package candidate: source {value["source"]["commit"]}, native {value["native"]["commit"]}; {output}')


def verify(app, candidate, output, expected_source, expected_native):
    value = read(candidate)
    require(value.get('schema') == CANDIDATE, 'Package lacks a source-bound candidate record; rerun build/cook/stage wrappers.')
    require(value['source']['commit'] == revision(expected_source), 'Package source differs from declared candidate.')
    require(value['native']['commit'] == revision(expected_native), 'Package native source differs from declared candidate.')
    require(value['app_name'] == app.name and value['app_files'] == files(app, ['.']), 'Packaged artifact bytes differ from the candidate record.')
    require(native(app / 'Contents/UE/SoraArena') == value['native'], 'Packaged bridge/sidecar no longer matches native build evidence.')
    write(output, {'candidate_sha256': digest(candidate), 'candidate': value,
                   'verified_at': datetime.now(timezone.utc).isoformat()})
    print(f'Verified staged candidate source {value["source"]["commit"]}, ABI30 native {value["native"]["commit"]}, sha256 {value["native"]["library_sha256"]}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('begin'); p.add_argument('phase', choices=('editor', 'game', 'cook')); p.add_argument('output', type=Path)
    p.add_argument('--configuration', default='Development'); p.add_argument('--source'); p.add_argument('--native')
    p = sub.add_parser('invalidate'); p.add_argument('phase', choices=('editor', 'game', 'cook'))
    p = sub.add_parser('finish'); p.add_argument('start', type=Path)
    p = sub.add_parser('stage-begin'); p.add_argument('output', type=Path); p.add_argument('source'); p.add_argument('native')
    p = sub.add_parser('stage-finish'); p.add_argument('start', type=Path); p.add_argument('app', type=Path); p.add_argument('output', type=Path)
    p = sub.add_parser('verify'); p.add_argument('app', type=Path); p.add_argument('candidate', type=Path); p.add_argument('output', type=Path); p.add_argument('source'); p.add_argument('native')
    args = parser.parse_args()
    try:
        if args.command == 'begin': begin(args.root, args.phase, args.output, args.configuration, args.source, args.native)
        elif args.command == 'invalidate': (args.root / RECEIPTS / f'{args.phase}.json').unlink(missing_ok=True)
        elif args.command == 'finish': finish(args.root, args.start)
        elif args.command == 'stage-begin': stage_begin(args.root, args.output, args.source, args.native)
        elif args.command == 'stage-finish': stage_finish(args.root, args.start, args.app, args.output)
        else: verify(args.app, args.candidate, args.output, args.source, args.native)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f'FAIL Mac candidate: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
