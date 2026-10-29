#!/usr/bin/env python3
"""Map animals: where the game's world map shows animals worth exploring for.

Proposal 0038 section 4: zoomed in a lot, the map shows animals where they
live, as silhouettes until the child has met them. Not every animal: only the
ones in PICKS below, the most striking from animal-list.json, each at up to
three real spots far apart.

Spots come from GBIF records (human observations, no geospatial issues),
fetched per top country so they spread over the animal's range. A record only
counts when the habitat grid cell it falls in is one of the animal's habitats,
which drops zoo and garden records. Each spot is the centre of its 25 km tile,
never finer (0038: "never finer than one tile"); GBIF blurs sensitive species
itself.

    python3 tools/map_animals.py           # fetch from GBIF (needs network), write map-animals.json
    python3 tools/map_animals.py --check   # offline: the file matches PICKS, the list and the Finnish names

The habitat grid is the builder's (`data/habitat-grid` in animundo-builder,
RESOLVE Ecoregions 2017 CC BY 4.0, Natural Earth, ETOPO 2022), read only.
English names come from animal-list.json; Finnish names are in
locale/fi/animals.json as `animal.<id>.map_name`.
"""
import argparse
import gzip
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "map-animals.json")
LIST = os.path.join(ROOT, "animal-list.json")
FI = os.path.join(ROOT, "locale", "fi", "animals.json")
GRID = os.path.join(ROOT, "..", "animundo-builder", "data", "habitat-grid")
API = "https://api.gbif.org/v1/occurrence/search"

# The animals the map shows, most striking first. Only ones we can make
# (`can_make` in animal-list.json): an animal on the map should be one a
# child could some day play or meet.
PICKS = [
    "polar_bear", "arctic_fox", "walrus", "narwhal", "beluga", "reindeer", "musk_ox",
    "wolverine", "lynx", "wolf", "brown_bear", "moose", "beaver", "otter", "saimaa_seal",
    "snowy_owl", "puffin", "snow_leopard", "ibex", "marmot", "emperor_penguin",
    "king_penguin", "sea_otter", "lion", "cheetah", "giraffe", "zebra", "hippo", "rhino",
    "meerkat", "ostrich", "flamingo", "kangaroo", "emu", "wombat", "tiger", "giant_panda",
    "red_panda", "jaguar", "toucan", "scarlet_macaw", "capybara", "bison", "camel",
    "fennec_fox", "komodo_dragon", "green_sea_turtle", "clownfish", "manta_ray",
    "crocodile", "okapi", "harpy_eagle",
]
# Records that aren't the animal living wild there, by country code or tile:
# GBIF files dingoes under the wolf, emus are farmed outside Australia, and
# single walruses visited the Netherlands and Wales.
NOT_IN = {"wolf": ["AU", "n_164_281"], "emu": ["US", "NZ"], "walrus": ["NL", "GB"]}
SPOTS = 3            # at most this many spots per animal
APART_KM = 1500.0    # spots at least this far apart
MIN_RECORDS = 3      # a cell needs this many matching records to be a spot
COUNTRIES = 6        # records are fetched from this many top countries
PER_COUNTRY = 300    # GBIF's largest page

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
        eco1, _s1, _e2, _s2, biome, land, water, elev = v
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


def _get(params):
    url = API + "?" + urllib.parse.urlencode(params, doseq=True)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception as e:   # GBIF is sometimes slow: try again
            if attempt == 3:
                raise
            print("  retry (%s)" % e, file=sys.stderr)
            time.sleep(2 + attempt * 3)


BASE = {
    "hasCoordinate": "true", "hasGeospatialIssue": "false", "occurrenceStatus": "PRESENT",
    "basisOfRecord": "HUMAN_OBSERVATION",
}


