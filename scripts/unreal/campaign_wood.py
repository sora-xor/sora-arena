"""Chapter-one optional wood: authored XY frame, with connected provisional floors.

Chapter-01 §3.5/§4 b08 specifies the POIs, trail and 45 m challenge. Heights,
the clapper's southward azimuth and 30×40 cm face are provisional gameplay
collision choices; they do not qualify the final terrain or set-piece art.
"""
import math

POIS = (("poi_ch01_issoseki", -10000, 8800),
        ("poi_ch01_vista", -9000, 2600),
        ("poi_ch01_sakaiishi", -6000, 3400),
        ("poi_ch01_hokora", -11800, 10000))


def connect_wood(space, beats, layout):
    if not any(b["id"] == "ch01.b08" for b in beats):
        return
    rows = {b["beat"]: b for b in space["beats"]}
    wood, range_, smithy = (rows[k] for k in ("ch01.b08", "ch01.b07", "ch01.b09"))
    zone = space["zones"][wood["zone"]]
    x0, y0, x1, y1 = zone["rect"]
    offset = (x0 + 15000, y0 - 2500)
    def xy(p): return [p[0] + offset[0], p[1] + offset[1]]
    spline = next(s for s in layout["splines"] if s["id"] == "spl_ch01_wood_trail")
    trail = [xy(p) for p in spline["nodes_cm"]]
    # A 4 m apron includes the authored entrance/exit outside the wood bounds.
    # Runtime z remains flat until the authored slope/stream terrain is built.
    zone["rect"] = [x0-400, y0-400, x1+600, y1+400]
    zone["walls"], zone["props"], zone["cover"] = [], [], []
    wood["entry"] = [*trail[0], 45]
    wood["anchor"] = trail[0]
    wood["exit"] = {"center": trail[-1], "size": [400,400]}
    wood["cache"] = None
    wood["volumes"] = [{"event":"volume_enter:vol_ch01_wood_exit", **wood["exit"]}]
    range_zone, smithy_zone = (space["zones"][r["zone"]] for r in (range_,smithy))
    gate = [range_zone["rect"][2], 0]
    junction = [gate[0]+1200, trail[0][1]]
    arrival = smithy["entry"][:2]
    terrace_y = y0-1100
    terrace = [junction, [junction[0],terrace_y], [arrival[0]-700,terrace_y],
               [arrival[0]-700,arrival[1]],arrival]
    bridge = [trail[-1], [arrival[0]-700,trail[-1][1]], [arrival[0]-700,arrival[1]],arrival]
    # Physical door openings in the range's east and smithy's west walls.
    for z, side in ((range_zone,1),(smithy_zone,0)):
        wall=z["walls"].pop(side)
        low, high = z["rect"][1], z["rect"][3]
        for a,b in ((low,-350),(350,high)):
            z["walls"].append([wall[0],(a+b)//2,60,b-a,wall[4]])
    vista = xy(POIS[1][1:])
    target = [vista[0],vista[1]-4500,150]
    space["wood"] = {"beat":"ch01.b08", "pois":[{"id":p[0],"at":xy(p[1:])} for p in POIS],
        "approach":[gate,junction,trail[0]], "trail":trail, "terrace":terrace,"bridge":bridge,
        "entry":trail[0], "arrival":arrival, "naruko":target,"face_cm":[30,40],
        "reward":"codex_toshiya","distance_cm":4500,
        "trail_polyline_cm":round(sum(math.dist(a,b) for a,b in zip(trail,trail[1:]))),
        "provisional":"Flat collision; southward clapper azimuth and 30x40cm face; final authored terrain/art pending."}


def wood_valid(chapter):
    """Fail closed on mismatched discovery, completion and physical route data."""
    if not chapter["id"].startswith("ch01_"):
        return "wood" not in chapter["space"]
    try:
        space, beats = chapter["space"], chapter["beats"]
        w = space["wood"]
        point = lambda p, n=2: isinstance(p, list) and len(p) == n and all(type(v) is int for v in p)
        for name, count in (("approach",3),("trail",6),("terrace",5),("bridge",4)):
            if len(w[name]) != count or not all(point(p) for p in w[name]): return False
        if not all(point(w[k]) for k in ("entry","arrival","face_cm")) or not point(w["naruko"],3): return False
        if w["beat"] != "ch01.b08" or w["reward"] != "codex_toshiya" or type(w["distance_cm"]) is not int or w["distance_cm"] != 4500: return False
        if not all(0 < v <= 100 for v in w["face_cm"]): return False
        challenge = beats[7]["ext"]["challenge"]
        if type(challenge["distance_m"]) is not int or challenge != {"id":"poi_ch01_naruko","distance_m":45,"reward":"codex_toshiya"}: return False
        if beats[7]["task"]["goal"] != "exit" or beats[7]["task"]["exit_event"] != "volume_enter:vol_ch01_wood_exit": return False
        if beats[8]["requires"] != ["ch01.b07"] or not beats[7]["optional"]: return False
        if len(w["pois"]) != 4: return False
        offset = [w["entry"][0]+15200,w["entry"][1]-3000]
        for row, (name,x,y) in zip(w["pois"],POIS):
            if row["id"] != name or not point(row["at"]) or row["at"] != [x+offset[0],y+offset[1]]: return False
        bindings = {p["id"]:p.get("collectible") for p in beats[7]["params"]["pois"]}
        if bindings != {POIS[0][0]:"ch01.c01",POIS[1][0]:None,POIS[2][0]:"ch01.c02",POIS[3][0]:None,"poi_ch01_naruko":None}: return False
        spline = next(s for s in chapter["layout"]["splines"] if s["id"]=="spl_ch01_wood_trail")
        if w["trail"] != [[p[0]+offset[0],p[1]+offset[1]] for p in spline["nodes_cm"]]: return False
        vista = w["pois"][1]["at"]+[150]
        if not math.isclose(math.dist(vista,w["naruko"]),4500,abs_tol=.001): return False
        bspace = space["beats"][7]
        return (w["approach"][-1] == w["entry"] == w["trail"][0] and
                w["terrace"][0] == w["approach"][1] and w["bridge"][0] == w["trail"][-1] == bspace["exit"]["center"] and
                w["terrace"][-1] == w["bridge"][-1] == w["arrival"] == space["beats"][8]["entry"][:2] and
                bspace["cache"] is None)
    except (KeyError,TypeError,IndexError,ValueError,StopIteration):
        return False
