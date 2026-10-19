"""Preview renders for the Sand Lizard.
python3 render_lizard.py <blend> <outdir> <job> ...
jobs: hero | still:<Action>:<frame>:<name>[:view] | gif:<Action>:<every>[:view]
      spin:<Action>:<sign>:<frames>:<every>[:view]  (rotates the lizard at the turn-clip rate while the clip loops)
views: q (3/4 front), side, top, face, low"""
import sys, os
import bpy
from mathutils import Vector

blend, out = sys.argv[1], sys.argv[2]
jobs = sys.argv[3:]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend)
scn = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')

scn.render.engine = 'CYCLES'
scn.cycles.device = 'CPU'
scn.cycles.use_denoising = True
scn.view_settings.view_transform = 'AgX'
scn.view_settings.look = 'AgX - Medium High Contrast'

world = bpy.data.worlds.new("W"); scn.world = world
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.72, 0.8, 0.9, 1); bg.inputs[1].default_value = 0.4

bpy.ops.mesh.primitive_plane_add(size=40)
g = bpy.context.active_object
gm = bpy.data.materials.new("Sand"); gb = gm.node_tree.nodes["Principled BSDF"]
gb.inputs["Base Color"].default_value = (0.62, 0.45, 0.27, 1); gb.inputs["Roughness"].default_value = 0.9
g.data.materials.append(gm)

sun_d = bpy.data.lights.new("Sun", 'SUN'); sun_d.energy = 4.2; sun_d.color = (1.0, 0.9, 0.78); sun_d.angle = 0.05
sun = bpy.data.objects.new("Sun", sun_d); scn.collection.objects.link(sun)
sun.rotation_euler = (0.85, 0.25, 0.9)
fill_d = bpy.data.lights.new("Fill", 'AREA'); fill_d.energy = 6; fill_d.size = 0.6; fill_d.color = (0.7, 0.8, 1.0)
fill = bpy.data.objects.new("Fill", fill_d); scn.collection.objects.link(fill)
fill.location = (-0.6, -0.3, 0.4)
fill.rotation_euler = (Vector((0, 0, 0.04)) - fill.location).to_track_quat('-Z', 'Y').to_euler()

cd = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cd); scn.collection.objects.link(cam)
scn.camera = cam


def aim(loc, tgt=(0, 0.03, 0.04), lens=50):
    cam.location = loc; cd.lens = lens
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


VIEWS = {
    "q": ((0.42, -0.48, 0.26), (0, 0.03, 0.035), 55),
    "side": ((0.75, 0.04, 0.12), (0, 0.04, 0.04), 50),
    "top": ((0.001, 0.05, 0.9), (0, 0.05, 0), 45),
    "topc": ((0.001, 0.0, 1.0), (0, 0.0, 0), 50),
    "face": ((0.10, -0.40, 0.09), (0, -0.14, 0.05), 70),
    "low": ((0.32, -0.42, 0.07), (0, 0.0, 0.05), 50),
}


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
        set_action("Idle", 60)
        aim((0.36, -0.44, 0.13), (0, 0.0, 0.045), 50); render(f"{out}/hero.png", 1400, 1000, 128)
    elif parts[0] == "still":
        _, act, fr, name = parts[:4]
        loc, tgt, lens = VIEWS[parts[4] if len(parts) > 4 else "q"]
        set_action(act, int(fr)); aim(loc, tgt, lens)
        render(f"{out}/{name}.png", 700, 500, 32)
    elif parts[0] == "spin":
        act, sign, n, every = parts[1], int(parts[2]), int(parts[3]), int(parts[4])
        loc, tgt, lens = VIEWS[parts[5] if len(parts) > 5 else "top"]
        f1 = int(bpy.data.actions[act].frame_range[1])
        aim(loc, tgt, lens)
        for f in range(0, n, every):
            arm.rotation_euler = (0, 0, sign * 1.5625 * f / 30)
            set_action(act, f % f1); render(f"{out}/spin_{act}_{f:03d}.png", 480, 480, 12)
        arm.rotation_euler = (0, 0, 0)
    elif parts[0] == "gif":
        act, every = parts[1], int(parts[2])
        loc, tgt, lens = VIEWS[parts[3] if len(parts) > 3 else "q"]
        a = bpy.data.actions[act]; f0, f1 = map(int, a.frame_range)
        aim(loc, tgt, lens)
        for f in range(f0, f1, every):
            set_action(act, f); render(f"{out}/{act}_{f:03d}.png", 560, 400, 12)
