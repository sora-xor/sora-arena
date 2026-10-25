"""The authored two-horse treatment contract for ch02.b06."""
import json

IDS = ['pack_horse_a', 'pack_horse_b']


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def contract(beat, record):
    if not same(beat['params']['defend'], {
            'targets': [{'actor': name, 'hp': 400} for name in IDS],
            'duration_s': 150, 'fail_on_target_destroyed': True,
            'repair_interact': {'kind': 'treat_horse', 'hold_s': 2.0, 'heal': 60, 'cooldown_s': 20}}):
        raise ValueError('horse defense must retain its two targets and authored held treatment')
    if (beat['task']['goal'] != 'survive' or beat['task']['duration_ms'] != 150000 or
            not same(beat['task']['targets'], [{'id': name, 'hp': 400} for name in IDS]) or
            record['kit']['targets'] != ['horse', 'horse'] or len(record['targets']) != 2):
        raise ValueError('horse treatment must bind the actual two defended horse targets')
    return dict(targets=IDS, hold_ms=2000, heal_hp=60, cooldown_ms=20000, cooldown_scope='per_horse')


def place_horse_treatment(beats, records, fail):
    for beat, record in zip(beats, records):
        if beat['id'] == 'ch02.b06':
            try:
                record['horse_treatment'] = contract(beat, record)
            except (KeyError, TypeError, ValueError) as error:
                fail(beat['id'], str(error))


def horse_treatment_valid(chapter):
    try:
        for beat, record in zip(chapter['beats'], chapter['space']['beats']):
            if beat['id'] == 'ch02.b06':
                if not same(record['horse_treatment'], contract(beat, record)):
                    return False
            elif 'horse_treatment' in record:
                return False
        return True
    except (KeyError, ValueError, TypeError):
        return False
