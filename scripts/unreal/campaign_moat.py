"""Authored ch06.b02 water frame; appended after climb to preserve old spaces."""
from campaign_climb import exact

TRAVERSAL = {"mode": "swim", "surface_speed_cm_s": 180, "dive_speed_cm_s": 140,
             "dive_max_s": 8, "breath_recover_s": 3, "drown_dps": 10,
             "surface_noise_cm": 500, "dive_noise_cm": 0, "weapons_usable": False}


AUTHORED_PARAMS = {'guards': [{'id': 'g_moat_parapet_a',
             'type': 'enforcer_rifle',
             'patrol': 'spl_moat_parapet_a',
             'sight': {'cone_deg': 90, 'range_cm': 3500, 'dark_range_cm': 1200},
             'hearing_cm': 1200},
            {'id': 'g_moat_parapet_b',
             'type': 'enforcer_rifle',
             'patrol': 'spl_moat_parapet_b',
             'sight': {'cone_deg': 90, 'range_cm': 3500, 'dark_range_cm': 1200},
             'hearing_cm': 1200},
            {'id': 'g_moat_drone',
             'type': 'drone',
             'patrol': 'spl_moat_drone_fig8',
             'sight': {'cone_deg': 50, 'range_cm': 1200, 'dark_range_cm': 1000},
             'hearing_cm': 600}],
 'waves': [{'id': 'w_moat_alarm',
            'trigger': 'alert_state:alert',
            'enemies': [{'type': 'enforcer_rifle', 'count': 2, 'spawn': 'sp_moat_parapet_c'}],
            'effects': ['searchlights_lock_last_seen_6s', 'drone_descend_to_300cm']}],
 'allies': [{'npc': 'npc_kohagi', 'role': 'swim_lead', 'detectable': False}],
 'detection': {'suspicion_rate': 0.8, 'suspicious_at': 0.35, 'alert_threshold': 1.0, 'search_s': 20}}
TASK_GUARDS = [{'type': 'enforcer_rifle',
  'post': False,
  'scan_deg': 0,
  'scan_ms': 0,
  'turn_ms': 0,
  'sight_cm': 3500,
  'dark_sight_cm': 1200,
  'view_deg': 90,
  'hearing_cm': 1200,
  'suspicion_permille': 0},
 {'type': 'enforcer_rifle',
  'post': False,
  'scan_deg': 0,
  'scan_ms': 0,
  'turn_ms': 0,
  'sight_cm': 3500,
  'dark_sight_cm': 1200,
  'view_deg': 90,
  'hearing_cm': 1200,
  'suspicion_permille': 0},
 {'type': 'drone',
  'post': False,
  'scan_deg': 0,
  'scan_ms': 0,
  'turn_ms': 0,
  'sight_cm': 1200,
  'dark_sight_cm': 1000,
  'view_deg': 50,
  'hearing_cm': 600,
  'suspicion_permille': 0}]
SENSORS = [{'id': 's_searchlight_1',
  'kind': 'searchlight',
  'mount': 'yagura_s1',
  'sweep_deg': 70,
  'period_s': 10,
  'spot_radius_cm': 400,
  'suspicious_after_s': 0.5,
  'alert_after_s': 1.5},
 {'id': 's_searchlight_2',
  'kind': 'searchlight',
  'mount': 'yagura_s2',
  'sweep_deg': 70,
  'period_s': 10,
  'spot_radius_cm': 400,
  'suspicious_after_s': 0.5,
  'alert_after_s': 1.5},
 {'id': 's_float_line',
  'kind': 'float_line',
  'volume': 'vol_moat_boom',
  'touch_noise_cm': 1400,
  'clear_depth_cm': 80}]

def contract(origin):
    return {"origin": list(origin), "length_cm": 22000, "width_cm": 3600,
            "surface_cm": 0, "bed_cm": -240, "gate_bed_cm": -300,
            "parapet_walk_cm": 1750, "parapet_y_cm": 4860,
            "gate_x_cm": [20600, 21000], "gate_y_cm": [3560, 3640],
            "gate_bottom_cm": -180, "gate_top_cm": -120,
            "float_clear_depth_cm": 80, "hitscan_clear_depth_cm": 100,
            "swim_radius_cm": 28, "swim_half_height_cm": 28, "head_offset_cm": 18,
            "surface_center_cm": -6, "dive_center_cm": -150,
            "provisional_posture": True}


