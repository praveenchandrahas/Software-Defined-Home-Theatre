"""Echo (8-18 s): pings from the speakers' places spread through a dark room; its edges light where each wave passes.

Blender coordinates are the seat's: x right, y forward, z up, metres."""
import bpy
import common as C
from common import T

CYCLES = dict(volume_bounces=0)
COLS = [(0.35, 0.65, 1.0), (0.45, 0.9, 1.0), (0.65, 0.5, 1.0), (0.4, 1.0, 0.8), (1.0, 0.7, 0.4)]


def bounds():
    w, d, h, f = T.ROOM["width"], T.ROOM["depth"], T.ROOM["height"], T.ROOM["front"]
    return (-w / 2, w / 2), (f - d, f), (0.0, h)


def source(name):
    """The speaker's direction from the seat, pulled inside the room."""
    sx, sy, sz = T.ROOM["seat"]
    d = T.SPEAKERS[name]
    lim = bounds()
    s = T.SPEAKER_DIST
    for k, (c, (lo, hi)) in enumerate(zip((sx, sy, sz), lim)):
        if d[k] > 1e-6:
            s = min(s, 0.92 * (hi - c) / d[k])
        elif d[k] < -1e-6:
            s = min(s, 0.92 * (lo - c) / d[k])
    return (sx + d[0] * s, sy + d[1] * s, sz + d[2] * s)


def build(sc):
    (x0, x1), (y0, y1), (z0, z1) = bounds()
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    room = bpy.context.object
    room.scale = (x1 - x0, y1 - y0, z1 - z0)
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.subdivide(number_cuts=11)
    bpy.ops.object.mode_set(mode="OBJECT")
    md = room.modifiers.new("w", "WIREFRAME"); md.thickness = 0.005; md.use_replace = True

    m = bpy.data.materials.new("waves"); m.use_nodes = True; nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    total_col = None
    for i, (tp, spk) in enumerate(T.PINGS):
        f0 = T.scene_frame("echo", tp)
        life = 3.2 * T.FPS
        radius = C.value_node(nt, [(1, -5.0), (f0 - 1, -5.0), (f0, 0.0), (f0 + life, T.WAVE_SPEED * life / T.FPS)])
        amp = C.value_node(nt, [(1, 0.0), (f0 - 1, 0.0), (f0, 1.0), (f0 + life, 0.0)])
        dist = nt.nodes.new("ShaderNodeVectorMath"); dist.operation = "DISTANCE"
        dist.inputs[1].default_value = source(spk)
        nt.links.new(geo.outputs["Position"], dist.inputs[0])
        d = C.math_node(nt, "SUBTRACT", dist.outputs["Value"], radius.outputs[0])
        z = C.math_node(nt, "DIVIDE", d, 0.05)
        g = C.math_node(nt, "EXPONENT", C.math_node(nt, "MULTIPLY", C.math_node(nt, "MULTIPLY", z, z), -1.0))
        after = C.math_node(nt, "MULTIPLY", C.math_node(nt, "LESS_THAN", d, 0.0), 0.04)
        e = C.math_node(nt, "MULTIPLY", C.math_node(nt, "MULTIPLY_ADD", g, 7.0, after), amp.outputs[0])
        rgb = nt.nodes.new("ShaderNodeCombineColor")
        for k in range(3):
            nt.links.new(C.math_node(nt, "MULTIPLY", e, COLS[i][k]), rgb.inputs[k])
        if total_col is None:
            total_col = rgb.outputs[0]
        else:
            mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "ADD"
            mix.inputs["Factor"].default_value = 1.0
            nt.links.new(total_col, mix.inputs[6]); nt.links.new(rgb.outputs[0], mix.inputs[7])
            total_col = mix.outputs[2]
    floor = nt.nodes.new("ShaderNodeEmission"); floor.inputs["Strength"].default_value = 1.0
    nt.links.new(total_col, floor.inputs["Color"])
    nt.links.new(floor.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    room.data.materials.append(m)

    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    haze = bpy.context.object; haze.scale = (x1 - x0, y1 - y0, z1 - z0)
    haze.data.materials.append(C.volume("haze", density=0.025, anisotropy=0.5)[0])
    for i, (tp, spk) in enumerate(T.PINGS):
        f0 = T.scene_frame("echo", tp)
        li = bpy.data.lights.new("ping%d" % i, "POINT"); li.shadow_soft_size = 0.03; li.color = COLS[i]
        lo = C.link(bpy.data.objects.new("ping%d" % i, li), sc); lo.location = source(spk)
        for f, en in [(f0 - 1, 0), (f0, 260), (f0 + 2, 120), (f0 + 14, 0)]:
            li.energy = en
            li.keyframe_insert("energy", frame=f)
        orb_m, orb_e = C.emissive("orb%d" % i, COLS[i], 0)
        for f, s in [(f0 - 1, 0), (f0, 40), (f0 + 10, 3), (f0 + 40, 0)]:
            orb_e.inputs["Strength"].default_value = s
            orb_e.inputs["Strength"].keyframe_insert("default_value", frame=f)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.025, location=source(spk))
        bpy.context.object.data.materials.append(orb_m)
    sx, sy, sz = T.ROOM["seat"]
    cam = C.camera(sc, (sx, sy - 0.35, sz + 0.05), (0.0, y1, 1.25), lens=16)
    n = C.scene_frames("echo")
    C.key(cam, 1, location=(sx, sy - 0.35, sz + 0.05))
    C.key(cam, n, location=(sx + 0.06, sy + 0.15, sz + 0.1))
    C.linear_all(cam)
