"""Sand Lizard: small low-poly desert lizard (Synty style), rigged, animated, exported as FBX for Unity.
Feet are placed with an analytic two-bone IK solve per frame, then baked to plain bone keys.
Run: python3 build_lizard.py [out_dir]   (default: the model folder above source/)"""
import sys, os, math
from collections import defaultdict
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion
import numpy as np
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(OUT, "Textures")
os.makedirs(TEX, exist_ok=True)
NAME = "SandLizard"

# ---------------------------------------------------------------- palette atlas
GRID, TS = 4, 256
SW = dict(MAIN=0, BAND=1, BELLY=2, THROAT=3, EYE=4, EYE_RIM=5, CLAW=6, TONGUE=7,
          SPIKE=8, MOUTH=9, EYE_HI=10, MAIN_DK=11)
PALETTES = {
    "Desert": dict(MAIN=(198, 152, 94), BAND=(128, 84, 48), BELLY=(234, 214, 176), THROAT=(230, 112, 40),
                   EYE=(22, 18, 16), EYE_RIM=(150, 108, 64), CLAW=(58, 42, 32), TONGUE=(206, 76, 92),
                   SPIKE=(156, 108, 60), MOUTH=(110, 40, 44), EYE_HI=(250, 246, 236), MAIN_DK=(172, 128, 78)),
    "Dune": dict(MAIN=(214, 200, 172), BAND=(140, 130, 114), BELLY=(242, 236, 222), THROAT=(66, 126, 190),
                 EYE=(18, 18, 20), EYE_RIM=(162, 150, 130), CLAW=(70, 64, 58), TONGUE=(196, 84, 104),
                 SPIKE=(176, 164, 142), MOUTH=(100, 44, 52), EYE_HI=(250, 250, 250), MAIN_DK=(188, 174, 148)),
    "Ember": dict(MAIN=(178, 70, 38), BAND=(42, 30, 28), BELLY=(228, 160, 96), THROAT=(250, 196, 54),
                  EYE=(242, 172, 32), EYE_RIM=(64, 40, 34), CLAW=(30, 24, 22), TONGUE=(70, 30, 60),
                  SPIKE=(60, 40, 34), MOUTH=(60, 20, 24), EYE_HI=(255, 244, 210), MAIN_DK=(140, 52, 30)),
}
SMOOTH = dict(MAIN=.3, BAND=.3, BELLY=.25, THROAT=.4, EYE=.9, EYE_RIM=.3, CLAW=.5, TONGUE=.6,
              SPIKE=.35, MOUTH=.5, EYE_HI=.9, MAIN_DK=.3)
cell = TS // GRID


