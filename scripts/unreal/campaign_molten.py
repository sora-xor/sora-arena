"""ch05.b15 molten channels. Placement is provisional; authored rates are fixed."""
import json

AUTHORED = {'count': 4, 'cycle_s': 12, 'glow_ramp_s': 2, 'flow_s': 5,
            'player_dps': 35, 'burn_s': 2,
            'enemy_contact': 'loom_automaton destroyed; others 60 dps'}


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def contract(beat, record):
    if not same(beat['ext'], {'hazards': {'molten_channels': AUTHORED}, 'environmental_kills_count': True}):
        raise ValueError('casting channels must retain the complete authored timing/contact/credit contract')
    if beat['type'] != 'combat_wave' or beat['place'] != 'pl_imonoba' or record['height_cm'] != 0:
        raise ValueError('casting channels require the authored casting-floor encounter')
    return {'cycle_ms': 12000, 'warning_ms': 2000, 'flow_ms': 5000,
            'player_dps': 35, 'burn_ms': 2000, 'burn_dps': 35,
            'burn_rate_interpretation': 'same_as_contact_nonstacking_refresh',
            'enemy_dps': 60, 'destroy_enemy': 'loom_automaton',
            'environmental_kills_count': True, 'floor_z_cm': 0,
            'channels': [{'center': [68200, y], 'size': [2500, 80]} for y in (-1000, -350, 350, 1000)],
            'provisional_placement': True}


def place_molten(beats, records, fail):
    for beat, record in zip(beats, records):
        if beat['id'] == 'ch05.b15':
            try:
                record['molten_channels'] = contract(beat, record)
            except (KeyError, TypeError, ValueError) as error:
                fail(beat['id'], str(error))


def molten_valid(chapter):
    try:
        for beat, record in zip(chapter['beats'], chapter['space']['beats']):
            if beat['id'] != 'ch05.b15':
                if 'molten_channels' in record: return False
                continue
            if not same(record['molten_channels'], contract(beat, record)): return False
            zone = chapter['space']['zones'][record['zone']]
            if zone['rect'] != [66400, -1300, 70000, 1300]: return False
            for strip in record['molten_channels']['channels']:
                x, y = strip['center']; w, h = strip['size']
                if any(abs(x-cx) < (w+sx)/2 and abs(y-cy) < (h+sy)/2
                       for cx, cy, sx, sy, _ in zone['cover']): return False
        return True
    except (KeyError, TypeError, ValueError, IndexError):
        return False
