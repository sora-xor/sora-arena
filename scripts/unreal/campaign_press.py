"""Chapter-six press positions and stamp/inspection contract, in authored cm.

The floor footprint and eight machine positions come from chapter-06 L7.
Catwalk access, patrol timing, machine art and synchronized music require
separate runtime/visual evidence; this contract does not qualify them.
"""
import json

CENTERS = ((800, 500), (1800, 500), (2800, 500), (800, 1200),
           (1800, 1200), (2800, 1200), (1200, 1900), (2400, 1900))
IDS = ('press_a1', 'press_a2', 'press_a3', 'press_b1', 'press_b2', 'press_b3', 'press_c1', 'press_c2')
MASTERS = (1, 4, 6)
LAMP_IDS = tuple('l_die_lamp_'+IDS[i].removeprefix('press_') for i in MASTERS)
MASK = {'source': 'press_stamp', 'period_ms': 1600, 'window_ms': 500,
        'radius_cm': 800, 'player_noise_mult': 0.2}


def same(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def contract(beat, origin):
    if (beat['id'] != 'ch06.b11' or beat['type'] != 'stealth_zone' or beat['place'] != 'pl_press_hall'
            or not same(beat['ext']['noise_mask'], MASK)
            or not same(beat['ext']['press_silent_inspection'], {'auditor_investigates_within_s': 20})
            or not same(beat['params']['light_sources'],
                        [{'id': name, 'extinguishable': 'arrow', 'suspicion_delay_s': 5} for name in LAMP_IDS])
            or beat['task']['objectives'] != ['press_a2', 'press_b2', 'press_c1', 'exit']
            or not same(beat['task']['objective_hold_ms'], [4000, 4000, 4000, 0])):
        raise ValueError('press hall must retain its authored masters, holds, stamp mask and inspection deadline')
    if len(origin) != 2 or any(type(v) is not int for v in origin):
        raise ValueError('press hall origin must be integer cm')
    x, y = origin
    return {'origin_cm': list(origin), 'period_ms': 1600, 'window_ms': 500, 'radius_cm': 800,
            'noise_permille': 200, 'inspection_ms': 20000, 'lamp_suspicion_ms': 5000,
            'presses': [{'id': name, 'center_cm': [x+dx, y+dy],
                         'work_cm': [x+dx, y+dy-240],
                         'objective': MASTERS.index(i) if i in MASTERS else -1}
                        for i, (name, (dx, dy)) in enumerate(zip(IDS, CENTERS))]}


def die_lamps(hall):
    return [{'id': name, 'kind': 'die', 'at': hall['presses'][i]['center_cm'][:],
             'radius_cm': 700, 'snuff': 'shot', 'hold_ms': 0, 'relight_ms': 0}
            for name, i in zip(LAMP_IDS, MASTERS)]


def place_press_hall(beats, records, zones, pickups, fail):
    for beat, record in zip(beats, records):
        if beat['id'] != 'ch06.b11':
            continue
        zone = zones[record['zone']]
        x, y, x1, y1 = zone.rect
        try:
            if (x1-x, y1-y) != (4200, 2400) or record['height_cm'] != 0:
                raise ValueError('press hall needs its authored 42 by 24 m floor')
            hall = contract(beat, [x, y])
        except (KeyError, TypeError, ValueError) as error:
            fail(beat['id'], str(error))
        record['press_hall'] = hall
        # Floor access is provisional until the NW catwalk and ladder are built.
        record['entry'] = [x+200, y+2200, -90]
        record['objectives'] = [hall['presses'][i]['work_cm'][:] for i in MASTERS] + [[x+4000, y+200]]
        record['anchor'] = [x+3500, y+800]
        record['exit'] = {'center': [x+4000, y+200], 'size': [300, 300]}
        zone.cover = []  # The eight runtime machine frames own their collision.
        zone.props = []
        record['spawns'] = [[x+500,y+260], [x+3000,y+1660], [x+1000,y+850],
                            [x+2600,y+1550], [x+4000,y+2000], [x+3300,y+1200]]
        record['patrols'] = [[[x+500,y+260],[x+3000,y+260],[x+3000,y+960],
                              [x+500,y+960],[x+500,y+1660],[x+3000,y+1660]],
                             [[x+500,y+850],[x+3200,y+850],[x+3200,y+1550],[x+500,y+1550]]]
        record['fieldcraft']['lamps'] = die_lamps(hall)
        for volume in record['volumes']:
            if volume['event'] == 'volume_enter:vol_press_floor':
                volume.update(center=[x+2100,y+1200], size=[4000,2200])
            elif volume['event'] == 'volume_enter:vol_press_binding':
                volume.update(center=[x+3600,y+250], size=[800,300])
        for pickup in pickups:
            if pickup['collectible'] == 'ch06.c06':
                pickup['at'] = [x+3600,y+250]


def press_hall_valid(chapter):
    try:
        for beat, record in zip(chapter['beats'], chapter['space']['beats'], strict=True):
            if beat['id'] != record['beat']:
                return False
            if beat['id'] != 'ch06.b11':
                if 'press_hall' in record:
                    return False
                continue
            zone = chapter['space']['zones'][record['zone']]
            x, y, x1, y1 = zone['rect']
            expected = contract(beat, [x, y])
            if ((x1-x, y1-y) != (4200,2400) or not same(record['press_hall'],expected)
                    or not same(record['objectives'],[expected['presses'][i]['work_cm'] for i in MASTERS]+[[x+4000,y+200]])
                    or not same(record['fieldcraft']['lamps'],die_lamps(expected))
                    or zone['cover'] or record['height_cm'] != 0):
                return False
        return True
    except (KeyError, TypeError, ValueError, IndexError):
        return False
