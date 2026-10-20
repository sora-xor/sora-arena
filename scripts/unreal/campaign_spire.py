"""Chapter eight's physical spiral. Proxy collision, independent of final art."""

import math

WIDTH_CM, VOID_CM, HEIGHT_CM = 400, 1400, 2700
APOTHEM = (VOID_CM + WIDTH_CM) / 2
RADIUS = 2 * APOTHEM / math.sqrt(3)
SIDES = round(HEIGHT_CM * 12 / RADIUS)
SUBDIVISIONS = 3
LANDINGS = [level * SIDES for level in range(4)]
VERTICES = [(-RADIUS, 0), (-RADIUS/2, -APOTHEM), (RADIUS/2, -APOTHEM),
            (RADIUS, 0), (RADIUS/2, APOTHEM), (-RADIUS/2, APOTHEM)]


def route():
    points = []
    for n in range(SIDES * SUBDIVISIONS + 1):
        edge = (-SIDES + n // SUBDIVISIONS) % 6
        a, b = VERTICES[edge], VERTICES[(edge + 1) % 6]
        f = (n % SUBDIVISIONS) / SUBDIVISIONS
        points.append([round(a[0] + (b[0]-a[0])*f), round(a[1] + (b[1]-a[1])*f),
                       round(n * HEIGHT_CM / (SIDES * SUBDIVISIONS))])
    return points


def landing_formation(ramp, node, side_offsets):
    """Keep grounded wave capsules on the flat, incoming half of a landing."""
    p, previous = ramp[node], ramp[node - 1]
    length = math.dist(p[:2], previous[:2])
    dx, dy = (p[0] - previous[0]) / length, (p[1] - previous[1]) / length
    return [[round(p[0] - dx * back - dy * side),
             round(p[1] - dy * back + dx * side), p[2]]
            for back in (100, 240) for side in side_offsets]


def place_spire(beats, records, zones, fail):
    by_id = {row['beat']: row for row in records}
    if 'ch08.b10' not in by_id:
        return
    beat = next(row for row in beats if row['id'] == 'ch08.b10')
    expected = [
        ('start', [('enforcer_rifle', 4, 'sp_sp_L2_ramp'), ('marksman', 1, 'sp_sp_L2_gantry_far')]),
        ('alive_below:2', [('shield_enforcer', 2, 'sp_sp_L3_ramp_down'), ('blade_retainer', 2, 'sp_sp_L3_ramp_down')]),
        ('volume_enter:vol_spire_L3', [('drone', 4, 'sp_sp_void_air'), ('grenadier', 1, 'sp_sp_L4_gantry'), ('auditor', 2, 'sp_sp_L4_office')])]
    actual = [(w['trigger'], [(g['type'], g['count'], g['spawn']) for g in w['enemies']]) for w in beat['params']['waves']]
    if actual != expected or beat['params']['complete'] != {'kind': 'all_waves_cleared'}:
        fail(beat['id'], 'spire requires its authored level-specific wave contract')
    row, lift = by_id['ch08.b10'], by_id['ch08.b11']
    x, y = lift['anchor']
    ramp = [[x+px,y+py,z] for px,py,z in route()]
    l2, l3, l4 = (ramp[n] for n in LANDINGS[1:])
    # The rising ramp overlaps the square landing. A symmetric grid around
    # its center puts some capsules below the actual walk surface. Place the
    # two ranks down the incoming run, clear of its side rails and pad edges.
    spawns = landing_formation(ramp, LANDINGS[1], (-80, 80))
    spawns += [[2*x-l2[0],2*y-l2[1],900]]
    # L3 also has an ascending shortcut across its northern half; both ranks
    # stay south of it, within the incoming ramp's clear width.
    spawns += landing_formation(ramp, LANDINGS[2], (-120, -20))
    spawns += [[x+dx,y+dy,2100] for dx,dy in [(-300,-300),(300,-300),(-300,300),(300,300)]]
    spawns += [[x-800,y,2700],[l4[0],y-100,2700],[l4[0],y+100,2700]]
    row['spire'] = {'center': [x,y], 'width_cm': WIDTH_CM, 'void_diameter_cm': VOID_CM, 'landing_nodes': LANDINGS, 'ramp': ramp, 'spawns': spawns}
    row['entry'] = ramp[0][:2] + [-120]
    row['anchor'] = ramp[0][:2]
    row['spawns'] = [p[:2] for p in spawns]
    row['patrols'] = []
    row['exit'] = {'center': [x-800,y], 'size': [300,300], 'floor_cm': 2700}
    for volume in row['volumes']:
        level = LANDINGS[2] if volume['event'] == 'volume_enter:vol_spire_L3' else LANDINGS[1]
        volume.update(center=ramp[level][:2], size=[500,500], floor_cm=ramp[level][2])
    for n, ally in enumerate(row['fieldcraft']['allies']):
        ally['at'] = [ramp[0][0]-100+(n%2)*140,ramp[0][1]-100+(n//2)*150]
    zone = zones[row['zone']]
    zone.rect = (x-1900,y-1900,x+1900,y+2600)
    zone.entry = tuple(row['entry'])
    zone.cover, zone.props = [], []
