#!/usr/bin/env python3
"""Validate Content/Data/audio.json against the game it drives.

USoraAudioSubsystem loads the file fail-closed; this host check makes sure
that what it loads is complete and means what it says. It fails when:

1. the file differs from a fresh ``scripts/audio/build_audio_data.py`` build,
   or has another schema, or stray or missing top-level fields;
2. the bus tree is not the ESoraAudioBus sliders under one Master, a submix
   parent is neither Master nor the bus's own parent, or a floored (telegraph)
   bus does not route straight to Master with a floor below 0 dB;
3. a cue names an unknown bus or attenuation preset, is spatial without a
   preset, plays a wave neither an OWN manifest nor the CC0 derivatives'
   ledger records (or a one-shot as a loop), is ready or a placeholder without
   waves, is ready-cc0 or placeholder-cc0 with other than CC0 derivatives (or
   plays a derivative under any other status), says nothing
   about the sound it still needs (a placeholder included), carries a caption that has no
   ``NSLOCTEXT("SoraArena.SoundCaptions", ...)`` with an English subtitle in
   Game.po, marks a looping or 3D stinger, a strike mark off the telegraph
   bus or past its wave, or a broken sustain;
4. an event family is not the USoraGameEvents delegates plus Kernel, UI,
   Hero, Footstep, Horse and Workshop, a family has no rule and no reason, a rule tests
   a field its family does not carry or a value its enum lacks, or forwards to
   an unknown family; a practice kernel event kind is neither bound nor
   explained; a catalog weapon has no firing or swing rule;
5. a cue is neither played by a rule, a sustain, the music, the ambience or
   an attached loop nor explained as unbound, or an unbound cue is played;
6. the music lacks one of its five states, a piece's stems differ in length
   or are not a whole number of bars, or the title handoff is not its bars;
7. the beats are not exactly the chapter files' beats with their places and
   music ids, or a beat or map names an unknown state, bed, weather or surface;
8. an attack of bosses.json or enemies.json has no telegraph class, or a
   horse gait, footstep surface, material role or attached archetype is unknown.

  python3 scripts/audio/validate_audio_data.py
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_audio_data  # noqa: E402

DATA = ROOT / 'Content/Data'
AUDIO_JSON = DATA / 'audio.json'
SOURCE = 'Content/SourceArt/Audio'
EVENTS_HEADER = ROOT / 'Source/SoraArena/Public/SoraGameEvents.h'
SETTINGS_HEADER = ROOT / 'Source/SoraArena/Public/SoraSettings.h'
MOUNT_HEADER = ROOT / 'Source/SoraArena/Public/SoraMountRules.h'
ARENA_HEADER = ROOT / 'crates/arena-ffi/include/arena.h'
CAPTION_SOURCES = ROOT / 'Source/SoraArena/Private/Audio'
GAME_PO = ROOT / 'Content/Localization/Game/en/Game.po'
OWN_MANIFESTS = (ROOT / SOURCE / 'Original/manifest.json', ROOT / SOURCE / 'Music/manifest.json')
CC0_MANIFEST = ROOT / SOURCE / 'CC0/manifest.json'
READY = ('ready-own', 'ready-cc0')
TOP = {'schema_version', 'source', 'sample_rate_hz', 'buses', 'ducking', 'attenuation', 'cues', 'bindings',
       'unbound_events', 'music', 'beats', 'maps', 'weather', 'footsteps', 'horses', 'attached', 'telegraphs'}
STATES = {'menu', 'exploration', 'stealth', 'combat', 'boss'}
SPARRING = {'', 'bokuto', 'fukuro_shinai'}
TELEGRAPH_CLASSES = {'none', 'lock', 'cleave', 'area', 'margin_call', 'reload'}
# What the subsystem polls rather than hears; OnKernelEvent and OnUISound are
# the Kernel and UI families.
POLLED = {'Hero', 'Footstep', 'Horse', 'Workshop'}
RENAMED = {'KernelEvent': 'Kernel', 'UISound': 'UI'}
HERO_ACTIONS = {'ReloadStarted', 'ChargeStarted', 'ChargeHeld', 'BowDrawn', 'Sheathed', 'Drawn'}
HORSE_ACTIONS = {'Hoof', 'Spooked', 'Mounted', 'Dismounted'}
PACES = {'crouch', 'walk', 'run'}
ERRORS: list[str] = []


def error(message):
    ERRORS.append(message)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def enum_values(text, name):
    match = re.search(r'enum class ' + name + r'\s*:\s*\w+(?:\s+\w+)?\s*\{(.*?)\};', text, re.S)
    if not match:
        sys.exit(f'validate_audio_data: {name} not found')
    body = re.sub(r'//[^\n]*', '', match.group(1))
    return [item.strip().split('=')[0].strip() for item in body.split(',') if item.strip()]


def delegates(text):
    """USoraGameEvents' delegate members, without their On prefix."""
    body = text[text.index('class SORAARENA_API USoraGameEvents'):]
    names = [name[2:] for name in re.findall(r'^\s+FSora\w+Signature (On\w+);', body, re.M)]
    return [RENAMED.get(name, name) for name in names]


