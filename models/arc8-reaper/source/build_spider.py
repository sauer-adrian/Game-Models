"""ARC-8 'Reaper' Crawler v2 — menacing low-poly mech spider (Synty-style), rigged + animated, FBX for Unity.
Run: python3 build_spider_v2.py <out_dir>"""
import sys, os, math, random
from collections import defaultdict
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion
import numpy as np
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(OUT, "Textures")
os.makedirs(TEX, exist_ok=True)
for f in os.listdir(TEX): os.remove(os.path.join(TEX, f))
random.seed(13)

# ---------------------------------------------------------------- palette atlas
GRID, TS = 4, 512
SW = dict(DARK=0, MID=1, LIGHT=2, CHROME=3, BRASS=4, ACCENT=5, GLOW=6, EYE=7, RUBBER=8, DARK2=9, BLADE=10)
PALETTES = {
    "Obsidian": dict(DARK=(13, 14, 17), MID=(54, 58, 66), LIGHT=(108, 114, 124), CHROME=(168, 172, 180),
                     BRASS=(58, 46, 38), ACCENT=(96, 12, 10), GLOW=(255, 34, 18), EYE=(255, 24, 10),
                     RUBBER=(6, 6, 7), DARK2=(26, 28, 32), BLADE=(196, 200, 208)),
    "Rust": dict(DARK=(30, 22, 18), MID=(82, 46, 28), LIGHT=(128, 84, 52), CHROME=(160, 146, 128),
                 BRASS=(70, 54, 30), ACCENT=(46, 48, 30), GLOW=(255, 120, 10), EYE=(255, 150, 20),
                 RUBBER=(12, 9, 8), DARK2=(48, 34, 26), BLADE=(170, 156, 136)),
    "Void": dict(DARK=(10, 10, 14), MID=(30, 30, 40), LIGHT=(62, 62, 80), CHROME=(150, 150, 170),
                 BRASS=(40, 34, 52), ACCENT=(60, 20, 90), GLOW=(150, 60, 255), EYE=(200, 90, 255),
                 RUBBER=(5, 5, 7), DARK2=(20, 20, 28), BLADE=(180, 180, 200)),
}
GLOWS = {"GLOW", "EYE"}
METAL = dict(DARK=(0.85, 0.5), MID=(0.9, 0.55), LIGHT=(0.9, 0.6), CHROME=(1.0, 0.85), BRASS=(1.0, 0.6),
             ACCENT=(0.6, 0.5), GLOW=(0.0, 0.8), EYE=(0.0, 0.9), RUBBER=(0.0, 0.15), DARK2=(0.8, 0.45),
             BLADE=(1.0, 0.9))
cell = TS // GRID


