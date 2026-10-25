"""Bind the one horse-defense grenadier to the current shared shell catalog."""
import json
from pathlib import Path
from campaign_horse_treatment import IDS, same

ROOT = Path(__file__).resolve().parents[2]


def contract(beat, record, enemies=None):
    if enemies is None:
        enemies = json.loads((ROOT/'Content/Data/enemies.json').read_text())
    kinds = [e for e in enemies['archetypes'] if e['id'] == 'grenadier']
    if len(kinds) != 1 or kinds[0]['behavior'] != 'grenadier':
        raise ValueError('horse shell requires the current grenadier archetype')
    attacks = kinds[0]['attacks']
    expected = dict(id='arcing_shell', kind='lob', damage=35, radius_cm=300,
                    flight_ms=1400, arming_cm=200, range_cm=[600, 2500])
    if len(attacks) != 1 or not same({k: attacks[0][k] for k in expected}, expected):
        raise ValueError('horse shell drifted from the actual catalog projectile')
    if (beat['id'] != 'ch02.b06' or record['horse_treatment']['targets'] != IDS or
            len(record['pod_arrivals']['arrivals']) != 3 or
            not same([(g['type'], g['count']) for g in beat['task']['waves'][1]['members']],
                     [('enforcer_rifle', 2), ('grenadier', 1)])):
        raise ValueError('horse shell must bind pod B and the two indexed horses')
    return dict(wave=1, archetype='grenadier', attack='arcing_shell', targets=IDS,
                warning_ms=1400, release_interval_ms=6000, flight_ms=1400,
                arming_cm=200, damage=35, radius_cm=300, range_cm=[600, 2500],
                contact='armed_sphere_with_cover')


def place_horse_shell(beats, records, fail):
    for beat, record in zip(beats, records):
        if beat['id'] == 'ch02.b06':
            try:
                record['horse_shell'] = contract(beat, record)
            except (KeyError, TypeError, ValueError) as error:
                fail(beat['id'], str(error))


def horse_shell_valid(chapter, enemies=None):
    try:
        if len(chapter['beats']) != len(chapter['space']['beats']):
            return False
        for beat, record in zip(chapter['beats'], chapter['space']['beats']):
            if beat['id'] != record['beat']:
                return False
            if beat['id'] == 'ch02.b06':
                if not same(record['horse_shell'], contract(beat, record, enemies)):
                    return False
            elif 'horse_shell' in record:
                return False
        return True
    except (KeyError, ValueError, TypeError, IndexError):
        return False
