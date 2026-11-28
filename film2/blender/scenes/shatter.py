"""Pressure wave (78-90 s): out of black, a wall of shards bursts towards and past the viewer; the core pulses
with each thump while the shards slow and drift."""
import random
import bpy
from mathutils import Vector
import common as C
from common import T

CYCLES = dict(volume_bounces=1)


def build(sc):
    rnd = random.Random(11)
    n = C.scene_frames("shatter")
    hot = [C.material("shard%d" % i, c, roughness=0.15, metallic=0.9, emission=em, emission_color=c)
           for i, (c, em) in enumerate([((1.0, 0.55, 0.2), 4.0), ((0.3, 0.6, 1.0), 2.5), ((0.9, 0.9, 1.0), 0.0)])]
    bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=0.12, depth=0.02)
    proto = bpy.context.object
    proto.data.materials.append(hot[0])
    centre = Vector((0, 8, 1.2))
    fast, end = 1 + int(0.5 * T.FPS), n
    for i in range(2500):
        o = proto.copy(); C.link(o, sc)
        o.material_slots[0].link = "OBJECT"
        o.material_slots[0].material = hot[rnd.randrange(3)]
        start = centre + Vector((rnd.uniform(-4, 4), rnd.uniform(-0.05, 0.05), rnd.uniform(-2.2, 2.2)))
        d = (start - centre + Vector((0, -2.5, 0))).normalized()
        speed = rnd.uniform(0.4, 1.3)
        s = rnd.uniform(0.4, 2.2)
        o.scale = (s, s, s)
        rot = Vector((rnd.uniform(0, 6), rnd.uniform(0, 6), rnd.uniform(0, 6)))
        spin = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
        C.key(o, 1, location=start, rotation_euler=rot)
        C.key(o, fast, location=start + d * speed * 7, rotation_euler=rot + spin * 8)
        C.key(o, end, location=start + d * speed * 10, rotation_euler=rot + spin * 14)
    bpy.data.objects.remove(proto)
    core, e = C.emissive("core", (1.0, 0.85, 0.65), 0)
    keys = [(1, 60), (12, 4)]
    for t in T.THUMPS:
        f = T.scene_frame("shatter", t)
        keys += [(f - 1, 2.5), (f, 22), (f + 6, 2.5)]
    keys.append((n, 1.5))
    for f, s in keys:
        e.inputs["Strength"].default_value = s
        e.inputs["Strength"].keyframe_insert("default_value", frame=f)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=centre)
    bpy.context.object.data.materials.append(core)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 6, 1))
    hz = bpy.context.object; hz.scale = (30, 20, 12)
    hz.data.materials.append(C.volume("dust", density=0.015, anisotropy=0.4)[0])
    li = bpy.data.lights.new("burst", "POINT"); li.shadow_soft_size = 0.4; li.color = (1.0, 0.8, 0.6)
    lo = C.link(bpy.data.objects.new("burst", li), sc); lo.location = centre
    lk = [(1, 2e4), (12, 1500)]
    for t in T.THUMPS:
        f = T.scene_frame("shatter", t)
        lk += [(f - 1, 700), (f, 6000), (f + 6, 700)]
    for f, en in lk:
        li.energy = en
        li.keyframe_insert("energy", frame=f)
    cam = C.camera(sc, (0, -1.5, 1.2), tuple(centre), lens=24)
    C.key(cam, 1, location=(0, -1.5, 1.2))
    for t in [T.HIT] + T.THUMPS:
        f = T.scene_frame("shatter", t)
        a = 0.09 if t == T.HIT else 0.025
        C.key(cam, max(1, f), location=(rnd.uniform(-a, a), -1.5 + rnd.uniform(-a, a), 1.2 + rnd.uniform(-a, a)))
        C.key(cam, f + 3, location=(0, -1.5, 1.2))