def swatch_px(k): return (k % GRID) * cell, (k // GRID) * cell


def make_textures():
    for pname, pal in PALETTES.items():
        alb = np.zeros((TS, TS, 3), np.uint8); em = np.zeros((TS, TS, 3), np.uint8)
        for key, k in SW.items():
            x, y = swatch_px(k); c = np.array(pal[key], float)
            g = np.linspace(1.08, 0.92, cell)[:, None, None]
            alb[y:y + cell, x:x + cell] = np.clip(c[None, None, :] * g, 0, 255)
            if key in GLOWS: em[y:y + cell, x:x + cell] = pal[key]
        Image.fromarray(alb).save(f"{TEX}/T_SpiderBot_{pname}_Albedo.png")
        Image.fromarray(em).save(f"{TEX}/T_SpiderBot_{pname}_Emission.png")
    ms = np.zeros((TS, TS, 4), np.uint8)
    for key, k in SW.items():
        x, y = swatch_px(k); m, s = METAL[key]
        ms[y:y + cell, x:x + cell] = (int(m * 255), 0, 0, int(s * 255))
    Image.fromarray(ms, "RGBA").save(f"{TEX}/T_SpiderBot_MetallicSmoothness.png")


def swatch_uv(key):
    k = SW[key]; return ((k % GRID) + 0.5) / GRID, 1.0 - ((k // GRID) + 0.5) / GRID


bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene; scn.render.fps = 30
coll = scn.collection
parts = []


def frame_from(origin, zdir, xhint):
    Z = Vector(zdir).normalized(); X = Vector(xhint)
    X = (X - Z * X.dot(Z)).normalized(); Y = Z.cross(X)
    M = Matrix.Identity(4)
    for i in range(3): M[i][0], M[i][1], M[i][2], M[i][3] = X[i], Y[i], Z[i], origin[i]
    return M


def finish(bm, name, key, bone):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    uvl = me.uv_layers.new(name="UVMap"); u, v = swatch_uv(key)
    for d in uvl.data: d.uv = (u, v)
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    ob.vertex_groups.new(name=bone).add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    parts.append(ob); return ob


def box(name, size, M, key, bone, bevel=0.0, taper=(1, 1), z0=False, shift=(0, 0)):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
        if v.co.z > 0:
            v.co.x = v.co.x * taper[0] + shift[0]; v.co.y = v.co.y * taper[1] + shift[1]
        if z0: v.co.z += size[2] / 2
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.verts) + list(bm.edges), offset=bevel, segments=1,
                        profile=0.5, affect='EDGES', clamp_overlap=True)
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    return finish(bm, name, key, bone)


def cyl(name, r, depth, M, key, bone, seg=8, r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r,
                          radius2=r if r2 is None else r2, depth=depth)
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    return finish(bm, name, key, bone)


def T(p): return Matrix.Translation(Vector(p))


def seg(name, a, b, w, h, key, bone, taper=(1, 1), bevel=0.0, xhint=(1, 0, 0), extend=0.0, shift=(0, 0)):
    a, b = Vector(a), Vector(b); d = b - a
    M = frame_from(a - d.normalized() * extend, d, xhint)
    return box(name, (w, h, d.length + extend * 2), M, key, bone, bevel, taper, z0=True, shift=shift)


def spike(name, base, direction, length, w, key, bone, xhint=(1, 0, 0), h=None):
    base = Vector(base); d = Vector(direction).normalized()
    return seg(name, base - d * 0.01, base + d * length, w, h or w, key, bone, taper=(0.06, 0.06), xhint=xhint)


H = 0.20
UP = Vector((0, 0, 1))

# ---- thorax (Body): low, wide armoured carapace with swept-back spines
box("Thorax", (0.34, 0.36, 0.10), T((0, 0, H)), "DARK", "Body", bevel=0.028)
box("Carapace", (0.30, 0.33, 0.05), T((0, 0.0, H + 0.065)), "MID", "Body", bevel=0.012, taper=(0.62, 0.78))
box("CarapaceRidge", (0.07, 0.30, 0.03), T((0, 0.01, H + 0.095)), "DARK2", "Body", bevel=0.008, taper=(0.4, 0.9))
for i, (y, L) in enumerate(((-0.09, 0.06), (-0.01, 0.08), (0.07, 0.07))):
    spike(f"ThoraxSpine{i}", (0, y, H + 0.10), (0, 0.9, 1.0), L, 0.03, "LIGHT", "Body", h=0.022)
for s in (1, -1):
    box(f"SideArmor{s}", (0.03, 0.30, 0.06), T((s * 0.16, 0, H + 0.02)), "MID", "Body", bevel=0.008,
        taper=(0.6, 0.85))
    for k, y in enumerate((-0.09, 0.0, 0.09)):
        box(f"Vent{s}{k}", (0.012, 0.035, 0.008), T((s * 0.176, y, H + 0.0)), "GLOW", "Body")
box("Belly", (0.24, 0.26, 0.04), T((0, 0, H - 0.065)), "DARK2", "Body", bevel=0.01)
box("BellyGlow", (0.10, 0.14, 0.01), T((0, 0, H - 0.087)), "GLOW", "Body")
cyl("Pedicel", 0.045, 0.10, frame_from((0, 0.17, H + 0.01), (0, 1, 0), (1, 0, 0)), "DARK2", "Body")

# ---- head: low wedge, angry V-brow, slit eyes + diamond eye cluster
box("Neck", (0.12, 0.08, 0.06), T((0, -0.19, H)), "DARK2", "Head", bevel=0.01)
seg("HeadBlock", (0, -0.16, H + 0.005), (0, -0.345, H - 0.01), 0.20, 0.10, "DARK", "Head",
    taper=(0.58, 0.62), bevel=0.014, shift=(0, -0.006))
seg("HeadCrest", (0, -0.17, H + 0.05), (0, -0.30, H + 0.03), 0.05, 0.03, "MID", "Head", taper=(0.4, 0.6))
for s in (1, -1):
    # V-brow: outer end high/back, inner end low/front -> scowl
    seg(f"Brow{s}", (s * 0.085, -0.22, H + 0.06), (s * 0.012, -0.335, H + 0.022), 0.05, 0.022, "MID", "Head",
        taper=(0.6, 0.7), bevel=0.004)
    spike(f"BrowHorn{s}", (s * 0.08, -0.215, H + 0.06), (s * 0.5, 0.8, 0.55), 0.07, 0.022, "LIGHT", "Head")
    # main slit eye, slanted under the brow
    seg(f"EyeSlit{s}", (s * 0.012, -0.344, H + 0.002), (s * 0.052, -0.322, H + 0.018), 0.012, 0.012, "EYE",
        "Head", xhint=(0, -1, 0))
    eye = lambda nm, x, y, z, r, d: cyl(nm, r, 0.012, frame_from((x, y, z), d, (1, 0, 0)), "EYE", "Head", seg=4)
    eye(f"EyeA{s}", s * 0.072, -0.285, H + 0.028, 0.010, (s * 0.5, -1, 0.5))
    eye(f"EyeB{s}", s * 0.040, -0.300, H + 0.040, 0.008, (s * 0.2, -1, 0.9))
    eye(f"EyeC{s}", s * 0.090, -0.255, H + 0.016, 0.008, (s * 1, -0.6, 0.2))

# ---- chelicerae (big serrated fangs) + pedipalps
mand, palp = {}, {}
for s, side in ((1, "R"), (-1, "L")):
    base = Vector((s * 0.035, -0.325, H - 0.03))
    mid = base + Vector((s * 0.03, -0.065, -0.055))
    tip = mid + Vector((-s * 0.05, -0.03, -0.065))
    seg(f"Chel{side}", base, mid, 0.045, 0.05, "DARK2", f"Mandible_{side}", taper=(0.75, 0.75), bevel=0.006,
        extend=0.01)
    seg(f"Fang{side}", mid, tip, 0.034, 0.03, "BLADE", f"Mandible_{side}", taper=(0.05, 0.05), extend=0.006)
    for k, t_ in enumerate((0.3, 0.6)):
        spike(f"Tooth{side}{k}", base.lerp(mid, t_), (-s, -0.3, -0.2), 0.022, 0.012, "BLADE", f"Mandible_{side}")
    mand[side] = (base, mid)
    pb0 = Vector((s * 0.075, -0.30, H - 0.015)); pb1 = pb0 + Vector((s * 0.035, -0.08, 0.035))
    pb2 = pb1 + Vector((-s * 0.005, -0.05, -0.07))
    seg(f"PalpA{side}", pb0, pb1, 0.02, 0.022, "MID", f"Palp_{side}", taper=(0.8, 0.8), extend=0.005)
    seg(f"PalpB{side}", pb1, pb2, 0.018, 0.018, "DARK", f"Palp_{side}", taper=(0.2, 0.2), extend=0.005)
    palp[side] = (pb0, pb1)

# ---- abdomen: glowing core showing between overlapping armour bands, dorsal spines
ABD = "Abdomen"
box("AbdCore", (0.20, 0.34, 0.13), T((0, 0.375, H + 0.06)), "GLOW", ABD, bevel=0.02)
for nm, y, sx, sy, sz, zc in (("A", 0.255, 0.25, 0.10, 0.16, 0.05), ("B", 0.37, 0.31, 0.115, 0.20, 0.07),
                              ("C", 0.485, 0.25, 0.10, 0.165, 0.06)):
    box(f"Abd{nm}", (sx, sy, sz), T((0, y, H + zc)), "DARK", ABD, bevel=0.024, taper=(0.82, 0.9))
    box(f"AbdPlate{nm}", (sx * 0.62, sy * 0.92, 0.03), T((0, y, H + zc + sz / 2 + 0.005)), "MID", ABD,
        bevel=0.008, taper=(0.6, 0.85))
seg("AbdTail", (0, 0.53, H + 0.06), (0, 0.66, H + 0.02), 0.17, 0.12, "DARK2", ABD, taper=(0.12, 0.2), bevel=0.01)
for i, (y, z, L) in enumerate(((0.25, 0.16, 0.07), (0.37, 0.20, 0.10), (0.485, 0.175, 0.08), (0.58, 0.10, 0.06))):
    spike(f"AbdSpine{i}", (0, y, H + z), (0, 0.8, 1.0), L, 0.035, "LIGHT", ABD, h=0.024)
for s in (1, -1):
    spike(f"AbdSideSpike{s}", (s * 0.14, 0.37, H + 0.12), (s * 1, 0.6, 0.7), 0.075, 0.03, "LIGHT", ABD)
    box(f"AbdTrim{s}", (0.012, 0.09, 0.016), T((s * 0.152, 0.37, H + 0.07)), "ACCENT", ABD)

# ---- legs: high spiked knees, blade tibias, needle feet
LEG_ANG_R = [-50, -17, 17, 48]
LEG_Y = [-0.13, -0.045, 0.045, 0.13]
LEG_S = [1.2, 1.0, 1.0, 1.15]
legs = []
for side, sx in (("L", -1), ("R", 1)):
    for i in range(4):
        th = math.radians(LEG_ANG_R[i])
        o = Vector((sx * math.cos(th), math.sin(th), 0)); t = UP.cross(o)
        A = Vector((sx * 0.155, LEG_Y[i], H)); s = LEG_S[i]
        P = lambda r, z: A + o * r + UP * z
        rB, zB = 0.06, 0.02
        el = math.radians(62); fl = 0.30 * s
        rC, zC = rB + fl * math.cos(el), zB + fl * math.sin(el)
        rE, zE = rC + 0.30 * s, -H
        rD, zD = rE - 0.035, -H + 0.095
        B, C, D, E = P(rB, zB), P(rC, zC), P(rD, zD), P(rE, zE)
        n = f"{side}{i + 1}"
        legs.append(dict(name=n, side=sx, o=o, t=t, A=A, B=B, C=C, D=D, E=E, idx=i, lever=(rE - rB),
                         group=("A" if (i % 2 == 0) == (side == "L") else "B")))
        bc, bf, bt, bfo = f"Leg_{n}_Coxa", f"Leg_{n}_Femur", f"Leg_{n}_Tibia", f"Leg_{n}_Foot"
        cyl(f"Hip{n}", 0.034, 0.06, T(A), "DARK2", "Body")
        seg(f"Coxa{n}", A, B, 0.05, 0.045, "DARK", bc, bevel=0.006, xhint=t)
        cyl(f"HipAxle{n}", 0.026, 0.06, frame_from(B, t, o), "DARK2", bf, seg=6)
        fd = (C - B).normalized(); top = fd.cross(t).normalized()
        if top.z < 0: top = -top
        seg(f"Femur{n}", B, C, 0.05, 0.062, "MID", bf, taper=(0.75, 0.6), bevel=0.007, xhint=t, extend=0.01)
        seg(f"FemurArmor{n}", B + fd * 0.04 + top * 0.022, C - fd * 0.05 + top * 0.016, 0.058, 0.018, "DARK",
            bf, taper=(0.7, 1), xhint=t)
        for k, ft in enumerate((0.35, 0.65)):
            spike(f"FemurSpike{n}{k}", B.lerp(C, ft) + top * 0.03, top * 1.0 - fd * 0.7, 0.05 - k * 0.01, 0.02,
                  "LIGHT", bf, xhint=t)
        pa, pb = B + fd * 0.06 - top * 0.034, C - fd * 0.06 - top * 0.026
        cyl(f"PistonHouse{n}", 0.013, fl * 0.36, frame_from(pa.lerp(pb, 0.25), pb - pa, t), "DARK", bf, seg=6)
        cyl(f"PistonRod{n}", 0.007, fl * 0.72, frame_from(pa.lerp(pb, 0.5), pb - pa, t), "CHROME", bf, seg=6)
        td = (D - C).normalized(); ty = td.cross(t).normalized()
        if ty.dot(o) < 0: ty = -ty  # ty = outer (back) edge of the blade
        tl = (D - C).length
        cyl(f"KneeAxle{n}", 0.028, 0.064, frame_from(C, t, o), "DARK2", bt, seg=6)
        spike(f"KneeSpike{n}", C + fd * 0.01, fd * 1.0 + UP * 0.6, 0.085, 0.032, "BLADE", bt, xhint=t)
        # blade tibia: thin across t, wide in the leg plane
        seg(f"Tibia{n}", C, D, 0.026, 0.07, "DARK", bt, taper=(0.7, 0.4), bevel=0.004, xhint=t, extend=0.012)
        seg(f"TibiaEdge{n}", C + td * 0.05 - ty * 0.032, D - ty * 0.012, 0.012, 0.014, "BLADE", bt,
            taper=(0.6, 0.4), xhint=t)
        seg(f"TibiaGlow{n}", C + td * 0.06 + ty * 0.034, C + td * (tl * 0.5) + ty * 0.022, 0.009, 0.006, "GLOW", bt,
            xhint=t)
        for k, tt in enumerate((0.3, 0.48, 0.66)):
            spike(f"TibiaTooth{n}{k}", C.lerp(D, tt) - ty * 0.025, -ty * 1.0 + td * 0.8, 0.03, 0.014, "BLADE", bt,
                  xhint=t)
        cyl(f"AnkleAxle{n}", 0.016, 0.034, frame_from(D, t, o), "DARK2", bfo, seg=6)
        seg(f"Foot{n}", D, E, 0.026, 0.032, "BLADE", bfo, taper=(0.04, 0.04), xhint=t, extend=0.01)

# ---------------------------------------------------------------- join mesh
bpy.ops.object.select_all(action='DESELECT')
for p in parts: p.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
mesh = bpy.context.active_object; mesh.name = "SpiderBot_Mesh"; mesh.data.name = "SpiderBot_Mesh"
for poly in mesh.data.polygons: poly.use_smooth = False
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.00005); bpy.ops.object.mode_set(mode='OBJECT')