def kernel_kinds(text):
    names = re.findall(r'#define ARENA_EVENT_([A-Z_]+) \d+u', text)
    return [''.join(part.capitalize() for part in name.split('_')) for name in names]


def caption_keys():
    keys = {}
    pattern = re.compile(r'NSLOCTEXT\(\s*"SoraArena\.SoundCaptions"\s*,\s*"([A-Za-z0-9_.]+)"\s*,\s*"([^"]*)"\s*\)')
    for path in sorted(CAPTION_SOURCES.glob('*.cpp')):
        for key, japanese in pattern.findall(path.read_text(encoding='utf-8')):
            keys[key] = japanese
    return keys


def translated(key):
    text = GAME_PO.read_text(encoding='utf-8')
    match = re.search(r'msgctxt "SoraArena\.SoundCaptions,' + re.escape(key) + r'"\nmsgid "[^"]*"\nmsgstr "([^"]*)"',
                      text)
    return bool(match and match.group(1))


def project_waves():
    """Every wave the import makes: the OWN renders and the CC0 derivatives, by audio.json path."""
    records = [record for manifest in OWN_MANIFESTS for record in read(manifest)['files']]
    records += [row for record in read(CC0_MANIFEST)['records'] for row in record['files']]
    return {record['file'][len(SOURCE) + 1:-4]: record for record in records if record['file'].endswith('.wav')}


def check_buses(data, sliders):
    buses = {bus['id']: bus for bus in data['buses']}
    roots = [bus['id'] for bus in data['buses'] if not bus['parent']]
    if roots != ['Master']:
        error(f'the bus tree needs Master as its only root: {roots}')
    for bus in data['buses']:
        if bus['parent'] and bus['parent'] not in buses:
            error(f"bus {bus['id']} has an unknown parent {bus['parent']}")
        if bus['submix_parent'] not in ('Master', bus['parent']) and bus['id'] != 'Master':
            error(f"bus {bus['id']} routes its submix to {bus['submix_parent']}")
        if bus['floor_of']:
            if bus['submix_parent'] != 'Master' or not bus['floor_db'] < 0.0 or bus['floor_of'] not in buses:
                error(f"floored bus {bus['id']} must feed Master with a floor below 0 dB of a known slider bus")
            if not buses.get(bus['floor_of'], {}).get('slider'):
                error(f"bus {bus['id']} floors a bus without a slider")
        elif bus['submix_parent'] != bus['parent']:
            error(f"bus {bus['id']} bypasses its parent without a floor")
    got = [bus['slider'] for bus in data['buses'] if bus['slider']]
    if sorted(got) != sorted(sliders) or any(buses[name]['slider'] != name for name in sliders if name in buses):
        error(f'the user sliders must be the ESoraAudioBus buses {sliders}: {got}')
    return buses


