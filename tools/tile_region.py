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
  animals  the tile's species lists
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
WATER_LEVEL = 8      # every biome on the grid shares one water level (spec 02 Part 1)
BIOME_NOTES = ("id", "name", "country", "about", "based_on", "author")
OPEN_SEA = "open_sea"   # the biome of every open-ocean cell (game proposal 0047)
MAX_SKERRIES = 12
SHOAL = 8            # fish of a schooling kind in an open-sea tile; others come in twos
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
    terrain["lakes"] = min(float(terrain.get("lakes", 0.2)) * float(tile.get("water", HOME_WATER)) / HOME_WATER, MAX_LAKES)
    if "level" in tile:   # a grid tile: its own height, around its real level
        if int(terrain.get("water_level", WATER_LEVEL)) > WATER_LEVEL:   # a deep sea biome (game decision 0045) keeps its water; the game lifts the edges to meet it
            terrain["height"] = max(int(tile.get("height", 32)), int(terrain.get("height", 32)))
        else:
            terrain["height"] = int(tile.get("height", 32))
            terrain["water_level"] = WATER_LEVEL
        d["level"] = tile["level"]
    d["terrain"] = terrain
    d["edges"] = copy.deepcopy(tile.get("edges", {}))
    if "coast" in tile:   # where a coastal cell's land is
        d["coast"] = copy.deepcopy(tile["coast"])
    if blend:
        _blend(d, blend, min(max(float(tile.get("blend", {}).get("share", 0.0)), 0.0), 0.5))
    if isinstance(tile.get("plants"), dict):   # the tile's own plants over the biome's (0043)
        layers.use_plants(d, tile["plants"])
    species = tile.get("species", {})
    d["animals"] = {k: list(species.get(k, [])) for k in ("playable", "prey", "predators")}
    if biome_of(tile) == OPEN_SEA:
        _open_sea(d, tile)
    d["food"] = food.worked_out(d)   # from the plants, water and animals (0043)
    return d


def _open_sea(d, tile):
    """An open-sea tile (0047, Tile._open_sea): skerries from the real cell's land
    share, and the tile's fish as shoals in the open water."""
    per = float(d["terrain"].get("skerries", 0.0))
    d["skerries"] = min(int(math.floor(float(tile.get("land_share", 0.0)) * 100.0 * per + 0.5)), MAX_SKERRIES)   # roundi
    fish = []
    for kind in d["animals"]["playable"] + d["animals"]["prey"]:
        own = _animal(kind)
        if own.get("archetype") == "fish" and kind not in [f["kind"] for f in fish]:
            fish.append({"kind": kind, "count": SHOAL if own.get("school") else 2})
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