make_textures()
mat = bpy.data.materials.new("M_SpiderBot_Obsidian")
nt = mat.node_tree; nodes = nt.nodes; bsdf = nodes["Principled BSDF"]


def img_node(path, noncolor=False):
    n = nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(path); n.interpolation = 'Closest'
    if noncolor: n.image.colorspace_settings.name = 'Non-Color'
    return n


ta = img_node(f"{TEX}/T_SpiderBot_Obsidian_Albedo.png")
te = img_node(f"{TEX}/T_SpiderBot_Obsidian_Emission.png")
tm = img_node(f"{TEX}/T_SpiderBot_MetallicSmoothness.png", True)
nt.links.new(ta.outputs["Color"], bsdf.inputs["Base Color"])
nt.links.new(te.outputs["Color"], bsdf.inputs["Emission Color"]); bsdf.inputs["Emission Strength"].default_value = 6.0
sep = nodes.new("ShaderNodeSeparateColor"); nt.links.new(tm.outputs["Color"], sep.inputs[0])
nt.links.new(sep.outputs["Red"], bsdf.inputs["Metallic"])
inv = nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
nt.links.new(tm.outputs["Alpha"], inv.inputs[1]); nt.links.new(inv.outputs[0], bsdf.inputs["Roughness"])
mesh.data.materials.append(mat)

