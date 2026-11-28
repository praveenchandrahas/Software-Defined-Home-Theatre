"""Canyon (50-65 s): a fast flight between walls of glass blades and light strips; things rush past on every side;
the canyon ends and the camera rises into open light as the frame opens to 16:9."""
import random
import bpy
from mathutils import Vector
import common as C
from common import T

CYCLES = dict(volume_bounces=0, transmission=6)
SPEED = 40.0                                   # metres per second
END_Y = SPEED * (T.OPEN[0] - T.CANYON_ENTRY)   # where the walls stop


def cam_pos(t):
    """Camera position at film time t."""
    y = SPEED * (t - T.CANYON_ENTRY)
    rise = max(0.0, t - T.OPEN[0])
    return Vector((0.4 * (y / END_Y), y, 1.2 + 0.8 * rise * rise))


def build(sc):
    rnd = random.Random(7)
    n = C.scene_frames("canyon")
    glass = C.material("glass", (0.85, 0.95, 1.0), roughness=0.04, transmission=1.0, ior=1.5)
    cols = [(0.1, 0.45, 1.0), (1.0, 0.35, 0.08), (0.7, 0.2, 1.0), (0.1, 1.0, 0.7)]
    lights = [C.emissive("strip%d" % i, c, 12)[0] for i, c in enumerate(cols)]
    for i in range(1100):
        side = -1 if i % 2 else 1
        y = rnd.uniform(-10, END_Y + 10)
        x = side * rnd.uniform(2.2, 9.0)
        h = rnd.uniform(1.5, 14)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, h / 2 - 2))
        o = bpy.context.object
        o.scale = (rnd.uniform(0.08, 0.5), rnd.uniform(0.6, 4.0), h)
        o.rotation_euler = (0, rnd.uniform(-0.25, 0.25), rnd.uniform(-0.5, 0.5))
        o.data.materials.append(lights[rnd.randrange(4)] if rnd.random() < 0.16 else glass)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, END_Y / 2 + 200, -2))
    fl = bpy.context.object; fl.scale = (60, END_Y + 600, 1)
    fl.data.materials.append(C.material("floor", (0.02, 0.02, 0.025), roughness=0.08, metallic=0.6))
    # beyond the canyon: a bright horizon of warm light
    sky, _ = C.emissive("exit", (1.0, 0.72, 0.42), 2.2)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, END_Y + 700, 30), rotation=(C.deg(90), 0, 0))
    ex = bpy.context.object; ex.scale = (1400, 140, 1); ex.data.materials.append(sky)
    # things that rush past
    for i, (tp, side) in enumerate(T.PASSES):
        m, _ = C.emissive("flier%d" % i, cols[i % 4], 25)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.18, segments=24, ring_count=12)
        o = bpy.context.object; o.scale = (1, 3.5, 1); o.data.materials.append(m)
        for t in (tp - 2.0, tp + 0.6):
            rel = Vector(T.pass_pos(t, tp, side))
            o.location = cam_pos(t) + rel
            o.keyframe_insert("location", frame=(t - T.CANYON_ENTRY) * T.FPS + 1)
        C.linear_all(o)
    cam = C.camera(sc, tuple(cam_pos(T.CANYON_ENTRY)), (0, 40, 1.6), lens=24, fstop=2.8, focus=12)
    tgt = C.link(bpy.data.objects.new("look", None), sc)
    for k in range(0, n + 1, 6):
        t = T.CANYON_ENTRY + k / T.FPS
        cam.location = cam_pos(t); cam.keyframe_insert("location", frame=k + 1)
        tgt.location = cam_pos(t) + Vector((0, 40, 0.4 + 0.9 * max(0.0, t - T.OPEN[0])))
        tgt.keyframe_insert("location", frame=k + 1)
    tr = cam.constraints.new("TRACK_TO"); tr.target = tgt; tr.track_axis = "TRACK_NEGATIVE_Z"; tr.up_axis = "UP_Y"
    C.linear_all(cam); C.linear_all(tgt)
