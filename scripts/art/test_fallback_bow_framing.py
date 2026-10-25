"""Source geometry regression for the explicitly unadmitted cube bow.

Uses the actual component declarations (100 cm engine cube, checked separately
by prepared engine bounds tests). This models volumes, not authored sockets or
rendered visibility. Native capture measures loaded mesh OBBs independently.
"""
import itertools
import math
from pathlib import Path
import re
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_viewmodel_framing import rotation, apply

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = ROOT / 'Source/SoraArena/Private/Characters/SoraViewmodelComponent.cpp'
POLICY = ROOT / 'Source/SoraArena/Private/Characters/SoraViewmodelPresentation.cpp'


def numbers(text):
    return tuple(float(x.strip()) for x in text.split(','))


def quat(angles):
    # Convert UE basis rows to a conventional column matrix, then unit WXYZ.
    rows = rotation(*angles)
    m = [[rows[j][i] for j in range(3)] for i in range(3)]
    w = math.sqrt(1 + sum(m[i][i] for i in range(3))) / 2
    return (w, (m[2][1]-m[1][2])/(4*w), (m[0][2]-m[2][0])/(4*w), (m[1][0]-m[0][1])/(4*w))


def mul(a, b):
    w,x,y,z=a; v,i,j,k=b
    return (w*v-x*i-y*j-z*k, w*i+x*v+y*k-z*j, w*j-x*k+y*v+z*i, w*k+x*j-y*i+z*v)


def rotate(q, v):
    return mul(mul(q,(0,*v)),(q[0],-q[1],-q[2],-q[3]))[1:]


def slerp(a, b, t):
    dot=sum(x*y for x,y in zip(a,b))
    if dot < 0: b=tuple(-x for x in b);dot=-dot
    if dot > .9999:
        result=tuple(x*(1-t)+y*t for x,y in zip(a,b));norm=math.sqrt(sum(x*x for x in result))
        return tuple(x/norm for x in result)
    theta=math.acos(dot)
    return tuple((x*math.sin((1-t)*theta)+y*math.sin(t*theta))/math.sin(theta) for x,y in zip(a,b))


