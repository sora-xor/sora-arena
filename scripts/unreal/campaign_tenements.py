"""Bind the chapter-three back tenements to their authored ward coordinates.

The shared street remains part of the arena. Its two boundary walls need
explicit openings where this district and its north passage join it.
"""
import copy

BEATS = ('ch03.b04', 'ch03.b05', 'ch03.b06', 'ch03.b13', 'ch03.b14')
ZONE = [-4700, -400, -600, 4300]
ENTRY = [-2800, 450, 90]
WELL = [-3100, 3200]
HOIST = [-2600, 3100]
HIDEOUT = [-2550, 1050]
FIRES = [[-3320, 2950], [-3320, 3250], [-3320, 3500]]
PATROLS = [[[-4500, 0], [-1000, 0]], [[-4500, 100], [-1000, 100]]]
SPAWNS = [[-2800, 500], [-2800, 650], [-2800, 800], [-2800, 950], [-3500, 3600], [-3600, 3400]]
VOLUMES = {
    'poi_idobata': ([-2420, 3170], [300, 300]),
    'poi_chalk': ([-2800, 1800], [180, 300]),
    'poi_leaflet': ([-2800, 1350], [180, 300]),
    'poi_balance_door': ([-2800, 2475], [180, 300]),
    'vol_b05_alley_mouth': ([-2800, 600], [180, 300]),
    'vol_b14_supply': ([-2370, 3700], [300, 300]),
}


def contract():
    return {'alley_cm': [-2890, 1200, -2710, 2820], 'units_per_row': 6,
            'unit_cm': [270, 360], 'court_cm': [-3400, 2820, -2200, 3600],
            'dry_well_cm': WELL + [90, 700, 75], 'hoist_cm': list(HOIST),
            'hideout_cm': [-2710, 900, -2440, 1200], 'dropoff_cm': list(HIDEOUT),
            'manager_cm': [-3200, 3600, -2400, 4200], 'patrol_ms': 45000}


def record_values(beat):
    values = {'entry': list(ENTRY), 'height_cm': 0, 'anchor': [-2800, 3000],
              'spawns': copy.deepcopy(SPAWNS), 'patrols': [],
              'exit': {'center': [-2800, 650], 'size': [180, 300]}, 'tenements': contract()}
    if beat == 'ch03.b04':
        values.update(anchor=[-2440, 3330], cache=[-2800, 1800])
    elif beat == 'ch03.b05':
        values.update(anchor=[-2900, 2900], recovery=list(WELL), pickups=[list(HOIST)],
                      dropoffs=[list(HIDEOUT)], spawns=[p[0] for p in PATROLS], patrols=copy.deepcopy(PATROLS))
    elif beat == 'ch03.b06':
        values.update(entry=[-2580, 1050, 0], anchor=[-2510, 1110])
    elif beat == 'ch03.b13':
        values.update(entry=[-2800, 3850, 90], height_cm=45, anchor=[-2800, 3970],
                      camera=[-2900, 3730, 220, -2670, 3750, 210, -2800, 3970, 155])
    elif beat == 'ch03.b14':
        values.update(entry=[-2800, 3000, 180], anchor=[-3220, 3250])
    return values


