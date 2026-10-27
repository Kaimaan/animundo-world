#!/usr/bin/env python3
"""Make a new animal's model spec from a reference model and a short list of edits.

Writing a spec by hand means keeping about 80 positions and sizes consistent
in your head; a one-shot lynx written that way came out with floating legs
(2026-10-27). This does the geometry in code instead: scale the reference to
the new animal's real size, then apply edits to whole groups of parts (found
by their bones' roles), moving positions and sizes together so parts keep
overlapping. What's left to decide is a few words and factors, the edits.

Usage:
    python3 tools/adapt_model.py models/fox.json edits.json --out models/lynx.json

The edits file (every key but `id` and `name` is optional):

    {
      "id": "lynx", "name": "Eurasian lynx (Lynx lynx)", "author": "...",
      "length_m": 1.05,        # nose to rump, without the tail (an upright bird: its height): scales everything
      "shoulder_m": 0.68,      # top of the back at the shoulders: sets the legs' length
      "tail_m": 0.18,          # the tail's length: shortens or lengthens it; 0 removes it
      "colors": {"fur": "#8b7355", "belly": "#f0e8d8", "dark": "#2a2420"},
      "head": 1.1,             # the head, whole, about the neck joint
      "muzzle": 0.6,           # the face's length in front of the eyes
      "ears": 1.0,
      "leg_thickness": 1.3,    # legs' width, not length
      "paws": 1.5,             # the lowest part of each leg
      "body_girth": 1.1,       # the body's width and depth
      "tail_width": 0.7,
      "neck": 2.0,             # the neck's length; the head moves with it
      "mane": 1.3,             # the mane's height (parts named mane_*)
      "drop": ["antlers", "bell"],   # parts, groups (mane: mane_1, mane_2...) or bones to remove
      "marks": ["ear_tufts", "ruff", "tail_tip"],
      "horn_m": 0.3,           # with the horns mark: horn length, and how far they sweep back
      "horn_curve": 40,
      "repaint": [{"part": "chest", "color": "belly"}]
    }

Marks: ear_tufts, ruff, tail_tip, horns (a pair on the skull, colour `horn` or
`dark`), stripes (bands around the body and neck, colour `dark`).

Factors are clamped to 0.4-2.5, so an edit can't break the body plan. Prints the
new spec, or writes it with --out. Then build it: tools/build_model.sh.
"""
import argparse
import copy
import json
import math
import sys

MARKS = ("ear_tufts", "ruff", "tail_tip", "horns", "stripes")
FACTORS = ("head", "muzzle", "ears", "leg_thickness", "paws", "body_girth", "tail_width", "neck", "mane")


def clamp(f):
    return max(0.4, min(2.5, float(f)))


def roles(spec):
    """bone name -> role, and part -> its bone's role."""
    by_bone = {b["name"]: b.get("role", "none") for b in spec["bones"]}
    return by_bone, {p["name"]: by_bone.get(p.get("bone"), "none") for p in spec["parts"]}


def bone(spec, name):
    return next(b for b in spec["bones"] if b["name"] == name)


def upright(spec):
    """A body bone standing more than 60 degrees from level (a penguin): its length is its height."""
    b = next((b for b in spec["bones"] if b.get("role") == "body"), None)
    if b is None:
        return False
    dy = abs(b["tail"][1] - b["head"][1])
    dz = math.hypot(b["tail"][2] - b["head"][2], b["tail"][0] - b["head"][0])
    return math.degrees(math.atan2(dy, dz)) > 60


def body_length(spec):
    """Nose to rump along z, without the tail; for an upright animal, its standing height."""
    _, role = roles(spec)
    if upright(spec):
        return max(p["at"][1] + p["size"][1] / 2 for p in spec["parts"] if role[p["name"]] not in ("wing", "tail"))
    zs = []
    for p in spec["parts"]:
        if role[p["name"]] == "tail":
            continue
        zs += [p["at"][2] - p["size"][2] / 2, p["at"][2] + p["size"][2] / 2]
    return max(zs) - min(zs)


