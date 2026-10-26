"""Place the charge encounter on the ward's existing terminal and north alley.

This binds the charge/escape contract. Roof and patrol staging are provisional;
their authored heights, circuits and timings are a separate open requirement.
"""

BEATS=('ch03.b10','ch03.b11','ch03.b12')
ZONE=[-2200,-1000,3200,3200]
ENTRY=[-1000,2800,-90]
PANEL=[-730,560]
SAFE=[-1600,3000]


def contract():
    return {'terminal_cm':[-730,460,0],'panel_cm':PANEL+[110],
            'holds_ms':[4000,1000],'fuse_ms':[20000],
            'blast_cm_hp':[800,120],'safe_cm':[-2200,2900,0,-1000,3100,400,1500]}


def place_notice_square(beats,records,zones,layout,fail):
    selected=[(b,r) for b,r in zip(beats,records,strict=True) if b['id'] in BEATS]
    if not selected:return
    if len(selected)!=3:fail('notice square','all three square beats are required')
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
            # Preserve a playable provisional ladder while the ridge route is rebuilt.
            ladder=f['ladders'][0];ladder.update(foot=[450,1200],height_cm=750,roof={'center':[900,1200],'size':[760,600]})
            f['surfaces'].append({'kind':'board_roof','center':[900,1200],'size':[760,600],
                                 'height_cm':750,'step_permille':1500,'crouch_permille':1500})
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
        return (r['terminal_charge']==contract() and r['objectives']==[PANEL,PANEL,SAFE] and
                task['goal']=='objectives' and task['count']==3 and task['objective_hold_ms']==[4000,1000,0] and
                task['objectives']==['obj_plant_charge','obj_light_fuse','obj_reach_safe'] and
                beat['ext']['charge']=={'fuse_s':20,'blast_radius_cm':800,'damages_player':True} and
                beat['params']['complete']['objectives'][2]=={'id':'obj_reach_safe','volume':'vol_b10_blast_safe','within_s':20} and
                next(l['at'] for l in r['fieldcraft']['lamps'] if l['id']=='terminal_glow_b10')==[-730,460])
    except (KeyError,TypeError,IndexError,StopIteration):return False