def between(a, b):
    cross=(a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
    q=(1+sum(x*y for x,y in zip(a,b)),*cross); norm=math.sqrt(sum(x*x for x in q))
    return tuple(x/norm for x in q)


def geometry():
    source=COMPONENT.read_text()
    body=source.split('if(WeaponId==18)')[1].split('else if(WeaponId==19')[0]
    body+='\n'+next(line for line in source.splitlines() if 'Add(TEXT("FurPaw")' in line)
    pattern=r'Add\(TEXT\("(\w+)"\),FVector\(([^)]+)\),FVector\(([^)]+)\)[^\n]*'
    parts={}
    for name,location,scale in re.findall(pattern,body):
        line=next(line for line in body.splitlines() if f'TEXT("{name}")' in line)
        turn=re.search(r'SetRelativeRotation\(FRotator\(([^)]+)\)',line)
        rot=rotation(*numbers(turn[1])) if turn else rotation(0,0,0)
        points=[]
        for signs in itertools.product((-1,1),repeat=3):
            p=apply(rot,tuple(50*s*size for s,size in zip(signs,numbers(scale))))
            points.append(tuple(x+loc-pivot for x,loc,pivot in zip(p,numbers(location),(7,0,-5))))
        parts[name]=points
    if len(parts)!=7: raise AssertionError('actual proxy component inventory changed')
    return parts


def poses():
    source=POLICY.read_text().split('FPose FallbackBowPose')[1].split('float BlendAlpha')[0]
    found=re.search(r'Pose.Location=bDrawn\?FVector\(([^)]+)\):FVector\(([^)]+)\)',source)
    angles=re.search(r'Pose.Rotation=bDrawn\?FQuat::Identity:FRotator\(([^)]+)\)',source)
    return numbers(found[2]),numbers(found[1]),quat(numbers(angles[1]))


def measure(parts,anchor,q,bob=(0,0,0),first_fov=70,scale=.6):
    result={}
    tan=math.tan(math.radians(first_fov/2))
    for name,points in parts.items():
        transformed=[tuple(a+b+c for a,b,c in zip(rotate(q,p),anchor,bob)) for p in points]
        if any(p[0]<=0 for p in transformed): raise AssertionError('geometry behind camera')
        uv=[(p[1]/p[0]/tan,p[2]/p[0]/tan*16/9) for p in transformed]
        result[name]=(min(p[0]*scale for p in transformed),min(p[0] for p in uv),max(p[0] for p in uv),min(p[1] for p in uv),max(p[1] for p in uv))
    return result


class FallbackBowFraming(unittest.TestCase):
    def test_native_rotation_model_matches_basis(self):
        for angles in ((0,6,-8),(-10,0,-15),(28,0,0),(.18,.28,0)):
            self.assertLess(math.dist(rotate(quat(angles),(7,-3,11)),apply(rotation(*angles),(7,-3,11))),1e-10)

    def test_previous_authored_anchor_obstructs_the_actual_proxy(self):
        values=measure(geometry(),(60,-3,-9.5),quat((0,0,0)))
        self.assertGreater(values['YumiGrip'][2],0, 'previous anchor must reproduce the observed central obstruction')
        self.assertLess(values['FurPaw'][3],-1, 'previous paw also leaves the frame')

    def test_fixed_poses_and_blends_keep_readable_grip_and_aim_clearance(self):
        rest,drawn,rest_q=poses();parts=geometry();cases=0
        for t,draw,pitch,roll,bob in itertools.product([n/8 for n in range(9)],(False,True),(-10,0,25,28),(-15,0),((0,-.7,-.6),(0,.7,.6))):
            anchor=tuple(a*(1-t)+b*t for a,b in zip(rest,drawn))
            q=mul(quat((pitch,0,roll)),slerp(rest_q,(1,0,0,0),t))
            # Includes rest/release and immediate draw changes during a blend.
            for yaw,pitch_offset in ((0,0),(.28,.18),(-.28,-.18)) if draw else ((0,0),):
                world_ray=apply(rotation(pitch_offset,yaw,0),(1,0,0))
                factor=math.tan(math.radians(94/2))/math.tan(math.radians(70/2))
                desired=(world_ray[0],world_ray[1]/factor,world_ray[2]/factor)
                norm=math.sqrt(sum(x*x for x in desired));desired=tuple(x/norm for x in desired)
                aim=between(rotate(q,(1,0,0)),desired) if draw else (1,0,0,0)
                values=measure(parts,anchor,mul(aim,q),bob)
                center=world_ray[1]/world_ray[0]/math.tan(math.radians(94/2)) if draw else 0
                for name,(depth,x0,x1,y0,y1) in values.items():
                    self.assertGreaterEqual(depth,12,(t,draw,pitch,roll,name,'near plane'))
                    if name not in ('NockedArrow','Arrowhead'):
                        self.assertLessEqual(x1,center-.14,(t,draw,pitch,roll,name,'clearance'))
                _,x0,x1,y0,y1=values['YumiGrip']
                self.assertTrue(-.9<=x0<x1<=.9 and -.9<=y0<y1<=.9,(t,draw,pitch,roll,'grip clipped'))
                self.assertGreaterEqual(x1-x0,.07,'grip narrower than3.5%viewport')
                self.assertGreaterEqual(y1-y0,.30,'grip shorter than15%viewport')
                cases+=1
        self.assertEqual(cases,576)

    def test_source_geometry_is_preserved_and_fallback_is_separate(self):
        parts=geometry(); self.assertEqual(set(parts),{'YumiLower','YumiUpper','YumiGrip','YumiString','NockedArrow','Arrowhead','FurPaw'})
        self.assertEqual(sorted({p[2] for p in parts['YumiGrip']}),[-11,11])
        source=COMPONENT.read_text()
        self.assertIn('Part->GetStaticMesh()->GetBoundingBox()',source)
        self.assertIn('Part->GetComponentTransform().TransformPosition(Local)',source)
        self.assertIn('bFallbackBowPresentation?SoraViewmodelPresentation::FallbackBowPose(bDrawn)',source)
        self.assertNotIn('SetRelativeScale3D',source.split('void USoraViewmodelComponent::Present(')[1].split('void USoraViewmodelComponent::Sway')[0])


if __name__=='__main__': unittest.main()