def area(origin, x0, y0, x1, y1, event=None):
    row = {"center": [origin[0] + (x0+x1)//2, origin[1] + (y0+y1)//2], "size": [x1-x0, y1-y0]}
    if event:
        row["event"] = "volume_enter:" + event
    return row


def fields(origin):
    x, y = origin
    return {"entry": [x+1000, y-100, 0], "anchor": [x+20800, y+3400], "height_cm": 0,
            "exit": area(origin, 20400, 3700, 21400, 4500),
            "spawns": [[x+19500,y+4860],[x+20500,y+4860]],
            "patrols": [[[x+3000,y+4860],[x+10000,y+4860]],
                        [[x+11000,y+4860],[x+19000,y+4860]],
                        [[x+4000,y+1800],[x+7500,y+2800],[x+11000,y+1800],[x+14500,y+800],
                         [x+18000,y+1800],[x+14500,y+2800],[x+11000,y+1800],[x+7500,y+800]]],
            "volumes": [area(origin,8800,400,9600,3200,"vol_moat_pilings"),
                        area(origin,13000,0,13400,3600,"vol_moat_boom"),
                        area(origin,3000,3000,20000,3600,"vol_moat_wallbase"),
                        area(origin,4000,400,7000,1400,"vol_moat_lotus_1")],
            "moat": contract(origin)}


def water(origin):
    return {**area(origin,0,-400,22000,4500), "surface_cm_s":180,"dive_cm_s":140,
            "breath_ms":8000,"recover_ms":3000,"drown_hp_s":10,"surface_step_permille":1111,
            "cover":[area(origin,*r) for r in ((0,-400,2000,200),(4000,400,7000,1400),
                      (10000,2000,12500,3200),(16500,600,18500,1600))],
            "lines":[{**area(origin,13000,0,13400,3600),"noise_cm":1400}]}


def authored_valid(beat):
    return (all(exact(beat["params"][k],v) for k,v in AUTHORED_PARAMS.items())
            and exact(beat["task"]["guards"],TASK_GUARDS) and exact(beat["ext"]["sensors"],SENSORS)
            and exact(beat["ext"]["traversal"],TRAVERSAL) and beat["ext"]["exit"]=="vol_water_gate_inner"
            and exact(beat["ext"]["sensors"][-1],{"id":"s_float_line","kind":"float_line",
              "volume":"vol_moat_boom","touch_noise_cm":1400,"clear_depth_cm":80})
            and beat["task"]["goal"]=="exit" and beat["task"]["on_detected"]=="reinforce"
            and beat["task"]["stealth"]["rate_permille"]==800
            and beat["task"]["stealth"]["search_ms"]==20000)


def place_moat(beats,records,zones,pickups,fail):
    if not any(b["id"]=="ch06.b02" for b in beats):
        return
    from campaign_space import Zone
    beat=next(b for b in beats if b["id"]=="ch06.b02")
    if not authored_valid(beat):
        fail(beat["id"],"moat requires authored swimming, float depth and detection rules")
    record=next(r for r in records if r["beat"]==beat["id"])
    x=max(z.rect[2] for z in zones)+20000
    origin=[x,0]
    zone=Zone("ch06_physical_moat",beat["place"],"citadel","yard",(x-1000,-1000,x+23000,5500),360)
    zone.entry=(x+1000,-100,0)
    record["zone"]=len(zones)
    zones.append(zone)
    record.update(fields(origin))
    craft=record["fieldcraft"]
    craft["water"]=water(origin)
    craft["allies"][0]["at"]=[x+1200,-50]
    for light,xx in zip(craft["searchlights"],(6000,15000)):
        light.update(at=[x+xx,4800],height_cm=1750,reach_cm=3000,yaw=-90)
    for pickup in pickups:
        if pickup["collectible"]=="ch06.c01":
            pickup.update(zone=record["zone"],at=[x+20800,3500])


def moat_valid(chapter):
    try:
        if [b["id"] for b in chapter["beats"]]!=[r["beat"] for r in chapter["space"]["beats"]]: return False
        for beat,record in zip(chapter["beats"],chapter["space"]["beats"]):
            if beat["id"]!="ch06.b02":
                if "moat" in record: return False
                continue
            if not authored_valid(beat): return False
            origin=record["moat"]["origin"]
            if type(origin) is not list or len(origin)!=2 or any(type(v) is not int for v in origin) or origin[1]!=0:
                return False
            if not -(2**31)+1000<=origin[0]<=2**31-1-23000: return False
            if any(not exact(record[k],v) for k,v in fields(origin).items()): return False
            z=record["zone"]
            if type(z) is not int or not 0<=z<len(chapter["space"]["zones"]): return False
            zone=chapter["space"]["zones"][z]
            if zone["id"]!="ch06_physical_moat" or zone["place"]!="pl_citadel_moat" or zone["cover"] or zone["props"] or zone["route"]: return False
            if not exact(zone["rect"],[origin[0]-1000,-1000,origin[0]+23000,5500]) or not exact(zone["entry"],record["entry"]): return False
            craft=record["fieldcraft"]
            if not exact(craft["water"],water(origin)): return False
            if len(craft["allies"])!=1 or craft["allies"][0]["detectable"] or craft["allies"][0]["at"]!=[origin[0]+1200,-50]: return False
            for light,xx in zip(craft["searchlights"],(6000,15000)):
                for k,v in {"at":[origin[0]+xx,4800],"height_cm":1750,"reach_cm":3000,"yaw":-90,"sweep_deg":70,"period_ms":10000,"spot_cm":800,"suspicious_ms":500,"alert_ms":1500,"lock_ms":6000}.items():
                    if not exact(light[k],v): return False
            if len(craft["searchlights"])!=2: return False
        return True
    except (KeyError,TypeError,IndexError,ValueError):
        return False
