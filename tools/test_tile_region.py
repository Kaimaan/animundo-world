#!/usr/bin/env python3
"""tools/tile_region.py gives the golden places, and check_tile.py judges the same place.

tests/tile_region/ holds real tiles (the boreal n_414_478 and n_414_480 and the
Helsinki shore n_415_479 with its coast, as published), a lab tile with a blend
and the Helsinki shore with its own plants, each with the place the game
builds from it (<name>.place.json). The game's tools/check_tile_region.gd
holds the game to the same files. Here:

  golden    the converter gives each expected place exactly
  forest    the boreal tiles keep the squirrel and the bee: mushrooms grow on
            the forest floor and flowers give nectar (inbox #152), and their
            food check passes
  one       check_tile.py's region is the converter's place, only named and
            without the fields a region file doesn't have

Usage: python3 tools/test_tile_region.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_tile  # noqa: E402
import tile_region  # noqa: E402

errors = []


def check(ok, why):
    if not ok:
        errors.append(why)
        print("FAIL:", why)


def golden(name):
    with open(os.path.join(tile_region.GOLDEN, name), encoding="utf-8") as f:
        return json.load(f)


names = sorted(f[:-len(".tile.json")] for f in os.listdir(tile_region.GOLDEN) if f.endswith(".tile.json"))
check(len(names) >= 5, f"only {len(names)} golden tiles")
for n in names:
    tile = golden(n + ".tile.json")
    made = tile_region.place(tile)
    check(tile_region.dump(made) == tile_region.dump(golden(n + ".place.json")),
          f"{n}: the converter no longer gives its golden place (python3 tools/tile_region.py golden shows which;"
          " remake them with --write if the change is meant)")
    t, _ = check_tile.as_home(tile)
    region, why = check_tile.region_of(t)
    check(region is not None, f"{n}: check_tile.py made no region ({why})")
    if region:
        mine = {k: v for k, v in made.items() if k not in check_tile.GAME_ONLY}
        theirs = {k: v for k, v in region.items() if k not in ("id", "name", "country", "author")}
        check(mine == theirs, f"{n}: check_tile.py's region isn't the converter's place")

for n in ("n_414_478", "n_414_480"):
    tile = golden(n + ".tile.json")
    place = tile_region.place(tile)
    check({"squirrel", "bee"} <= set(place["animals"]["playable"]), f"{n}: the squirrel and the bee aren't playable")
    gc = place["ground_cover"]
    check(any(isinstance(p.get("food"), dict) and p["food"].get("kind") == "mushrooms" or p.get("food") == "mushrooms"
              for p in gc.get("plants", [])), f"{n}: no mushrooms on the forest floor")
    check(float(gc.get("flowers", 0)) > 0 and gc.get("flower_colors"), f"{n}: no flowers, so no nectar")
    food = [r for r in check_tile.check_tile(tile) if r["check"] == "food"][0]
    check(food["status"] == "pass", f"{n}: its food check fails: {food['problems']}")

print(f"tile region test: {len(names)} golden tiles, {len(errors)} errors")
sys.exit(1 if errors else 0)