def place_tenements(beats, records, zones, sites, pickups, layout, fail):
    selected = [(b, r) for b, r in zip(beats, records, strict=True) if b['id'] in BEATS]
    if not selected:
        return
    if len(selected) != len(BEATS):
        fail('tenements', 'all five back-tenement beats are required')
    authored = {p['id']: p for p in layout['points']}
    for name, at in [('act_b05_dry_well_rope', WELL), ('pk_b05_tsurube', HOIST), ('dp_b05_hideout', HIDEOUT)]:
        if authored.get(name, {}).get('positions_cm') != [at + [0]]:
            fail(name, 'authored tenement point changed; review the physical layout')
    for b, r in selected:
        zone = zones[r['zone']]
        if zone.place != 'pl_ura_nagaya':
            fail(b['id'], 'back tenements need their own authored zone')
        zone.rect = tuple(ZONE); zone.entry = tuple(ENTRY)
        zone.wall = 240; zone.walls = []; zone.cover = []; zone.props = []
        r.update(record_values(b['id']))
        for v in r['volumes']:
            name = v['event'].split(':', 1)[1]
            if name not in VOLUMES:
                fail(b['id'], 'unplaced tenement volume ' + name)
            at, size = VOLUMES[name]
            v.update(center=list(at), size=list(size))
        r['fieldcraft']['surfaces'] = [
            {'kind': 'dobuita', 'center': [-2800, 2010], 'size': [80, 1620], 'height_cm': 0,
             'step_permille': 1500, 'crouch_permille': 1500},
        ]
        if b['id'] == 'ch03.b14':
            for fire, at in zip(r['fieldcraft']['fires']['points'], FIRES, strict=True):
                fire['at'] = list(at)
        if b['site'] is not None:
            sites[b['site']] = list(r['anchor'])
    zone_index = selected[0][1]['zone']
    for pickup in pickups:
        if pickup['zone'] == zone_index:
            if pickup['collectible'] == 'ch03.c03':
                # The vertical placement is applied by the dedicated builder
                # and runtime collectible query, not moved onto the court.
                pickup['at'] = list(WELL)
                pickup['height_cm'] = -650
            elif pickup['collectible'] == 'ch03.c05':
                pickup['at'] = [-3080, 4020]
                pickup['height_cm'] = 125
            else:
                fail(pickup['collectible'], 'unplaced tenement collectible')


def tenement_hub_overlap(chapter, zone, rect):
    return (chapter['id'] == 'ch03_lantern_ward' and zone['place'] == 'pl_ura_nagaya' and
            zone['rect'] == ZONE and tuple(rect) == (-3150, -2550, 3150, 2550))


def tenement_neighbour(chapter, a, b):
    pair={a['place']:a,b['place']:b}
    return (chapter['id']=='ch03_lantern_ward' and set(pair)=={'pl_kido','pl_ura_nagaya'} and
            pair['pl_kido']['rect']==[-8000,-1000,-5600,1100] and pair['pl_ura_nagaya']['rect']==ZONE)


def tenements_valid(chapter):
    try:
        selected = [r for r in chapter['space']['beats'] if r['beat'] in BEATS]
        if not chapter['id'].startswith('ch03_'):
            return not any('tenements' in r for r in chapter['space']['beats'])
        if len(selected) != len(BEATS):
            return False
        if any(('tenements' in r)!=(r['beat'] in BEATS) for r in chapter['space']['beats']):
            return False
        for r in selected:
            if any(r.get(k) != v for k, v in record_values(r['beat']).items()):
                return False
            z = chapter['space']['zones'][r['zone']]
            if (z['id'] != 'pl_ura_nagaya' or z['rect'] != ZONE or z['entry'] != ENTRY or
                    z['walls'] or z['cover'] or z['props'] or z['route'] or z['wall_cm'] != 240):
                return False
            for v in r['volumes']:
                at, size = VOLUMES[v['event'].split(':', 1)[1]]
                if v['center'] != at or v['size'] != size:
                    return False
            if r['fieldcraft']['surfaces'] != [{'kind':'dobuita','center':[-2800,2010],
                    'size':[80,1620],'height_cm':0,'step_permille':1500,'crouch_permille':1500}]:
                return False
            if r['beat']=='ch03.b14' and [f['at'] for f in r['fieldcraft']['fires']['points']]!=FIRES:
                return False
        picks={p['collectible']:p for p in chapter['space']['pickups']}
        if picks['ch03.c03']['at']!=WELL or picks['ch03.c03'].get('height_cm')!=-650:
            return False
        if picks['ch03.c05']['at']!=[-3080,4020] or picks['ch03.c05'].get('height_cm')!=125:
            return False
        if chapter['space']['sites'][0]!=[-2900,2900] or chapter['space']['sites'][2]!=[-3220,3250]:
            return False
        return True
    except (KeyError, TypeError, IndexError):
        return False
