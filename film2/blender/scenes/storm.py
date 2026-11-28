"""Storm: a cloud deck lit from inside by lightning, seen from below."""
import random
import bpy
from mathutils import Vector
import common as C

CYCLES = dict(volume_bounces=2, volume_step=4.0)
STRIKE = 20


def cloud_material():
    m = bpy.data.materials.new("cloud")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.noise_dimensions = "4D"
    nz.inputs["Scale"].default_value = 0.9; nz.inputs["Detail"].default_value = 12; nz.inputs["Roughness"].default_value = 0.62
    nz.inputs["W"].default_value = 0.0
    nz.inputs["W"].keyframe_insert("default_value", frame=1)
    nz.inputs["W"].default_value = 0.25
    nz.inputs["W"].keyframe_insert("default_value", frame=96)
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    # thin the cloud towards its bottom and top so it reads as a layer
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    band = nt.nodes.new("ShaderNodeMapRange"); band.inputs["From Min"].default_value = -1; band.inputs["From Max"].default_value = 0.2
    nt.links.new(sep.outputs["Z"], band.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
    nt.links.new(nz.outputs["Fac"], mul.inputs[0]); nt.links.new(band.outputs[0], mul.inputs[1])
    ramp = nt.nodes.new("ShaderNodeMapRange"); ramp.inputs["From Min"].default_value = 0.42; ramp.inputs["From Max"].default_value = 0.7
    ramp.inputs["To Max"].default_value = 6.0
    nt.links.new(mul.outputs[0], ramp.inputs["Value"])
    v = nt.nodes.new("ShaderNodeVolumePrincipled")
    v.inputs["Color"].default_value = (0.75, 0.8, 0.95, 1); v.inputs["Anisotropy"].default_value = 0.6
    nt.links.new(ramp.outputs[0], v.inputs["Density"])
    nt.links.new(v.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    return m


def bolt(sc, start, end, seed):
    rnd = random.Random(seed)
    pts = [Vector(start)]
    n = 40
    for i in range(1, n):
        p = Vector(start).lerp(Vector(end), i / n)
        p += Vector((rnd.gauss(0, 1.2), rnd.gauss(0, 1.2), rnd.gauss(0, 0.4))) * (1 - abs(i / n - 0.5))
        pts.append(p)
    pts.append(Vector(end))
    cu = bpy.data.curves.new("bolt", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.06
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (*p, 1)
    ob = C.link(bpy.data.objects.new("bolt", cu), sc)
    m, e = C.emissive("bolt", (0.75, 0.85, 1.0), 0)
    for f, s in [(STRIKE - 1, 0), (STRIKE, 30), (STRIKE + 1, 8), (STRIKE + 2, 22), (STRIKE + 4, 0)]:
        e.inputs["Strength"].default_value = s
        e.inputs["Strength"].keyframe_insert("default_value", frame=f)
    cu.materials.append(m)
    return ob


def build(sc):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 60, 22))
    deck = bpy.context.object
    deck.scale = (160, 120, 14)
    deck.data.materials.append(cloud_material())
    bolt(sc, (-14, 70, 26), (-9, 55, -4), 3)
    li = bpy.data.lights.new("flash", "POINT"); li.shadow_soft_size = 3
    lo = C.link(bpy.data.objects.new("flash", li), sc); lo.location = (-12, 66, 20)
    for f, e in [(STRIKE - 1, 0), (STRIKE, 2.5e5), (STRIKE + 1, 6e4), (STRIKE + 2, 1.8e5), (STRIKE + 5, 0)]:
        li.energy = e
        li.keyframe_insert("energy", frame=f)
    moon = bpy.data.lights.new("moon", "SUN"); moon.energy = 0.02; moon.color = (0.6, 0.7, 1.0)
    mo = C.link(bpy.data.objects.new("moon", moon), sc); mo.rotation_euler = (C.deg(40), 0, C.deg(30))
    cam = C.camera(sc, (0, -5, 1.5), (0, 60, 18), lens=18)
    C.key(cam, 1, location=(0, -5, 1.5)); C.key(cam, 96, location=(0, 1, 2.5))
