"""Build an animated low-poly animal from a model spec (models/<id>.json).

Run through tools/build_model.sh, which calls:
    blender -b --factory-startup -P tools/blender/build_model.py -- models/<id>.json

The spec is plain data (shapes, colours, bones), so anyone can write one
without knowing Blender. This script turns it into:
  assets/animals/<id>.glb     the model with its animation clips, for the game
  models/previews/<id>.png    a preview sheet for human review
Seasonal coats (colours that change for a season) live in the game's
animals/<id>.json under model.coats; the preview sheet shows each one.

Coordinates in the spec are game coordinates in metres: x = the animal's
left, y = up, z = forward (the animal faces +z). Angles are in degrees.
"""

import bpy
import bmesh
import json
import math
import os
import sys
from mathutils import Matrix, Vector

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))
from spec_shapes import AXIS, ROOT, add_shape, g2b, render_tile, rot_matrix, save_sheet, setup_render, srgb_to_linear  # noqa: E402

FPS = 24
SHAPES = ("box", "ball", "cone", "cylinder", "taper")
ROLES = ("body", "head", "neck", "leg", "tail", "ear", "wing", "fin", "jaw", "none")
CLIPS = {"idle": 48, "walk": 24, "run": 16, "eat": 24, "sleep": 48}
errors = []


def fail(msg):
    errors.append(msg)


# --- spec ----------------------------------------------------------------------

def mirror_name(name):
    if name.endswith("_l"):
        return name[:-2] + "_r"
    fail(f"'{name}': a mirrored name must end in _l (the right side gets _r)")
    return name + "_r"


def load_spec(path):
    with open(path) as f:
        spec = json.load(f)
    for key in ("id", "colors", "bones", "parts"):
        if key not in spec:
            fail(f"missing '{key}'")
    if errors:
        return spec
    spec.setdefault("gait", "walk")
    if spec["gait"] not in ("walk", "bound"):
        fail("gait must be 'walk' (legs on each side alternate) or 'bound' (left and right move together)")
    # expand mirrored bones and parts into explicit left/right copies
    bones = []
    for b in spec["bones"]:
        b = dict(b)
        b.setdefault("parent", "root")
        b.setdefault("role", "none")
        b.setdefault("phase", 0.0)
        b.setdefault("swing", 1.0)
        if b["role"] not in ROLES:
            fail(f"bone '{b.get('name')}': unknown role '{b['role']}' (use one of {', '.join(ROLES)})")
        bones.append(b)
        if b.get("mirror"):
            m = dict(b)
            m["name"] = mirror_name(b["name"])
            m["head"] = [-b["head"][0], b["head"][1], b["head"][2]]
            m["tail"] = [-b["tail"][0], b["tail"][1], b["tail"][2]]
            if b["parent"].endswith("_l"):
                m["parent"] = mirror_name(b["parent"])
            if spec["gait"] == "walk" and b["role"] == "leg":
                m["phase"] = (b["phase"] + 0.5) % 1.0
            bones.append(m)
    names = {"root"}
    for b in bones:
        if b["name"] in names:
            fail(f"bone '{b['name']}' is defined twice")
        if b["parent"] not in names:
            fail(f"bone '{b['name']}': parent '{b['parent']}' must be defined above it")
        names.add(b["name"])
    parts = []
    for p in spec["parts"]:
        p = dict(p)
        p.setdefault("rot", [0, 0, 0])
        p.setdefault("bone", bones[0]["name"] if bones else "root")
        if p.get("shape") not in SHAPES:
            fail(f"part '{p.get('name')}': shape must be one of {', '.join(SHAPES)}")
        if p.get("color") not in spec["colors"]:
            fail(f"part '{p.get('name')}': colour '{p.get('color')}' is not in 'colors'")
        if p["bone"] not in names:
            fail(f"part '{p.get('name')}': bone '{p['bone']}' does not exist")
        parts.append(p)
        if p.get("mirror"):
            m = dict(p)
            m["name"] = mirror_name(p["name"])
            m["at"] = [-p["at"][0], p["at"][1], p["at"][2]]
            m["rot"] = [p["rot"][0], -p["rot"][1], -p["rot"][2]]
            if p["bone"].endswith("_l"):
                m["bone"] = mirror_name(p["bone"])
            parts.append(m)
    spec["bones"], spec["parts"] = bones, parts
    return spec


# --- building --------------------------------------------------------------------

