"""Bind ch02.b06's named pod arrivals and defended horses to the estate frame."""
import json

FRAME = 'pl_estate_night'
PODS = [('sp_pod_a_road', [-200, 200, 0], 0),
        ('sp_pod_b_north', [-600, 1100, 0], 45000),
        ('sp_pod_c_west', [-1900, -300, 0], 95000)]
HORSES = [('pack_horse_a', [800, -1050, 0]), ('pack_horse_b', [1200, -1050, 0])]
OFFSETS = [[-110, -60], [110, -60], [0, 120]]
HAZARD = [dict(kind='drop_pod_impact', telegraph='amber_ring', radius_cm=350,
               windup_ms=2500, damage=60, hits_allies=True)]
GROUPS = [[('enforcer_rifle', 3)], [('enforcer_rifle', 2), ('grenadier', 1)],
          [('blade_retainer', 1), ('enforcer_rifle', 2)]]


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def contract(beat, record, layout):
    if (beat['id'] != 'ch02.b06' or beat['place'] != FRAME or
            not same(beat['ext']['hazards'], HAZARD) or record['zone'] != -1 or
            not same(record['height_cm'], 0) or not same(beat['task']['max_alive'], 6) or
            beat['task']['goal'] != 'survive' or not same(beat['task']['duration_ms'], 150000)):
        raise ValueError('pod defense must retain its authored hazard, task and arena frame')
    for name, position in [(p[0], p[1]) for p in PODS] + HORSES:
        points = [p for p in layout['points'] if p['id'] == name]
        if (len(points) != 1 or points[0]['frame'] != FRAME or points[0]['place'] != FRAME or
                not same(points[0]['positions_cm'], [position])):
            raise ValueError('missing, duplicate or moved named pod/horse point: ' + name)
    expected = []
    for index, ((name, _, release), groups) in enumerate(zip(PODS, GROUPS)):
        expected.append(dict(enemies=[dict(type=kind, count=n, spawn=name) for kind, n in groups],
                             trigger='start' if index == 0 else f'after_s:{release//1000}'))
    if not same(beat['params']['waves'], expected) or len(beat['task']['waves']) != 3:
        raise ValueError('pod wave composition or release time drift')
    for index, (_, _, release) in enumerate(PODS):
        wave = beat['task']['waves'][index]
        if (wave['trigger'] != ('start' if index == 0 else 'after_ms') or not same(wave['value'], release) or
                not same([(g['type'], g['count']) for g in wave['members']], GROUPS[index]) or
                any(g['lethal'] is not True or g['invulnerable'] is not False for g in wave['members'])):
            raise ValueError('normalized pod wave does not match authored members')
    return dict(windup_ms=2500, radius_cm=350, damage=60, hits_allies=True,
                contact='foot_center_cylinder', floor_band_cm=[-20, 80],
                spawn_offsets_cm=OFFSETS,
                arrivals=[dict(id=name, wave=i, floor_cm=p, release_ms=t)
                          for i, (name, p, t) in enumerate(PODS)])


def place_pods(beats, records, layout, fail):
    for beat, record in zip(beats, records):
        if beat['id'] == 'ch02.b06':
            try:
                record['pod_arrivals'] = contract(beat, record, layout)
                record['targets'] = [p[:2] for _, p in HORSES]
            except (KeyError, TypeError, ValueError) as error:
                fail(beat['id'], str(error))


def pods_valid(chapter):
    try:
        if len(chapter['beats']) != len(chapter['space']['beats']):
            return False
        for beat, record in zip(chapter['beats'], chapter['space']['beats']):
            if record['beat'] != beat['id']:
                return False
            if beat['id'] == 'ch02.b06':
                if (not same(record['pod_arrivals'], contract(beat, record, chapter['layout'])) or
                        not same(record['targets'], [p[:2] for _, p in HORSES])):
                    return False
            elif 'pod_arrivals' in record:
                return False
        return True
    except (KeyError, ValueError, TypeError):
        return False
