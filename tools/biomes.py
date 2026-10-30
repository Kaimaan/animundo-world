#!/usr/bin/env python3
"""Biomes and the homes made from them (game proposal 0043, phase 3).

A biome (biomes/<id>.json) is a home in layers: it names a land style
(lands/<id>.json) for its colours, sky and roughness, lists its plants by id
from the library where it can, and gives small-life names instead of a food
list (the food is worked out, food/rules.json). Whatever the layers can't say
yet stays written out: a palette colour of its own, a tree with no species
file, its lakes and bogs.

homes/ is made from biomes/ by this tool, for the tools and the builder that
still read whole homes. Never edit homes/<id>.json: edit the biome and run
`flatten`. CI runs `flatten --check`.

Usage:
    python3 tools/biomes.py flatten           # biomes/ -> homes/
    python3 tools/biomes.py flatten --check   # fails when homes/ isn't up to date
    python3 tools/biomes.py split <home id> <land id>   # a home written out -> biomes/<id>.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import layers  # noqa: E402

BIOMES = os.path.join(ROOT, "biomes")
HOMES = os.path.join(ROOT, "homes")
SMALL_LIFE = ("insects", "water_bugs", "bottom_bugs", "carrion", "grass", "water_plants")
LAYERED = ("land", "plants", "small_life")
# a home's fields in the order homes/ has always had them
ORDER = ["id", "name", "country", "center", "description", "about", "author", "based_on", "ecoregions", "habitat",
         "terrain", "palette", "sky", "seasons", "trees", "ground_cover", "lakes", "places", "lake_life", "food",
         "fish", "migrants", "animals", "sources", "bogs", "streams", "ice", "caves"]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump(data):
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def flat(biome):
    """The whole home a biome stands for."""
    home = layers.resolve(biome)
    for k in LAYERED:
        home.pop(k, None)
    ordered = {k: home[k] for k in ORDER if k in home}
    ordered.update({k: v for k, v in home.items() if k not in ordered})
    return ordered


def flatten(check=False):
    stale = []
    for f in sorted(os.listdir(BIOMES)):
        if not f.endswith(".json"):
            continue
        text = dump(flat(load(os.path.join(BIOMES, f))))
        path = os.path.join(HOMES, f)
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old == text:
            continue
        if check:
            stale.append(f)
        else:
            with open(path, "w", encoding="utf-8") as out:
                out.write(text)
            print(f"wrote homes/{f}")
    for f in sorted(os.listdir(HOMES)):
        if f.endswith(".json") and not os.path.exists(os.path.join(BIOMES, f)):
            stale.append(f"{f} (no biome)")
    if stale:
        print("homes/ isn't made from biomes/: " + ", ".join(stale) + ". Edit the biome, then run python3 tools/biomes.py flatten.")
        return 1
    if check:
        print("homes/ is made from biomes/")
    return 0


def split(home_id, land_id):
    """A written-out home as a biome on `land_id`, keeping whatever the layers can't say."""
    home = load(os.path.join(HOMES, f"{home_id}.json"))
    style = layers.land(land_id)
    if style is None:
        raise SystemExit(f"there is no lands/{land_id}.json")
    biome = {}
    for k, v in home.items():
        if k in ("palette", "sky", "seasons", "ice", "terrain") and isinstance(v, dict) and isinstance(style.get(k), dict):
            own = {kk: vv for kk, vv in v.items() if style[k].get(kk) != vv}
            if own:
                biome[k] = own
            continue
        if k == "food":
            continue
        biome[k] = v
        if k == "habitat":
            biome["land"] = land_id
    plants = {}
    mix = home.get("trees", {}).get("mix", [])
    total = sum(t.get("weight", 1) for t in mix) or 1
    entries = [layers.tree_entry(t.get("plant", ""), 1) if t.get("plant") else None for t in mix]
    same = all(e and all(t.get(f) == e.get(f) for f in ("shape", "plant", "food", "leaves", "trunk", "autumn")) for t, e in zip(mix, entries))
    if mix and same:
        plants["trees"] = [{"id": t["plant"], "share": round(t.get("weight", 1) / total, 3)} for t in mix]
        biome["trees"] = {k: v for k, v in home["trees"].items() if k != "mix"}
    cover = home.get("ground_cover", {}).get("plants", [])
    if cover and all(p == layers.plant_entry(p["model"], p.get("density")) for p in cover):
        under = [p for p in cover if "seabed" in p.get("on", [])]
        plants["cover"] = [{"id": p["model"], "density": p["density"]} for p in cover if p not in under]
        if under:
            plants["water"] = [{"id": p["model"], "density": p["density"]} for p in under]
        biome["ground_cover"] = {k: v for k, v in home["ground_cover"].items() if k != "plants"}
    small = {f["kind"]: f.get("names", []) for f in home.get("food", []) if f.get("kind") in SMALL_LIFE and f.get("names")}
    out = {}
    for k, v in biome.items():
        out[k] = v
        if k == "ground_cover":
            if plants:
                out["plants"] = plants
            if small:
                out["small_life"] = small
    if "ground_cover" not in biome:
        if plants:
            out["plants"] = plants
        if small:
            out["small_life"] = small
    # the biome must stand for the same land as the home did
    made = flat(out)
    for k in ("terrain", "palette", "sky", "seasons", "ice", "lakes", "bogs", "streams", "ground_cover", "lake_life", "fish", "migrants"):
        if made.get(k) != home.get(k):
            raise SystemExit(f"{home_id}: the biome's {k} isn't the home's: {made.get(k)} vs {home.get(k)}")
    for a, b in zip(made.get("trees", {}).get("mix", []), mix):
        if any(a.get(f) != b.get(f) for f in ("shape", "plant", "food", "leaves", "trunk", "autumn")):
            raise SystemExit(f"{home_id}: a tree differs: {a} vs {b}")
    os.makedirs(BIOMES, exist_ok=True)
    with open(os.path.join(BIOMES, f"{home_id}.json"), "w", encoding="utf-8") as f:
        f.write(dump(out))
    print(f"wrote biomes/{home_id}.json on {land_id}: plants {sorted(plants)}, small life {sorted(small)}")
    return 0


def main(argv):
    if argv[:1] == ["flatten"]:
        return flatten(check="--check" in argv)
    if argv[:1] == ["split"] and len(argv) == 3:
        return split(argv[1], argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