def make_textures():
    for pname, pal in PALETTES.items():
        alb = np.zeros((TS, TS, 3), np.uint8)
        for key, k in SW.items():
            x, y = (k % GRID) * cell, (k // GRID) * cell
            g = np.linspace(1.06, 0.94, cell)[:, None, None]
            alb[y:y + cell, x:x + cell] = np.clip(np.array(pal[key], float)[None, None, :] * g, 0, 255)
        Image.fromarray(alb).save(f"{TEX}/T_{NAME}_{pname}_Albedo.png")
    ms = np.zeros((TS, TS, 4), np.uint8)
    for key, k in SW.items():
        x, y = (k % GRID) * cell, (k // GRID) * cell
        ms[y:y + cell, x:x + cell] = (0, 0, 0, int(SMOOTH[key] * 255))
    Image.fromarray(ms, "RGBA").save(f"{TEX}/T_{NAME}_MetallicSmoothness.png")


def swatch_uv(key):
    k = SW[key]
    return ((k % GRID) + 0.5) / GRID, 1.0 - ((k // GRID) + 0.5) / GRID


bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = 30
coll = scn.collection
parts = []


# ---------------------------------------------------------------- geometry helpers (Blender: +Z up, forward -Y, left +X)
def frame_from(origin, zdir, xhint):
    Z = Vector(zdir).normalized(); X = Vector(xhint)
    X = (X - Z * X.dot(Z)).normalized(); Y = Z.cross(X)
    M = Matrix.Identity(4)
    for i in range(3):
        M[i][0], M[i][1], M[i][2], M[i][3] = X[i], Y[i], Z[i], origin[i]
    return M


def finish(bm, name, key, bone):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    uvl = me.uv_layers.new(name="UVMap"); u, v = swatch_uv(key)
    for d in uvl.data: d.uv = (u, v)
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    ob.vertex_groups.new(name=bone).add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    parts.append(ob)
    return ob


def box(name, size, M, key, bone, bevel=0.0, taper=(1, 1), z0=False):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
        if v.co.z > 0: v.co.x *= taper[0]; v.co.y *= taper[1]
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


def seg(name, a, b, w, h, key, bone, taper=(1, 1), bevel=0.0, xhint=(1, 0, 0), extend=0.0):
    a, b = Vector(a), Vector(b); d = b - a
    M = frame_from(a - d.normalized() * extend, d, xhint)
    return box(name, (w, h, d.length + extend * 2), M, key, bone, bevel, taper, z0=True)


def spike(name, base, direction, length, w, key, bone, xhint=(1, 0, 0), h=None):
    base = Vector(base); d = Vector(direction).normalized()
    return seg(name, base - d * 0.002, base + d * length, w, h or w, key, bone, taper=(0.08, 0.08), xhint=xhint)


def tube(name, rings, key, sides=8, hint=(0, 0, 1), key_fn=None):
    """Lofted, capped tube through rings of (point, half_w, half_h, {bone: weight}).
    Ring frames use parallel transport so the tube never twists; weights blend smoothly across joints."""
    pts = [Vector(r[0]) for r in rings]; n = len(pts)
    tans = [(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(n)]
    N = Vector(hint); N = (N - tans[0] * N.dot(tans[0])).normalized()
    bm = bmesh.new(); vs = []
    for i in range(n):
        if i > 0:
            N = tans[i - 1].rotation_difference(tans[i]) @ N
            N = (N - tans[i] * N.dot(tans[i])).normalized()
        B = tans[i].cross(N); _, w, h, _ = rings[i]
        vs.append([bm.verts.new(pts[i] + B * (w * math.cos(2 * math.pi * j / sides + math.pi / sides))
                                + N * (h * math.sin(2 * math.pi * j / sides + math.pi / sides))) for j in range(sides)])
    uv = bm.loops.layers.uv.new("UVMap")
    faces = []
    for i in range(n - 1):
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append((bm.faces.new((vs[i][j], vs[i][j2], vs[i + 1][j2], vs[i + 1][j])), key_fn(i, j) if key_fn else key))
    faces.append((bm.faces.new(list(reversed(vs[0]))), key)); faces.append((bm.faces.new(vs[-1]), key))
    for f, k in faces:
        u, v = swatch_uv(k)
        for l in f.loops: l[uv].uv = (u, v)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    groups = {}
    for i, r in enumerate(rings):
        for b, w in r[3].items():
            if b not in groups: groups[b] = ob.vertex_groups.new(name=b)
            groups[b].add([i * sides + j for j in range(sides)], w, 'REPLACE')
    parts.append(ob)
    return ob


smooth = lambda x: (lambda c: c * c * (3 - 2 * c))(min(1.0, max(0.0, x)))

# ---------------------------------------------------------------- body loft (smooth-skinned along the spine)
KEYS = [  # y, z centre, half width, half height
    (-0.128, 0.050, 0.024, 0.019), (-0.105, 0.049, 0.029, 0.021), (-0.075, 0.048, 0.039, 0.025),
    (-0.045, 0.047, 0.048, 0.028), (-0.010, 0.046, 0.053, 0.029), (0.025, 0.046, 0.050, 0.028),
    (0.055, 0.045, 0.040, 0.024), (0.085, 0.041, 0.025, 0.018), (0.130, 0.034, 0.016, 0.013),
    (0.180, 0.027, 0.011, 0.009), (0.230, 0.020, 0.007, 0.006), (0.275, 0.015, 0.004, 0.0035),
    (0.305, 0.012, 0.0012, 0.0012)]


def profile(y):
    for i in range(len(KEYS) - 1):
        a, b = KEYS[i], KEYS[i + 1]
        if a[0] <= y <= b[0]:
            t = smooth((y - a[0]) / (b[0] - a[0]))
            return [a[k] + (b[k] - a[k]) * t for k in range(1, 4)]
    return list(KEYS[-1][1:]) if y > 0 else list(KEYS[0][1:])


CTRL = [("Head", -0.14), ("Neck", -0.099), ("Chest", -0.05), ("Body", 0.0), ("Hips", 0.0475),
        ("Tail1", 0.1025), ("Tail2", 0.1575), ("Tail3", 0.2125), ("Tail4", 0.2725)]


def weights_at(y):
    if y <= CTRL[0][1]: return {CTRL[0][0]: 1.0}
    if y >= CTRL[-1][1]: return {CTRL[-1][0]: 1.0}
    for i in range(len(CTRL) - 1):
        (n0, y0), (n1, y1) = CTRL[i], CTRL[i + 1]
        if y0 <= y <= y1:
            t = (y - y0) / (y1 - y0)
            return {n0: 1 - t, n1: t}


def build_loft():
    NR, NS = 31, 8
    y0, y1 = KEYS[0][0], KEYS[-1][0]
    ys = [y0 + (y1 - y0) * (i / (NR - 1)) ** 1.08 for i in range(NR)]
    bm = bmesh.new()
    rings = []
    for y in ys:
        zc, w, h = profile(y)
        ring = []
        for j in range(NS):
            a = 2 * math.pi * j / NS + math.pi / NS
            s, c = math.sin(a), math.cos(a)
            zz = h * s * (0.7 if s < 0 else 1.0) + (0.1 * h if s > 0.9 else 0)
            ring.append(bm.verts.new((w * c, y, zc + zz)))
        rings.append(ring)
    bm.verts.ensure_lookup_table()
    uv = bm.loops.layers.uv.new("UVMap")
    face_keys = []
    for i in range(NR - 1):
        ym = (ys[i] + ys[i + 1]) / 2
        band = (i // 2) % 2 == 0 and -0.095 < ym < 0.3
        for j in range(NS):
            j2 = (j + 1) % NS
            f = bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]))
            sm = math.sin(2 * math.pi * (j + 1) / NS)
            if sm > 0.55: key = "BAND" if band else "MAIN"
            elif sm < -0.35: key = "THROAT" if ym < -0.072 else "BELLY"
            else: key = "MAIN_DK" if band and ym > -0.06 else "MAIN"
            face_keys.append((f, key))
    face_keys.append((bm.faces.new(list(reversed(rings[0]))), "MAIN"))
    face_keys.append((bm.faces.new(rings[-1]), "BAND"))
    for f, key in face_keys:
        u, v = swatch_uv(key)
        for loop in f.loops: loop[uv].uv = (u, v)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("Loft"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("Loft", me); coll.objects.link(ob)
    groups = {n: ob.vertex_groups.new(name=n) for n, _ in CTRL}
    for i, y in enumerate(ys):
        for n, w in weights_at(y).items():
            groups[n].add([i * NS + j for j in range(NS)], w, 'REPLACE')
    parts.append(ob)
    return ys


build_loft()


def bone_at(y):
    return max(weights_at(y).items(), key=lambda kv: kv[1])[0]


# dorsal crest
for i, y in enumerate([-0.09 + 0.024 * k for k in range(10)]):
    zc, w, h = profile(y)
    L = 0.011 - 0.0005 * i if y < 0.06 else 0.007
    spike(f"Crest{i}", (0, y, zc + h * 1.06), (0, 0.55, 1), L, 0.006, "SPIKE", bone_at(y), h=0.004)

# ---------------------------------------------------------------- head, jaw, eyes, tongue
HZ = 0.050
seg("Head", (0, -0.112, HZ - 0.002), (0, -0.200, HZ - 0.008), 0.052, 0.030, "MAIN", "Head", taper=(0.42, 0.5), bevel=0.004)
seg("Jaw", (0, -0.116, HZ - 0.017), (0, -0.195, HZ - 0.018), 0.044, 0.011, "MAIN", "Jaw", taper=(0.42, 0.6), bevel=0.002)
seg("JawThroat", (0, -0.12, HZ - 0.021), (0, -0.17, HZ - 0.021), 0.028, 0.004, "THROAT", "Jaw", taper=(0.6, 1))
seg("Mouth", (0, -0.124, HZ - 0.0105), (0, -0.192, HZ - 0.0105), 0.028, 0.002, "MOUTH", "Jaw", taper=(0.45, 1))
for sx in (1, -1):
    ec = Vector((sx * 0.0185, -0.142, HZ + 0.007)); ed = Vector((sx, -0.25, 0.35)).normalized()
    cyl(f"EyeRim{sx}", 0.0076, 0.010, frame_from(ec, ed, (0, 0, 1)), "EYE_RIM", "Head", seg=7)
    cyl(f"Eye{sx}", 0.0057, 0.012, frame_from(ec + ed * 0.0012, ed, (0, 0, 1)), "EYE", "Head", seg=7)
    box(f"EyeHi{sx}", (0.002, 0.002, 0.002), T(ec + ed * 0.0066 + Vector((0, -0.0022, 0.0026))), "EYE_HI", "Head")
    seg(f"Brow{sx}", (sx * 0.0125, -0.133, HZ + 0.0135), (sx * 0.0205, -0.151, HZ + 0.0125), 0.006, 0.0035, "BAND", "Head",
        taper=(0.6, 0.6))
    box(f"Nostril{sx}", (0.0018, 0.0018, 0.0018), T((sx * 0.005, -0.1975, HZ - 0.0035)), "MOUTH", "Head")
    seg(f"TongueFork{sx}", (0, -0.188, HZ - 0.007), (sx * 0.0045, -0.199, HZ - 0.007), 0.0026, 0.0018, "TONGUE", "Tongue")
seg("Tongue", (0, -0.13, HZ - 0.007), (0, -0.19, HZ - 0.007), 0.0048, 0.002, "TONGUE", "Tongue")

# ---------------------------------------------------------------- legs (sprawled)
LEGS = []
for side, sx in (("L", 1), ("R", -1)):
    for kind in ("Front", "Rear"):
        if kind == "Front":
            S = Vector((sx * 0.030, -0.058, 0.044)); E = Vector((sx * 0.072, -0.050, 0.048))
            W = Vector((sx * 0.080, -0.078, 0.009)); hd = Vector((sx * 0.55, -1, 0)).normalized()
            names = (f"UpperArm_{side}", f"Forearm_{side}", f"Hand_{side}"); parent = "Chest"
            toes = (0.013, 0.018, 0.021, 0.019, 0.012); spread = 50
        else:
            S = Vector((sx * 0.030, 0.050, 0.043)); E = Vector((sx * 0.080, 0.035, 0.052))
            W = Vector((sx * 0.088, 0.072, 0.009)); hd = Vector((sx * 1.0, 0.25, 0)).normalized()
            names = (f"Thigh_{side}", f"Shin_{side}", f"Foot_{side}"); parent = "Hips"
            toes = (0.015, 0.021, 0.026, 0.032, 0.019); spread = 55
        up, lo, hand = names
        LEGS.append(dict(name=f"{kind}{side}", side=sx, kind=kind, S=S, E=E, W=W, hd=hd,
                         up=up, lo=lo, hand=hand, parent=parent))
        u1, u2 = (E - S).normalized(), (W - E).normalized()
        L1, L2 = (E - S).length, (W - E).length
        if kind == "Front":  # (point, half-width, half-height, weights): continuous limb, joints blended
            rs = [(S - u1 * 0.008, .0105, .0095, {parent: .6, up: .4}), (S + u1 * 0.004, .0102, .0092, {parent: .15, up: .85}),
                  (S + u1 * L1 * 0.45, .0092, .0085, {up: 1}), (E - u1 * 0.006, .0080, .0076, {up: .8, lo: .2}),
                  (E, .0079, .0077, {up: .5, lo: .5}), (E + u2 * 0.006, .0072, .0068, {up: .2, lo: .8}),
                  (E + u2 * L2 * 0.55, .0060, .0056, {lo: 1}), (W - u2 * 0.004, .0050, .0047, {lo: .8, hand: .2}),
                  (W + u2 * 0.003, .0050, .0046, {lo: .4, hand: .6}), (W + u2 * 0.0075, .0056, .0042, {lo: .1, hand: .9})]
            pad, toe_r = (0.009, 0.0075, 0.0036), (.0018, .0010)
        else:
            rs = [(S - u1 * 0.010, .0150, .0130, {parent: .6, up: .4}), (S + u1 * 0.006, .0145, .0128, {parent: .15, up: .85}),
                  (S + u1 * L1 * 0.45, .0125, .0112, {up: 1}), (E - u1 * 0.007, .0095, .0090, {up: .8, lo: .2}),
                  (E, .0093, .0091, {up: .5, lo: .5}), (E + u2 * 0.007, .0086, .0082, {up: .2, lo: .8}),
                  (E + u2 * L2 * 0.55, .0072, .0066, {lo: 1}), (W - u2 * 0.004, .0058, .0054, {lo: .85, hand: .15}),
                  (W + u2 * 0.003, .0056, .0052, {lo: .4, hand: .6}), (W + u2 * 0.0075, .0062, .0046, {lo: .1, hand: .9})]
            pad, toe_r = (0.011, 0.009, 0.0040), (.0021, .0011)
        tube(f"{up}_limb", rs, "MAIN", sides=8, hint=(0, 0, 1))
        # palm pad: a flattened low-poly dome under the wrist, toes fanning out of its front edge
        pc = W + hd * (pad[0] * 0.45) + Vector((0, 0, -0.0045))
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=4, radius=1.0)
        side_v = Vector((hd.y, -hd.x, 0))
        Mp = Matrix(((side_v.x * pad[1], hd.x * pad[0], 0), (side_v.y * pad[1], hd.y * pad[0], 0), (0, 0, pad[2]))).to_4x4()
        Mp.translation = pc
        bmesh.ops.transform(bm, matrix=Mp, verts=bm.verts)
        finish(bm, f"{hand}_pad", "MAIN", hand)
        for k, L in enumerate(toes):
            ang = math.radians(-spread + spread * 2 * k / 4) * (1 if sx > 0 else -1)
            d = Matrix.Rotation(ang, 3, 'Z') @ hd
            p0 = pc + d * (pad[0] * 0.6) + Vector((0, 0, 0.0002))
            tip = p0 + d * L + Vector((0, 0, -0.0018))
            tube(f"{hand}_toe{k}", [(p0 - d * 0.002, toe_r[0], toe_r[0] * 0.85, {hand: 1}),
                                     (p0.lerp(tip, 0.55), (toe_r[0] + toe_r[1]) / 2, toe_r[0] * 0.7, {hand: 1}),
                                     (tip, toe_r[1], toe_r[1] * 0.85, {hand: 1})], "MAIN", sides=5, hint=(0, 0, 1))
            cyl(f"{hand}_claw{k}", toe_r[1] * 1.05, 0.0045, frame_from(tip + d * 0.0019 + Vector((0, 0, -0.0005)), d + Vector((0, 0, -0.25)), (0, 0, 1)),
                "CLAW", hand, seg=4, r2=0.0001)

# ---------------------------------------------------------------- join + material
bpy.ops.object.select_all(action='DESELECT')
for p in parts: p.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
mesh = bpy.context.active_object; mesh.name = f"{NAME}_Mesh"; mesh.data.name = f"{NAME}_Mesh"
for poly in mesh.data.polygons: poly.use_smooth = False

make_textures()
mat = bpy.data.materials.new(f"M_{NAME}_Desert")
nt = mat.node_tree; nodes = nt.nodes; bsdf = nodes["Principled BSDF"]
ta = nodes.new("ShaderNodeTexImage"); ta.image = bpy.data.images.load(f"{TEX}/T_{NAME}_Desert_Albedo.png"); ta.interpolation = 'Closest'
tm = nodes.new("ShaderNodeTexImage"); tm.image = bpy.data.images.load(f"{TEX}/T_{NAME}_MetallicSmoothness.png"); tm.interpolation = 'Closest'
tm.image.colorspace_settings.name = 'Non-Color'
nt.links.new(ta.outputs["Color"], bsdf.inputs["Base Color"])
inv = nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
nt.links.new(tm.outputs["Alpha"], inv.inputs[1]); nt.links.new(inv.outputs[0], bsdf.inputs["Roughness"])
bsdf.inputs["Metallic"].default_value = 0.0
mesh.data.materials.append(mat)

# ---------------------------------------------------------------- armature
arm_data = bpy.data.armatures.new(f"{NAME}_Armature")
arm = bpy.data.objects.new(NAME, arm_data); coll.objects.link(arm)
bpy.context.view_layer.objects.active = arm; arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones


def bone(name, h, t, parent=None, connect=False):
    b = eb.new(name); b.head = Vector(h); b.tail = Vector(t); b.roll = 0
    if parent: b.parent = eb[parent]; b.use_connect = connect


bone("Root", (0, 0, 0), (0, -0.06, 0))
bone("Body", (0, 0, 0.046), (0, -0.03, 0.046), "Root")
bone("Chest", (0, -0.02, 0.047), (0, -0.08, 0.048), "Body")
bone("Neck", (0, -0.08, 0.048), (0, -0.118, 0.049), "Chest", True)
bone("Head", (0, -0.118, 0.049), (0, -0.20, 0.045), "Neck", True)
bone("Jaw", (0, -0.118, 0.036), (0, -0.195, 0.034), "Head")
bone("Tongue", (0, -0.13, 0.043), (0, -0.19, 0.043), "Head")
bone("Hips", (0, 0.02, 0.046), (0, 0.075, 0.044), "Body")
bone("Tail1", (0, 0.075, 0.044), (0, 0.13, 0.034), "Hips", True)
bone("Tail2", (0, 0.13, 0.034), (0, 0.185, 0.026), "Tail1", True)
bone("Tail3", (0, 0.185, 0.026), (0, 0.24, 0.019), "Tail2", True)
bone("Tail4", (0, 0.24, 0.019), (0, 0.305, 0.012), "Tail3", True)
for L in LEGS:
    bone(L["up"], L["S"], L["E"], L["parent"])
    bone(L["lo"], L["E"], L["W"], L["up"], True)
    bone(L["hand"], L["W"], L["W"] + L["hd"] * 0.012, L["lo"], True)
bpy.ops.object.mode_set(mode='OBJECT')
mesh.parent = arm
mesh.modifiers.new("Armature", 'ARMATURE').object = arm
arm_data.display_type = 'STICK'

# ---------------------------------------------------------------- animation (pose spec -> IK solve -> bone keys)
REST = {b.name: b.matrix_local.copy() for b in arm_data.bones}
REST3 = {k: v.to_3x3() for k, v in REST.items()}
REST3_INV = {k: v.inverted() for k, v in REST3.items()}
PB = {pb.name: pb for pb in arm.pose.bones}
for pb in PB.values(): pb.rotation_mode = 'QUATERNION'
I3 = Matrix.Identity(3)
NOSE_UP = Vector((-1, 0, 0)); UPZ = Vector((0, 0, 1)); FWD_AX = Vector((0, 1, 0))
BODY_C = Vector((0, 0, 0.046))


def basis3(d, h):
    c = d.cross(h)
    return Matrix(((d.x, h.x, c.x), (d.y, h.y, c.y), (d.z, h.z, c.z)))


for L in LEGS:
    S, E, W = L["S"], L["E"], L["W"]
    L["L1"], L["L2"] = (E - S).length, (W - E).length
    L["up_rest"], L["lo_rest"] = (E - S).normalized(), (W - E).normalized()
    L["hinge_rest"] = L["up_rest"].cross(L["lo_rest"]).normalized()
    u = (W - S).normalized(); pole = (E - S) - u * (E - S).dot(u)
    L["pole_local"] = REST3_INV[L["parent"]] @ pole.normalized()
    L["Bup_rest_T"] = basis3(L["up_rest"], L["hinge_rest"]).transposed()
    L["Blo_rest_T"] = basis3(L["lo_rest"], L["hinge_rest"]).transposed()
LEG = {L["name"]: L for L in LEGS}


def mat4(R3, t):
    M = R3.to_4x4(); M.translation = t; return M


class Pose:
    def __init__(self):
        self.q = defaultdict(Quaternion); self.loc = {}
        self.body_loc = Vector(); self.body_rot = Quaternion()
        self.tgt = {}; self.hrot = {}

    def rot(self, b, axis, ang):
        ax = (REST3_INV[b] @ Vector(axis)).normalized()
        self.q[b] = self.q[b] @ Quaternion(ax, ang)

    def body(self, axis, ang):
        self.body_rot = Quaternion(Vector(axis), ang) @ self.body_rot

    def body_matrix(self):
        R = self.body_rot.to_matrix().to_4x4()
        return Matrix.Translation(BODY_C + self.body_loc) @ R @ Matrix.Translation(-BODY_C)


def set_basis(pb, B):
    loc, rot, _ = B.decompose()
    pb.rotation_quaternion = rot
    pb.location = loc


def apply(p):
    for pb in PB.values():
        pb.rotation_quaternion = Quaternion(); pb.location = (0, 0, 0)
    for b, q in p.q.items():
        if b != "Body": PB[b].rotation_quaternion = q
    for b, l in p.loc.items(): PB[b].location = l
    Rb = p.body_rot.to_matrix()
    PB["Body"].rotation_quaternion = (REST3_INV["Body"] @ Rb @ REST3["Body"]).to_quaternion()
    PB["Body"].location = REST3_INV["Body"] @ p.body_loc
    bpy.context.view_layer.update()
    for L in LEGS:
        Pp = PB[L["parent"]].matrix.copy()
        S = PB[L["up"]].matrix.translation.copy()
        Tg = p.tgt.get(L["name"], L["W"])
        pole = (Pp.to_3x3() @ L["pole_local"]).normalized()
        d = Tg - S
        L1, L2 = L["L1"], L["L2"]
        dist = min(max(d.length, abs(L1 - L2) + 1e-4), (L1 + L2) * 0.999)
        u = d.normalized()
        w = pole - u * u.dot(pole)
        w = w.normalized() if w.length > 1e-6 else Vector((0, 0, 1))
        ca = max(-1.0, min(1.0, (L1 * L1 + dist * dist - L2 * L2) / (2 * L1 * dist)))
        a = math.acos(ca)
        up_dir = (u * math.cos(a) + w * math.sin(a)).normalized()
        Ej = S + up_dir * L1
        Wj = S + u * dist
        lo_dir = (Wj - Ej).normalized()
        hinge = up_dir.cross(lo_dir)
        hinge = hinge.normalized() if hinge.length > 1e-6 else (Pp.to_3x3() @ (REST3_INV[L["parent"]] @ L["hinge_rest"]))
        Mup = mat4(basis3(up_dir, hinge) @ L["Bup_rest_T"] @ REST3[L["up"]], S)
        Mlo = mat4(basis3(lo_dir, hinge) @ L["Blo_rest_T"] @ REST3[L["lo"]], Ej)
        Mh = mat4(p.hrot.get(L["name"], I3) @ REST3[L["hand"]], Wj)
        set_basis(PB[L["up"]], (REST[L["parent"]].inverted() @ REST[L["up"]]).inverted() @ (Pp.inverted() @ Mup))
        set_basis(PB[L["lo"]], (REST[L["up"]].inverted() @ REST[L["lo"]]).inverted() @ (Mup.inverted() @ Mlo))
        set_basis(PB[L["hand"]], (REST[L["lo"]].inverted() @ REST[L["hand"]]).inverted() @ (Mlo.inverted() @ Mh))


arm.animation_data_create()
CLIPS = {}


def _fcurves(act):
    if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])): return list(act.fcurves)
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags: out.extend(cb.fcurves)
    return out


