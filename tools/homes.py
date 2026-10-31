#!/usr/bin/env python3
"""Home templates: the land of an animal's habitat, ready to copy.

A home (homes/<habitat>.json) is a region without a place: its land, trees,
plants, water, food kinds and fish, but no name, no center and no animals.
Animundo Builder's animal-first build copies one for the grown-up's spot,
then adds the animal, its food and its neighbours (spec 04, inbox #40).

Usage:
    python3 tools/homes.py check                     # every home makes a valid region
    python3 tools/homes.py make boreal_forest --id fi_lynx_forest --name "Lynx forest" \\
        --country Finland --lat 61.2 --lon 26.9 [--out regions/fi_lynx_forest.json]

`make` prints the region (or writes it with --out). The animals lists stay
empty; the builder fills them in. `make` needs only the standard library;
`check` also uses jsonschema for the region schema, when it's installed.
"""
import argparse
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
HOMES = os.path.join(ROOT, "homes")

sys.path.insert(0, HERE)
import validate_region  # noqa: E402

# fields a home has that a region doesn't: notes for builders, not players
HOME_ONLY = ("based_on", "about", "ecoregions", "habitat")
# the habitat grid's open sea (spec 04), which no ecoregion covers: its one biome lists none (game proposal 0047)
OPEN_OCEAN = "open_ocean"
# a spot to check each home at: where it was based on
CHECK_AT = {"boreal_forest": (60.3, 24.53), "boreal_lake": (62.12, 28.51),
            # Proposal 0038's lab spots: Pallas, Yasuní, the Serengeti, Pembrokeshire
            "tundra": (68.4, 23.6), "rainforest": (-1.0, -75.5), "savanna": (-2.33, 34.83), "sea": (52.0, -4.5),
            "open_sea": (59.9, 25.0)}   # the Gulf of Finland, south of Helsinki


def homes():
    return sorted(f[:-5] for f in os.listdir(HOMES) if f.endswith(".json"))


def load(habitat):
    with open(os.path.join(HOMES, habitat + ".json"), encoding="utf-8") as f:
        return json.load(f)


def make(habitat, region_id, name, country, lat, lon):
    """The region for one spot: the home renamed and centred, nothing else changed."""
    region = load(habitat)
    for key in HOME_ONLY:
        region.pop(key, None)
    region["id"] = region_id
    region["name"] = name
    region["country"] = country
    region["center"] = {"lat": round(lat, 4), "lon": round(lon, 4)}
    return region


def problems(habitat):
    """The region checks' problems for this home, made at a sample spot with one animal."""
    lat, lon = CHECK_AT.get(habitat, (60.3, 24.53))
    region = make(habitat, f"fi_home_{habitat}", "Home check", "Finland", lat, lon)
    region["animals"]["playable"] = ["fox"]
    return home_problems(habitat) + region_problems(region)


def home_problems(habitat):
    """A home's own fields: the RESOLVE ecoregions and habitat it stands for, and the home or place it was adapted from."""
    home = load(habitat)
    out = []
    eco = home.get("ecoregions")
    open_sea = home.get("habitat") == OPEN_OCEAN and eco == []   # one biome for every sea, which has no ecoregion (0047)
    if not open_sea and not (isinstance(eco, list) and eco and all(isinstance(e, int) and not isinstance(e, bool) and 1 <= e <= 999 for e in eco)
            and len(set(eco)) == len(eco)):
        out.append('"ecoregions" must list the RESOLVE 2017 ecoregion ids (ECO_ID) this home stands for')
    if home.get("terrain", {}).get("water_level", 8) != 8:
        out.append('"terrain.water_level" must be 8: every home on the tile grid has one water level, so a shared edge is '
                   'water or land on both sides alike. Make the sea deep with lower ground')
    habitats = json.load(open(os.path.join(ROOT, "animal-list.json"), encoding="utf-8"))["habitats"]
    if home.get("habitat") not in habitats + [OPEN_OCEAN]:
        out.append(f'"habitat" must be one of animal-list.json\'s habitats: {habitats}')
    if not (isinstance(home.get("based_on"), str) and home["based_on"]):
        out.append('"based_on" must name the home (or place) it was adapted from')
    return out


def region_problems(region):
    """validate_region.py's problems for a made region, then the region schema's."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, region["id"] + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(region, f)
        found = validate_region.check(path)
    try:
        import check_schemas
        from jsonschema import Draft202012Validator
    except ImportError:  # the schema half needs jsonschema; CI has it
        return found
    schemas, registry = check_schemas.load_schemas()
    validator = Draft202012Validator(schemas["region"], registry=registry)
    return found + ["schema: " + e.message for e in validator.iter_errors(region)]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    m = sub.add_parser("make")
    m.add_argument("habitat", choices=homes())
    m.add_argument("--id", required=True)
    m.add_argument("--name", required=True)
    m.add_argument("--country", required=True)
    m.add_argument("--lat", type=float, required=True)
    m.add_argument("--lon", type=float, required=True)
    m.add_argument("--out")
    args = parser.parse_args()

    if args.command == "check":
        failed = 0
        for habitat in homes():
            found = problems(habitat)
            print(("FAIL " if found else "ok   ") + f"homes/{habitat}.json")
            for line in found:
                print("     - " + line)
            failed += bool(found)
        sys.exit(1 if failed else 0)

    region = make(args.habitat, args.id, args.name, args.country, args.lat, args.lon)
    text = json.dumps(region, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