def check_cues(data, buses, waves, captions):
    cues = {}
    for cue in data['cues']:
        name = cue['id']
        if name in cues:
            error(f'duplicate cue {name}')
        cues[name] = cue
        if cue['bus'] not in buses:
            error(f'{name}: unknown bus {cue["bus"]}')
        if cue['attenuation'] and cue['attenuation'] not in data['attenuation']:
            error(f'{name}: unknown attenuation {cue["attenuation"]}')
        if cue['spatial'] != bool(cue['attenuation']):
            error(f'{name}: spatial cues and only they name an attenuation preset')
        if cue['max_instances'] < 1:
            error(f'{name}: needs at least one instance')
        if cue['pitch_cents'][0] > cue['pitch_cents'][1] or cue['volume_db'][0] > cue['volume_db'][1] \
                or cue['volume_db'][1] > 0.0:
            error(f'{name}: pitch and volume ranges must be ordered and never boost')
        for wave in cue['waves']:
            record = waves.get(wave)
            if record is None:
                error(f'{name}: no OWN manifest or CC0 ledger records {wave}')
            elif record['loop'] != cue['loop']:
                error(f'{name}: {wave} loop flag {record["loop"]} differs from the cue {cue["loop"]}')
            if (cue['status'] in ('ready-cc0', 'placeholder-cc0')) != wave.startswith('CC0/'):
                error(f'{name}: status {cue["status"]} does not match its wave {wave}')
        if (not cue['waves'] or cue['status'] not in READY) and not cue['needs']:
            error(f'{name}: says nothing about the sound it still needs')
        if (cue['status'] in READY or cue['status'] == 'placeholder-cc0') and not cue['waves']:
            error(f'{name}: is {cue["status"]} without waves')
        if cue['caption']:
            if cue['caption'] not in captions:
                error(f'{name}: caption {cue["caption"]} has no NSLOCTEXT("SoraArena.SoundCaptions", ...)')
            elif not translated(cue['caption']):
                error(f'{name}: caption {cue["caption"]} has no English subtitle in Game.po')
            if not cue['waves']:
                error(f'{name}: captions a sound that does not exist yet')
        if cue['stinger'] and (cue['loop'] or cue['spatial']):
            error(f'{name}: a stinger is a 2D one-shot')
        if cue['strike_ms']:
            if cue['bus'] != 'SFX_Telegraph':
                error(f'{name}: only telegraphs carry a strike mark')
            for wave in cue['waves']:
                if wave in waves and cue['strike_ms'] >= waves[wave]['qa']['seconds'] * 1000:
                    error(f'{name}: the strike mark is past the end of {wave}')
        if cue['sustain']:
            for part, looping in (('loop', True), ('release', False)):
                target = cue['sustain'][part]
                if target not in {c['id'] for c in data['cues']}:
                    error(f'{name}: sustain {part} {target} is not a cue')
                elif next(c for c in data['cues'] if c['id'] == target)['loop'] != looping:
                    error(f'{name}: sustain {part} {target} must {"" if looping else "not "}loop')
            if cue['sustain']['gap_ms'] <= 0:
                error(f'{name}: sustain gap must be positive')
    unused = sorted(set(captions) - {cue['caption'] for cue in cues.values()})
    if unused:
        error(f'caption texts no cue uses: {unused}')
    return cues


