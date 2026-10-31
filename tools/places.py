#!/usr/bin/env python3
"""The place list: the game's built places, for Animundo Builder.

The builder (decisions D10 and D11) suggests places of interest from Wikidata.
A picked place that the game already has, with the picked animal playable in
it, needs no build: "Ready, go and play". This list is how the builder knows
which places are built. A picked place is a built one when its Wikidata id
equals a place's `wikidata` here.

regions/*.json are the source (draft_* files and draft regions are left out).
The English name is the region's `name`; the Finnish one is
`region.<id>.name` in locale/fi/regions.json. `country` is the ISO 3166-1
code from the id (`fi_nuuksio` is FI), as in the builder's place list.

    python3 tools/places.py           # write places.json
    python3 tools/places.py --check   # offline: places.json matches the regions
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "places.json")
ANIMAL_LISTS = ("playable", "predators", "prey")


def finnish_names():
    with open(os.path.join(ROOT, "locale", "fi", "regions.json"), encoding="utf-8") as f:
        return json.load(f)


def entries():
    fi = finnish_names()
    out, problems = [], []
    for path in sorted(glob.glob(os.path.join(ROOT, "regions", "*.json"))):
        stem = os.path.basename(path)[:-5]
        if stem.startswith("draft_"):
            continue
        with open(path, encoding="utf-8") as f:
            region = json.load(f)
        if region.get("status") == "draft":
            continue
        fi_name = fi.get(f"region.{stem}.name")
        if not fi_name:
            problems.append(f"{stem}: no Finnish name (region.{stem}.name in locale/fi/regions.json)")
        if not region.get("wikidata"):
            problems.append(f"{stem}: no wikidata id")
        animals = region.get("species", region.get("animals", {}))   # a place on a biome names its species as a tile does
        out.append({
            "id": stem,
            "name": {"en": region["name"], "fi": fi_name},
            "country": stem.split("_", 1)[0].upper(),
            "center": {"lat": region["center"]["lat"], "lon": region["center"]["lon"]},
            "wikidata": region.get("wikidata"),
            "animals": {k: animals.get(k, []) for k in ANIMAL_LISTS},
        })
    seen = {}
    for e in out:
        if e["wikidata"] in seen:
            problems.append(f"{e['id']}: the same wikidata id as {seen[e['wikidata']]}")
        seen.setdefault(e["wikidata"], e["id"])
    return out, problems


def document(places):
    return {
        "about": "The game's built places, for Animundo Builder. Written by tools/places.py from regions/; edit the regions.",
        "places": places,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="offline: compare places.json with the regions")
    args = parser.parse_args()
    places, problems = entries()

    if args.check:
        with open(OUT, encoding="utf-8") as f:
            written = json.load(f)
        if written != document(places):
            problems.append("places.json is out of date; run tools/places.py")
    else:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(document(places), f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"wrote places.json: {len(places)} places")

    for p in problems:
        print(f"places: {p}", file=sys.stderr)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
