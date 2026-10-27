"""Bind the chapter-three back tenements to their authored ward coordinates.

The shared street remains part of the arena. Its two boundary walls need
explicit openings where this district and its north passage join it.
"""
import copy

BEATS = ('ch03.b04', 'ch03.b05', 'ch03.b06', 'ch03.b13', 'ch03.b14')
HUB_RETURNS = {'ch03.b16': {'entry': [-350, 0, 0]},
               'ch03.b18': {'entry': [-350, 0, 0], 'anchor': [400, -220]}}
ZONE = [-4700, -400, -600, 4300]
ENTRY = [-2800, 450, 90]
WELL = [-3100, 3200]
HOIST = [-2600, 3100]
HIDEOUT = [-2550, 1050]
FIRES = [[-3320, 2950], [-3320, 3250], [-3320, 3500]]
PATROLS = [[[-4500, 0], [-1000, 0]], [[-4500, 100], [-1000, 100]]]
SPAWNS = [[-2800, 500], [-2800, 650], [-2800, 800], [-2800, 950], [-3500, 3600], [-3600, 3400]]
DEFENSE_SPAWNS = [[-2800,450],[-2800,570],[-2800,690],[-2800,810],[-3500,3600],[-3500,3400]]
FINDS = [{'id':'poi_chalk','collectible':'ch03.c01','at_cm':[-2887,1830,65]},
         {'id':'poi_balance_door','collectible':'ch03.c02','at_cm':[-2713,2415,135]}]
DEFENSE = {'hold_cm':[-3400,2220,0,-2200,3600,600], 'street_cm':[-2800,450,0],
           'air_cm':[-3500,3600,600], 'street_spacing_cm':120, 'air_spacing_cm':200,
           'flight_cm':[[[-3300,3350,600],[-2800,3050,600]],[[-3300,3050,600],[-2800,2750,600]]]}
VOLUMES = {
    'poi_idobata': ([-2420, 3170], [300, 300]),
    'poi_chalk': ([-2800, 1800], [180, 300]),
    'poi_leaflet': ([-2800, 1350], [180, 300]),
    'poi_balance_door': ([-2800, 2475], [180, 300]),
    'vol_b05_alley_mouth': ([-2800, 600], [180, 300]),
    'vol_b14_supply': ([-2400, 3600], [200, 200]),
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
        values.update(anchor=[-2440, 3330], cache=[-2800, 1800], tenement_finds=copy.deepcopy(FINDS))
    elif beat == 'ch03.b05':
        values.update(anchor=[-2900, 2900], recovery=list(WELL), pickups=[list(HOIST)],
                      dropoffs=[list(HIDEOUT)], spawns=[p[0] for p in PATROLS], patrols=copy.deepcopy(PATROLS))
    elif beat == 'ch03.b06':
        values.update(entry=[-2580, 1050, 0], anchor=[-2510, 1110])
    elif beat == 'ch03.b13':
        values.update(entry=[-2800, 3850, 90], height_cm=45, anchor=[-2800, 3970],
                      camera=[-2900, 3730, 220, -2670, 3750, 210, -2800, 3970, 155])
    elif beat == 'ch03.b14':
        values.update(entry=[-2800, 3000, 180], anchor=[-3220, 3250],
                      spawns=copy.deepcopy(DEFENSE_SPAWNS),tenement_defense=copy.deepcopy(DEFENSE))
    return values


def place_tenements(beats, records, zones, sites, pickups, layout, fail):
    selected = [(b, r) for b, r in zip(beats, records, strict=True) if b['id'] in BEATS]
    if not selected:
        return
    if len(selected) != len(BEATS):
        fail('tenements', 'all five back-tenement beats are required')
    # The authored tenements overlap the arena's old west-street spawn.
    # Later hub arrivals must stand on the remaining hub, not in zone 2.
    for r in records:
        if r['beat'] in HUB_RETURNS:
            r.update(copy.deepcopy(HUB_RETURNS[r['beat']]))
    authored = {p['id']: p for p in layout['points']}
    for name, at in [('act_b05_dry_well_rope', WELL), ('pk_b05_tsurube', HOIST), ('dp_b05_hideout', HIDEOUT)]:
        if authored.get(name, {}).get('positions_cm') != [at + [0]]:
            fail(name, 'authored tenement point changed; review the physical layout')
    for name,at in [('sp_b14_alley_mouth',DEFENSE['street_cm']),('sp_b14_backfence_air',DEFENSE['air_cm'])]:
        if authored.get(name,{}).get('positions_cm')!=[at]:fail(name,'authored defense entrance changed')
    hold=next((v for v in layout['volumes'] if v['id']=='vol_b14_kitchen'),{})
    if hold.get('center_cm')!=[-2800,2910,300] or hold.get('size_cm')!=[1200,1380,600]:
        fail('vol_b14_kitchen','authored court and alley defense volume changed')
    defense=next(b for b,_ in selected if b['id']=='ch03.b14')
    if not defense_waves_valid(defense):fail(defense['id'],'authored defense wave identities changed')
    explore=next(b for b,_ in selected if b['id']=='ch03.b04')
    if not finds_valid(explore):fail(explore['id'],'chalk and notice need their separate collectible bindings')
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
            pair['pl_kido']['rect']==[-8000,-1000,-4700,1100] and pair['pl_ura_nagaya']['rect']==ZONE)


