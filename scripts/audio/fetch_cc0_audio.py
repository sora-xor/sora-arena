#!/usr/bin/env python3
"""Fetch the allowlisted CC0 / public-domain audio sources for SORA Arena: Nyaagyu Rebellion.

Policy (docs/art-research/free-asset-acquisition-plan.md, sections 2, 4.1 and 5):
  * Only sources the plan approves for unattended agent fetch: Kenney, OpenGameArt (items whose
    page lists CC0), VCSL (Versilian Community Sample Library, CC0, per-file from a pinned commit)
    and Wikimedia Commons (per-file CC0 / public-domain check through the API).
  * Every item's license is re-read from its primary page / API / LICENSE file at fetch time and the
    run aborts that item if the license is not CC0 or public domain. Nothing behind a login, no
    click-through, no account.
  * Raw files go ONLY to the gitignored Local/ThirdPartyRaw/audio/ tree. Page / license snapshots go
    to Local/ThirdPartyRaw/_licenses/audio/ (private; their SHA-256 is recorded).
  * Committed output is the manifests in scripts/assets/manifests/audio_<source>.json: schema-2
    ledger records with URL, license, license evidence, SHA-256 per file, retrieval time.
    Reference-only items (e.g. a CC0 recording of an uncleared composition) are tier REF and go to
    scripts/assets/restricted/audio_<source>_reference.json instead (hashes and paths only).
  * Items whose page names an earlier source (a Freesound upload re-hosted on OpenGameArt or Commons)
    record that true source as origin_url and the page we downloaded from as mirror_url. The origin's
    public page is read for its license (never downloaded from: Freesound downloads need a login).
  * Disk guard: aborts if the data volume would drop below MIN_FREE_GIB, or if this lane's raw
    audio tree would exceed LANE_BUDGET_GIB.

Usage:
  python3 scripts/audio/fetch_cc0_audio.py --list
  python3 scripts/audio/fetch_cc0_audio.py --source kenney --source wikimedia
  python3 scripts/audio/fetch_cc0_audio.py            # all sources
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'Local/ThirdPartyRaw/audio'
LICENSE_SNAPSHOTS = ROOT / 'Local/ThirdPartyRaw/_licenses/audio'
MANIFESTS = ROOT / 'scripts/assets/manifests'
RESTRICTED = ROOT / 'scripts/assets/restricted'
UA = ('SORA-Arena-Audio-Acquisition/0.1 (offline game production; CC0-only unattended fetch; '
      'license verified per item at fetch time)')
ALLOWED_HOSTS = {
    'kenney.nl', 'opengameart.org', 'raw.githubusercontent.com', 'github.com',
    'commons.wikimedia.org', 'upload.wikimedia.org',
}
# Upstream origin pages read (public GET, no login) only to confirm their license; never downloaded from.
LICENSE_PAGE_HOSTS = {'freesound.org'}
DATA_VOLUME = '/System/Volumes/Data' if Path('/System/Volumes/Data').exists() else '/'
MIN_FREE_GIB = 35.0
LANE_BUDGET_GIB = 4.0
GIB = 1024 ** 3
AUDIO_EXT = {'.wav', '.ogg', '.oga', '.flac', '.mp3', '.aif', '.aiff'}
ARCHIVE_EXT = {'.zip', '.7z', '.tar', '.gz', '.tgz'}
CC0_URL = 'https://creativecommons.org/publicdomain/zero/1.0/'
CC0_LEGAL = 'https://creativecommons.org/publicdomain/zero/1.0/legalcode'
PLAN = 'docs/art-research/free-asset-acquisition-plan.md'

# --------------------------------------------------------------------------------------------
# Selections. Roles map to docs/audio.md cue families.
# --------------------------------------------------------------------------------------------
VCSL_REPO = 'https://github.com/sgossner/VCSL.git'
VCSL_WEB = 'https://github.com/sgossner/VCSL'
VCSL_COMMIT = 'c1ea7bcc3c7309650ab0da9d15c9cd1fbc4a4c7e'  # master on 2026-09-25 ("Create LICENSE", 2026-01-14)
VCSL_FOLDERS = [
    ('Chordophones/Zithers/Dan Tranh', 'music: koto stand-in (plucked zither, normal/vibrato/tremolo/gliss)'),
    ('Chordophones/Zithers/Psaltery, Bowed and Plucked', 'music: biwa/koto colour, bowed alien shimmer'),
    ('Aerophones/Edge-blown Aerophones/Baroque Tenor Recorder', 'music: shakuhachi-like flute body (resynthesised)'),
    ('Aerophones/Edge-blown Aerophones/Baroque Alto Recorder', 'music: shinobue-like upper flute body'),
    ('Membranophones/Struck Membranophones/Bass Drum 1', 'music: odaiko stand-in'),
    ('Membranophones/Struck Membranophones/Bass Drum 2', 'music: odaiko stand-in (more velocity layers)'),
    ('Membranophones/Struck Membranophones/Bass Drum 3 - Legacy', 'music: odaiko stand-in (legacy set)'),
    ('Membranophones/Struck Membranophones/Frame Drum', 'music: hand drum / uchiwa-daiko stand-in'),
    ('Membranophones/Struck Membranophones/Tom 1', 'music: shime/nagado mid drum stand-in'),
    ('Membranophones/Struck Membranophones/Tom 2', 'music: shime/nagado mid drum stand-in'),
    ('Membranophones/Struck Membranophones/Timpani 1', 'music: sub drum reinforcement'),
    ('Membranophones/Other Membranophones/Ocean Drum', 'sfx/music: surf and rain texture'),
    ('Idiophones/Struck Idiophones/Woodblock', 'music/ui: hyoshigi-like wood clack'),
    ('Idiophones/Struck Idiophones/Claves', 'music/ui: hyoshigi-like wood clack'),
    ('Idiophones/Struck Idiophones/Slit Drum', 'music: mokugyo-like wood drum'),
    ('Idiophones/Struck Idiophones/Gong 1', 'music/sfx: dora gong, bell layers'),
    ('Idiophones/Struck Idiophones/Gong 2', 'music/sfx: dora gong, bell layers'),
    ('Idiophones/Struck Idiophones/Tubular Bells 1', 'sfx: hansho alarm bell layer, temple bell partials'),
    ('Idiophones/Struck Idiophones/Tubular Bells 2', 'sfx: hansho alarm bell layer'),
    ('Idiophones/Struck Idiophones/Hand Bells, Nepalese', 'music/ui: rin-like bowl bell'),
    ('Idiophones/Struck Idiophones/Hand Chimes', 'music/ui: bell motif'),
    ('Idiophones/Struck Idiophones/Finger Cymbals', 'music/ui: small bell accent'),
    ('Idiophones/Struck Idiophones/Anvil', 'sfx/music: smithy anvil, forge percussion'),
    ('Idiophones/Struck Idiophones/Ratchet', 'sfx: crank / winch ratchet'),
    ('Idiophones/Friction Idiophones/Wine Glasses', 'music/sfx: alien glass harmonics'),
]

KENNEY_PACKS = [
    ('interface-sounds', 'ui: placeholder clicks and confirms'),
    ('ui-audio', 'ui: placeholder clicks and switches'),
    ('impact-sounds', 'sfx: impact / footstep placeholder layers'),
    ('rpg-audio', 'sfx: foley placeholders (cloth, metal, footsteps, doors)'),
    ('sci-fi-sounds', 'sfx: alien placeholder layers'),
    ('digital-audio', 'ui/sfx: digital placeholder layers'),
    ('casino-audio', 'ui: coin/chip handling placeholders for XOR payout UI'),
    ('music-jingles', 'music: placeholder stingers only'),
]

# (slug, role, max_mb). Only items whose OGA page lists CC0 are accepted at fetch time.
OGA_ITEMS = [
    ('the-free-firearm-sound-library', 'weapons: matchlock report low layers, mechanisms (Free Firearm Sound Library, CC0)', 200),
    ('medieval-sound-effects-weapon-impacts', 'melee: real steel clashes, parries, blade-on-blade', 160),
    ('medieval-sound-effects-weapon-textures', 'melee: draws, sheathing, handling, armour textures', 180),
    ('swish-bamboo-stick-weapon-swhoshes', 'melee: bokuto / fukuro-shinai swing whooshes (bamboo stick)', 6),
    ('swishes-sound-pack', 'melee: light/heavy swish layers', 1),
    ('33-metal-clang-sounds-cast-iron-pans', 'smithy / melee: cast-iron clang layers', 6),
    ('31-pings-and-metal-filing-sounds', 'smithy: filing, pings', 9),
    ('100-cc0-metal-and-wood-sfx', 'foley: metal and wood handling', 3),
    ('35-wooden-crackshitsdestructions', 'foley: wood cracks and breaks (props, shields)', 5),
    ('wood-and-metal-sound-effects-volume-2', 'foley: wood and metal impacts', 2),
    ('68-workshop-sounds', 'smithy / workshop: tools recorded in a garage', 26),
    ('chain-winch-sounds', 'mechanisms: chain winch (lift, kusarigama chain layer)', 2),
    ('equipment-clicks-ii', 'weapons: equipment clicks (reload, pickup)', 1),
    ('metal-impact-sounds', 'foley: metal impacts', 1),
    ('blacksmiths-hammer', 'smithy: hammer on a 45 lb anvil', 1),
    ('fantozzis-footsteps-grasssand-stone', 'footsteps: grass/sand and stone single steps', 1),
    ('park-ambiences', 'ambience: birds before rain, small river, wind (long field recordings)', 270),
    ('amb-rain-loop-2', 'ambience: rain bed (GoPro raw)', 80),
    ('rain-loopable', 'ambience: rain loops (window, mono)', 6),
    ('rain-long-thunder', 'weather: rain with long thunder', 1),
    ('20-rustles-dry-leaves', 'foley: dry-leaf rustles (24-bit / 96 kHz)', 11),
    ('water-waves', 'ambience: small waves (upstream Freesound 11505, CC0)', 2),
    ('dripping-water-loop', 'ambience: basement drips (vault, cave)', 2),
    ('6-short-water-splashes', 'foley: water splashes (moat swim, paddies)', 1),
    ('40-cc0-water-splash-slime-sfx', 'foley: water splash and bubble layers', 3),
    ('30-cc0-sfx-loops', 'ambience: machine / pump / water loops (alien machinery layers)', 4),
    ('crow-caw', 'ambience: crow call', 1),
    ('fireplace-sound-loop', 'ambience: wood fire loop (burning estate, forge)', 11),
    ('fire-crackling', 'ambience: fire crackle', 1),
    ('flare-ignition', 'weapons: matchlock pan-flash layer (matchstick ignition)', 1),
    ('cannon-fire', 'weapons: cannon report layer', 1),
    ('25-cc0-bang-firework-sfx', 'weapons / festival: firework bangs (hanabi, grenades)', 2),
    ('muffled-distant-explosion', 'weapons: distant explosion tail', 1),
    ('60-cc0-sci-fi-sfx', 'alien: sci-fi layers', 10),
    ('50-cc0-sci-fi-sfx', 'alien: sci-fi layers', 3),
    ('space-ship-shield-sounds', 'alien: shield layers', 2),
    ('50-free-scifi-soundfx-192khz-64-bit-24576kbps-wav', 'alien: high-rate sci-fi layers', 60),
    ('raw-b%C4%9Bixi%C4%81o-audio', 'music: beixiao (end-blown bamboo flute) samples as a shakuhachi stand-in', 32),
    ('ui-sound-effects-button-clicks-user-feedback-notifications', 'ui: clicks/notifications built from VCSL + VSCO2 CE', 2),
    ('16-button-clicks', 'ui: button clicks', 1),
    ('horse-trotting', 'horse: trot placeholder (foley, jacket on bottle)', 1),
]

# Items re-hosted from an earlier source: asset_id -> (origin site, origin page, origin authors, snapshot name).
# The origin page must state CC0 when read; origin_url becomes that page and mirror_url the page we used.
UPSTREAM = {
    'opengameart/water-waves': (
        'Freesound', 'https://freesound.org/people/transitking/sounds/11505/', ['transitking'],
        'freesound-sound-11505'),
    'opengameart/fantozzis-footsteps-grasssand-stone': (
        'Freesound', 'https://freesound.org/people/Fantozzi/packs/10338/', ['Fantozzi'], 'freesound-pack-10338'),
    'wikimedia/File:Shakuhachi-flute-440Hz.ogg': (
        'Freesound', 'https://freesound.org/people/--DeletedUser--/sounds/268183/',
        ['--DeletedUser-- (Freesound account since deleted)'], 'freesound-sound-268183'),
}
CC0_PAGE_MARKERS = ('Creative Commons 0', 'publicdomain/zero/1.0')

# (title, role, use_policy). use_policy 'sample' may be sampled into our renders; 'reference-only' may not
# (recorded as tier REF in the restricted directory).
WIKIMEDIA_FILES = [
    ('File:Shakuhachi-flute-440Hz.ogg', 'music: single shakuhachi A4 tone (timbre reference and sampler seed)', 'sample'),
    ('File:02 Taiko2 (short).oga', 'music: taiko timbre reference (spectral target for the taiko stand-in)',
     'reference-only: the recording is CC0 on Commons, but it performs Scott Harding\'s composition "Taiko", '
     'whose copyright was not cleared; never sample it into shipped audio'),
]


# --------------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------------
def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha1(path: Path) -> str:
    size = path.stat().st_size
    h = hashlib.sha1(f'blob {size}\0'.encode())
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def free_gib() -> float:
    return shutil.disk_usage(DATA_VOLUME).free / GIB


def tree_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for base, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += (Path(base) / name).lstat().st_size
            except OSError:
                pass
    return total


class Guard:
    """Disk floor and lane budget guard, checked before every download or extraction."""

    def __init__(self, budget_gib: float):
        self.budget = budget_gib * GIB
        self.start_lane = tree_bytes(RAW) + tree_bytes(LICENSE_SNAPSHOTS)
        self.start_free = free_gib()

    def check(self, expected_bytes: int, what: str) -> None:
        free = free_gib()
        if free - expected_bytes / GIB < MIN_FREE_GIB:
            raise SystemExit(f'DISK FLOOR: {what} needs {expected_bytes/1e6:.1f} MB but only {free:.1f} GiB free '
                             f'(floor {MIN_FREE_GIB} GiB). Stopping.')
        lane = tree_bytes(RAW) + tree_bytes(LICENSE_SNAPSHOTS)
        if lane + expected_bytes > self.budget:
            raise SystemExit(f'LANE BUDGET: {what} would take the raw audio tree to '
                             f'{(lane + expected_bytes)/GIB:.2f} GiB (> {self.budget/GIB:.2f} GiB). Stopping.')


def check_host(url: str, extra: frozenset = frozenset()) -> None:
    host = urllib.parse.urlparse(url).hostname or ''
    if host not in ALLOWED_HOSTS and host not in extra:
        raise RuntimeError(f'host not on the audio allowlist: {url}')


def http_get(url: str, *, method: str = 'GET', timeout: int = 120, extra_hosts: frozenset = frozenset()):
    check_host(url, extra_hosts)
    req = urllib.request.Request(url, headers={'User-Agent': UA}, method=method)
    return urllib.request.urlopen(req, timeout=timeout)


def http_text(url: str, license_page: bool = False) -> str:
    """GET a page. license_page=True also allows the upstream license-page hosts (read only)."""
    extra = frozenset(LICENSE_PAGE_HOSTS) if license_page else frozenset()
    for attempt in range(4):
        try:
            with http_get(url, extra_hosts=extra) as resp:
                return resp.read().decode('utf-8', 'replace')
        except Exception as exc:  # noqa: BLE001 - network retries
            if attempt == 3:
                raise
            print(f'  retry {attempt+1} {url}: {exc}', flush=True)
            time.sleep(2 + attempt * 3)
    raise AssertionError


def http_size(url: str) -> int:
    try:
        with http_get(url, method='HEAD', timeout=60) as resp:
            return int(resp.headers.get('Content-Length') or 0)
    except Exception:  # noqa: BLE001
        return 0


def download(url: str, dest: Path, guard: Guard, expected_size: int | None = None) -> dict:
    """Stream url to dest (atomic). Skips if dest exists with the expected size."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if expected_size is None:
        expected_size = http_size(url)
    if dest.is_file() and (not expected_size or dest.stat().st_size == expected_size):
        return {'url': url, 'file': rel(dest), 'bytes': dest.stat().st_size, 'sha256': sha256_file(dest),
                'reused_local': True}
    guard.check(expected_size or 0, url)
    partial = dest.with_name(dest.name + '.partial')
    for attempt in range(4):
        try:
            with http_get(url, timeout=300) as resp, open(partial, 'wb') as out:
                shutil.copyfileobj(resp, out, 1 << 20)
            break
        except Exception as exc:  # noqa: BLE001
            if attempt == 3:
                raise
            print(f'  retry {attempt+1} {url}: {exc}', flush=True)
            time.sleep(3 + attempt * 5)
    size = partial.stat().st_size
    if expected_size and size != expected_size:
        raise RuntimeError(f'incomplete download {url}: {size} != {expected_size}')
    partial.replace(dest)
    print(f'  fetched {rel(dest)} ({size/1e6:.1f} MB)', flush=True)
    return {'url': url, 'file': rel(dest), 'bytes': size, 'sha256': sha256_file(dest), 'reused_local': False}