def records(key, skip=()):
    """[(lat, lon)] for a GBIF taxon key, spread over its top countries."""
    top = _get({**BASE, "taxonKey": key, "limit": 0, "facet": "country", "facetLimit": COUNTRIES + len(skip)})
    out = []
    counts = [c for c in (top.get("facets") or [{}])[0].get("counts", []) if c["name"] not in skip]
    for c in counts[:COUNTRIES]:
        page = _get({**BASE, "taxonKey": key, "country": c["name"], "limit": PER_COUNTRY})
        for r in page.get("results", []):
            if "decimalLatitude" in r and "decimalLongitude" in r:
                out.append((r["decimalLatitude"], r["decimalLongitude"]))
        time.sleep(0.2)
    return out


def spots(points, habitats, grid, skip=()):
    """Up to SPOTS tile centres with the most matching records, APART_KM apart."""
    counts = {}
    for lat, lon in points:
        c = cell(lat, lon)
        if tile_id(c) not in skip and grid.fits(c, habitats):
            counts[c] = counts.get(c, 0) + 1
    chosen = []
    for c, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if n < MIN_RECORDS or len(chosen) >= SPOTS:
            break
        ll = centre(c)
        if all(km(ll, (s["lat"], s["lon"])) >= APART_KM for s in chosen):
            chosen.append({"tile": tile_id(c), "lat": ll[0], "lon": ll[1]})
    return chosen


def load_list():
    with open(LIST, encoding="utf-8") as f:
        return {a["id"]: a for a in json.load(f)["animals"]}


def check():
    problems = []
    listed = load_list()
    with open(FI, encoding="utf-8") as f:
        fi = json.load(f)
    if not os.path.exists(OUT):
        return ["map-animals.json is missing: run tools/map_animals.py"]
    with open(OUT, encoding="utf-8") as f:
        data = json.load(f)
    ids = [a["id"] for a in data.get("animals", [])]
    for p in PICKS:
        a = listed.get(p)
        if a is None:
            problems.append("%s is in PICKS but not in animal-list.json" % p)
        elif not a.get("can_make"):
            problems.append("%s can't be made yet, so it isn't a map animal" % p)
        if ("animal.%s.map_name" % p) not in fi:
            problems.append("locale/fi/animals.json has no animal.%s.map_name" % p)
    for a in data.get("animals", []):
        if a["id"] not in PICKS:
            problems.append("%s is in map-animals.json but not in PICKS: run the tool again" % a["id"])
            continue
        if a.get("name") != listed.get(a["id"], {}).get("name"):
            problems.append("%s: name differs from animal-list.json: run the tool again" % a["id"])
        if not a.get("spots") or len(a["spots"]) > SPOTS:
            problems.append("%s: needs 1 to %d spots" % (a["id"], SPOTS))
        for s in a.get("spots", []):
            c = cell(s["lat"], s["lon"])
            if tile_id(c) != s["tile"] or centre(c) != (s["lat"], s["lon"]):
                problems.append("%s: spot %s isn't its tile's centre" % (a["id"], s["tile"]))
    missing = [p for p in PICKS if p not in ids]
    if missing:
        print("No spots found (left off the map): " + ", ".join(missing))
    return problems


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
    grid = Habitats(args.grid)
    old = {}
    if args.only and os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            old = {a["id"]: a for a in json.load(f)["animals"]}
    out = []
    for p in PICKS:
        a = listed[p]
        if args.only and p not in args.only:
            if p in old:
                out.append(old[p])
            continue
        pts = records(a["gbif_key"], NOT_IN.get(p, ()))
        found = spots(pts, a["habitats"], grid, NOT_IN.get(p, ()))
        print("%-18s %4d records, %d spots %s" % (p, len(pts), len(found), " ".join(s["tile"] for s in found)))
        if found:
            out.append({"id": p, "name": a["name"], "in_library": a.get("in_library"), "spots": found})
    data = {
        "about": "Animals the game's world map shows where they live (Proposal 0038 section 4). "
                 "Written by tools/map_animals.py from GBIF records and the habitat grid; edit PICKS there.",
        "credit": "Spots: GBIF.org occurrence records; habitats: RESOLVE Ecoregions 2017 (Dinerstein et al. 2017), CC BY 4.0.",
        "animals": out,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("Wrote %d animals to map-animals.json." % len(out))


if __name__ == "__main__":
    main()
