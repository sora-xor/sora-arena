"""Authored ward gate, with explicit buildable routes through its solids.

The proposed south patrol knots cross the hut and culvert. Keep the prose's
40/50-second duties, adding an apron detour around those solids. The prose's
three-metre culvert governs the provisional two-metre layout volume.
"""
import copy
from campaign_landing import WARD_APPROACH, ZONE as LANDING_ZONE

ZONE = [-8000,-1000,-4700,1100]
ENTRY = [-7820,-550,0]
# Enter the next district on foot before advancing, so the ordinary zone
# transition preserves the hero's position. Checkpoint entry stays separate.
EXIT = {'center':[-4450,0],'size':[300,720]}
STREET = [-5600,-360,-4700,360]
IDS = ['kidoban','g_b03_c2','g_b03_c3','g_b03_e1','g_b03_e2']
PATROLS = [
    [[-6300,150]],
    [[-7900,-650],[-7000,-650],[-7000,-800],[-6450,-800],[-7000,-800],[-7000,-650]],
    [[-6660,-290]],
    [[-6300,0]],
    [[-7900,-500],[-7900,600],[-6400,600],[-6400,-190],[-7000,-190],[-7000,-500]],
]
PERIODS = [0,40000,0,0,50000]
LAMPS = [[-6840,-430],[-6600,-380],[-6220,-70]]
PUDDLES = [[-7520,-300],[-7150,300],[-7100,-500]]
VOLUMES = [
    {'event':'volume_enter:vol_b03_first_conscript','center':[-7300,0],'size':[600,1400]},
    {'event':'volume_enter:vol_b03_bansho_rear','center':[-6850,-565],'size':[300,300]},
]
LADDER = {'id':'ladder_b03_shop','foot':[-6400,650],'yaw':90,
          'roof':{'center':[-6550,930],'size':[1100,320]},'height_cm':320,
          'drop_noise_cm':900,'straw':{'center':[-6000,500],'size':[260,260]},'guards':[]}


def contract():
    return {'plaza_cm':[-8000,-700,-6200,700],'fence_x_cm':-6200,'fence_height_cm':240,
            'gate_width_cm':360,'wicket_cm':[-6200,135,90,120],
            'culvert_cm':[-6200,-650,-90,300,100,90],
            'scanner_cm':[-6220,-45,0,20,270,240],
            'guard_ids':list(IDS),'periods_ms':list(PERIODS),'shared_landing_cm':list(WARD_APPROACH),
            'tenement_street_cm':list(STREET)}


def walls():
    return [[-8030,50,60,2220,420],[-5570,-710,60,700,420],[-6600,-1030,2000,60,420],
            [-6800,1130,2400,60,420],[-5570,760,60,800,420],
            [-5120,-390,840,60,420],[-5120,390,840,60,420]]


def shared_approach(chapter, a, b):
    """Only the authored landing/ward entrance shares a floor rectangle."""
    if chapter['id']!='ch03_lantern_ward':return False
    pair={a['place']:a,b['place']:b}
    return (set(pair)=={'pl_horiwari','pl_kido'} and pair['pl_horiwari']['rect']==LANDING_ZONE and
            pair['pl_kido']['rect']==ZONE and
            any(r['beat']=='ch03.b03' and r.get('ward_gate',{}).get('shared_landing_cm')==WARD_APPROACH
                for r in chapter['space']['beats']))


def ward_hub_neighbour(chapter, zone, rect):
    # The continuous street ends at the tenements, 15.5 m from the hub's
    # west bound, inside the generic 20 m spacing for disconnected places.
    return (chapter['id']=='ch03_lantern_ward' and zone['place']=='pl_kido' and
            zone['rect']==ZONE and tuple(rect)==(-3150,-2550,3150,2550))


