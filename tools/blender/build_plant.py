"""Build a low-poly plant from a plant spec (models/plants/<id>.json).

Run through tools/build_model.sh, which calls:
    blender -b --factory-startup -P tools/blender/build_plant.py -- models/plants/<id>.json

Like an animal spec, a plant spec is plain data (shapes and colours), but a
plant has no bones: it sways in the game's wind instead. This script turns it
into:
  assets/plants/<id>.glb            one mesh, colours baked into the vertices
                                    (the game draws thousands of copies at once)
  models/previews/plants/<id>.png   a preview sheet for human review

Coordinates are game coordinates in metres: x = left, y = up, z = forward,
with the plant standing on the ground at y = 0 around x = z = 0.
"""

import bpy
import bmesh
import json
import math
import os
import random
import re
import sys
from mathutils import Vector

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))
from spec_shapes import ROOT, add_shape, g2b, render_tile, save_sheet, setup_render, srgb_to_linear  # noqa: E402

SHAPES = ("box", "ball", "cone", "cylinder", "taper", "leaf")
SEASONS = ("spring", "summer", "autumn", "winter")
MARK = re.compile(r"^(spring|summer|autumn|winter)(\+\d+)?$")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
# triangle budgets from ART.md, on the busiest day of the year: ground cover
# is drawn thousands of times
BUDGET = {"ground": 50, "bush": 300}
errors = []


def fail(msg):
    errors.append(msg)


# --- spec ----------------------------------------------------------------------

def mirror_name(name):
    if name.endswith("_l"):
        return name[:-2] + "_r"
    fail(f"'{name}': a mirrored name must end in _l (the right side gets _r)")
    return name + "_r"


def around_y(v, deg, pivot):
    """Turns game point v around the upright line through pivot [x, z]."""
    a = math.radians(deg)
    x, z = v[0] - pivot[0], v[2] - pivot[1]
    return [pivot[0] + x * math.cos(a) + z * math.sin(a), v[1], pivot[1] + z * math.cos(a) - x * math.sin(a)]


def load_spec(path):
    with open(path) as f:
        spec = json.load(f)
    for key in ("id", "colors", "parts"):
        if key not in spec:
            fail(f"missing '{key}'")
    if errors:
        return spec
    spec.setdefault("kind", "ground")
    if spec["kind"] not in BUDGET:
        fail(f"kind must be one of {', '.join(BUDGET)}")
    if len(spec["colors"]) > 64:
        fail("use at most 64 colours")
    for name, hex_color in spec["colors"].items():
        if not HEX.match(str(hex_color)):
            fail(f"colour '{name}' must look like \"#5f9445\"")
    for season, changes in spec.setdefault("seasons", {}).items():
        if season not in SEASONS:
            fail(f"seasons: '{season}' must be one of {', '.join(SEASONS)}")
        for name, hex_color in changes.items():
            if name not in spec["colors"]:
                fail(f"seasons.{season}: '{name}' is not a colour in 'colors'")
            elif not HEX.match(str(hex_color)):
                fail(f"seasons.{season}.{name} must look like \"#5f9445\"")
    parts = []
    for src, p in enumerate(spec["parts"]):
        p = dict(p)
        p.setdefault("rot", [0, 0, 0])
        p["src"] = src
        name = p.get("name", "?")
        show = p.get("show")
        if show is not None and not (isinstance(show, dict) and MARK.match(str(show.get("from")))
                                     and MARK.match(str(show.get("until")))):
            fail(f"part '{name}': show must be like {{\"from\": \"summer+55\", \"until\": \"autumn+15\"}}")
        nectar = p.get("nectar")
        if nectar is not None and nectar is not True and not (isinstance(nectar, dict) and MARK.match(str(nectar.get("from")))
                                                              and MARK.match(str(nectar.get("until")))):
            fail(f"part '{name}': nectar must be true or like {{\"from\": \"summer+55\", \"until\": \"autumn\"}}")
        if p.get("shape") not in SHAPES:
            fail(f"part '{name}': shape must be one of {', '.join(SHAPES)}")
            continue
        if p.get("color") not in spec["colors"]:
            fail(f"part '{name}': colour '{p.get('color')}' is not in 'colors'")
            continue
        copies = [p]
        if p.get("mirror"):
            m = dict(p)
            m["name"] = mirror_name(name)
            m["at"] = [-p["at"][0], p["at"][1], p["at"][2]]
            m["rot"] = [p["rot"][0], -p["rot"][1], -p["rot"][2]]
            copies.append(m)
        n = int(p.get("around", 1))
        if n > 1:
            # n copies spaced evenly around the stem, each a little different
            # parts with the same seed get the same turns (a flower spike on its shoot)
            rng = random.Random(f"{spec['id']}/{p.get('seed', name)}")
            jit = float(p.get("jitter", 0.0))
            pivot = p.get("pivot", [0, 0])
            ring = []
            for c in copies:
                for k in range(n):
                    deg = p.get("turn", 0) + k * 360 / n + rng.uniform(-0.5, 0.5) * jit * 360 / n
                    r = dict(c)
                    r["name"] = f"{c['name']}_{k + 1}"
                    r["at"] = around_y(c["at"], deg, pivot)
                    r["rot"] = [c["rot"][0] + rng.uniform(-15, 15) * jit, c["rot"][1] + deg, c["rot"][2]]
                    sc = 1 + rng.uniform(-0.2, 0.2) * jit
                    r["size"] = [s * sc for s in c["size"]]
                    ring.append(r)
            copies = ring
        parts += copies
    spec["shows"] = [p.get("show") for p in spec["parts"]]
    spec["parts"] = parts
    return spec