# ---------------------------------------------------------------- armature
arm_data = bpy.data.armatures.new("SpiderBot_Armature")
arm = bpy.data.objects.new("SpiderBot", arm_data); coll.objects.link(arm)
bpy.context.view_layer.objects.active = arm; arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones


def bone(name, h, t, parent=None, connect=False):
    b = eb.new(name); b.head = Vector(h); b.tail = Vector(t); b.roll = 0
    if parent: b.parent = eb[parent]; b.use_connect = connect
    return b


bone("Root", (0, 0, 0), (0, -0.15, 0))
bone("Body", (0, 0, H), (0, -0.14, H), "Root")
bone("Head", (0, -0.18, H + 0.005), (0, -0.32, H), "Body")
bone("Abdomen", (0, 0.17, H + 0.01), (0, 0.55, H + 0.05), "Body")
for side in ("L", "R"):
    bone(f"Mandible_{side}", *mand[side], "Head")
    bone(f"Palp_{side}", *palp[side], "Head")
for L in legs:
    n = L["name"]
    bone(f"Leg_{n}_Coxa", L["A"], L["B"], "Body")
    bone(f"Leg_{n}_Femur", L["B"], L["C"], f"Leg_{n}_Coxa", True)
    bone(f"Leg_{n}_Tibia", L["C"], L["D"], f"Leg_{n}_Femur", True)
    bone(f"Leg_{n}_Foot", L["D"], L["E"], f"Leg_{n}_Tibia", True)
