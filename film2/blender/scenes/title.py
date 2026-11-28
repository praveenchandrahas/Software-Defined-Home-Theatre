"""Title: bevelled letters in a beam of light through haze."""
import os
import bpy
import common as C

CYCLES = dict(volume_bounces=1)
FONT = "/usr/share/fonts/opentype/inter/Inter-Thin.otf"


def build(sc):
    font = bpy.data.fonts.load(FONT) if os.path.exists(FONT) else None
    for text, z, size in [("SOFTWARE-DEFINED", 0.32, 0.36), ("HOME THEATRE", -0.22, 0.36)]:
        cu = bpy.data.curves.new(text, "FONT"); cu.body = text; cu.align_x = "CENTER"; cu.align_y = "CENTER"
        cu.size = size; cu.extrude = 0.03; cu.bevel_depth = 0.006; cu.space_character = 1.15
        if font:
            cu.font = font
        o = C.link(bpy.data.objects.new(text, cu), sc)
        o.location = (0, 0, z); o.rotation_euler = (C.deg(90), 0, 0)
        cu.materials.append(C.material("metal", (0.9, 0.92, 1.0), roughness=0.18, metallic=1.0))
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0.4, 0), rotation=(C.deg(90), 0, 0))
    back = bpy.context.object; back.scale = (40, 20, 1)
    back.data.materials.append(C.material("back", (0.01, 0.01, 0.012), roughness=0.6))
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -3, 0))
    hz = bpy.context.object; hz.scale = (24, 12, 10)
    hz.data.materials.append(C.volume("haze", density=0.012, anisotropy=0.6)[0])
    sp = bpy.data.lights.new("beam", "SPOT"); sp.energy = 6000; sp.spot_size = C.deg(28); sp.spot_blend = 0.4
    sp.shadow_soft_size = 0.05; sp.color = (0.75, 0.85, 1.0)
    so = C.link(bpy.data.objects.new("beam", sp), sc)
    C.aim(so, (3.5, -6, 4.5), (0, 0, 0))
    rim = bpy.data.lights.new("rim", "AREA"); rim.energy = 400; rim.size = 6; rim.color = (1.0, 0.6, 0.3)
    ro = C.link(bpy.data.objects.new("rim", rim), sc)
    C.aim(ro, (-6, 2, -1), (0, 0, 0))
    cam = C.camera(sc, (0, -7.5, 0.1), (0, 0, 0.1), lens=50)
    C.key(cam, 1, location=(0.25, -7.8, 0.1)); C.key(cam, 96, location=(-0.25, -7.2, 0.1))
