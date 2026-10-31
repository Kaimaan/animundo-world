#!/usr/bin/env python3
"""Work out a place's food from what grows and lives there (game proposal 0043).

A place's food used to be written by hand, apart from its plants and animals,
so the two drifted: a sea home listed bird cherry berries with no bird cherry
in it. This tool works the food out instead, from food/rules.json, the
plants' and trees' own `grows`, the land and the animals, and says where the
written food disagrees.

Usage:
    python3 tools/food.py derive homes/sea_717.json   # the worked-out food, as JSON
    python3 tools/food.py report                       # every home and region: what disagrees
    python3 tools/food.py report regions/fi_nuuksio.json

The report lists, per file:
  written, nothing makes it   a kind in `food` that no plant, tree, water or animal here gives
  made, not written           a kind this place makes that `food` leaves out
  names nothing here gives    plant food names that no plant or tree here has
  tree with no species        a trees.mix entry with no `plant`, so its food has no names
  animal can't eat            an animal here whose diet kind the worked-out food lacks
Exit status 1 only for "animal can't eat" (the rule of decision 0011); the rest
is information while the layers move in.
"""
import glob
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def library(folder):
    out = {}
    d = os.path.join(ROOT, "models", folder)
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if f.endswith(".json"):
            out[f[:-5]] = load(os.path.join(d, f))
    return out


RULES = load(os.path.join(ROOT, "food", "rules.json"))
PLANTS = library("plants")
TREES = library("trees")
ANIMALS = {f[:-5]: load(os.path.join(ROOT, "animals", f)) for f in os.listdir(os.path.join(ROOT, "animals"))
           if f.endswith(".json") and f != "archetypes.json"}


def _kind(food):
    return str(food.get("kind", "")) if isinstance(food, dict) else str(food or "")


def _add(made, kind, names, source):
    if not kind:
        return
    e = made.setdefault(kind, {"kind": kind, "names": [], "from": []})
    for n in names:
        if n not in e["names"]:
            e["names"].append(n)
    if source not in e["from"]:
        e["from"].append(source)


def animals_of(d):
    a = d.get("animals", {})
    ids = []
    for group in ("playable", "prey", "predators"):
        for i in a.get(group, []) if isinstance(a, dict) else []:
            if i not in ids:
                ids.append(i)
    return ids


def derive(d):
    """{kind: {kind, names, from}} for a place or home, and notes on what it couldn't place."""
    made, notes = {}, []
    written = {f.get("kind"): f for f in d.get("food", [])}
    for kind, names in d.get("small_life", {}).items():   # a layered place's or biome's own names (0043)
        written[kind] = {"kind": kind, "names": names}
    gc = d.get("ground_cover", {})
    # plants on the ground and the seabed
    for p in gc.get("plants", []):
        spec = PLANTS.get(p.get("model"), {})
        grows = spec.get("grows", {})
        food = p.get("food", grows.get("food"))
        if _kind(food):
            _add(made, _kind(food), p.get("names", grows.get("names", [])), p.get("model"))
    # trees
    for t in d.get("trees", {}).get("mix", []):
        shape = t.get("shape")   # a tree built from a spec is its own species; a game shape ("birch") isn't one
        sid = t.get("plant") or (shape if shape in TREES and "game_shape" not in TREES[shape] else None)
        grows = TREES.get(sid, {}).get("grows", {}) if sid else {}
        if not sid:
            notes.append(("tree with no species", f'{t.get("shape")} (food {t.get("food", "none")})'))
        # the place's own food for this tree, and what the species gives anyway
        _add(made, _kind(t.get("food")), grows.get("names", []) if _kind(t.get("food")) == _kind(grows.get("food")) else [], sid or shape)
        _add(made, _kind(grows.get("food")), grows.get("names", []), sid)
        for k, names in grows.get("more_food", {}).items():
            _add(made, k, names, sid)
        if grows.get("bark"):
            name = TREES[sid].get("name", sid).split()[-1].lower()
            _add(made, "bark", [f"{name} bark"], sid)
    # water plants in lakes and the sea
    life = d.get("lake_life", {})
    if any(float(life.get(k, 0)) > 0 for k in ("lilies", "pondweed")):
        _add(made, "water_plants", written.get("water_plants", {}).get("names", []), "lake_life")
    # the land
    if float(gc.get("grass", 0)) > 0:
        _add(made, "grass", written.get("grass", {}).get("names", []), "grass")
    habitat = d.get("habitat", "")
    terrain = d.get("terrain", {})
    sea = habitat in ("sea", "open_ocean")   # open_ocean: an open-sea tile (game proposal 0047)
    fresh = not sea and (bool(d.get("lakes")) or bool(d.get("streams")) or bool(d.get("bogs"))
                                  or float(terrain.get("lakes", 0)) > 0)
    water = fresh or sea or "coast" in d   # a coast: a tile's mask of where its land is
    when = {"land": True, "fresh_water": fresh, "water": water}
    for kind, rule in RULES["kinds"].items():
        if rule["from"] == "small_life" and when.get(rule.get("when"), False):
            _add(made, kind, written.get(kind, {}).get("names", []), "small_life")
    # large animals leave carrion; with "or": "small_life", large animals the place doesn't list die there too
    carrion = RULES["kinds"].get("carrion", {})
    if carrion.get("or") == "small_life" and when.get(carrion.get("when"), False):
        _add(made, "carrion", written.get("carrion", {}).get("names", []), "small_life")
    for a in animals_of(d):
        tags = ANIMALS.get(a, {}).get("tags", [])
        if any(t in RULES["large_animals"] for t in tags):
            _add(made, "carrion", [a.replace("_", " ") + " remains"], a)
    return made, notes


