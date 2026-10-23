"""Chapter-seven authored exposed hull and hangar. Functional proxy layout."""
def place_wind(beats, records, zones, fail):
    by={r['beat']:r for r in records}
    if 'ch07.b10' not in by:
        return
    for name,mode in [('ch07.b08','hangar'),('ch07.b09','hangar'),('ch07.b10','ridge')]:
        r=by[name]; z=zones[r['zone']]; x=z.rect[0]; y=0 if mode=='ridge' else z.rect[1]
        origin=[x,y]
        z.walls=[]
        r['wind']={'kind':mode,'origin':origin,'base_mps':8,'gust_mps':18,
                   'gust_schedule_ms':[11000,9000,14000,10000,12000],
                   'warning_ms':1000,'hold_ms':2500,'push_cm_s':[120,60,0,0],
                   'acceleration_cm_s2_per_mps':35,'fall_cost':25,'recoveries':3}
        if mode=='ridge':
            z.cover=[]; z.props=[]; z.z_bounds=(-2000,2500)
            r['entry']=[x+200,0,0]; z.entry=tuple(r['entry'])
            r['anchor']=[x+17800,0]
            r['exit']={'center':[x+17800,0],'size':[400,400],'floor_cm':-198}
            r['spawns']=[[x+2000,0],[x+9000,0],[x+16000,0]]
            r['patrols']=[]
            for v in r['volumes']:
                at=9000 if v['event']=='volume_enter:vol_ridge_mid' else 15000
                v.update(center=[x+at,0],size=[2000,2400],floor_cm=round(-at/90))
        else:
            z.cover=[]; z.props=[]
            r['entry']=[x+400,y+600,0]; z.entry=tuple(r['entry'])
            r['anchor']=[x+4000,y+1600]
            r['spawns']=[[x+7200,y+2200],[x+4000,y+200],[x+4000,y+2500],
                         [x+6600,y+200],[x+4000,y+4300]]
            r['patrols']=[]
            r['exit']={'center':[x+7750,y+1000],'size':[500,600]}
            if r['closing'] is not None:r['closing']=[x+7750,y+1000]
            for v in r['volumes']:
                if 'dorsal_hatch' in v['event']: v.update(center=[x+7750,y+1000],size=[500,600])
                elif 'sled_bay' in v['event']:v.update(center=[x+2500,y+3700],size=[1000,1400])
                elif 'canisters' in v['event']:v.update(center=[x+4000,y+1200],size=[2800,700])

def wind_valid(chapter):
    """Strict, scoped normalized contract; other chapters may not opt in."""
    expected={'base_mps':8,'gust_mps':18,'gust_schedule_ms':[11000,9000,14000,10000,12000],
              'warning_ms':1000,'hold_ms':2500,'push_cm_s':[120,60,0,0],
              'acceleration_cm_s2_per_mps':35,'fall_cost':25,'recoveries':3}
    for r in chapter['space']['beats']:
        wants=r['beat'] in ('ch07.b08','ch07.b09','ch07.b10')
        if ('wind' in r)!=wants:return False
        if not wants:continue
        w=r['wind'];ridge=r['beat']=='ch07.b10';z=chapter['space']['zones'][r['zone']]
        if type(w) is not dict or w.get('kind')!=('ridge' if ridge else 'hangar'):return False
        for k,v in expected.items():
            if type(w.get(k)) is not type(v) or w[k]!=v:return False
            if isinstance(v,list) and any(type(n) is not int for n in w[k]):return False
        if type(w.get('origin')) is not list or any(type(n) is not int for n in w['origin']):return False
        if w['origin']!=[z['rect'][0],0 if ridge else z['rect'][1]]:return False
        if [z['rect'][2]-z['rect'][0],z['rect'][3]-z['rect'][1]]!=([18000,2400] if ridge else [8000,4500]):return False
        if z['walls'] or z['cover'] or z['props']:return False
        x,y=w['origin']
        if ridge and (r['entry']!=[x+200,0,0] or r['anchor']!=[x+17800,0] or
                      r['exit']!={'center':[x+17800,0],'size':[400,400],'floor_cm':-198}):return False
    return True
