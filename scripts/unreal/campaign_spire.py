"""Chapter eight's physical spiral. Proxy collision, independent of final art."""

VERTICES = [(-1386, 0), (-693, -1200), (693, -1200), (1386, 0), (693, 1200), (-693, 1200)]


def place_spire(beats, records, zones, fail):
    by_id = {row['beat']: row for row in records}
    if 'ch08.b10' not in by_id:
        return
    beat = next(row for row in beats if row['id'] == 'ch08.b10')
    expected = [
        ('start', [('enforcer_rifle', 4, 'sp_sp_L2_ramp'), ('marksman', 1, 'sp_sp_L2_gantry_far')]),
        ('alive_below:2', [('shield_enforcer', 2, 'sp_sp_L3_ramp_down'), ('blade_retainer', 2, 'sp_sp_L3_ramp_down')]),
        ('volume_enter:vol_spire_L3', [('drone', 4, 'sp_sp_void_air'), ('grenadier', 1, 'sp_sp_L4_gantry'), ('auditor', 2, 'sp_sp_L4_office')])]
    actual = [(w['trigger'], [(g['type'], g['count'], g['spawn']) for g in w['enemies']]) for w in beat['params']['waves']]
    if actual != expected or beat['params']['complete'] != {'kind': 'all_waves_cleared'}:
        fail(beat['id'], 'spire requires its authored level-specific wave contract')
    row, lift = by_id['ch08.b10'], by_id['ch08.b11']
    x, y = lift['anchor']
    ramp = [[x + VERTICES[n % 6][0], y + VERTICES[n % 6][1], (n * 2700 + 12) // 24] for n in range(25)]
    spawns = [[ramp[8][0] + dx, ramp[8][1] + dy, 900] for dx, dy in [(-100,-100),(-100,100),(100,-100),(100,100)]]
    spawns += [[x-693,y+1200,900]]
    spawns += [[ramp[16][0]+dx,ramp[16][1]+dy,1800] for dx,dy in [(-100,-100),(-100,100),(100,-100),(100,100)]]
    spawns += [[x+dx,y+dy,2100] for dx,dy in [(-300,-300),(300,-300),(-300,300),(300,300)]]
    spawns += [[x-1000,y,2700],[x-1386,y-100,2700],[x-1386,y+100,2700]]
    row['spire'] = {'center': [x,y], 'width_cm': 400, 'void_diameter_cm': 1400, 'ramp': ramp, 'spawns': spawns}
    row['entry'] = [x-1500,y, -60]
    row['anchor'] = [x-1386,y]
    row['spawns'] = [p[:2] for p in spawns]
    row['patrols'] = []
    row['exit'] = {'center': [x-1100,y], 'size': [400,300], 'floor_cm': 2700}
    for volume in row['volumes']:
        level = 16 if volume['event'] == 'volume_enter:vol_spire_L3' else 8
        volume.update(center=ramp[level][:2], size=[500,500], floor_cm=ramp[level][2])
    for n, ally in enumerate(row['fieldcraft']['allies']):
        ally['at'] = [x-1450+(n%2)*140,y-150+(n//2)*150]
    zone = zones[row['zone']]
    zone.rect = (x-1900,y-1900,x+1900,y+2600)
    zone.entry = tuple(row['entry'])
    zone.cover, zone.props = [], []