def place_ward_gate(beats,records,zones,layout,fail):
    for b,r in zip(beats,records,strict=True):
        if b['id']!='ch03.b03':continue
        guards=b['params']['guards'];authored={p['id']:p for p in layout['patrols']}
        if ([g.get('id') for g in guards]!=IDS or
            authored.get('pt_b03_c2',{}).get('points_cm')!=[[-7900,-650],[-6300,-650]] or
            authored.get('pt_b03_c2',{}).get('loop_s')!=40 or
            authored.get('pt_b03_e2',{}).get('points_cm')!=[[-7900,-600],[-7900,600],[-6400,600],[-6400,-600]] or
            authored.get('pt_b03_e2',{}).get('loop_s')!=50 or
            b['ext'].get('hazards')!=[{'id':'scan_arch_b03','on_enter':'alert'}]):
            fail(b['id'],'ward gate guard/hazard contract changed; review physical binding')
        z=zones[r['zone']]
        if z.place!='pl_kido':fail(b['id'],'ward gate needs its own place')
        z.rect=tuple(ZONE);z.entry=tuple(ENTRY);z.wall=420;z.walls=walls();z.cover=[];z.props=[]
        r.update(entry=list(ENTRY),anchor=[-7200,0],spawns=[p[0] for p in PATROLS],
                 patrols=copy.deepcopy(PATROLS),exit=copy.deepcopy(EXIT),volumes=copy.deepcopy(VOLUMES),ward_gate=contract())
        f=r['fieldcraft']
        if [p['id'] for p in f['lamps']]!=['andon_b03_bansho','brazier_b03','scan_arch_b03']:
            fail(b['id'],'ward gate lamps changed')
        for lamp,at in zip(f['lamps'],LAMPS,strict=True):lamp['at']=list(at)
        # The scanner is an active sensor, not an extinguishable lantern.
        f['lamps'][2].update(snuff='none',hold_ms=0,relight_ms=0)
        if [p['kind'] for p in f['surfaces']]!=['puddle']*3+['running_water']:
            fail(b['id'],'ward gate surfaces changed')
        for patch,at in zip(f['surfaces'][:3],PUDDLES,strict=True):patch.update(center=list(at),size=[180,120])
        f['surfaces'][3].update(center=[-6200,-650],size=[300,100],height_cm=-90)
        f['ladders']=[copy.deepcopy(LADDER)]


def ward_gate_valid(chapter):
    try:
        records=chapter['space']['beats'];selected=[r for r in records if 'ward_gate' in r]
        if not chapter['id'].startswith('ch03_'):return not selected
        if len(selected)!=1:return False
        r=selected[0];z=chapter['space']['zones'][r['zone']];f=r['fieldcraft']
        if (r['beat']!='ch03.b03' or r['ward_gate']!=contract() or r['entry']!=ENTRY or r['height_cm']!=0 or
            r['patrols']!=PATROLS or r['spawns']!=[p[0] for p in PATROLS] or r['exit']!=EXIT or r['volumes']!=VOLUMES or
            z['id']!='pl_kido' or z['rect']!=ZONE or z['entry']!=ENTRY or z['wall_cm']!=420 or
            z['walls']!=walls() or z['cover'] or z['props'] or z['route'] or f['ladders']!=[LADDER]):return False
        lamps=f['lamps']
        if len(lamps)!=3 or [p['at'] for p in lamps]!=LAMPS:return False
        for p,name,kind,radius,snuff,hold in zip(lamps,
            ['andon_b03_bansho','brazier_b03','scan_arch_b03'],['andon','brazier','arch'],[650,400,450],['hold','none','none'],[1000,0,0],strict=True):
            if (p['id'],p['kind'],p['radius_cm'],p['snuff'],p['hold_ms'],p['relight_ms'])!=(name,kind,radius,snuff,hold,0):return False
        patches=f['surfaces']
        if len(patches)!=4:return False
        for p,at in zip(patches[:3],PUDDLES,strict=True):
            if p!={'kind':'puddle','center':at,'size':[180,120],'height_cm':0,'step_permille':2000,'crouch_permille':2000}:return False
        return patches[3]=={'kind':'running_water','center':[-6200,-650],'size':[300,100],'height_cm':-90,'step_permille':500,'crouch_permille':500}
    except (KeyError,IndexError,TypeError):return False