def shoulder(spec):
    """The top of the body parts above the front legs."""
    _, role = roles(spec)
    front = [b for b in spec["bones"] if b.get("role") == "leg" and b["head"][2] > 0]
    z = front[0]["head"][2] if front else 0.0
    tops = [p["at"][1] + p["size"][1] / 2 for p in spec["parts"]
            if role[p["name"]] in ("body",) and abs(p["at"][2] - z) <= p["size"][2] / 2 + 0.05]
    return max(tops) if tops else max(p["at"][1] + p["size"][1] / 2 for p in spec["parts"]
                                      if role[p["name"]] == "body")


def rotate(rot, v):
    """A part's local vector to the world, as the builder turns it (spec_shapes.rot_matrix)."""
    def turn(axis, a, v):   # Rodrigues, about a unit axis
        c, s = math.cos(a), math.sin(a)
        d = sum(axis[i] * v[i] for i in range(3))
        cr = [axis[1] * v[2] - axis[2] * v[1], axis[2] * v[0] - axis[0] * v[2], axis[0] * v[1] - axis[1] * v[0]]
        return [v[i] * c + cr[i] * s + axis[i] * d * (1 - c) for i in range(3)]
    p, y, r = (math.radians(a) for a in (rot or [0, 0, 0]))
    b = [v[0], -v[2], v[1]]   # game -> Blender
    b = turn([0, -1, 0], r, b)
    b = turn([1, 0, 0], p, b)
    b = turn([0, 0, 1], y, b)
    return [b[0], b[2], -b[1]]


def long_axis(p, direction=None):
    """The part's local axis (0, 1, 2) that is longest, or that lies closest to a direction."""
    if direction is None:
        return max(range(3), key=lambda i: p["size"][i])
    def along(i):
        e = [0, 0, 0]
        e[i] = 1
        w = rotate(p.get("rot"), e)
        return abs(sum(w[k] * direction[k] for k in range(3)))
    return max(range(3), key=along)


def descendants(spec, name):
    out, todo = set(), [name]
    while todo:
        n = todo.pop()
        for b in spec["bones"]:
            if b.get("parent") == n and b["name"] not in out:
                out.add(b["name"])
                todo.append(b["name"])
    return out


def neck_length(spec, f):
    """Stretch the neck along its bone; the head and everything on it moves to the new end."""
    nb = next((b for b in spec["bones"] if b.get("role") == "neck"), None)
    if nb is None:
        return
    n0, n1 = nb["head"], nb["tail"]
    d = [n1[i] - n0[i] for i in range(3)]
    ln = math.sqrt(sum(c * c for c in d)) or 1.0
    u = [c / ln for c in d]
    delta = [d[i] * (f - 1) for i in range(3)]
    for p in spec["parts"]:
        if p.get("bone") != nb["name"]:
            continue
        rel = [p["at"][i] - n0[i] for i in range(3)]
        s = sum(rel[i] * u[i] for i in range(3))
        p["at"] = [p["at"][i] + u[i] * s * (f - 1) for i in range(3)]   # along the neck only
        p["size"][long_axis(p, u)] *= f
    below = descendants(spec, nb["name"])
    for p in spec["parts"]:
        if p.get("bone") in below:
            p["at"] = [p["at"][i] + delta[i] for i in range(3)]
    for b in spec["bones"]:
        if b["name"] in below:
            b["head"] = [b["head"][i] + delta[i] for i in range(3)]
            b["tail"] = [b["tail"][i] + delta[i] for i in range(3)]
    nb["tail"] = [n1[i] + delta[i] for i in range(3)]