def family_fields(enums):
    shot = enums['ESoraShotKind']
    phase = enums['ESoraBossPhase']
    enemy = enums['ESoraEnemyCue']
    boolean = [True, False]
    return {
        'WeaponFired': {'WeaponId': int, 'Kind': shot, 'ShooterIsHero': boolean},
        'MeleeCommitted': {'WeaponId': int, 'WindupSeconds': float, 'AttackerIsHero': boolean, 'Sparring': SPARRING},
        'StrikeResolved': {'WeaponId': int, 'bHit': boolean, 'Damage': float, 'AttackerIsHero': boolean,
                           'TargetIsHero': boolean, 'Sparring': SPARRING},
        'Guarded': {'bDojo': boolean, 'HeldMs': int, 'Damage': float, 'DefenderIsHero': boolean,
                    'AttackerIsHero': boolean},
        'Parried': {'bDojo': boolean, 'HeldMs': int, 'Damage': float, 'DefenderIsHero': boolean,
                    'AttackerIsHero': boolean},
        'Marobashi': {'bAfterAwase': boolean},
        'Damaged': {'VictimIsHero': boolean, 'CauserIsHero': boolean, 'Amount': float, 'HealthAfter': float},
        'Died': {'VictimIsHero': boolean, 'KillerIsHero': boolean, 'bSparring': boolean},
        'Detonated': {'Radius': float, 'Damage': float},
        'EnemyCue': {'Cue': enemy, 'Archetype': str, 'Detail': str, 'Telegraph': TELEGRAPH_CLASSES},
        'SiteRestored': {'ChapterId': int, 'SiteIndex': int, 'Kind': str, 'bCampaign': boolean},
        'ChapterStarted': {'ChapterId': int, 'bResumed': boolean, 'bLiberated': boolean},
        'ChapterCompleted': {'ChapterId': int, 'bResumed': boolean, 'bLiberated': boolean},
        'BossPhase': {'Phase': phase, 'bBeam': boolean, 'BossId': str, 'PhaseIndex': int, 'Detail': str,
                      'Telegraph': TELEGRAPH_CLASSES, 'WindupMs': int},
        'BeatStarted': {'ChapterId': int, 'BeatId': str, 'bResumed': boolean, 'Phase': int, 'bOptional': boolean},
        'BeatCompleted': {'ChapterId': int, 'BeatId': str, 'bResumed': boolean, 'Phase': int, 'bOptional': boolean},
        'BeatFailed': {'ChapterId': int, 'BeatId': str, 'bResumed': boolean, 'Phase': int, 'bOptional': boolean},
        'Kernel': {'Kind': enums['Kernel'], 'WeaponId': int, 'WeaponKind': str, 'ActorIsHero': boolean,
                   'TargetIsHero': boolean, 'Detail': int, 'HeroWon': boolean},
        'UI': {'Sound': enums['ESoraUISound']},
        'Hero': {'Action': HERO_ACTIONS, 'WeaponId': int, 'IsHero': boolean},
        'Footstep': {'Surface': set(), 'Pace': PACES, 'IsHero': boolean},
        'Horse': {'Action': HORSE_ACTIONS, 'Gait': enums['EGait']},
        'Workshop': {'Action': {'HammerCue', 'HammerHit', 'LoomCall'}},
    }


def value_fits(allowed, value):
    if allowed is int:
        return isinstance(value, int) and not isinstance(value, bool) or (
            isinstance(value, str) and re.fullmatch(r'(<|<=|>|>=|!)-?\d+', value))
    if allowed is float:
        return isinstance(value, (int, float)) and not isinstance(value, bool) or (
            isinstance(value, str) and re.fullmatch(r'(<|<=|>|>=)-?\d+(\.\d+)?', value))
    if allowed is str:
        return isinstance(value, str) and value != ''
    if isinstance(value, str) and value.startswith('!'):
        value = value[1:]
    return value in allowed


def matches(when, facts):
    for field, expected in when.items():
        values = expected if isinstance(expected, list) else [expected]
        actual = facts.get(field)
        if actual is None:
            return False
        if isinstance(values[0], str) and values[0][:1] in '<>':
            match = re.fullmatch(r'(<=|>=|<|>)(-?[\d.]+)', values[0])
            op, bound = match.group(1), float(match.group(2))
            if not {'<': actual < bound, '<=': actual <= bound, '>': actual > bound, '>=': actual >= bound}[op]:
                return False
        elif actual not in values:
            return False
    return True


