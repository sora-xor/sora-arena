"""Chapter-six ledger aisles and their physical link into the palace.

This is a spatial/encounter contract. Rendering, ordinary stealth difficulty,
sliding fusuma and carried auditor lamps need their own runtime evidence.
"""
import json

AISLES = (280, 720, 1160, 1600, 2040)
CROSS_AISLES = (1200, 2800, 4400, 6000)
SHELF_X = (0, 440, 880, 1320, 1760, 2200)
SHELF_Y = ((400,1040),(1360,2640),(2960,4240),(4560,5840))
# One-metre written-off gaps within six banks; the remaining shelf is solid.
NICHES = ((0,1800),(1,3400),(2,5000),(3,1800),(4,3400),(5,5000))
PERIODS = (0,0,0,0,0,0,35000,35000,0,0,40000,0)
HEIGHTS = (0,0,0,0,0,0,550,550,0,0,0,0)
YAWS = (90,90,-90,-90,0,180,0,0,90,90,0,-90)
TYPES = ('auditor',)*4+('enforcer_rifle',)*2+('drone',)*2+('auditor',)*2+('enforcer_rifle',)*2
POSTS = (4,5,8,11)


def p(origin,x,y):
    return [origin[0]+x,origin[1]+y]


def routes(origin,palace):
    raw = (((280,600),(280,5600)),((720,1000),(720,5400)),
           ((1600,5400),(1600,800)),((2040,5600),(2040,1000)),
           ((1160,2800),(1160,2800)),((1160,6000),(1160,6000)),
           ((280,1200),(2040,1200),(2040,4400),(280,4400)),
           ((720,2800),(2040,2800),(2040,6000),(720,6000)),
           ((2535,-100),(2535,-100)),((2535,400),(2535,1900)),
           ((-300,-135),(2200,-135)),((2540,2140),(2540,2140)))
    return [[p(origin if i<8 else palace,*point) for point in loop] for i,loop in enumerate(raw)]


def shelf_rects(origin):
    result=[]
    for bank,x in enumerate(SHELF_X):
        for low,high in SHELF_Y:
            cuts=[(low,high)]
            for b,center in NICHES:
                if b==bank and low<center<high:
                    cuts=[(low,center-50),(center+50,high)]
            for a,b in cuts:
                result.append([*p(origin,x,a),*p(origin,x+120,b)])
    return result


def floor_rects(origin):
    return [[*p(origin,0,0),*p(origin,2400,6400)],
            [*p(origin,-1000,0),*p(origin,0,800)],
            [*p(origin,1965,6400),*p(origin,2400,6670)]]


def palace_floors(origin):
    return [[*p(origin,-600,-270),*p(origin,4400,3400)],
            [*p(origin,0,-1070),*p(origin,2400,-270)]]


def inside(rect,at,margin=0):
    return rect[0]+margin<=at[0]<=rect[2]-margin and rect[1]+margin<=at[1]<=rect[3]-margin


