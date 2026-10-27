"""Build a tree from its spec (models/trees/<id>.json): block templates and a preview sheet.

Run through tools/build_model.sh, which calls:
    blender -b --factory-startup -P tools/blender/build_tree.py -- models/trees/<id>.json

The game's trees are made of blocks, like its land. tools/tree_shape.py turns
the spec into a few block templates (short, medium and tall), and this script:
  assets/trees/<id>.json        the templates and colours, which the game stamps into the land
  models/trees/previews/<id>.png  a preview sheet of the same blocks, with a moose for scale
"""

import bpy
import bmesh
import json
import math
import os
import sys
from mathutils import Vector

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from spec_shapes import ROOT, render_tile, save_sheet, setup_render, srgb_to_linear  # noqa: E402
import tree_shape  # noqa: E402

errors = []


def material(name, hex_color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*srgb_to_linear(hex_color), 1.0)
    return mat


def blocks_object(name, template, colors, leaves=True, at=(0, 0)):
    """One mesh of unit cubes: the trunk and (unless bare) the leaves.
    Template coordinates are game blocks (x, y up, z); Blender is z up."""
    bm = bmesh.new()
    me = bpy.data.meshes.new(name)
    for kind in ("trunk", "leaf"):
        if kind == "leaf" and not leaves:
            continue
        for x, y, z in template[kind]:
            r = bmesh.ops.create_cube(bm, size=1.0)
            for v in r["verts"]:
                v.co += Vector((x + at[0] + 0.5, -(z + at[1] + 0.5), y - 0.5))
            for f in {f for v in r["verts"] for f in v.link_faces}:
                f.material_index = 0 if kind == "trunk" else 1
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    me.materials.append(material(name + "_trunk", colors["trunk"]))
    me.materials.append(material(name + "_leaves", colors["leaves"]))
    return obj


def add_moose(x):
    """The moose (about 2 m tall) next to the tree, for scale."""
    path = os.path.join(ROOT, "assets", "animals", "moose.glb")
    if not os.path.exists(path):
        return []
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.parent is None:
            o.location.x += x
            o.rotation_mode = "XYZ"
            o.rotation_euler.z += math.radians(-70)
    return new


def render_sheet(spec, templates, out_path):
    size = 320
    setup_render(size)
    scene = bpy.context.scene
    colors = spec["colors"]
    tall = templates[-1]
    reach = max(max(abs(b[0]), abs(b[2])) for b in tall["trunk"] + tall["leaf"])
    top = max(b[1] for b in tall["trunk"] + tall["leaf"])
    extent = max(top, reach * 2 + 6)
    bpy.ops.mesh.primitive_circle_add(vertices=48, radius=extent * 0.75, fill_type="NGON", location=(0, 0, -0.002))
    ground = bpy.context.active_object
    ground.data.materials.append(material("_ground", "#8fae6a"))
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = extent * 1.25
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    label_data = bpy.data.curves.new("label", "FONT")
    label = bpy.data.objects.new("label", label_data)
    scene.collection.objects.link(label)
    label.parent = cam
    label_data.size = extent * 0.06
    label_data.materials.append(material("_label", "#1a1e1a"))
    label.location = (-cam_data.ortho_scale * 0.46, cam_data.ortho_scale * 0.4, -1.0)
    center = Vector((0, 0, top * 0.45))

    def shoot(name, direction):
        d = Vector(direction).normalized()
        cam.location = center + d * extent * 4
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        label_data.body = name
        return render_tile(size)

    tiles = []
    moose = add_moose(reach + 3)
    obj = blocks_object("tree", templates[1], colors)
    tiles.append(shoot("side", (1, 0, 0.12)))
    tiles.append(shoot("3/4", (0.8, -0.8, 0.5)))
    tiles.append(shoot("top", (0.001, 0, 1)))
    for o in moose:
        o.hide_render = True
    bpy.data.objects.remove(obj)
    # the three heights side by side
    gap = reach * 2 + 3
    objs = [blocks_object(f"v{i}", t, colors, at=((i - 1) * gap, 0)) for i, t in enumerate(templates)]
    old = cam_data.ortho_scale
    cam_data.ortho_scale = max(old, gap * 3 + 2)
    tiles.append(shoot("short, medium, tall", (0, -1, 0.15)))
    cam_data.ortho_scale = old
    for o in objs:
        bpy.data.objects.remove(o)
    if colors.get("autumn"):   # deciduous: the autumn colour, then bare in winter
        autumn = dict(colors, leaves=colors["autumn"])
        obj = blocks_object("autumn", templates[1], autumn)
        tiles.append(shoot("autumn", (0.8, -0.8, 0.5)))
        bpy.data.objects.remove(obj)
        obj = blocks_object("winter", templates[1], colors, leaves=False)
        tiles.append(shoot("winter", (0.8, -0.8, 0.5)))
        bpy.data.objects.remove(obj)
    while len(tiles) % 4:
        obj = blocks_object("tree", templates[2], colors)
        tiles.append(shoot("tall", (-0.8, 0.8, 0.4)))
        bpy.data.objects.remove(obj)
    save_sheet(tiles, out_path)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        print("usage: tools/build_model.sh models/trees/<id>.json")
        sys.exit(2)
    with open(args[0]) as f:
        spec = json.load(f)
    tid = spec.get("id", "")
    for key in ("id", "trunk", "crown", "colors"):
        if key not in spec:
            errors.append(f"missing '{key}'")
    for key in ("trunk", "leaves"):
        if key not in spec.get("colors", {}):
            errors.append(f"colors needs '{key}'")
    if not errors:
        errors.extend(tree_shape.problems(spec))
    if errors:
        for e in errors:
            print("ERROR:", e)
        sys.exit(1)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    templates = tree_shape.variants(spec)
    out = os.path.join(ROOT, "assets", "trees", tid + ".json")
    preview = os.path.join(ROOT, "models", "trees", "previews", tid + ".png")
    if os.environ.get("BUILD_OUT"):   # experiments: write somewhere else
        out = os.path.join(os.environ["BUILD_OUT"], tid + ".json")
        preview = os.path.join(os.environ["BUILD_OUT"], tid + ".png")
    for p in (out, preview):
        os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(out, "w") as f:
        json.dump({"id": tid, "colors": spec["colors"], "on": spec.get("on", ["grass"]), "variants": templates}, f)
        f.write("\n")
    render_sheet(spec, templates, preview)
    sizes = ", ".join(f"{max(b[1] for b in t['trunk'] + t['leaf'])} m" for t in templates)
    blocks = max(len(t["trunk"]) + len(t["leaf"]) for t in templates)
    print(f"BUILT {tid}: a {spec['crown']['shape']} tree, {sizes} tall, up to {blocks} blocks")
    print(f"  template: {os.path.relpath(out, ROOT)}")
    print(f"  preview: {os.path.relpath(preview, ROOT)}")


main()
# Leave without Blender's shutdown: on macOS, Blender 5.2.3 crashes while
# stopping its threads after a headless run (see build_model.py).
sys.stdout.flush()
os._exit(0)
