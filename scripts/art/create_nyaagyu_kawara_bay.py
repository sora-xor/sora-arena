"""Model a one-bay honbuki-inspired concave/convex roof study in Blender.

Run build_nyaagyu_kawara_pbr.py first, then:
  blender -b --factory-startup --python scripts/art/create_nyaagyu_kawara_bay.py
This is a source-only form/material test, not an Edo-period reconstruction.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuKawaraBay"
LOGO = ROOT / "Content/SourceArt/UI/SORA_Resistance_Logo.png"
ALBEDO_GENERATED = OUT / "T_NyaagyuKawara_ImageGenAlbedo_v1.png"
LOGO_MANIFEST = json.loads((LOGO.parent / "sora_logo_manifest.json").read_text())
assert hashlib.sha256(LOGO.read_bytes()).hexdigest() == LOGO_MANIFEST["runtime_sha256"]
assert ALBEDO_GENERATED.exists(), ALBEDO_GENERATED
OUT.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1
asset = bpy.data.collections.new("KawaraBay_Editable")
scene.collection.children.link(asset)


def material(name, color, rough=.7, metal=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    return mat


ceramic = material("M_Kawara_FiredCeramic_OriginalAtlas", (.29,.30,.31))
nodes, links = ceramic.node_tree.nodes, ceramic.node_tree.links
bsdf = nodes.get("Principled BSDF")
uv = nodes.new("ShaderNodeTexCoord")
tex = {}
for channel in ("Albedo", "NormalDX", "ORM"):
    path = OUT / f"T_NyaagyuKawara_{channel}.png"
    assert path.exists(), path
    node = nodes.new("ShaderNodeTexImage")
    node.name = channel
    node.image = bpy.data.images.load(str(path), check_existing=True)
    node.image.colorspace_settings.name = "sRGB" if channel == "Albedo" else "Non-Color"
    links.new(uv.outputs["UV"], node.inputs["Vector"])
    tex[channel] = node
links.new(tex["Albedo"].outputs["Color"], bsdf.inputs["Base Color"])
orm = nodes.new("ShaderNodeSeparateColor")
links.new(tex["ORM"].outputs["Color"], orm.inputs["Color"])
links.new(orm.outputs["Green"], bsdf.inputs["Roughness"])
split = nodes.new("ShaderNodeSeparateColor")
links.new(tex["NormalDX"].outputs["Color"], split.inputs["Color"])
flip = nodes.new("ShaderNodeMath")
flip.operation = "SUBTRACT"
flip.inputs[0].default_value = 1
links.new(split.outputs["Green"], flip.inputs[1])
join = nodes.new("ShaderNodeCombineColor")
links.new(split.outputs["Red"], join.inputs["Red"])
links.new(flip.outputs[0], join.inputs["Green"])
links.new(split.outputs["Blue"], join.inputs["Blue"])
nmap = nodes.new("ShaderNodeNormalMap")
nmap.inputs["Strength"].default_value = .48
links.new(join.outputs["Color"], nmap.inputs["Color"])
links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

cedar = material("M_Kawara_CharredCedarSupport", (.075,.058,.046), .8)
end_clay = material("M_Kawara_ExposedClayEdge", (.21,.22,.22), .78)
brass = material("M_Kawara_WeatheredBrassInlay", (.24,.18,.085), .43, .7)


def place(obj, name, mat):
    obj.name = name
    for collection in tuple(obj.users_collection):
        collection.objects.unlink(obj)
    asset.objects.link(obj)
    obj.data.materials.append(mat)
    obj["author"] = "SORA Arena original modeled roof-bay study"
    return obj


def box(name, loc, dimensions, mat, bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = place(bpy.context.object, name, mat)
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("softened_arris", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        for face in obj.data.polygons:
            face.use_smooth = True
    return obj


def roof_z(y):
    return .40 + y*.265


def tile(name, cx, y0, width, length, cover, variant, warp):
    # The two differently curved solids are separate real clay pieces. Each
    # overlaps the course below by ~74 mm; the cover sits over a pan seam.
    verts, faces, uv_faces = [], [], []
    nx, ny = 12, 8
    thickness = .011 if not cover else .012
    for skin in (0, 1):
        for iy in range(ny+1):
            v = iy/ny
            yy = y0 + v*length
            for ix in range(nx+1):
                u = ix/nx
                signed = 2*u-1
                xx = cx + signed*width*.5
                # Kiln twist and slightly rounded, individually varied lip.
                twist = warp * math.sin(math.pi*v) * signed
                lip = .0035*math.sin(math.pi*v)*math.sin(math.pi*u)
                section = (.038*signed*signed if not cover else .038-.021*signed*signed)
                # The raised down-slope nose is what makes one course visibly
                # lap over the course below; coplanar sheets z-fight in Lumen.
                course_lift = .014*(1-v)**2
                top = roof_z(yy) + .024 + section + twist + lip + course_lift
                verts.append((xx, yy, top - skin*thickness))
    stride = (nx+1)*(ny+1)
    for skin in (0,1):
        for iy in range(ny):
            for ix in range(nx):
                a=skin*stride+iy*(nx+1)+ix
                quad=(a,a+1,a+nx+2,a+nx+1)
                faces.append(quad if skin==0 else tuple(reversed(quad)))
                uv_faces.append(((ix/nx,iy/ny),((ix+1)/nx,iy/ny),
                                 ((ix+1)/nx,(iy+1)/ny),(ix/nx,(iy+1)/ny)))
    for iy in range(ny):
        for ix in (0,nx):
            a=iy*(nx+1)+ix; b=(iy+1)*(nx+1)+ix
            faces.append((a,b,b+stride,a+stride))
            uv_faces.append(((0,iy/ny),(1,iy/ny),(1,(iy+1)/ny),(0,(iy+1)/ny)))
    for ix in range(nx):
        for iy in (0,ny):
            a=iy*(nx+1)+ix; b=a+1
            faces.append((a,b,b+stride,a+stride))
            uv_faces.append(((ix/nx,0),((ix+1)/nx,0),((ix+1)/nx,1),(ix/nx,1)))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj=bpy.data.objects.new(name,mesh)
    asset.objects.link(obj)
    mesh.materials.append(ceramic)
    layer=mesh.uv_layers.new(name="UVMap")
    for poly, corners in zip(mesh.polygons, uv_faces):
        for loop_index, (u,v) in zip(poly.loop_indices, corners):
            # 1.5% atlas padding prevents mip bleed between tile faces.
            layer.data[loop_index].uv=((variant%4 + .015 + .970*u)/4,
                                       (variant//4 + .015 + .970*v)/4)
        poly.use_smooth = True
    obj["tile_type"]="mune-maru cover" if cover else "hira-gawara pan"
    obj["tile_variant"] = variant
    return obj


cols, rows = 6, 5
width, length, course = .240, .303, .229
for row in range(rows):
    # Back courses first and foreground eaves last, avoiding open seams.
    y0 = row*course
    for col in range(cols):
        variant = (row*7+col*11) % 16
        warp = .0018*math.sin(row*17+col*29)
        tile(f"HiraGawara_Pan_R{row}_C{col}", (col+.5)*width, y0,
             width+.012, length, False, variant, warp)
    for col in range(1,cols):
        variant = (row*13+col*5+3) % 16
        tile(f"MaruGawara_Cover_R{row}_C{col}", col*width,
             y0-.004, .087, length+.010, True, variant,
             .0012*math.cos(row*19+col*7))

for row in range(rows):
    y=row*course+.055
    box(f"CedarBatten_{row}",(.72,y,roof_z(y)-.032),
        (1.48,.041,.025),cedar)
box("EaveFascia",(.72,-.024,roof_z(0)-.034),(1.50,.045,.081),cedar,.006)

# One heraldic eave disc uses the user's exact supplied mark as a decorative
# project crest. It is not a claim about historical tile ornament.
bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=.043,depth=.012,
                                    location=(.24,-.040,roof_z(0)+.053),
                                    rotation=(math.pi/2,0,0))
cap=place(bpy.context.object,"SORA_Kamon_EaveCap",end_clay)
bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=.038,depth=.0015,
                                    location=(.24,-.048,roof_z(0)+.053),
                                    rotation=(math.pi/2,0,0))
inlay=place(bpy.context.object,"Kamon_Brass_Ring",brass)
logo_mat=material("M_Kawara_SORA_Kamon_UserRaster",(.7,.1,.1),.46)
ln=logo_mat.node_tree.nodes.new("ShaderNodeTexImage")
ln.image=bpy.data.images.load(str(LOGO),check_existing=True)
ln.image.alpha_mode='STRAIGHT'
logo_mat.node_tree.links.new(ln.outputs["Color"],logo_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
logo_mat.node_tree.links.new(ln.outputs["Alpha"],logo_mat.node_tree.nodes["Principled BSDF"].inputs["Alpha"])
logo_mat.surface_render_method='DITHERED'
bpy.ops.mesh.primitive_plane_add(size=1, location=(.24,-.050,roof_z(0)+.053),
                                 rotation=(math.pi/2,0,0))
decal=place(bpy.context.object,"SORA_Kamon_UserSuppliedLogo",logo_mat)
decal.scale=(.065,.065,.065)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)

camera_data=bpy.data.cameras.new("RoofBay_ReviewCamera")
camera=bpy.data.objects.new("RoofBay_ReviewCamera",camera_data)
scene.collection.objects.link(camera)
camera.location=(1.85,-2.28,1.96)
target=Vector((.72,.55,.58))
camera.rotation_euler=(target-Vector(camera.location)).to_track_quat("-Z","Y").to_euler()
camera_data.type='ORTHO'; camera_data.ortho_scale=2.05
scene.camera=camera

world=bpy.data.worlds.new("Neutral_Overcast")
scene.world=world; world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Color"].default_value=(.37,.41,.46,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.32
for name,loc,power,size in (("SkyKey",(0.2,-1.1,3.2),360,2.7),
                            ("SoftFill",(2.2,1.1,2.4),160,2.2)):
    data=bpy.data.lights.new(name,"AREA"); data.energy=power; data.shape='DISK'; data.size=size
    obj=bpy.data.objects.new(name,data); scene.collection.objects.link(obj); obj.location=loc
    obj.rotation_euler=(target-Vector(loc)).to_track_quat("-Z","Y").to_euler()
scene.render.engine='CYCLES'
scene.cycles.samples=48
scene.render.resolution_x=1360; scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.view_settings.exposure = -.35
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(OUT/"Nyaagyu_KawaraBay_ProceduralReview.png")
scene.camera.data.lens=50
bpy.ops.render.render(write_still=True)

# Keep the geometry, normals, roughness, camera, and lights exactly unchanged:
# only albedo changes in this source-only A/B. The generated swatch is an
# illustration-like color source, not a measured photographic/PBR capture.
generated = nodes.new("ShaderNodeTexImage")
generated.name = "ImageGen ceramic albedo candidate"
generated.image = bpy.data.images.load(str(ALBEDO_GENERATED), check_existing=True)
generated.image.colorspace_settings.name = "sRGB"
links.new(uv.outputs["UV"], generated.inputs["Vector"])
links.new(generated.outputs["Color"], bsdf.inputs["Base Color"])
scene.render.filepath=str(OUT/"Nyaagyu_KawaraBay_ImageGenReview.png")
bpy.ops.render.render(write_still=True)

for image in bpy.data.images:
    if image.source=='FILE' and image.filepath:
        image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"Nyaagyu_KawaraBay.blend"))
bpy.ops.object.select_all(action="DESELECT")
for obj in asset.objects: obj.select_set(True)
bpy.context.view_layer.objects.active=next(iter(asset.objects))
bpy.ops.export_scene.fbx(filepath=str(OUT/"SM_Nyaagyu_KawaraBay.fbx"),
                         use_selection=True, object_types={'MESH'},
                         apply_unit_scale=True, axis_forward='-Z', axis_up='Y',
                         add_leaf_bones=False, path_mode='STRIP')
manifest={
    "status":"source-only form/material study; not approved for Unreal runtime",
    "generator":"scripts/art/create_nyaagyu_kawara_bay.py",
    "tile_count":{"pan":cols*rows,"cover":(cols-1)*rows},
    "nominal_dimensions_m":{"tile_width":width,"tile_length":length,
                            "course":course,"roof_bay_width":cols*width},
    "design_reference":"https://eishiro.co.jp/english/products/honbuki/index.html",
    "reference_note":"Modern honbuki concave/convex arrangement informs the form. Pan width 240 mm and length 303 mm are independent study choices from different listed sizes; the 87 mm seam-cover width and overlap are artistic approximations, not a historical or product match.",
    "sora_logo_raster_sha256":hashlib.sha256(LOGO.read_bytes()).hexdigest(),
    "generated_albedo":{"file":ALBEDO_GENERATED.name,
      "sha256":hashlib.sha256(ALBEDO_GENERATED.read_bytes()).hexdigest(),
      "generation_id":"exec-2c249455-3d4c-4d61-ba66-851b7bc735b0",
      "role":"source-only color reference; not a measured ceramic or PBR capture"},
    "outputs":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
               (OUT/"SM_Nyaagyu_KawaraBay.fbx",OUT/"Nyaagyu_KawaraBay.blend",
                OUT/"Nyaagyu_KawaraBay_ProceduralReview.png",
                OUT/"Nyaagyu_KawaraBay_ImageGenReview.png")},
}
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print(json.dumps(manifest,indent=2))