def snapshot(name: str, text: str) -> dict:
    """Private snapshot of a license/terms page (never committed; hash recorded)."""
    LICENSE_SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    safe = re.sub(r'[^A-Za-z0-9._-]+', '_', name)[:120]
    path = LICENSE_SNAPSHOTS / f'{safe}-{day}.html'
    path.write_text(text, encoding='utf-8')
    return {'path': rel(path), 'sha256': sha256_file(path), 'captured_at_utc': now()}


def safe_extract_zip(archive: Path, out: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            target = (out / member.filename).resolve()
            if not str(target).startswith(str(out.resolve())):
                raise RuntimeError(f'unsafe path in {archive}: {member.filename}')
        zf.extractall(out)


def extract(archive: Path, out: Path, guard: Guard) -> None:
    marker = out / '.extracted'
    if marker.is_file():
        return
    guard.check(int(archive.stat().st_size * 1.6), f'extract {archive.name}')
    out.mkdir(parents=True, exist_ok=True)
    if archive.suffix.lower() == '.zip':
        safe_extract_zip(archive, out)
    else:
        # bsdtar (libarchive) reads 7z and tar; -P is NOT passed, so absolute / .. paths are refused.
        subprocess.run(['bsdtar', '-xf', str(archive), '-C', str(out)], check=True)
    marker.write_text(now() + '\n')
    print(f'  extracted {archive.name} -> {rel(out)}', flush=True)


def file_records(base: Path) -> list[dict]:
    rows = []
    for path in sorted(p for p in base.rglob('*') if p.is_file()):
        if path.name.startswith('.') or '__MACOSX' in path.parts:
            continue
        if path.suffix.lower() not in AUDIO_EXT and path.suffix.lower() not in {'.txt', '.md', '.pdf', '.rtf'}:
            continue
        rows.append({'file': rel(path), 'bytes': path.stat().st_size, 'sha256': sha256_file(path)})
    return rows


def upstream_fields(asset_id: str, mirror_url: str) -> dict:
    """origin_url / mirror_url / upstream evidence for an item re-hosted from an earlier source."""
    if asset_id not in UPSTREAM:
        return {}
    site, url, authors, snap_name = UPSTREAM[asset_id]
    page = http_text(url, license_page=True)
    stated = [m for m in CC0_PAGE_MARKERS if m in page]
    if not stated:
        raise SystemExit(f'{asset_id}: upstream page {url} no longer states CC0; stopping for review')
    return {
        'origin_url': url,
        'mirror_url': mirror_url,
        'upstream': {'site': site, 'url': url, 'authors': authors, 'license': 'CC0-1.0',
                     'license_stated': stated, 'page_snapshot': snapshot(snap_name, page),
                     'access': 'direct (public page read; nothing downloaded from it)',
                     'verified_at_utc': now()},
    }


def reference_fields(asset_id: str, listing_url: str, reason: str) -> dict:
    """Tier REF: kept locally as a reference, never sampled, shipped or committed."""
    return {'tier': 'REF', 'commercial_use': False, 'redistribution': 'none', 'derivatives': False,
            'listing_url': listing_url, 'user_step': None,
            'entitlement_owner': 'none (public file; no account, entitlement or terms acceptance)',
            'reason': reason}


def base_record(**kw) -> dict:
    record = {
        'tier': 'PUB-CC0',
        'license': 'CC0-1.0',
        'license_url': CC0_URL,
        'legal_code_url': CC0_LEGAL,
        'commercial_use': True,
        'redistribution': 'unrestricted',
        'derivatives': True,
        'platform_restriction': None,
        'ai_terms': 'none',
        'agent_handling': 'allowed',
        'attribution_text': None,
        'changes': None,
        'access': 'direct',
        'acquired_by': 'agent',
        'storage': 'local-private',
        'committed': False,
        'used_by': [],
        'fallback': None,
    }
    record.update(kw)
    return record


def write_manifest(name: str, payload: dict, restricted: bool = False) -> Path:
    folder = RESTRICTED if restricted else MANIFESTS
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (f'audio_{name}_reference.json' if restricted else f'audio_{name}.json')
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'MANIFEST {rel(path)}', flush=True)
    return path