def make_materials(spec):
    mats = {}
    for name, hex_color in spec["colors"].items():
        lin = srgb_to_linear(hex_color)
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = (*lin, 1.0)
        mat.roughness = 1.0
        mat.metallic = 0.0
        bsdf = mat.node_tree.nodes.get("Principled BSDF") if mat.node_tree else None
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (*lin, 1.0)
            bsdf.inputs["Roughness"].default_value = 1.0
        mats[name] = mat
    return mats


def build_mesh(spec, mats, arm_obj):
    mesh = bpy.data.meshes.new(spec["id"])
    obj = bpy.data.objects.new(spec["id"], mesh)
    bpy.context.scene.collection.objects.link(obj)
    color_names = list(spec["colors"])
    for name in color_names:
        mesh.materials.append(mats[name])
    groups = {b.name: obj.vertex_groups.new(name=b.name) for b in arm_obj.data.bones}
    bm = bmesh.new()
    deform = bm.verts.layers.deform.verify()
    for p in spec["parts"]:
        verts = add_shape(bm, p)
        vset = set(verts)
        gi = groups[p["bone"]].index
        for v in verts:
            v[deform][gi] = 1.0
        for f in bm.faces:
            if f.verts[0] in vset:
                f.material_index = color_names.index(p["color"])
                f.smooth = bool(p.get("smooth", False))
    bm.to_mesh(mesh)
    bm.free()
    obj.parent = arm_obj
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm_obj
    return obj


# --- skin: one continuous body ---------------------------------------------------
# The parts are melted into one body (voxel remesh), smoothed, and reduced to a
# triangle budget, so the animal is one sculpted-looking skin instead of loose
# balls and sticks. Parts thinner than `keep` voxels (eyes, nose, ears) stay
# separate and crisp. Each skin vertex takes the bone of the nearest part, and
# the weights are blended across joints so the skin bends instead of tearing.

SKIN_DEFAULTS = {"voxel": 1 / 70, "smooth": 4, "triangles": 1000, "shading": "smooth", "keep": 2.0, "blend": 3}


def skin_settings(spec, length):
    opts = dict(SKIN_DEFAULTS)
    opts.update(spec.get("skin", {}))
    opts.update(json.loads(os.environ.get("BUILD_SKIN", "{}")))   # experiments
    if opts["voxel"] < 0.2:
        opts["voxel"] = opts["voxel"] * length   # a fraction of the body length
    return opts


def build_skin(spec, mats, arm_obj, opts):
    import numpy as np
    from mathutils.bvhtree import BVHTree
    color_names = list(spec["colors"])
    vox = opts["voxel"]
    body = [p for p in spec["parts"] if min(p["size"]) >= opts["keep"] * vox and not p.get("separate")]
    detail = [p for p in spec["parts"] if p not in body]
    # the parts, as they are, for colour and bone lookups
    src = bmesh.new()
    src_info = []   # per face: (material index, bone name)
    for p in body:
        add_shape(src, p)
        src.faces.index_update()   # new faces come last: they belong to this part
        while len(src_info) < len(src.faces):
            src_info.append((color_names.index(p["color"]), p["bone"]))
    src.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(src)
    # melt, smooth, reduce
    src_mesh = bpy.data.meshes.new("_parts")
    src.to_mesh(src_mesh)
    tmp = bpy.data.objects.new("_parts", src_mesh)
    bpy.context.scene.collection.objects.link(tmp)
    rm = tmp.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = vox
    if opts["smooth"] > 0:
        sm = tmp.modifiers.new("smooth", "LAPLACIANSMOOTH")   # keeps the volume: parts stay attached
        sm.iterations = int(opts["smooth"])
        sm.lambda_factor = 0.5
        sm.use_volume_preserve = True
        sm.use_normalized = True
    dg = bpy.context.evaluated_depsgraph_get()
    tris = sum(len(f.vertices) - 2 for f in tmp.evaluated_get(dg).data.polygons)
    detail_tris = 0
    probe = bmesh.new()
    for p in detail:
        add_shape(probe, p)
    detail_tris = sum(len(f.verts) - 2 for f in probe.faces)
    probe.free()
    want = max(200, opts["triangles"] - detail_tris)
    if tris > want:
        dc = tmp.modifiers.new("decimate", "DECIMATE")
        dc.ratio = want / tris
        dc.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    skin_mesh = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    bpy.data.meshes.remove(src_mesh)

    # one object: the skin plus the crisp detail parts
    obj = bpy.data.objects.new(spec["id"], bpy.data.meshes.new(spec["id"]))
    bpy.context.scene.collection.objects.link(obj)
    for name in color_names:
        obj.data.materials.append(mats[name])
    bone_names = [b.name for b in arm_obj.data.bones]
    groups = {n: obj.vertex_groups.new(name=n) for n in bone_names}
    bm = bmesh.new()
    bm.from_mesh(skin_mesh)
    bpy.data.meshes.remove(skin_mesh)
    deform = bm.verts.layers.deform.verify()
    flat = opts["shading"] == "flat"
    for f in bm.faces:
        _, _, fi, _ = tree.find_nearest(f.calc_center_median())
        f.material_index = src_info[fi][0] if fi is not None else 0
        f.smooth = not flat
    # weights: nearest part's bone, then blended along the skin's edges
    bm.verts.ensure_lookup_table()
    n = len(bm.verts)
    w = np.zeros((n, len(bone_names)), dtype=np.float32)
    for v in bm.verts:
        _, _, fi, _ = tree.find_nearest(v.co)
        w[v.index, bone_names.index(src_info[fi][1] if fi is not None else body[0]["bone"])] = 1.0
    edges = np.array([(e.verts[0].index, e.verts[1].index) for e in bm.edges], dtype=np.int64)
    deg = np.bincount(edges.ravel(), minlength=n).astype(np.float32)[:, None]
    for _ in range(int(opts["blend"])):
        acc = np.zeros_like(w)
        np.add.at(acc, edges[:, 0], w[edges[:, 1]])
        np.add.at(acc, edges[:, 1], w[edges[:, 0]])
        w = 0.5 * w + 0.5 * acc / np.maximum(deg, 1)
    w[w < 0.05] = 0
    for v in bm.verts:
        row = w[v.index]
        top = np.argsort(row)[::-1][:4]
        total = row[top].sum()
        for bi in top:
            if row[bi] > 0:
                v[deform][groups[bone_names[bi]].index] = float(row[bi] / total)
    for p in detail:
        verts = set(add_shape(bm, p))
        gi = groups[p["bone"]].index
        for v in verts:
            v[deform][gi] = 1.0
        for f in bm.faces:
            if f.verts[0] in verts:
                f.material_index = color_names.index(p["color"])
                f.smooth = bool(p.get("smooth", not flat))
    bm.to_mesh(obj.data)
    bm.free()
    src.free()
    obj.parent = arm_obj
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm_obj
    return obj


