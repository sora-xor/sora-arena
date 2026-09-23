"""Author an original Nyaagyu hero katana and saya in Blender 5.2+.

Run: blender -b --factory-startup --python scripts/art/create_hero_katana.py

The model is an editable source prop, not a claim that UE has imported it or that
the whole game has production-quality art. Dimensions are meters. The rendered
preview is a Blender product shot, not an Unreal gameplay image.
"""

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content" / "SourceArt"
OUT.mkdir(parents=True, exist_ok=True)
FBX = OUT / "SM_Nyaagyu_HeroKatana.fbx"
SAYA_FBX = OUT / "SM_Nyaagyu_HeroSaya.fbx"
BLEND = OUT / "Nyaagyu_HeroKatana.blend"
PREVIEW = OUT / "Nyaagyu_HeroKatana_Preview.png"
DETAIL = OUT / "Nyaagyu_HeroKatana_Detail.png"
ASSET_NAME = "SM_Nyaagyu_HeroKatana"

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

asset_collection = bpy.data.collections.new("Nyaagyu_HeroKatana_Asset")
bpy.context.scene.collection.children.link(asset_collection)


def move_to_asset(obj):
    for collection in tuple(obj.users_collection):
        collection.objects.unlink(obj)
    asset_collection.objects.link(obj)
    obj["author"] = "SORA Arena original procedural source art"
    return obj


def principled(name, rgb, metallic=0, roughness=0.5, noise_scale=0,
               rough_low=None, rough_high=None, bump=0, emission=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*rgb, 1)
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = 1.1
    if noise_scale:
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = noise_scale
        tex.inputs["Detail"].default_value = 3
        ramp = nodes.new("ShaderNodeMapRange")
        ramp.inputs["To Min"].default_value = rough_low if rough_low is not None else roughness * 0.8
        ramp.inputs["To Max"].default_value = rough_high if rough_high is not None else roughness * 1.2
        mat.node_tree.links.new(tex.outputs["Fac"], ramp.inputs["Value"])
        mat.node_tree.links.new(ramp.outputs["Result"], bsdf.inputs["Roughness"])
        if bump:
            node = nodes.new("ShaderNodeBump")
            node.inputs["Strength"].default_value = 0.16
            node.inputs["Distance"].default_value = bump
            mat.node_tree.links.new(tex.outputs["Fac"], node.inputs["Height"])
            mat.node_tree.links.new(node.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


STEEL = principled("M_HK_Tamahagane_Polished", (0.37, 0.43, 0.47), 1, .22, 72, .16, .29, .00006)
HA = principled("M_HK_Ha_BrightSteel", (.61, .66, .67), 1, .14, 55, .11, .20)
HAMON = principled("M_HK_Hamon_FrostedSteel", (.43, .49, .50), 1, .43, 110, .35, .48, .00003)
MUNE = principled("M_HK_Mune_BrushedSteel", (.20, .25, .27), 1, .33, 85, .27, .38)
IRON = principled("M_HK_PatinatedIron", (.070, .072, .069), .91, .40, 52, .33, .49, .0002)
BRASS = principled("M_HK_AgedBrass", (.39, .28, .12), .9, .34, 86, .27, .41, .0001)
HORN = principled("M_HK_BuffaloHorn", (.018, .023, .023), .02, .28, 64, .24, .36, .00008)
SKIN = principled("M_HK_RaySkin_Ivory", (.29, .27, .21), .0, .76, 240, .69, .84, .00028)
SILK = principled("M_HK_IndigoIto", (.025, .047, .063), .0, .77, 205, .66, .84, .00019)
LACQUER = principled("M_HK_Urushi_BlackBrown", (.018, .012, .009), .0, .19, 26, .15, .27, .0001)
CORD = principled("M_HK_Sageo_Silk", (.065, .073, .068), .0, .68, 180, .60, .77, .00016)
JADE = principled("M_HK_Induction_Inlay", (.018, .31, .29), .22, .23, emission=(.007, .12, .105))


def mesh(name, vertices, faces, materials, indices=None, smooth=True):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    asset_collection.objects.link(obj)
    for mat in materials:
        data.materials.append(mat)
    for i, poly in enumerate(data.polygons):
        poly.material_index = indices[i] if indices is not None else 0
        poly.use_smooth = smooth
    return move_to_asset(obj)


def bevel(obj, width, segments=2):
    mod = obj.modifiers.new("Small_machined_edge", "BEVEL")
    mod.width = width
    mod.segments = segments
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def cube(name, center, size, mat, edge=.001):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = move_to_asset(bpy.context.object)
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if edge:
        bevel(obj, edge, 3)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def tube(name, points, radius, mat, resolution=4):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 24
    curve.bevel_depth = radius
    curve.bevel_resolution = resolution
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, xyz in zip(spline.points, points):
        point.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, curve)
    asset_collection.objects.link(obj)
    curve.materials.append(mat)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj.select_set(False)
    return move_to_asset(bpy.context.object)


