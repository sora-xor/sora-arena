"""Compiled builder solids and authored routes. Actual UE movement is separate."""
import copy
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest
import campaign_tenements as tenements
import campaign_notice_square as square

ROOT=Path(__file__).resolve().parents[2]


class TenementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chapter=json.loads((ROOT/'Content/Data/campaign/chapter_03.json').read_text())
        cls.enemies={e['id']:e for e in json.loads((ROOT/'Content/Data/enemies.json').read_text())['archetypes']}
        env=os.environ.copy();flags=[]
        compiler=shutil.which('clang++') or shutil.which('c++')
        if platform.system()=='Darwin':
            pins=json.loads((ROOT/'scripts/toolchain/versions.json').read_text())
            env['DEVELOPER_DIR']=env.get('SORA_DEVELOPER_DIR') or str(Path(pins['default_macos_xcode']).expanduser())
            compiler=subprocess.check_output(['xcrun','--find','clang++'],env=env,text=True).strip()
            sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],env=env,text=True).strip()
            flags=['-isysroot',sdk]
        if not compiler:raise RuntimeError('A C++ compiler is required')
        with tempfile.TemporaryDirectory(prefix='sora-tenements-') as directory:
            binary=Path(directory)/'tenements'
            subprocess.run([compiler,'-std=c++20','-UNDEBUG','-Wall','-Wextra','-Werror',
                '-fsanitize=undefined','-fsanitize-trap=undefined',*flags,'-I',str(ROOT/'Source/SoraArena/Public'),
                str(ROOT/'scripts/unreal/tenement_rules_driver.cpp'),'-o',str(binary)],check=True,env=env)
            cls.native=json.loads(subprocess.check_output([str(binary)],text=True,env=env))
            cls.solids=cls.native['solids']

    @staticmethod
    def hits(box,point,radius=34,height=176):
        x,y,z,sx,sy,sz,yaw,_=box
        a=math.radians(yaw);px=point[0]-x;py=point[1]-y
        dx=max(abs(px*math.cos(a)+py*math.sin(a))-sx/2,0)
        dy=max(abs(-px*math.sin(a)+py*math.cos(a))-sy/2,0)
        dz=max(z-sz/2-(point[2]+height-radius),(point[2]+radius)-(z+sz/2),0)
        return dx*dx+dy*dy+dz*dz<radius*radius-1e-6

    @staticmethod
    def sample(points,step=5):
        for a,b in zip(points,points[1:]):
            n=max(1,math.ceil(math.dist(a,b)/step))
            for i in range(n+1):yield [a[j]+(b[j]-a[j])*i/n for j in range(3)]

    def clear(self,points):
        for point in self.sample(points):
            for index,box in enumerate(self.solids):
                self.assertFalse(self.hits(box,point),(point,index,box))

    def floor_at(self,x,y):
        heights=[b[2]+b[5]/2 for b in self.solids if (b[7]==0 or b[7]==2 and b[5]<=45) and
                 abs(x-b[0])<=b[3]/2 and abs(y-b[1])<=b[4]/2]
        if -3200<=x<=3200 and -2600<=y<=2600:heights.append(0)
        return max(heights,default=None)

    def test_separate_finds_have_grounded_alley_approaches(self):
        self.assertEqual(self.native['finds'],[f['at_cm'] for f in tenements.FINDS])
        self.assertLess(self.native['finds'][0][2],100)
        self.assertGreater(math.dist(*[p[:2] for p in self.native['finds']]),280)
        for x,y,z in self.native['finds']:
            self.clear([[-2800,1250,2.15],[-2800,y,2.15]])
            self.assertLess(abs(x+2800),140)

    def test_supply_crate_is_on_ground_and_clear_of_doorway_steps(self):
        x,y,z,sx,sy,sz=self.native['supply']
        self.assertEqual(self.floor_at(x,y),z)
        self.assertTrue(-2500<=x-sx/2<x+sx/2<=-2300)
        self.assertTrue(3500<=y-sy/2<y+sy/2<=3700)
        for bx,by,bz,wx,wy,wz,yaw,_ in self.solids:
            a=math.radians(yaw)
            ex=(abs(math.cos(a))*wx+abs(math.sin(a))*wy)/2
            ey=(abs(math.sin(a))*wx+abs(math.cos(a))*wy)/2
            overlaps=(abs(x-bx)<sx/2+ex-1e-6 and abs(y-by)<sy/2+ey-1e-6 and
                      z<bz+wz/2-1e-6 and z+sz>bz-wz/2+1e-6)
            self.assertFalse(overlaps,(bx,by,bz,'supply overlaps a tenement solid'))
        crate=[x,y,z+sz/2,sx,sy,sz,0,1]
        self.clear([[-2800,3000,2.15],[-2800,3350,2.15],[-2250,3400,2.15],[-2250,3660,2.15]])
        self.assertFalse(self.hits(crate,[-2365,3660,24.65]))
        # Both authored 22.5 cm steps and the full 45 cm room remain valid
        # supply floors; an actual step-up sweep is checked only in Unreal.
        self.clear([[-2365,3660,24.65],[-2365,3660,24.65]])

    def test_rejects_swapped_combined_and_moved_finds(self):
        for mutation in ('item','point','height','reward','duplicate','extra'):
            c=copy.deepcopy(self.chapter)
            b=next(b for b in c['beats'] if b['id']=='ch03.b04')
            r=next(r for r in c['space']['beats'] if r['beat']=='ch03.b04')
            if mutation=='item':next(p for p in b['params']['pois'] if p['id']=='poi_chalk')['collectible']='ch03.c02'
            elif mutation=='point':r['tenement_finds'][0]['at_cm'][0]=-2800
            elif mutation=='height':r['tenement_finds'][0]['at_cm'][2]=165
            elif mutation=='reward':b['params']['rewards']=['ch03.c01']
            elif mutation=='duplicate':b['params']['pois'].append(copy.deepcopy(b['params']['pois'][0]))
            else:next(r for r in c['space']['beats'] if r['beat']=='ch03.b05')['tenement_finds']=copy.deepcopy(tenements.FINDS)
            self.assertFalse(tenements.tenements_valid(c),mutation)

    def test_authored_contract_and_home_dimensions(self):
        self.assertTrue(tenements.tenements_valid(self.chapter))
        faces=[b for b in self.solids if b[7]==3]
        self.assertEqual(len(faces),24)
        for b in faces:
            self.assertIn(b[4],(150,20))
            self.assertEqual(b[0]+b[3]/2 if b[0]<-2800 else b[0]-b[3]/2,
                             -2890 if b[0]<-2800 else -2710)
        floors=[b for b in self.solids if b[3:6]==[360,270,15]]
        self.assertEqual(len(floors),12)

    def test_residents_have_distinct_clear_routes_into_real_homes(self):
        routes=self.native['queue_routes']
        self.assertEqual(len(routes),6)
        self.assertEqual(len({tuple(r[-1]) for r in routes}),6)
        for queue,approach,home in routes:
            self.assertTrue(-3400<=queue[0]<=-2200 and 2220<=queue[1]<=3600)
            self.assertEqual(self.floor_at(*queue),0)
            self.assertEqual(self.floor_at(*home),15)
            self.assertEqual(approach[1],home[1])
            self.clear([queue+[2.15],approach+[2.15]])
            # Clearance while stepping onto the 15 cm room threshold. This
            # does not substitute for the runtime CharacterMovement test.
            self.clear([approach+[2.15],approach+[17.15],home+[17.15]])
            front=-2895 if home[0]<-2800 else -2705
            blocked=[front,home[1],145,10,100,290,0,3]
            self.assertTrue(self.hits(blocked,[front,home[1],17.15]))
            # Narrowing a doorway below the standing body's width fails.
            narrow=[front,home[1]+28,145,10,50,290,0,3]
            self.assertTrue(self.hits(narrow,[front,home[1],17.15]))
        for i,r in enumerate(routes):
            for other in routes[i+1:]:self.assertGreater(math.dist(r[0],other[0]),68)

    def test_open_doors_preserve_the_chalk_and_notice_backing(self):
        for x,y,z in self.native['finds']:
            front=-2895 if x<-2800 else -2705
            self.assertTrue(any(b[7]==3 and b[0]==front and
                                abs(y-b[1])<b[4]/2 and abs(z-b[2])<b[5]/2
                                for b in self.solids),(x,y,z))

    def test_grounded_entry_court_and_carry_routes(self):
        routes=[[-2800,450],[-2800,2900],[-2600,2950],[-2800,2900],[-2800,1050],[-2550,1050]]
        points=[p+[2.15] for p in routes]
        self.clear(points)
        for p in self.sample(points):self.assertEqual(self.floor_at(*p[:2]),0,p)
        self.assertLess(math.dist(routes[2],tenements.HOIST),260)
        self.assertEqual(routes[-1],tenements.HIDEOUT)

    def test_late_hub_arrivals_clear_districts_and_shared_square_solids(self):
        records=[r for r in self.chapter['space']['beats'] if r['zone']==-1]
        self.assertEqual({r['beat'] for r in records},{'ch03.b16','ch03.b18'})
        for r in records:
            for key,margin in [('entry',34),('anchor',0)]:
                x,y=r[key][:2]
                self.assertLess(abs(x)+margin,3150)
                self.assertLess(abs(y)+margin,2550)
                self.assertEqual(self.floor_at(x,y),0)
                self.clear([[x,y,2.15],[x,y,2.15]])
                for zone in self.chapter['space']['zones']:
                    if zone['place']=='pl_kosatsuba':
                        self.assertTrue(square.notice_valid(self.chapter))
                        for box in self.native['notice_solids']:
                            self.assertFalse(self.hits(box,[x,y,2.15]),(r['beat'],key,box))
                        continue
                    x0,y0,x1,y1=zone['rect']
                    self.assertFalse(x0-margin<=x<=x1+margin and y0-margin<=y<=y1+margin,
                                     (r['beat'],key,zone['id']))
            c=copy.deepcopy(self.chapter)
            next(b for b in c['space']['beats'] if b['beat']==r['beat'])['entry']=[-2700,0,0]
            self.assertFalse(tenements.tenements_valid(c),'legacy spawn overlaps tenements')

    def test_notice_ground_routes_have_connected_clear_floors(self):
        self.assertEqual(self.native['kept_houses'],[0,1,3,4])
        self.assertNotIn([-500,-680],self.native['kept_cover'])
        self.assertNotIn([-500,680],self.native['kept_cover'])
        boxes=self.solids+self.native['notice_solids']+self.native['north_walls']+self.native['street_walls']+self.native['workshop_solids']
        boxes += [[x,y,70,230,180,140,0,1] for x,y in self.native['kept_cover']]
        # The generic row's foundations are wider than its walls. The side
        # passage splits its northwest house; that house is away from these
        # street routes, so conservatively keep its full foundation here.
        boxes += [[-2000+i*1000,side*1200,24,685,735,48,0,2]
                  for side in (-1,1) for i in self.native['kept_houses']]
        boxes += [[-2000+i*1000,side*1200,(330+(i%2)*100)/2,650,700,330+(i%2)*100,0,1]
                  for side in (-1,1) for i in self.native['kept_houses']]
        floors=self.native['street_floors']+[b for b in self.native['workshop_solids'] if b[2]+b[5]/2==0]
        for route in square.ground_patrols():
            for point in self.sample([p+[2.15] for p in route+route[:1]],step=10):
                self.assertTrue(self.floor_at(*point[:2])==0 or any(
                    abs(point[0]-b[0])<=b[3]/2 and abs(point[1]-b[1])<=b[4]/2 and b[2]+b[5]/2==0
                    for b in floors),('unsupported ground route',point))
                for box in boxes:self.assertFalse(self.hits(box,point),(point,box))
        self.assertEqual((min(p[1] for p in square.P2),max(p[1] for p in square.P2)),(-2000,3800))
        # The pre-change house and solid boundary wall would fail this test.
        self.assertTrue(self.hits([0,1200,24,685,735,48,0,2],[0,1200,2.15]))
        self.assertTrue(self.hits([1130,2550,220,4140,100,540,0,1],[0,2550,2.15]))
        for point in ([0,3900,2.15],[-400,3250,2.15],[400,3250,2.15],
                      [4100,0,2.15],[3900,-400,2.15],[3650,400,2.15]):
            self.assertTrue(any(self.hits(b,point) for b in self.native['street_walls']),('open edge',point))
        # Neighbouring districts share one continuous floor, with no slab
        # overlap and no new wall across the workshop's existing side route.
        for point in self.sample([[3480,-1030,2.15],[3480,0,2.15],[4000,0,2.15]]):
            for box in boxes:self.assertFalse(self.hits(box,point),(point,box))
        self.assertTrue(self.hits([3700,-1150,100,12,2700,200,0,1],[3700,0,2.15]))
        for i,a in enumerate(floors):
            for b in floors[i+1:]:
                overlap_x=min(a[0]+a[3]/2,b[0]+b[3]/2)-max(a[0]-a[3]/2,b[0]-b[3]/2)
                overlap_y=min(a[1]+a[4]/2,b[1]+b[4]/2)-max(a[1]-a[4]/2,b[1]-b[4]/2)
                self.assertFalse(overlap_x>0 and overlap_y>0,('coplanar floor overlap',a,b))

    def test_notice_panel_and_north_escape_clear_actual_solids(self):
        self.clear([[-1000,2800,2.15],[-1000,540,2.15],[-730,548,2.15]])
        route=[[-730,548,2.15],[-1000,548,2.15],[-1000,3000,2.15],[-1600,3000,2.15]]
        self.clear(route)
        for p in self.sample(route):
            self.assertEqual(self.floor_at(*p[:2]),0,p)
            for box in self.native['notice_solids']:
                self.assertFalse(self.hits(box,p),(p,box))

    def test_full_width_alley_and_north_passage(self):
        # The capsule may run along either edge with its 34 cm radius inside
        # the specified width, rather than only on a favourable centre line.
        for x in (-2855.9,-2744.1):self.clear([[x,1250,2.15],[x,2780,2.15]])
        for x in (-1025.9,-974.1):self.clear([[x,800,2.15],[x,2850,2.15]])
        self.clear([[-2400,3000,2.15],[-1000,3000,2.15],[-1000,700,2.15],[-730,700,2.15]])

    def test_well_has_real_seven_metre_floor_and_ninety_cm_bore(self):
        self.assertEqual(self.floor_at(-3100,3200),-700)
        self.assertEqual(self.floor_at(-3030,3200),0)
        self.assertEqual(self.floor_at(-3170,3200),0)
        self.clear([[-3100,3200,-697.85],[-3100,3200,82.15]])
        # An oversized body fails: a missing or wrongly scaled wall must
        # not make the positive route test pass vacuously.
        self.assertTrue(any(self.hits(b,[-3100,3200,-400],radius=46) for b in self.solids))

    def test_rope_rises_above_curb_before_entering(self):
        self.clear([[-2800,2900,2.15],[-2970,3200,2.15],[-2970,3200,82.15],
                    [-3100,3200,82.15],[-3100,3200,-697.85]])
        direct=self.sample([[-2970,3200,2.15],[-3100,3200,2.15]])
        self.assertTrue(any(self.hits(b,p) for p in direct for b in self.solids))

    def test_manager_steps_and_collectible_approach(self):
        # Landing poses and raised-room paths; CharacterMovement's actual
        # step-up sweep is covered by the pending UE test, not this test.
        for p in ([-2460,3565,24.65],[-2460,3636,47.15]):self.clear([p,p])
        self.clear([[-2460,3636,47.15],[-2800,3850,47.15],[-3080,3910,47.15]])
        self.assertEqual(self.floor_at(-2800,3850),45)
        pick=next(p for p in self.chapter['space']['pickups'] if p['collectible']=='ch03.c05')
        self.assertEqual(pick['at']+[pick['height_cm']],[-3080,4020,125])

    def test_patrols_clear_new_solids_and_one_another(self):
        for route in tenements.PATROLS:
            points=[p+[2.15] for p in route]
            self.clear(points)
            for p in self.sample(points):self.assertEqual(self.floor_at(*p[:2]),0)
        self.assertGreater(abs(tenements.PATROLS[0][0][1]-tenements.PATROLS[1][0][1]),68)
        self.assertLess(2*3500/45,self.enemies['bound_conscript']['speed_cm_s'])

    def test_west_fence_opening_and_cookfire_hold(self):
        self.clear([[-3600,3300,2.15],[-3250,3300,2.15]])
        r=next(r for r in self.chapter['space']['beats'] if r['beat']=='ch03.b14')
        self.clear([r['anchor']+[2.15],r['anchor']+[2.15]])
        for p in tenements.FIRES:self.assertLessEqual(math.dist(r['anchor'],p),420)

    def test_rejects_moved_recovery_patrol_and_height_contracts(self):
        for key,value in [('entry',[-2800,450,0]),('recovery',[-3000,3200]),
                          ('pickups',[[-2600,3260]]),('dropoffs',[[-2550,900]]),
                          ('patrols',[[[-4500,0],[-1000,0]]])]:
            with self.subTest(key=key):
                c=copy.deepcopy(self.chapter)
                next(r for r in c['space']['beats'] if r['beat']=='ch03.b05')[key]=value
                self.assertFalse(tenements.tenements_valid(c))
        for item,height in [('ch03.c03',0),('ch03.c05',0)]:
            c=copy.deepcopy(self.chapter)
            next(p for p in c['space']['pickups'] if p['collectible']==item)['height_cm']=height
            self.assertFalse(tenements.tenements_valid(c))

    def test_defense_group_spawns_are_named_separated_and_at_authored_height(self):
        rows=self.native['defense_spawns']
        self.assertEqual(len(rows),8)
        self.assertEqual([r[3:] for r in rows if r[0]==0],
                         [[-2800,y,90.15] for y in (450,570,690,810)])
        self.assertEqual([r[3:] for r in rows if r[0]==1],
                         [[-3500,3600,600],[-3500,3400,600]])
        self.assertEqual([r[3:] for r in rows if r[0]==2],[[-2800,450,90.15],[-2800,570,90.15]])
        for row in rows:
            wave,_,_,x,y,z=row;radius=38 if wave==1 else 34;height=76 if wave==1 else 176
            for box in self.solids:self.assertFalse(self.hits(box,[x,y,z-height/2],radius,height),(row,box))
            for other in rows:
                if other!=row and other[0]==wave:self.assertGreater(math.dist(row[3:],other[3:]),radius*2)

    def test_both_drone_ingresses_clear_fence_and_roofs_at_six_metres(self):
        self.assertEqual([[p[2:] for p in self.native['defense_flight'] if p[0]==i] for i in range(2)],
                         tenements.DEFENSE['flight_cm'])
        for i in range(2):
            start=next(p[3:] for p in self.native['defense_spawns'] if p[:3]==[1,0,i])
            route=[start]+[p[2:] for p in self.native['defense_flight'] if p[0]==i]
            for point in self.sample(route):
                self.assertEqual(point[2],600)
                for box in self.solids:self.assertFalse(self.hits(box,[*point[:2],point[2]-38],38,76),(point,box))

    def test_defense_wave_and_volume_mutations_fail_closed(self):
        for key,value in [('hold_cm',[-3400,2220,0,-2200,3600,0]),('air_cm',[-3500,3600,120]),
                          ('street_spacing_cm',0),('flight_cm',[[[-3300,3350,0]],[]])]:
            c=copy.deepcopy(self.chapter)
            next(r for r in c['space']['beats'] if r['beat']=='ch03.b14')['tenement_defense'][key]=value
            self.assertFalse(tenements.tenements_valid(c),key)
        for change in ('spawn','kind','count','trigger','lethal'):
            c=copy.deepcopy(self.chapter);b=next(b for b in c['beats'] if b['id']=='ch03.b14')
            if change=='spawn':b['params']['waves'][1]['enemies'][0]['spawn']='sp_b14_alley_mouth'
            elif change=='kind':b['params']['waves'][1]['enemies'][0]['type']='enforcer_rifle'
            elif change=='count':b['params']['waves'][1]['enemies'][0]['count']=3
            elif change=='trigger':b['task']['waves'][1]['value']=500
            else:b['task']['waves'][0]['members'][1]['lethal']=True
            self.assertFalse(tenements.tenements_valid(c),change)


if __name__=='__main__':unittest.main()
