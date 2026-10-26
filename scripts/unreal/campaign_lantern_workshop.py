"""Bind ch03's lantern workshop to its authored street, floor and yard."""
import copy

BEATS=('ch03.b08','ch03.b09')
ZONE=[1450,-2500,3700,200]
ENTRY=[2000,-2300,90]
STATIONS=[[2100,-620],[2100,-950],[2100,-1300],[2790,-2050]]
# Clear staging positions for the existing wave runner. Authored vault and
# rooftop arrival behavior is a separate encounter implementation.
SPAWNS=[[3280,-1050],[3100,-1050],[2920,-1050],[2000,-2320],[2000,-2420],[2750,-1700]]


def contract():
    return {'building_cm':[1600,-1500,2320,-400], 'plank_cm':[1780,-1500,2320,-400,45],
            'earth_passage_cm':[1600,-1500,1780,-400], 'back_door_cm':[1900,-1500,140],
            'yard_cm':[1600,-2200,3400,-900], 'well_cm':[2600,-1400],
            'storehouse_cm':[2900,-2200,3400,-1600,650], 'back_gate_cm':[2000,-2200,180]}


def record_values(beat):
    r={'entry':list(ENTRY),'height_cm':0,'anchor':[1900,-1660],
       'spawns':copy.deepcopy(SPAWNS),'patrols':[],
       'exit':{'center':[3480,-250],'size':[300,300]},'lantern_workshop':contract()}
    if beat=='ch03.b09':
        r.update(anchor=[2050,-950],stations=copy.deepcopy(STATIONS),step_stations=[0,1,1,2,3,3])
    return r


def place_lantern_workshop(beats,records,zones,sites,pickups,layout,fail):
    selected=[(b,r) for b,r in zip(beats,records,strict=True) if b['id'] in BEATS]
    if not selected:return
    if len(selected)!=2:fail('lantern workshop','both combat and manufacturing beats are required')
    points={p['id']:p['positions_cm'] for p in layout['points']}
    for name,at in [('sp_b08_street',[3400,-1000,0]),('sp_b08_canal',[2000,-2250,0]),
                    ('sp_b08_eastfence',[3400,-1600,0]),('sp_b08_kura_roof',[3150,-1900,650])]:
        if points.get(name)!=[at]:fail(name,'authored workshop entrance changed; review its geometry')
    for b,r in selected:
        z=zones[r['zone']]
        if z.place!='pl_chochin_kobo':fail(b['id'],'workshop needs its own authored zone')
        z.rect=tuple(ZONE);z.entry=tuple(ENTRY);z.wall=430
        z.walls=[];z.cover=[];z.props=[]
        r.update(record_values(b['id']))
        if b['site'] is not None:sites[b['site']]=list(r['anchor'])
    for p in pickups:
        if p['zone']==selected[0][1]['zone']:
            if p['collectible']!='ch03.c04':fail(p['collectible'],'unplaced workshop collectible')
            p['at']=[3150,-2000]


def workshop_hub_overlap(chapter,zone,rect):
    return (chapter['id']=='ch03_lantern_ward' and zone['place']=='pl_chochin_kobo' and
            zone['rect']==ZONE and tuple(rect)==(-3150,-2550,3150,2550))


def workshop_neighbour(chapter,a,b):
    pair={a['place']:a,b['place']:b}
    return (chapter['id']=='ch03_lantern_ward' and set(pair)=={'pl_ura_nagaya','pl_chochin_kobo'} and
            pair['pl_ura_nagaya']['rect']==[-4700,-400,-600,4300] and pair['pl_chochin_kobo']['rect']==ZONE)


def workshop_valid(chapter):
    try:
        records=chapter['space']['beats']
        if chapter['id']!='ch03_lantern_ward':return not any('lantern_workshop' in r for r in records)
        selected=[r for r in records if r['beat'] in BEATS]
        if len(selected)!=2 or any(('lantern_workshop' in r)!=(r['beat'] in BEATS) for r in records):return False
        for r in selected:
            if any(r.get(k)!=v for k,v in record_values(r['beat']).items()):return False
            z=chapter['space']['zones'][r['zone']]
            if (z['id']!='pl_chochin_kobo' or z['rect']!=ZONE or z['entry']!=ENTRY or z['wall_cm']!=430 or
                    z['walls'] or z['cover'] or z['props'] or z['route']):return False
        pickup=next(p for p in chapter['space']['pickups'] if p['collectible']=='ch03.c04')
        return (pickup['zone']==selected[0]['zone'] and pickup['at']==[3150,-2000] and
                pickup.get('height_cm',0)==0 and chapter['space']['sites'][1]==[2050,-950])
    except (KeyError,TypeError,IndexError,StopIteration):return False