def mane(spec, f):
    """Raise or lower the mane ridge (parts mane_*) above the neck line."""
    nb = next((b for b in spec["bones"] if b.get("role") == "neck"), None)
    parts = [p for p in spec["parts"] if p["name"].startswith("mane")]
    if nb is None or not parts:
        return
    n0, n1 = nb["head"], nb["tail"]
    d = [n1[i] - n0[i] for i in range(3)]
    ln = math.sqrt(sum(c * c for c in d)) or 1.0
    u = [c / ln for c in d]
    for p in parts:
        rel = [p["at"][i] - n0[i] for i in range(3)]
        s = sum(rel[i] * u[i] for i in range(3))
        perp = [rel[i] - u[i] * s for i in range(3)]
        p["at"] = [n0[i] + u[i] * s + perp[i] * (1 + (f - 1) * 0.5) for i in range(3)]
        p["size"][1] *= f


def drop(spec, names):
    """Remove parts by name, group (mane: mane_1...) or bone, then bones left with nothing on them."""
    names = set(names)
    def gone(p):
        n = p["name"]
        return n in names or any(n.startswith(k + "_") for k in names) or p.get("bone") in names
    found = [p for p in spec["parts"] if gone(p)]
    if not found:
        raise ValueError(f"drop: no parts match {sorted(names)}")
    emptied = {p.get("bone") for p in found} | (names & {b["name"] for b in spec["bones"]})
    spec["parts"] = [p for p in spec["parts"] if not gone(p)]
    used = {p.get("bone") for p in spec["parts"]}
    for b in reversed(list(spec["bones"])):   # a bone left with nothing on it and below it goes too
        if b["name"] in emptied and b["name"] not in used and not any(c.get("parent") == b["name"] for c in spec["bones"]):
            spec["bones"].remove(b)


def scale_all(spec, f):
    for p in spec["parts"]:
        p["at"] = [c * f for c in p["at"]]
        p["size"] = [c * f for c in p["size"]]
    for b in spec["bones"]:
        b["head"] = [c * f for c in b["head"]]
        b["tail"] = [c * f for c in b["tail"]]


def legs_to(spec, target):
    """Stretch the legs (ground stays at 0) and lift everything else, to a shoulder height."""
    legs = [b for b in spec["bones"] if b.get("role") == "leg"]
    if not legs:
        return
    top = sum(b["head"][1] for b in legs) / len(legs)
    now = shoulder(spec)
    f = max(0.6, min(1.8, 1 + (target - now) / top))
    lift = top * (f - 1)
    by_bone, role = roles(spec)
    for p in spec["parts"]:
        if role[p["name"]] == "leg":
            p["at"][1] *= f
            p["size"][1] *= f
        else:
            p["at"][1] += lift
    for b in spec["bones"]:
        if b.get("role") == "leg":
            b["head"][1] *= f
            b["tail"][1] *= f
        else:
            b["head"][1] += lift
            b["tail"][1] += lift


def about(p, centre, f, axes=(0, 1, 2)):
    """Scale a part about a point: its position and its size together."""
    for i in axes:
        p["at"][i] = centre[i] + (p["at"][i] - centre[i]) * f
        p["size"][i] *= f


def group(spec, wanted):
    _, role = roles(spec)
    return [p for p in spec["parts"] if role[p["name"]] in wanted]


def scale_head(spec, f):
    neck_joint = bone(spec, "head")["head"] if any(b["name"] == "head" for b in spec["bones"]) else None
    if neck_joint is None:
        return
    for p in group(spec, ("head", "ear")):
        about(p, neck_joint, f)
    for b in spec["bones"]:
        if b.get("role") in ("ear",) or b["name"] == "head":
            for k in ("head", "tail"):
                b[k] = [neck_joint[i] + (b[k][i] - neck_joint[i]) * f for i in range(3)]


def scale_muzzle(spec, f):
    """The parts of the head in front of the eyes, along z."""
    heads = group(spec, ("head",))
    eyes = [p for p in heads if p["name"].startswith("eye")]
    if not eyes:
        return
    z0 = eyes[0]["at"][2]
    for p in heads:
        if p["at"][2] > z0 + 0.005 and not p["name"].startswith("eye"):
            p["at"][2] = z0 + (p["at"][2] - z0) * f
            p["size"][2] *= f