def tenements_valid(chapter):
    try:
        selected = [r for r in chapter['space']['beats'] if r['beat'] in BEATS]
        if not chapter['id'].startswith('ch03_'):
            return not any('tenements' in r or 'tenement_defense' in r or 'tenement_finds' in r for r in chapter['space']['beats'])
        if len(selected) != len(BEATS):
            return False
        returns = [r for r in chapter['space']['beats'] if r['beat'] in HUB_RETURNS]
        if len(returns) != len(HUB_RETURNS) or any(r['zone'] != -1 or
                any(r.get(k) != v for k, v in HUB_RETURNS[r['beat']].items()) for r in returns):
            return False
        if any(('tenements' in r)!=(r['beat'] in BEATS) for r in chapter['space']['beats']):
            return False
        if any(('tenement_defense' in r)!=(r['beat']=='ch03.b14') for r in chapter['space']['beats']):return False
        if any(('tenement_finds' in r)!=(r['beat']=='ch03.b04') for r in chapter['space']['beats']):return False
        if not finds_valid(next(b for b in chapter['beats'] if b['id']=='ch03.b04')):return False
        if not defense_waves_valid(next(b for b in chapter['beats'] if b['id']=='ch03.b14')):return False
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
    except (KeyError, TypeError, IndexError, StopIteration):
        return False


def finds_valid(beat):
    try:
        pois=beat['params']['pois']
        return (beat['optional'] is True and beat['task']['goal']=='cache' and
                beat['params']['rewards']==['ch03.c01','ch03.c02'] and
                {p['id']:p.get('collectible') for p in pois if 'collectible' in p}==
                {f['id']:f['collectible'] for f in FINDS} and
                len({p['id'] for p in pois})==len(pois))
    except (KeyError,TypeError):return False


def defense_waves_valid(beat):
    try:
        groups=[[('enforcer_rifle',2),('bound_conscript',2)],[('drone',2)],[('blade_retainer',1),('enforcer_rifle',1)]]
        waves=beat['params']['waves'];compiled=beat['task']['waves']
        if len(waves)!=3 or len(compiled)!=3:return False
        if beat['task']['duration_ms']!=120000 or beat['task']['contest']!='pause':return False
        for i,(raw,task,expected) in enumerate(zip(waves,compiled,groups,strict=True)):
            mark=(300,600,800)[i];spawn='sp_b14_backfence_air' if i==1 else 'sp_b14_alley_mouth'
            if raw['trigger']!=f'progress_at:{mark/1000:g}' or task['trigger']!='progress_at' or task['value']!=mark:return False
            if raw['enemies']!=[{'type':kind,'count':count,'spawn':spawn} for kind,count in expected]:return False
            if task['members']!=[{'type':kind,'count':count,'lethal':kind!='bound_conscript','invulnerable':False} for kind,count in expected]:return False
        return True
    except (KeyError,TypeError,IndexError,ValueError):return False