def manifest_header(source: str, purpose: str, guard: Guard, started: str) -> dict:
    return {
        'schema_version': 2,
        'source': source,
        'purpose': purpose,
        'ledger_policy': PLAN + ' (sections 2.1-2.5)',
        'fetch_script': 'scripts/audio/fetch_cc0_audio.py',
        'raw_root': rel(RAW),
        'raw_committed': False,
        'batch_log': {
            'started_at_utc': started,
            'finished_at_utc': now(),
            'free_gib_before': round(guard.start_free, 2),
            'free_gib_after': round(free_gib(), 2),
            'raw_audio_tree_bytes_after': tree_bytes(RAW),
        },
    }


# --------------------------------------------------------------------------------------------
# Kenney
# --------------------------------------------------------------------------------------------
def fetch_kenney(guard: Guard) -> None:
    started = now()
    assets = []
    for slug, role in KENNEY_PACKS:
        page_url = f'https://kenney.nl/assets/{slug}'
        page = http_text(page_url)
        lic = re.search(r"License</td>\s*<td[^>]*>(.*?)</td>", page, re.S)
        license_text = ' '.join(html.unescape(re.sub('<[^>]+>', ' ', lic.group(1))).split()) if lic else ''
        if 'CC0' not in license_text:
            print(f'SKIP kenney/{slug}: license on page is {license_text!r}, not CC0', flush=True)
            continue
        m = re.search(r"https://kenney\.nl/media/pages/assets/%s/[^'\"\s]+\.zip" % re.escape(slug), page)
        if not m:
            print(f'SKIP kenney/{slug}: no direct zip link on page', flush=True)
            continue
        zip_url = m.group(0)
        title = re.search(r'<title>([^<]*)</title>', page)
        dest = RAW / 'kenney' / slug / Path(urllib.parse.urlparse(zip_url).path).name
        dl = download(zip_url, dest, guard)
        out = RAW / 'kenney' / slug / 'extracted'
        extract(dest, out, guard)
        lic_files = [p for p in out.rglob('*') if p.is_file() and p.name.lower().startswith('license')]
        lic_evidence = []
        for lf in lic_files:
            txt = lf.read_text('utf-8', 'replace')
            ok = ('CC0' in txt) or ('Creative Commons Zero' in txt) or ('publicdomain/zero' in txt)
            lic_evidence.append({'file': rel(lf), 'sha256': sha256_file(lf), 'states_cc0': ok})
            if not ok:
                raise SystemExit(f'kenney/{slug}: bundled {lf.name} does not state CC0; stopping for review')
        assets.append(base_record(
            asset_id=f'kenney/{slug}',
            name=html.unescape(title.group(1)).split('·')[0].strip() if title else slug,
            role=role,
            origin_url=page_url,
            mirror_url=None,
            authors=['Kenney (kenney.nl)'],
            license_evidence={
                'page_license_field': license_text,
                'page_snapshot': snapshot(f'kenney-{slug}', page),
                'bundled_license_files': lic_evidence,
                'verified_at_utc': now(),
            },
            acquired_at_utc=now(),
            archive=dl,
            files=file_records(out),
            placeholder_only=True,
            notes='Kenney audio is stylised game audio: placeholder / layering only, never a hero sound.',
        ))
        print(f'OK kenney/{slug}: {len(assets[-1]["files"])} files', flush=True)
    payload = manifest_header('Kenney (kenney.nl) audio packs', 'CC0 UI / foley / sci-fi placeholder layers', guard, started)
    payload['credit'] = 'Kenney (www.kenney.nl) — CC0; credit appreciated, not required.'
    payload['assets'] = assets
    write_manifest('kenney', payload)


