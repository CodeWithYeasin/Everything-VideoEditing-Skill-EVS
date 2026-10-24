"""Runs INSIDE Blender (called by title3d.py). Builds an animated 3D title and renders
an RGBA PNG sequence. Args come as JSON in the EVE_TITLE_ARGS environment variable.
Tested with Blender 4.5 LTS.
"""
import json
import math
import os
import sys

import bpy

A = json.loads(os.environ["EVE_TITLE_ARGS"])
W, H, FPS = int(A["w"]), int(A["h"]), int(A["fps"])
FRAMES = max(2, int(round(float(A["dur"]) * FPS)))


def hex_rgba(h, a=1.0):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (lin(r), lin(g), lin(b), a)


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, FRAMES
sc.render.film_transparent = A.get("bg", "transparent") == "transparent"
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.render.filepath = os.path.join(A["frames_dir"], "f_")
try:
    sc.view_settings.view_transform = "Standard"
except Exception:
    pass

# ---- world
world = bpy.data.worlds.new("W")
sc.world = world
world.use_nodes = True
bgn = world.node_tree.nodes["Background"]
bgc = A.get("bg", "transparent")
bgn.inputs[0].default_value = hex_rgba(bgc if bgc != "transparent" else "#202024")
bgn.inputs[1].default_value = 0.4 if bgc == "transparent" else 1.0

# ---- text
curve = bpy.data.curves.new("T", "FONT")
curve.body = A["text"]
if A.get("font") and os.path.exists(A["font"]):
    curve.font = bpy.data.fonts.load(A["font"])
curve.align_x, curve.align_y = "CENTER", "CENTER"
curve.extrude = float(A.get("depth", 0.12))
curve.bevel_depth = float(A.get("bevel", 0.018))
curve.bevel_resolution = 3
curve.size = 1.0
obj = bpy.data.objects.new("Title", curve)
sc.collection.objects.link(obj)

style = A.get("style", "glossy")
col = hex_rgba(A.get("color", "#FFD400"))
mat = bpy.data.materials.new("M")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = col
if style == "metal":
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.22
elif style == "glossy":
    bsdf.inputs["Roughness"].default_value = 0.18
    try:
        bsdf.inputs["Coat Weight"].default_value = 0.6
    except KeyError:
        pass
elif style == "clay":
    bsdf.inputs["Roughness"].default_value = 0.85
elif style == "neon":
    bsdf.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1)
    try:
        bsdf.inputs["Emission Color"].default_value = col
        bsdf.inputs["Emission Strength"].default_value = 6.0
    except KeyError:
        bsdf.inputs["Emission"].default_value = col
elif style == "glass":
    bsdf.inputs["Roughness"].default_value = 0.05
    try:
        bsdf.inputs["Transmission Weight"].default_value = 0.9
    except KeyError:
        pass
curve.materials.append(mat)

# fit: measure text size by converting a copy to mesh
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev = obj.evaluated_get(dg)
xs = [v[0] for v in ev.bound_box]
ys = [v[1] for v in ev.bound_box]
tw, th = max(xs) - min(xs), max(ys) - min(ys)
aspect = W / H
cam_angle = math.radians(50) if W >= H else math.radians(70)
vis_h = 2 * math.tan(cam_angle / 2) * 10
vis_w = vis_h * aspect
fill = float(A.get("fill", 0.7))
scale = min(fill * vis_w / max(tw, 1e-3), 0.45 * vis_h / max(th, 1e-3))
obj.scale = (scale, scale, scale)
obj.rotation_euler = (math.radians(90), 0, 0)

# ---- camera + lights
cam_data = bpy.data.cameras.new("C")
cam_data.angle_y = cam_angle
cam_data.sensor_fit = "VERTICAL"
cam = bpy.data.objects.new("Cam", cam_data)
cam.location = (0, -10, 0)
cam.rotation_euler = (math.radians(90), 0, 0)
sc.collection.objects.link(cam)
sc.camera = cam
for name, loc, energy, size in (("Key", (-4, -6, 4), 900, 4), ("Fill", (5, -5, 1), 350, 5), ("Rim", (0, 4, 5), 700, 3)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy, ld.size = energy, size
    lo = bpy.data.objects.new(name, ld)
    lo.location = loc
    sc.collection.objects.link(lo)
    # point at origin
    con = lo.constraints.new("TRACK_TO")
    con.target = obj
    con.track_axis, con.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"

# ---- animation
anim = A.get("anim", "pop")
f_in = max(2, int(FPS * 0.6))
f_out = FRAMES - int(FPS * 0.35)


def key(frame, s=None, rot=None, loc=None):
    if s is not None:
        obj.scale = (scale * s,) * 3
        obj.keyframe_insert("scale", frame=frame)
    if rot is not None:
        obj.rotation_euler = rot
        obj.keyframe_insert("rotation_euler", frame=frame)
    if loc is not None:
        obj.location = loc
        obj.keyframe_insert("location", frame=frame)


R0 = (math.radians(90), 0, 0)
if anim == "pop":
    key(1, s=0.01)
    key(int(f_in * 0.7), s=1.06)
    key(f_in, s=1.0)
    key(f_out, s=1.0)
    key(FRAMES, s=0.01)
elif anim == "spin":
    key(1, s=0.6, rot=(math.radians(90), 0, math.radians(-180)))
    key(f_in, s=1.0, rot=R0)
    key(FRAMES, rot=(math.radians(90), 0, math.radians(12)))
elif anim == "rise":
    key(1, loc=(0, 0, -4), rot=(math.radians(150), 0, 0))
    key(f_in, loc=(0, 0, 0), rot=R0)
    key(f_out, loc=(0, 0, 0.15))
    key(FRAMES, loc=(0, 0, 6))
else:  # float
    key(1, rot=(math.radians(90), 0, math.radians(-15)))
    key(FRAMES, rot=(math.radians(90), 0, math.radians(15)))
if obj.animation_data and obj.animation_data.action:
    act = obj.animation_data.action
    curves = []
    try:
        curves = list(act.fcurves)
    except AttributeError:  # layered actions (Blender 5)
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    curves += list(cb.fcurves)
    for fc in curves:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.easing = "EASE_OUT"

# ---- engine
engine = A.get("engine", "auto")
names = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
eevee = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in names else "BLENDER_EEVEE"
if engine == "cycles":
    sc.render.engine = "CYCLES"
else:
    sc.render.engine = eevee
if sc.render.engine == "CYCLES":
    sc.cycles.samples = int(A.get("samples", 48))
    sc.cycles.use_denoising = True
    sc.cycles.device = "CPU"
else:
    try:
        sc.eevee.taa_render_samples = int(A.get("samples", 32))
    except Exception:
        pass

# neon glow via compositor
if style == "neon":
    try:
        sc.use_nodes = True
        tree = sc.node_tree
        rl = tree.nodes.get("Render Layers") or tree.nodes.new("CompositorNodeRLayers")
        comp = tree.nodes.get("Composite") or tree.nodes.new("CompositorNodeComposite")
        glare = tree.nodes.new("CompositorNodeGlare")
        glare.glare_type = "FOG_GLOW"
        try:
            glare.size = 8
        except Exception:
            pass
        tree.links.new(rl.outputs["Image"], glare.inputs["Image"])
        tree.links.new(glare.outputs["Image"], comp.inputs["Image"])
    except Exception as e:
        print("glare skipped:", e)

print(f"EVE rendering {FRAMES} frames {W}x{H} with {sc.render.engine}", flush=True)
bpy.ops.render.render(animation=True)
print("EVE DONE", flush=True)
