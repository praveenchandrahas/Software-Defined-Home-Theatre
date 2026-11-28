"""Canyon: flying fast between walls of glass blades with light strips; motion blur and depth of field."""
import random
import bpy
import common as C

CYCLES = dict(volume_bounces=0, transmission=6)


def build(sc):
    rnd = random.Random(7)
    glass = C.material("glass", (0.85, 0.95, 1.0), roughness=0.04, transmission=1.0, ior=1.5)
    cols = [(0.1, 0.45, 1.0), (1.0, 0.35, 0.08), (0.7, 0.2, 1.0), (0.1, 1.0, 0.7)]
    lights = [C.emissive("strip%d" % i, c, 12)[0] for i, c in enumerate(cols)]
    for i in range(420):
        side = -1 if i % 2 else 1
        y = rnd.uniform(0, 260)
        x = side * rnd.uniform(2.2, 9.0)
        h = rnd.uniform(1.5, 14)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, h / 2 - 2))
        o = bpy.context.object
        o.scale = (rnd.uniform(0.08, 0.5), rnd.uniform(0.6, 4.0), h)
        o.rotation_euler = (0, rnd.uniform(-0.25, 0.25), rnd.uniform(-0.5, 0.5))
        if rnd.random() < 0.16:
            o.scale.x = 0.03
            o.data.materials.append(lights[rnd.randrange(len(lights))])
        else:
            o.data.materials.append(glass)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 130, -2))
    fl = bpy.context.object; fl.scale = (40, 300, 1)
    fl.data.materials.append(C.material("floor", (0.02, 0.02, 0.025), roughness=0.08, metallic=0.6))
    # the exit: a bright horizon to fly towards
    sky, e = C.emissive("exit", (1.0, 0.75, 0.45), 6)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 300, 10), rotation=(C.deg(90), 0, 0))
    ex = bpy.context.object; ex.scale = (80, 30, 1); ex.data.materials.append(sky)
    cam = C.camera(sc, (0, 0, 1.2), (0, 40, 1.6), lens=24, fstop=2.8, focus=12)
    C.key(cam, 1, location=(0, 0, 1.2))
    C.key(cam, 72, location=(0.6, 120, 2.0))
    C.linear_keys(cam)
