#!/usr/bin/env python3
"""Map animals: where the game's world map shows animals worth exploring for.

Proposal 0038 section 4: zoomed in a lot, the map shows animals where they
live, as silhouettes until the child has met them. Every animal in
animal-list.json, so the unknown world shows what's there to find: the
playable ones first (FIRST), then the most striking (STRIKING), then the rest.

Nearby matters most: an animal seen in the tiles round a built place makes a
child want to walk there. So each animal gets up to NEAR spots within NEAR_KM
of every built place (places.json), NEAR_APART_KM apart, never in the place's
own tile; then up to FAR spots further away, spread over the whole range
first (SPREAD_KM apart), then filled in (FAR_APART_KM apart). Nearby spots come
first in the file.

Where an animal lives comes from GBIF's density map tiles of human
observations: two tiles (the west and east halves of the Earth, about 20 km a
pixel) per animal, which GBIF serves quickly and without the search API's rate
limit. A pixel only counts when the habitat grid cell it falls in is one of the
animal's habitats, which drops zoo and garden records. Each spot is the centre
of its 25 km tile, never finer (0038: "never finer than one tile"); GBIF blurs
sensitive species itself. Needs Pillow to read the tiles.

    python3 tools/map_animals.py           # fetch from GBIF (needs network), write map-animals.json
    python3 tools/map_animals.py --check   # offline: the file matches the playable animals

The habitat grid is the builder's (`data/habitat-grid` in animundo-builder,
RESOLVE Ecoregions 2017 CC BY 4.0, Natural Earth, ETOPO 2022), read only.
The game names playable animals with their own text (`animal.<id>.title`);
the others have their English name in the file and `animal.<id>.map_name` in
locale/fi/animals.json.
"""
import argparse
import gzip
import hashlib
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "map-animals.json")
LIST = os.path.join(ROOT, "animal-list.json")
GRID = os.path.join(ROOT, "..", "animundo-builder", "data", "habitat-grid")
TILE = "https://api.gbif.org/v2/map/occurrence/density/0/%d/0@2x.png"