def scale_ears(spec, f):
    for b in spec["bones"]:
        if b.get("role") != "ear":
            continue
        base = b["head"]
        for p in spec["parts"]:
            if p.get("bone") == b["name"]:
                about(p, base, f)
        b["tail"] = [base[i] + (b["tail"][i] - base[i]) * f for i in range(3)]


def leg_thickness(spec, f):
    for p in group(spec, ("leg",)):
        p["size"][0] *= f
        p["size"][2] *= f


def paws(spec, f):
    for b in spec["bones"]:
        if b.get("role") != "leg":
            continue
        mine = [p for p in spec["parts"] if p.get("bone") == b["name"]]
        if not mine:
            continue
        low = min(mine, key=lambda p: p["at"][1])
        low["size"] = [low["size"][0] * f, low["size"][1] * f, low["size"][2] * f]
        low["at"][1] = low["size"][1] / 2   # still standing on the ground


def body_girth(spec, f):
    _, role = roles(spec)
    trunk = [p for p in spec["parts"] if not p.get("separate")
             and (role[p["name"]] in ("body", "neck") or role[p["name"]] == "fin")]   # a fish's rear half rides its fin bones
    surface = [p for p in spec["parts"] if p.get("separate") and role[p["name"]] in ("body", "neck", "fin")]
    moves = []
    for p in surface:   # on the skin (gills, eyes, fins): move out as far as the skin beneath moves
        under = [q for q in trunk if abs(q["at"][2] - p["at"][2]) <= q["size"][2] / 2] or trunk
        if not under:
            continue
        q = min(under, key=lambda q: abs(q["at"][2] - p["at"][2]))
        dx, dy = p["at"][0] - q["at"][0], p["at"][1] - q["at"][1]
        n = math.hypot(dx / (q["size"][0] / 2), dy / (q["size"][1] / 2)) or 1.0
        moves.append((p, dx / n * (f - 1), dy / n * (f - 1)))
    for p, mx, my in moves:
        p["at"][0] += mx
        p["at"][1] += my
    for p in trunk:
        p["size"][0] *= f
        p["size"][1] *= f
    for p in spec["parts"]:   # legs keep reaching the body: widen their stance with it
        if p.get("bone") and bone(spec, p["bone"]).get("role") == "leg":
            p["at"][0] *= f
    for b in spec["bones"]:
        if b.get("role") == "leg":
            b["head"][0] *= f
            b["tail"][0] *= f


def tail_base(spec):
    first = next((b for b in spec["bones"] if b.get("role") == "tail"), None)
    return first["head"] if first else None


def tail_parts(spec):
    """Tail parts from the base outwards, measured in 3D: a tail may hang down (a horse) or reach back (a fox)."""
    tail = group(spec, ("tail",))
    base = tail_base(spec)
    if base is None:
        return sorted(tail, key=lambda p: -p["at"][2])
    return sorted(tail, key=lambda p: dist(p["at"], base))


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def tail_length(spec, target):
    tail = tail_parts(spec)
    base = tail_base(spec)
    if not tail or base is None:
        return
    reach = lambda p: dist(p["at"], base) + max(p["size"]) / 2
    now = max(reach(p) for p in tail)
    if now <= 0:
        return
    if target < 0.02:   # no tail to speak of (a capybara): remove it
        drop(spec, [b["name"] for b in spec["bones"] if b.get("role") == "tail"])
        return
    if target < now:   # keep the parts that fit
        keep = [p for p in tail if reach(p) <= target + 0.02] or tail[:1]
        cut = {p["name"] for p in tail if p not in keep}
        spec["parts"] = [p for p in spec["parts"] if p["name"] not in cut]
        used = {p.get("bone") for p in spec["parts"]}
        for b in reversed([b for b in spec["bones"] if b.get("role") == "tail"]):
            children = [c for c in spec["bones"] if c.get("parent") == b["name"]]
            if b["name"] not in used and not children:
                spec["bones"].remove(b)
    else:   # stretch the tail along its own line, about its base
        f = min(2.5, target / now)
        for p in tail:
            u = [p["at"][i] - base[i] for i in range(3)]
            n = math.sqrt(sum(c * c for c in u)) or 1.0
            p["at"] = [base[i] + u[i] * f for i in range(3)]
            p["size"][long_axis(p, [c / n for c in u])] *= f
        for b in spec["bones"]:
            if b.get("role") == "tail":
                for k in ("head", "tail"):
                    b[k] = [base[i] + (b[k][i] - base[i]) * f for i in range(3)]


