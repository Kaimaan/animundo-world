#!/usr/bin/env python3
"""Check region files before they are merged.

Usage:
    python3 tools/validate_region.py              # all files in regions/
    python3 tools/validate_region.py regions/x.json

Exits non-zero and explains every problem if a file is invalid.
Keep the lists below in sync with the game code (world.gd, food.gd). Animals are read from animals/.
"""
import json
import os
import re
import sys

TREE_SHAPES = {"spruce", "pine", "birch", "round", "rowan"}
FOOD_KINDS = {"clover", "carrot", "berries", "insects", "water_bugs", "browse"}
EDGES = {"lake", "none"}
MIGRANT_KINDS = {"geese", "cranes"}  # flocks the game can draw (scripts/migrants.gd)
PLANT_GROUND = {"grass", "rock", "sand"}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
ID = re.compile(r"^[a-z]{2}_[a-z0-9_]+$")

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
# every animal is a file in animals/ (archetypes.json holds shared defaults)
ANIMALS = {f[:-5] for f in os.listdir(os.path.join(ROOT, "animals"))
           if f.endswith(".json") and f != "archetypes.json"}
# every plant is a spec in models/plants/, built by tools/build_model.sh
PLANTS = {f[:-5] for f in os.listdir(os.path.join(ROOT, "models", "plants")) if f.endswith(".json")}