# The order the map takes them in: these playable animals, then the rest of
# the playable ones, then STRIKING, then every other animal in the list's order.
FIRST = [
    "fox", "moose", "saimaa_seal", "mountain_hare", "flying_squirrel", "herring_gull",
    "kestrel", "pike", "mallard", "squirrel", "frog",
]
STRIKING = [
    "polar_bear", "arctic_fox", "walrus", "narwhal", "beluga", "reindeer", "musk_ox",
    "wolverine", "lynx", "wolf", "brown_bear", "beaver", "otter", "snowy_owl", "puffin",
    "snow_leopard", "ibex", "emperor_penguin", "king_penguin", "sea_otter", "lion",
    "cheetah", "giraffe", "zebra", "african_elephant", "hippo", "rhino", "meerkat",
    "ostrich", "flamingo", "kangaroo", "koala", "platypus", "emu", "tiger", "giant_panda",
    "red_panda", "orangutan", "gorilla", "jaguar", "sloth", "toucan", "scarlet_macaw",
    "capybara", "bison", "camel", "fennec_fox", "komodo_dragon", "green_sea_turtle",
    "clownfish", "whale_shark", "humpback_whale", "orca", "crocodile", "okapi", "harpy_eagle",
]
FI = os.path.join(ROOT, "locale", "fi", "animals.json")
# Areas whose records aren't the animal living wild there, as (south, north,
# west, east): GBIF files dingoes under the wolf, emus are farmed outside
# Australia, and single walruses visited Ireland, Britain, the Netherlands and Oslo.
NOT_IN = {
    "wolf": [(-45, -10, 110, 155)],
    "emu": [(15, 50, -125, -65), (-48, -34, 165, 179), (30, 60, -12, 40), (-36, -20, 10, 35)],
    "walrus": [(49, 60.5, -11, 12)],
}
# Where famous animals really live, as (south, north, west, east) boxes:
# records outside them are zoos, farms, ranches and safari parks (zebras in
# Texas, a tiger in Germany, a koala in Japan), which the lone-dot rule misses
# when a country has several.
AFRICA = (-36, 38, -20, 52)
SOUTH_AMERICA = (-56, 25, -118, -34)
AUSTRALIA = (-45, -10, 110, 155)
ONLY_IN = {
    **{a: [AFRICA] for a in ("chimpanzee", "gorilla", "okapi", "giraffe", "zebra", "african_elephant",
                             "hippo", "rhino", "meerkat", "african_wild_dog", "hyena", "wildebeest",
                             "impala", "warthog", "gazelle", "ostrich")},
    "lion": [AFRICA, (20, 23, 69, 72)],   # and India's Gir forest
    "cheetah": [AFRICA, (30, 38, 50, 62)],   # and Iran
    **{a: [AUSTRALIA] for a in ("kangaroo", "koala", "wombat", "emu", "thorny_devil")},
    **{a: [SOUTH_AMERICA] for a in ("jaguar", "sloth", "capybara", "tapir", "giant_anteater", "toucan",
                                    "scarlet_macaw", "harpy_eagle", "poison_dart_frog", "anaconda", "piranha")},
    "orangutan": [(-6, 8, 94, 120)],
    "proboscis_monkey": [(-6, 8, 108, 120)],
    "komodo_dragon": [(-10, -7, 118, 121)],
    "ring_tailed_lemur": [(-26, -12, 43, 51)],
    "tiger": [(-11, 55, 60, 150)],
    "asian_elephant": [(-11, 35, 60, 125)],
    "giant_panda": [(20, 40, 95, 115)],
    "red_panda": [(20, 35, 80, 110)],
    "snow_leopard": [(25, 55, 60, 110)],
    "polar_bear": [(50, 90, -180, 180)],
    "emperor_penguin": [(-90, -55, -180, 180)],
    "king_penguin": [(-90, -45, -180, 180)],
}
NEAR = 6             # spots round each built place, per animal
NEAR_KM = 300.0      # how far round a built place counts as near
NEAR_APART_KM = 60.0
FAR = 10             # spots further away, per animal
SPREAD_KM = 1000.0   # first the range, this far apart
FAR_APART_KM = 250.0  # then filled in
LONE_PX = 8          # fewer record pixels than this round a pixel: a zoo or a stray

# An animal habitat (animal-list.json) -> the habitat grid's cell habitats it
# accepts. The grid has no river or reef, and its "mountain" is only montane
# grassland, so high cells count as mountain too (MOUNTAIN_M).
ACCEPTS = {
    "boreal_forest": {"boreal_forest", "boreal_lake"},
    "boreal_lake": {"boreal_lake", "boreal_forest"},
    "forest": {"forest", "dry_forest", "mediterranean"},
    "rainforest": {"rainforest"},
    "grassland": {"grassland", "savanna", "mediterranean"},
    "savanna": {"savanna", "grassland", "dry_forest"},
    "desert": {"desert"},
    "tundra": {"tundra", "ice"},
    "ice": {"ice", "tundra", "sea", "open_ocean"},
    "mountain": {"mountain"},
    "sea": {"sea", "open_ocean"},
    "reef": {"sea", "open_ocean"},
    "mangrove": {"mangrove", "rainforest", "sea"},
    "wetland": {"wetland", "lake", "boreal_lake"},
    "lake": {"lake", "wetland", "boreal_lake"},
    "river": {"wetland", "lake", "boreal_lake", "mangrove"},
}
MOUNTAIN_M = 1500.0

# RESOLVE biome -> grid habitat, as the builder's habitats.py has it
BIOME_TO_HABITAT = {
    1: "rainforest", 2: "dry_forest", 3: "dry_forest", 4: "forest", 5: "forest",
    6: "boreal_forest", 7: "savanna", 8: "grassland", 9: "wetland", 10: "mountain",
    11: "tundra", 12: "mediterranean", 13: "desert", 14: "mangrove",
}

# EASE-Grid 2.0 at 25 km (spec 02 §1, scripts/ease_grid.gd in the game)
A = 6378137.0
E2 = 0.0066943799901413165
E = math.sqrt(E2)
CELL = 25000.0
CELLS = 720
CORNER = 9000000.0


def _q(phi):
    s = math.sin(phi)
    return (1 - E2) * (s / (1 - E2 * s * s) - 1 / (2 * E) * math.log((1 - E * s) / (1 + E * s)))


