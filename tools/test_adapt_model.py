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

    for e in errors:
        print("ERROR: " + e, file=sys.stderr)
    print("adapt_model: sizes and marks as expected" if not errors else f"{len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