# --------------------------------------------------------------------------------------------
# OpenGameArt
# --------------------------------------------------------------------------------------------
def parse_oga(page: str) -> dict:
    title = re.search(r'<title>([^|<]*)', page)
    lic = re.search(r'field-name-field-art-licenses.*?</div></div></div>', page, re.S)
    licenses = re.findall(r"license-name'>([^<]*)", lic.group(0)) if lic else []
    # <div class="field field-name-author-submitter ..."><div class="field-label">Author:</div>
    # <div class="field-items"><div class="field-item even">NAME<br/>(Submitted by <strong>USER</strong>)</div>
    auth = re.search(r'field-name-author-submitter.*?<div class="field-item[^"]*">(.*?)</div>', page, re.S)
    author = ''
    if auth:
        item = re.split(r'\(\s*Submitted by', auth.group(1), maxsplit=1)[0]
        author = ' '.join(html.unescape(re.sub('<[^>]+>', ' ', item)).split()).strip(' (')
    files_block = re.search(r'field-name-field-art-files.*?</div></div></div>', page, re.S)
    urls = re.findall(r'href="(https://opengameart\.org/sites/default/files/[^"]+)"', files_block.group(0)) if files_block else []
    body = re.search(r'field-name-body.*?</div></div></div>', page, re.S)
    body_text = ' '.join(html.unescape(re.sub('<[^>]+>', ' ', body.group(0))).split()) if body else ''
    body_text = re.sub(r'^field-name-body[^>]*>\s*', '', body_text)
    return {'title': html.unescape(title.group(1)).strip() if title else '', 'licenses': licenses,
            'author': author, 'file_urls': urls, 'body': body_text}


