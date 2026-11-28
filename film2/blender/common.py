"""Shared Blender helpers. Scene-linear units: 1.0 = 100 nits (SDR reference white), 10.0 = 1000 nits."""
import math
import bpy
from mathutils import Vector

FPS = 24


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    w = bpy.data.worlds.new("world")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
    sc.world = w
    return sc


def cycles(sc, res=(1920, 1080), samples=128, motion_blur=True, volume_bounces=1, transmission=8, volume_step=1.0):
    sc.render.engine = "CYCLES"
    c = sc.cycles
    c.device = "CPU"
    c.samples = samples
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.02
    c.use_denoising = True
    c.max_bounces = 8
    c.diffuse_bounces = 2
    c.glossy_bounces = 3
    c.transmission_bounces = transmission
    c.volume_bounces = volume_bounces
    c.transparent_max_bounces = 8
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.blur_glossy = 1.0
    c.volume_step_rate = volume_step
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.use_motion_blur = motion_blur
    sc.render.motion_blur_shutter = 0.5          # 180 degree shutter
    sc.render.image_settings.file_format = "OPEN_EXR"
    sc.render.image_settings.color_depth = "16"
    sc.render.image_settings.exr_codec = "ZIP"
    sc.render.image_settings.color_mode = "RGB"
    sc.view_settings.view_transform = "Standard"  # EXR keeps scene-linear values either way


def eevee(sc, res=(1920, 1080), samples=64, motion_blur=True):
    sc.render.engine = "BLENDER_EEVEE"
    e = sc.eevee
    e.taa_render_samples = samples
    e.use_raytracing = True
    e.volumetric_tile_size = "4"
    e.volumetric_samples = 96
    e.use_volumetric_shadows = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.use_motion_blur = motion_blur
    sc.render.motion_blur_shutter = 0.5
    sc.render.image_settings.file_format = "OPEN_EXR"
    sc.render.image_settings.color_depth = "16"
    sc.render.image_settings.exr_codec = "ZIP"
    sc.render.image_settings.color_mode = "RGB"
    sc.view_settings.view_transform = "Standard"


def material(name, color=(1, 1, 1), emission=0.0, emission_color=None, roughness=0.5, metallic=0.0,
             transmission=0.0, ior=1.45, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = roughness
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Transmission Weight"].default_value = transmission
    p.inputs["IOR"].default_value = ior
    p.inputs["Alpha"].default_value = alpha
    if emission:
        p.inputs["Emission Color"].default_value = (*(emission_color or color), 1)
        p.inputs["Emission Strength"].default_value = emission
    return m


def emissive(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return m, e


def volume(name, density=0.02, color=(1, 1, 1), anisotropy=0.3):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    v = nt.nodes.new("ShaderNodeVolumePrincipled")
    v.inputs["Density"].default_value = density
    v.inputs["Color"].default_value = (*color, 1)
    v.inputs["Anisotropy"].default_value = anisotropy
    nt.links.new(v.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    return m, v


def link(obj, sc=None):
    (sc or bpy.context.scene).collection.objects.link(obj)
    return obj


def camera(sc, loc, target, lens=28.0, fstop=None, focus=None):
    cam = link(bpy.data.objects.new("cam", bpy.data.cameras.new("cam")), sc)
    cam.data.lens = lens
    cam.data.sensor_width = 36
    cam.data.clip_end = 5000
    aim(cam, loc, target)
    if fstop:
        cam.data.dof.use_dof = True
        cam.data.dof.aperture_fstop = fstop
        cam.data.dof.focus_distance = focus or (Vector(target) - Vector(loc)).length
    sc.camera = cam
    return cam


def aim(obj, loc, target):
    obj.location = loc
    d = Vector(target) - Vector(loc)
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def key(obj, frame, **props):
    for k, v in props.items():
        setattr(obj, k, v)
        obj.keyframe_insert(data_path=k, frame=frame)


def linear_keys(obj):
    ad = obj.animation_data
    if ad and ad.action:
        for layer in getattr(ad.action, "layers", []):
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = "LINEAR"
        for fc in getattr(ad.action, "fcurves", []) or []:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"


def deg(x):
    return math.radians(x)