def tail_width(spec, f):
    for p in group(spec, ("tail",)):
        p["size"][0] *= f
        p["size"][1] *= f


def add_marks(spec, marks, edits=None):
    edits = edits or {}
    names = {p["name"] for p in spec["parts"]}
    dark = "dark" if "dark" in spec["colors"] else list(spec["colors"])[-1]
    for mark in marks:
        if mark == "ear_tufts":
            for ear in [p for p in spec["parts"] if p.get("bone") and bone(spec, p["bone"]).get("role") == "ear"
                        and not p["name"].startswith("ear_in")]:
                w, h, d = ear["size"]
                tip = ear["at"][1] + h / 2
                spec["parts"].append({
                    "name": "tuft" + ear["name"][len("ear"):], "shape": "taper", "top": 0.1,
                    "size": [w * 0.22, h * 0.35, max(d, 0.012)],
                    "at": [ear["at"][0], tip + h * 0.1, ear["at"][2]], "rot": ear.get("rot", [0, 0, 0]),
                    "color": dark, "bone": ear["bone"], "mirror": ear.get("mirror", False), "separate": True})
        elif mark == "ruff" and "cheeks" in names:
            cheeks = next(p for p in spec["parts"] if p["name"] == "cheeks")
            cheeks["size"] = [cheeks["size"][0] * 1.7, cheeks["size"][1] * 2.0, cheeks["size"][2] * 1.2]
            cheeks["at"][2] -= cheeks["size"][2] * 0.25
        elif mark == "tail_tip":
            tail = tail_parts(spec)
            if tail:
                tail[-1]["color"] = dark
        elif mark == "horns":
            add_horns(spec, float(edits.get("horn_m", 0)), float(edits.get("horn_curve", 30)))
        elif mark == "stripes":
            add_stripes(spec)


def melt_limit(spec):
    """The thinnest part the builder melts into the skin (build_model.py: skin_settings, keep)."""
    skin = spec.get("skin") or {}
    pts = [p["at"] for p in spec["parts"]]
    span = max(max(v[2] for v in pts) - min(v[2] for v in pts), max(v[1] for v in pts))
    voxel = skin.get("voxel", 1 / 70)
    if voxel < 0.2:
        voxel *= span + min(0.05, span * 0.15)
    return skin.get("keep", 2.0) * voxel


def add_horns(spec, length, curve):
    """A pair of horns on top of the skull: three tapers each, sweeping back by `curve` degrees."""
    heads = [p for p in group(spec, ("head",)) if not p.get("separate")]
    if not heads:
        raise ValueError("horns: the reference has no head parts")
    skull = max(heads, key=lambda p: p["at"][1] + p["size"][1] / 2)
    w, h, _ = skull["size"]
    length = length or h * 1.2
    color = "horn" if "horn" in spec["colors"] else ("dark" if "dark" in spec["colors"] else list(spec["colors"])[-1])
    x, y, z = w * 0.28, skull["at"][1] + h * 0.5 - h * 0.12, skull["at"][2]
    width = max(w * 0.22, length * 0.16)
    seg = length / 3
    for i in range(3):
        a = math.radians(curve * (i + 0.5) / 3)
        dy, dz = math.cos(a), -math.sin(a)
        spec["parts"].append({
            "name": f"horn{i + 1}_l", "shape": "taper", "top": 0.7,
            "size": [round(width, 4), round(seg * 1.3, 4), round(width, 4)],
            "at": [x + seg * 0.08, y + dy * seg / 2, z + dz * seg / 2], "rot": [-math.degrees(a), 0, 0],
            "color": color, "bone": skull["bone"], "mirror": True, "separate": True, "detail": 0.5})
        x, y, z, width = x + seg * 0.16, y + dy * seg, z + dz * seg, width * 0.7