bpy.ops.object.mode_set(mode='OBJECT')
mesh.parent = arm
mesh.modifiers.new("Armature", 'ARMATURE').object = arm
arm_data.display_type = 'STICK'

# ---------------------------------------------------------------- animation
REST = {b.name: b.matrix_local.to_3x3() for b in arm_data.bones}
REST_INV = {k: v.inverted() for k, v in REST.items()}
BODY_C = Vector((0, 0, H))
NOSE_UP = Vector((-1, 0, 0)); ROLL_R = Vector((0, 1, 0))


class Pose:
    def __init__(self):
        self.q = defaultdict(Quaternion); self.body_rot = Quaternion(); self.body_loc = Vector()
        self.planted = {L["name"]: True for L in legs}

    def rot(self, b, axis, ang):
        ax = (REST_INV[b] @ Vector(axis)).normalized(); self.q[b] = self.q[b] @ Quaternion(ax, ang)

    def body(self, axis, ang): self.body_rot = Quaternion(Vector(axis), ang) @ self.body_rot
    def lift(self, L, a): self.rot(f"Leg_{L['name']}_Femur", -L["t"], a)
    def curl(self, L, a): self.rot(f"Leg_{L['name']}_Tibia", L["t"], a)
    def foot(self, L, a): self.rot(f"Leg_{L['name']}_Foot", L["t"], a)
    def yaw(self, L, a): self.rot(f"Leg_{L['name']}_Coxa", UP, a)
    def swing(self, L, s): self.yaw(L, s * (1 if L["side"] < 0 else -1))

    def mand(self, a):
        for side, sx in (("L", -1), ("R", 1)): self.rot(f"Mandible_{side}", (0, -sx, 0), a)

    def palp(self, a_l, a_r):
        self.rot("Palp_L", NOSE_UP, a_l); self.rot("Palp_R", NOSE_UP, a_r)

    def apply(self, pb_map):
        R = self.body_rot.to_matrix()
        for L in legs:
            if not self.planted[L["name"]]: continue
            A2 = BODY_C + R @ (L["A"] - BODY_C) + self.body_loc
            self.lift(L, -math.asin(max(-0.9, min(0.9, (A2.z - L["A"].z) / L["lever"]))))
        for name, pb in pb_map.items():
            pb.rotation_quaternion = self.q[name] if name in self.q else Quaternion(); pb.location = (0, 0, 0)
        pb = pb_map["Body"]
        pb.rotation_quaternion = (REST_INV["Body"] @ R @ REST["Body"]).to_quaternion()
        pb.location = REST_INV["Body"] @ self.body_loc