# --- building --------------------------------------------------------------------

def build_mesh(spec, look=None):
    """One mesh with the colours stored per corner (no materials needed).

    Each corner's UV says which part and colour it belongs to (u = part * 64 +
    colour, colours sorted by name), so the game can recolour the plant for
    the season and leave out parts that aren't there (scripts/plant_model.gd).
    `look` ({colors, date}) builds it as it looks on a day, for the preview."""
    mesh = bpy.data.meshes.new(spec["id"])
    obj = bpy.data.objects.new(spec["id"], mesh)
    bpy.context.scene.collection.objects.link(obj)
    bm = bmesh.new()
    col_layer = bm.loops.layers.float_color.new("Color")
    uv_layer = bm.loops.layers.uv.new("UVMap")
    names = sorted(spec["colors"])
    colors = look["colors"] if look else spec["colors"]
    for p in spec["parts"]:
        if look and p.get("show") and not look["date"].between(p["show"]["from"], p["show"]["until"]):
            continue
        vset = set(add_shape(bm, p))
        lin = (*srgb_to_linear(colors[p["color"]]), 1.0)
        code = p["src"] * 64 + names.index(p["color"])
        for f in bm.faces:
            if f.verts[0] in vset:
                f.smooth = bool(p.get("smooth", False))
                for loop in f.loops:
                    loop[col_layer] = lin
                    loop[uv_layer].uv = (code, 0.0)
    bm.to_mesh(mesh)
    bm.free()
    mesh.color_attributes.active_color = mesh.color_attributes["Color"]
    mesh.color_attributes.render_color_index = mesh.color_attributes.active_color_index
    # a plain material, so the exporter keeps the vertex colours; the game
    # draws plants with its own swaying foliage material
    mat = bpy.data.materials.new("plant")
    mat.roughness, mat.metallic = 1.0, 0.0
    mesh.materials.append(mat)
    return obj


# --- seasons (as scripts/season.gd works them out) --------------------------------

NORTH = {"spring": "04-05", "summer": "05-25", "autumn": "09-20", "winter": "11-25"}
BEFORE = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def day_of_year(md):
    m, d = (int(x) for x in md.split("-")[-2:])
    return (BEFORE[m - 1] + d - 1) % 365


class RegionDate:
    """One day of the year in a region: its season and how far into it."""

    def __init__(self, cfg, md):
        self.label = f"{int(md[3:])} {MONTHS[int(md[:2]) - 1]}"
        self.starts = {n: day_of_year(cfg.get(n, NORTH[n])) for n in SEASONS}
        self.today = day_of_year(md)
        self.name = min(SEASONS, key=lambda n: (self.today - self.starts[n]) % 365)
        self.days_in = (self.today - self.starts[self.name]) % 365

    def mark(self, m):
        season, _, offset = m.partition("+")
        return (self.starts[season] + int(offset or 0)) % 365

    def between(self, a, b):
        a, b = self.mark(a), self.mark(b)
        return (self.today - a) % 365 <= (b - a) % 365

    def weights(self):
        """Last season's colours fading, this season's growing in (three weeks)."""
        t = min(1.0, self.days_in / 21)
        return {SEASONS[(SEASONS.index(self.name) + 3) % 4]: 1 - t, self.name: t}


def busiest_day(spec, me):
    """The most triangles shown on any day of the year (in the starter region),
    and that day: parts that never show together don't add up."""
    per_part = {}
    uv = me.uv_layers["UVMap"].data
    for poly in me.polygons:
        src = round(uv[poly.loop_indices[0]].uv[0]) // 64
        per_part[src] = per_part.get(src, 0) + len(poly.vertices) - 2
    cfg = starter_region().get("seasons", {})
    best = None
    for m in range(12):
        for d in (1, 8, 15, 22):
            date = RegionDate(cfg, f"{m + 1:02d}-{d:02d}")
            n = sum(t for src, t in per_part.items() if not spec["shows"][src]
                    or date.between(spec["shows"][src]["from"], spec["shows"][src]["until"]))
            if best is None or n > best[0]:
                best = (n, date)
    return best


