"""Record-time scripted players and scenarios for the practice-abi4 fixture.

Only `verify_parity.py --record-reference` runs these players. Each tick they
read the real kernel through the C ABI and choose ordinary canonical inputs,
and the fixture stores those bytes. Verification replays the stored bytes and
never runs this code, so its floating-point aim and navigation cannot affect
parity. These are fixture authors, not the shipped practice bots, and they
make no balance claim.
"""
from collections import OrderedDict, deque
import ctypes
import math
import struct

import kernel_abi as abi

WIRE=struct.Struct('<HbbHh')
FIRE,MELEE,BLOCK,JUMP,ABILITY,RELOAD,LOADOUT=1,2,4,8,16,32,64
FFA,CONTROL,PAYLOAD,MELEE_MODE=0,1,2,3
CELL=500

def crosses(ax,ay,bx,by,box):
    """Whether segment a-b meets the closed 2D box (min_x, min_y, max_x, max_y)."""
    low,high=0.0,1.0;dx,dy=bx-ax,by-ay
    for p,q in ((-dx,ax-box[0]),(dx,box[2]-ax),(-dy,ay-box[1]),(dy,box[3]-ay)):
        if p==0:
            if q<0:return False
            continue
        t=q/p
        if p<0:low=max(low,t)
        else:high=min(high,t)
        if low>high:return False
    return True

