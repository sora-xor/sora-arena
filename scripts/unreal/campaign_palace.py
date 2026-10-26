"""Chapter six L5: registry levels and seized-store placement.

The nightingale route in b06 remains a separate, unfinished integration.
Coordinates here use the palace garden's authored southwest origin.
"""
import json

DESKS = ((1600, 2900, 0), (600, 2900, 15), (-200, 2900, 30))
NAMES = ('desk_tagata', 'desk_machikata', 'desk_shokukata')
SPAWNS = ((1600,2790),(600,2790),(-200,2790),(1800,2320),(300,3000),(1800,3200))
PATROLS = (((1600,2790),(1850,2700),(1850,3200),(1450,3200)),
           ((600,2790),(850,2700),(850,3200),(450,3200)),
           ((-200,2790),(50,2700),(50,3200),(-350,3200)),
           ((1800,2320),(-300,2320)),
           ((300,3000),(1800,3000),(1800,3200),(300,3200)))
STORE_VOLUMES = {'vol_vault_armory':(3500,2500), 'vol_poi_contraband':(4100,2500),
                 'vol_poi_heirloom_map':(3400,2800), 'vol_poi_vista':(3700,2200)}


def contract(origin):
    x, y = origin
    return {'origin_cm': list(origin),
            'desks_cm': [[x+a, y+b, z] for a,b,z in DESKS],
            'perimeter_width_cm': 180}


def point(origin, x, y):
    return [origin[0]+x, origin[1]+y]


def place_palace(beats, records, zones, sites, pickups, fail):
    for beat, record in zip(beats, records, strict=True):
        if beat['id'] not in ('ch06.b07', 'ch06.b08'):
            continue
        zone = zones[record['zone']]
        x,y,x1,y1 = zone.rect
        if zone.place != 'pl_uguisu_hall' or (x1-x,y1-y) != (5000,3670):
            fail(beat['id'], 'palace must retain the garden, vestibule, store and registry frame')
        origin = (x+600,y+270)
        p = lambda a,b: point(origin,a,b)
        zone.cover = []  # The dedicated builder supplies the interior walls/steps.
        zone.props = []
        zone.entry = (*p(2600,2500),180)
        record['registry_hall'] = contract(origin)
        record['entry'] = list(zone.entry)
        record['spawns'] = [p(a,b) for a,b in SPAWNS]
        record['patrols'] = [[p(a,b) for a,b in loop] for loop in PATROLS]
        record['exit'] = {'center':p(1800,3200),'size':[300,300]}
        if beat['id'] == 'ch06.b07':
            record['anchor'] = p(3700,2500)
            record['cache'] = p(3700,2600)
            for row in record['volumes']:
                row.update(center=p(*STORE_VOLUMES[row['event'].split(':',1)[1]]),size=[300,300])
        else:
            if tuple(beat['task']['objectives']) != NAMES or beat['task']['objective_hold_ms'] != [30000]*3:
                fail(beat['id'], 'three separate thirty-second desk copies are required')
            record['anchor'] = p(1900,2500)
            record['objectives'] = [p(a,b-110) for a,b,_ in DESKS]
            record['volumes'] = [{'event':'volume_enter:vol_kicho_chudan',
                                  'center':p(600,2500),'size':[600,300],'floor_cm':15}]
            sites[beat['site']] = p(1900,2500)
        for index,pickup in enumerate(p for p in pickups if p['zone']==record['zone']):
            pickup['at'] = p(3300+index*180,2300)


def palace_valid(chapter):
    try:
        for beat, record in zip(chapter['beats'],chapter['space']['beats'],strict=True):
            if beat['id'] not in ('ch06.b07','ch06.b08'):
                if 'registry_hall' in record:
                    return False
                continue
            zone = chapter['space']['zones'][record['zone']]
            x,y,x1,y1 = zone['rect']; origin=(x+600,y+270)
            p = lambda a,b: point(origin,a,b)
            same = lambda a,b: json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True)
            if (zone['place']!='pl_uguisu_hall' or (x1-x,y1-y)!=(5000,3670)
                    or zone['wall_cm']!=500 or zone['cover'] or zone['props']
                    or not same(record['registry_hall'],contract(origin))):
                return False
            if (record['beat']!=beat['id'] or record['height_cm']!=0
                    or not same(record['entry'],[*p(2600,2500),180])
                    or not same(zone['entry'],record['entry'])
                    or not same(record['spawns'],[p(a,b) for a,b in SPAWNS])
                    or not same(record['patrols'],[[p(a,b) for a,b in loop] for loop in PATROLS])
                    or not same(record['exit'],{'center':p(1800,3200),'size':[300,300]})):
                return False
            if beat['id']=='ch06.b08':
                if (tuple(beat['task']['objectives'])!=NAMES or beat['task']['objective_hold_ms']!=[30000]*3
                        or not same(record['objectives'],[p(a,b-110) for a,b,_ in DESKS])
                        or not same(record['anchor'],p(1900,2500))
                        or not same(chapter['space']['sites'][beat['site']],p(1900,2500))
                        or not same(record['volumes'],[{'event':'volume_enter:vol_kicho_chudan',
                            'center':p(600,2500),'size':[600,300],'floor_cm':15}])):
                    return False
            else:
                if (not same(record['anchor'],p(3700,2500)) or not same(record['cache'],p(3700,2600))
                        or len(record['volumes'])!=len(STORE_VOLUMES)
                        or {r['event'] for r in record['volumes']}!={'volume_enter:'+n for n in STORE_VOLUMES}):
                    return False
                for row in record['volumes']:
                    name=row['event'].split(':',1)[1]
                    if name not in STORE_VOLUMES or not same(row['center'],p(*STORE_VOLUMES[name])) or row['size']!=[300,300]:
                        return False
        return True
    except (KeyError,TypeError,IndexError,ValueError):
        return False