def sectioned_oval(name, sections, material, sides=32, y_offset=0):
    vertices = []
    faces = []
    for x, zcenter, ry, rz in sections:
        for i in range(sides):
            a = math.tau * i / sides
            vertices.append((x, y_offset + ry * math.sin(a), zcenter + rz * math.cos(a)))
    for s in range(len(sections) - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((s*sides+i, s*sides+j, (s+1)*sides+j, (s+1)*sides+i))
    faces.extend([tuple(reversed(range(sides))), tuple((len(sections)-1)*sides+i for i in range(sides))])
    return mesh(name, vertices, faces, [material])


# Sword origin lies on its grip/guard line. It spans 1.17 m: a ~77 cm blade
# and a ~27 cm grip, at a scale appropriate for a one-handed/two-handed katana.
def blade_profile(x):
    t = max(0, min(1, (x - .021) / .819))
    # A restrained Edo-period sori, with a subtly lifted kissaki.
    z = .003 + .016 * math.sin(math.pi * t) * .45 + .011 * t * t
    half_height = (.0174 * (1 - .22*t))
    thickness = (.0034 * (1 - .40*t))
    if x > .718:
        kissaki = max(.03, (0.840-x) / (.840-.718))
        half_height *= kissaki ** .53
        thickness *= kissaki ** .55
        z += .004 * (1-kissaki)
    return z, half_height, thickness


blade_sections = [(.021 + .819*i/85) for i in range(86)]
verts = []
faces = []
face_mats = []
for x in blade_sections:
    z, h, t = blade_profile(x)
    verts.extend([
        (x, 0, z-h),                        # ha, mathematically narrow edge
        (x, -t*.66, z-h*.12),
        (x, -t, z+h*.30),                   # shinogi ridge
        (x, -t*.59, z+h),
        (x, +t*.59, z+h),                   # mune
        (x, +t, z+h*.30),
        (x, +t*.66, z-h*.12),
    ])
for i in range(len(blade_sections)-1):
    for j in range(7):
        k = (j+1) % 7
        faces.append((i*7+j, (i+1)*7+j, (i+1)*7+k, i*7+k))
        face_mats.append({0:1, 1:0, 2:0, 3:3, 4:0, 5:0, 6:1}[j])
faces.extend([tuple(reversed(range(7))), tuple((len(blade_sections)-1)*7+i for i in range(7))])
face_mats.extend([3, 1])
blade = mesh("Blade_ForgedWithShinogiAndKissaki", verts, faces,
             [STEEL, HA, HAMON, MUNE], face_mats, smooth=False)
blade["function"] = "Curved forged blade with distinct edge, shinogi and mune facets"


def lower_face_y(x, z_at):
    z, h, t = blade_profile(x)
    lo, hi = z-h, z-h*.12
    frac = max(0.0, min(1.0, (z_at-lo)/(hi-lo)))
    return -t*.66*frac


# An irregular, very shallow hardening line on both visible blade faces.
# It is geometry, so it survives the FBX round trip without a node graph.
for side in (-1, 1):
    vertices = []
    faces = []
    for i in range(186):
        x = .071 + .716*i/185
        z, h, _ = blade_profile(x)
        ripple = .00085*math.sin(2*math.pi*x/0.031) + .00035*math.sin(2*math.pi*x/.079)
        center = z-h + .0062+ripple
        for offset in (-.00105, .00105):
            zz = center+offset
            yy = lower_face_y(x, zz)
            yy = yy-.00013 if side < 0 else -yy+.00013
            vertices.append((x, yy, zz))
        if i:
            q = 2*i
            faces.append((q-2, q-1, q+1, q))
    mesh("Hamon_CloudLine_Front" if side < 0 else "Hamon_CloudLine_Back",
         vertices, faces, [HAMON], smooth=False)

# Narrow golden habaki, seppa washers, and iron guard. These proportions make
# the structural transition legible in first-person closeups.
sectioned_oval("Habaki_TaperedCollar", [(.011, .003, .0067, .021),
                 (.041, .003, .0056, .017), (.061, .003, .0048, .016)], BRASS)
for x, ry, rz in [(.008, .015, .027), (-.008, .014, .026)]:
    sectioned_oval("Seppa_BrassWasher", [(x-.0015,.003,ry,rz),(x+.0015,.003,ry,rz)], BRASS)


def tsuba():
    n = 72
    vv = []
    ff = []
    def outer(a, scale=1):
        lobes = 1 + .055*math.cos(4*a) - .014*math.cos(8*a)
        return (.061*math.sin(a)*lobes*scale, .068*math.cos(a)*lobes*scale+.003)
    rings = [(-.005, .925), (-.003, 1.0), (.003, 1.0), (.005, .925)]
    for x, scale in rings:
        for i in range(n):
            y,z = outer(math.tau*i/n, scale)
            vv.append((x,y,z))
    for s in range(3):
        for i in range(n):
            j=(i+1)%n
            ff.append((s*n+i,s*n+j,(s+1)*n+j,(s+1)*n+i))
    # Front/back annular iron faces with an open central nakago aperture.
    for x in (-.005,.005):
        for i in range(n):
            a=math.tau*i/n
            vv.append((x,.010*math.sin(a),.022*math.cos(a)+.003))
    front=4*n; back=5*n
    for i in range(n):
        j=(i+1)%n
        ff.append((front+i,front+j,j,i))
        ff.append((back+i,back+j,3*n+j,3*n+i))
        ff.append((front+i,back+i,back+j,front+j))
    guard=mesh("Tsuba_MokkoFourLobedOpenwork",vv,ff,[IRON],smooth=False)
    guard["historical_inspiration"] = "Four-lobed mokko iron tsuba; original inlay design"
    # Inlay follows the rim; smaller leaf motifs give detail without making
    # the sword read as ornate fantasy equipment.
    for sx in (-1,1):
        x=sx*.00545
        points=[]
        for i in range(145):
            a=math.tau*i/144
            y,z=outer(a,.806)
            points.append((x,y,z))
        tube("Tsuba_AgedBrassRimInlay", points, .00065, BRASS, 2)
        for quadrant in range(4):
            a=math.tau*quadrant/4+math.pi/4
            cy=.035*math.sin(a); cz=.037*math.cos(a)+.003
            motif=[]
            for k in range(17):
                phi=math.tau*k/16
                motif.append((x,cy+.006*math.sin(phi)*math.sin(a),
                              cz+.006*math.sin(phi)*math.cos(a)))
            tube("Tsuba_PetalInlay",motif,.00055,BRASS,2)


tsuba()

# Bronze fuchi/kashira over a tapered ray-skin core. The main ito is true
# crossing ribbon geometry, leaving recognizable diamond windows of samegawa.
sectioned_oval("Tsuka_RaySkinCore",[
    (-.336, .001, .019, .024),(-.302,.001,.022,.026),
    (-.164,.002,.023,.027),(-.014,.003,.021,.025)], SKIN)

# Raised samegawa granules, modeled explicitly so the grip retains its tactile
# material in an FBX import even when Blender procedural nodes are not copied.
bead_verts=[]; bead_faces=[]
for row in range(93):
    x=-.319+.268*row/92
    ry=.0222+.0008*math.sin(math.pi*row/92)
    rz=.0260+.0010*math.sin(math.pi*row/92)
    for column in range(18):
        phi=math.tau*(column+(row%2)*.5)/18
        normal=Vector((0,math.sin(phi)/ry,math.cos(phi)/rz)).normalized()
        tangent=Vector((0,math.cos(phi),-math.sin(phi)))
        base=Vector((x,ry*math.sin(phi),.002+rz*math.cos(phi)))
        # A lightly varied low dome; 0.7 mm scale is visible in closeups.
        r=.00070+.00015*math.sin(row*7.23+column*3.71)
        start=len(bead_verts)
        for k in range(6):
            a=math.tau*k/6
            v=base+Vector((math.cos(a)*r,0,0))+tangent*(math.sin(a)*r)
            bead_verts.append(tuple(v))
        bead_verts.append(tuple(base+normal*(r*.83)))
        for k in range(6):
            bead_faces.append((start+k,start+(k+1)%6,start+6))
mesh("Samegawa_RaySkinGranules",bead_verts,bead_faces,[SKIN],smooth=False)

for name,x0,x1,ry,rz,material in [
    ("Kashira_Endcap",-.345,-.327,.021,.027,IRON),
    ("Fuchi_Collar",-.044,-.011,.023,.028,IRON),
]:
    sectioned_oval(name, [(x0,.002,ry*.94,rz*.94),
                         (x0+.002,.002,ry,rz),
                         (x1-.002,.002,ry,rz),
                         (x1,.002,ry*.94,rz*.94)],material)
for hand in (-1,1):
    # Two oppositely wound continuous cloth ribbons. Their geometry is kept
    # above the grip for silhouette and specular readability.
    vv=[]; ff=[]
    steps=7*72
    for i in range(steps+1):
        t=i/steps
        phi=hand*(math.tau*7.1*t)+.11
        x=-.322+.264*t
        shape=1-.08*abs(2*t-1)
        ry=(.0235*shape)+.0017
        rz=(.0275*shape)+.0017
        for off in (-.0050,.0050):
            vv.append((x+off,ry*math.sin(phi),.002+rz*math.cos(phi)))
        if i:
            q=2*i
            ff.append((q-2,q-1,q+1,q))
    mesh("Tsuka_Ito_Clockwise" if hand > 0 else "Tsuka_Ito_Counterclockwise",
         vv,ff,[SILK],smooth=False)

# Small menuki castings partly visible below the wrappings.
for x in (-.245,-.126):
    cube("Menuki_BrassSeed",(x,-.023,.002),(.015,.0024,.004),BRASS,.001)

# One low-key original science-fiction element: a recessed, narrow induction
# line in the habaki and two tiny isolated conductor dots, never a blade-wide
# neon beam. It is an inlay, not a mechanical power/stat modifier.
tube("Habaki_InductionInlay",[(.035,-.0066,-.010),(.039,-.0066,.0),
     (.035,-.0066,.011)],.00075,JADE,3)
for z in (-.029,.029):
    tube("Tsuba_InductionContact",[(-.0058,-.012,z),(-.0058,-.007,z)],.0009,JADE,3)

# Lacquered saya beside the drawn blade. Its own curve mirrors the sori;
# the opening, kurikata, cord, and kojiri are separate readable forms.
saya_y=.175
saya_sections=[]
for i in range(33):
    x=.053+.776*i/32
    bz,_,_=blade_profile(min(.839,x))
    taper=1-.23*i/32
    if i==32: taper=.28
    saya_sections.append((x,bz-.004,.015*taper,.023*taper))
sectioned_oval("Saya_UrushiLacquerWood",saya_sections,LACQUER,40,saya_y)
for name,x0,x1,mat in [
    ("Koiguchi_HornMouth",.047,.070,HORN),
    ("Kojiri_BrassChape",.806,.832,BRASS),
]:
    sectioned_oval(name,[(x0,-.001,.016,.025),(x0+.002,-.001,.017,.026),
                         (x1-.002,.002,.016,.024),(x1,.002,.015,.023)],
                  mat,40,saya_y)
sectioned_oval("Kurikata_CordMount",[(.300,.020,.011,.009),(.314,.022,.013,.011),
                        (.340,.022,.013,.011),(.351,.020,.011,.009)],HORN,28,saya_y+.005)
tube("Sageo_Loop",[(.326,saya_y+.018,.023),(.330,saya_y+.037,.040),
     (.361,saya_y+.046,.028),(.379,saya_y+.041,.009)],.003, CORD)
tube("Sageo_HangingCord",[(.379,saya_y+.041,.009),(.388,saya_y+.052,-.027),
     (.453,saya_y+.040,-.040),(.497,saya_y+.022,-.013)],.0025,CORD)

# Fine longitudinal hairline in the lacquer and matched fittings are deliberately
# subdued. The viewport source preserves all components as independently editable.
tube("Saya_FineBrassInlay",[(.102+i*.006,saya_y-.0151,
       blade_profile(.102+i*.006)[0]+.007) for i in range(110)],.00052,BRASS,2)

parts=[o for o in asset_collection.objects if o.type == "MESH"]
assert len(parts) >= 20, len(parts)
assert sum(len(o.data.polygons) for o in parts) > 5000


def assign_projection_uv(obj):
    """Keep a stable physical-scale UV on fine fittings and curved steel alike.

    The side of the blade uses X along its length; each other face projects
    from its dominant normal. Texture tiling is deliberate at this prop scale.
    """
    data = obj.data
    layer = data.uv_layers.get("HeroKatanaProjection") or data.uv_layers.new(name="HeroKatanaProjection")
    for polygon in data.polygons:
        nx, ny, nz = map(abs, polygon.normal)
        for loop_index in polygon.loop_indices:
            x, y, z = data.vertices[data.loops[loop_index].vertex_index].co
            if ny >= nx and ny >= nz:
                uv = (x * 4.0, z * 4.0)
            elif nz >= nx:
                uv = (x * 4.0, y * 4.0)
            else:
                uv = (y * 4.0, z * 4.0)
            layer.data[loop_index].uv = uv


for part in parts:
    assign_projection_uv(part)

# A drawn first-person katana must not carry its saya in parallel with the
# blade. Preserve all scabbard components in the editable source and review
# render; export only the unsheathed weapon to the runtime asset identity.
saya_prefixes = ("Saya_", "Koiguchi_", "Kojiri_", "Kurikata_", "Sageo_")
drawn_parts = [part for part in parts if not part.name.startswith(saya_prefixes)]
saya_parts = [part for part in parts if part.name.startswith(saya_prefixes)]
assert len(drawn_parts) >= 15 and len(drawn_parts) < len(parts)

# Export drawn sword and saya independently.  Source parts remain editable and
# the scabbard is recentered from its side-by-side review pose for a future hip
# attachment. The FBX runtime identity of the sword is unchanged.
def export_prop(selected_parts, name, path, recenter_y=0):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in selected_parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active=selected_parts[0]
    bpy.ops.object.duplicate()
    copies=list(bpy.context.selected_objects)
    bpy.context.view_layer.objects.active=copies[0]
    bpy.ops.object.join()
    export_obj=bpy.context.object
    export_obj.name=name
    if recenter_y:
        for vertex in export_obj.data.vertices:
            vertex.co.y -= recenter_y
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={"MESH"},
        apply_unit_scale=True,global_scale=1.0,axis_forward="-Y",axis_up="Z",
        add_leaf_bones=False,bake_anim=False,path_mode="AUTO")
    bpy.data.objects.remove(export_obj,do_unlink=True)


