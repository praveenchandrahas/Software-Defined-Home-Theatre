"""Storm (30-42 s): a cloud deck lit from inside by lightning, seen from below. Strike times and directions from the timeline."""
import random
import bpy
from mathutils import Vector
import common as C
from common import T

CYCLES = dict(volume_bounces=2, volume_step=4.0)
CAM = Vector((0, -5, 1.5))


def cloud_material(n):
    m = bpy.data.materials.new("cloud"); m.use_nodes = True; nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.noise_dimensions = "4D"
    nz.inputs["Scale"].default_value = 0.9; nz.inputs["Detail"].default_value = 12; nz.inputs["Roughness"].default_value = 0.62
    for f, w in [(1, 0.0), (n, 0.35)]:
        nz.inputs["W"].default_value = w
        nz.inputs["W"].keyframe_insert("default_value", frame=f)
    C.linear_all(nt)
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    band = nt.nodes.new("ShaderNodeMapRange"); band.inputs["From Min"].default_value = -1; band.inputs["From Max"].default_value = 0.2
    nt.links.new(sep.outputs["Z"], band.inputs["Value"])
    mul = C.math_node(nt, "MULTIPLY", nz.outputs["Fac"], band.outputs[0])
    ramp = nt.nodes.new("ShaderNodeMapRange"); ramp.inputs["From Min"].default_value = 0.42; ramp.inputs["From Max"].default_value = 0.7
    ramp.inputs["To Max"].default_value = 6.0
    nt.links.new(mul, ramp.inputs["Value"])
    v = nt.nodes.new("ShaderNodeVolumePrincipled")
    v.inputs["Color"].default_value = (0.75, 0.8, 0.95, 1); v.inputs["Anisotropy"].default_value = 0.6
    nt.links.new(ramp.outputs[0], v.inputs["Density"])
    nt.links.new(v.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    return m


def strike_point(az, el):
    """Where a strike sits in the cloud: the sound's direction, with elevation squeezed into the camera's view."""
    el_view = 14 + 0.28 * el
    az_view = max(-40, min(40, az))
    d = Vector(T.polar(az_view, el_view, 1.0))
    t = (22 - CAM.z) / max(d.z, 0.05)
    return CAM + d * min(t, 110)


def bolt(sc, i, top, f0):
    rnd = random.Random(10 + i)
    end = Vector((top.x + rnd.uniform(-6, 6), top.y + rnd.uniform(-8, 4), -2))
    pts = [top]
    n = 46
    for k in range(1, n):
        p = top.lerp(end, k / n)
        p += Vector((rnd.gauss(0, 1.1), rnd.gauss(0, 1.1), rnd.gauss(0, 0.35))) * (1 - abs(k / n - 0.5))
        pts.append(p)
    pts.append(end)
    cu = bpy.data.curves.new("bolt%d" % i, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.07
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for k, p in enumerate(pts):
        sp.points[k].co = (*p, 1)
    ob = C.link(bpy.data.objects.new("bolt%d" % i, cu), sc)
    for f, hide in [(1, True), (f0 - 1, True), (f0, False), (f0 + 5, True)]:
        ob.hide_render = hide
        ob.keyframe_insert("hide_render", frame=f)
    m, e = C.emissive("bolt%d" % i, (0.75, 0.85, 1.0), 0)
    for f, s in [(f0 - 1, 0), (f0, 30), (f0 + 1, 6), (f0 + 2, 22), (f0 + 4, 0)]:
        e.inputs["Strength"].default_value = s
        e.inputs["Strength"].keyframe_insert("default_value", frame=f)
    cu.materials.append(m)


def build(sc):
    n = C.scene_frames("storm")
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 60, 22))
    deck = bpy.context.object; deck.scale = (180, 140, 14)
    deck.data.materials.append(cloud_material(n))
    for i, (t, az, el) in enumerate(T.STRIKES):
        f0 = T.scene_frame("storm", t)
        top = strike_point(az, el)
        bolt(sc, i, top, f0)
        li = bpy.data.lights.new("flash%d" % i, "POINT"); li.shadow_soft_size = 4
        lo = C.link(bpy.data.objects.new("flash%d" % i, li), sc); lo.location = top + Vector((0, 4, -1))
        for f, en in [(f0 - 1, 0), (f0, 2.5e5), (f0 + 1, 6e4), (f0 + 2, 1.8e5), (f0 + 6, 0)]:
            li.energy = en
            li.keyframe_insert("energy", frame=f)
        # a dim afterglow inside the cloud while the thunder rolls
        ag = bpy.data.lights.new("glow%d" % i, "POINT"); ag.shadow_soft_size = 8; ag.color = (0.6, 0.7, 1.0)
        go = C.link(bpy.data.objects.new("glow%d" % i, ag), sc); go.location = top + Vector((0, 6, 1))
        for f, en in [(f0 - 1, 0), (f0 + 3, 9000), (f0 + 40, 0)]:
            ag.energy = en
            ag.keyframe_insert("energy", frame=f)
    moon = bpy.data.lights.new("moon", "SUN"); moon.energy = 0.03; moon.color = (0.6, 0.7, 1.0)
    mo = C.link(bpy.data.objects.new("moon", moon), sc); mo.rotation_euler = (C.deg(40), 0, C.deg(30))
    cam = C.camera(sc, tuple(CAM), (0, 60, 18), lens=18)
    C.key(cam, 1, location=tuple(CAM)); C.key(cam, n, location=(0.5, 2.0, 2.4))
    C.linear_all(cam)
