"""Export SandLizard.blend as a GLB (skinned mesh + every action, no images) for the web preview.
Usage: python3 export_web.py <SandLizard.blend> <out.glb>"""
import sys
import bpy

blend, out = sys.argv[1], sys.argv[2]
bpy.ops.wm.open_mainfile(filepath=blend)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
arm.animation_data.action = None
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
    if o.type in ('ARMATURE', 'MESH'): o.select_set(True)
bpy.ops.export_scene.gltf(
    filepath=out, export_format='GLB', use_selection=True,
    export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
    export_optimize_animation_size=True, export_skins=True, export_yup=True,
    export_image_format='NONE', export_texcoords=True, export_normals=True,
    export_apply=False)
print("exported", out)
