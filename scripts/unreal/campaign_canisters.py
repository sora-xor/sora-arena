"""ch07.b08 fuel canisters in the existing authored hangar frame."""
import json

AUTHORED = [{'kind': 'explosive_canister', 'ids': ['fc_01', 'fc_02', 'fc_03'],
             'blast_radius_cm': 360, 'damage': 80, 'hurts_player': True}]
LOCAL_CM = ((2800, 1200), (5200, 1200), (4000, 3800))


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def contract(beat, record):
    if not same(beat['ext']['hazards'], AUTHORED):
        raise ValueError('fuel canisters must retain authored IDs, radius, base damage and player exposure')
    if beat['id'] != 'ch07.b08' or beat['type'] != 'combat_wave' or beat['place'] != 'pl_hangar' or not same(record['height_cm'], 0):
        raise ValueError('fuel canisters require the authored hangar encounter')
    wind = record['wind']
    if wind['kind'] != 'hangar' or not same(wind['origin'], [38000, -2250]):
        raise ValueError('fuel canisters require the current validated hangar frame')
    x, y = wind['origin']
    return {'blast_radius_cm': 360, 'damage': 80, 'hurts_player': True,
            'trigger': 'positive_ranged_hit',
            'items': [{'id': name, 'floor_cm': [x+dx, y+dy, 0]}
                      for name, (dx, dy) in zip(AUTHORED[0]['ids'], LOCAL_CM)]}


def place_canisters(beats, records, fail):
    for beat, record in zip(beats, records):
        if beat['id'] == 'ch07.b08':
            try:
                record['fuel_canisters'] = contract(beat, record)
            except (KeyError, TypeError, ValueError) as error:
                fail(beat['id'], str(error))


def canisters_valid(chapter):
    try:
        if len(chapter['beats']) != len(chapter['space']['beats']): return False
        for beat, record in zip(chapter['beats'], chapter['space']['beats']):
            if record['beat'] != beat['id']: return False
            if beat['id'] != 'ch07.b08':
                if 'fuel_canisters' in record: return False
                continue
            if not same(record['fuel_canisters'], contract(beat, record)): return False
            zone = chapter['space']['zones'][record['zone']]
            if zone['rect'] != [38000, -2250, 46000, 2250]: return False
            # The existing proxy shuttles occupy local X +/-900, Y1800..3200.
            # No provisional 30cm-radius canister may be embedded in that cover.
            for dx, dy in LOCAL_CM:
                if any(abs(dx-sx) < 930 and 1770 < dy < 3230 for sx in (1500, 4000, 6500)): return False
        return True
    except (KeyError, TypeError, ValueError, IndexError):
        return False
