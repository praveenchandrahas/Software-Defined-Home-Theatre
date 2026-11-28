"""Pressure wave: a wall of shards bursts towards and past the viewer."""
import math, random
import bpy
from mathutils import Vector
import common as C

CYCLES = dict(volume_bounces=1)
HIT = 4


def build(sc):
    rnd = random.Random(11)
    hot = [C.material("shard%d" % i, c, roughness=0.15, metallic=0.9, emission=em, emission_color=c)
           for i, (c, em) in enumerate([((1.0, 0.55, 0.2), 4.0), ((0.3, 0.6, 1.0), 2.5), ((0.9, 0.9, 1.0), 0.0)])]
    bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=0.12, depth=0.02)
    proto = bpy.context.object
    proto.data.materials.append(hot[0])
    centre = Vector((0, 8, 1.2))
    for i in range(2500):
        o = proto.copy(); o.data = proto.data; C.link(o, sc)
        o.material_slots[0].link = "OBJECT"
        o.material_slots[0].material = hot[rnd.randrange(3)]
        start = centre + Vector((rnd.uniform(-4, 4), rnd.uniform(-0.05, 0.05), rnd.uniform(-2.2, 2.2)))
        d = (start - centre + Vector((0, -2.5, 0))).normalized()
        speed = rnd.uniform(0.4, 1.3)
        s = rnd.uniform(0.4, 2.2)
        o.scale = (s, s, s)
        C.key(o, HIT, location=start, rotation_euler=(rnd.uniform(0, 6), rnd.uniform(0, 6), rnd.uniform(0, 6)))
        C.key(o, HIT + 24, location=start + d * speed * 10,
              rotation_euler=(rnd.uniform(-20, 20), rnd.uniform(-20, 20), rnd.uniform(-20, 20)))
        C.linear_keys(o)
    bpy.data.objects.remove(proto)
    core, e = C.emissive("core", (1.0, 0.85, 0.65), 0)
    for f, s in [(HIT - 1, 0), (HIT, 60), (HIT + 10, 4)]:
        e.inputs["Strength"].default_value = s
        e.inputs["Strength"].keyframe_insert("default_value", frame=f)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=centre)
    bpy.context.object.data.materials.append(core)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 6, 1))
    hz = bpy.context.object; hz.scale = (30, 20, 12)
    hz.data.materials.append(C.volume("dust", density=0.015, anisotropy=0.4)[0])
    li = bpy.data.lights.new("burst", "POINT"); li.shadow_soft_size = 0.4; li.color = (1.0, 0.8, 0.6)
    lo = C.link(bpy.data.objects.new("burst", li), sc); lo.location = centre
    for f, en in [(HIT - 1, 0), (HIT, 2e4), (HIT + 12, 1500)]:
        li.energy = en
        li.keyframe_insert("energy", frame=f)
    C.camera(sc, (0, -1.5, 1.2), centre, lens=24)