export_prop(drawn_parts, ASSET_NAME, FBX)
export_prop(saya_parts, "SM_Nyaagyu_HeroSaya", SAYA_FBX, saya_y)

# A studio preview is kept as an editable Blender scene. The warm key and cool
# edge light are an art presentation, not a purported engine screenshot.
studio=bpy.data.collections.new("Preview_Studio_NotForFBX")
bpy.context.scene.collection.children.link(studio)
ground=principled("M_Preview_DarkStone",(.007,.009,.012),0,.79,13,.74,.84,.0007)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.071))
floor=bpy.context.object;floor.name="Preview_Floor";floor.data.materials.append(ground)
for col in tuple(floor.users_collection): col.objects.unlink(floor)
studio.objects.link(floor)

def area(name, pos, color, power, size):
    bpy.ops.object.light_add(type="AREA",location=pos)
    ob=bpy.context.object;ob.name=name
    ob.data.energy=power;ob.data.color=color;ob.data.shape="DISK";ob.data.size=size
    ob.rotation_euler=(Vector((.23,.09,0))-ob.location).to_track_quat("-Z","Y").to_euler()
    for col in tuple(ob.users_collection): col.objects.unlink(ob)
    studio.objects.link(ob)

area("Warm_Softbox",(.3,-.7,1.5),(1.0,.78,.56),115,1.15)
area("Cold_Rim",(.7,1.1,1.2),(.40,.70,1.0),145,.8)
area("Long_Steel_Reflection",(-.55,-.1,1.05),(.90,.91,1.0),52,.44)

