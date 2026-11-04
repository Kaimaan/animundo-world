#!/usr/bin/env python3
"""A tile becomes a place: the one converter (game proposals 0038 and 0043).

A tile (the game repo's docs/hackathon/spec/02-data-contracts.md, section 2)
names a biome (`biome`, or `home` before 0043) and carries its own seed,
level, edges, coast, blend, plants and animals. The game turns it into the
region it plays (scripts/tile.gd Tile.from_json, with scripts/tile_layers.gd);
this does exactly the same, so the world's checks and the builder judge the
place children get:

  biome    biomes/<id>.json (else homes/<id>.json), in layers: its land style,
           its plants, its food (layers.resolve); its notes (id, name,
           country, about, based_on, author) dropped
  tile     centre; terrain seed, size 1,024, an open edge, lakes scaled by the
           tile's `water` (the biome's lakes stand for 10% water, at most
           0.6); a grid tile's level, height and the shared water level 8
           (a deep sea biome keeps its water and is at least its height);
           edges; coast
  blend    the second biome mixed in by its share (at most 0.5): tree mix and
           density, ground plants, palette and sky colours
  plants   the tile's own trees, cover and water plants, each part replacing
           the biome's (layers.use_plants)
  animals  the tile's species lists, then its biome's residents (0064)
  open sea an open-sea tile (biome open_sea, game proposal 0047): its own land
           style (`land`), skerries (`skerries`, how many) from its
           `land_share`, and its fish as shoals in the open water
  food     worked out from the plants, water and animals (food.worked_out):
           mushrooms from the forest floor's plants, berries, bark, grass...,
           weight 0 for a kind no animal here eats

tests/tile_region/ holds golden examples (<name>.tile.json and the place it
must give, <name>.place.json); tools/test_tile_region.py checks this tool
against them and the game's tools/check_tile_region.gd checks the game.

Usage:
    python3 tools/tile_region.py TILE.json                   # the place, as JSON
    python3 tools/tile_region.py GROUP.json --tile n_414_480  # one tile of a group file
    python3 tools/tile_region.py TILE.json --biomes DIR       # a draft's biomes first
    python3 tools/tile_region.py TILE.json --out PLACE.json
    python3 tools/tile_region.py golden --write              # remake the golden places

From Python (tools/ on sys.path):
    import tile_region
    place = tile_region.place(tile)   # biomes read from this checkout
    place = tile_region.place(tile, biome=my_biome, blend=my_blend_biome)

It reads the content of the world checkout it is in (biomes, plants, trees,
lands, animals, food/rules.json). Exits 0, or 2 when a file can't be read.
"""
import argparse
import copy
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import food  # noqa: E402
import layers  # noqa: E402

SIZE = 1024          # metres a side (Tile.SIZE)
HOME_WATER = 0.1     # the share of a real cell under lakes a biome's terrain.lakes stands for
MAX_LAKES = 0.6
# A biome with terrain.water_cover (lakeland 0054, taiga 0056): its ponds cover the
# real cell's water share, between MIN_COVER and MAX_COVER (Tile.cover_lakes):
# [terrain.lakes, share of the tile under water], measured on Saimaa's tiles
COVER = [[0.3, 0.01], [0.4, 0.06], [0.5, 0.19], [0.6, 0.37], [0.7, 0.56], [0.8, 0.73], [0.9, 0.86], [1.0, 0.92]]
COVER_DEPTH = 16
MIN_COVER = 0.1
MAX_COVER = 0.85
WATER_LEVEL = 8      # every biome on the grid shares one water level (spec 02 Part 1)
BIOME_NOTES = ("id", "name", "country", "about", "based_on", "author", "retired")
OPEN_SEA = "open_sea"   # the biome of every open-ocean cell (game proposal 0047)
REEF_CELLS = 16   # a terrain.reef_mask's cells a side (builder #255, TileSides.REEF_CELLS)
REEF_SEA = ["water_deep", "water_shallow", "sand"]   # an open-sea tile on the reef map takes these colours from the reef (Tile.REEF_SEA)
REEF_FISH = 0.1   # an open-sea tile with this much reef has all the reef's fish, fewer with less (Tile.REEF_FISH)
REEF_BIOME = "coral_reef"   # whose corals grow on another tile's reef_mask patches (Tile.REEF_BIOME)
MAX_SKERRIES = 12
SHOAL = 8            # fish of a schooling kind in an open-sea tile; others come in twos
MIN_SEA_DEPTH = 6.0  # a deep sea biome on a coastal sea cell: the floor stays at the cell's own depth, at least this (game Tile.MIN_SEA_DEPTH)
GOLDEN = os.path.join(ROOT, "tests", "tile_region")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def biome_of(t):
    """The biome a tile (or its `blend`) names: `biome`, or `home`, its old name."""
    return str(t.get("biome", t.get("home", "")))