def fetch_opengameart(guard: Guard) -> None:
    started = now()
    assets, skipped = [], []
    for slug, role, max_mb in OGA_ITEMS:
        page_url = f'https://opengameart.org/content/{slug}'
        page = http_text(page_url)
        info = parse_oga(page)
        if 'CC0' not in info['licenses']:
            skipped.append({'slug': slug, 'reason': f'licenses on page: {info["licenses"]}'})
            print(f'SKIP oga/{slug}: {info["licenses"]}', flush=True)
            continue
        sizes = [http_size(u) for u in info['file_urls']]
        if sum(sizes) > max_mb * 1e6:
            skipped.append({'slug': slug, 'reason': f'size {sum(sizes)/1e6:.1f} MB > cap {max_mb} MB'})
            print(f'SKIP oga/{slug}: too large ({sum(sizes)/1e6:.1f} MB)', flush=True)
            continue
        item_dir = RAW / 'opengameart' / urllib.parse.unquote(slug)
        downloads = []
        for url, size in zip(info['file_urls'], sizes):
            name = urllib.parse.unquote(Path(urllib.parse.urlparse(url).path).name)
            downloads.append(download(url, item_dir / 'download' / name, guard, size or None))
        extracted = []
        for dl in downloads:
            path = ROOT / dl['file']
            if path.suffix.lower() in ARCHIVE_EXT:
                out = item_dir / 'extracted' / path.stem
                extract(path, out, guard)
                extracted.extend(file_records(out))
        multi = len(info['licenses']) > 1
        asset_id = f'opengameart/{urllib.parse.unquote(slug)}'
        record = base_record(
            asset_id=asset_id,
            name=info['title'],
            role=role,
            origin_url=page_url,
            mirror_url=None,
            authors=[info['author']] if info['author'] else [],
            license_evidence={
                'page_licenses': info['licenses'],
                'license_selected': 'CC0' + (' (item is multi-licensed; CC0 option selected)' if multi else ''),
                'page_statement': info['body'][:1200],
                'page_snapshot': snapshot(f'oga-{urllib.parse.unquote(slug)}', page),
                'verified_at_utc': now(),
            },
            acquired_at_utc=now(),
            downloads=downloads,
            files=extracted,
            notes=('Upstream chain stated on the page; see page_statement.'
                   if re.search(r'freesound|derivat|from http', info['body'], re.I) else None),
        )
        record.update(upstream_fields(asset_id, page_url))
        assets.append(record)
        print(f'OK oga/{slug}: {len(downloads)} download(s), {len(extracted)} extracted files', flush=True)
        time.sleep(0.5)
    payload = manifest_header('OpenGameArt.org (CC0-listed items only)',
                              'Real recordings and layers for melee, weapons, foley, ambience, UI and music samples',
                              guard, started)
    payload['assets'] = assets
    payload['skipped'] = skipped
    write_manifest('opengameart', payload)