def colors_on(spec, date):
    out = {}
    for name, hex_color in spec["colors"].items():
        c = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
        for season, w in date.weights().items():
            new = spec["seasons"].get(season, {}).get(name)
            if new and w > 0:
                n = [int(new[i:i + 2], 16) for i in (1, 3, 5)]
                c = [a + (b - a) * w for a, b in zip(c, n)]
        out[name] = "#" + "".join(f"{round(v):02x}" for v in c)
    return out


# --- preview sheet ---------------------------------------------------------------

def starter_region():
    """The starter region: its ground colours and season dates."""
    try:
        with open(os.path.join(ROOT, "regions", "fi_nuuksio.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def ground_colour(key="ground_lush", fallback="#5f9445"):
    return starter_region().get("palette", {}).get(key, fallback)


def paint(obj, hex_color):
    lin = (*srgb_to_linear(hex_color), 1.0)
    attr = obj.data.color_attributes["Color"]
    for i in range(len(obj.data.loops)):
        attr.data[i].color = lin


def add_ground(radius, center):
    bpy.ops.mesh.primitive_circle_add(vertices=48, radius=radius, fill_type="NGON",
                                      location=(center.x, center.y, -0.002))
    ground = bpy.context.active_object
    me = ground.data
    attr = me.color_attributes.new("Color", "FLOAT_COLOR", "CORNER")
    lin = (*srgb_to_linear(ground_colour()), 1.0)
    for i in range(len(me.loops)):
        attr.data[i].color = lin
    me.color_attributes.active_color = attr
    return ground


def add_squirrel(x):
    """The red squirrel (0.36 m long) next to the plant, for scale."""
    path = os.path.join(ROOT, "assets", "animals", "squirrel.glb")
    if not os.path.exists(path):
        return []
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.parent is None:
            o.location.x += x
            o.rotation_mode = "XYZ"
            o.rotation_euler.z += math.radians(-60)
        if o.type == "MESH":
            # show its material colours in the vertex-colour view
            me = o.data
            attr = me.color_attributes.new("Color", "FLOAT_COLOR", "CORNER")
            for poly in me.polygons:
                c = me.materials[poly.material_index].diffuse_color if me.materials else (0.5, 0.5, 0.5, 1)
                for li in poly.loop_indices:
                    attr.data[li].color = c
            me.color_attributes.active_color = attr
    return new


def render_sheet(spec, obj, out_path):
    size = 320
    setup_render(size)
    scene = bpy.context.scene
    sh = scene.display.shading
    sh.color_type = "VERTEX"
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector([min(c[i] for c in corners) for i in range(3)])
    hi = Vector([max(c[i] for c in corners) for i in range(3)])
    center = (lo + hi) / 2
    extent = max(max(hi - lo), 0.05)
    ground_r = 1.0
    ground = add_ground(ground_r, Vector((0, 0, 0)))
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    label_data = bpy.data.curves.new("label", "FONT")
    label = bpy.data.objects.new("label", label_data)
    scene.collection.objects.link(label)
    label.parent = cam
    lmat = bpy.data.materials.new("_label")
    lmat.diffuse_color = (0.1, 0.12, 0.1, 1)
    label_data.materials.append(lmat)

    def shoot(name, d, frame, at=None):
        cam_data.ortho_scale = frame
        direction = g2b(d).normalized()
        target = at if at is not None else center
        ground.scale = [frame * 0.42 / ground_r] * 3  # leave room for the label
        ground.location = (target.x, target.y, -0.002)
        cam.location = target + direction * frame * 4
        cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
        label_data.body = name
        label_data.size = frame * 0.06
        label.location = (-frame * 0.46, frame * 0.4, -1.0)
        tiles.append(render_tile(size))

    tiles = []
    frame = extent * 1.45
    shoot("front", (0, 0.25, 1), frame)
    shoot("side", (1, 0.15, 0), frame)
    shoot("3/4", (0.9, 0.55, 0.6), frame)
    shoot("top", (0.001, 1, 0.2), frame)

    # silhouette: can you name it from its outline?
    sh.color_type, sh.single_color = "SINGLE", (0.05, 0.06, 0.05)
    sh.show_shadows = sh.show_cavity = False
    ground.hide_render = True
    shoot("silhouette", (1, 0.15, 0), frame)
    ground.hide_render = False
    sh.color_type = "VERTEX"
    sh.show_shadows = sh.show_cavity = True

    # a patch as the game scatters it (turned and sized a little differently)
    rng = random.Random(spec["id"])
    spacing = max(hi.x - lo.x, hi.y - lo.y) * 1.1 + 0.05
    copies = []
    for i in range(6):
        c = obj.copy()
        scene.collection.objects.link(c)
        a = i * 2.4
        c.location = (math.cos(a) * spacing * (0.6 + i * 0.25), math.sin(a) * spacing * (0.6 + i * 0.25), 0)
        c.rotation_euler.z = rng.uniform(0, math.tau)
        c.scale = [rng.uniform(0.85, 1.15)] * 3
        copies.append(c)
    shoot("a patch", (0.9, 0.7, 0.7), spacing * 4.5, Vector((0, 0, center.z)))
    for c in copies:
        bpy.data.objects.remove(c)

    squirrel = add_squirrel(-(hi.x - lo.x) / 2 - 0.25)
    both = max(extent, 0.4) + 0.5
    shoot("with a squirrel (0.36 m)", (0.2, 0.25, 1), both * 1.3, Vector((-0.2, 0, max(center.z, 0.15))))
    for o in squirrel:
        bpy.data.objects.remove(o)

    # how big it looks from the game camera, a few metres away
    shoot("game distance", (0.9, 0.5, 0.7), 5.0, Vector((0, 0, 0.3)))

    # through the year in the starter region (Nuuksio's season dates)
    cfg = starter_region().get("seasons", {})
    obj.hide_render = True
    for md in ("06-10", "08-10", "10-10", "01-20"):
        date = RegionDate(cfg, md)
        look = build_mesh(spec, {"colors": colors_on(spec, date), "date": date})
        if date.name == "winter":
            paint(ground, ground_colour("snow", "#eef2f6"))
        shoot(f"{date.label} ({date.name})", (0.9, 0.55, 0.6), frame)
        paint(ground, ground_colour())
        bpy.data.objects.remove(look)
    obj.hide_render = False
    save_sheet(tiles, out_path)
    for o in (ground, cam, label):
        bpy.data.objects.remove(o)


# --- main ------------------------------------------------------------------------

def report_errors():
    for e in errors:
        print("ERROR:", e)
    sys.exit(1)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        print("usage: tools/build_model.sh models/plants/<id>.json")
        sys.exit(2)
    spec = load_spec(os.path.abspath(args[0]))
    if errors:
        report_errors()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obj = build_mesh(spec)
    me = obj.data
    tris, busiest = busiest_day(spec, me)
    zs = [v.co.z for v in me.vertices]
    if min(zs) < -0.05:
        fail(f"parts reach {-min(zs):.2f} m under the ground: the plant stands at y = 0")
    budget = BUDGET[spec["kind"]]
    if tris > budget:
        fail(f"{tris} triangles on {busiest.label} is over the budget for kind '{spec['kind']}' "
             f"({budget}, see ART.md): use fewer parts, lower 'detail', or 'leaf' shapes")
    if errors:
        report_errors()

    plant_id = spec["id"]
    if not isinstance(plant_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", plant_id):   # it becomes a file name
        print(f"ERROR: 'id' must be lowercase letters, digits and _, got {plant_id!r}")
        sys.exit(1)
    glb = os.path.join(ROOT, "assets", "plants", plant_id + ".glb")
    preview = os.path.join(ROOT, "models", "previews", "plants", plant_id + ".png")
    if os.environ.get("BUILD_OUT"):   # experiments and examples: write somewhere else
        glb = os.path.join(os.environ["BUILD_OUT"], plant_id + ".glb")
        preview = os.path.join(os.environ["BUILD_OUT"], plant_id + ".png")
    os.makedirs(os.path.dirname(glb), exist_ok=True)
    os.makedirs(os.path.dirname(preview), exist_ok=True)
    render_sheet(spec, obj, preview)

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True,
                              export_vertex_color="NAME", export_vertex_color_name="Color",
                              export_all_vertex_colors=False, export_animations=False,
                              export_yup=True)
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    print(f"BUILT {plant_id}: {tris} triangles at most ({busiest.label}), budget {budget} for '{spec['kind']}'")
    print(f"  size: {max(zs):.3f} m tall, {max(xs) - min(xs):.3f} x {max(ys) - min(ys):.3f} m wide")
    print(f"  glb:     {os.path.relpath(glb, ROOT)}")
    print(f"  preview: {os.path.relpath(preview, ROOT)}")


main()
# Leave without Blender's shutdown: on macOS, Blender 5.2.3 crashes while
# stopping its threads after a headless run, and every crash opens a
# "Blender quit unexpectedly" dialog. The build is already written.
sys.stdout.flush()
os._exit(0)
