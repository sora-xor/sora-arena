"""V5 adult-cat facial-form study, edited from the pinned project-owned V4.

The CC BY real-cat scans named in README are visual anatomy references only:
this script neither reads them nor transfers their vertices or textures.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
V4=ROOT.parent/"NyaakotoHeadV4"
BASE=V4/"Nyaakoto_HeadAnatomy_V4_Study.blend"
PIN="3962b343f35e55c61f387c14ad0ab21468a88d2849e2772225ecc83145a85021"
assert hashlib.sha256(BASE.read_bytes()).hexdigest()==PIN,"V4 source changed"
bpy.ops.wm.open_mainfile(filepath=str(BASE))
scene=bpy.context.scene


def smooth(a,b,v):
    t=max(0.,min(1.,(v-a)/(b-a)))
    return t*t*(3-2*t)


def gauss(v,c,r):
    return math.exp(-((v-c)/r)**2)


def sculpt(p):
    x,y,z=p
    side=1 if y>=0 else -1
    ay=abs(y)
    # Shorten the round occipital hemisphere; adult domestic cats have a
    # flatter head-to-neck slope than the V4 toy-like spherical profile.
    rear=(1-smooth(-.055,.055,x))*smooth(1.56,1.66,z)
    x+=.021*rear
    crown=smooth(1.66,1.748,z)
    z-=.011*crown
    # Moderate global width, concentrated above the jaw.
    cranial=smooth(1.55,1.65,z)
    y*=1-.105*cranial
    ay=abs(y)
    # Pull the inflated V4 zygomatic lobes into the cheek-to-jaw plane.
    cheek=gauss(x,.085,.080)*gauss(ay,.090,.044)*gauss(z,1.616,.042)
    y-=side*.024*cheek
    x-=.006*cheek
    # The most important visible correction: the V4 forehead-to-nasal bridge
    # was an oversized forward bulb (215 mm at midline). Give it a shallow
    # continuous dorsum tapering toward the small nose and lower muzzle.
    bridge=gauss(y,0,.037)*gauss(z,1.667,.044)*smooth(.120,.198,x)
    x-=.043*bridge
    whisker_pad=smooth(.152,.195,x)*gauss(z,1.585,.041)
    x-=.010*whisker_pad
    y*=1-.035*whisker_pad
    # A compact muscular neck anchor rather than a long pointed bust.
    neck=1-smooth(1.49,1.565,z)
    z+=.022*neck
    x+=.008*neck
    y*=1-.060*neck
    return Vector((x,y,z))


def transform_mesh(ob):
    inv=ob.matrix_world.inverted()
    for v in ob.data.vertices:
        v.co=inv@sculpt(ob.matrix_world@v.co)
    ob.data.update()


for ob in tuple(bpy.data.objects):
    if ob.name.startswith("Ear_CuppedThick_V4_"):
        bpy.data.objects.remove(ob,do_unlink=True)
for ob in bpy.data.objects:
    if ob.type=="MESH":
        transform_mesh(ob)
    elif ob.type=="CURVE" and ob.name.startswith(("Groom_Nyaakoto_","Vibrissae_Curved")):
        for spline in ob.data.splines:
            if spline.type=="BEZIER":
                for point in spline.bezier_points:
                    point.co=sculpt(point.co)
                    point.handle_left=sculpt(point.handle_left)
                    point.handle_right=sculpt(point.handle_right)
            else:
                for point in spline.points:
                    q=sculpt(Vector(point.co[:3]))
                    point.co=(*q,1)

head=bpy.data.objects["SM_Nyaakoto_HeadAnatomy_V4_Study"]
head.name="SM_Nyaakoto_AdultCatHead_V5_Study"
head["source_only"] = True
head["form_source"] = "Pinned project-owned V4; real-cat scans consulted visually only"

# Increase the forehead tabby character on the *front-facing shell* only. Use
# the existing UV-preserving CoatMix attribute, not a floating decal.
front={}
for v in head.data.vertices:
    p=v.co
    if 1.68<=p.z<=1.75 and abs(p.y)<.075:
        key=(round(p.y/.006),round(p.z/.006))
        front[key]=max(front.get(key,-10),p.x)
coatmix=head.data.color_attributes["CoatMix"]
for loop in head.data.loops:
    p=head.data.vertices[loop.vertex_index].co
    if not (1.688<=p.z<=1.747 and abs(p.y)<.069): continue
    key=(round(p.y/.006),round(p.z/.006))
    if p.x<front.get(key,p.x)-.005: continue
    t=(p.z-1.688)/.059
    band=0.
    for sign in (-1,0,1):
        yc=sign*(.023+.012*(1-t)) if sign else .004*math.sin(t*math.pi*2)
        band=max(band,gauss(p.y,yc,.0055)*smooth(0,.13,t)*(1-smooth(.82,1,t)))
    current=list(coatmix.data[loop.index].color)
    current[1]=max(current[1],.88*band)
    coatmix.data[loop.index].color=current

material=head.data.materials[0]
color=material.node_tree.nodes["UniqueUV_Albedo"]
image=bpy.data.images.load(str(ROOT/"T_Nyaakoto_HeadV5_Albedo.png"),check_existing=False)
image.pack();color.image=image
stripe=next(n for n in material.node_tree.nodes if n.type=="MATH" and n.operation=="MULTIPLY")
stripe.inputs[1].default_value=.95
material.name="M_Nyaakoto_V5_UniqueUV_Coat"

# Keep the eyes feline: minimal visible sclera, a higher iris-to-aperture ratio,
# and slimmer matte lids. This remains a rigid source study, not a facial rig.
for side in (-1,1):
    eye=bpy.data.objects.get(f"Eye_globe_{side}")
    if eye:
        p=eye.data.materials[0].node_tree.nodes.get("Principled BSDF")
        p.inputs["Base Color"].default_value=(.105,.11,.12,1)
        p.inputs["Roughness"].default_value=.24
    iris=bpy.data.objects.get(f"Iris_UV0_{side}")
    if iris:
        cy=side*.055
        for v in iris.data.vertices:
            q=iris.matrix_world@v.co
            q.y=cy+(q.y-cy)*1.10
            q.z=1.665+(q.z-1.665)*1.12
            v.co=iris.matrix_world.inverted()@q
        iris.data.update()
    for prefix in ("Upper_TarsalMargin_","Lower_TarsalMargin_"):
        ob=bpy.data.objects.get(f"{prefix}{side}")
        if not ob: continue
        center=Vector((.125,side*.056,1.667))
        inv=ob.matrix_world.inverted()
        for v in ob.data.vertices:
            q=ob.matrix_world@v.co
            q=center+Vector((((q.x-center.x)*.93)-.002,(q.y-center.y)*.94,(q.z-center.z)*.78))
            v.co=inv@q
        ob.data.update()


def mat(name,outer,inner):
    m=bpy.data.materials.new(name);m.use_nodes=True
    n=m.node_tree.nodes;links=m.node_tree.links
    bsdf=n.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value=.86
    bsdf.inputs["Metallic"].default_value=0
    bsdf.inputs["Subsurface Weight"].default_value=.08
    attr=n.new("ShaderNodeAttribute");attr.attribute_name="EarSkinMix"
    mix=n.new("ShaderNodeMixRGB")
    mix.inputs[1].default_value=outer;mix.inputs[2].default_value=inner
    links.new(attr.outputs["Fac"],mix.inputs[0])
    links.new(mix.outputs[0],bsdf.inputs["Base Color"])
    return m

earmat=mat("M_V5_Auricle_OuterFur_InnerSkin",(.105,.108,.11,1),(.19,.09,.083,1))
for side in (-1,1):
    nr,nc=30,32
    verts=[];uv=[];faces=[]
    for layer in range(2):
        for j in range(nr+1):
            t=j/nr
            half=.036*(1-t)**.85+.0003
            center_y=side*(.066+.015*t)
            z=1.654+.132*t
            cx=-.006-.022*t+.003*math.sin(math.pi*t)
            thick=.017*(1-t)**.82+.0004
            for i in range(nc+1):
                u=2*i/nc-1
                cup=math.sin(math.pi*t)
                frontx=cx+thick*.55+.008*abs(u)**1.6*cup-.006*(1-u*u)*cup
                backx=cx-thick*.55-.002*(1-u*u)*cup
                verts.append((frontx if layer==0 else backx,center_y+side*u*half,z))
                uv.append((i/nc,t))
    stride=nc+1;sheet=(nr+1)*stride
    for layer in range(2):
        for j in range(nr):
            for i in range(nc):
                a=layer*sheet+j*stride+i
                q=(a,a+1,a+stride+1,a+stride)
                faces.append(q if layer==0 else q[::-1])
    for j in range(nr):
        for i in (0,nc):
            a=j*stride+i;faces.append((a,a+stride,a+stride+sheet,a+sheet))
    for i in range(nc):
        faces.append((i,i+sheet,i+sheet+1,i+1))
        a=nr*stride+i;faces.append((a,a+1,a+sheet+1,a+sheet))
    mesh=bpy.data.meshes.new(f"Ear_AnatomyV5_{side}")
    mesh.from_pydata(verts,[],faces);mesh.update()
    ob=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(ob)
    ob["source_only"] = True
    mesh.materials.append(earmat)
    layer=mesh.uv_layers.new(name="UVMap")
    for face in mesh.polygons:
        face.use_smooth=True
        for li in face.loop_indices:
            layer.data[li].uv=uv[mesh.loops[li].vertex_index]
    attr=mesh.color_attributes.new(name="EarSkinMix",type="FLOAT_COLOR",domain="CORNER")
    for loop in mesh.loops:
        idx=loop.vertex_index
        if idx>=sheet: f=0
        else:
            j,i=divmod(idx,stride);t=j/nr;u=abs(2*i/nc-1)
            f=.78*(1-smooth(.25,.72,u))*smooth(.22,.42,t)*(1-smooth(.83,1,t))
        attr.data[loop.index].color=(f,f,f,1)

scene.render.engine="CYCLES";scene.cycles.samples=48
scene.render.resolution_x=1152;scene.render.resolution_y=1152
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.world.color=(.15,.15,.15)
scene.view_settings.view_transform="AgX"
scene.view_settings.look="AgX - Medium High Contrast"
scene.view_settings.exposure=-.23
cam=bpy.data.objects["Portrait_85mm"];cam.data.ortho_scale=.42
for label,loc in (("Front",(.70,0,1.675)),("ThreeQuarter",(.52,-.45,1.705)),("Profile",(.025,-.74,1.675))):
    cam.location=loc
    cam.rotation_euler=(Vector((.074,0,1.684))-cam.location).to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=str(ROOT/f"Nyaakoto_HeadV5_{label}.png")
    bpy.ops.render.render(write_still=True)

meshes=[o for o in scene.objects if o.type=="MESH"]
bpy.ops.object.select_all(action="DESELECT")
for ob in meshes:ob.select_set(True)
bpy.context.view_layer.objects.active=head
bpy.ops.export_scene.fbx(filepath=str(ROOT/"SM_Nyaakoto_AdultCatHead_V5_Study.fbx"),
    use_selection=True,object_types={"MESH"},apply_unit_scale=True,
    add_leaf_bones=False,path_mode="STRIP",embed_textures=False,
    use_mesh_modifiers=True,mesh_smooth_type="FACE")
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"Nyaakoto_AdultCatHead_V5_Study.blend"))

manifest={
 "schema_version":1,
 "identity":"Nyaakoto / ニャーコト V5 adult domestic-cat anatomical source study",
 "production_status":"SOURCE_REVIEW_ONLY; no runtime integration, rig, or photoreal qualification",
 "base_v4_blend_sha256":PIN,
 "user_reference_sha256":"c9f7a4bbe6ba529b2bbdb629db3ba09858c11b563c334e31593876455a550801",
 "real_cat_reference":"Neo_minigan / Cat (Take 2), CC BY 4.0; visually consulted only; no source mesh/texture included or read by generator",
 "real_cat_reference_url":"https://sketchfab.com/3d-models/cat-take-2-2996f59c517245aa91cf513a5624935e",
 "real_cat_reference_glb_sha256":"b2c2cad76dbad62d3eb41c99a20292de31f5b55163eb6d7ca84c11b7dccb444c",
 "texture_provenance":"Project-owned V4 atlas graded; original V4 artist-derived normal and ORM packed into blend, reused for FBX companion maps",
 "units":"meters; +X face forward; +Z up",
 "files_sha256":{},
}
for p in sorted(ROOT.iterdir()):
    if p.is_file() and p.name not in ("manifest.json","create_head_v5.py","create_head_v5_maps.py","validate_head_v5.py","README.md"):
        manifest["files_sha256"][p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
(ROOT/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
print("NYAAKOTO_HEAD_V5_COMPLETE",len(meshes),"meshes",len(head.data.vertices),"head vertices")
