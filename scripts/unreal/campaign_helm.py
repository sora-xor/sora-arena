"""Chapter seven's authored helm contract and local floor/wheel placement."""
import math

def place_helm(beats, records, zones, fail):
    for beat, record in zip(beats, records):
        if beat['id'] != 'ch07.b14':
            if 'trim_events' in beat['ext']:
                fail(beat['id'], 'helm trim belongs to ch07.b14')
            continue
        ext = beat['ext']
        trim, timer = ext.get('trim_events'), ext.get('fail_timer')
        if not isinstance(trim, dict) or not isinstance(timer, dict):
            fail(beat['id'], 'helm trim and deadline contracts are required')
        def whole(value, scale=1):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value*scale != round(value*scale):
                fail(beat['id'], 'helm values must be exact numeric units')
            return int(value*scale)
        thresholds = [whole(value, 1000) for value in trim.get('at_progress', [])]
        work, grace = whole(trim.get('interact_s'), 1000), whole(trim.get('grace_s'), 1000)
        decay = whole(trim.get('decay_per_s_if_ignored'), 1000)
        deadlines = [whole(timer.get(name+'_s'), 1000) for name in ('easy', 'normal', 'hard')]
        if (len(thresholds) != 3 or not 0 < thresholds[0] < thresholds[1] < thresholds[2] < 1000 or
                not 0 < work <= grace <= 60000 or not 0 < decay <= 1000 or
                any(not 60000 < value <= 1073741824 for value in deadlines) or
                trim.get('interact_point') != 'helm_trim_wheel' or timer.get('on_expire') != 'fail' or
                ext.get('fail_extra') != {'on':'x_timer_expired','to':'checkpoint'} or
                beat['task']['goal'] != 'hold' or beat['task']['duration_ms'] != 60000):
            fail(beat['id'], 'invalid helm contract')
        zone = zones[record['zone']]
        # Bridge-local authored lowest tier: X 0..6 m, Y -8..8 m;
        # wheel (3,-5), beacon (3,6). Existing bridge is still a proxy hall.
        origin = [zone['rect'][2]-900, 0]
        center = [origin[0]+300, origin[1]]
        wheel = [origin[0]+300, origin[1]-500]
        record['anchor'] = center
        record['helm'] = {'threshold_permille': thresholds, 'work_ms': work, 'grace_ms': grace,
                          'decay_permille': decay, 'deadline_ms': deadlines,
                          'center': center, 'size': [600,1600], 'wheel': wheel,
                          'beacon': [origin[0]+300, origin[1]+600]}
        for ally in record['fieldcraft']['allies']:
            if ally['id'] == 'kohagi':
                ally['at'] = [origin[0]+100, origin[1]+600]
