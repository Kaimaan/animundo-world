#!/usr/bin/env python3
"""Check a new place (game decision 0060) before it goes live by itself.

A place is a name, its tiles, its animals and points at real latitude and
longitude, laid over ordinary tiles (places/<id>.json, game decision 0057).
Animundo Builder's place job writes one and publishes it with no person
looking first, so this check stands in for the play test. Run it on a world
checkout that already has the job's new animals and plants in it.

  schema   the place schema (schemas/place.schema.json)
  tiles    1 to 4 tiles in a rectangle, each given (a tile or a group file),
           and none of them another place's (places/)
  start    a start point, every start point inside the place's tiles, and
           the first playable animal can start where the first one is: on an
           open-sea tile it lives at sea ("open_sea": true)
  animals  every animal the place names is in animals/, the playable ones
           playable
  habitat  every animal the place names lives in the habitat of at least one
           of its tiles (its "habitats" in animal-list.json): the tile
           biome's habitat, "reef" where the biome has reef rock, "sea" at
           sea, and on land its waters too (wetland, river, lake), so a reef
           shark can't live in a taiga pond however many fish it finds
  laid     each tile with the place laid over it (its animals joined to the
           tile's, as the game's Places.lay does) passes check_tile.py:
           animals, region and food (what an animal can't find there is a
           gap, not a failure: game decision 0061)
  playable at least one tile passes, and every playable animal eats something
           (any of its diet, or any prey) on at least one of them: a player
           only starts where their animal can eat (0061)

Usage:
    python3 tools/check_place.py PLACE.json TILE_OR_GROUP.json [...]
    python3 tools/check_place.py PLACE.json GROUP.json --text

The JSON: {"ok": true/false, "place": "br_amazon_x",
           "results": [{"check", "status", "problems", "reason"?}, ...],
           "tiles": [{"tile", "ok", "results"}, ...]}
Exits 0 when ok, 1 when a check failed, 2 when a file can't be read.
"""
import argparse
import copy
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import check_animals  # noqa: E402
import check_tile  # noqa: E402
import tile_region  # noqa: E402
from check_tile import result, skip  # noqa: E402

N = 1024        # z10 tiles a side (game decision 0051)
MAX_LAT = 85.0511287798
ROLES = ("playable", "predators", "prey", "featured")


def tile_id(x, y):
    return f"z10_{x:04d}_{y:04d}"


def tile_at(lat, lon):
    """The z10 tile id at a point (Web Mercator, the game's Grid.tile_id)."""
    lat = max(-MAX_LAT, min(MAX_LAT, lat))
    x = int(((lon + 180.0) % 360.0) / 360.0 * N)
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * N)
    return tile_id(min(x, N - 1), min(max(y, 0), N - 1))


def schema_problems(place):
    import jsonschema
    with open(os.path.join(ROOT, "schemas", "place.schema.json"), encoding="utf-8") as f:
        schema = json.load(f)
    return [f"{'/'.join(map(str, e.path)) or 'place'}: {e.message}"
            for e in jsonschema.Draft202012Validator(schema).iter_errors(place)]


def other_places(own_id):
    """{tile id: place id} for every place in places/ but this one."""
    out = {}
    folder = os.path.join(ROOT, "places")
    for f in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if not f.endswith(".json"):
            continue
        with open(os.path.join(folder, f), encoding="utf-8") as fh:
            p = json.load(fh)
        if p.get("id") == own_id:
            continue
        for x, y in p.get("tiles", []):
            out[tile_id(x, y)] = p.get("id", f[:-5])
    return out


def read_tiles(paths):
    """{tile id: tile} from tile files and group files."""
    out = {}
    for path in paths:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        if isinstance(doc, dict) and "tiles" in doc and "grid" in doc:
            out.update({k: v for k, v in doc["tiles"].items() if isinstance(v, dict)})
        elif isinstance(doc, dict) and isinstance(doc.get("id"), str):
            out[doc["id"]] = doc
        else:
            raise ValueError(f"{path} is not a tile or a group file")
    return out


def tile_problems(place, tiles):
    cells = [tuple(c) for c in place["tiles"]]
    out = []
    if not 1 <= len(cells) <= 4:
        out.append(f"a place has 1 to 4 tiles, not {len(cells)}")
    if len(set(cells)) != len(cells):
        out.append("a tile is listed twice")
    xs, ys = {c[0] for c in cells}, {c[1] for c in cells}
    if cells and len(set(cells)) != (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1):
        out.append("the tiles aren't a rectangle")
    taken = other_places(place["id"])
    for c in cells:
        tid = tile_id(*c)
        if tid not in tiles:
            out.append(f"{tid} isn't given: pass its tile or group file")
        if tid in taken:
            out.append(f"{tid} is {taken[tid]}'s")
    return out


def start_problems(place, tiles, content):
    own = {tile_id(*c) for c in place["tiles"]}
    starts = [p for p in place.get("points", []) if p.get("kind") == "start"]
    if not starts:
        return ["the place has no start point"]
    out = []
    for p in starts:
        at = tile_at(p["lat"], p["lon"])
        if at not in own:
            out.append(f'start "{p["id"]}" is in {at}, not in the place\'s tiles')
    first = tile_at(starts[0]["lat"], starts[0]["lon"])
    animal = place["species"]["playable"][0]
    t = tiles.get(first)
    if t and check_tile.open_sea(t) and content.exists(animal) and not content.get_def(animal).get("open_sea"):
        out.append(f'start "{starts[0]["id"]}" is on the open sea, where {animal} can\'t start')
    return out


