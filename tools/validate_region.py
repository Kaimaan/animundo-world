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
PLANT_FOOD_KINDS = {"berries", "mushrooms", "clover", "browse"}  # food from ground-cover plants (not nectar yet)
FOOD_KINDS = {"clover", "carrot", "berries", "insects", "water_bugs", "browse", "water_plants", "cones", "bottom_bugs", "seeds",
              "grass", "bark", "carrion"}
EDGES = {"lake", "none"}
MIGRANT_KINDS = {"geese", "cranes"}  # flocks the game can draw (scripts/migrants.gd)
PLANT_GROUND = {"grass", "rock", "sand", "seabed"}   # seabed: under water (corals, sea grass)
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
ID = re.compile(r"^[a-z]{2}_[a-z0-9_]+$")

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
# every animal is a file in animals/ (archetypes.json holds shared defaults)
ANIMALS = {f[:-5] for f in os.listdir(os.path.join(ROOT, "animals"))
           if f.endswith(".json") and f != "archetypes.json"}
# every plant is a spec in models/plants/, built by tools/build_model.sh
PLANTS = {f[:-5] for f in os.listdir(os.path.join(ROOT, "models", "plants")) if f.endswith(".json")}


# Plants are drawn thousands of times on cheap phones, so a place's plants
# together may cost at most this many triangles per square metre of open ground:
# each plant's density times its triangles, added up (ART.md, budgets).
PLANT_TRIS_PER_M2 = 100


def glb_triangles(path):
    """Triangles in a built model, read from the .glb (every part, all year)."""
    import struct
    with open(path, "rb") as f:
        data = f.read()
    n = struct.unpack("<I", data[12:16])[0]
    gltf = json.loads(data[20:20 + n])
    tris = 0
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            acc = prim.get("indices", prim.get("attributes", {}).get("POSITION"))
            if acc is not None:
                tris += gltf["accessors"][acc]["count"] // 3
    return tris