QP = _q(math.pi / 2)


def cell(lat, lon):
    """(grid, col, row) of the 25 km cell holding a point."""
    lam = math.radians(lon)
    if lat >= 0:
        rho = A * math.sqrt(max(QP - _q(math.radians(lat)), 0.0))
        x, y = rho * math.sin(lam), -rho * math.cos(lam)
    else:
        rho = A * math.sqrt(max(QP + _q(math.radians(lat)), 0.0))
        x, y = rho * math.sin(lam), rho * math.cos(lam)
    col = min(max(int(math.floor((x + CORNER) / CELL)), 0), CELLS - 1)
    row = min(max(int(math.floor((CORNER - y) / CELL)), 0), CELLS - 1)
    return ("n" if lat >= 0 else "s", col, row)


def tile_id(c):
    return "%s_%03d_%03d" % c


def centre(c):
    """The latitude and longitude of a cell's centre."""
    grid, col, row = c
    x = -CORNER + (col + 0.5) * CELL
    y = CORNER - (row + 0.5) * CELL
    rho = math.hypot(x, y)
    if grid == "n":
        q = QP - (rho / A) ** 2
        lon = math.degrees(math.atan2(x, -y))
    else:
        q = (rho / A) ** 2 - QP
        lon = math.degrees(math.atan2(x, y))
    phi = math.asin(max(-1.0, min(1.0, q / QP)))
    for _ in range(10):   # Snyder 3-16
        s = math.sin(phi)
        if abs(math.cos(phi)) < 1e-12:
            break
        phi += (1 - E2 * s * s) ** 2 / (2 * math.cos(phi)) * (
            q / (1 - E2) - s / (1 - E2 * s * s) + 1 / (2 * E) * math.log((1 - E * s) / (1 + E * s)))
    return round(math.degrees(phi), 3), round(lon, 3)


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


class Habitats:
    """The builder's baked habitat grid, both hemispheres."""

    def __init__(self, folder):
        self.cells = {}
        for g in ("n", "s"):
            with gzip.open(os.path.join(folder, "ease2_%s25.json.gz" % g), "rt", encoding="utf-8") as f:
                self.cells[g] = json.load(f)["cells"]

    def at(self, c):
        """(habitat, elevation in metres) of a cell."""
        grid, col, row = c
        v = self.cells[grid].get("%d,%d" % (col, row))
        if v is None:
            return "open_ocean", 0.0
        eco1, _s1, _e2, _s2, biome, land, water, elev = v[:8]   # later fields: the coast samples
        land, water, elev = float(land), float(water), float(elev or 0)
        if land < 0.1:
            return "open_ocean", elev
        if land < 0.5:
            return "sea", elev
        if eco1 == 0:
            return "ice", elev
        h = BIOME_TO_HABITAT.get(biome, "sea")
        if h == "boreal_forest" and water >= 0.15:
            h = "boreal_lake"
        elif h not in ("boreal_forest", "boreal_lake") and water >= 0.5:
            h = "lake"
        return h, elev

    def fits(self, c, habitats):
        h, elev = self.at(c)
        for want in habitats:
            if h in ACCEPTS.get(want, {want}):
                return True
            if want == "mountain" and elev >= MOUNTAIN_M:
                return True
        return False


CACHE = os.path.join(os.path.expanduser("~"), ".cache", "animundo-gbif")   # a rerun asks GBIF nothing twice


def _tile(key, x):
    """GBIF's density tile x (0 west, 1 east) for a taxon, as PNG bytes."""
    url = (TILE % x) + "?" + urllib.parse.urlencode({
        "srs": "EPSG:4326", "taxonKey": key, "basisOfRecord": "HUMAN_OBSERVATION", "style": "classic.point"})
    cached = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest() + ".png")
    if os.path.exists(cached):
        with open(cached, "rb") as f:
            return f.read()
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                data = r.read()
            os.makedirs(CACHE, exist_ok=True)
            with open(cached, "wb") as f:
                f.write(data)
            return data
        except Exception as e:   # GBIF is sometimes slow: try again, waiting longer each time
            if attempt == 5:
                raise
            print("  retry (%s)" % e, file=sys.stderr)
            time.sleep(5 * (attempt + 1))


