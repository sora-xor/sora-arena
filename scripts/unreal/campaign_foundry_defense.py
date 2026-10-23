"""The authored ch05.b07 supplies, rescue and furnace-pressure contract."""
import copy
import json

def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


TUBS = ['clay_tub_w', 'clay_tub_e', 'clay_tub_n']
CREW = ['bellows_boy', 'bellows_worker']


def contract(beat, record):
    if not same(beat['params']['defend'], {
            'targets': [{'actor': 'tatara_furnace', 'hp': 1500}, {'actor': 'npc:kozo', 'hp': 300}],
            'duration_s': 180, 'fail_on_target_destroyed': True,
            'repair_interact': {'actors': TUBS, 'hold_s': 3, 'heal': 150, 'uses_each': 1}}):
        raise ValueError('foundry targets, duration and finite clay repairs must retain authored values')
    if not same(beat['ext'], {'kozo': {'downable': True, 'revive_s': 4, 'fail_after_down_s': 25},
            'grenadier_target_priority': 'tatara_furnace',
            'drone_behavior': 'seizure_net on bellows crew; netted crew stop the bellows (furnace takes 5 HP/s until freed)'}):
        raise ValueError('foundry rescue and enemy pressure must retain the complete authored contract')
    x, y = record['targets'][0]
    return {'furnace_target': 0, 'kozo_target': 1, 'repair_ms': 3000, 'repair_hp': 150,
            'revive_ms': 4000, 'down_limit_ms': 25000, 'crew_drain_hp_s': 5,
            'tubs': [{'id': name, 'at': [x+dx, y+dy]} for name, (dx, dy) in
                     zip(TUBS, [(-380, -380), (380, -380), (0, 380)])],
            'crew': [{'id': name, 'at': [x+dx, y+700]} for name, dx in zip(CREW, [-160, 160])],
            'provisional_placement': True}


def place_foundry_defense(beats, records, fail):
    for beat, record in zip(beats, records):
        if beat['id'] != 'ch05.b07':
            continue
        try:
            row = contract(beat, record)
        except (KeyError, TypeError, ValueError) as error:
            fail(beat['id'], str(error))
        record['foundry_defense'] = row
        # Kōzō remains the first defended person. Runtime configures his real
        # companion HP; two workmates use the existing person-quarry nets.
        craft = record['fieldcraft']
        craft['people'] = [{'id': 'kozo', 'target': 1, 'at': record['targets'][1]}] + [
            {'id': c['id'], 'target': -1, 'at': c['at'], 'cover': c['at']} for c in row['crew']]
        craft['nets'] = {'quarry': [{'id': c['id'], 'kind': 'person', 'index': i+1, 'hp': 0}
                                   for i, c in enumerate(row['crew'])],
                         'windup_ms': 800, 'haul_ms': 0, 'cut_ms': 1000, 'saddle_weapon': -1,
                         'saddle_side': 0, 'tether': True, 'halts': False, 'net_waves': [2],
                         'nets_per_wave': [2], 'scout_waves': [], 'cross_wave': -1,
                         'cross_at_cm': 0, 'lost_event': None}


def _strict(value):
    if isinstance(value, dict):
        return all(_strict(v) for v in value.values())
    if isinstance(value, list):
        return all(_strict(v) for v in value)
    return value is None or type(value) in (str, int, bool)


def foundry_valid(chapter):
    try:
        for beat, record in zip(chapter['beats'], chapter['space']['beats']):
            if beat['id'] != 'ch05.b07':
                if 'foundry_defense' in record:
                    return False
                continue
            expected = copy.deepcopy(record)
            place_foundry_defense([beat], [expected], lambda *args: (_ for _ in ()).throw(ValueError(args)))
            # JSON text comparison distinguishes true, 1 and 1.0.
            if (not _strict(record['foundry_defense']) or not same(record['foundry_defense'], expected['foundry_defense']) or
                    not same(record['fieldcraft']['people'], expected['fieldcraft']['people']) or
                    not same(record['fieldcraft']['nets'], expected['fieldcraft']['nets']) or
                    beat['task']['duration_ms'] != 180000 or beat['task']['goal'] != 'survive' or
                    record['zone'] < 0 or record['height_cm'] != 0):
                return False
            zone = chapter['space']['zones'][record['zone']]
            for point in [t['at'] for t in record['foundry_defense']['tubs'] + record['foundry_defense']['crew']]:
                x, y = point
                if not zone['rect'][0]+100 < x < zone['rect'][2]-100 or not zone['rect'][1]+100 < y < zone['rect'][3]-100:
                    return False
                if any(abs(x-cx) <= sx/2+100 and abs(y-cy) <= sy/2+100 for cx, cy, sx, sy, _ in zone['cover']):
                    return False
        return True
    except (KeyError, ValueError, TypeError, IndexError):
        return False