# --------------------------------------------------------------------------------------------
# VCSL (pinned commit, per-file, verified against git blob ids)
# --------------------------------------------------------------------------------------------
def git(*args: str, cwd: Path, capture: bool = True, env_extra: dict | None = None) -> str:
    env = dict(os.environ)
    env['GIT_NO_LAZY_FETCH'] = '1'  # never let a metadata query pull the whole 3.8 GB repository
    env.update(env_extra or {})
    res = subprocess.run(['git', *args], cwd=cwd, check=True, env=env,
                         stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE)
    return res.stdout.decode('utf-8', 'replace') if capture else ''


def fetch_vcsl(guard: Guard) -> None:
    started = now()
    clone = RAW / 'vcsl'
    if not (clone / '.git').is_dir():
        guard.check(50_000_000, 'VCSL blobless clone')
        subprocess.run(['git', 'clone', '--filter=blob:none', '--no-checkout', '--sparse', VCSL_REPO, str(clone)], check=True)
    try:
        git('cat-file', '-e', VCSL_COMMIT + '^{commit}', cwd=clone)
    except subprocess.CalledProcessError:
        subprocess.run(['git', 'fetch', '--filter=blob:none', 'origin', VCSL_COMMIT], cwd=clone, check=True)
    # License: read LICENSE + README from the pinned commit (explicitly allow the two small blob fetches).
    lic_text = subprocess.run(['git', 'show', f'{VCSL_COMMIT}:LICENSE'], cwd=clone, check=True,
                              stdout=subprocess.PIPE).stdout.decode()
    readme = subprocess.run(['git', 'show', f'{VCSL_COMMIT}:README.md'], cwd=clone, check=True,
                            stdout=subprocess.PIPE).stdout.decode()
    if 'CC0 1.0 Universal' not in lic_text or 'Creative Commons 0' not in readme:
        raise SystemExit('VCSL LICENSE/README at the pinned commit no longer state CC0; stopping for review')
    lic_snap = snapshot('vcsl-LICENSE', lic_text)
    readme_snap = snapshot('vcsl-README', readme)
    head = git('ls-remote', VCSL_REPO, 'HEAD', cwd=clone).split()[0]
    local_blobs = set()
    for line in git('cat-file', '--batch-all-objects', '--batch-check', cwd=clone).splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == 'blob':
            local_blobs.add(parts[0])
    out_root = RAW / f'vcsl-{VCSL_COMMIT[:7]}'
    assets = []
    for folder, role in VCSL_FOLDERS:
        listing = git('ls-tree', '-r', VCSL_COMMIT, '--', folder, cwd=clone).splitlines()
        rows = []
        for line in listing:
            meta, path = line.split('\t', 1)
            _mode, kind, blob = meta.split()
            if kind != 'blob':
                continue
            dest = out_root / path
            if dest.is_file() and git_blob_sha1(dest) == blob:
                source = 'local-verified'
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                if blob in local_blobs:
                    data = subprocess.run(['git', 'cat-file', 'blob', blob], cwd=clone, check=True,
                                          stdout=subprocess.PIPE,
                                          env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'}).stdout
                    dest.write_bytes(data)
                    source = 'git-object-already-local'
                else:
                    url = f'https://raw.githubusercontent.com/sgossner/VCSL/{VCSL_COMMIT}/' + urllib.parse.quote(path)
                    download(url, dest, guard, None)
                    source = 'raw.githubusercontent.com'
                if git_blob_sha1(dest) != blob:
                    raise SystemExit(f'VCSL blob mismatch for {path}')
            rows.append({'file': rel(dest), 'bytes': dest.stat().st_size, 'git_blob_sha1': blob,
                         'sha256': sha256_file(dest), 'retrieved_via': source,
                         'url': f'{VCSL_WEB}/blob/{VCSL_COMMIT}/' + urllib.parse.quote(path)})
        assets.append(base_record(
            asset_id='vcsl/' + folder,
            name=folder.split('/')[-1],
            role=role,
            origin_url=f'{VCSL_WEB}/tree/{VCSL_COMMIT}/' + urllib.parse.quote(folder),
            mirror_url=None,
            authors=['Versilian Studios LLC and VCSL contributors'],
            acquired_at_utc=now(),
            files=rows,
        ))
        print(f'OK vcsl/{folder}: {len(rows)} files, {sum(r["bytes"] for r in rows)/1e6:.1f} MB', flush=True)
    payload = manifest_header('VCSL — Versilian Community Sample Library',
                              'CC0 instrument samples for original music (koto/shakuhachi/taiko stand-ins) and SFX layers',
                              guard, started)
    payload.update({
        'repository': VCSL_WEB,
        'pinned_commit': VCSL_COMMIT,
        'remote_head_at_fetch': head,
        'license_evidence': {
            'LICENSE_first_lines': lic_text.splitlines()[:3],
            'README_statement': 'This collection is under a Creative Commons 0 license. Essentially it\'s Public '
                                'Domain- you can do whatever you want with these sounds (even make commercial '
                                'software), no royalties, no credit, no special terms.',
            'LICENSE_snapshot': lic_snap,
            'README_snapshot': readme_snap,
            'verified_at_utc': now(),
        },
        'integrity': 'each file verified against its git blob id at the pinned commit, then SHA-256 recorded',
        'assets': assets,
    })
    for a in assets:
        a['license_evidence'] = {'see': 'top-level license_evidence (repository LICENSE at pinned commit)'}
    write_manifest('vcsl', payload)


# --------------------------------------------------------------------------------------------
# Wikimedia Commons (per-file license through the API)
# --------------------------------------------------------------------------------------------
def fetch_wikimedia(guard: Guard) -> None:
    started = now()
    assets, reference, skipped = [], [], []
    for title, role, use_policy in WIKIMEDIA_FILES:
        api = ('https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo'
               '&iiprop=url|size|sha1|extmetadata|mime&titles=' + urllib.parse.quote(title))
        data = json.loads(http_text(api))
        page = next(iter(data['query']['pages'].values()))
        if 'imageinfo' not in page:
            skipped.append({'title': title, 'reason': 'missing'})
            continue
        ii = page['imageinfo'][0]
        meta = {k: re.sub('<[^>]+>', '', str(v.get('value', ''))) for k, v in ii.get('extmetadata', {}).items()}
        short = meta.get('LicenseShortName', '')
        code = meta.get('License', '').lower()
        if not (short in ('CC0', 'Public domain') or code in ('cc0', 'pd')):
            skipped.append({'title': title, 'reason': f'license {short!r}'})
            print(f'SKIP wikimedia {title}: {short}', flush=True)
            continue
        dest = RAW / 'wikimedia' / Path(urllib.parse.unquote(urllib.parse.urlparse(ii['url']).path)).name
        dl = download(ii['url'], dest, guard, ii['size'])
        sha1 = hashlib.sha1(dest.read_bytes()).hexdigest()
        if sha1 != ii['sha1']:
            raise SystemExit(f'Wikimedia sha1 mismatch for {title}')
        asset_id = 'wikimedia/' + title
        page_url = 'https://commons.wikimedia.org/wiki/' + urllib.parse.quote(title.replace(' ', '_'))
        is_ref = use_policy.startswith('reference-only')
        record = base_record(
            asset_id=asset_id,
            name=title,
            role=role,
            tier='PUB-CC0' if short == 'CC0' else 'PUB-PD',
            license='CC0-1.0' if short == 'CC0' else 'PDM-1.0',
            license_url=meta.get('LicenseUrl') or CC0_URL,
            origin_url=page_url,
            mirror_url=None,
            access='api',
            authors=[meta.get('Artist', '').strip()],
            license_evidence={'api_url': api, 'LicenseShortName': short, 'License': code,
                              'UsageTerms': meta.get('UsageTerms'), 'Credit': meta.get('Credit', '')[:300],
                              'ImageDescription': meta.get('ImageDescription', '')[:500],
                              'api_snapshot': snapshot('wikimedia-' + title, json.dumps(data, indent=1)),
                              'verified_at_utc': now()},
            acquired_at_utc=now(),
            files=[{**dl, 'upstream_sha1': ii['sha1'], 'mime': ii.get('mime')}],
            use_policy=use_policy,
        )
        record.update(upstream_fields(asset_id, page_url))
        if is_ref:
            record.update(reference_fields(asset_id, page_url, use_policy))
        (reference if is_ref else assets).append(record)
        print(f'OK wikimedia {title}: {short}' + (' (REF)' if is_ref else ''), flush=True)
    payload = manifest_header('Wikimedia Commons (per-file CC0 / public domain only)',
                              'Japanese instrument reference tones for the music sampler', guard, started)
    payload['assets'] = assets
    payload['skipped'] = skipped
    write_manifest('wikimedia', payload)
    ref_payload = manifest_header('Wikimedia Commons (reference-only audio)',
                                  'Timbre references that may be listened to but never sampled or shipped (tier REF)',
                                  guard, started)
    ref_payload['kind'] = 'restricted-manifest'
    ref_payload['assets'] = reference
    write_manifest('wikimedia', ref_payload, restricted=True)


SOURCES = {'kenney': fetch_kenney, 'wikimedia': fetch_wikimedia, 'opengameart': fetch_opengameart, 'vcsl': fetch_vcsl}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--source', action='append', choices=sorted(SOURCES), help='repeatable; default all')
    ap.add_argument('--list', action='store_true', help='print the allowlisted selection and exit')
    ap.add_argument('--budget-gib', type=float, default=LANE_BUDGET_GIB)
    args = ap.parse_args()
    if args.list:
        print('VCSL @', VCSL_COMMIT)
        for f, r in VCSL_FOLDERS:
            print('  ', f, '—', r)
        print('Kenney:', ', '.join(s for s, _ in KENNEY_PACKS))
        print('OpenGameArt:', ', '.join(urllib.parse.unquote(s) for s, _, _ in OGA_ITEMS))
        print('Wikimedia:', ', '.join(t for t, _, _ in WIKIMEDIA_FILES))
        return
    guard = Guard(args.budget_gib)
    print(f'free {guard.start_free:.1f} GiB; raw audio tree {guard.start_lane/1e6:.1f} MB; floor {MIN_FREE_GIB} GiB; '
          f'lane budget {args.budget_gib} GiB', flush=True)
    for name in args.source or ['kenney', 'wikimedia', 'opengameart', 'vcsl']:
        print(f'== {name}', flush=True)
        SOURCES[name](guard)
    print(f'DONE free {free_gib():.1f} GiB; raw audio tree {tree_bytes(RAW)/1e6:.1f} MB', flush=True)


if __name__ == '__main__':
    main()