def records(key, skip=(), only=()):
    """{cell: weight} for a GBIF taxon key: how much it was seen in each 25 km
    cell. The classic style goes yellow (few records) to red (many), so a
    pixel weighs more the less green it has."""
    import io
    from PIL import Image
    pixels = []
    for x in (0, 1):
        data = _tile(key, x)
        if not data.startswith(b"\x89PNG"):
            continue   # no records in this half of the Earth (GBIF sends nothing)
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        w, h = im.size
        px = im.load()
        for py in range(h):
            lat = 90.0 - (py + 0.5) * 180.0 / h
            for pxx in range(w):
                r, g, b, a = px[pxx, py]
                if a == 0:
                    continue
                lon = -180.0 + x * 180.0 + (pxx + 0.5) * 180.0 / w
                if any(s <= lat <= n and west <= lon <= e for s, n, west, e in skip):
                    continue
                if only and not any(s <= lat <= n and west <= lon <= e for s, n, west, e in only):
                    continue
                pixels.append((lat, lon, 1.0 + (255 - g) / 51.0))
    # A zoo or a stray is one lone dot (a 2 x 2 pixel bin); a real population
    # has more round it. Keep a pixel only with LONE_PX others within about 150 km.
    near = {}
    for lat, lon, _ in pixels:
        k = (int(lat // 0.7), int(lon // 0.7))
        near[k] = near.get(k, 0) + 1
    counts = {}
    for lat, lon, wt in pixels:
        k0, k1 = int(lat // 0.7), int(lon // 0.7)
        if sum(near.get((k0 + i, k1 + j), 0) for i in (-1, 0, 1) for j in (-1, 0, 1)) < LONE_PX:
            continue
        c = cell(lat, lon)
        counts[c] = counts.get(c, 0.0) + wt
    return counts


def near_spots(counts, habitats, grid, place, chosen):
    """Up to NEAR tile centres within NEAR_KM of `place` where the animal was
    seen most, NEAR_APART_KM from each other and from `chosen`, not in the
    place's own tile."""
    own = cell(*place)
    out = []
    for c, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if len(out) >= NEAR:
            break
        if c == own or not grid.fits(c, habitats):
            continue
        ll = centre(c)
        if cell(*ll) != c:
            continue   # by the equator a cell's centre can fall in the other hemisphere's grid
        if km(ll, place) <= NEAR_KM and all(km(ll, (s["lat"], s["lon"])) >= NEAR_APART_KM for s in chosen + out):
            out.append({"tile": tile_id(c), "lat": ll[0], "lon": ll[1]})
    return out


def spots(counts, habitats, grid, places=()):
    """Up to FAR tile centres beyond NEAR_KM of every built place (those are
    near spots): where the animal was seen most, first SPREAD_KM apart so its
    whole range shows, then FAR_APART_KM apart."""
    cells = [c for c, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])) if grid.fits(c, habitats)]
    chosen = []
    for apart in (SPREAD_KM, FAR_APART_KM):
        for c in cells:
            if len(chosen) >= FAR:
                return chosen
            ll = centre(c)
            if cell(*ll) != c:
                continue
            if all(km(ll, pl) > NEAR_KM for pl in places) and all(km(ll, (s["lat"], s["lon"])) >= apart for s in chosen):
                chosen.append({"tile": tile_id(c), "lat": ll[0], "lon": ll[1]})
    return chosen


def picks(listed):
    """Every animal in the map's order."""
    out = [i for i in FIRST if i in listed]
    out += [i for i, a in listed.items() if a.get("in_library") and i not in out]
    out += [i for i in STRIKING if i in listed and i not in out]
    return out + [i for i in listed if i not in out]


def load_places():
    """(lat, lon) of every built place."""
    with open(os.path.join(ROOT, "places.json"), encoding="utf-8") as f:
        return [(p["center"]["lat"], p["center"]["lon"]) for p in json.load(f)["places"]]


def load_list():
    with open(LIST, encoding="utf-8") as f:
        return {a["id"]: a for a in json.load(f)["animals"]}


