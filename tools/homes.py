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

# fields a home has that a region doesn't
HOME_ONLY = ("based_on",)
# a spot to check each home at: where it was based on
CHECK_AT = {"boreal_forest": (60.3, 24.53), "boreal_lake": (62.12, 28.51)}


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