def build_armature(spec):
    arm = bpy.data.armatures.new(spec["id"] + "_rig")
    arm_obj = bpy.data.objects.new(spec["id"] + "_rig", arm)
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    root = arm.edit_bones.new("root")
    root.head, root.tail = Vector((0, 0, 0)), Vector((0, 0, 0.05))
    for b in spec["bones"]:
        eb = arm.edit_bones.new(b["name"])
        eb.head, eb.tail = g2b(b["head"]), g2b(b["tail"])
        if (eb.tail - eb.head).length < 1e-4:
            fail(f"bone '{b['name']}': head and tail are in the same place")
        eb.parent = arm.edit_bones[b["parent"]]
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_obj


# --- animation -------------------------------------------------------------------

def wave(t, phase=0.0, cycles=1):
    return math.sin(2 * math.pi * (t * cycles + phase))


def pose_for(clip, t, b, height, is_front, side):
    """Rotation (pitch, yaw, roll in radians) for one bone at time t (0..1)."""
    role, ph, sw = b["role"], b["phase"], b["swing"]
    s = wave(t, ph)
    p = y = r = 0.0
    if role == "leg":
        if clip == "walk":
            p = 0.45 * sw * s
        elif clip == "run":
            p = 0.85 * sw * s
        elif clip == "sleep":
            p = -1.1 if is_front else -0.9
    elif role == "body":
        if clip == "run":
            p = 0.12 * sw * wave(t, ph)
        elif clip == "walk":
            y = 0.04 * sw * s
    elif role in ("head", "neck"):
        k = 1.0 if role == "head" else 0.5
        if clip == "idle":
            y = 0.35 * k * sw * wave(t, ph) * max(0.0, wave(t, ph + 0.1))
            p = 0.06 * k * wave(t, ph, 2)
        elif clip in ("walk", "run"):
            p = 0.06 * k * s
        elif clip == "eat":
            p = 0.55 * k + 0.08 * wave(t, ph, 4)
        elif clip == "sleep":
            p, y = 0.4 * k, 0.5 * k
    elif role == "jaw" and clip == "eat":
        p = -0.25 * max(0.0, wave(t, ph, 4))
    elif role == "tail":
        if clip == "idle":
            y = 0.18 * sw * wave(t, -ph)
        elif clip in ("walk", "run", "eat"):
            p = 0.15 * sw * wave(t, -ph, 2 if clip == "eat" else 1)
        elif clip == "sleep":
            y = 0.5 * sw
    elif role == "ear":
        if clip == "idle":
            r = side * 0.25 * sw * max(0.0, wave(t, ph, 2)) ** 8
        elif clip == "sleep":
            p = -0.5
        elif clip == "run":
            p = -0.35
    elif role == "wing":
        if clip == "fly":
            r = side * 0.9 * sw * s
    elif role == "fin":
        if clip in ("swim", "walk", "run", "idle"):
            amp = {"idle": 0.1, "walk": 0.3, "swim": 0.35, "run": 0.5}[clip]
            y = amp * sw * wave(t, -ph, 2 if clip == "run" else 1)
    return p, y, r