def eaten(d):
    """The food kinds the animals here eat (animals not in animals/ eat nothing)."""
    return {k for a in animals_of(d) for k in ANIMALS.get(a, {}).get("diet", []) or []}


def as_food(made, d=None):
    """Worked-out food as a region's `food` list, with the rules' weights (a region file's shape).
    With the place `d`, a kind no animal there eats gets weight 0, as in the game
    (scripts/tile_layers.gd food()): it isn't scattered, but a visitor still finds it."""
    wanted = eaten(d) if d is not None else None
    out = []
    for kind, e in made.items():
        rule = RULES["kinds"].get(kind, {})
        if "amount" not in rule and "weight" not in rule:
            continue   # eaten off the plant itself (mushrooms), never scattered or listed
        f = {"kind": kind, "names": e["names"]}
        if "amount" in rule:
            f["amount"] = rule["amount"]
        else:
            f["weight"] = rule.get("weight", 0) if wanted is None or kind in wanted else 0
        out.append(f)
    return out


def report(path):
    d = load(path)
    layered = "food" not in d   # a layered place: its food is worked out, so there's nothing to drift
    if "land" in d or "plants" in d:
        import layers
        d = layers.resolve(d)
    made, notes = derive(d)
    written = {} if layered else {f.get("kind"): f for f in d.get("food", [])}
    lines = list(notes)
    for kind in written:
        if kind not in made:
            lines.append(("written, nothing makes it", f'{kind} ({", ".join(written[kind].get("names", [])) or "no names"})'))
    for kind in made if not layered else []:
        if kind not in written:
            lines.append(("made, not written", f'{kind} (from {", ".join(made[kind]["from"])})'))
    for kind, e in made.items():
        if kind in written and RULES["kinds"].get(kind, {}).get("from") == "plants" and e["names"]:
            stray = [n for n in written[kind].get("names", []) if n not in e["names"]]
            if stray:
                lines.append(("names nothing here gives", f'{kind}: {", ".join(stray)}'))
    bad = False
    for a in animals_of(d):
        for kind in ANIMALS.get(a, {}).get("diet", []) or []:
            if kind != "nectar" and kind not in made:
                lines.append(("animal can't eat", f"{a}: {kind}"))
                bad = True
    print(f"{'problem' if bad else 'ok':7} {os.path.relpath(path, ROOT)}")
    for what, detail in lines:
        print(f"          {what}: {detail}")
    return not bad


def worked_out(d):
    """A place's `food` list, worked out the way the game does (scripts/tile_layers.gd food())."""
    return as_food(derive(d)[0], d)


def main(argv):
    if len(argv) >= 2 and argv[0] == "derive":
        import layers
        made, notes = derive(layers.resolve(load(argv[1])))
        print(json.dumps({"food": list(made.values()), "notes": [f"{a}: {b}" for a, b in notes]}, indent=2, ensure_ascii=False))
        return 0
    if argv and argv[0] == "report":
        files = argv[1:] or sorted(glob.glob(os.path.join(ROOT, "homes", "*.json")) + glob.glob(os.path.join(ROOT, "regions", "*.json")))
        ok = all([report(f) for f in files])
        return 0 if ok else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