PB = {pb.name: pb for pb in arm.pose.bones}
for pb in PB.values(): pb.rotation_mode = 'QUATERNION'
arm.animation_data_create()
CLIPS = {}


def _fcurves(act):
    if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])): return list(act.fcurves)
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags: out.extend(cb.fcurves)
    return out


def record(name, frames, fn, every=1, interp='LINEAR'):
    act = bpy.data.actions.new(name); act.use_fake_user = True
    arm.animation_data.action = act
    keys = frames if isinstance(frames, list) else list(range(0, frames + 1, every))
    for f in keys:
        p = Pose(); fn(p, f); p.apply(PB)
        for pb in PB.values():
            pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
            pb.keyframe_insert("location", frame=f, group=pb.name)
    for fc in _fcurves(act):
        for kp in fc.keyframe_points: kp.interpolation = interp
    act.frame_range = (keys[0], keys[-1]); CLIPS[name] = (keys[0], keys[-1])


smooth = lambda x: x * x * (3 - 2 * x)
TAU = math.tau


def held(f, period, keys, snap=3):
    """sample-and-hold with fast snaps -> twitchy, mechanical motion (loops over period)"""
    n = len(keys); step = period / n
    i = int(f // step) % n; local = f - (f // step) * step
    prev = keys[i - 1]; cur = keys[i]
    return prev + (cur - prev) * smooth(min(1.0, local / snap))


def gait(p, f, period, amp, lift, curl, bob, roll=0.02, pitch=0.0, mand=0.0):
    u = f / period
    p.body_loc = Vector((0, 0, bob * math.cos(2 * TAU * u)))
    p.body(ROLL_R, roll * math.sin(TAU * u)); p.body(NOSE_UP, pitch)
    p.rot("Abdomen", NOSE_UP, 0.03 * math.sin(2 * TAU * u + 0.8)); p.rot("Abdomen", UP, 0.05 * math.sin(TAU * u))
    p.rot("Head", UP, -0.04 * math.sin(TAU * u)); p.rot("Head", NOSE_UP, -0.06)
    p.mand(mand * (0.5 + 0.5 * math.sin(4 * TAU * u)))
    p.palp(0.2 * math.sin(TAU * u), 0.2 * math.sin(TAU * u + math.pi))
    for L in legs:
        uu = (u + (0.0 if L["group"] == "A" else 0.5)) % 1.0
        if uu < 0.5: s, h = 1 - 4 * uu, 0.0
        else:
            v = (uu - 0.5) / 0.5; s, h = -1 + 2 * smooth(v), math.sin(math.pi * v)
        p.swing(L, s * amp); p.lift(L, h * lift); p.curl(L, h * curl); p.foot(L, -h * 0.25)


# Idle: hunter at rest — twitchy head scans, chittering fangs, raised front legs tasting the air
HEAD_YAW = [0.0, 0.0, 0.32, 0.32, -0.05, -0.28, -0.28, 0.1, 0.1, 0.0]
HEAD_NOD = [0.0, -0.05, -0.05, 0.08, 0.0, 0.0, -0.08, -0.08, 0.04, 0.0]


def idle(p, f):
    u = f / 120
    p.body_loc = Vector((0, 0, 0.005 * math.sin(2 * TAU * u))); p.body(NOSE_UP, 0.03)
    p.rot("Abdomen", NOSE_UP, 0.05 * math.sin(2 * TAU * u + 1.2) + 0.02 * math.sin(16 * TAU * u))
    p.rot("Head", UP, held(f, 120, HEAD_YAW, 3)); p.rot("Head", NOSE_UP, held(f, 120, HEAD_NOD, 3))
    chit = max(0.0, math.sin(6 * TAU * u)) ** 4
    p.mand(0.08 + 0.18 * chit * abs(math.sin(48 * TAU * u)))
    p.palp(0.15 * math.sin(4 * TAU * u) + 0.1 * chit, 0.15 * math.sin(4 * TAU * u + 2) + 0.1 * chit)
    for L in legs:
        if L["idx"] == 0:  # front legs held up, slowly probing
            p.planted[L["name"]] = False
            ph = 0 if L["side"] < 0 else math.pi
            p.lift(L, 0.30 + 0.08 * math.sin(2 * TAU * u + ph) - math.asin(p.body_loc.z / L["lever"]))
            p.curl(L, -0.25 + 0.1 * math.sin(2 * TAU * u + ph + 1)); p.swing(L, 0.08)
        else:
            p.curl(L, 0.015 * math.sin(TAU * u + L["idx"] * 1.7))


WALK_P, WALK_AMP = 24, 0.24
RUN_P, RUN_AMP = 14, 0.30
record("Idle", 120, idle)
record("Walk", WALK_P, lambda p, f: gait(p, f, WALK_P, WALK_AMP, 0.30, 0.10, 0.006, mand=0.1))
record("Run", RUN_P, lambda p, f: gait(p, f, RUN_P, RUN_AMP, 0.42, 0.20, 0.01, roll=0.035, mand=0.2))

FRONT = [L for L in legs if L["idx"] == 0]; SECOND = [L for L in legs if L["idx"] == 1]


def attack(p, f):  # fast: short coil, violent double-leg stab + fang bite
    K = {0: (0, 0, 0, 0, 0, 0, 0.1, 0), 6: (0.03, 0.28, 0.05, 0.62, -0.55, 0.12, 0.7, -0.1),
         10: (0.035, 0.32, 0.06, 0.68, -0.6, 0.15, 0.75, -0.12),
         14: (0.0, -0.18, -0.12, -0.2, 0.25, 0.04, 0.0, 0.22), 18: (0.0, -0.14, -0.10, -0.15, 0.2, 0.02, 0.35, 0.16),
         21: (0.0, -0.15, -0.10, -0.16, 0.22, 0.02, 0.0, 0.18), 34: (0, 0, 0, 0, 0, 0, 0.1, 0)}
    up, nose, back, fl, fc, sl, md, nod = K[f]
    p.body_loc = Vector((0, back, up)); p.body(NOSE_UP, nose)
    p.rot("Head", NOSE_UP, nod); p.mand(md); p.rot("Abdomen", NOSE_UP, -nose * 0.5)
    p.palp(-md * 0.6, -md * 0.6)
    for L in FRONT:
        p.planted[L["name"]] = False; p.lift(L, fl); p.curl(L, fc); p.foot(L, -0.3 * max(fl, 0)); p.swing(L, 0.3 * fl)
    for L in SECOND: p.lift(L, sl)


record("Attack", [0, 6, 10, 14, 18, 21, 34], attack, interp='BEZIER')


def threat(p, f):  # rear up, legs spread wide, fangs flared, shudder
    base = {0: 0.0, 8: 1.0, 30: 1.0, 44: 0.0}
    keyf = [0, 8, 11, 14, 17, 20, 23, 26, 30, 44]
    w = 0.0 if f == 0 else 1.0 if 8 <= f <= 30 else 0.0
    sh = 0.0 if f in (0, 8, 30, 44) else (0.04 if (keyf.index(f) % 2) else -0.04)
    p.body_loc = Vector((0, 0.04 * w, 0.05 * w)); p.body(NOSE_UP, 0.32 * w + sh * 0.5); p.body(ROLL_R, sh * 0.5)
    p.rot("Abdomen", NOSE_UP, -0.25 * w + sh); p.rot("Head", NOSE_UP, -0.1 * w)
    p.mand(0.9 * w + sh * 2); p.palp(0.5 * w - sh * 3, 0.5 * w + sh * 3)
    for L in FRONT:
        p.planted[L["name"]] = False
        p.lift(L, 0.55 * w + sh); p.curl(L, -0.75 * w); p.swing(L, -0.15 * w); p.foot(L, -0.3 * w)
    for L in SECOND:
        p.planted[L["name"]] = False
        p.lift(L, 0.32 * w - sh); p.curl(L, -0.45 * w); p.swing(L, 0.1 * w)
        p.lift(L, -math.asin(min(0.9, p.body_loc.z / L["lever"])) * 0.0)


record("Threat", [0, 8, 11, 14, 17, 20, 23, 26, 30, 44], threat, interp='BEZIER')


def hit(p, f):
    K = {0: (0, 0, 0, 0), 3: (0.05, 0.14, 0.09, 0.22), 7: (0.02, -0.03, -0.03, 0.08), 16: (0, 0, 0, 0)}
    back, nose, roll, fl = K[f]
    p.body_loc = Vector((0, back, 0.01 * (fl > 0))); p.body(NOSE_UP, nose); p.body(ROLL_R, roll)
    p.rot("Head", NOSE_UP, nose * 1.2); p.mand(fl * 2.5); p.palp(fl * 2, fl * 2); p.rot("Abdomen", UP, -roll)
    for L in legs: p.curl(L, fl * 0.5)


record("Hit", [0, 3, 7, 16], hit, interp='BEZIER')

DROP = -(H - 0.09)
jit = {L["name"]: (random.uniform(-0.15, 0.15), random.uniform(-0.2, 0.2)) for L in legs}


def death(p, f):
    K = {0: (0, 0, 0, 0), 4: (0.03, 0.12, 0.15, 0.2), 10: (0.0, -0.05, -0.1, 0.35),
         22: (1.0, -0.06, 0.05, 1.0), 26: (0.9, -0.05, 0.04, 1.0), 32: (1.0, -0.06, 0.05, 1.0),
         50: (1.0, -0.06, 0.05, 1.0)}
    w, nose, roll, legw = K[f]
    drop = DROP * max(0.0, w) if f >= 10 else 0.02 * w / 0.03
    p.body_loc = Vector((0, 0.02 * legw, drop)); p.body(NOSE_UP, nose); p.body(ROLL_R, roll)
    p.rot("Head", NOSE_UP, -0.25 * legw); p.rot("Abdomen", NOSE_UP, -0.12 * legw)
    p.mand(0.6 * legw if f < 22 else 0.05); p.palp(-0.6 * legw, -0.5 * legw)
    for L in legs:
        p.planted[L["name"]] = False; j1, j2 = jit[L["name"]]
        if f <= 10:
            p.lift(L, 0.35 * legw); p.curl(L, 0.4 * legw)
        else:
            p.lift(L, -0.62 + j1 * 0.4); p.curl(L, -1.1 + j2); p.foot(L, 0.35 + j1); p.swing(L, j2 * 0.4)
            if f == 26: p.foot(L, 0.15)


record("Death", [0, 4, 10, 22, 26, 32, 50], death, interp='BEZIER')

arm.animation_data.action = None
for pb in PB.values(): pb.rotation_quaternion = Quaternion(); pb.location = (0, 0, 0)

bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "SpiderBot.blend"))
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); mesh.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(
    filepath=os.path.join(OUT, "SpiderBot.fbx"), use_selection=True, object_types={'ARMATURE', 'MESH'},
    apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', use_mesh_modifiers=False,
    mesh_smooth_type='FACE', add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
    use_armature_deform_only=False, bake_anim=True, bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=False, bake_anim_use_all_actions=True, bake_anim_force_startend_keying=True,
    bake_anim_simplify_factor=0.0, path_mode='STRIP', embed_textures=False)

print("TRIS", sum(len(p.vertices) - 2 for p in mesh.data.polygons), "VERTS", len(mesh.data.vertices),
      "BONES", len(arm_data.bones))
print("CLIPS", CLIPS)
lev = sum(L["lever"] for L in legs) / len(legs)
for nm, P_, A_ in (("Walk", WALK_P, WALK_AMP), ("Run", RUN_P, RUN_AMP)):
    print(nm, "speed", round(2 * A_ * (lev + 0.06) / (P_ / 2 / 30), 2))
