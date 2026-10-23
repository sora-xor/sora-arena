"""ch06.b14 culvert and moat. The middle inspection shaft is provisional.

The authored final 15 m at 140 cm/s takes 10.71 s, exceeding eight seconds
of breath. A visible 2 m air shaft divides it into 6.5 m submerged legs;
actual surfacing, with the existing three-second recovery, remains necessary.
"""

def place_flood(beats, records, zones, fail):
    if not any(b['id']=='ch06.b14' for b in beats): return
    from campaign_space import Zone
    beat=next(b for b in beats if b['id']=='ch06.b14')
    expected={'kind':'rising_water','from_cm':40,'to_cm':160,'over_s':150,'deep_volume':'vol_ankyo_deep'}
    if beat['ext'].get('hazard')!=expected or beat['ext'].get('traversal')!={'mode':'wade_swim','wade_noise_mult':2.0,'dive_max_s':8}:
        fail(beat['id'],'flood route requires the authored rise and eight-second dive contract')
    r=next(r for r in records if r['beat']==beat['id'])
    # Own campaign-only zone; never edit the practice/multiplayer citadel.
    x=max(z.rect[2] for z in zones)+15000
    rect=(x-11200,-4600,x+11000,600)
    z=Zone('ch06_flood_exfil',beat['place'],'citadel','hall',rect,300)
    z.entry=(x+200,0,0)
    r['zone']=len(zones);zones.append(z)
    r['entry']=[x+200,0,0];r['anchor']=[x+9500,-4300]
    r['exit']={'center':r['anchor'],'size':[400,300],'floor_cm':200}
    r['flood']={'origin':[x,0],'length_cm':9000,'width_cm':240,'height_cm':220,
                'deep_start_cm':7500,'deep_floor_cm':-200,'deep_roof_cm':20,
                'air_shaft_cm':[8150,8350],'from_cm':40,'to_cm':160,'rise_ms':150000,
                'provisional_air_shaft':True}
    r['volumes']=[{'event':'volume_enter:'+n,'center':[x+a,b],'size':[w,h]}
       for n,a,b,w,h in [('vol_ankyo_start',300,0,600,240),('vol_ankyo_grate_1',2000,0,300,240),

        ('vol_ankyo_deep',7500,0,150,240),('vol_water_gate_exit',9500,-400,400,150)]]
    r['spawns']=[[x+a,b] for a,b in [(2000,0),(4500,0),(7000,0),(9500,-700),(4000,-2100),(4150,-2100)]]
    r['patrols']=[]
    f=r['fieldcraft'];f['surfaces']=[]
    f['water']={'center':[x-100,-2000],'size':[22000,4800],'surface_cm_s':180,'dive_cm_s':140,
                'breath_ms':8000,'recover_ms':3000,'drown_hp_s':10,'surface_step_permille':2000,
                'cover':[{'center':[x+9500,-3900],'size':[1600,300]}],'lines':[]}
    # Hand lamps shine through the three ceiling grates. Their 1.1 s alarm
    # dwell follows the authored 0.9/s suspicion rate; they are not wall towers.
    f['searchlights']=[{'id':f'grate_lamp_{i+1}','at':[x+a,0],'height_cm':210,'yaw':0,'reach_cm':1,
        'road_from_cm':0,'road_to_cm':0,'sweep_deg':1,'period_ms':6000,'spot_cm':180,
        'suspicious_ms':400,'alert_ms':1100,'lock_ms':0,'active_on':None,'spooks':False}
        for i,a in enumerate((2000,4500,7000))]
    for a in f['allies']:
        a['at']=[x+100,0] if a['id']!='npc_kohagi' else [x+9850,-230]


def flood_valid(chapter):
    """Fail closed on a misplaced, malformed or mechanically changed flood contract."""
    try:
        beats=chapter['beats']; records=chapter['space']['beats']; zones=chapter['space']['zones']
        for b,r in zip(beats,records):
            if b['id']!='ch06.b14':
                if 'flood' in r: return False
                continue
            f=r['flood'];o=f['origin']
            if not isinstance(o,list) or len(o)!=2 or any(type(n)!=int for n in o): return False
            x,y=o
            if y!=0: return False
            expected={'origin':o,'length_cm':9000,'width_cm':240,'height_cm':220,'deep_start_cm':7500,
                'deep_floor_cm':-200,'deep_roof_cm':20,'air_shaft_cm':[8150,8350],'from_cm':40,'to_cm':160,
                'rise_ms':150000,'provisional_air_shaft':True}
            if f!=expected or any(type(f[k])!=int for k in expected if k not in ('origin','air_shaft_cm','provisional_air_shaft')): return False
            if type(f['provisional_air_shaft'])!=bool or any(type(v)!=int for v in f['air_shaft_cm']): return False
            if r['entry']!=[x+200,y,0] or r['anchor']!=[x+9500,y-4300] or r['height_cm']!=0: return False
            if r['exit']!={'center':r['anchor'],'size':[400,300],'floor_cm':200}: return False
            if zones[r['zone']]['id']!='ch06_flood_exfil' or b['task']['goal']!='exit': return False
            if r['spawns']!=[[x+a,y+c] for a,c in ((2000,0),(4500,0),(7000,0),(9500,-700),(4000,-2100),(4150,-2100))]: return False
            expected_volumes=[{'event':'volume_enter:'+n,'center':[x+a,y+c],'size':[w,h]}
                for n,a,c,w,h in [('vol_ankyo_start',300,0,600,240),('vol_ankyo_grate_1',2000,0,300,240),
                    ('vol_ankyo_deep',7500,0,150,240),('vol_water_gate_exit',9500,-400,400,150)]]
            if r['volumes']!=expected_volumes: return False
            w=r['fieldcraft']['water']
            for k,v in {'surface_cm_s':180,'dive_cm_s':140,'breath_ms':8000,'recover_ms':3000,'drown_hp_s':10,'surface_step_permille':2000}.items():
                if type(w[k])!=int or w[k]!=v: return False
            if w['center']!=[x-100,y-2000] or w['size']!=[22000,4800]: return False
            if r['fieldcraft']['surfaces'] or len(r['fieldcraft']['searchlights'])!=3: return False
            for i,l in enumerate(r['fieldcraft']['searchlights']):
                if l['at']!=[x+(2000,4500,7000)[i],y] or l['height_cm']!=210 or l['spot_cm']!=180: return False
            if {a['id'] for a in r['fieldcraft']['allies']}!={'npc_toranosuke','npc_iota','npc_kohagi'}: return False
            if any(a['detectable'] or a['downable'] for a in r['fieldcraft']['allies']): return False
        return True
    except (KeyError,TypeError,IndexError,ValueError): return False