def animal_problems(place, content):
    out = []
    for role in ROLES:
        for a in place["species"].get(role, []):
            if not content.exists(a):
                out.append(f'"species.{role}": there is no animals/{a}.json')
            elif role == "playable" and not content.get_def(a).get("playable"):
                out.append(f'"species.playable": {a} isn\'t a playable animal')
    return out


def tile_habitats(t):
    """The habitats an animal may have to live on tile `t`."""
    bid = tile_region.biome_of(t)
    biome = tile_region.read_biome(bid) if tile_region.biome_file(bid) else {}
    h = biome.get("habitat") or t.get("habitat", "")
    out = {h}
    if h in ("sea", "open_ocean"):
        out.add("sea")
    else:
        out |= {"wetland", "river", "lake"}
    if (biome.get("terrain") or {}).get("reef"):
        out.add("reef")
    if h in ("boreal_forest", "rainforest"):
        out.add("forest")
    if h.startswith("boreal"):
        out |= {"boreal_forest", "boreal_lake"}
    return out


def habitat_problems(place, tiles):
    with open(os.path.join(ROOT, "animal-list.json"), encoding="utf-8") as f:
        listed = {a["id"]: a for a in json.load(f)["animals"]}
    given = [tiles[tile_id(x, y)] for x, y in place["tiles"] if tile_id(x, y) in tiles]
    if not given:
        return []
    here = set().union(*(tile_habitats(t) for t in given))
    out = []
    for role in ROLES:
        for a in place["species"].get(role, []):
            habitats = set(listed.get(a, {}).get("habitats", []))
            if not habitats:
                out.append(f'{a} has no "habitats" in animal-list.json')
            elif not habitats & here:
                out.append(f'{a} lives in {", ".join(sorted(habitats))}, and the place\'s tiles are {", ".join(sorted(here))}')
    return out


def laid(place, t):
    """The tile with the place laid over it: the place's animals first, then
    the tile's own (the game's Places.lay)."""
    t = copy.deepcopy(t)
    species = t.setdefault("species", {})
    for role in ("playable", "predators", "prey"):
        joined = list(place["species"].get(role, []))
        joined += [a for a in species.get(role, []) if a not in joined]
        species[role] = joined
    req = t.setdefault("requires", {"homes": [], "animals": []})
    for role in ("playable", "predators", "prey"):
        for a in species[role]:
            if a not in req.setdefault("animals", []):
                req["animals"].append(a)
    return t


def check(place, tiles):
    results = []
    probs = schema_problems(place)
    results.append(result("schema", probs))
    if probs:
        return results + [skip(c, "the place breaks its schema") for c in ("tiles", "start", "animals", "habitat", "laid", "playable")], []
    content = check_animals.Content(ROOT)
    results.append(result("tiles", tile_problems(place, tiles)))
    results.append(result("start", start_problems(place, tiles, content)))
    results.append(result("animals", animal_problems(place, content)))
    results.append(result("habitat", habitat_problems(place, tiles)))
    per_tile = []
    for x, y in place["tiles"]:
        tid = tile_id(x, y)
        if tid not in tiles:
            continue
        res = check_tile.check_tile(laid(place, tiles[tid]), published=True)
        per_tile.append({"tile": tid, "ok": all(r["status"] != "fail" for r in res), "results": res})
    if not per_tile:
        results.append(skip("laid", "no tile of the place is given"))
        results.append(skip("playable", "no tile of the place is given"))
        return results, per_tile
    results.append(result("laid", [f"{t['tile']} fails with the place laid over it" for t in per_tile if not t["ok"]]))
    good = [t for t in per_tile if t["ok"]]
    if not good:
        results.append(result("playable", ["no tile of the place passes, so no animal can play there"]))
        return results, per_tile
    hungry = []
    for a in place["species"].get("playable", []):
        fed = [t for t in good if a not in next((r.get("eats_nothing", []) for r in t["results"] if r["check"] == "food"), [])]
        if not fed:
            hungry.append(f"{a} finds none of its food on any of the place's tiles, so no one can start as it here (decision 0061)")
    results.append(result("playable", hungry))
    return results, per_tile


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("place", help="the place file")
    ap.add_argument("tiles", nargs="*", help="its tiles: tile or group files")
    ap.add_argument("--text", action="store_true", help="for people instead of JSON")
    args = ap.parse_args()
    try:
        with open(args.place, encoding="utf-8") as f:
            place = json.load(f)
        if not isinstance(place, dict):
            raise ValueError(f"{args.place} is not a place file")
        tiles = read_tiles(args.tiles)
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print(json.dumps({"ok": False, "error": str(e)}) if not args.text else f"ERROR: {e}")
        return 2
    results, per_tile = check(place, tiles)
    ok = all(r["status"] != "fail" for r in results) and all(t["ok"] for t in per_tile)
    report = {"ok": ok, "place": place.get("id"), "results": results, "tiles": per_tile}
    if args.text:
        check_tile.print_text(report)
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
