#!/usr/bin/env python3
"""A tile's layers over its biome (game proposal 0043), the way the game
builds them (scripts/tile_layers.gd): the tile's own `plants`, library ids,
replace the biome's trees and ground plants part by part, never merging.

Used by tools/check_tile.py; tools/food.py then works out the tile's food."""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GROWS = ("density", "on", "habitat", "near_trees", "food", "names", "amount")
MAX_GROUND = 24   # cover and water plants together, after a blend (Nuuksio has 22)
MAX_TREES = 6


def spec(folder, pid):
    path = os.path.join(ROOT, "models", folder, f"{pid}.json")
    if not (isinstance(pid, str) and pid.isidentifier() and os.path.isfile(path)):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def plant_entry(pid, density=None):
    s = spec("plants", pid)
    if s is None:
        return None
    e = {"model": pid}
    e.update({k: v for k, v in s.get("grows", {}).items() if k in GROWS})
    if density is not None:
        e["density"] = density
    return e


def tree_entry(tid, share):
    s = spec("trees", tid)
    if s is None:
        return None
    e = {"weight": max(share, 0.001) * 100}
    if "game_shape" in s:
        e.update({"shape": s["game_shape"], "plant": tid})
        e.update({k: v for k, v in s.get("colors", {}).items() if k in ("leaves", "trunk", "autumn")})
    else:
        e["shape"] = tid
    if "food" in s.get("grows", {}):
        e["food"] = s["grows"]["food"]
    return e


def problems(plants):
    """What's wrong with a tile's `plants` (spec 02 §2), as messages."""
    if not isinstance(plants, dict) or set(plants) - {"trees", "cover", "water", "tree_density"}:
        return ['"plants" must be {"trees", "cover", "water"} (each optional)']
    out = []
    for part, folder, amount in (("trees", "trees", "share"), ("cover", "plants", "density"), ("water", "plants", "density")):
        items = plants.get(part, [])
        if not isinstance(items, list):
            out.append(f'"plants.{part}" must be a list')
            continue
        seen = set()
        for i, p in enumerate(items):
            if not (isinstance(p, dict) and set(p) == {"id", amount}):
                out.append(f'"plants.{part}[{i}]" must be {{"id", "{amount}"}}')
                continue
            if spec(folder, p["id"]) is None:
                out.append(f'"plants.{part}[{i}]": there is no models/{folder}/{p["id"]}.json')
            if not (isinstance(p[amount], (int, float)) and not isinstance(p[amount], bool) and 0 < p[amount] <= 1):
                out.append(f'"plants.{part}[{i}].{amount}" must be above 0 and at most 1')
            if p["id"] in seen:
                out.append(f'"plants.{part}": {p["id"]} is listed twice')
            seen.add(p["id"])
    if isinstance(plants.get("trees"), list) and len(plants["trees"]) > MAX_TREES:
        out.append(f'"plants.trees" has {len(plants["trees"])} species; at most {MAX_TREES}')
    ground = sum(len(plants.get(k, [])) for k in ("cover", "water") if isinstance(plants.get(k), list))
    if ground > MAX_GROUND:
        out.append(f'"plants" has {ground} cover and water plants; at most {MAX_GROUND} (a cheap phone builds each one)')
    return out


def ids(plants):
    """(plant ids, tree ids) a tile's `plants` names."""
    return ([p["id"] for k in ("cover", "water") for p in plants.get(k, [])],
            [p["id"] for p in plants.get("trees", [])])


def use_plants(region, plants):
    """The tile's `plants` over the biome's region, in place."""
    if isinstance(plants.get("trees"), list):
        trees = region.setdefault("trees", {})
        trees["mix"] = [e for e in (tree_entry(p["id"], p["share"]) for p in plants["trees"]) if e]
        if "tree_density" in plants:
            trees["density"] = plants["tree_density"]
    if isinstance(plants.get("cover"), list) or isinstance(plants.get("water"), list):
        gc = region.setdefault("ground_cover", {})
        keep = [p for p in gc.get("plants", [])
                if ("seabed" in p.get("on", []) and not isinstance(plants.get("water"), list))
                or ("seabed" not in p.get("on", []) and not isinstance(plants.get("cover"), list))]
        for part in ("cover", "water"):
            for p in plants.get(part, []) or []:
                e = plant_entry(p["id"], p["density"])
                if e:
                    if part == "water":
                        e.setdefault("on", ["seabed"])
                    keep.append(e)
        gc["plants"] = keep
