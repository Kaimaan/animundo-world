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
      "length_m": 1.05,        # nose to rump, without the tail: scales everything
      "shoulder_m": 0.68,      # top of the back at the shoulders: sets the legs' length
      "tail_m": 0.18,          # the tail's length: shortens or lengthens it
      "colors": {"fur": "#8b7355", "belly": "#f0e8d8", "dark": "#2a2420"},
      "head": 1.1,             # the head, whole, about the neck joint
      "muzzle": 0.6,           # the face's length in front of the eyes
      "ears": 1.0,
      "leg_thickness": 1.3,    # legs' width, not length
      "paws": 1.5,             # the lowest part of each leg
      "body_girth": 1.1,       # the body's width and depth
      "tail_width": 0.7,
      "marks": ["ear_tufts", "ruff", "tail_tip"],
      "repaint": [{"part": "chest", "color": "belly"}]
    }

Factors are clamped to 0.4-2.5, so an edit can't break the body plan. Prints the
new spec, or writes it with --out. Then build it: tools/build_model.sh.
"""
import argparse
import copy
import json
import sys

MARKS = ("ear_tufts", "ruff", "tail_tip")
FACTORS = ("head", "muzzle", "ears", "leg_thickness", "paws", "body_girth", "tail_width")


def clamp(f):
    return max(0.4, min(2.5, float(f)))


def roles(spec):
    """bone name -> role, and part -> its bone's role."""
    by_bone = {b["name"]: b.get("role", "none") for b in spec["bones"]}
    return by_bone, {p["name"]: by_bone.get(p.get("bone"), "none") for p in spec["parts"]}


def bone(spec, name):
    return next(b for b in spec["bones"] if b["name"] == name)


def body_length(spec):
    """Nose to rump along z, without the tail."""
    _, role = roles(spec)
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
    for p in group(spec, ("body", "neck")):
        p["size"][0] *= f
        p["size"][1] *= f
    for p in spec["parts"]:   # legs keep reaching the body: widen their stance with it
        if p.get("bone") and bone(spec, p["bone"]).get("role") == "leg":
            p["at"][0] *= f
    for b in spec["bones"]:
        if b.get("role") == "leg":
            b["head"][0] *= f
            b["tail"][0] *= f


def tail_parts(spec):
    """Tail parts from the base outwards."""
    tail = group(spec, ("tail",))
    return sorted(tail, key=lambda p: -p["at"][2])


def tail_length(spec, target):
    tail = tail_parts(spec)
    if not tail:
        return
    base = tail[0]["at"][2] + tail[0]["size"][2] / 2
    end = tail[-1]["at"][2] - tail[-1]["size"][2] / 2
    now = base - end
    if now <= 0:
        return
    if target < now:   # keep the parts that fit, then pull the last one in to end exactly
        keep = [p for p in tail if base - (p["at"][2] - p["size"][2] / 2) <= target + 0.02] or tail[:1]
        drop = {p["name"] for p in tail if p not in keep}
        spec["parts"] = [p for p in spec["parts"] if p["name"] not in drop]
        used = {p.get("bone") for p in spec["parts"]}
        for b in reversed([b for b in spec["bones"] if b.get("role") == "tail"]):
            children = [c for c in spec["bones"] if c.get("parent") == b["name"]]
            if b["name"] not in used and not children:
                spec["bones"].remove(b)
    else:   # stretch the tail along its length, about its base
        f = min(2.5, target / now)
        for p in tail:
            p["at"][2] = base + (p["at"][2] - base) * f
            p["at"][1] = tail[0]["at"][1] + (p["at"][1] - tail[0]["at"][1]) * f
            p["size"][2] *= f
        for b in spec["bones"]:
            if b.get("role") == "tail":
                for k in ("head", "tail"):
                    b[k][2] = base + (b[k][2] - base) * f


def tail_width(spec, f):
    for p in group(spec, ("tail",)):
        p["size"][0] *= f
        p["size"][1] *= f


def add_marks(spec, marks):
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


def adapt(ref, edits):
    spec = copy.deepcopy(ref)
    for key in ("id", "name"):
        if key not in edits:
            raise ValueError(f"edits need {key!r}")
    for k in ("id", "name", "author"):
        if k in edits:
            spec[k] = edits[k]
    if "length_m" in edits:
        scale_all(spec, float(edits["length_m"]) / body_length(spec))
    if "head" in edits:
        scale_head(spec, clamp(edits["head"]))
    if "muzzle" in edits:
        scale_muzzle(spec, clamp(edits["muzzle"]))
    if "ears" in edits:
        scale_ears(spec, clamp(edits["ears"]))
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
    add_marks(spec, edits.get("marks", []))
    for r in edits.get("repaint", []):
        if r["color"] not in spec["colors"]:
            raise ValueError(f"repaint: {r['color']!r} is not a colour")
        for p in spec["parts"]:
            if p["name"] == r["part"]:
                p["color"] = r["color"]
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
