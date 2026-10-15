"""Shared by build_model.py (animals) and build_plant.py (plants): game
coordinates, the simple shapes a spec is made of, colours and the preview
renderer.

Coordinates in a spec are game coordinates in metres: x = left, y = up,
z = forward. Angles are in degrees.
"""

import bpy
import bmesh
import math
import os
from mathutils import Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


# --- coordinates -------------------------------------------------------------

def g2b(v):
    """Game (x, y up, z forward) -> Blender (x, y back, z up)."""
    return Vector((v[0], -v[2], v[1]))


AXIS = {"pitch": Vector((1, 0, 0)), "yaw": Vector((0, 0, 1)), "roll": Vector((0, -1, 0))}


def rot_matrix(rot):
    """[pitch, yaw, roll] in degrees, game axes. Pitch + tips the front down."""
    p, y, r = (math.radians(a) for a in rot)
    return (Matrix.Rotation(y, 3, AXIS["yaw"]) @ Matrix.Rotation(p, 3, AXIS["pitch"])
            @ Matrix.Rotation(r, 3, AXIS["roll"]))


# --- shapes --------------------------------------------------------------------

# a flat leaf, pointed at the front (+z), lying flat: one face
LEAF = [(0, 0.5), (-0.5, 0.1), (-0.35, -0.25), (0, -0.5), (0.35, -0.25), (0.5, 0.1)]
# cheaper versions for plants drawn thousands of times (`detail` 0.5 or less)
LEAF_LOW = [(0, 0.5), (-0.5, -0.05), (0, -0.5), (0.5, -0.05)]           # a diamond: 2 triangles
OCTA = [(0.5, 0, 0), (-0.5, 0, 0), (0, 0.5, 0), (0, -0.5, 0), (0, 0, 0.5), (0, 0, -0.5)]
OCTA_FACES = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]


def add_shape(bm, p):
    """Adds one spec part to the bmesh and returns its new vertices."""
    detail = p.get("detail", 1.0)
    shape = p["shape"]
    if shape == "ball" and detail <= 0.3:
        # a ball of 8 triangles: berries and tiny buds, drawn thousands of times
        geom = [bm.verts.new(v) for v in OCTA]
        for f in OCTA_FACES:
            bm.faces.new([geom[i] for i in f])
    elif shape == "box":
        geom = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    elif shape == "ball":
        geom = bmesh.ops.create_uvsphere(bm, u_segments=max(4, round(10 * detail)),
                                         v_segments=max(3, round(7 * detail)), radius=0.5)["verts"]
    elif shape == "leaf":
        geom = [bm.verts.new((x, y, 0.0)) for x, y in (LEAF_LOW if detail <= 0.5 else LEAF)]
        bm.faces.new(geom)
    else:
        top = {"cone": 0.0, "cylinder": 1.0, "taper": p.get("top", 0.5)}[shape]
        geom = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=max(3, round(8 * detail)),
                                     radius1=0.5, radius2=0.5 * top, depth=1.0)["verts"]
    s = p["size"]
    m = (Matrix.Translation(g2b(p["at"])) @ rot_matrix(p["rot"]).to_4x4()
         @ Matrix.Diagonal((s[0], s[2], s[1], 1.0)))
    bmesh.ops.transform(bm, matrix=m, verts=geom)
    return geom


# --- colour and rendering -------------------------------------------------------

def srgb_to_linear(hex_color):
    h = hex_color.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]


def setup_render(size):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.film_transparent = False
    sh = scene.display.shading
    sh.light = "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_shadows = True
    sh.show_cavity = True
    sh.cavity_type = "WORLD"
    sh.show_object_outline = True
    sh.background_type = "VIEWPORT"
    sh.background_color = (0.86, 0.9, 0.84)
    scene.world = scene.world or bpy.data.worlds.new("World")
    scene.world.color = (0.86, 0.9, 0.84)
    scene.view_settings.view_transform = "Standard"


def save_sheet(tiles, out_path, per_row=4):
    """Joins square tiles (numpy RGBA arrays) into rows and saves a PNG."""
    import numpy as np
    rows = [np.concatenate(tiles[r:r + per_row], axis=1) for r in range(0, len(tiles), per_row)]
    sheet = np.concatenate(rows[::-1], axis=0)  # Blender images start at the bottom
    h, w = sheet.shape[:2]
    out = bpy.data.images.new("sheet", w, h, alpha=True)
    out.pixels = sheet.ravel()
    out.filepath_raw = out_path
    out.file_format = "PNG"
    out.save()


def render_tile(size):
    """Renders the scene camera and returns the image as a numpy array."""
    import numpy as np
    tmp = os.path.join(bpy.app.tempdir, "shot.png")
    bpy.context.scene.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(tmp)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(size, size, 4)
    bpy.data.images.remove(img)
    return px
