"""One drop (42-50 s): in black, a single drop falls in slow motion and lands on still, dark water; rings spread."""
import bpy
import common as C
from common import T


def build(sc):
    n = C.scene_frames("drop")
    hit = T.scene_frame("drop", T.DROP_HIT)
    f0 = T.scene_frame("drop", T.DROP_FALL[0])
    # water: glossy dark plane with animated radial ripples as a bump
    bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0))
    water = bpy.context.object
    m = bpy.data.materials.new("water"); m.use_nodes = True; nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (0.002, 0.004, 0.008, 1)
    p.inputs["Roughness"].default_value = 0.03
    p.inputs["Specular IOR Level"].default_value = 0.8
    tc = nt.nodes.new("ShaderNodeTexCoord")
    ln = nt.nodes.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"
    nt.links.new(tc.outputs["Object"], ln.inputs[0])
    r = ln.outputs["Value"]
    front = C.value_node(nt, [(1, 0.0), (hit, 0.0), (n, 0.38)])          # ring radius grows after the hit
    amp = C.value_node(nt, [(1, 0.0), (hit - 1, 0.0), (hit, 1.0), (n, 0.25)])
    phase = C.math_node(nt, "SUBTRACT", r, front.outputs[0])
    wave = C.math_node(nt, "SINE", C.math_node(nt, "MULTIPLY", phase, 2 * 3.14159 / 0.018))
    inside = C.math_node(nt, "LESS_THAN", phase, 0.0)
    decay = C.math_node(nt, "EXPONENT", C.math_node(nt, "MULTIPLY", C.math_node(nt, "ABSOLUTE", phase), -14.0))
    h = C.math_node(nt, "MULTIPLY", C.math_node(nt, "MULTIPLY", C.math_node(nt, "MULTIPLY", wave, inside), decay), amp.outputs[0])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6; bump.inputs["Distance"].default_value = 0.002
    nt.links.new(h, bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    water.data.materials.append(m)
    # the drop, and the jet that rises after it lands
    glassy = C.material("drop", (0.9, 0.95, 1.0), roughness=0.0, transmission=1.0, ior=1.33)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.006, segments=48, ring_count=24)
    d = bpy.context.object; bpy.ops.object.shade_smooth(); d.data.materials.append(glassy)
    d.scale = (1, 1, 1.15)
    C.key(d, 1, location=(0, 0, 0.6))
    C.key(d, f0, location=(0, 0, 0.32))
    C.key(d, hit, location=(0, 0, 0.004))
    C.key(d, hit + 1, location=(0, 0, -0.05))
    C.linear_all(d)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.004, segments=32, ring_count=16)
    jet = bpy.context.object; bpy.ops.object.shade_smooth(); jet.data.materials.append(glassy)
    for f, z, sz in [(hit, -0.02, 0.2), (hit + 6, 0.02, 3.5), (hit + 14, 0.045, 2.5), (hit + 26, 0.01, 1.2), (hit + 34, -0.02, 0.5)]:
        jet.location = (0, 0, z); jet.scale = (1, 1, sz)
        jet.keyframe_insert("location", frame=f); jet.keyframe_insert("scale", frame=f)
    # light: a cool soft key behind and a thin warm rim
    key = bpy.data.lights.new("key", "AREA"); key.energy = 3; key.size = 1.2; key.color = (0.7, 0.85, 1.0)
    ko = C.link(bpy.data.objects.new("key", key), sc); C.aim(ko, (0.6, 0.9, 0.9), (0, 0, 0))
    rim = bpy.data.lights.new("rim", "AREA"); rim.energy = 6; rim.size = 0.15; rim.color = (1.0, 0.75, 0.5)
    ro = C.link(bpy.data.objects.new("rim", rim), sc); C.aim(ro, (-0.5, 0.6, 0.15), (0, 0, 0.02))
    for li, peak in ((key, 3), (rim, 1.5)):
        for f, en in [(1, 0), (f0 - 24, 0), (f0, peak), (n, peak)]:
            li.energy = en
            li.keyframe_insert("energy", frame=f)
    cam = C.camera(sc, (0, -0.32, 0.07), (0, 0, 0.03), lens=85, fstop=2.0, focus=0.32)
    C.key(cam, 1, location=(0, -0.32, 0.07)); C.key(cam, n, location=(0.01, -0.29, 0.065))
    C.linear_all(cam)