def root_offset(clip, t, height, gait):
    """Body bob in game metres (up)."""
    if clip == "walk":
        return 0.03 * height * abs(wave(t))
    if clip == "run":
        return (0.15 if gait == "bound" else 0.06) * height * max(0.0, wave(t))
    if clip == "sleep":
        return -0.2 * height
    if clip == "eat":
        return -0.04 * height
    if clip == "idle":
        return 0.01 * height * wave(t)
    return 0.0


def make_actions(spec, arm_obj, height):
    bones = {b["name"]: b for b in spec["bones"]}
    clips = dict(CLIPS)
    roles = {b["role"] for b in spec["bones"]}
    if "wing" in roles:
        clips["fly"] = 16
    if "fin" in roles:
        clips["swim"] = 24
    arm_obj.animation_data_create()
    actions = {}
    for clip, frames in clips.items():
        action = bpy.data.actions.new(clip)
        action.use_fake_user = True
        arm_obj.animation_data.action = action
        for f in range(frames + 1):
            t = f / frames
            for pb in arm_obj.pose.bones:
                pb.rotation_mode = "QUATERNION"
                rest = pb.bone.matrix_local.to_3x3()
                if pb.name == "root":
                    up = Vector((0, 0, root_offset(clip, t, height, spec["gait"])))
                    pb.location = rest.inverted() @ up
                    pb.keyframe_insert("location", frame=f + 1)
                    continue
                b = bones[pb.name]
                head = pb.bone.head_local
                side = 1.0 if head.x >= 0 else -1.0
                p, y, r = pose_for(clip, t, b, height, head.y < 0, side)
                world = (Matrix.Rotation(y, 3, AXIS["yaw"]) @ Matrix.Rotation(p, 3, AXIS["pitch"])
                         @ Matrix.Rotation(r, 3, AXIS["roll"]))
                pb.rotation_quaternion = (rest.inverted() @ world @ rest).to_quaternion()
                pb.keyframe_insert("rotation_quaternion", frame=f + 1)
        actions[clip] = (action, frames)
    arm_obj.animation_data.action = None
    return actions


# --- preview sheet ---------------------------------------------------------------

def render_sheet(spec, arm_obj, mesh_obj, actions, out_path, coats, mats):
    size = 320
    setup_render(size)
    scene = bpy.context.scene
    corners = [mesh_obj.matrix_world @ Vector(c) for c in mesh_obj.bound_box]
    lo = Vector([min(c[i] for c in corners) for i in range(3)])
    hi = Vector([max(c[i] for c in corners) for i in range(3)])
    center = (lo + hi) / 2
    extent = max(hi - lo)
    # ground shadow catcher: a pale disc
    bpy.ops.mesh.primitive_circle_add(vertices=32, radius=extent * 0.9, fill_type="NGON",
                                      location=(center.x, center.y, -0.001))
    ground = bpy.context.active_object
    gmat = bpy.data.materials.new("_ground")
    gmat.diffuse_color = (0.55, 0.65, 0.5, 1)
    ground.data.materials.append(gmat)
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = extent * 1.45
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    label_data = bpy.data.curves.new("label", "FONT")
    label = bpy.data.objects.new("label", label_data)
    scene.collection.objects.link(label)
    label.parent = cam
    label_data.size = extent * 0.09
    lmat = bpy.data.materials.new("_label")
    lmat.diffuse_color = (0.1, 0.12, 0.1, 1)
    label_data.materials.append(lmat)
    label.location = (-cam_data.ortho_scale * 0.46, cam_data.ortho_scale * 0.4, -1.0)

    # game directions, turned into Blender views
    views = {"front": (0, 0.25, 1), "side": (1, 0.15, 0), "back 3/4": (-0.8, 0.5, -0.8), "top": (0.001, 1, 0.2)}
    shots = []
    for name, d in views.items():
        shots.append((name, d, "idle", 0.0, {}))
    for i in range(4):
        shots.append((f"walk {i + 1}/4", (1, 0.15, 0), "walk", i / 4, {}))
    extra = ["run", "eat", "sleep"] + [c for c in ("fly", "swim") if c in actions]
    for clip in extra:
        shots.append((clip, (0.9, 0.35, 0.5), clip, 0.3, {}))
    for season, coat in coats.items():
        shots.append((f"{season} coat", (0.9, 0.35, 0.5), "idle", 0.0, coat))
    while len(shots) % 4:
        shots.append(("idle", (0.9, 0.35, -0.5), "idle", 0.5, {}))

    tiles = []
    base = {n: tuple(m.diffuse_color) for n, m in mats.items()}
    for name, d, clip, t, coat in shots:
        for n, m in mats.items():
            m.diffuse_color = (*srgb_to_linear(coat[n]), 1.0) if n in coat else base[n]
        action, frames = actions[clip]
        arm_obj.animation_data.action = action
        scene.frame_set(1 + round(t * frames))
        direction = g2b(d).normalized()
        cam.location = center + direction * extent * 4
        cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
        label_data.body = name
        tiles.append(render_tile(size))
    save_sheet(tiles, out_path)
    arm_obj.animation_data.action = actions["idle"][0]
    for obj in (ground, cam, label):
        bpy.data.objects.remove(obj)


