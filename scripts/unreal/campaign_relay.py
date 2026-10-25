"""Chapter six L3: relay room dimensions, controls and scan contract."""
import json

NODES = ((920, 500, 120), (1080, 500, 120), (1000, 580, 520))
WORK = ((800, 500, 0), (1200, 500, 0), (1000, 690, 400))
SENSOR = {'id': 's_relay_fan', 'kind': 'rotating_scan', 'period_s': 12,
          'exposed_s': 8, 'gap_s': 4,
          'on_interact_exposed': {'suspicion_add': 0.6, 'fan_lock_s': 2}}
LAMPS = ('l_worklamp_se', 'l_worklamp_nw')


def same(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def contract(beat, origin):
    p, t = beat['params'], beat['task']
    if (beat['id'] != 'ch06.b04' or beat['type'] != 'stealth_zone' or beat['place'] != 'pl_relay_room'
            or not same(beat['ext']['sensors'], [SENSOR])
            or p['on_detected'] != 'reinforce:w_relay'
            or not same(p['waves'], [{'id': 'w_relay', 'trigger': 'alert_state:alert',
                'enemies': [{'type': 'enforcer_rifle', 'count': 2, 'spawn': 'sp_relay_east_door', 'delay_s': 8}],
                'effects': ['relay_nodes_locked_30s']}])
            or not same(p['light_sources'], [{'id': n, 'extinguishable': True, 'suspicion_delay_s': 5} for n in LAMPS])
            or not same(p['objectives'], [{'id': n, 'interact_s': 3, 'at': 'relay_'+n} for n in ('node_w','node_e','node_n')]
                         + [{'id':'exit','volume':'vol_relay_exit_east'}])
            or t['objectives'] != ['node_w', 'node_e', 'node_n', 'exit']
            or not same(t['objective_hold_ms'], [3000, 3000, 3000, 0])
            or [g['type'] for g in t['guards']] != ['enforcer_rifle','enforcer_rifle','auditor','drone']
            or not same([g['post'] for g in t['guards']], [False,False,True,False])
            or [g.get('patrol',g.get('post')) for g in p['guards']] !=
                ['spl_relay_1f_loop_50s','spl_relay_2f_loop_40s','post_relay_mitai','spl_relay_orbit_30s']
            or p['guards'][2].get('investigates') != 'dark_node'
            or not same(p['noise_surfaces'],[{'kind':'gravel','volume':'vol_bell_clappers_'+str(i)} for i in (1,2)])
            or beat['ext']['on_complete_effects'] != ['drone_marks_local_only_20m','moat_searchlights_fixed']):
        raise ValueError('relay room must retain its authored nodes, scan, detection, lamps and completion effects')
    if len(origin) != 2 or any(type(v) is not int for v in origin):
        raise ValueError('relay origin must be integer centimetres')
    x, y = origin
    xyz = lambda point: [x+point[0], y+point[1], point[2]]
    return {'origin_cm': list(origin), 'period_ms':12000, 'exposed_ms':8000, 'gap_ms':4000,
            'pull_ms':3000, 'caught_suspicion_permille':600, 'fan_lock_ms':2000,
            'nodes_lock_ms':30000, 'reinforcement_delay_ms':8000, 'reinforcement_count':2,
            'lamp_notice_ms':5000, 'gallery_height_cm':400, 'gallery_width_cm':180,
            'nodes_cm':[xyz(n) for n in NODES], 'work_cm':[xyz(n) for n in WORK]}


def lamps(origin):
    x,y=origin
    return [{'id':name,'kind':'lamp','at':[x+dx,y+dy],'radius_cm':700,
             'snuff':'hold','hold_ms':1000,'relight_ms':0}
            for name,(dx,dy) in zip(LAMPS,((1900,100),(100,900)))]


def entry_volumes(x,y):
    return [{'event':'volume_enter:vol_relay_entry','center':[x+180,y+500],
             'size':[300,300],'floor_cm':0}]


def spawn_points(x,y):
    return [[x+dx,y+dy] for dx,dy in ((650,200),(510,160),(300,500),(1250,500),(1850,400),(1850,600))]


def place_relay(beats, records, zones, pickups, fail):
    for beat, record in zip(beats, records):
        if beat['id'] != 'ch06.b04': continue
        zone=zones[record['zone']]; x,y,x1,y1=zone.rect
        try:
            if (x1-x,y1-y)!=(2000,1000): raise ValueError('relay room needs its authored 20 by 10 m floor')
            room=contract(beat,[x,y])
        except (KeyError,TypeError,ValueError) as e: fail(beat['id'],str(e))
        record['relay_room']=room
        record['entry']=[x+180,y+500,0]
        record['anchor']=[x+400,y+500]
        record['objectives']=[p[:2] for p in room['work_cm']]+[[x+1850,y+500]]
        record['exit']={'center':[x+1850,y+500],'size':[300,300],'floor_cm':0}
        record['volumes']=entry_volumes(x,y)
        record['spawns']=spawn_points(x,y)
        record['patrols']=[[[x+dx,y+dy] for dx,dy in ((650,200),(1350,200),(1350,800),(650,800))]]
        record['fieldcraft']['lamps']=lamps([x,y])
        zone.cover=[];zone.props=[] # Runtime column, gallery, stair and cover own collision.
        for pickup in pickups:
            if pickup['collectible']=='ch06.c02':pickup['at']=[x+1650,y+850]


def relay_valid(chapter):
    try:
        for beat, record in zip(chapter['beats'],chapter['space']['beats'],strict=True):
            if beat['id']!=record['beat']:return False
            if beat['id']!='ch06.b04':
                if 'relay_room' in record:return False
                continue
            zone=chapter['space']['zones'][record['zone']];x,y,x1,y1=zone['rect']
            room=contract(beat,[x,y])
            if ((x1-x,y1-y)!=(2000,1000) or not same(record['relay_room'],room)
                    or not same(record['entry'],[x+180,y+500,0])
                    or not same(record['objectives'],[p[:2] for p in room['work_cm']]+[[x+1850,y+500]])
                    or not same(record['exit'],{'center':[x+1850,y+500],'size':[300,300],'floor_cm':0})
                    or not same(record['fieldcraft']['lamps'],lamps([x,y]))
                    or not same(record['volumes'],entry_volumes(x,y))
                    or not same(record['spawns'],spawn_points(x,y))
                    or not same(record['anchor'],[x+400,y+500])
                    or zone['cover'] or record['height_cm']!=0):return False
        return True
    except (KeyError,TypeError,ValueError,IndexError):return False
