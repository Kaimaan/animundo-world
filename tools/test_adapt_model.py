#!/usr/bin/env python3
"""adapt_model.py reaches the sourced sizes, and makes what its marks promise.

D19 (the game's plan.md): an animal whose start model is a poor match gets a
free spec from the builder's loop, then this tool sizes it with only its
sourced length, shoulder height and tail. The lab's kangaroo (tests/adapt/
kangaroo_free.json, written by Muse Spark in the sheets lab) has a short
three-ball tail and stands on its back legs: its tail has to reach the
sourced 100 cm, and its legs must not stretch to a "shoulder height" that
is really its standing height. Builder tests replay this kangaroo, so a
change here shows up first.

Usage: python3 tools/test_adapt_model.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import adapt_model  # noqa: E402


def load(*path):
    with open(os.path.join(ROOT, *path), encoding="utf-8") as f:
        return json.load(f)


def tail_reach(spec):
    base = adapt_model.tail_base(spec)
    tail = adapt_model.tail_parts(spec)
    if base is None or not tail:
        return 0.0
    def half(p):
        u = [p["at"][i] - base[i] for i in range(3)]
        n = sum(c * c for c in u) ** 0.5
        return p["size"][adapt_model.long_axis(p, [c / n for c in u] if n else None)] / 2
    return max(adapt_model.dist(p["at"], base) + half(p) for p in tail)


def near(errors, what, got, want, within=0.03):
    if abs(got - want) > want * within:
        errors.append(f"{what}: {got:.3f}, should be {want:.3f} (within {within:.0%})")


def main():
    errors = []

    # the lab kangaroo, sized with its sourced numbers only: as the builder's newshape step does
    free = load("tests", "adapt", "kangaroo_free.json")
    if not adapt_model.on_back_legs(free):
        errors.append("kangaroo_free: not seen as standing on its back legs")
    k = adapt_model.adapt(free, {"id": "kangaroo", "name": "Red kangaroo",
                                 "length_m": 1.4, "shoulder_m": 1.5, "tail_m": 1.0})
    near(errors, "kangaroo tail", tail_reach(k), 1.0)
    near(errors, "kangaroo length", adapt_model.body_length(k), 1.4)
    scaled = adapt_model.adapt(free, {"id": "kangaroo", "name": "Red kangaroo", "length_m": 1.4})
    near(errors, "kangaroo shoulder (its legs keep their proportion)",
         adapt_model.shoulder(k), adapt_model.shoulder(scaled), 0.001)

    # tails both ways, from the library: a long stretch and a cut
    vole = load("models", "vole.json")
    v = adapt_model.adapt(vole, {"id": "v", "name": "v", "tail_m": tail_reach(vole) * 4})
    near(errors, "vole tail stretched 4 times", tail_reach(v), tail_reach(vole) * 4)
    lynx = adapt_model.adapt(load("models", "fox.json"), load("models", "examples", "edits", "lynx.json"))
    near(errors, "lynx tail cut short", tail_reach(lynx), 0.18, 0.1)

    # no library animal stands on its back legs: their shoulder_m still sets the legs
    for name in sorted(os.listdir(os.path.join(ROOT, "models"))):
        if name.endswith(".json") and adapt_model.on_back_legs(load("models", name)):
            errors.append(f"models/{name}: seen as standing on its back legs")

    # a hedgehog from the vole has spines on its back, in its own colour
    edits = load("models", "examples", "edits", "hedgehog.json")
    edits.pop("reference")
    h = adapt_model.adapt(vole, edits)
    spines = [p for p in h["parts"] if p["name"].startswith("spine")]
    if len(spines) < 30:
        errors.append(f"hedgehog: {len(spines)} spines, should be at least 30")
    if any(p["color"] != "spine" or p["bone"] != "body" for p in spines):
        errors.append("hedgehog: spines should be colour spine, on the body bone")
    top = max(p["at"][1] + p["size"][1] / 2 for p in h["parts"] if not p["name"].startswith("spine"))
    if not any(p["at"][1] > top for p in spines):
        errors.append("hedgehog: no spine stands above its back")
    if h["skin"]["triangles"] > 1000:
        errors.append(f"hedgehog: skin.triangles {h['skin']['triangles']} is over a playable animal's 1000")

    # a jaguar from the fox: open rings (a dark patch with the coat's colour on it), a thin tail
    edits = load("models", "examples", "edits", "jaguar.json")
    edits.pop("reference")
    j = adapt_model.adapt(load("models", "fox.json"), edits)
    rings = [p for p in j["parts"] if p["name"].startswith("rosette_") and not p["name"].startswith("rosette_in")]
    centres = [p for p in j["parts"] if p["name"].startswith("rosette_in")]
    if not 12 <= len(rings) <= 30 or len(centres) != len(rings):
        errors.append(f"jaguar: {len(rings)} rosettes and {len(centres)} centres, should be 12-30 of each")
    if any(p["color"] != "dark" for p in rings) or any(p["color"] in ("dark", "spot") for p in centres):
        errors.append("jaguar: rings should be dark round a centre in the coat's own colour")
    if any(p["name"].startswith("spot_") for p in j["parts"]):
        errors.append("jaguar: rosettes must not add whole-coat spots")
    fox_tail = max(max(p["size"][0], p["size"][1]) for p in adapt_model.tail_parts(load("models", "fox.json")))
    cat_tail = max(max(p["size"][0], p["size"][1]) for p in adapt_model.tail_parts(j))
    scale = adapt_model.body_length(j) / adapt_model.body_length(load("models", "fox.json"))
    if cat_tail > fox_tail * scale * 0.45:
        errors.append(f"jaguar: tail {cat_tail:.3f} wide, should be under half the fox's brush")

    # an anaconda from the grass snake: many blotches along the whole body, each smaller than it is thick
    snake = load("models", "examples", "grass_snake.json")
    a = adapt_model.adapt(snake, {"id": "anaconda", "name": "Green anaconda", "length_m": 4.6, "marks": ["blotches"]})
    blotches = [p for p in a["parts"] if p["name"].startswith("blotch_")]
    segs = [p for p in a["parts"] if p["name"].startswith("seg_")]
    if not 20 <= len(blotches) <= 64:
        errors.append(f"anaconda: {len(blotches)} blotches, should be 20-64")
    bones = {p["bone"] for p in blotches}
    if len([b for b in bones if b.startswith("spine_")]) < 5:
        errors.append(f"anaconda: blotches on {sorted(bones)}, should run down the body's segments")
    thick = max(sorted(p["size"])[1] for p in segs)
    if any(max(p["size"]) > thick * 1.6 for p in blotches):
        errors.append("anaconda: a blotch is much bigger than the body is thick")

    # an iguana from the lizard: one row of small spikes along the top of the back
    li = load("models", "lizard.json")
    g = adapt_model.adapt(li, {"id": "green_iguana", "name": "Green iguana", "length_m": 0.5, "marks": ["crest"]})
    crest = [p for p in g["parts"] if p["name"].startswith("crest_")]
    if len(crest) < 8:
        errors.append(f"iguana: {len(crest)} crest spikes, should be at least 8")
    if any(abs(p["at"][0]) > 1e-6 for p in crest):
        errors.append("iguana: crest spikes should stand on the middle line of the back")
    back = max(p["at"][1] + p["size"][1] / 2 for p in g["parts"] if p["name"] in ("trunk", "hips"))
    if any(p["size"][1] > back for p in crest):
        errors.append("iguana: crest spikes taller than the animal: a hedgehog's coat, not a crest")

    # the big cat is a reference elsewhere, made from the fox with the jaguar's body and no marks
    cat = load("models", "examples", "big_cat.json")
    if any(p["name"].startswith(("rosette", "spot")) for p in cat["parts"]):
        errors.append("big_cat: a reference should carry no coat marks")

    # a clownfish from the perch has three wide white bands, evenly spaced, nose to tail
    edits = load("models", "examples", "edits", "clownfish.json")
    edits.pop("reference")
    c = adapt_model.adapt(load("models", "perch.json"), edits)
    bands = sorted((p for p in c["parts"] if p["name"].startswith("band")), key=lambda p: p["at"][2])
    if len(bands) != 3 or any(p["color"] != "band" for p in bands):
        errors.append(f"clownfish: {len(bands)} bands, should be 3 in colour band")
    elif not bands[0]["at"][2] < bands[1]["at"][2] < bands[2]["at"][2]:
        errors.append("clownfish: bands should sit one behind another along the body")
    if any(p["name"].startswith("stripe") for p in c["parts"]):
        errors.append("clownfish: bands must not add thin stripes")

    for e in errors:
        print("ERROR: " + e, file=sys.stderr)
    print("adapt_model: sizes and marks as expected" if not errors else f"{len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
