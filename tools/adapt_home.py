#!/usr/bin/env python3
"""Make a new home from the closest home and a short list of choices.

A made rainforest whose land height was written by hand ended up under the
water, an island in a lake (2026-10-27). This keeps every number that makes a
place playable in code: the land always stands above the water, the edge
follows the kind of water, and densities come from a few named levels. What's
left to choose is words and colours, the choices.

Usage:
    python3 tools/adapt_home.py homes/boreal_forest.json choices.json --out homes/rainforest.json

The choices file (see homes/examples/ for whole ones):

    {
      "id": "rainforest",
      "description": "A warm wet rainforest ...",
      "land": "flat",                 # flat | rolling | hilly
      "water": "river",               # river | lake | pools | sea | none: the main water
      "wetness": "wet",               # dry | wet | very_wet: ponds, bogs and streams besides it
      "water_name": "Slow river",
      "tropical": true,               # no seasons and no snow (near the equator)
      "palette": {"ground_lush": "#...", "ground_dry": "#...", "ground_high": "#...", "dirt": "#...",
                  "rock": "#...", "sand": "#...", "water_deep": "#...", "water_shallow": "#..."},
      "trees": {"density": "dense",   # none | sparse | medium | dense
                "mix": [{"shape": "round", "leaves": "#2f7a3a", "trunk": "#6b4a33", "weight": 60,
                         "food": "browse", "autumn": null}]},
      "grass": "some",                # none | some | lush
      "flowers": [{"name": "heliconia", "color": "#e8452c"}],
      "plants": [{"model": "bracken", "food": null}],   # library plant specs only
      "water_life": {"reeds": "some", "lilies": "many", "pondweed": "some"},
      "food": [{"kind": "browse", "names": ["kapok leaves"]}],
      "sources": ["https://..."]
    }

Prints the home, or writes it with --out. Then: python3 tools/homes.py check.
"""
import argparse
import copy
import json
import sys

WATER = 8   # the game's default water level (terrain.water_level)

LAND = {   # land height always above the water: the lowest ground is base_height
    "flat":    {"base_height": WATER + 2, "relief": 4,  "frequency": 0.02, "rock_ridges": 0.0},
    "rolling": {"base_height": WATER + 1, "relief": 9,  "frequency": 0.03, "rock_ridges": 0.15},
    "hilly":   {"base_height": WATER + 1, "relief": 14, "frequency": 0.04, "rock_ridges": 0.4},
}
WETNESS = {   # ponds in the low ground, bogs and side streams
    "dry":      {"lakes": 0.03, "bogs": 0, "streams": 0},
    "wet":      {"lakes": 0.15, "bogs": 1, "streams": 1},
    "very_wet": {"lakes": 0.3,  "bogs": 2, "streams": 2},
}
TREES = {"none": 0.0, "sparse": 0.004, "medium": 0.014, "dense": 0.03}
GRASS = {"none": 0.0, "some": 0.15, "lush": 0.3}
LIFE = {"none": 0.0, "some": 0.15, "many": 0.35}
SHAPES = {"spruce", "pine", "birch", "round", "rowan"}
BOGS = [{"x": 0.3, "z": 0.62, "radius": 55}, {"x": 0.66, "z": 0.4, "radius": 45}]
STREAMS = [{"width": 4, "points": [[0.18, 0.7], [0.27, 0.6], [0.33, 0.55], [0.42, 0.5]]},
           {"width": 4, "points": [[0.62, 0.22], [0.58, 0.32], [0.62, 0.42], [0.72, 0.48]]}]


def pick(table, key, what):
    if key not in table:
        raise ValueError(f"{what} must be one of {', '.join(table)}, not {key!r}")
    return table[key]


def hex_ok(value, what):
    if not (isinstance(value, str) and len(value) == 7 and value.startswith("#")):
        raise ValueError(f"{what} must be a colour like #5f9445, not {value!r}")
    return value