bpy.ops.object.camera_add(location=(.22,-.87,1.16))
camera=bpy.context.object;camera.name="Katana_Preview_Camera"
for col in tuple(camera.users_collection): col.objects.unlink(camera)
studio.objects.link(camera)
target=Vector((.245,.084,0))
camera.rotation_euler=(target-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.type="ORTHO"
camera.data.ortho_scale=1.38
bpy.context.scene.camera=camera

bpy.ops.object.camera_add(location=(-.46,-.52,.38))
detail_camera=bpy.context.object;detail_camera.name="Katana_Fittings_Detail_Camera"
for col in tuple(detail_camera.users_collection): col.objects.unlink(detail_camera)
studio.objects.link(detail_camera)
detail_camera.rotation_euler=(Vector((-.035,0,.002))-detail_camera.location).to_track_quat("-Z","Y").to_euler()
detail_camera.data.type="ORTHO"
detail_camera.data.ortho_scale=.55

scene=bpy.context.scene
scene.render.engine="CYCLES"
scene.cycles.samples=64
scene.cycles.use_denoising=True
scene.render.resolution_x=1920
scene.render.resolution_y=820
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.filepath=str(PREVIEW)
scene.world.color=(.035,.045,.052)
scene.view_settings.view_transform="AgX"
scene.view_settings.exposure=-1.25
bpy.ops.render.render(write_still=True)
scene.camera=detail_camera
scene.render.resolution_x=1400
scene.render.resolution_y=1000
scene.render.filepath=str(DETAIL)
bpy.ops.render.render(write_still=True)
scene.camera=camera
scene.render.resolution_x=1920
scene.render.resolution_y=820
scene.render.filepath=str(PREVIEW)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

manifest_path=OUT/"manifest.json"
manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["hero_katana"]={
    "name":ASSET_NAME,
    "authorship":"Original geometry, material graphs and lighting authored for SORA Arena by procedural Blender script; no third-party source meshes or textures",
    "license":"Original project-owned artwork; no purchased assets",
    "source_blend":BLEND.name,
    "generator":"scripts/art/create_hero_katana.py",
    "fbx":FBX.name,
    "saya_name":"SM_Nyaagyu_HeroSaya",
    "saya_fbx":SAYA_FBX.name,
    "preview":PREVIEW.name,
    "detail_preview":DETAIL.name,
    "fbx_sha256":hashlib.sha256(FBX.read_bytes()).hexdigest(),
    "saya_fbx_sha256":hashlib.sha256(SAYA_FBX.read_bytes()).hexdigest(),
    "units":"Blender meters; FBX converts for Unreal centimeter import",
    "materials":"Physically based Principled BSDF source materials, with metalness/roughness and subtle procedural surface variation; author matching Unreal material instances on import",
    "runtime_export":"Drawn katana only; the separately modeled saya remains in the editable Blender source and review renders",
    "projection_uv":"Dominant-normal planar UV, four repeats per source meter; present on every modeled part",
    "scope":"Detailed drawn hero katana with separate non-runtime saya source. This does not establish game-wide photorealism or verify Unreal rendering.",
}
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("HERO_KATANA_READY",len(parts),sum(len(o.data.polygons) for o in parts),FBX,PREVIEW)