def record(name, nframes, fn):
    act = bpy.data.actions.new(name); act.use_fake_user = True
    arm.animation_data.action = act
    for f in range(nframes + 1):
        p = Pose(); fn(p, f); apply(p)
        for pb in PB.values():
            pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
            pb.keyframe_insert("location", frame=f, group=pb.name)
    for fc in _fcurves(act):
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    act.frame_range = (0, nframes); CLIPS[name] = nframes


TAU = math.tau
TAILS = ["Tail1", "Tail2", "Tail3", "Tail4"]


def lateral(L):  # horizontal unit vector pointing away from the body on this leg's side
    return Vector((L["side"], 0, 0))


def held(f, period, keys, snap=3.0):
    n = len(keys); step = period / n
    i = int(f // step) % n; local = f - (f // step) * step
    return keys[i - 1] + (keys[i] - keys[i - 1]) * smooth(local / snap)


# ---- locomotion: diagonal-pair trot with a travelling S-wave through spine and tail
GROUP = {"FrontL": 0, "RearR": 0, "FrontR": 1, "RearL": 1}


def gait(p, f, period, stride, duty, lift, undul, tail_amp, rise, head_up):
    ph = f / period
    wave = math.cos(TAU * ph)
    p.body_loc = Vector((0, 0, rise + 0.0018 * math.cos(2 * TAU * ph)))
    p.body(FWD_AX, 0.035 * math.sin(TAU * ph))
    p.rot("Chest", UPZ, -undul * wave)
    p.rot("Hips", UPZ, undul * wave)
    p.rot("Neck", UPZ, undul * 0.85 * wave)
    p.rot("Neck", NOSE_UP, head_up)
    p.rot("Head", UPZ, -undul * 0.15 * wave)
    for i, t in enumerate(TAILS):
        p.rot(t, UPZ, -undul * 0.5 * wave * (i == 0) + tail_amp * (0.35 + 0.22 * i) * math.cos(TAU * ph - 1.0 * (i + 1)))
        p.rot(t, NOSE_UP, 0.03 * rise / 0.006 if rise else 0.0)
    for L in LEGS:
        u = (ph + 0.5 * GROUP[L["name"]]) % 1.0
        if u < duty: s, h = 0.5 - u / duty, 0.0
        else:
            v = (u - duty) / (1 - duty); s, h = -0.5 + smooth(v), math.sin(math.pi * v)
        p.tgt[L["name"]] = L["W"] + Vector((0, -s * stride, h * lift)) + lateral(L) * (0.004 * h)
        ax = L["hd"].cross(UPZ).normalized()
        p.hrot[L["name"]] = Quaternion(ax, -0.5 * h * L["side"]).to_matrix()


WALK = dict(period=24, stride=0.05, duty=0.62, lift=0.014, undul=0.16, tail_amp=0.22, rise=0.0, head_up=0.05)
RUN = dict(period=10, stride=0.095, duty=0.45, lift=0.022, undul=0.22, tail_amp=0.32, rise=0.006, head_up=0.12)


# ---- turn in place: planted feet sweep around the pivot (opposite to the turn) and step back,
# while the spine curves into the turn. Play it while rotating the object at TURN_RATE.
TURN = dict(period=16, duty=0.6, lift=0.016, sweep=0.5)
TURN_RATE = TURN["sweep"] / (TURN["duty"] * TURN["period"] / 30)  # rad/s


def turn(p, f, sign, period, duty, lift, sweep):
    ph = f / period
    wave = math.cos(TAU * ph)
    p.body_loc = Vector((0, 0, 0.0015 * math.cos(2 * TAU * ph)))
    p.body(FWD_AX, 0.02 * math.sin(TAU * ph))
    p.rot("Chest", UPZ, sign * 0.16 - 0.05 * wave)
    p.rot("Hips", UPZ, -sign * 0.08 + 0.05 * wave)
    p.rot("Neck", UPZ, sign * 0.12); p.rot("Neck", NOSE_UP, 0.06)
    p.rot("Head", UPZ, sign * 0.10)
    for i, t in enumerate(TAILS):
        p.rot(t, UPZ, -sign * (0.06 + 0.035 * i) + 0.06 * (0.5 + 0.25 * i) * math.cos(TAU * ph - 0.9 * (i + 1)))
    for L in LEGS:
        u = (ph + 0.5 * GROUP[L["name"]]) % 1.0
        if u < duty: s, h = 0.5 - u / duty, 0.0
        else:
            v = (u - duty) / (1 - duty); s, h = -0.5 + smooth(v), math.sin(math.pi * v)
        R = Matrix.Rotation(sign * s * sweep, 3, 'Z')
        w = L["W"]
        p.tgt[L["name"]] = R @ Vector((w.x, w.y, 0)) + Vector((0, 0, w.z + h * lift)) + lateral(L) * (0.003 * h)
        ax = L["hd"].cross(UPZ).normalized()
        p.hrot[L["name"]] = R @ Quaternion(ax, -0.5 * h * L["side"]).to_matrix()

# ---- idle: breathing, snapping head looks, tongue flicks, lazy tail tip
HEAD_YAW = [0, 0, 0.38, 0.38, 0.38, 0.05, -0.32, -0.32, -0.05, 0]
HEAD_TILT = [0, 0, 0.12, 0.12, 0.0, 0, -0.1, -0.1, 0, 0]


def tongue_flick(p, local):
    if 0 <= local <= 8:
        ext = abs(math.sin(math.pi * local / 4))
        p.loc["Tongue"] = Vector((0, 0.034 * ext, 0))
        p.rot("Jaw", (1, 0, 0), 0.07 * min(1, local / 2) * (1 - max(0, local - 6) / 2))


def idle(p, f):
    br = math.sin(TAU * f / 40)
    p.body_loc = Vector((0, 0, 0.0012 * br))
    p.rot("Chest", NOSE_UP, 0.012 * br)
    p.rot("Neck", NOSE_UP, 0.06)
    p.rot("Neck", UPZ, held(f, 120, HEAD_YAW) * 0.6)
    p.rot("Head", UPZ, held(f, 120, HEAD_YAW) * 0.4)
    p.rot("Head", FWD_AX, held(f, 120, HEAD_TILT))
    tongue_flick(p, f - 46); tongue_flick(p, f - 98)
    for i, t in enumerate(TAILS):
        p.rot(t, UPZ, 0.06 * (i + 1) * math.sin(TAU * f / 120 + i * 0.6))
        if i >= 2: p.rot(t, NOSE_UP, 0.05 * math.sin(TAU * f / 60 + i))


# ---- push-up display
def pushups(p, f):
    keys = [(0, 0), (6, 1), (12, 0.1), (18, 1), (25, 0), (45, 0)]
    k = 0.0
    for (fa, va), (fb, vb) in zip(keys, keys[1:]):
        if fa <= f <= fb: k = va + (vb - va) * smooth((f - fa) / (fb - fa)); break
    p.body_loc = Vector((0, 0, 0.010 * k))
    p.body(NOSE_UP, 0.24 * k)
    p.rot("Neck", NOSE_UP, -0.12 * k + 0.05)
    p.rot("Head", NOSE_UP, 0.12 * k)
    p.rot("Jaw", (1, 0, 0), 0.03 * k)
    for i, t in enumerate(TAILS): p.rot(t, NOSE_UP, -0.06 * k * (i == 0))
    if f >= 30: tongue_flick(p, f - 34)


# ---- burrow into sand (Emerge plays it backwards)
BURROW_N = 36


def burrow(p, f):
    w = smooth(f / 30)
    wig = math.sin(TAU * f / 5) * 0.32 * (0.3 + 0.7 * min(1, f / 8)) * (1 - smooth((f - 28) / 6))
    p.body_loc = Vector((0, -0.01 * w, -0.115 * w))
    p.body(NOSE_UP, -0.22 * math.sin(math.pi * min(1, f / 26)))
    p.rot("Chest", UPZ, wig); p.rot("Hips", UPZ, -wig)
    p.rot("Neck", NOSE_UP, -0.2 * w)
    for i, t in enumerate(TAILS):
        p.rot(t, UPZ, wig * (0.5 + 0.3 * i) * math.cos(i))
        p.rot(t, NOSE_UP, 0.09 * math.sin(math.pi * min(1, f / 26)))
    for L in LEGS:
        sgn = 1 if GROUP[L["name"]] == 0 else -1
        p.tgt[L["name"]] = L["W"] + Vector((0, 0.016 * sgn * math.sin(TAU * f / 5), -0.11 * w))


# ---- death: flips belly-up, legs curl, twitches
def death(p, f):
    wf = smooth((f - 2) / 12)
    p.body(FWD_AX, math.pi * wf)
    p.body_loc = Vector((0, 0, 0.05 * math.sin(math.pi * wf) - 0.017 * wf))
    wl = smooth(f / 10)
    p.rot("Neck", UPZ, 0.35 * wl); p.rot("Neck", NOSE_UP, -0.15 * wl)
    p.rot("Jaw", (1, 0, 0), 0.22 * smooth((f - 16) / 8))
    p.loc["Tongue"] = Vector((0, 0.016 * smooth((f - 20) / 6), 0))
    for i, t in enumerate(TAILS): p.rot(t, UPZ, 0.28 * wl * (1 + 0.3 * i))
    Mb = p.body_matrix(); Rq = p.body_rot
    for L in LEGS:
        curled = Vector((L["W"].x * 0.72, L["W"].y * 0.9, L["W"].z + 0.03))
        tw = 0.0
        if f > 22: tw = 0.006 * math.sin(f * 1.9 + L["side"] * 2 + (L["kind"] == "Rear") * 1.3) * (1 - smooth((f - 22) / 16))
        curled.z += tw
        tgt = Mb @ curled
        p.tgt[L["name"]] = L["W"].lerp(tgt, wl)
        p.hrot[L["name"]] = Quaternion().slerp(Rq, wl).to_matrix()


record("Idle", 120, idle)
record("Walk", WALK["period"], lambda p, f: gait(p, f, **WALK))
record("Run", RUN["period"], lambda p, f: gait(p, f, **RUN))
record("PushUps", 45, pushups)
record("Burrow", BURROW_N, burrow)
record("Emerge", BURROW_N, lambda p, f: burrow(p, BURROW_N - f))
record("Death", 40, death)
record("TurnLeft", TURN["period"], lambda p, f: turn(p, f, 1, **TURN))
record("TurnRight", TURN["period"], lambda p, f: turn(p, f, -1, **TURN))

arm.animation_data.action = None
for pb in PB.values(): pb.rotation_quaternion = Quaternion(); pb.location = (0, 0, 0)
bpy.context.view_layer.update()

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{NAME}.blend"))
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); mesh.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(
    filepath=os.path.join(OUT, f"{NAME}.fbx"), use_selection=True, object_types={'ARMATURE', 'MESH'},
    apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', use_mesh_modifiers=False,
    mesh_smooth_type='FACE', add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
    use_armature_deform_only=False, bake_anim=True, bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=False, bake_anim_use_all_actions=True, bake_anim_force_startend_keying=True,
    bake_anim_simplify_factor=0.0, path_mode='STRIP', embed_textures=False)

print("TRIS", sum(len(p.vertices) - 2 for p in mesh.data.polygons), "VERTS", len(mesh.data.vertices),
      "BONES", len(arm_data.bones))
print("CLIPS", CLIPS)
for nm, g in (("Walk", WALK), ("Run", RUN)):
    print(nm, "speed m/s", round(g["stride"] / (g["duty"] * g["period"] / 30), 3))
print("Turn rate rad/s", round(TURN_RATE, 4), "deg/s", round(math.degrees(TURN_RATE), 2))