def check_bindings(data, cues, enums, fields):
    families = delegates_list = enums['delegates']
    expected = set(families) | POLLED
    got = set(data['bindings'])
    if got != expected:
        error(f'event families differ from the game: missing {sorted(expected - got)}, extra {sorted(got - expected)}')
    fields['Footstep']['Surface'] = set(data['footsteps']['surfaces'])
    unbound = data['unbound_events']
    for family in sorted(expected):
        rules = data['bindings'].get(family, [])
        if not rules and family not in unbound:
            error(f'event family {family} has no rule and no reason')
        if rules and family in unbound:
            error(f'event family {family} is bound and explained as unbound')
        for index, rule in enumerate(rules):
            where = f'{family}[{index}]'
            if set(rule) not in ({'when', 'cue', 'continue', 'delay_ms'}, {'when', 'as', 'continue', 'delay_ms'}):
                error(f'{where}: a rule has when, cue or as, continue and delay_ms: {sorted(rule)}')
                continue
            if 'cue' in rule and rule['cue'] not in cues:
                error(f'{where}: unknown cue {rule["cue"]}')
            if 'as' in rule and (family != 'Kernel' or rule['as'] not in set(delegates_list) - {'Kernel', 'UI'}):
                error(f'{where}: only kernel rules forward, and only to a USoraGameEvents family')
            if rule['delay_ms'] < 0:
                error(f'{where}: negative delay')
            for field, value in rule['when'].items():
                allowed = fields.get(family, {}).get(field)
                if allowed is None:
                    error(f'{where}: {family} has no field {field}')
                    continue
                for item in value if isinstance(value, list) else [value]:
                    if not value_fits(allowed, item):
                        error(f'{where}: {field} cannot be {item!r}')
    for kind in enums['Kernel']:
        bound = any(matches(rule['when'], {'Kind': kind}) or rule['when'].get('Kind') == kind
                    or kind in (rule['when'].get('Kind') or [])
                    for rule in data['bindings'].get('Kernel', []))
        if not bound and f'Kernel.{kind}' not in unbound:
            error(f'kernel event {kind} is neither bound nor explained')
    for key in unbound:
        if key.startswith('Kernel.') and key[7:] not in enums['Kernel']:
            error(f'unbound kernel event {key} does not exist')
        elif not key.startswith('Kernel.') and key not in expected:
            error(f'unbound event family {key} does not exist')

    catalog = read(DATA / 'catalog.json')
    for weapon in catalog['weapons']:
        family = 'MeleeCommitted' if weapon['kind'] == 'melee' else 'WeaponFired'
        facts = {'WeaponId': weapon['id'], 'Kind': 'Arrow' if weapon['kind'] == 'bow' else
                 'Shell' if weapon['kind'] == 'explosive' else 'Hitscan', 'WindupSeconds': 0.3, 'Sparring': '',
                 'ShooterIsHero': True, 'AttackerIsHero': True}
        hits = [rule for rule in data['bindings'][family] if 'cue' in rule and matches(rule['when'], facts)]
        if not hits:
            error(f'catalog weapon {weapon["id"]} {weapon["name_en"]} has no {family} rule')
        elif family == 'WeaponFired' and not hits[0]['cue'].endswith(
                re.sub(r'[^a-z]+', '_', weapon['name_en'].lower().replace('ō', 'o')).strip('_')):
            error(f'catalog weapon {weapon["id"]} {weapon["name_en"]} plays {hits[0]["cue"]}')


def played_cues(data):
    played = {rule['cue'] for rules in data['bindings'].values() for rule in rules if 'cue' in rule}
    for cue in data['cues']:
        if cue['sustain'] and cue['id'] in played:
            played |= {cue['sustain']['loop'], cue['sustain']['release']}
    for beat in list(data['beats'].values()) + list(data['maps'].values()):
        played |= {beat['bed'], data['weather'][beat['weather']]}
    played |= set(data['attached'].values())
    if any(beat['thunder_s'] for beat in data['beats'].values()):
        played.add('amb.thunder')
    return played - {''}


def check_coverage(data, cues):
    played = played_cues(data)
    for name, cue in cues.items():
        if cue['unbound'] and name in played:
            error(f'{name} is played but explained as unbound')
        if not cue['unbound'] and name not in played:
            error(f'{name} is never played and not explained')
    music = set()
    for piece in data['music']['pieces'].values():
        music |= set(piece['stems'].values()) | {piece['intro'], piece['full']}
    referenced = {wave for cue in cues.values() for wave in cue['waves']} | (music - {''})
    missing = sorted(set(project_waves()) - referenced)
    if missing:
        error(f'waves no cue or piece plays (the import needs each): {missing[:5]}')