def check():
    problems = []
    listed = load_list()
    PICKS = picks(listed)
    if not os.path.exists(OUT):
        return ["map-animals.json is missing: run tools/map_animals.py"]
    with open(OUT, encoding="utf-8") as f:
        data = json.load(f)
    ids = [a["id"] for a in data.get("animals", [])]
    with open(FI, encoding="utf-8") as f:
        fi = json.load(f)
    for p in FIRST:
        if not listed.get(p, {}).get("in_library"):
            problems.append("%s is in FIRST but isn't a playable animal" % p)
    for p in list(STRIKING) + list(ONLY_IN) + list(NOT_IN):
        if p not in listed:
            problems.append("%s is in STRIKING but not in animal-list.json" % p)
    for p in PICKS:
        if not listed[p].get("in_library") and ("animal.%s.map_name" % p) not in fi:
            problems.append("locale/fi/animals.json has no animal.%s.map_name" % p)
    for a in data.get("animals", []):
        if a["id"] not in PICKS:
            problems.append("%s is in map-animals.json but not in animal-list.json: run the tool again" % a["id"])
            continue
        if a.get("name") != listed.get(a["id"], {}).get("name"):
            problems.append("%s: name differs from animal-list.json: run the tool again" % a["id"])
        if not a.get("spots") or len(a["spots"]) > NEAR * len(load_places()) + FAR:
            problems.append("%s: needs 1 to %d spots" % (a["id"], NEAR * len(load_places()) + FAR))
        for lat, lon in a.get("spots", []):
            if centre(cell(lat, lon)) != (lat, lon):
                problems.append("%s: spot %s,%s isn't a tile's centre" % (a["id"], lat, lon))
    missing = [p for p in PICKS if p not in ids]
    if missing:
        print("No spots found (left off the map): " + ", ".join(missing))
    return problems


def write(data):
    """Small on purpose (the game downloads it): one animal per line, each spot
    [lat, lon] (its tile's centre, so the tile id isn't kept)."""
    lines = []
    for a in data["animals"]:
        a = dict(a, spots=[[s["lat"], s["lon"]] if isinstance(s, dict) else s for s in a["spots"]])
        lines.append(json.dumps(a, ensure_ascii=False, separators=(",", ":")))
    head = json.dumps({k: v for k, v in data.items() if k != "animals"}, ensure_ascii=False)[:-1]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(head + ',"animals":[\n' + ",\n".join(lines) + "\n]}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="check map-animals.json offline")
    ap.add_argument("--grid", default=GRID, help="the builder's data/habitat-grid folder")
    ap.add_argument("--only", nargs="*", help="fetch only these ids (the rest are kept)")
    args = ap.parse_args()
    if args.check:
        problems = check()
        for p in problems:
            print("map-animals: " + p)
        sys.exit(1 if problems else 0)
    listed = load_list()
    places = load_places()
    grid = Habitats(args.grid)
    old = {}
    if args.only and os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            old = {a["id"]: a for a in json.load(f)["animals"]}
    def fetch(p):
        a = listed[p]
        if args.only and p not in args.only:
            return old.get(p)
        counts = records(a["gbif_key"], NOT_IN.get(p, ()), ONLY_IN.get(p, ()))
        found = []
        for place in places:
            found += near_spots(counts, a["habitats"], grid, place, found)
        near = len(found)
        found += spots(counts, a["habitats"], grid, places)
        print("%-18s %d near, %d far" % (p, near, len(found) - near), flush=True)
        return {"id": p, "name": a["name"], "spots": found} if found else None

    with ThreadPoolExecutor(6) as pool:   # map tiles are quick to serve; the order is kept
        out = [r for r in pool.map(fetch, picks(listed)) if r]
    data = {
        "about": "Animals the game's world map shows where they live (Proposal 0038 section 4). "
                 "Written by tools/map_animals.py from GBIF records and the habitat grid; edit FIRST there.",
        "credit": "Spots: GBIF.org occurrence density maps; habitats: RESOLVE Ecoregions 2017 (Dinerstein et al. 2017), CC BY 4.0.",
        "animals": out,
    }
    write(data)
    print("Wrote %d animals to map-animals.json." % len(out))


if __name__ == "__main__":
    main()
