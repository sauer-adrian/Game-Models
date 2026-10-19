"""Preview renders. python3 render.py <blend> <outdir> <job> ...
jobs: hero | sheet | gif:<Action>:<every> | still:<Action>:<frame>:<name>"""
import sys, os, math
import bpy
from mathutils import Vector

blend, out = sys.argv[1], sys.argv[2]
jobs = sys.argv[3:]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend)
scn = bpy.context.scene
arm = bpy.data.objects["SpiderBot"]

scn.render.engine = 'CYCLES'
scn.cycles.device = 'CPU'
scn.cycles.samples = 48
scn.cycles.use_denoising = True
scn.view_settings.view_transform = 'AgX'
scn.view_settings.look = 'AgX - Medium High Contrast'
scn.render.film_transparent = False

world = bpy.data.worlds.new("W"); scn.world = world
wn = world.node_tree.nodes; bg = wn["Background"]
bg.inputs[0].default_value = (0.012, 0.013, 0.016, 1); bg.inputs[1].default_value = 1.0

# ground
bpy.ops.mesh.primitive_plane_add(size=30)
g = bpy.context.active_object
gm = bpy.data.materials.new("Ground"); gb = gm.node_tree.nodes["Principled BSDF"]
gb.inputs["Base Color"].default_value = (0.022, 0.023, 0.026, 1); gb.inputs["Roughness"].default_value = 0.7
g.data.materials.append(gm)


def light(kind, loc, energy, color, size=1.0, rot=None):
    ld = bpy.data.lights.new(kind + str(len(bpy.data.lights)), kind)
    ld.energy = energy; ld.color = color
    if kind == 'AREA': ld.size = size
    ob = bpy.data.objects.new(ld.name, ld); scn.collection.objects.link(ob); ob.location = loc
    tgt = Vector((0, 0, 0.25)); d = tgt - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob


light('AREA', (2.0, -1.6, 2.8), 230, (0.85, 0.9, 1.0), 1.0)
light('AREA', (-2.4, -0.6, 1.0), 25, (0.6, 0.7, 1.0), 2.0)
light('AREA', (-0.8, 2.6, 1.4), 200, (1.0, 0.3, 0.22), 1.0)

cd = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cd); scn.collection.objects.link(cam)
scn.camera = cam; cd.lens = 50


def aim(loc, tgt=(0, 0, 0.22), lens=50):
    cam.location = loc; cd.lens = lens
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


def set_action(name, frame):
    arm.animation_data.action = bpy.data.actions[name]
    if hasattr(arm.animation_data, "action_slot") and arm.animation_data.action_slot is None:
        slots = bpy.data.actions[name].slots
        if len(slots): arm.animation_data.action_slot = slots[0]
    scn.frame_set(frame)


def render(path, w, h, samples):
    scn.render.resolution_x, scn.render.resolution_y = w, h
    scn.cycles.samples = samples; scn.render.filepath = path
    bpy.ops.render.render(write_still=True)


for job in jobs:
    parts = job.split(":")
    if parts[0] == "hero":
        set_action("Idle", 0)
        aim((1.5, -1.85, 0.95), (0, -0.02, 0.18), lens=40); render(f"{out}/hero.png", 1400, 1000, 96)
    elif parts[0] == "still":
        _, act, fr, name = parts[:4]
        view = parts[4] if len(parts) > 4 else "q"
        set_action(act, int(fr))
        if view == "q": aim((1.5, -1.85, 0.95), (0, -0.02, 0.2), lens=40)
        elif view == "side": aim((2.4, 0.0, 0.5), lens=55)
        elif view == "top": aim((0.001, 0.0, 3.0), (0, 0, 0), lens=45)
        elif view == "face": aim((0.25, -0.95, 0.38), (0, -0.3, 0.2), lens=60)
        elif view == "back": aim((-1.3, 1.9, 1.0), lens=48)
        render(f"{out}/{name}.png", 700, 500, 40)
    elif parts[0] == "gif":
        act, every = parts[1], int(parts[2])
        a = bpy.data.actions[act]; f0, f1 = map(int, a.frame_range)
        aim((1.6, -1.6, 0.8), (0, 0, 0.2), lens=40)
        for f in range(f0, f1, every):
            set_action(act, f); render(f"{out}/{act}_{f:03d}.png", 560, 400, 16)