def add_stripes(spec):
    """Dark bands around the body and neck: thin rings, a little proud of the skin, kept as their
    own pieces like a fish's bars (the skin is too coarse to carry narrow bands). The parts along
    each run (the trunk, the neck) share a grid; each ring spans every part it cuts through."""
    if "dark" not in spec["colors"]:
        raise ValueError("stripes need a colour named dark")
    _, role = roles(spec)
    period = body_length(spec) / 16
    line = {}
    for b in spec["bones"]:
        d = [b["tail"][i] - b["head"][i] for i in range(3)]
        n = math.sqrt(sum(c * c for c in d)) or 1.0
        line[b["name"]] = [c / n for c in d]
    cuts = {}
    for p in spec["parts"]:
        if p.get("separate") or role[p["name"]] not in ("body", "neck") or p["name"].startswith(("mane", "belly")):
            continue
        ax = long_axis(p, line[p["bone"]])
        e = [0, 0, 0]
        e[ax] = 1
        u = rotate(p.get("rot"), e)
        half = p["size"][ax] / 2
        c = sum(p["at"][i] * u[i] for i in range(3))
        run = (role[p["name"]], tuple(round(x, 1) for x in u))
        for k in range(math.ceil((c - half * 0.85) / period), math.floor((c + half * 0.85) / period) + 1):
            t = k * period - c
            s = math.sqrt(max(0.0, 1 - (t / half) ** 2)) if p["shape"] == "ball" else 1.0
            if s >= 0.6:
                cuts.setdefault((run, k), []).append((p, ax, u, t, s))
    n = 0
    for (run, k), found in sorted(cuts.items()):
        p0, ax, u, t0, _ = max(found, key=lambda f: f[0]["size"][(f[1] + 1) % 3] * f[4])
        centre = [p0["at"][j] + u[j] * t0 for j in range(3)]
        lo, hi = [0.0] * 3, [0.0] * 3
        for j in range(3):   # extents along the ring's own cross axes, over every part it cuts
            if j == ax:
                continue
            e = [0, 0, 0]
            e[j] = 1
            w = rotate(p0.get("rot"), e)
            for p, pax, _, t, s in found:
                off = sum((p["at"][i] + u[i] * t - centre[i]) * w[i] for i in range(3))
                r = p["size"][j if pax == ax else (j + pax) % 3] * s / 2
                lo[j], hi[j] = min(lo[j], off - r), max(hi[j], off + r)
        size, shift = [0.0] * 3, [0.0] * 3
        for j in range(3):
            if j != ax:
                size[j] = (hi[j] - lo[j]) * 1.06
                e = [0, 0, 0]
                e[j] = 1
                w = rotate(p0.get("rot"), e)
                shift = [shift[i] + w[i] * (hi[j] + lo[j]) / 2 for i in range(3)]
        # a short cylinder, which keeps its full width out to the rim (a flat ball thins to nothing there),
        # turned onto the run's line: a cylinder's axis is its local y, pitched 90 degrees onto z
        pitch, yaw, roll = p0.get("rot", [0, 0, 0])
        if ax != 2 or yaw or roll:
            continue
        n += 1
        spec["parts"].append({"name": f"stripe_{n}", "shape": "cylinder",
                              "size": [size[0] * 1.02, period * 0.42, size[1] * 1.02],
                              "at": [centre[i] + shift[i] for i in range(3)], "rot": [pitch + 90, 0, 0],
                              "color": "dark", "bone": p0["bone"], "separate": True})
    skin = spec.setdefault("skin", {})
    if isinstance(skin, dict):   # the rings take about 30 triangles each: a large animal's budget
        skin["triangles"] = max(skin.get("triangles", 1000), 1500)


