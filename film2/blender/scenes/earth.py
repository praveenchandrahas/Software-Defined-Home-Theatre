"""Orbit: sunrise over the Earth's limb, from about 420 km up. Procedural surface for the test; NASA textures in the film."""
import math
import bpy
import common as C

CYCLES = dict(volume_bounces=1, volume_step=2.0)
R = 64.0      # Earth radius in scene units (1 unit = 100 km)
H = 4.2       # altitude


def sun_rotation(elev_deg):
    """Rotation about X for a sun in the +Y direction at this elevation (seen from the camera)."""
    e = math.radians(elev_deg)
    return math.atan2(-math.cos(e), math.sin(e))


def build(sc):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=R, segments=256, ring_count=128)
    e = bpy.context.object
    bpy.ops.object.shade_smooth()
    m = bpy.data.materials.new("earth"); m.use_nodes = True; nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.06; nz.inputs["Detail"].default_value = 14
    tc = nt.nodes.new("ShaderNodeTexCoord"); nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.52; cr.color_ramp.elements[0].color = (0.005, 0.02, 0.06, 1)
    cr.color_ramp.elements[1].position = 0.55; cr.color_ramp.elements[1].color = (0.06, 0.05, 0.03, 1)
    nt.links.new(nz.outputs["Fac"], cr.inputs["Fac"]); nt.links.new(cr.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.35
    e.data.materials.append(m)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=R * 1.003, segments=256, ring_count=128)
    cl = bpy.context.object; bpy.ops.object.shade_smooth()
    cm = bpy.data.materials.new("clouds"); cm.use_nodes = True; ct = cm.node_tree
    cp = ct.nodes["Principled BSDF"]
    cn = ct.nodes.new("ShaderNodeTexNoise"); cn.inputs["Scale"].default_value = 0.35; cn.inputs["Detail"].default_value = 15
    cr2 = ct.nodes.new("ShaderNodeMapRange"); cr2.inputs["From Min"].default_value = 0.52; cr2.inputs["From Max"].default_value = 0.7
    ct.links.new(cn.outputs["Fac"], cr2.inputs["Value"]); ct.links.new(cr2.outputs[0], cp.inputs["Alpha"])
    cl.data.materials.append(cm)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=R * 1.02, segments=256, ring_count=128)
    at = bpy.context.object; bpy.ops.object.shade_smooth()
    at.data.materials.append(C.volume("air", density=0.06, color=(0.25, 0.5, 1.0), anisotropy=0.75)[0])
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 30; sun.angle = C.deg(0.53)
    so = C.link(bpy.data.objects.new("sun", sun), sc)
    disc, _ = C.emissive("sundisc", (1.0, 0.95, 0.88), 400)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=2000 * math.tan(C.deg(0.27)), segments=32, ring_count=16)
    sd = bpy.context.object; sd.data.materials.append(disc)
    cam_z = R + H
    for f, el in [(1, -21.5), (96, -18.5)]:
        so.rotation_euler = (sun_rotation(el), 0, 0)
        so.keyframe_insert("rotation_euler", index=0, frame=f)
        sd.location = (0, 2000 * math.cos(C.deg(el)), cam_z + 2000 * math.sin(C.deg(el)))
        sd.keyframe_insert("location", frame=f)
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (1, 1, 1, 1)
    sky = sc.world.node_tree
    st = sky.nodes.new("ShaderNodeTexVoronoi"); st.inputs["Scale"].default_value = 900
    cr3 = sky.nodes.new("ShaderNodeMapRange"); cr3.inputs["From Min"].default_value = 0.0; cr3.inputs["From Max"].default_value = 0.035
    cr3.inputs["To Min"].default_value = 0.6; cr3.inputs["To Max"].default_value = 0.0
    sky.links.new(st.outputs["Distance"], cr3.inputs["Value"])
    sky.links.new(cr3.outputs[0], bg.inputs["Strength"])
    dip = math.degrees(math.acos(R / cam_z))
    C.camera(sc, (0, 0, cam_z), (0, 100, cam_z - 100 * math.tan(C.deg(dip - 4))), lens=28)