def check_music(data, waves):
    music = data['music']
    if set(music['states']) != STATES:
        error(f'music states must be {sorted(STATES)}: {sorted(music["states"])}')
    for name, piece in music['pieces'].items():
        bar = piece['beats_per_bar'] * 60.0 / piece['bpm']
        lengths = set()
        for stem in list(piece['stems'].values()) + ([piece['full']] if piece['full'] else []):
            record = waves.get(stem)
            if record is None:
                error(f'piece {name}: no OWN manifest records {stem}')
                continue
            if not record['loop']:
                error(f'piece {name}: {stem} does not loop')
            lengths.add(round(record['qa']['seconds'], 3))
            bars = record['qa']['seconds'] / bar
            if abs(bars - round(bars)) > 0.001:
                error(f'piece {name}: {stem} is {bars:.4f} bars, not whole bars')
        if len(lengths) > 1:
            error(f'piece {name}: stems differ in length {sorted(lengths)}')
        if piece['intro']:
            record = waves.get(piece['intro'])
            handoff = piece['handoff_bars'] * bar * data['sample_rate_hz']
            if record is None or record['loop']:
                error(f'piece {name}: the intro {piece["intro"]} must be a recorded one-shot')
            elif abs(handoff - piece['handoff_sample']) > 1.0 or piece['handoff_sample'] >= record['qa']['seconds'] \
                    * data['sample_rate_hz']:
                error(f'piece {name}: handoff at sample {piece["handoff_sample"]} is not {piece["handoff_bars"]} bars '
                      f'({handoff:.1f}) inside the intro')
    for name, state in music['states'].items():
        piece = music['pieces'].get(state['piece'])
        if piece is None:
            error(f'music state {name}: unknown piece {state["piece"]}')
            continue
        if state['intro'] and not piece['intro']:
            error(f'music state {name}: {state["piece"]} has no intro')
        mixes = list(state['mixes'].values()) + state['phase_mixes']
        if 'default' not in state['mixes']:
            error(f'music state {name}: needs a default mix')
        for mix in mixes:
            if not mix or set(mix) - set(piece['stems']):
                error(f'music state {name}: mix {mix} names stems {state["piece"]} lacks')
    levels = music['alert_levels']
    if set(levels) != {'unaware', 'retreat', 'suspicious', 'search', 'alert', 'combat'}:
        error(f'alert levels must name every AlertState detail: {sorted(levels)}')
    stealth = music['states']['stealth']['mixes']
    for detail, level in levels.items():
        if level < 3 and detail != 'retreat' and detail not in stealth:
            error(f'the stealth state has no mix for {detail}')


def check_places(data, cues):
    surfaces = set(data['footsteps']['surfaces'])
    beds = {name for name, cue in cues.items() if cue['loop'] and cue['bus'] in ('Ambience', 'SFX_Alien')}
    for name, bed in data['weather'].items():
        if bed and bed not in beds:
            error(f'weather {name} plays {bed}, which is not an ambience loop')
    beats = {}
    for chapter in range(1, 9):
        for beat in read(DATA / f'campaign/chapter_0{chapter}.json')['beats']:
            beats[beat['id']] = (chapter, beat['place'], beat['music'] or '')
    if set(beats) != set(data['beats']):
        error(f'beats differ from the chapter files: {sorted(set(beats) ^ set(data["beats"]))[:5]}')
    rows = list(data['beats'].items()) + [(f'map {key}', value) for key, value in data['maps'].items()]
    for name, row in rows:
        if name in beats and (row['chapter'], row['place'], row['music_id']) != beats[name]:
            error(f'beat {name} disagrees with its chapter file')
        if name in beats and (row['state'] not in STATES or row['sparring'] not in SPARRING):
            error(f'beat {name}: unknown music state or sparring weapon')
        if row['bed'] and row['bed'] not in beds:
            error(f'{name}: bed {row["bed"]} is not an ambience loop')
        if row['weather'] not in data['weather']:
            error(f'{name}: unknown weather {row["weather"]}')
        if row['surface'] not in surfaces:
            error(f'{name}: unknown surface {row["surface"]}')
    maps = read(DATA / 'catalog.json')['maps']
    if sorted(data['maps']) != sorted(str(index) for index in range(len(maps))):
        error(f'maps must cover the catalog arenas 0-{len(maps) - 1}')


