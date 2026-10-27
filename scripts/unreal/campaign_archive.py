"""Chapter-six archive footprint and solid duel posts; final art remains separate."""
import json

POSTS = ((900, 600), (1700, 600), (900, 1200), (1700, 1200))
SPAWNS = ((1300, 1300), (1300, 500), (1100, 900), (1500, 900), (1100, 500), (1500, 1300))
FLOOR_CM = 600
EXIT_EVENT = 'volume_enter:vol_archive_press_landing'


def portal_walls(rect, height, door_x):
    """Full side/south walls; two north spans leave a 240 cm doorway."""
    x,y,x1,y1=rect
    return [[x-30,(y+y1)//2,60,y1-y+120,height],
            [x1+30,(y+y1)//2,60,y1-y+120,height],
            [(x+x1)//2,y-30,x1-x,60,height],
            [(x+door_x-120)//2,y1+30,door_x-120-x,60,height],
            [(door_x+120+x1)//2,y1+30,x1-door_x-120,60,height]]


def place_archive(beats, records, zones, fail):
    if not any(b['id']=='ch06.b09' for b in beats):
        return
    press=next(r for b,r in zip(beats,records,strict=True) if b['id']=='ch06.b11')
    press_zone=zones[press['zone']]
    landing=press['press_hall']['catwalk']['ladder_top_cm']
    press_zone.walls=portal_walls(press_zone.rect,press_zone.wall,landing[0])
    for beat, record in zip(beats, records, strict=True):
        if beat['id'] not in ('ch06.b09', 'ch06.b10'):
            continue
        zone = zones[record['zone']]
        x, y, x1, y1 = zone.rect
        if zone.place != 'pl_archive' or (x1-x, y1-y) != (2600, 1800):
            fail(beat['id'], 'archive needs the authored 26 by 18 metre floor')
        zone.cover = [[x+a, y+b, 60, 60, 600] for a,b in POSTS]
        zone.walls = portal_walls(zone.rect,zone.wall,x+1300)
        zone.props = []
        zone.entry = (x+1300, y+200, 90)
        record['entry'] = list(zone.entry)
        record['anchor'] = [x+1300, y+900]
        record['exit'] = {'center':[x+1300, y+1600], 'size':[400, 300]}
        record['spawns'] = [[x+a, y+b] for a,b in SPAWNS]
        record['patrols'] = []
        record['height_cm'] = FLOOR_CM
        if beat['id']=='ch06.b10':
            if not beat['task']['anchor_after_lines'] or beat['task']['closing_event']!=EXIT_EVENT:
                fail(beat['id'],'the pledge ends on the press landing after its dialogue')
            record['closing']=landing[:]
            record['volumes']=[{'event':EXIT_EVENT,'center':landing[:],'size':[300,120],'floor_cm':400}]


def archive_valid(chapter):
    try:
        if not any(b['id']=='ch06.b09' for b in chapter['beats']):
            return True
        press=next(r for r in chapter['space']['beats'] if r['beat']=='ch06.b11')
        press_zone=chapter['space']['zones'][press['zone']]
        landing=press['press_hall']['catwalk']['ladder_top_cm']
        if press_zone['walls']!=portal_walls(press_zone['rect'],900,landing[0]):
            return False
        for beat, record in zip(chapter['beats'], chapter['space']['beats'], strict=True):
            if beat['id'] not in ('ch06.b09', 'ch06.b10'):
                continue
            zone = chapter['space']['zones'][record['zone']]
            x,y,x1,y1 = zone['rect']
            if (x1-x,y1-y) != (2600,1800) or zone['wall_cm'] != 600 or zone['place'] != 'pl_archive':
                return False
            expected = {'entry':[x+1300,y+200,90], 'anchor':[x+1300,y+900],
                'exit':{'center':[x+1300,y+1600], 'size':[400,300]},
                'spawns':[[x+a,y+b] for a,b in SPAWNS], 'patrols':[], 'height_cm':FLOOR_CM}
            if any(json.dumps(record[k],sort_keys=True) != json.dumps(v,sort_keys=True) for k,v in expected.items()):
                return False
            if zone['cover'] != [[x+a,y+b,60,60,600] for a,b in POSTS] or zone['props'] or zone['entry'] != expected['entry']:
                return False
            if zone['walls']!=portal_walls(zone['rect'],600,x+1300):
                return False
            if beat['id']=='ch06.b10' and (not beat['task']['anchor_after_lines'] or beat['task']['closing_event']!=EXIT_EVENT
                    or record['closing']!=landing or record['volumes']!=[{'event':EXIT_EVENT,'center':landing,'size':[300,120],'floor_cm':400}]):
                return False
        return True
    except (KeyError,TypeError,IndexError,ValueError,StopIteration):
        return False