def keep_thick(spec, ref, scale):
    """No edit may make a part thinner than the builder's melting limit (build_model.py: keep x
    voxel), or than the reference part itself if that was already thinner: below it a part stays
    a loose piece and floats (a vole's tail at tail_width 0.4 became dashes behind the body)."""
    limit = melt_limit(spec) * 1.1
    was = {p["name"]: p["size"] for p in ref["parts"]}
    _, role = roles(spec)
    for p in spec["parts"]:   # separate parts are meant to be thin (ears, eyes), except a thin tail's
        if p["name"] in was and (not p.get("separate") or role[p["name"]] == "tail"):
            p["size"] = [max(c, min(limit, r * scale)) for c, r in zip(p["size"], was[p["name"]])]


def adapt(ref, edits):
    spec = copy.deepcopy(ref)
    for key in ("id", "name"):
        if key not in edits:
            raise ValueError(f"edits need {key!r}")
    for k in ("id", "name", "author"):
        if k in edits:
            spec[k] = edits[k]
    scale = 1.0
    if "length_m" in edits:
        scale = float(edits["length_m"]) / body_length(spec)
        scale_all(spec, scale)
    if "head" in edits:
        scale_head(spec, clamp(edits["head"]))
    if "muzzle" in edits:
        scale_muzzle(spec, clamp(edits["muzzle"]))
    if "ears" in edits:
        scale_ears(spec, clamp(edits["ears"]))
    if "drop" in edits:
        drop(spec, edits["drop"])
    if "neck" in edits:
        neck_length(spec, clamp(edits["neck"]))
    if "mane" in edits:
        mane(spec, clamp(edits["mane"]))
    if "body_girth" in edits:
        body_girth(spec, clamp(edits["body_girth"]))
    if "shoulder_m" in edits:
        legs_to(spec, float(edits["shoulder_m"]))
    if "leg_thickness" in edits:
        leg_thickness(spec, clamp(edits["leg_thickness"]))
    if "paws" in edits:
        paws(spec, clamp(edits["paws"]))
    if "tail_m" in edits:
        tail_length(spec, float(edits["tail_m"]))
    if "tail_width" in edits:
        tail_width(spec, clamp(edits["tail_width"]))
    if "colors" in edits:
        spec["colors"].update(edits["colors"])
    for mark in edits.get("marks", []):
        if mark not in MARKS:
            raise ValueError(f"unknown mark {mark!r}; marks: {', '.join(MARKS)}")
    add_marks(spec, edits.get("marks", []), edits)
    for r in edits.get("repaint", []):
        if r["color"] not in spec["colors"]:
            raise ValueError(f"repaint: {r['color']!r} is not a colour")
        for p in spec["parts"]:
            if p["name"] == r["part"]:
                p["color"] = r["color"]
    keep_thick(spec, ref, scale)
    for p in spec["parts"]:
        p["at"] = [round(c, 4) for c in p["at"]]
        p["size"] = [round(c, 4) for c in p["size"]]
    for b in spec["bones"]:
        b["head"] = [round(c, 4) for c in b["head"]]
        b["tail"] = [round(c, 4) for c in b["tail"]]
    return spec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("reference")
    ap.add_argument("edits")
    ap.add_argument("--out")
    args = ap.parse_args()
    with open(args.reference, encoding="utf-8") as f:
        ref = json.load(f)
    with open(args.edits, encoding="utf-8") as f:
        edits = json.load(f)
    edits.pop("reference", None)   # an edits file may say which reference it was written for
    try:
        spec = adapt(ref, edits)
    except (ValueError, KeyError, StopIteration) as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    text = json.dumps(spec, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