def check(path):
    errors = []

    def err(msg):
        errors.append(msg)

    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:  # noqa: BLE001
        return [f"not valid JSON: {e}"]

    file_id = os.path.splitext(os.path.basename(path))[0]
    if d.get("id") != file_id:
        err(f'"id" must equal the file name ("{file_id}")')
    if not ID.match(file_id):
        err('file name must be <country code>_<place>, lowercase, e.g. "fi_nuuksio"')
    for key in ("name", "country", "description", "author"):
        if not isinstance(d.get(key), str) or not d.get(key).strip():
            err(f'"{key}" must be a non-empty text')

    c = d.get("center", {})
    if not (isinstance(c.get("lat"), (int, float)) and -90 <= c["lat"] <= 90):
        err('"center.lat" must be a number between -90 and 90')
    if not (isinstance(c.get("lon"), (int, float)) and -180 <= c["lon"] <= 180):
        err('"center.lon" must be a number between -180 and 180')

    def num(section, key, lo, hi):
        v = d.get(section, {}).get(key)
        if v is None:
            return
        if not isinstance(v, (int, float)) or not lo <= v <= hi:
            err(f'"{section}.{key}" must be a number from {lo} to {hi}')

    num("terrain", "base_height", 2, 14)
    num("terrain", "relief", 0, 16)
    num("terrain", "frequency", 0.005, 0.15)
    num("terrain", "rock_ridges", 0, 1)
    num("terrain", "rock_above", 6, 28)
    num("terrain", "lakes", 0, 1)
    edge = d.get("terrain", {}).get("edge")
    if edge is not None and edge not in EDGES:
        err(f'"terrain.edge" must be one of {sorted(EDGES)}')

    for section in ("palette", "sky"):
        for k, v in d.get(section, {}).items():
            if not (isinstance(v, str) and HEX.match(v)):
                err(f'"{section}.{k}" must be a colour like "#5f9445"')

    seasons = d.get("seasons", {})
    if not isinstance(seasons, dict):
        err('"seasons" must be an object')
        seasons = {}
    for k in ("spring", "summer", "autumn", "winter"):
        v = seasons.get(k)
        if v is not None and not (isinstance(v, str) and re.match(r"^(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$", v)):
            err(f'"seasons.{k}" must be a start date like "09-20" (month-day)')
    if "snow" in seasons and not isinstance(seasons["snow"], bool):
        err('"seasons.snow" must be true or false')

    for i, m in enumerate(d.get("migrants", [])):
        if m.get("kind") not in MIGRANT_KINDS:
            err(f'"migrants[{i}].kind" must be one of {sorted(MIGRANT_KINDS)}')
        for k in ("south", "north"):
            span = m.get(k)
            if span is None:
                continue
            if not (isinstance(span, list) and len(span) == 2 and all(isinstance(x, str) and re.match(r"^(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$", x) for x in span)):
                err(f'"migrants[{i}].{k}" must be two dates like ["09-20", "10-25"]')

    trees = d.get("trees", {})
    num("trees", "density", 0, 0.05)
    for i, t in enumerate(trees.get("mix", [])):
        if t.get("shape") not in TREE_SHAPES:
            err(f'"trees.mix[{i}].shape" must be one of {sorted(TREE_SHAPES)}')
        if not isinstance(t.get("weight"), (int, float)) or t["weight"] <= 0:
            err(f'"trees.mix[{i}].weight" must be a positive number')
        for k in ("leaves", "trunk", "autumn"):
            if k in t and not (isinstance(t[k], str) and HEX.match(t[k])):
                err(f'"trees.mix[{i}].{k}" must be a colour like "#2c5846"')

    gc = d.get("ground_cover", {})
    for k in ("grass", "flowers", "stones"):
        num("ground_cover", k, 0, 1)
    plants = gc.get("plants", [])
    if not isinstance(plants, list):
        err('"ground_cover.plants" must be a list')
        plants = []
    for i, pl in enumerate(plants):
        if pl.get("model") not in PLANTS:
            err(f'"ground_cover.plants[{i}].model" must be a plant in models/plants/ (known: {sorted(PLANTS)})')
        elif not os.path.exists(os.path.join(ROOT, "assets", "plants", pl["model"] + ".glb")):
            err(f'"ground_cover.plants[{i}]": build it first with tools/build_model.sh models/plants/{pl["model"]}.json')
        if not isinstance(pl.get("density"), (int, float)) or not 0 < pl["density"] <= 1:
            err(f'"ground_cover.plants[{i}].density" must be a number above 0, up to 1')
        on = pl.get("on", ["grass"])
        if not (isinstance(on, list) and on and all(g in PLANT_GROUND for g in on)):
            err(f'"ground_cover.plants[{i}].on" must be a list of {sorted(PLANT_GROUND)}')
        nt = pl.get("near_trees", 0)
        if not isinstance(nt, (int, float)) or not 0 <= nt <= 16:
            err(f'"ground_cover.plants[{i}].near_trees" must be a number of blocks from 0 to 16')
    total = sum(gc.get(k, 0) for k in ("grass", "flowers", "stones"))
    total += sum(pl.get("density", 0) for pl in plants if isinstance(pl.get("density"), (int, float)))
    if total > 1:
        err('"ground_cover" grass + flowers + stones + plant densities must add up to 1 or less')
    for i, col in enumerate(gc.get("flower_colors", [])):
        if not (isinstance(col, str) and HEX.match(col)):
            err(f'"ground_cover.flower_colors[{i}]" must be a colour')
    names = gc.get("flower_names")
    if names is not None and (not isinstance(names, list) or len(names) != len(gc.get("flower_colors", []))
                              or not all(isinstance(n, str) and n.strip() for n in names)):
        err('"ground_cover.flower_names" must be a list of names, one for each flower colour')

    for i, f in enumerate(d.get("food", [])):
        if f.get("kind") not in FOOD_KINDS:
            err(f'"food[{i}].kind" must be one of {sorted(FOOD_KINDS)}')

    num("terrain", "size", 128, 2048)
    for i, lake in enumerate(d.get("lakes", [])):
        if not isinstance(lake.get("name"), str) or not lake["name"].strip():
            err(f'"lakes[{i}].name" must be the lake\'s real name')
        for k, lo, hi in (("x", 0, 1), ("z", 0, 1), ("length", 0.02, 1), ("width", 0.01, 0.5), ("angle", -360, 360), ("depth", 2, 7), ("islands", 0, 6)):
            v = lake.get(k)
            if v is not None and (not isinstance(v, (int, float)) or not lo <= v <= hi):
                err(f'"lakes[{i}].{k}" must be a number from {lo} to {hi}')
    for i, pl in enumerate(d.get("places", [])):
        if not isinstance(pl.get("name"), str) or not pl["name"].strip():
            err(f'"places[{i}].name" must be the place\'s real name')
        if pl.get("at") is not None:
            if pl["at"] != "highest":
                err(f'"places[{i}].at" can only be "highest"')
        else:
            for k in ("x", "z"):
                v = pl.get(k)
                if not isinstance(v, (int, float)) or not 0 <= v <= 1:
                    err(f'"places[{i}].{k}" must be a number from 0 to 1 (or use "at": "highest")')
    for k in ("reeds", "lilies", "pondweed"):
        num("lake_life", k, 0, 1)
    for i, f in enumerate(d.get("fish", [])):
        if f.get("kind") not in ANIMALS:
            err(f'"fish[{i}].kind" must be an animal in animals/ (known: {sorted(ANIMALS)})')
        if not isinstance(f.get("count"), int) or not 0 <= f["count"] <= 40:
            err(f'"fish[{i}].count" must be a whole number from 0 to 40')

    for k, v in d.get("animals", {}).items():
        for a in v:
            if a not in ANIMALS:
                err(f'"animals.{k}" has unknown animal "{a}" (known: {sorted(ANIMALS)})')
    return errors


def main():
    paths = sys.argv[1:] or sorted(
        os.path.join(ROOT, "regions", f) for f in os.listdir(os.path.join(ROOT, "regions")) if f.endswith(".json")
    )
    failed = False
    for p in paths:
        problems = check(p)
        name = os.path.relpath(p, ROOT)
        if problems:
            failed = True
            print(f"FAIL {name}")
            for e in problems:
                print(f"  - {e}")
        else:
            print(f"ok   {name}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
