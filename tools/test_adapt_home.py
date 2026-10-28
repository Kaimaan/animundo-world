#!/usr/bin/env python3
"""adapt_home.py makes every example home with the numbers the tile grid needs.

Every home has the one water level (8) and states its height, 32 or 64
(Proposal 0038, T87). The special places keep what made them work in the
game: the mountain is 64 tall with bare rock, the polar ice home keeps its
icebergs and frozen sea, and a sea home's bay is deep enough for swimmers.
Builder tests replay these examples through the tool, so a change here
shows up first.

Usage: python3 tools/test_adapt_home.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import adapt_home  # noqa: E402
import validate_region  # noqa: E402
import tempfile  # noqa: E402


def make(name):
    with open(os.path.join(ROOT, "homes", "boreal_forest.json"), encoding="utf-8") as f:
        base = json.load(f)
    with open(os.path.join(ROOT, "homes", "examples", name + ".json"), encoding="utf-8") as f:
        choices = json.load(f)
    choices.pop("base", None)
    return choices, adapt_home.adapt(base, choices)


def region_problems(home):
    region = {k: v for k, v in home.items() if k not in ("about", "based_on", "ecoregions", "habitat")}
    region.update({"id": "xx_check_" + home["id"], "name": "Check", "country": "Check",
                   "center": {"lat": 61.0, "lon": 26.0}, "animals": {"playable": ["fox"], "predators": [], "prey": []}})
    with tempfile.TemporaryDirectory() as t:
        path = os.path.join(t, region["id"] + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(region, f)
        return validate_region.check(path)


def main():
    errors = []
    names = sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, "homes", "examples")) if f.endswith(".json"))
    for name in names:
        choices, home = make(name)
        t = home["terrain"]
        if t.get("water_level", 8) != 8:
            errors.append(f"{name}: water level {t['water_level']}, not the one water level 8")
        want = 64 if choices.get("land") == "mountains" else 32
        if t.get("height") != want:
            errors.append(f"{name}: terrain.height is {t.get('height')}, should be {want}")
        if t["base_height"] <= 8:
            errors.append(f"{name}: the land's lowest ground ({t['base_height']}) isn't above the water")
        if choices.get("water") == "sea" and not any(l.get("depth") == adapt_home.SEA_DEPTH for l in home["lakes"]):
            errors.append(f"{name}: a sea home needs its {adapt_home.SEA_DEPTH}-block bay for swimmers")
        if choices.get("ice") == "polar":
            ice = home.get("ice", {})
            if not (ice.get("icebergs") and ice.get("frozen_water") and ice.get("glacier_above")):
                errors.append(f"{name}: polar ice needs icebergs, frozen water and glaciers: {ice}")
            elif ice["glacier_above"] > t["height"] - 4:
                errors.append(f"{name}: glaciers above {ice['glacier_above']} don't fit under the height {t['height']}")
        for p in region_problems(home):
            errors.append(f"{name}: {p}")
    for e in errors:
        print("ERROR: " + e, file=sys.stderr)
    print(f"adapt_home: {len(names)} example homes as expected" if not errors else f"{len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