def patch(origin,kind,rect,step,crouch):
    x,y,x1,y1=rect
    return {'kind':kind,'center':p(origin,(x+x1)//2,(y+y1)//2),
            'size':[x1-x,y1-y],'height_cm':0,'step_permille':step,'crouch_permille':crouch}


def surfaces(origin,palace):
    return [patch(palace,'nightingale_floor',(-600,-270,2400,0),4000,5000),
            patch(palace,'nightingale_floor',(2400,-270,2670,2200),4000,5000),
            patch(palace,'gravel',(0,0,2400,1600),1500,1500),
            patch(palace,'tatami',(0,-1070,1200,-270),500,500),
            patch(palace,'tatami',(1200,-1070,2400,-270),500,500),
            *[patch(origin,'puddle',(x-100,y-100,x+100,y+100),1500,1500)
              for x,y in ((280,500),(1160,6200),(2040,600))],
            patch(palace,'edge_strip',(-600,-270,2400,-250),4000,0),
            patch(palace,'edge_strip',(2650,0,2670,2200),4000,0)]


def volumes(origin,palace):
    return [{'event':'volume_enter:'+name,'center':p(frame,*point),'size':size}
            for name,frame,point,size in (
                ('vol_rubble_c1',origin,(1160,1200),[320,320]),
                ('vol_aisle_c2',origin,(1160,2800),[2400,320]),
                ('vol_uguisu_entry',palace,(-300,-135),[400,270]),
                ('vol_sugido',palace,(2540,2500),[500,400]))]


def place_ledger(beats,records,zones,pickups,fail):
    if not any(b['id']=='ch06.b06' for b in beats):
        return
    zindex=next(i for i,z in enumerate(zones) if z.place=='pl_ledger_corridors')
    pindex=next(i for i,z in enumerate(zones) if z.place=='pl_uguisu_hall')
    palace=(zones[pindex].rect[0]+600,zones[pindex].rect[3]-3400)
    origin=(palace[0]-3000,palace[1]-6670)
    z=zones[zindex]
    z.rect=(*p(origin,-1000,0),*p(origin,2400,6670))
    z.wall=600;z.cover=[];z.props=[];z.walls=[]
    z.entry=(*p(origin,-700,400),0)
    for beat,record in zip(beats,records,strict=True):
        if beat['id'] not in ('ch06.b05','ch06.b06'):
            continue
        record['ledger_hall']={'origin_cm':list(origin),'palace_origin_cm':list(palace),'palace_zone':pindex}
        if beat['id']=='ch06.b05':
            record['entry']=list(z.entry);record['anchor']=p(origin,-350,400)
            record['spawns']=[p(origin,280,600)]*6
            record['patrols']=[[p(origin,280,600),p(origin,280,1000)]]
            record['exit']={'center':p(origin,280,400),'size':[300,300]}
            continue
        record['entry']=[*p(origin,280,400),90]
        record['anchor']=p(origin,1160,1200)
        record['patrols']=routes(origin,palace)
        record['spawns']=[loop[0] for loop in record['patrols']]
        record['exit']={'center':p(palace,2540,2500),'size':[500,400]}
        record['volumes']=volumes(origin,palace)
        f=record['fieldcraft'];f['surfaces']=surfaces(origin,palace)
        f['stones']['piles']=[p(origin,x,y) for x,y in ((1160,1200),(720,4400),(1600,6000))]
        for alarm,at in zip(f['alarms'],((280,2800),(2040,4400)),strict=True):
            alarm['at']=p(origin,*at)
    for i,pickup in enumerate(v for v in pickups if v['zone']==zindex):
        pickup['at']=p(origin,-750+i*200,600)


def ledger_valid(chapter):
    try:
        relevant=[b for b in chapter['beats'] if b['id'] in ('ch06.b05','ch06.b06')]
        if not relevant:
            return not any('ledger_hall' in r for r in chapter['space']['beats'])
        zones=chapter['space']['zones'];rs=chapter['space']['beats']
        zindex=next(i for i,z in enumerate(zones) if z['place']=='pl_ledger_corridors')
        pindex=next(i for i,z in enumerate(zones) if z['place']=='pl_uguisu_hall')
        palace=(zones[pindex]['rect'][0]+600,zones[pindex]['rect'][3]-3400)
        origin=(palace[0]-3000,palace[1]-6670);z=zones[zindex]
        same=lambda a,b:json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True)
        if (z['wall_cm']!=600 or z['walls'] or z['cover'] or z['props'] or
            not same(z['rect'],[*p(origin,-1000,0),*p(origin,2400,6670)]) or
            not same(z['entry'],[*p(origin,-700,400),0])): return False
        for b,r in zip(chapter['beats'],rs,strict=True):
            if b['id'] not in ('ch06.b05','ch06.b06'):
                if 'ledger_hall' in r:return False
                continue
            if r['beat']!=b['id'] or r['zone']!=zindex or r['height_cm']!=0 or not same(r['ledger_hall'],
                {'origin_cm':list(origin),'palace_origin_cm':list(palace),'palace_zone':pindex}):return False
            if b['id']=='ch06.b05':
                if (not same(r['entry'],z['entry']) or r['anchor']!=p(origin,-350,400) or
                    not same(r['spawns'],[p(origin,280,600)]*6) or
                    not same(r['patrols'],[[p(origin,280,600),p(origin,280,1000)]]) or
                    not same(r['exit'],{'center':p(origin,280,400),'size':[300,300]})):return False
                continue
            expected={'entry':[*p(origin,280,400),90],'anchor':p(origin,1160,1200),
                'patrols':routes(origin,palace),'spawns':[v[0] for v in routes(origin,palace)],
                'exit':{'center':p(palace,2540,2500),'size':[500,400]},'volumes':volumes(origin,palace)}
            if any(not same(r[k],v) for k,v in expected.items()):return False
            if not same(r['fieldcraft']['surfaces'],surfaces(origin,palace)):return False
            if r['fieldcraft']['stones']['piles']!=[p(origin,x,y) for x,y in ((1160,1200),(720,4400),(1600,6000))]:return False
            if [a['at'] for a in r['fieldcraft']['alarms']]!=[p(origin,280,2800),p(origin,2040,4400)]:return False
            guards=b['task']['guards']
            if len(guards)!=12 or tuple(g['type'] for g in guards)!=TYPES:return False
            if any(g['post']!=(i in POSTS) for i,g in enumerate(guards)):return False
            if any(guards[i]['scan_deg']!=90 or guards[i]['scan_ms']!=8000 for i in (4,5)):return False
        return True
    except (KeyError,TypeError,IndexError,ValueError,StopIteration):
        return False


def union_supports(rects,point,margin=42):
    """Conservative capsule support: the entire enclosing square is on floor.

    Subdivide at every floor edge so adjoining rectangles are one continuous
    floor. Requiring clearance inside just one rectangle incorrectly rejects
    a capsule crossing the annex/hall or link/palace seam.
    """
    if margin==0:
        return any(inside(rect,point) for rect in rects)
    x0,y0,x1,y1=point[0]-margin,point[1]-margin,point[0]+margin,point[1]+margin
    edges=sorted({x0,x1,*[x for r in rects for x in (r[0],r[2]) if x0<x<x1]})
    for left,right in zip(edges,edges[1:]):
        mid=(left+right)/2
        intervals=sorted((r[1],r[3]) for r in rects if r[0]<=mid<=r[2])
        end=y0
        for low,high in intervals:
            if high<end:continue
            if low>end:break
            end=max(end,high)
        if end<y1:return False
    return True


def supported(chapter,index,point,include_palace=False,margin=42):
    """Exact floor union, including capsule clearance inside the narrow link.

    Shelf/wall clearance is additionally checked against the authored route
    constants and runtime collision; the bounding box's west void is not floor.
    """
    z=chapter['space']['zones'][index]
    origin=(z['rect'][0]+1000,z['rect'][1])
    rects=floor_rects(origin)
    if include_palace:
        rects+=palace_floors((origin[0]+3000,origin[1]+6670))
    return union_supports(rects,point,margin)
