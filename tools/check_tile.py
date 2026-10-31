#!/usr/bin/env python3
"""Check a tile (Proposal 0038) the way the world checks a place.

A tile is a 25 km cell of the world's tile grid, made by Animundo Builder's
tile maker from a biome (a home before game proposal 0043; `biome` and `home` are both read), a seed and the animals GBIF has there (the game
repo's docs/hackathon/spec/02-data-contracts.md, section 2). The tile maker
calls this on every tile and never publishes one that fails.

The tile becomes a region exactly as the game builds it (tools/tile_region.py,
the one converter: its biome, blend, plants, seed, lakes, animals and food),
named after the tile. A "place" tile is a cell of a hand-made place, so its region is
regions/<place>.json itself. Then:

  tile     the tile's own fields (format, id, kind, ecoregion, blend, seed, water,
           species, requires); an open-sea tile (biome open_sea, game proposal
           0047) has no land: no ecoregion, coast or blend, but its sea (`sea`,
           in seas/names.json) and that sea's `name`, a land style `land` and
           a `land_share` under 0.1
  animals  the home lists the tile's ecoregion (not for the open sea) and has its habitat; an
           open-sea tile's animals all live at sea (`open_sea`); a blend's home exists, every
           animal is in animals/, the playable ones are playable, and requires
           lists every home and animal
  region   validate_region.py and the region schema on the made region
           (needs the models built, like check_draft.py)
  food     food first (decision 0011, check_animals.py's rule): every animal
           finds all its food in the food worked out from the tile's plants, water
           and animals (tools/food.py, 0043), and every hunter some prey
  plants   (in tile) the tile's own `plants`: library ids, at most 24 cover and water
           plants and 6 trees, listed in requires; the region check then holds
           them to the 100 triangles per m² budget
  edges    65 samples a side, whole blocks, the corners agree (n[0] == w[64],
           n[64] == e[64], s[0] == w[0], s[64] == e[0]); every sample and the
           cell's level are above 0 and under the tile's own height; the height
           is 64 when the level or a sample is above 28, else 32; the level is
           above the shared water level (8) on land and under it at sea

A group file (8 x 8 cells) checks each tile, and also that each tile is in
the group's cells and that neighbours in the group share their sides exactly
(a tile's e equals its east neighbour's w, its s its south neighbour's n).

Usage:
    python3 tools/check_tile.py TILE.json            # JSON on stdout
    python3 tools/check_tile.py GROUP.json --text    # the same, for people

The JSON, for one tile:
    {"ok": true/false, "tile": "n_412_301",
     "results": [{"check": "food", "status": "pass"/"fail"/"skip",
                  "problems": ["..."], "reason": "why it was skipped"}, ...]}
For a group file, "results" holds the group's own checks and "tiles" one
{"tile", "ok", "results"} per tile. A skipped check doesn't make "ok" false.

Exits 0 when ok, 1 when a check failed, 2 when the file can't be read.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import check_animals  # noqa: E402
import food  # noqa: E402
import homes  # noqa: E402
import layers  # noqa: E402
import tile_region  # noqa: E402

TILE_ID = re.compile(r"^([ns])_([0-9]{3})_([0-9]{3})$")
GRIDS = {"ease2_n25": "n", "ease2_s25": "s"}
SAMPLES = 65        # one every 16 m along a 1,024 m side
TILE_SIZE = 1024    # metres in the game
SIDES = ("n", "e", "s", "w")
WATER_LEVEL = 8     # one water level for every home on the grid (spec/02 Part 1)
TALL_ABOVE = 28     # a tile is 64 blocks tall when its level or an edge sample is above this (spec/04)
SEA = ("sea", "open_ocean")
OPEN_SEA = "open_sea"   # the open sea's one biome (game proposal 0047)
LAND_SHARE = 0.1        # an open-ocean cell has less land than this (spec/04)
# a tile's place fields the game reads but a region file doesn't have (its biome's
# land and plants are already worked into the place, so the region check mustn't redo them)
GAME_ONLY = ("level", "edges", "coast", "ecoregions", "habitat", "land", "plants", "skerries")
CODE_ONLY = ("habitat", "ecoregion", "home", "seed", "water", "species")


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def names(v):
    return isinstance(v, list) and all(isinstance(x, str) and x for x in v)


def result(check, problems):
    return {"check": check, "status": "fail" if problems else "pass", "problems": problems}


def skip(check, reason):
    return {"check": check, "status": "skip", "problems": [], "reason": reason}


def tile_problems(t):
    out = []
    if t.get("format") != 1:
        out.append('"format" must be 1')
    if not (isinstance(t.get("id"), str) and TILE_ID.match(t["id"])):
        out.append('"id" must be like "n_412_301"')
    if not (is_int(t.get("version")) and t["version"] >= 1):
        out.append('"version" must be a whole number from 1')
    c = t.get("center")
    if not (isinstance(c, dict) and isinstance(c.get("lat"), (int, float)) and -90 <= c["lat"] <= 90
            and isinstance(c.get("lon"), (int, float)) and -180 <= c["lon"] <= 180):
        out.append('"center" must be {"lat", "lon"}')
    if not is_int(t.get("level")):
        out.append('"level" must be the cell\'s ground level in whole blocks')
    if t.get("height") not in (32, 64):
        out.append('"height" must be 32 or 64')
    if not (isinstance(t.get("grid_north"), (int, float)) and -180 <= t["grid_north"] <= 180):
        out.append('"grid_north" must be degrees from -180 to 180')
    kind = t.get("kind")
    if kind == "code":
        for key in CODE_ONLY:
            if key not in t and not (key == "ecoregion" and open_sea(t)):
                out.append(f'a code tile needs "{key}"')
        if open_sea(t):
            out += open_sea_problems(t)
        elif not (is_int(t.get("ecoregion")) and t["ecoregion"] >= 1):
            out.append('"ecoregion" must be a RESOLVE 2017 ecoregion id')
        if "blend" in t:
            b = t["blend"]
            if not (isinstance(b, dict) and set(b) == {"home", "share"} and isinstance(b["home"], str) and b["home"]
                    and isinstance(b["share"], (int, float)) and not isinstance(b["share"], bool)):
                out.append('"blend" must be {"home", "share"}')
            elif not 0.1 <= b["share"] <= 0.5:
                out.append('"blend.share" must be from 0.1 to 0.5: the second ecoregion\'s share of the cell')
        if not (is_int(t.get("seed")) and 0 <= t["seed"] < 2 ** 31):
            out.append('"seed" must be a 31-bit whole number')
        if not (isinstance(t.get("water"), (int, float)) and 0 <= t["water"] <= 1):
            out.append('"water" must be a number from 0 to 1')
        sp = t.get("species")
        if not (isinstance(sp, dict) and all(names(sp.get(k)) for k in ("playable", "prey", "predators"))):
            out.append('"species" must have "playable", "prey" and "predators" lists of animal ids')
        elif not sp["playable"]:
            out.append('"species.playable" is empty: a tile with no playable animal is blocked with no_animal')
        if "place" in t or "part" in t:
            out.append('a code tile has no "place" or "part"')
    elif kind == "place":
        if not (isinstance(t.get("place"), str) and t["place"]):
            out.append('a place tile needs "place", the region id')
        part = t.get("part")
        if not (isinstance(part, list) and len(part) == 2 and all(is_int(v) and v >= 0 for v in part)):
            out.append('a place tile needs "part", [i, j]')
        for key in CODE_ONLY:
            if key in t:
                out.append(f'a place tile has no "{key}": the game reads it from the region file')
    else:
        out.append('"kind" must be "code" or "place"')
    req = t.get("requires")
    if not (isinstance(req, dict) and names(req.get("homes")) and names(req.get("animals"))):
        out.append('"requires" must have "homes" and "animals" lists')
    return out


def open_sea(t):
    """An open-sea tile (game proposal 0047): a cell with no land to speak of,
    made from the one open_sea biome."""
    return t.get("home") == OPEN_SEA


def sea_names():
    with open(os.path.join(ROOT, "seas", "names.json"), encoding="utf-8") as f:
        return json.load(f)["seas"]


def open_sea_problems(t):
    """An open-sea tile has no ecoregion and no coast; it names its sea (seas/names.json)
    with that sea's own names, its land style (the nearest coast's) and its land share."""
    out = []
    if t.get("habitat") != "open_ocean":
        out.append('an open-sea tile\'s "habitat" is "open_ocean"')
    for key in ("ecoregion", "coast", "blend"):
        if key in t:
            out.append(f'an open-sea tile has no "{key}": no ecoregion covers the open sea, and it has no shore')
    seas = sea_names()
    sea = t.get("sea")
    if sea not in seas:
        out.append('"sea" must be a sea in seas/names.json: a cell no named sea covers isn\'t made')
    else:
        want = {k: seas[sea][k] for k in ("en", "fi") if k in seas[sea]}
        if t.get("name") != want:
            out.append(f'"name" must be the sea\'s own names from seas/names.json: {want}')
    land = t.get("land")
    if not (isinstance(land, str) and os.path.isfile(os.path.join(ROOT, "lands", f"{land}.json"))):
        out.append('"land" must be a land style in lands/ (the nearest coast\'s)')
    share = t.get("land_share", 0)
    if not (isinstance(share, (int, float)) and not isinstance(share, bool) and 0 <= share <= LAND_SHARE):
        out.append(f'"land_share" must be from 0 to {LAND_SHARE}: the real cell\'s land, which raises its skerries')
    return out


def region_of(t):
    """The region the game builds for this tile (tools/tile_region.py, the one
    converter), named so the region checks take it, or (None, why)."""
    if t["kind"] == "place":
        path = os.path.join(ROOT, "regions", t["place"] + ".json")
        if not os.path.isfile(path):
            return None, f'"place": there is no regions/{t["place"]}.json'
        with open(path, encoding="utf-8") as f:
            return json.load(f), None
    for owner, key in ((t, '"home"'), (t.get("blend"), '"blend.home"')):
        if isinstance(owner, dict) and tile_region.biome_file(owner["home"]) is None:
            return None, f'{key}: there is no biomes/{owner["home"]}.json or homes/{owner["home"]}.json'
    made = tile_region.place(t)
    region = {"id": "tl_" + t["id"], "name": "Tile " + t["id"], "country": "(tile)",
              "author": tile_region.read_biome(t["home"]).get("author", "Animundo team")}
    region.update({k: v for k, v in made.items() if k not in GAME_ONLY})
    return region, None


def animal_problems(t, content):
    out = []
    req = t["requires"]
    for h in req["homes"]:
        if h not in homes.homes():
            out.append(f'"requires.homes": there is no homes/{h}.json')
    for a in req["animals"]:
        if not content.exists(a):
            out.append(f'"requires.animals": there is no animals/{a}.json')
    if t["kind"] != "code":
        return out
    if t["home"] in homes.homes():
        home = homes.load(t["home"])
        if not open_sea(t) and t["ecoregion"] not in home.get("ecoregions", []):
            out.append(f'homes/{t["home"]}.json doesn\'t list the tile\'s ecoregion {t["ecoregion"]}: '
                       'a tile is built from its ecoregion\'s home')
        if home.get("habitat") != t["habitat"]:
            out.append(f'homes/{t["home"]}.json is a {home.get("habitat")} home, but the tile is {t["habitat"]}')
    used = [t["home"]]
    if "blend" in t:
        b = t["blend"]["home"]
        used.append(b)
        if b == t["home"]:
            out.append('"blend.home" is the tile\'s own home: leave "blend" out')
        elif b not in homes.homes():
            out.append(f'"blend.home": there is no homes/{b}.json')
    for h in used:
        if h not in req["homes"]:
            out.append(f'"requires.homes" must list "{h}"')
    for role in ("playable", "prey", "predators"):
        for a in t["species"][role]:
            if not content.exists(a):
                out.append(f'"species.{role}": there is no animals/{a}.json')
                continue
            if a not in req["animals"]:
                out.append(f'"requires.animals" must list "{a}"')
            if role == "playable" and not content.get_def(a).get("playable"):
                out.append(f'"species.playable": {a} isn\'t a playable animal')
            if open_sea(t) and not content.get_def(a).get("open_sea"):
                out.append(f'"species.{role}": {a} doesn\'t live at sea (no "open_sea": true), so it isn\'t in an open-sea tile')
    return out


def food_problems(rid, region, content):
    checker = check_animals.Checker(ROOT, built_models=False)
    checker.c = content
    content.region = lambda _rid: region
    checker.check_food_web(rid)
    return checker.errors


def edge_problems(t):
    edges = t.get("edges")
    if not isinstance(edges, dict) or set(edges) != set(SIDES):
        return ['"edges" must have exactly "n", "e", "s" and "w"']
    out = []
    height = t["height"] if t.get("height") in (32, 64) else 32
    for side in SIDES:
        e = edges[side]
        if not isinstance(e, list) or len(e) != SAMPLES:
            out.append(f'"edges.{side}" must have {SAMPLES} samples, one every 16 m; it has {len(e) if isinstance(e, list) else "none"}')
            continue
        if not all(is_int(v) for v in e):
            out.append(f'"edges.{side}" must be whole blocks')
            continue
        bad = [i for i, v in enumerate(e) if not 0 < v < height]
        if bad:
            out.append(f'"edges.{side}" leaves the land\'s limits (above 0, under the tile\'s height {height}) at '
                       + ", ".join(f"[{i}] = {e[i]}" for i in bad[:5]) + (" ..." if len(bad) > 5 else ""))
    if out:
        return out
    for a, i, b, j in (("n", 0, "w", 64), ("n", 64, "e", 64), ("s", 0, "w", 0), ("s", 64, "e", 0)):
        if edges[a][i] != edges[b][j]:
            out.append(f'corners don\'t agree: {a}[{i}] is {edges[a][i]} but {b}[{j}] is {edges[b][j]}')
    level = t.get("level")
    if not is_int(level):
        return out
    if not 0 < level < height:
        out.append(f'"level" {level} is outside the land\'s limits (above 0, under the tile\'s height {height})')
    tall = level > TALL_ABOVE or any(v > TALL_ABOVE for side in SIDES for v in edges[side])
    if tall and height != 64:
        out.append(f'"height" must be 64: the level or an edge sample is above {TALL_ABOVE}')
    elif not tall and height != 32:
        out.append(f'"height" must be 32: nothing here is above {TALL_ABOVE}')
    if t.get("kind") == "code" and t.get("habitat") in SEA and level >= WATER_LEVEL:
        out.append(f'"level" {level} of a sea cell must be under the water level {WATER_LEVEL}')
    elif t.get("kind") == "code" and t.get("habitat") not in SEA and level <= WATER_LEVEL:
        out.append(f'"level" {level} of a land cell must be above the water level {WATER_LEVEL}')
    return out


def as_home(t):
    """The tile with its biome as `home` (0043: tiles name a biome, `home` is its old name, both read)."""
    if not isinstance(t, dict):
        return t, []
    t, out = dict(t), []
    for key, owner in (("biome", t), ("biome", t.get("blend"))):
        if isinstance(owner, dict) and "biome" in owner:
            if "home" in owner and owner["home"] != owner["biome"]:
                out.append(f'"biome" {owner["biome"]!r} and "home" {owner["home"]!r} must be the same')
            if owner is t:
                t["home"] = t.pop("biome")
            else:
                b = dict(owner)
                b["home"] = b.pop("biome")
                t["blend"] = b
    req = t.get("requires")
    if isinstance(req, dict) and "biomes" in req:
        req = dict(req)
        req["homes"] = sorted(set(req.get("homes", [])) | set(req.pop("biomes")))
        t["requires"] = req
    return t, out


def plant_problems(t):
    """The tile's own plants (0043): library ids, the phone's limits, and requires lists them."""
    if "plants" not in t:
        return []
    out = layers.problems(t["plants"])
    if out:
        return out
    plants, trees = layers.ids(t["plants"])
    req = t.get("requires", {})
    for p in plants:
        if p not in req.get("plants", []):
            out.append(f'"requires.plants" must list "{p}"')
    for p in trees:
        if p not in req.get("trees", []):
            out.append(f'"requires.trees" must list "{p}"')
    return out


def check_tile(t):
    """[results] for one tile."""
    content = check_animals.Content(ROOT)
    t, named = as_home(t)
    if named:
        return [result("tile", named)]
    shape = (tile_problems(t) + plant_problems(t)) if isinstance(t, dict) else ["a tile must be an object"]
    results = [result("tile", shape)]
    if shape:
        return results + [skip(c, "the tile's fields are wrong") for c in ("animals", "region", "food")] + \
            ([result("edges", edge_problems(t))] if isinstance(t, dict) else [])
    results.append(result("animals", animal_problems(t, content)))
    region, why = region_of(t)
    if region is None:
        return results + [result("region", [why]), skip("food", "no region"), result("edges", edge_problems(t))]
    plants = os.path.join(ROOT, "assets", "plants")
    if os.path.isdir(plants) and any(f.endswith(".glb") for f in os.listdir(plants)):
        results.append(result("region", homes.region_problems(region)))
    else:
        results.append(skip("region", "models not built: run tools/build_model.sh first"))
    results.append(result("food", food_problems(region["id"], region, content)))
    results.append(result("edges", edge_problems(t)))
    return results


def cell(tile_id):
    m = TILE_ID.match(tile_id)
    return m.group(1), int(m.group(2)), int(m.group(3))


def check_group(g):
    """(group results, [{"tile", "ok", "results"}]) for a group file."""
    probs = []
    if g.get("format") != 1:
        probs.append('"format" must be 1')
    grid = g.get("grid")
    if grid not in GRIDS:
        probs.append(f'"grid" must be one of {sorted(GRIDS)}')
    group = g.get("group")
    if not (isinstance(group, list) and len(group) == 2 and all(is_int(v) and 0 <= v <= 89 for v in group)):
        probs.append('"group" must be [gcol, grow], each from 0 to 89')
        group = None
    tiles = g.get("tiles") if isinstance(g.get("tiles"), dict) else {}
    blocked = g.get("blocked") if isinstance(g.get("blocked"), dict) else {}
    if not isinstance(g.get("tiles"), dict) or not isinstance(g.get("blocked"), dict):
        probs.append('"tiles" and "blocked" must be objects keyed by tile id')
    for tid in list(tiles) + list(blocked):
        if not TILE_ID.match(tid):
            probs.append(f'"{tid}" isn\'t a tile id')
            continue
        hemi, col, row = cell(tid)
        if grid in GRIDS and hemi != GRIDS[grid]:
            probs.append(f'{tid} isn\'t in the grid {grid}')
        if group and (col // 8, row // 8) != tuple(group):
            probs.append(f'{tid} isn\'t in the group {group}')
    for tid in set(tiles) & set(blocked):
        probs.append(f'{tid} is both ready and blocked')
    for tid, t in tiles.items():
        if isinstance(t, dict) and t.get("id") != tid:
            probs.append(f'the tile under "{tid}" has the id "{t.get("id")}"')
    out = [result("group", probs)]

    sides = []
    by_cell = {cell(tid)[1:]: t for tid, t in tiles.items() if TILE_ID.match(tid) and isinstance(t, dict)}
    for (col, row), t in sorted(by_cell.items()):
        for (dc, dr), mine, theirs in (((1, 0), "e", "w"), ((0, 1), "s", "n")):
            other = by_cell.get((col + dc, row + dr))
            a = (t.get("edges") or {}).get(mine) if isinstance(t.get("edges"), dict) else None
            b = (other.get("edges") or {}).get(theirs) if other and isinstance(other.get("edges"), dict) else None
            if other is not None and a != b:
                sides.append(f'{t.get("id")}\'s {mine} side doesn\'t match {other.get("id")}\'s {theirs} side')
    out.append(result("neighbours", sides))

    per_tile = []
    for tid in sorted(tiles):
        res = check_tile(tiles[tid])
        per_tile.append({"tile": tid, "ok": all(r["status"] != "fail" for r in res), "results": res})
    return out, per_tile


def check(path):
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    if not isinstance(doc, dict):
        raise ValueError(f"{path} is not a tile or a group file")
    if "tiles" in doc and "grid" in doc:
        results, tiles = check_group(doc)
        ok = all(r["status"] != "fail" for r in results) and all(t["ok"] for t in tiles)
        return {"ok": ok, "group": doc.get("group"), "results": results, "tiles": tiles}
    results = check_tile(doc)
    return {"ok": all(r["status"] != "fail" for r in results), "tile": doc.get("id"), "results": results}


def print_text(report):
    def lines(results, indent=""):
        for r in results:
            print(f'{indent}{r["status"]:4}  {r["check"]}' + (f'  ({r["reason"]})' if r.get("reason") else ""))
            for p in r["problems"]:
                print(f"{indent}      {p}")
    lines(report["results"])
    for t in report.get("tiles", []):
        print(f'{t["tile"]}: {"ok" if t["ok"] else "not ok"}')
        lines(t["results"], "  ")
    print("ok" if report["ok"] else "not ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="a tile or a group file")
    ap.add_argument("--text", action="store_true", help="for people instead of JSON")
    args = ap.parse_args()
    try:
        report = check(args.file)
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print(json.dumps({"ok": False, "error": str(e)}) if not args.text else f"ERROR: {e}")
        return 2
    if args.text:
        print_text(report)
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