def biome_file(bid, extra=None):
    """A biome's file: in `extra` (a draft's folder) or the biomes/ beside it, else
    this checkout's biomes/, else homes/ (Tile.biome_file). None when there's none."""
    tries = [os.path.join(extra, bid + ".json"), os.path.join(os.path.dirname(os.path.abspath(extra)), "biomes", bid + ".json")] if extra else []
    tries += [os.path.join(ROOT, "biomes", bid + ".json"), os.path.join(ROOT, "homes", bid + ".json")]
    return next((f for f in tries if bid and os.path.isfile(f)), None)


def read_biome(bid, extra=None):
    path = biome_file(bid, extra)
    if path is None:
        raise ValueError(f"there is no biome {bid!r} (biomes/{bid}.json)")
    return load(path)


def place(tile, biome=None, blend=None, biomes=None):
    """The place (region data) the game builds for `tile`, as a new dict.
    `biome` and `blend` are the biomes' region JSON; read from `biomes` (a
    folder) or this checkout when left out."""
    if biome is None:
        biome = read_biome(biome_of(tile), biomes)
    if blend is None and isinstance(tile.get("blend"), dict):
        blend = read_biome(biome_of(tile["blend"]), biomes)
    if isinstance(tile.get("land"), str) and tile["land"]:   # the tile's own land style (an open sea's: its nearest coast's)
        biome = dict(biome, land=tile["land"])
    d = copy.deepcopy(layers.resolve(biome))   # a biome in layers (0043): its land style, plants, food
    blend = layers.resolve(blend) if blend else {}
    for k in BIOME_NOTES:
        d.pop(k, None)
    d["center"] = copy.deepcopy(tile.get("center", {}))
    terrain = d.get("terrain", {})
    terrain["seed"] = int(tile.get("seed", 0))
    terrain["size"] = SIZE
    terrain["edge"] = "open"
    water = float(tile.get("water", HOME_WATER))
    if terrain.get("water_cover", False):   # always a pond, even in a dry cell, as in the game
        terrain["lakes"] = cover_lakes(water)
        terrain["pond_depth"] = terrain.get("pond_depth", COVER_DEPTH)
    else:
        terrain["lakes"] = min(float(terrain.get("lakes", 0.2)) * water / HOME_WATER, MAX_LAKES)
    if "level" in tile:   # a grid tile: its own height, around its real level
        if int(terrain.get("water_level", WATER_LEVEL)) > WATER_LEVEL:   # a deep sea biome (game decision 0045) keeps its water; the game lifts the edges to meet it
            terrain["height"] = max(int(tile.get("height", 32)), int(terrain.get("height", 32)))
            if tile.get("habitat", "") != "open_ocean" and "sea_depth" in terrain:   # only open ocean sinks to the biome's deep sea
                terrain["sea_depth"] = min(max(WATER_LEVEL - float(tile["level"]), MIN_SEA_DEPTH), float(terrain["sea_depth"]))
        else:
            terrain["height"] = int(tile.get("height", 32))
            terrain["water_level"] = WATER_LEVEL
        d["level"] = tile["level"]
    d["terrain"] = terrain
    d["edges"] = copy.deepcopy(tile.get("edges", {}))
    if "coast" in tile:   # where a coastal cell's land is
        d["coast"] = copy.deepcopy(tile["coast"])
    mask = reef_mask(tile)
    if mask:   # where the real reef is (the tile's terrain.reef_mask, builder #255): it stands for the biome's flat terrain.reef
        d["reef_mask"] = copy.deepcopy(tile["terrain"]["reef_mask"])
        total = 0.0
        for v in mask:   # added one by one as the game does: Python 3.12's sum() rounds differently
            total += v
        terrain["reef"] = total / len(mask)
        if biome_of(tile) == OPEN_SEA:
            _reef_sea(d)
    if blend:
        _blend(d, blend, min(max(float(tile.get("blend", {}).get("share", 0.0)), 0.0), 0.5))
    if isinstance(tile.get("plants"), dict):   # the tile's own plants over the biome's (0043)
        layers.use_plants(d, tile["plants"])
    if mask:
        _reef_plants(d, biome_of(tile) == OPEN_SEA)
    d["animals"] = layers.tile_species(tile.get("species", {}), d, tile.get("ecoregion"))   # its own, then the biome's residents (0064)
    if biome_of(tile) == OPEN_SEA:
        _open_sea(d, tile)
    d["food"] = food.worked_out(d)   # from the plants, water and animals (0043)
    return d