def plant_cost(plants):
    """[(model, density × triangles)] for the plants whose model is built."""
    out = []
    for pl in plants:
        glb = os.path.join(ROOT, "assets", "plants", str(pl.get("model")) + ".glb")
        if isinstance(pl.get("density"), (int, float)) and os.path.exists(glb):
            out.append((pl["model"], pl["density"] * glb_triangles(glb)))
    return out


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
    if "welcome" in d and not (isinstance(d["welcome"], str) and d["welcome"].strip() and len(d["welcome"]) <= 300):
        err('"welcome" must be a non-empty text of at most 300 characters')
    # where the facts come from; required for new places once 0009's checks land
    src = d.get("sources")
    if src is not None and not (isinstance(src, list) and src and all(isinstance(x, str) and x.strip() for x in src)):
        err('"sources" must be a list of links or book titles')

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

    # a taller world (high mountains, deep sea) scales the land's limits: 32 blocks and water at 8 for most places
    num("terrain", "height", 32, 64)
    height = d.get("terrain", {}).get("height", 32)
    height = height if isinstance(height, int) and 32 <= height <= 64 else 32
    num("terrain", "water_level", 4, height - 8)
    water = d.get("terrain", {}).get("water_level", 8)
    water = water if isinstance(water, int) else 8
    num("terrain", "base_height", 2, 14 + height - 32)
    num("terrain", "relief", 0, 16 + height - 32)
    num("terrain", "frequency", 0.005, 0.15)
    num("terrain", "rock_ridges", 0, 1)
    num("terrain", "rock_above", 6, height - 4)
    num("terrain", "lakes", 0, 1)
    ice = d.get("ice", {})
    if not isinstance(ice, dict):
        err('"ice" must be an object')
        ice = {}
    num("ice", "glacier_above", 6, height - 4)
    for k, lo, hi in (("amount", 0, 0.3), ("height", 1, 8)):
        v = ice.get("icebergs", {}).get(k)
        if v is not None and (not isinstance(v, (int, float)) or not lo <= v <= hi):
            err(f'"ice.icebergs.{k}" must be a number from {lo} to {hi}')
    fw = ice.get("frozen_water")
    if fw is not None:
        when = r"^((0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])|(spring|summer|autumn|winter)([+-][0-9]{1,3})?)$"
        for k in ("from", "until"):
            if not (isinstance(fw.get(k), str) and re.match(when, fw[k])):
                err(f'"ice.frozen_water.{k}" must be a date like "12-01" or a season mark like "winter+10"')
        c = fw.get("cover")
        if not isinstance(c, (int, float)) or not 0 <= c <= 0.9:
            err('"ice.frozen_water.cover" must be a number from 0 to 0.9: swimmers must always find open water')
    caves = d.get("caves", {})
    if not isinstance(caves, dict):
        err('"caves" must be an object')
        caves = {}
    num("caves", "amount", 0, 0.3)
    if "entrances" in caves and not isinstance(caves["entrances"], bool):
        err('"caves.entrances" must be true or false')
    seabed = d.get("terrain", {}).get("seabed")
    if seabed is not None and seabed not in ("mud", "sand"):
        err('"terrain.seabed" must be "mud" or "sand"')
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
        shape = t.get("shape")
        if shape not in TREE_SHAPES:
            # a tree from a spec: models/trees/<shape>.json, built into assets/trees/<shape>.json
            spec_file = os.path.join(ROOT, "models", "trees", f"{shape}.json") if isinstance(shape, str) and re.match(r"^[a-z][a-z0-9_]*$", shape) else None
            if not spec_file or not os.path.exists(spec_file):
                err(f'"trees.mix[{i}].shape" must be one of {sorted(TREE_SHAPES)} or a tree spec in models/trees/')
            elif not os.path.exists(os.path.join(ROOT, "assets", "trees", f"{shape}.json")):
                err(f'"trees.mix[{i}]": build it first with tools/build_model.sh models/trees/{shape}.json')
            elif t.get("plant", shape) != shape:
                err(f'"trees.mix[{i}].plant" of a tree spec is the spec itself: leave it out or make it "{shape}"')
        if not isinstance(t.get("weight"), (int, float)) or t["weight"] <= 0:
            err(f'"trees.mix[{i}].weight" must be a positive number')
        for k in ("leaves", "trunk", "autumn"):
            if k in t and not (isinstance(t[k], str) and HEX.match(t[k])):
                err(f'"trees.mix[{i}].{k}" must be a colour like "#2c5846"')
        # the tree's field guide page (locale/<lang>/plants.json "plant.<id>.*") and the food it is to animals
        if "plant" in t and not (isinstance(t["plant"], str) and re.match(r"^[a-z][a-z0-9_]*$", t["plant"])):
            err(f'"trees.mix[{i}].plant" must be an id like "scots_pine"')
        if "food" in t and not (isinstance(t["food"], str) and t["food"]):
            err(f'"trees.mix[{i}].food" must be a food kind like "browse"')

    for i, bog in enumerate(d.get("bogs", [])):
        if not isinstance(bog, dict) or not all(isinstance(bog.get(k), (int, float)) and 0 <= bog[k] <= 1 for k in ("x", "z")):
            err(f'"bogs[{i}]" needs x/z between 0 and 1')
        if not isinstance(bog, dict) or not isinstance(bog.get("radius"), (int, float)) or not 1 <= bog["radius"] <= 512:
            err(f'"bogs[{i}].radius" must be 1–512 metres')
    for i, stream in enumerate(d.get("streams", [])):
        points = stream.get("points", []) if isinstance(stream, dict) else []
        if not isinstance(points, list) or len(points) < 2 or not all(isinstance(p, list) and len(p) == 2 and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in p) for p in points):
            err(f'"streams[{i}].points" needs at least two x/z pairs between 0 and 1')
        if not isinstance(stream, dict) or not isinstance(stream.get("width"), (int, float)) or not 1 <= stream["width"] <= 32:
            err(f'"streams[{i}].width" must be 1–32 metres')

    gc = d.get("ground_cover", {})
    for k in ("grass", "flowers", "stones"):
        num("ground_cover", k, 0, 1)
    plants = gc.get("plants", [])
    if not isinstance(plants, list):
        err('"ground_cover.plants" must be a list')
        plants = []
    for i, pl in enumerate(plants):
        if pl.get("habitat", "forest") not in ("forest", "bog"):
            err(f'"ground_cover.plants[{i}].habitat" must be forest or bog')
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
        # a food plant: "food": "mushrooms" (the whole plant) or {"kind": "berries", "part": "berry"}
        food = pl.get("food")
        if food is not None:
            kind = food if isinstance(food, str) else food.get("kind") if isinstance(food, dict) else None
            part = food.get("part", "") if isinstance(food, dict) else ""
            if kind == "nectar":
                err(f'"ground_cover.plants[{i}].food": plants can\'t be bee flowers yet: see wanted.json core "Bee flowers from plant specs"')
            elif kind not in PLANT_FOOD_KINDS:
                err(f'"ground_cover.plants[{i}].food" kind must be one of {sorted(PLANT_FOOD_KINDS)}')
            if part and pl.get("model") in PLANTS:
                spec = json.load(open(os.path.join(ROOT, "models", "plants", pl["model"] + ".json")))
                if part not in {p.get("name") for p in spec.get("parts", [])}:
                    err(f'"ground_cover.plants[{i}].food.part" "{part}" is not a part of models/plants/{pl["model"]}.json')
            if not isinstance(pl.get("names", []), list):
                err(f'"ground_cover.plants[{i}].names" must be a list of the food names the player is told')
    total = sum(gc.get(k, 0) for k in ("grass", "flowers", "stones"))
    total += sum(pl.get("density", 0) for pl in plants if pl.get("habitat", "forest") == "forest" and isinstance(pl.get("density"), (int, float)))
    bog_total = sum(pl.get("density", 0) for pl in plants if pl.get("habitat") == "bog" and isinstance(pl.get("density"), (int, float)))
    if bog_total > 1:
        err('Bog plant densities must add up to 1 or less')
    if total > 1:
        err('"ground_cover" grass + flowers + stones + plant densities must add up to 1 or less')
    cost = plant_cost(plants)
    if sum(c for _, c in cost) > PLANT_TRIS_PER_M2:
        top = ", ".join(f"{m} {c:.0f}" for m, c in sorted(cost, key=lambda x: -x[1])[:3])
        err(f'"ground_cover.plants" cost {sum(c for _, c in cost):.0f} triangles per square metre of open ground; '
            f'the limit is {PLANT_TRIS_PER_M2} (ART.md). Lower the density of a common plant or make it simpler. '
            f'Most expensive: {top}')
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
        for k, lo, hi in (("x", 0, 1), ("z", 0, 1), ("length", 0.02, 1.5), ("width", 0.01, 1.5), ("angle", -360, 360), ("depth", 2, max(7, water - 1)), ("islands", 0, 24)):
            v = lake.get(k)
            if v is not None and (not isinstance(v, (int, float)) or not lo <= v <= hi):
                err(f'"lakes[{i}].{k}" must be a number from {lo} to {hi}')
        radius = lake.get("island_radius", [3.5, 6.0])
        if not isinstance(radius, list) or len(radius) != 2 or not all(isinstance(v, (int, float)) for v in radius) or not 2 <= radius[0] <= radius[1] <= 80:
            err(f'"lakes[{i}].island_radius" must be [minimum, maximum] from 2 to 80 metres')
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