def check_rest(data, cues, enums):
    footsteps = data['footsteps']
    rules = {rule['when'].get('Surface') for rule in data['bindings']['Footstep']}
    if set(footsteps['surfaces']) != rules:
        error('every footstep surface needs its Footstep rule')
    for surface, cue in footsteps['surfaces'].items():
        if cue not in cues:
            error(f'surface {surface} plays unknown cue {cue}')
    for role, surface in footsteps['materials'].items():
        if surface not in footsteps['surfaces']:
            error(f'material {role} maps to unknown surface {surface}')
    if set(footsteps['stride_cm']) != PACES or set(footsteps['pace_db']) != PACES:
        error('footsteps need a stride and a level for crouch, walk and run')
    gaits = set(enums['EGait']) - {'Halt'}
    if set(data['horses']['hoofbeats_per_s']) != gaits:
        error(f'horse cadence must cover {sorted(gaits)}')
    archetypes = {item['id'] for item in read(DATA / 'enemies.json')['archetypes']}
    for archetype, cue in data['attached'].items():
        if archetype not in archetypes or cue not in cues or not cues[cue]['loop']:
            error(f'attached loop {archetype} -> {cue} needs a known archetype and a looping cue')
    telegraphs = data['telegraphs']
    bosses = read(DATA / 'bosses.json')
    expected = {f"{boss['id']}/{attack['id']}" for boss in bosses['bosses'] + bosses['duels']
                for attack in boss['attacks']}
    if set(telegraphs['boss']) != expected:
        error('boss telegraphs differ from bosses.json attacks')
    enemy = {attack['cue'] for item in read(DATA / 'enemies.json')['archetypes'] for attack in item.get('attacks', [])}
    if set(telegraphs['enemy']) != enemy:
        error('enemy telegraphs differ from enemies.json attack cues')
    for table in (telegraphs['boss'], telegraphs['enemy']):
        for key, row in table.items():
            if row['class'] not in TELEGRAPH_CLASSES:
                error(f'telegraph {key}: unknown class {row["class"]}')
    if len(telegraphs['windup_permille']) != 3:
        error('windup scaling needs Easy, Normal and Hard')


def main():
    data = read(AUDIO_JSON)
    if AUDIO_JSON.read_text(encoding='utf-8') != build_audio_data.render(build_audio_data.build()):
        error('Content/Data/audio.json differs from a fresh build_audio_data.py build')
    if data.get('schema_version') != 1 or set(data) != TOP:
        error(f'audio.json needs schema 1 and exactly {sorted(TOP)}')
        sys.exit('\n'.join(ERRORS))
    events = EVENTS_HEADER.read_text(encoding='utf-8')
    enums = {name: enum_values(events, name) for name in ('ESoraShotKind', 'ESoraBossPhase', 'ESoraEnemyCue',
                                                          'ESoraUISound')}
    enums['EGait'] = enum_values(MOUNT_HEADER.read_text(encoding='utf-8'), 'EGait')
    enums['Kernel'] = kernel_kinds(ARENA_HEADER.read_text(encoding='utf-8'))
    enums['delegates'] = delegates(events)
    sliders = enum_values(SETTINGS_HEADER.read_text(encoding='utf-8'), 'ESoraAudioBus')[:-1]
    waves = project_waves()
    buses = check_buses(data, sliders)
    captions = caption_keys()
    cues = check_cues(data, buses, waves, captions)
    fields = family_fields(enums)
    check_bindings(data, cues, enums, fields)
    check_coverage(data, cues)
    check_music(data, waves)
    check_places(data, cues)
    check_rest(data, cues, enums)
    if not all(math.isfinite(preset['inner_m']) and 0 < preset['inner_m'] < preset['falloff_m']
               for preset in data['attenuation'].values()):
        error('attenuation presets need 0 < inner < falloff')
    if ERRORS:
        sys.exit('validate_audio_data: ' + str(len(ERRORS)) + ' problems\n  ' + '\n  '.join(ERRORS))
    voiced = sum(1 for cue in data['cues'] if cue['waves'])
    print(f'AUDIO_DATA_OK: {len(data["cues"])} cues ({voiced} voiced), '
          f'{sum(len(rules) for rules in data["bindings"].values())} rules in {len(data["bindings"])} families, '
          f'{len(data["beats"])} beats, {len(captions)} captions')


if __name__ == '__main__':
    main()