# --- main ------------------------------------------------------------------------

def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        print("usage: tools/build_model.sh models/<id>.json")
        sys.exit(2)
    spec_path = os.path.abspath(args[0])
    spec = load_spec(spec_path)
    if errors:
        for e in errors:
            print("ERROR:", e)
        sys.exit(1)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS
    arm_obj = build_armature(spec)
    if errors:
        for e in errors:
            print("ERROR:", e)
        sys.exit(1)
    mats = make_materials(spec)
    if spec.get("skin", {}) is False:
        mesh_obj = build_mesh(spec, mats, arm_obj)   # loose parts, the old way
        skin = None
    else:
        pts = [Vector(p["at"]) for p in spec["parts"]]
        length = max(max(v.z for v in pts) - min(v.z for v in pts), max(v.y for v in pts)) + 0.05
        skin = skin_settings(spec, length)
        mesh_obj = build_skin(spec, mats, arm_obj, skin)
    zs = [v.co.z for v in mesh_obj.data.vertices]
    ys = [v.co.y for v in mesh_obj.data.vertices]
    height = max(zs)
    actions = make_actions(spec, arm_obj, height)

    model_id = spec["id"]
    glb = os.path.join(ROOT, "assets", "animals", model_id + ".glb")
    preview = os.path.join(ROOT, "models", "previews", model_id + ".png")
    if os.environ.get("BUILD_OUT"):   # experiments: write somewhere else
        glb = os.path.join(os.environ["BUILD_OUT"], model_id + ".glb")
        preview = os.path.join(os.environ["BUILD_OUT"], model_id + ".png")
    os.makedirs(os.path.dirname(preview), exist_ok=True)
    coats = {}
    animal_file = os.path.join(ROOT, "animals", model_id + ".json")
    if os.path.exists(animal_file):
        with open(animal_file) as f:
            coats = json.load(f).get("model", {}).get("coats", {})
    for season, coat in coats.items():
        for n in coat:
            if n not in mats:
                fail(f"animals/{model_id}.json: the {season} coat changes '{n}', which is not a colour in the spec")
    if errors:
        for e in errors:
            print("ERROR:", e)
        sys.exit(1)
    render_sheet(spec, arm_obj, mesh_obj, actions, preview, coats, mats)

    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    mesh_obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True,
                              export_animations=True, export_animation_mode="ACTIONS",
                              export_apply=False, export_yup=True)

    # The game measures a model by its bone positions (head of each bone), so
    # print the length to put in animals/<id>.json for real-world scale.
    heads = [b.head_local for b in arm_obj.data.bones]
    bone_len = max(max(h.y for h in heads) - min(h.y for h in heads),
                   max(h.x for h in heads) - min(h.x for h in heads))
    tri_count = sum(len(f.vertices) - 2 for f in mesh_obj.data.polygons)
    print(f"BUILT {model_id}: {tri_count} triangles, {len(arm_obj.data.bones)} bones, "
          f"clips {', '.join(actions)}")
    print(f"  size: {max(ys) - min(ys):.3f} m long, {height:.3f} m tall")
    print(f"  glb:     {os.path.relpath(glb, ROOT)}")
    print(f"  preview: {os.path.relpath(preview, ROOT)}")
    print(f'  for animals/{model_id}.json: "length": {bone_len:.3f} (real size), "yaw": 0.0')


main()
