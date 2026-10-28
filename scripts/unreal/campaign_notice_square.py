"""Place the charge encounter on the ward's existing terminal and north alley.

This binds the charge/escape contract and five ground patrol schedules. P1
uses clearance waypoints around the existing board and side-passage walls;
P2 keeps the authored -20 m / +38 m endpoints in separate passing lanes.
The drone follows an explicit 5.4 m / 6 m / 36 s circuit clear of the
money-changer footprint. Two supported flights reach its pitched roof.
"""

BEATS=('ch03.b10','ch03.b11','ch03.b12')
ZONE=[-2200,-1000,3200,3200]
ENTRY=[-1000,2800,-90]
PANEL=[-730,560]
SAFE=[-1600,3000]
DRONE=[[540,0],[530,105],[499,207],[449,300],[382,382],[300,449],[207,499],[105,530],
       [0,540],[-105,530],[-207,499],[-300,449],[-382,382],[-449,300],[-499,207],[-530,105],
       [-540,0],[-530,-105],[-499,-207],[-449,-300],[-382,-382],[-300,-449],[-207,-499],[-105,-530],
       [0,-540],[105,-530],[207,-499],[300,-449],[382,-382],[449,-300],[499,-207],[530,-105]]
P1=[[-1020,-700],[-510,-700],[0,-700],[510,-700],[1020,-700],
    [1020,-350],[1020,0],[1020,300],[440,300],[440,700],[0,700],[-510,700],
    [-1020,700],[-1020,233],[-1020,-233]]
P2=[[-60,-2000],[-60,-1033],[-60,-67],[-60,900],[-60,1867],[-60,2833],[-60,3800],
    [60,3800],[60,2971],[60,2143],[60,1314],[60,486],[60,-343],[60,-1171],[60,-2000]]


def ground_patrols():
    return [P1,P1[-1:]+P1[:-1],P2,P2[-1:]+P2[:-1],[[-4000,0],[4000,0]]]


def roof_ladders():
    return [dict(id='ladder_b10_pent',foot=[500,1600],yaw=-90,base_height_cm=0,height_cm=320,
                 roof=dict(center=[525,1200],size=[150,600]),world_roof='notice_pent',
                 drop_noise_cm=900,straw=None,guards=[]),
            dict(id='ladder_b10_kawara',foot=[500,1250],yaw=0,base_height_cm=320,height_cm=540,
                 roof=dict(center=[960,850],size=[780,1020]),world_roof='notice_kawara',
                 drop_noise_cm=900,straw=None,guards=[0])]


def ground_authored_valid(beat,layout):
    paths={p['id']:p for p in layout['patrols']}
    expected=[('pt_b10_p1',60,[[-800,-600],[800,-600],[800,600],[-800,600]]),
              ('pt_b10_p2',45,[[0,-2000],[0,3800]]),('pt_b10_p3',70,[[-4000,0],[4000,0]])]
    if any(paths.get(name,{}).get('loop_s')!=seconds or paths[name]['points_cm']!=points or
           paths[name]['alt_cm'] is not None or paths[name]['circle_cm'] is not None
           for name,seconds,points in expected):return False
    ladders=beat['ext'].get('ladders')
    if ladders!=[dict(id='ladder_b10_pent',roof='vol_b10_roofs',height_cm=320,drop_noise_cm=900),
                 dict(id='ladder_b10_kawara',roof='vol_b10_kawara',base_height_cm=320,height_cm=540,drop_noise_cm=900,guards=['g_b10_m1'])]:return False
    guards=beat['params']['guards']
    drone=paths.get('pt_b10_d',{})
    if (drone.get('loop_s')!=36 or drone.get('alt_cm')!=600 or
            drone.get('circle_cm')!={'center':[0,0],'radius':540} or drone.get('points_cm')):return False
    kinds=['marksman','drone','enforcer_rifle','enforcer_rifle','bound_conscript','bound_conscript','blade_retainer']
    routes=['static:sp_b10_roof','pt_b10_d','pt_b10_p1','pt_b10_p1','pt_b10_p2','pt_b10_p2','pt_b10_p3']
    return (len(guards)==7 and [g['type'] for g in guards]==kinds and
            [g['patrol'] for g in guards]==routes and
            [g.get('x_patrol_offset_s',0) for g in guards]==[0,0,0,4,0,3,0] and
            [g['type'] for g in beat['task']['guards']]==kinds and
            [g['post'] for g in beat['task']['guards']]==[True,False,False,False,False,False,False])


def contract():
    return {'terminal_cm':[-730,460,0],'panel_cm':PANEL+[110],
            'holds_ms':[4000,1000],'fuse_ms':[20000],
            'blast_cm_hp':[800,120],'safe_cm':[-2200,2900,0,-1000,3100,400,1500],
            'ground_patrol_periods_ms':[60000,60000,45000,45000,70000],
            'ground_patrol_pair_spacing_ms':[4000,3000],
            'drone_circuit_cm_ms':[0,0,540,600,36000,32],
            'roof_cm_permille':[600,400,1320,1300,570,340,1350,1360,800,750,475]}


