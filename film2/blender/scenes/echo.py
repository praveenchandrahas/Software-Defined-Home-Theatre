"""Echo: a ping from the screen spreads through a dark room; the room's edges light up where the wavefront passes.

The room is 3.0 m wide, 3.0 m deep, 2.7 m high (about 10 x 10 ft), seen from the seat."""
import bpy, bmesh
import common as C

CYCLES = dict(volume_bounces=0)
PING = 6           # frame of the ping
SPEED = 3.43 / 24  # metres per frame (sound, slowed 100x so it can be seen)


def wire_box(name, size, loc, thickness=0.006):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    md = o.modifiers.new("w", "WIREFRAME")
    md.thickness = thickness
    md.use_replace = True
    return o


def build(sc):
    src = (0.0, 2.6, 1.0)                                  # the centre speaker, behind the screen plane
    room = wire_box("room", (3.0, 3.0, 2.7), (0, 1.2, 1.35))
    # grid on floor and walls: subdivide so the wave reveals a lattice, not only the corners
    bpy.context.view_layer.objects.active = room
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.subdivide(number_cuts=9)
    bpy.ops.object.mode_set(mode="OBJECT")

    m = bpy.data.materials.new("wave")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    dist = nt.nodes.new("ShaderNodeVectorMath"); dist.operation = "DISTANCE"
    dist.inputs[1].default_value = src
    nt.links.new(geo.outputs["Position"], dist.inputs[0])
    radius = nt.nodes.new("ShaderNodeValue")               # keyframed below
    sub = nt.nodes.new("ShaderNodeMath"); sub.operation = "SUBTRACT"
    nt.links.new(dist.outputs["Value"], sub.inputs[0]); nt.links.new(radius.outputs[0], sub.inputs[1])
    # a sharp front and a slow afterglow behind it
    front = nt.nodes.new("ShaderNodeMath"); front.operation = "MULTIPLY"; front.inputs[1].default_value = -1 / 0.06
    nt.links.new(sub.outputs[0], front.inputs[0])
    sq = nt.nodes.new("ShaderNodeMath"); sq.operation = "MULTIPLY"
    nt.links.new(front.outputs[0], sq.inputs[0]); nt.links.new(front.outputs[0], sq.inputs[1])
    neg = nt.nodes.new("ShaderNodeMath"); neg.operation = "MULTIPLY"; neg.inputs[1].default_value = -1
    nt.links.new(sq.outputs[0], neg.inputs[0])
    ex = nt.nodes.new("ShaderNodeMath"); ex.operation = "EXPONENT"
    nt.links.new(neg.outputs[0], ex.inputs[0])
    behind = nt.nodes.new("ShaderNodeMath"); behind.operation = "LESS_THAN"; behind.inputs[1].default_value = 0
    nt.links.new(sub.outputs[0], behind.inputs[0])
    glow = nt.nodes.new("ShaderNodeMath"); glow.operation = "MULTIPLY"; glow.inputs[1].default_value = 0.025
    nt.links.new(behind.outputs[0], glow.inputs[0])
    tot = nt.nodes.new("ShaderNodeMath"); tot.operation = "MULTIPLY_ADD"; tot.inputs[1].default_value = 6.0
    nt.links.new(ex.outputs[0], tot.inputs[0]); nt.links.new(glow.outputs[0], tot.inputs[2])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.35, 0.65, 1.0, 1)
    nt.links.new(tot.outputs[0], em.inputs["Strength"])
    nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    room.data.materials.append(m)
    for f, r in [(1, -1.0), (PING, 0.0), (PING + 48, 48 * SPEED)]:
        radius.outputs[0].default_value = r
        radius.outputs[0].keyframe_insert("default_value", frame=f)
    for fc in nt.animation_data.action.layers[0].strips[0].channelbags[0].fcurves if hasattr(nt.animation_data.action, "layers") else nt.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"

    # faint haze in the room so the ping's flash has something to light
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1.2, 1.35))
    haze = bpy.context.object
    haze.scale = (3.0, 3.0, 2.7)
    haze.data.materials.append(C.volume("haze", density=0.03, anisotropy=0.5)[0])
    pt = bpy.data.lights.new("ping", "POINT")
    pt.shadow_soft_size = 0.02
    pt.color = (0.5, 0.75, 1.0)
    lo = C.link(bpy.data.objects.new("ping", pt), sc)
    lo.location = src
    for f, e in [(PING - 1, 0), (PING, 400), (PING + 6, 0)]:
        pt.energy = e
        pt.keyframe_insert("energy", frame=f)
    C.camera(sc, (0.0, -0.25, 1.05), (0.0, 2.6, 1.2), lens=20)