def reef_mask(tile):
    """A tile's terrain.reef_mask (16 x 16 reef shares, row by row from the
    north side) as shares up to 0.9 (TileSides.reef_mask), or [] without one."""
    cells = tile.get("terrain", {}).get("reef_mask") if isinstance(tile.get("terrain"), dict) else None
    if not isinstance(cells, list) or len(cells) != REEF_CELLS * REEF_CELLS:
        return []
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in cells):
        return []
    return [min(max(float(v), 0.0), 0.9) for v in cells]


def cover_lakes(water):
    """terrain.lakes for a water_cover biome's tile (Tile.cover_lakes, with no real lakes drawn)."""
    w = min(max(water, MIN_COVER), MAX_COVER)
    for (l0, w0), (l1, w1) in zip(COVER, COVER[1:]):
        if w <= w1:
            return l0 + (l1 - l0) * (w - w0) / (w1 - w0)
    return COVER[-1][0]


def _reef_sea(d):
    """An open-sea tile on the reef map (it has a reef_mask, even one with no
    reef; Tile._reef_sea): the reef's warm sea, its water's colours and a sandy
    floor, not its coast's land style's river water."""
    theirs = layers.resolve(read_biome(REEF_BIOME)).get("palette", {})
    palette = d.setdefault("palette", {})
    for k in REEF_SEA:
        if k in theirs:
            palette[k] = theirs[k]
    d["terrain"]["seabed"] = "sand"


def _reef_plants(d, open_sea):
    """A tile with reef in its reef_mask (Tile._reef_plants): the coral_reef
    biome's reef-rock colour, and when it has no plants of its own on reef rock,
    that biome's corals on its patches of reef rock. On an open-sea tile a reef
    plant grows on the reef rock only, not on the open floor too (builder #261a)."""
    if float(d["terrain"].get("reef", 0.0)) <= 0.0:
        return
    biome = layers.resolve(read_biome(REEF_BIOME))
    palette = d.setdefault("palette", {})
    if "reef_rock" not in palette and "reef_rock" in biome.get("palette", {}):
        palette["reef_rock"] = biome["palette"]["reef_rock"]
    cover = d.setdefault("ground_cover", {})
    plants = cover.setdefault("plants", [])
    own = False
    for p in plants:
        if "reef" in p.get("on", []):
            own = True
            if open_sea:
                p["on"] = ["reef"]
    if own:
        return
    for p in biome.get("ground_cover", {}).get("plants", []):
        if "reef" in p.get("on", []):
            plants.append(dict(copy.deepcopy(p), on=["reef"]))   # not its sandy seabed: that's all of an open sea


def _open_sea(d, tile):
    """An open-sea tile (0047, Tile._open_sea): skerries from the real cell's land
    share, the tile's fish as shoals in the open water, and where its reef_mask
    has reef, the reef's own fish."""
    per = float(d["terrain"].get("skerries", 0.0))
    d["skerries"] = min(int(math.floor(float(tile.get("land_share", 0.0)) * 100.0 * per + 0.5)), MAX_SKERRIES)   # roundi
    fish = []
    for kind in d["animals"]["playable"] + d["animals"]["prey"]:
        own = _animal(kind)
        if own.get("archetype") == "fish" and kind not in [f["kind"] for f in fish]:
            fish.append({"kind": kind, "count": SHOAL if own.get("school") else 2})
    reef = float(d.get("terrain", {}).get("reef", 0.0))
    if reef > 0.0:   # where its reef_mask has reef, the reef's own fish swim
        for e in layers.resolve(read_biome(REEF_BIOME)).get("fish", []):
            if isinstance(e, dict) and str(e.get("kind", "")) not in [f["kind"] for f in fish]:
                n = float(e.get("count", 1)) * min(1.0, reef / REEF_FISH)
                fish.append({"kind": str(e["kind"]), "count": max(1, int(math.floor(n + 0.5)))})   # roundi
    d["fish"] = fish


def _animal(kind):
    path = os.path.join(ROOT, "animals", kind + ".json")
    return load(path) if os.path.isfile(path) else {}


def _lerp(a, b, t):
    return a + (b - a) * t   # Godot's lerpf