def place_notice_square(beats,records,zones,layout,fail):
    selected=[(b,r) for b,r in zip(beats,records,strict=True) if b['id'] in BEATS]
    if not selected:return
    if len(selected)!=3:fail('notice square','all three square beats are required')
    if not ground_authored_valid(selected[0][0],layout):
        fail('notice square','authored ground patrols changed; review the physical routes and timing')
    for b,r in selected:
        z=zones[r['zone']]
        if z.place!='pl_kosatsuba':fail(b['id'],'charge needs the notice square')
        z.rect=tuple(ZONE);z.entry=tuple(ENTRY);z.walls=[];z.cover=[];z.props=[]
        r.update(entry=list(ENTRY),height_cm=0,anchor=list(PANEL),
                 exit={'center':[-1000,2800],'size':[300,300]},
                 spawns=[[2800,-300],[2800,0],[2800,300],[2500,-300],[2500,0],[2500,300]],
                 patrols=[[[-800,-500],[700,-500],[700,550],[-800,550]],
                          [[0,-600],[0,600]]])
        if b['id']=='ch03.b10':
            r['terminal_charge']=contract()
            r['patrols']=[[[900,800]],DRONE]+ground_patrols()
            r['objectives']=[list(PANEL),list(PANEL),list(SAFE)]
            r['volumes']=[{'event':'volume_enter:vol_b10_glint','center':[0,0],'size':[1800,1400]},
                          {'event':'volume_enter:vol_b10_dobuita','center':[0,382],'size':[1800,300]}]
            f=r['fieldcraft']
            for lamp in f['lamps']:
                lamp['at']={'terminal_glow_b10':[-730,460],'tsuji_andon_sw':[-900,-650],
                            'tsuji_andon_se':[900,-650]}[lamp['id']]
            f['surfaces']=[{'kind':'puddle','center':[-1000,2150],'size':[100,400],
                            'height_cm':0,'step_permille':2000,'crouch_permille':2000}]
            for y in (-382,382):
                f['surfaces'].append({'kind':'dobuita','center':[0,y],'size':[1800,45],
                    'height_cm':0,'step_permille':1500,'crouch_permille':1500})
                f['surfaces'].append({'kind':'edge_strip','center':[0,y+(16 if y>0 else -16)],'size':[1800,12],
                    'height_cm':0,'step_permille':1500,'crouch_permille':0})
            f['ladders']=roof_ladders()
            f['surfaces'].append({'kind':'board_roof','center':[525,1200],'size':[150,600],
                                 'height_cm':320,'step_permille':1500,'crouch_permille':1500})
        elif b['id']=='ch03.b11':
            r['camera']=[-1300,200,350,-1150,0,300,-730,460,160]


def notice_overlap(chapter,a,b=None):
    if chapter['id']!='ch03_lantern_ward':return False
    def square(z):return z['place']=='pl_kosatsuba' and z['rect']==ZONE
    if b is None:return square(a)
    return ((square(a) and b['place'] in ('pl_ura_nagaya','pl_chochin_kobo')) or
            (square(b) and a['place'] in ('pl_ura_nagaya','pl_chochin_kobo')))


def notice_valid(chapter):
    try:
        records=chapter['space']['beats']
        if chapter['id']!='ch03_lantern_ward':return not any('terminal_charge' in r for r in records)
        if any(('terminal_charge' in r)!=(r['beat']=='ch03.b10') for r in records):return False
        selected=[r for r in records if r['beat'] in BEATS]
        if len(selected)!=3:return False
        for r in selected:
            z=chapter['space']['zones'][r['zone']]
            if (z['place']!='pl_kosatsuba' or z['rect']!=ZONE or z['entry']!=ENTRY or
                    z['walls'] or z['cover'] or z['props'] or z['route'] or
                    r['entry']!=ENTRY or r['anchor']!=PANEL or r['height_cm']!=0):return False
        r=next(r for r in selected if r['beat']=='ch03.b10')
        beat=next(b for b in chapter['beats'] if b['id']=='ch03.b10');task=beat['task']
        return (ground_authored_valid(beat,chapter['layout']) and r['terminal_charge']==contract() and r['objectives']==[PANEL,PANEL,SAFE] and
                r['patrols']==[[[900,800]],DRONE]+ground_patrols() and r['fieldcraft']['ladders']==roof_ladders() and
                [s for s in r['fieldcraft']['surfaces'] if s['kind']=='board_roof']==[
                    {'kind':'board_roof','center':[525,1200],'size':[150,600],'height_cm':320,'step_permille':1500,'crouch_permille':1500}] and
                task['goal']=='objectives' and task['count']==3 and task['objective_hold_ms']==[4000,1000,0] and
                task['objectives']==['obj_plant_charge','obj_light_fuse','obj_reach_safe'] and
                beat['ext']['charge']=={'fuse_s':20,'blast_radius_cm':800,'damages_player':True} and
                beat['params']['complete']['objectives'][2]=={'id':'obj_reach_safe','volume':'vol_b10_blast_safe','within_s':20} and
                next(l['at'] for l in r['fieldcraft']['lamps'] if l['id']=='terminal_glow_b10')==[-730,460])
    except (KeyError,TypeError,IndexError,StopIteration):return False
