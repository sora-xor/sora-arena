#!/usr/bin/env python3
"""Validate the audio ledger and source audio (the audio half of plan §2.5 validator rules).

Fails when:
  1. a file under Content/SourceArt/Audio (wav / mid / flac / ogg) has no OWN manifest record, or its SHA-256
     differs from the record;
  2. an audio ledger record (scripts/assets/manifests/audio_*.json) has a license outside the allowlist, a tier
     other than PUB-CC0 / PUB-PD, a file without SHA-256, or a raw file whose SHA-256 no longer matches;
  3. a raw third-party audio path is not gitignored, or any path under Local/ is tracked by git;
  3b. a reference-only record (scripts/assets/restricted/audio_*.json) is not tier REF/RST, lists a file outside
     Local/ or with a changed SHA-256, or is used as a cue layer or music sample source;
  4. Content/SourceArt/Audio/cues.proposed.json references a file that does not exist;
  5. any WAV under Content/SourceArt/Audio fails listen-free QA (clipping, true peak > -0.5 dBTP, DC offset,
     silence, loop click) — see scripts/audio/qa_audio.py.

  python3 scripts/audio/validate_audio.py            # full (hashes every raw file: ~3 GB, ~1 min)
  python3 scripts/audio/validate_audio.py --quick    # skip re-hashing raw third-party files
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from qa_audio import analyze  # noqa: E402

AUDIO = ROOT / 'Content/SourceArt/Audio'
OWN_MANIFESTS = [AUDIO / 'Original/manifest.json', AUDIO / 'Music/manifest.json']
LICENSES = {'CC0-1.0', 'PDM-1.0', 'US-PD'}
TIERS = {'PUB-CC0', 'PUB-PD'}
REFERENCE_TIERS = {'REF', 'RST'}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true')
    args = ap.parse_args()
    errors: list[str] = []

    # 1. OWN files
    records = {}
    for m in OWN_MANIFESTS:
        if not m.exists():
            errors.append(f'missing manifest {m.relative_to(ROOT)}')
            continue
        data = json.loads(m.read_text())
        if data.get('tier') != 'OWN':
            errors.append(f'{m.relative_to(ROOT)} tier is not OWN')
        for row in data.get('files', []):
            records[row['file']] = row
    for p in sorted(AUDIO.rglob('*')):
        if p.suffix.lower() not in {'.wav', '.mid', '.flac', '.ogg'}:
            continue
        rel = str(p.relative_to(ROOT))
        row = records.get(rel)
        if row is None:
            errors.append(f'no OWN record for {rel}')
        elif row.get('sha256') != sha(p):
            errors.append(f'SHA-256 mismatch for {rel}')
    for rel in records:
        if not (ROOT / rel).exists():
            errors.append(f'manifest lists a missing file {rel}')

    # 2-3. third-party ledger
    raw_count = 0
    for m in sorted((ROOT / 'scripts/assets/manifests').glob('audio_*.json')):
        data = json.loads(m.read_text())
        for a in data.get('assets', []):
            if a.get('license') not in LICENSES:
                errors.append(f'{a["asset_id"]}: license {a.get("license")} not allowed')
            if a.get('tier') not in TIERS:
                errors.append(f'{a["asset_id"]}: tier {a.get("tier")} not allowed for agent-fetched audio')
            rows = list(a.get('files', [])) + list(a.get('downloads', [])) + ([a['archive']] if 'archive' in a else [])
            for row in rows:
                f = row['file']
                if not row.get('sha256'):
                    errors.append(f'{f}: no SHA-256')
                if not f.startswith('Local/'):
                    errors.append(f'{f}: third-party raw file outside Local/')
                path = ROOT / f
                if not path.exists():
                    errors.append(f'{f}: missing on disk')
                elif not args.quick:
                    raw_count += 1
                    if sha(path) != row['sha256']:
                        errors.append(f'{f}: SHA-256 changed since fetch')
    # 3b. reference-only audio (never sampled, never shipped)
    reference_files: dict[str, str] = {}
    for m in sorted((ROOT / 'scripts/assets/restricted').glob('audio_*.json')):
        data = json.loads(m.read_text())
        for a in data.get('assets', []) + data.get('records', []):
            if a.get('tier') not in REFERENCE_TIERS:
                errors.append(f'{a["asset_id"]}: tier {a.get("tier")} does not belong in {m.name}')
            for row in a.get('files', []):
                f = row['file']
                reference_files[f] = a['asset_id']
                if not f.startswith('Local/'):
                    errors.append(f'{f}: reference-only file outside Local/')
                path = ROOT / f
                if not path.exists():
                    errors.append(f'{f}: missing on disk')
                elif not args.quick and sha(path) != row.get('sha256'):
                    errors.append(f'{f}: SHA-256 changed since fetch')
    for m in OWN_MANIFESTS:
        if m.exists():
            text = m.read_text()
            for f, asset_id in reference_files.items():
                if f in text or asset_id in text:
                    errors.append(f'{m.relative_to(ROOT)} uses reference-only {asset_id}')
    ignored = subprocess.run(['git', 'check-ignore', '-q', 'Local/ThirdPartyRaw/audio/x.wav'], cwd=ROOT).returncode == 0
    if not ignored:
        errors.append('Local/ThirdPartyRaw/audio is not gitignored')
    tracked = subprocess.run(['git', 'ls-files', 'Local'], cwd=ROOT, stdout=subprocess.PIPE, text=True).stdout.strip()
    if tracked:
        errors.append(f'paths under Local/ are tracked by git: {tracked.splitlines()[:5]}')

    # 4. cue proposal
    cues_path = AUDIO / 'cues.proposed.json'
    if cues_path.exists():
        cues = json.loads(cues_path.read_text())
        for c in cues['cues']:
            for f in c['files']:
                if not (ROOT / f).exists():
                    errors.append(f'cue {c["id"]}: missing {f}')
            for layer in c['layers_cc0']:
                if layer.get('asset_id') in reference_files.values():
                    errors.append(f'cue {c["id"]}: layer {layer["asset_id"]} is reference-only')
                for f in layer['files']:
                    if f['file'] in reference_files:
                        errors.append(f'cue {c["id"]}: {f["file"]} is reference-only')
                    if not (ROOT / f['file']).exists():
                        errors.append(f'cue {c["id"]}: missing CC0 layer {f["file"]} (run fetch_cc0_audio.py)')
    else:
        errors.append('cues.proposed.json missing (run scripts/audio/build_cue_proposal.py)')

    # 5. QA
    wavs = sorted(AUDIO.rglob('*.wav'))
    for p in wavs:
        res = analyze(p)
        if res['fail']:
            errors.append(f'QA {p.relative_to(ROOT)}: {res["fail"]}')

    for e in errors:
        print('ERROR', e)
    print(f'{len(records)} OWN records, {len(wavs)} WAVs QA-checked, {raw_count} raw files re-hashed, '
          f'{len(errors)} errors')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