def _blend(d, other, share):
    """A mixed tile: the second biome's looks mixed in by `share` (Tile._blend)."""
    trees = d.get("trees", {})
    theirs = other.get("trees", {})
    trees["density"] = _lerp(float(trees.get("density", 0.0)), float(theirs.get("density", 0.0)), share)
    trees["mix"] = _mix(trees.get("mix", []), theirs.get("mix", []), share)
    d["trees"] = trees
    cover = d.get("ground_cover", {})
    cover["plants"] = [_scaled(p, 1.0 - share) for p in cover.get("plants", [])] + \
        [_scaled(p, share) for p in other.get("ground_cover", {}).get("plants", [])]
    d["ground_cover"] = cover
    for section in ("palette", "sky"):
        mine = d.get(section, {})
        for k, v in other.get(section, {}).items():
            if isinstance(mine.get(k), str) and isinstance(v, str) and _html(mine[k]) and _html(v):
                mine[k] = _lerp_html(mine[k], v, share)
        d[section] = mine


def _mix(mine, theirs, share):
    out = []
    for entries, k in ((mine, 1.0 - share), (theirs, share)):
        total = sum(float(e.get("weight", 1)) for e in entries)
        for e in entries:
            c = copy.deepcopy(e)
            c["weight"] = float(e.get("weight", 1)) / max(total, 0.001) * k
            out.append(c)
    return out


def _scaled(plant, k):
    c = copy.deepcopy(plant)
    c["density"] = float(plant.get("density", 0.0)) * k
    return c


# Colours as Godot's Color does them: 32-bit floats, html() in, to_html(false) out.
def _f32(x):
    return struct.unpack("f", struct.pack("f", x))[0]


def _html(s):
    """Godot's Color.html_is_valid: #rgb, #rgba, #rrggbb or #rrggbbaa (the # optional)."""
    h = s[1:] if s.startswith("#") else s
    return len(h) in (3, 4, 6, 8) and all(c in "0123456789abcdefABCDEF" for c in h)


def _rgb(s):
    h = s[1:] if s.startswith("#") else s
    if len(h) in (3, 4):
        return [_f32(int(c, 16) * 17 / 255.0) for c in h[:3]]
    return [_f32(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)]


def _lerp_html(a, b, share):
    w = _f32(share)
    out = "#"
    for x, y in zip(_rgb(a), _rgb(b)):
        v = _f32(x + _f32(_f32(y - x) * w))
        n = _f32(v * 255.0)
        out += "%02x" % min(max(int(math.floor(n + 0.5)), 0), 255)   # round half away from zero (Math::round)
    return out


def tile_in(doc, want=""):
    """A lone tile, or the tile `want` of a group file (its first tile when `want` is empty)."""
    if not isinstance(doc, dict):
        raise ValueError("not a tile or a group file")
    if "tiles" not in doc:
        return doc
    tiles = doc["tiles"]
    if not want and tiles:
        want = next(iter(tiles))
    if want not in tiles:
        raise ValueError(f"tile {want} is not ready in this group file ({doc.get('blocked', {}).get(want, 'missing')})")
    return tiles[want]


def dump(d):
    return json.dumps(d, indent=1, ensure_ascii=False) + "\n"


def golden(write):
    """Each golden tile's place against its expected place; with `write`, remake them."""
    bad = []
    for name in sorted(f[:-len(".tile.json")] for f in os.listdir(GOLDEN) if f.endswith(".tile.json")):
        made = dump(place(load(os.path.join(GOLDEN, name + ".tile.json"))))
        path = os.path.join(GOLDEN, name + ".place.json")
        old = open(path, encoding="utf-8").read() if os.path.isfile(path) else None
        if write and old != made:
            with open(path, "w", encoding="utf-8") as f:
                f.write(made)
            print(f"wrote   tests/tile_region/{name}.place.json")
        elif not write:
            print(f"{'ok' if old == made else 'differs'}  {name}")
            if old != made:
                bad.append(name)
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("Usage:")[1])
    ap.add_argument("file", help='a tile, a group file, or "golden"')
    ap.add_argument("--tile", default="", help="the tile to take from a group file")
    ap.add_argument("--biomes", help="a folder of biomes to read before this checkout's (a draft's)")
    ap.add_argument("--out", help="write the place here instead of printing it")
    ap.add_argument("--write", action="store_true", help='with "golden": remake the expected places')
    args = ap.parse_args(argv)
    if args.file == "golden":
        bad = golden(args.write)
        if bad:
            print("The converter no longer gives these golden places. If the change is meant (new content or a\n"
                  "game change made here too), run: python3 tools/tile_region.py golden --write")
        return 1 if bad else 0
    try:
        out = dump(place(tile_in(load(args.file), args.tile), biomes=args.biomes))
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