def adapt(base, c):
    home = copy.deepcopy(base)
    for key in ("id", "description"):
        if not c.get(key):
            raise ValueError(f"choices need {key!r}")
    home["id"] = c["id"]
    home["name"] = c.get("name", c["id"].replace("_", " ").capitalize() + " home")
    home["description"] = c["description"]
    home["about"] = f"Home template made by tools/adapt_home.py from {base['id']}."
    home["based_on"] = base.get("based_on", base["id"])

    land = pick(LAND, c.get("land", "rolling"), "land")
    wet = pick(WETNESS, c.get("wetness", "wet"), "wetness")
    water = c.get("water", "lake")
    if water not in ("river", "lake", "pools", "sea", "none"):
        raise ValueError(f"water must be river, lake, pools, sea or none, not {water!r}")
    terrain = home.setdefault("terrain", {})
    for k in ("water_level", "height", "seabed"):
        terrain.pop(k, None)
    terrain.update(land)
    terrain["lakes"] = wet["lakes"]
    terrain["rock_above"] = int(land["base_height"] + land["relief"] + 3)   # rock only on the highest tops
    terrain["edge"] = "lake" if water in ("lake", "sea") else "none"        # an island only by a lake or the sea
    name = c.get("water_name") or {"river": "The river", "lake": "The lake", "sea": "The sea",
                                    "pools": "Forest pool"}.get(water, "")
    if water == "river":   # a long river across the land, clear of the middle where animals start
        home["lakes"] = [{"name": name, "x": 0.5, "z": 0.3, "length": 1.4, "width": 0.05,
                          "angle": 8, "depth": 4, "islands": 1}]
    elif water == "lake":
        home["lakes"] = [{"name": name, "x": 0.5, "z": 0.3, "length": 0.6, "width": 0.3,
                          "angle": -10, "depth": 6, "islands": 3}]   # the land in the middle stays dry
    else:
        home["lakes"] = []
    bogs = wet["bogs"] + (2 if water == "pools" else 0)
    home["bogs"] = [dict(b, name=(name if water == "pools" else "Pool") if i == 0 else "Pool")
                    for i, b in enumerate((BOGS * 2)[:bogs])]
    home["streams"] = copy.deepcopy(STREAMS[:wet["streams"]])

    if c.get("tropical"):
        home.pop("seasons", None)
    if "palette" in c:
        for k, v in c["palette"].items():
            home.setdefault("palette", {})[k] = hex_ok(v, f"palette.{k}")

    trees = c.get("trees", {})
    mix = []
    for t in trees.get("mix", []):
        if t.get("shape") not in SHAPES:
            raise ValueError(f"tree shape must be one of {', '.join(sorted(SHAPES))}, not {t.get('shape')!r}")
        tree = {"shape": t["shape"], "weight": int(t.get("weight", 50)),
                "leaves": hex_ok(t["leaves"], "tree leaves"), "trunk": hex_ok(t["trunk"], "tree trunk")}
        if t.get("food"):
            tree["food"] = t["food"]
        if t.get("autumn"):
            tree["autumn"] = hex_ok(t["autumn"], "tree autumn")
        mix.append(tree)
    home["trees"] = {"density": pick(TREES, trees.get("density", "medium"), "trees.density"), "mix": mix}

    ground = home.setdefault("ground_cover", {})
    ground["grass"] = pick(GRASS, c.get("grass", "some"), "grass")
    flowers = c.get("flowers", [])[:4]
    ground["flowers"] = 0.03 if flowers else 0.0
    ground["flower_colors"] = [hex_ok(f["color"], "flower colour") for f in flowers]
    ground["flower_names"] = [f["name"] for f in flowers]
    kept = {p["model"]: p for p in base.get("ground_cover", {}).get("plants", [])}
    plants = []
    for p in c.get("plants", []):
        plant = copy.deepcopy(kept.get(p["model"], {"model": p["model"], "density": 0.08}))
        plants.append(plant)
    ground["plants"] = plants

    life = c.get("water_life", {})
    home["lake_life"] = {k: pick(LIFE, life.get(k, "some"), f"water_life.{k}") for k in ("reeds", "lilies", "pondweed")}

    by_kind = {f["kind"]: f for f in base.get("food", [])}
    food = []
    for f in c.get("food", []):
        item = copy.deepcopy(by_kind.get(f["kind"], {"kind": f["kind"], "weight": 10}))
        item["names"] = list(f["names"])
        food.append(item)
    home["food"] = food
    home["fish"] = []          # a made home starts with no living things of its own
    home["migrants"] = []
    home["places"] = []
    home["animals"] = {"playable": [], "predators": [], "prey": []}
    home["sources"] = list(c.get("sources") or [])
    return home


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("base")
    ap.add_argument("choices")
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true", help="run the region checks on the result, at a sample spot")
    args = ap.parse_args()
    with open(args.base, encoding="utf-8") as f:
        base = json.load(f)
    with open(args.choices, encoding="utf-8") as f:
        choices = json.load(f)
    choices.pop("base", None)   # an example may say which home it was written for
    try:
        home = adapt(base, choices)
    except (ValueError, KeyError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    if args.check:
        import os, tempfile
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import validate_region
        region = {k: v for k, v in home.items() if k not in ("about", "based_on")}
        region.update({"id": "xx_check_" + home["id"], "name": "Check", "country": "Check",
                       "center": {"lat": -3.0 if choices.get("tropical") else 61.0, "lon": 26.0},
                       "animals": {"playable": ["fox"], "predators": [], "prey": []}})
        with tempfile.TemporaryDirectory() as t:
            path = os.path.join(t, region["id"] + ".json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(region, f)
            problems = validate_region.check(path)
        for line in problems:
            print("FAIL " + line)
        if problems:
            sys.exit(1)
    text = json.dumps(home, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
