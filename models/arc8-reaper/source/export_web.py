"""Export SpiderBot.blend rest geometry for the web demo: per-bone triangle soups (Y-up, +Z forward),
swatch index per triangle, and joint positions. Usage: python3 export_web.py <blend> <out.json>"""
import sys, json, base64, struct
import bpy, bmesh
from mathutils import Vector

blend, out = sys.argv[1], sys.argv[2]
bpy.ops.wm.open_mainfile(filepath=blend)
mesh = bpy.data.objects["SpiderBot_Mesh"]
arm = bpy.data.objects["SpiderBot"]


def cv(v):  # blender (x,y,z), front=-Y  ->  three (x, z, -y), front=+Z
    return [round(v[0], 5), round(v[2], 5), round(-v[1], 5)]


me = mesh.data
bm = bmesh.new(); bm.from_mesh(me)
bmesh.ops.triangulate(bm, faces=bm.faces)
uv = bm.loops.layers.uv.active
dl = bm.verts.layers.deform.active
names = [g.name for g in mesh.vertex_groups]
segs = {}
for f in bm.faces:
    v0 = f.verts[0]; gi = max(v0[dl].items(), key=lambda kv: kv[1])[0]
    u, v = f.loops[0][uv].uv
    col = min(3, int(u * 4)); row = min(3, int((1 - v) * 4)); k = row * 4 + col
    s = segs.setdefault(names[gi], {"p": [], "k": []})
    for vert in f.verts: s["p"].extend(cv(vert.co))
    s["k"].append(k)
data = {"segments": {}, "bones": {}}
for n, s in segs.items():
    data["segments"][n] = {
        "p": base64.b64encode(struct.pack(f"<{len(s['p'])}f", *s["p"])).decode(),
        "k": base64.b64encode(bytes(s["k"])).decode()}
for b in arm.data.bones:
    data["bones"][b.name] = {"h": cv(b.head_local), "t": cv(b.tail_local)}
json.dump(data, open(out, "w"), separators=(",", ":"))
print("segments", len(segs), "tris", sum(len(s["k"]) for s in segs.values()))
