"""Title (90-100 s): bevelled letters come out of the dark in a beam through haze; at the end every light goes out."""
import os
import bpy
import common as C
from common import T

CYCLES = dict(volume_bounces=1)
FONT = "/usr/share/fonts/opentype/inter/Inter-Thin.otf"


def build(sc):
    n = C.scene_frames("title")
    fin = [T.scene_frame("title", x) for x in T.TITLE_IN]
    out = T.scene_frame("title", T.LIGHT_OUT)
    font = bpy.data.fonts.load(FONT) if os.path.exists(FONT) else None
    metal = C.material("metal", (0.9, 0.92, 1.0), roughness=0.18, metallic=1.0, emission=0.0, emission_color=(0.6, 0.75, 1.0))
    p = metal.node_tree.nodes["Principled BSDF"]
    for f, s in [(1, 0.0), (fin[0], 0.0), (fin[1], 0.6), (out - 1, 0.6), (out, 0.0)]:
        p.inputs["Emission Strength"].default_value = s
        p.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
    for text, z in [("SOFTWARE-DEFINED", 0.32), ("HOME THEATRE", -0.22)]:
        cu = bpy.data.curves.new(text, "FONT"); cu.body = text; cu.align_x = "CENTER"; cu.align_y = "CENTER"
        cu.size = 0.36; cu.extrude = 0.03; cu.bevel_depth = 0.006; cu.space_character = 1.15
        if font:
            cu.font = font
        o = C.link(bpy.data.objects.new(text, cu), sc)
        o.location = (0, 0, z); o.rotation_euler = (C.deg(90), 0, 0)
        cu.materials.append(metal)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -3, 0))
    hz = bpy.context.object; hz.scale = (24, 12, 10)
    hz.data.materials.append(C.volume("haze", density=0.006, anisotropy=0.7)[0])
    sp = bpy.data.lights.new("beam", "SPOT"); sp.spot_size = C.deg(28); sp.spot_blend = 0.4
    sp.shadow_soft_size = 0.05; sp.color = (0.75, 0.85, 1.0)
    so = C.link(bpy.data.objects.new("beam", sp), sc)
    for f, loc in [(1, (8, -6, 4.5)), (fin[1], (3.5, -6, 4.5)), (out, (-3.0, -6, 4.5))]:
        C.aim(so, loc, (0, 0, 0)); so.keyframe_insert("location", frame=f); so.keyframe_insert("rotation_euler", frame=f)
    rim = bpy.data.lights.new("rim", "AREA"); rim.size = 6; rim.color = (1.0, 0.6, 0.3)
    ro = C.link(bpy.data.objects.new("rim", rim), sc); C.aim(ro, (-6, 2, -1), (0, 0, 0))
    for li, peak in ((sp, 6000), (rim, 120)):
        for f, en in [(1, 0), (fin[0] - 12, 0), (fin[1], peak), (out - 1, peak), (out, 0)]:
            li.energy = en
            li.keyframe_insert("energy", frame=f)
    cam = C.camera(sc, (0, -7.5, 0.1), (0, 0, 0.05), lens=50)
    C.key(cam, 1, location=(0.25, -8.0, 0.1)); C.key(cam, n, location=(-0.2, -7.2, 0.1))
    C.linear_all(cam)
