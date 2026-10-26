"""Chapter-three west landing in its authored arena-relative centimetres.

The prose requires a figure-eight; the proposed four patrol knots draw a
diamond. Keep their bounds, centre, altitude and period, and sample a genuine
crossing figure-eight within that envelope. D2 keeps its exact authored ends.
"""
import copy

YARD = [-12000, -2800, -7600, -1200]
ZONE = [-12000, -3400, -7600, -660]  # Landing steps, warehouses and exit lane.
ENTRY = [-11300, -2700, 0]
D1_OFFSETS = [(0,0),(459,354),(849,500),(1109,354),(1200,0),(1109,-354),(849,-500),(459,-354),
              (0,0),(-459,354),(-849,500),(-1109,354),(-1200,0),(-1109,-354),(-849,-500),(-459,-354)]
PATROLS = [[[x-10200,y-2000] for x,y in D1_OFFSETS], [[-11800,-2700],[-7800,-2700]]]
PERIODS = [40000,30000]
HEIGHTS = [500,400]
CARGO = [[-11250,-2300],[-10500,-1850],[-9800,-2350],[-9200,-1450],[-8600,-1800]]
LAMPS = [[-11440,-1360],[-9600,-1360],[-8300,-1780]]
PUDDLES = [[-10700,-2190],[-10200,-2050],[-9700,-2170],[-9300,-2110],[-8600,-2450],[-8100,-2290]]
EXIT = {"center":[-7820,-850],"size":[360,300]}
VOLUMES = [
    {"event":"volume_enter:vol_b02_drones","center":[-11300,-2400],"size":[1000,800]},
    {"event":"volume_enter:vol_b02_puddles","center":[-10400,-2100],"size":[800,600]},
    {"event":"volume_enter:vol_b02_andon","center":[-11300,-1450],"size":[1000,500]},
]


def contract():
    return {"yard_cm":list(YARD),"altitudes_cm":list(HEIGHTS),"periods_ms":list(PERIODS),
            "figure_eight":True,"canal_ping_pong":True}


def walls():
    x,y,x1,y1=ZONE
    return [[x-30,(y+y1)//2,60,y1-y+120,360],[x1+30,(y+y1)//2,60,y1-y+120,360],
            [(x+x1)//2,y-30,x1-x,60,360],[(x+x1)//2,y1+30,x1-x,60,360]]


def place_landing(beats, records, zones, layout, fail):
    selected=[(b,r) for b,r in zip(beats,records,strict=True) if b['id']=='ch03.b02']
    if not selected:
        return
    beat,record=selected[0]
    authored={p['id']:p for p in layout['patrols']}
    for i,expected in enumerate(([[ -11400,-2000],[-10200,-1500],[-9000,-2000],[-10200,-2500]],PATROLS[1])):
        p=authored.get(f'pt_b02_d{i+1}',{})
        if (p.get('points_cm')!=expected or p.get('loop_s',0)*1000!=PERIODS[i] or p.get('alt_cm')!=HEIGHTS[i]):
            fail(beat['id'],'west-landing authored route changed; review its geometry and timing')
    zone=zones[record['zone']]
    if zone.place!='pl_horiwari' or [g['type'] for g in beat['task']['guards']]!=['drone','drone']:
        fail(beat['id'],'west landing requires its own place and two drones')
    zone.rect=tuple(ZONE);zone.entry=tuple(ENTRY);zone.wall=360
    zone.walls=walls();zone.cover=[[x,y,230,180,140] for x,y in CARGO];zone.props=[]
    # The cinematic and stealth beat share the place. Keep its control handoff
    # at the authored top of the steps, without moving any other chapter space.
    for b,r in zip(beats,records,strict=True):
        if r['zone']!=record['zone']:
            continue
        r.update(entry=list(ENTRY),anchor=[-11000,-2500],spawns=[[-11400,-2100],[-8000,-2700]],
                 patrols=copy.deepcopy(PATROLS),exit=copy.deepcopy(EXIT),landing=contract())
        if b['id']=='ch03.b01':
            # The final landing shot only. The full 100 m boat approach remains
            # a cinematic production task; this does not claim to replace it.
            r['camera']=[-11700,-3250,280,-11300,-2850,220,-11000,-2200,160]
        elif b['id']=='ch03.b02':
            r['volumes']=copy.deepcopy(VOLUMES)
            lamps=r['fieldcraft']['lamps'];surfaces=r['fieldcraft']['surfaces']
            if [p['id'] for p in lamps]!=['andon_b02_w1','andon_b02_w3','andon_b02_shed'] or len(surfaces)!=6:
                fail(b['id'],'west landing requires its three owned lamps and six puddles')
            for lamp,point in zip(lamps,LAMPS,strict=True):lamp['at']=list(point)
            for surface,point in zip(surfaces,PUDDLES,strict=True):
                surface.update(center=list(point),size=[280,140])
        else:
            fail(b['id'],'unreviewed beat shares the west landing')


def landing_valid(chapter):
    try:
        if not chapter['id'].startswith('ch03_'):
            return all('landing' not in r for r in chapter['space']['beats'])
        records={r['beat']:r for r in chapter['space']['beats']}
        r=records['ch03.b02'];zone=chapter['space']['zones'][r['zone']]
        if (zone['id']!='pl_horiwari' or zone['place']!='pl_horiwari' or zone['rect']!=ZONE or zone['entry']!=ENTRY or
                zone['wall_cm']!=360 or zone['route'] or
                zone['cover']!=[[x,y,230,180,140] for x,y in CARGO] or zone['props'] or zone['walls']!=walls()):
            return False
        for name in ('ch03.b01','ch03.b02'):
            p=records[name]
            if (p['zone']!=r['zone'] or p['entry']!=ENTRY or p['landing']!=contract() or
                    p['patrols']!=PATROLS or p['exit']!=EXIT):return False
        if r['volumes']!=VOLUMES:return False
        lamps=r['fieldcraft']['lamps'];puddles=r['fieldcraft']['surfaces']
        if [p['at'] for p in lamps]!=LAMPS:return False
        if [p['id'] for p in lamps]!=['andon_b02_w1','andon_b02_w3','andon_b02_shed']:return False
        if any(p['kind']!='andon' or p['radius_cm']!=650 or p['snuff']!='hold' or
               p['hold_ms']!=1000 or p['relight_ms']!=0 for p in lamps):return False
        if [p['center'] for p in puddles]!=PUDDLES:return False
        if any(p['kind']!='puddle' or p['size']!=[280,140] or p['height_cm']!=0 or
               p['step_permille']!=2000 or p['crouch_permille']!=2000 for p in puddles):return False
        return all('landing' not in r for k,r in records.items() if k not in ('ch03.b01','ch03.b02'))
    except (KeyError,TypeError,IndexError):
        return False