class Navigator:
    """A 500 mm walk grid around one arena's static walls with cached BFS fields."""
    def __init__(self,lib,map_id):
        info=abi.MapInfo();assert lib.arena_map_info(map_id,ctypes.byref(info))==0
        self.info=info;self.walls=[]
        for index in range(info.wall_count):
            wall=abi.MapWall();assert lib.arena_map_wall(map_id,index,ctypes.byref(wall))==0
            self.walls.append((wall.min_x,wall.min_y,wall.max_x,wall.max_y))
        clearance=info.player_radius+150
        self.solid=[(a-clearance,b-clearance,c+clearance,d+clearance) for a,b,c,d in self.walls]
        self.sight=[(a-20,b-20,c+20,d+20) for a,b,c,d in self.walls]
        self.nx=(info.max_x-info.min_x)//CELL;self.ny=(info.max_y-info.min_y)//CELL
        inner=info.player_radius+100
        def free(i,j):
            x,y=self.centre((i,j))
            return (info.min_x+inner<=x<=info.max_x-inner and info.min_y+inner<=y<=info.max_y-inner
                    and not any(a<=x<=c and b<=y<=d for a,b,c,d in self.solid))
        self.free={(i,j) for i in range(self.nx) for j in range(self.ny) if free(i,j)}
        self.fields=OrderedDict()
    def centre(self,cell):
        return (self.info.min_x+(cell[0]+.5)*CELL,self.info.min_y+(cell[1]+.5)*CELL)
    def cell(self,x,y):
        return (min(max(int((x-self.info.min_x)//CELL),0),self.nx-1),min(max(int((y-self.info.min_y)//CELL),0),self.ny-1))
    def neighbours(self,cell):
        i,j=cell
        for di in (-1,0,1):
            for dj in (-1,0,1):
                other=(i+di,j+dj)
                # Diagonal steps may not cut a blocked corner.
                if (di or dj) and other in self.free and (not di or not dj or ((i+di,j) in self.free and (i,j+dj) in self.free)):
                    yield other
    def nearest_free(self,cell):
        return min(self.free,key=lambda other:(abs(other[0]-cell[0])+abs(other[1]-cell[1]),other))
    def field(self,goal):
        key=self.cell(*goal)
        if key in self.fields:
            self.fields.move_to_end(key);return self.fields[key]
        start=key if key in self.free else self.nearest_free(key)
        distance={start:0};queue=deque([start])
        while queue:
            here=queue.popleft()
            for other in self.neighbours(here):
                if other not in distance:
                    distance[other]=distance[here]+1;queue.append(other)
        self.fields[key]=distance
        if len(self.fields)>512:self.fields.popitem(last=False)
        return distance
    def walkable(self,ax,ay,bx,by):
        return not any(crosses(ax,ay,bx,by,box) for box in self.solid)
    def visible(self,ax,ay,bx,by):
        return not any(crosses(ax,ay,bx,by,box) for box in self.sight)
    def heading(self,x,y,gx,gy):
        """World angle for walking from (x, y) toward (gx, gy) around the walls."""
        if self.walkable(x,y,gx,gy):return math.atan2(gy-y,gx-x)
        # Distance fields are cached per 1500 mm goal square; the direct walk
        # above takes over near the goal.
        snap=(gx//1500*1500+750,gy//1500*1500+750)
        distance=self.field(snap);here=self.cell(x,y)
        if here not in distance:
            # Hugging a wall: walk to the nearest reachable cell centre.
            best=min(distance,key=lambda cell:((self.centre(cell)[0]-x)**2+(self.centre(cell)[1]-y)**2,cell))
            cx,cy=self.centre(best);return math.atan2(cy-y,cx-x)
        # Follow the descent, then steer at the farthest cell still in sight.
        path=[here]
        for _ in range(8):
            options=[(distance[other],other) for other in self.neighbours(path[-1]) if other in distance]
            if not options:break
            step=min(options)
            if step[0]>=distance[path[-1]]:break
            path.append(step[1])
        target=path[-1] if len(path)>1 else here
        for cell in reversed(path[1:]):
            cx,cy=self.centre(cell)
            if self.walkable(x,y,cx,cy):target=cell;break
        cx,cy=self.centre(target);return math.atan2(cy-y,cx-x)

def route_point(route,distance):
    """The floor point `distance` mm along an axis-aligned route, as in maps.rs."""
    left=max(distance,0)
    for (x0,y0),(x1,y1) in zip(route,route[1:]):
        length=abs(x1-x0)+abs(y1-y0)
        if left<=length:
            return (x0+((x1>x0)-(x1<x0))*left,y0+((y1>y0)-(y1<y0))*left)
        left-=length
    return route[-1]

class Scenario:
    """One recorded case: configuration, roster and each slot's plan."""
    def __init__(self,case_id,mode,map_id,max_ticks,roster,base_bond=0,plan=None,loadouts=True):
        self.id=case_id;self.mode=mode;self.map_id=map_id;self.max_ticks=max_ticks
        self.base_bond=base_bond;self.plan=plan or fight;self.loadouts=loadouts
        self.participants=[]
        for slot,(team,class_id,weapon_id,entitled) in enumerate(roster):
            bond=0 if not base_bond else base_bond*(2 if weapon_id>=12 and not entitled else 1)
            self.participants.append({'slot':slot,'team':team,'class_id':class_id,'weapon_id':weapon_id,
                                      'bond':bond,'special_entitled':int(entitled),'reserved':0})
    def config(self):
        return {'abi_version':abi.ABI_VERSION,'mode':self.mode,'map_id':self.map_id,'max_ticks':self.max_ticks,
                'base_bond':self.base_bond,'player_count':len(self.participants),'offline':0 if self.base_bond else 1}

def fight(match,tick,slot):
    """Default plan: fight toward the mode's objective, or the nearest enemy."""
    return 'fight',match.objective_goal(slot)

class Match:
    """One scripted recording on its own kernel handle."""
    def __init__(self,lib,scenario,navigator):
        self.lib=lib;self.scenario=scenario;self.nav=navigator;self.info=navigator.info
        self.route=[]
        for index in range(self.info.route_point_count):
            point=abi.MapPoint();assert lib.arena_map_route_point(scenario.map_id,index,ctypes.byref(point))==0
            self.route.append((point.x,point.y))
        self.hazards=[]
        for index in range(self.info.hazard_count):
            hazard=abi.MapHazard();assert lib.arena_map_hazard(scenario.map_id,index,ctypes.byref(hazard))==0
            self.hazards.append(((hazard.min_x+hazard.max_x)//2,(hazard.min_y+hazard.max_y)//2))
        self.weapons=[]
        for weapon_id in range(18):
            spec=abi.Weapon();assert lib.arena_weapon_spec(weapon_id,ctypes.byref(spec))==0;self.weapons.append(spec)
        self.count=len(scenario.participants);self.requested={}
    def enemy(self,a,b):
        return a!=b and (self.scenario.mode not in (CONTROL,PAYLOAD) or self.players[a].team!=self.players[b].team)
    def objective_goal(self,slot):
        mode=self.scenario.mode;team=self.players[slot].team
        if mode==CONTROL:return (self.info.control_x,self.info.control_y)
        if mode==PAYLOAD:
            ahead=self.objective.payload_progress+(1200 if team==0 else 0)
            return route_point(self.route,min(ahead,self.info.route_length))
        return None
    def read(self):
        lib=self.lib;handle=self.handle
        self.players=[];self.visuals=[]
        for slot in range(self.count):
            player=abi.Player();visual=abi.Presentation()
            assert lib.arena_player(handle,slot,ctypes.byref(player))==0
            assert lib.arena_player_presentation(handle,slot,ctypes.byref(visual))==0
            self.players.append(player);self.visuals.append(visual)
        self.objective=abi.Objective();assert lib.arena_objective(handle,ctypes.byref(self.objective))==0
        count=ctypes.c_uint32();assert lib.arena_entity_count(handle,ctypes.byref(count))==0
        self.entities=[]
        for index in range(count.value):
            entity=abi.Entity();assert lib.arena_entity(handle,index,ctypes.byref(entity))==0;self.entities.append(entity)
    def aim(self,p,x,y,z):
        yaw=round(math.atan2(y-p.y,x-p.x)*65536/(2*math.pi))&65535
        pitch=round(math.atan2(z-(p.z+self.info.eye_height),max(math.hypot(x-p.x,y-p.y),1))*32768/math.pi)
        return yaw,max(-16384,min(16384,pitch))
    def loadout(self,slot,player,visual):
        # Rotate through the classes; alternate ranged and melee; take the
        # admitted special when it belongs to the new class. Melee mode keeps
        # melee weapons (the naginata is the only melee special).
        class_id=(player.class_id+1)%6;deaths=player.deaths
        if self.scenario.mode==MELEE_MODE:
            return class_id,(2 if visual.admitted_special==12 and class_id==0 else 1)
        if visual.admitted_special==12+class_id:return class_id,2
        return class_id,deaths%2
    def decide(self,tick,slot):
        p=self.players[slot];v=self.visuals[slot]
        if not p.alive:
            if p.exhausted or not self.scenario.loadouts or self.requested.get(slot)==p.deaths:
                return (0,0,0,0,0)
            self.requested[slot]=p.deaths
            class_id,index=self.loadout(slot,p,v)
            return (LOADOUT,class_id,index,0,0)
        role,goal=self.scenario.plan(self,tick,slot)
        self.repair_target=None
        spec=self.weapons[p.weapon_id];melee=self.weapons[2*p.class_id]
        # The nearest visible enemy, else the nearest enemy.
        enemies=sorted((math.hypot(q.x-p.x,q.y-p.y),other) for other,q in enumerate(self.players)
                       if q.alive and self.enemy(slot,other))
        target=(enemies[0][1],enemies[0][0],False) if enemies else None
        for distance,other in enemies:
            q=self.players[other]
            if self.nav.visible(p.x,p.y,q.x,q.y):target=(other,distance,True);break
        heal=None
        if p.weapon_id==17 and self.scenario.mode in (CONTROL,PAYLOAD):
            for other,q in enumerate(self.players):
                if other!=slot and q.alive and q.team==p.team and q.health<self.visuals[other].max_health:
                    distance=math.hypot(q.x-p.x,q.y-p.y)
                    if distance<spec.range_mm-500 and self.nav.visible(p.x,p.y,q.x,q.y):heal=(other,distance);break
        buttons=0;yaw=v.yaw;pitch=0;heading=None
        if goal is None and target and role!='hold':goal=(self.players[target[0]].x,self.players[target[0]].y)
        if goal is not None and math.hypot(goal[0]-p.x,goal[1]-p.y)>(250 if role=='hold' else 600):
            heading=self.nav.heading(p.x,p.y,goal[0],goal[1])
        engaged=role=='fight' and target and target[2] and target[1]<max(spec.range_mm,melee.range_mm)
        if heal:
            q=self.players[heal[0]];yaw,pitch=self.aim(p,q.x,q.y,q.z+900);buttons|=FIRE
        elif engaged:
            q=self.players[target[0]];yaw,pitch=self.aim(p,q.x,q.y,q.z+900);distance=target[1]
            reach=spec.range_mm-300
            if spec.kind==2:reach=min(reach,20000)
            safe=spec.kind!=2 or distance>max(spec.arming_mm,spec.blast_mm)+400
            if distance<=reach and safe:buttons|=FIRE
            if distance<=melee.range_mm-200 and not (spec.kind==0 and buttons&FIRE):buttons|=MELEE
            if distance<5000 and (tick//15+slot)%9==0 and not buttons&FIRE:buttons|=BLOCK
            close=spec.kind==0 or (buttons&MELEE)
            # Engaged players strafe; melee fighters close in first.
            if close and distance>1100:heading=math.atan2(q.y-p.y,q.x-p.x)
            elif goal is None or math.hypot(goal[0]-p.x,goal[1]-p.y)<2500 or self.scenario.mode==FFA or self.scenario.mode==MELEE_MODE:
                side=1 if (tick//80+slot)%2 else -1
                heading=math.atan2(q.y-p.y,q.x-p.x)+side*math.pi/2
            if v.ability_cooldown_ticks==0 and (tick+slot)%20==0 and self.ability_useful(slot,distance):buttons|=ABILITY
        elif heading is not None:
            yaw=round(heading*65536/(2*math.pi))&65535
        if role=='fight':
            if p.class_id==4 and not engaged:buttons|=self.repair(slot,p)
            if p.class_id==5 and v.ability_cooldown_ticks==0 and p.health<v.max_health-40:buttons|=ABILITY
            if v.magazine and not v.ammo and not v.reload_ticks and not buttons&(FIRE|MELEE|BLOCK):buttons|=RELOAD
            if (tick+37*slot)%311==0:buttons|=JUMP
        else:
            buttons=0
        if self.repair_target is not None and buttons&MELEE and not engaged:
            yaw,pitch=self.repair_target;self.repair_target=None
        move_x=move_y=0
        if heading is not None:
            turn=heading-yaw*2*math.pi/65536
            move_x=max(-127,min(127,round(127*math.cos(turn))));move_y=max(-127,min(127,round(127*math.sin(turn))))
        return (buttons,move_x,move_y,yaw,pitch)
    repair_target=None
    def repair(self,slot,p):
        # A Karakuri strikes its own damaged barricade with the forge hammer.
        for e in self.entities:
            if e.kind==2 and e.owner_slot==slot and e.health<e.max_health:
                distance=math.hypot(e.x-p.x,e.y-p.y)
                if distance<1600:
                    self.repair_target=self.aim(p,e.x,e.y,1000);return MELEE
        return 0
    def ability_useful(self,slot,distance):
        return distance<{0:2500,1:6000,2:40000,3:8500,4:12000,5:8000}[self.players[slot].class_id]
    def record(self):
        """Play to the terminal tick and return the canonical control bytes."""
        lib=self.lib;scenario=self.scenario
        people=(abi.Participant*self.count)(*(abi.Participant(**p) for p in scenario.participants))
        config=abi.Config(**scenario.config())
        self.handle=lib.arena_create(ctypes.byref(config),people,self.count)
        assert self.handle,scenario.id+': fixture admission failed'
        data=bytearray()
        try:
            for tick in range(scenario.max_ticks):
                self.read()
                frame=(abi.Input*self.count)()
                for slot in range(self.count):
                    buttons,move_x,move_y,yaw,pitch=self.decide(tick,slot)
                    data.extend(WIRE.pack(buttons,move_x,move_y,yaw,pitch))
                    frame[slot]=abi.Input(slot,buttons,move_x,move_y,yaw,pitch)
                assert lib.arena_step(self.handle,frame,self.count)==0,f'{scenario.id}: step {tick} rejected'
                state=abi.Snapshot();assert lib.arena_snapshot(self.handle,ctypes.byref(state))==0
                if state.terminal:return bytes(data),tick+1
            raise AssertionError(scenario.id+': did not terminate')
        finally:
            lib.arena_destroy(self.handle)

def record(lib,scenario,navigators):
    if scenario.map_id not in navigators:navigators[scenario.map_id]=Navigator(lib,scenario.map_id)
    return Match(lib,scenario,navigators[scenario.map_id]).record()

# Rosters are (team, class, weapon, special_entitled). Teams alternate by slot
# so each team holds ranks 0-5 in team modes.
FFA8=[(0,0,12,True),(1,1,3,False),(0,2,5,False),(1,3,6,False),(0,4,9,False),(1,5,17,True),(0,0,0,False),(1,3,15,True)]
MELEE8=[(0,0,0,False),(1,1,2,False),(0,2,4,False),(1,3,6,False),(0,4,8,False),(1,5,10,False),(0,0,12,True),(1,4,8,False)]
TEAM12=[(0,0,1,False),(1,3,7,False),(0,1,3,False),(1,1,13,True),(0,2,5,False),(1,4,8,False),
        (0,3,15,True),(1,5,11,False),(0,4,9,False),(1,0,0,False),(0,5,17,True),(1,2,14,False)]
MAPS=['estate','lantern','foundry','citadel']

def overtime_plan(match,tick,slot):
    # Team 0 takes and holds the point without attacking until overtime.
    # Team 1 waits at home, then walks onto the point to contest it and never
    # fights back, so team 0's score reaches the target while contested.
    point=(match.info.control_x,match.info.control_y)
    if match.players[slot].team==0:
        return ('fight' if match.objective.overtime else 'passive'),point
    if tick<11_000:return 'hold',None
    return 'passive',point

def escort_plan(match,tick,slot):
    # Passive defenders wait at far FFA corners while the attackers escort
    # the payload to the end of the route.
    if match.players[slot].team==0:return fight(match,tick,slot)
    # Nyaagyu Estate FFA spawns 1, 3 and 11: open floor, far from the route.
    return 'hold',[(18500,12500),(18500,-12500),(11000,13500)][slot//2]

def hazard_plan(match,tick,slot):
    # The last slot stands in the first hazard and never fights; the others
    # fight, so its deaths are both unassisted and enemy-credited.
    if slot==match.count-1:return 'hold',match.hazards[0]
    return fight(match,tick,slot)

def duel_plan(match,tick,slot):
    # Slot 1 walks at slot 0 and never strikes back, until its reserve is gone.
    if slot==0:return fight(match,tick,slot)
    other=match.players[0]
    return 'passive',(other.x,other.y)

SCENARIOS=(
    [Scenario(f'ffa8-{MAPS[m]}',FFA,m,1800,FFA8) for m in range(4)]
    +[Scenario(f'melee8-{MAPS[m]}',MELEE_MODE,m,1200,MELEE8) for m in range(4)]
    +[Scenario(f'control12-{MAPS[m]}',CONTROL,m,1800,TEAM12) for m in range(4)]
    +[Scenario(f'payload12-{MAPS[m]}',PAYLOAD,m,1800,TEAM12) for m in range(4)]
    +[Scenario('control4-overtime-estate',CONTROL,0,12_600,[(0,0,1,False),(1,5,11,False),(0,2,5,False),(1,0,0,False)],plan=overtime_plan,loadouts=False),
      Scenario('payload6-escort-estate',PAYLOAD,0,7200,[(0,0,1,False),(1,1,3,False),(0,3,7,False),(1,2,5,False),(0,5,11,False),(1,4,9,False)],plan=escort_plan,loadouts=False),
      Scenario('staked-ffa8-lantern',FFA,1,2400,[(0,0,12,False),(1,1,3,False),(0,2,14,True),(1,3,7,False),(0,4,9,False),(1,5,17,False),(0,0,1,False),(1,4,16,True)],base_bond=1000,plan=hazard_plan),
      Scenario('staked-control12-citadel',CONTROL,3,1800,TEAM12,base_bond=1000),
      Scenario('staked-melee2-foundry',MELEE_MODE,2,36_000,[(0,0,0,False),(1,3,6,False)],base_bond=1000,plan=duel_plan)]
)
