"""Chapter-six archive footprint and solid duel posts; final art remains separate."""
import json

POSTS = ((900, 600), (1700, 600), (900, 1200), (1700, 1200))
SPAWNS = ((1300, 1300), (1300, 500), (1100, 900), (1500, 900), (1100, 500), (1500, 1300))


def place_archive(beats, records, zones, fail):
    for beat, record in zip(beats, records, strict=True):
        if beat['id'] not in ('ch06.b09', 'ch06.b10'):
            continue
        zone = zones[record['zone']]
        x, y, x1, y1 = zone.rect
        if zone.place != 'pl_archive' or (x1-x, y1-y) != (2600, 1800):
            fail(beat['id'], 'archive needs the authored 26 by 18 metre floor')
        zone.cover = [[x+a, y+b, 60, 60, 600] for a,b in POSTS]
        zone.props = []
        zone.entry = (x+1300, y+200, 90)
        record['entry'] = list(zone.entry)
        record['anchor'] = [x+1300, y+900]
        record['exit'] = {'center':[x+1300, y+1600], 'size':[400, 300]}
        record['spawns'] = [[x+a, y+b] for a,b in SPAWNS]
        record['patrols'] = []


def archive_valid(chapter):
    try:
        for beat, record in zip(chapter['beats'], chapter['space']['beats'], strict=True):
            if beat['id'] not in ('ch06.b09', 'ch06.b10'):
                continue
            zone = chapter['space']['zones'][record['zone']]
            x,y,x1,y1 = zone['rect']
            if (x1-x,y1-y) != (2600,1800) or zone['wall_cm'] != 600 or zone['place'] != 'pl_archive':
                return False
            expected = {'entry':[x+1300,y+200,90], 'anchor':[x+1300,y+900],
                'exit':{'center':[x+1300,y+1600], 'size':[400,300]},
                'spawns':[[x+a,y+b] for a,b in SPAWNS], 'patrols':[], 'height_cm':0}
            if any(json.dumps(record[k],sort_keys=True) != json.dumps(v,sort_keys=True) for k,v in expected.items()):
                return False
            if zone['cover'] != [[x+a,y+b,60,60,600] for a,b in POSTS] or zone['props'] or zone['entry'] != expected['entry']:
                return False
        return True
    except (KeyError,TypeError,IndexError,ValueError):
        return False
