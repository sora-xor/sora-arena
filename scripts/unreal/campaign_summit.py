"""Elevated summit and the gallery's physical 18 metre north stair."""


def place_summit(beats, records, zones, fail):
    by_id = {r['beat']: r for r in records}
    if 'ch08.b13' not in by_id:
        return
    x,y=by_id['ch08.b11']['anchor']
    stairs=[[x+800,y+1800,14200],[x+800,y+2200,14200],
            [x-2000,y+2200,14800],[x-2000,y-2200,15400],
            [x,y-2200,16000],[x,y-1650,16000]]
    spec={'center':[x,y], 'height_cm':16000, 'radius_cm':1800, 'dais_cm':120, 'stairs':stairs}
    for name in ('ch08.b13','ch08.b14','ch08.b15'):
        row=by_id[name]
        row['height_cm']=16000
        row['summit']=spec.copy()
        row['entry']=[x,y-1650,90]
        row['anchor']=[x,y-700]
        row['exit']={'center':[x,y-1650],'size':[300,300],'floor_cm':16000}
        row['spawns']=[[x,y+800]]
        row['patrols']=[]
        if row['camera'] is not None:
            row['camera']=[x-1200,y-1100,16480,x-950,y-800,16420,x,y+1200,16180]
    gallery=by_id['ch08.b12']
    gallery['exit']={'center':stairs[-1][:2], 'size':[350,300], 'floor_cm':16000}
    # Places share XY in a tower. Their vertical ranges decide entry cuts.
    lower=zones[by_id['ch08.b10']['zone']]
    lower.z_bounds=(-500,15800)
    upper=zones[by_id['ch08.b13']['zone']]
    upper.rect=(x-2100,y-2100,x+2100,y+2100)
    upper.entry=tuple(by_id['ch08.b13']['entry'])
    upper.z_bounds=(15800,20000)
    upper.cover,upper.props=[],[]
