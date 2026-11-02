#!/usr/bin/env python3
"""check_place.py says yes to a good new place and no to broken ones, each for
the check named for it.

The good place is "Test taiga" on one z10 tile east of Nuuksio, made from
tests/tiles/n_412_301.json (a boreal_taiga tile, renamed to z10_0583_0295),
with the fox and the moose. Broken copies: a start outside its tiles, a tile
not given, Nuuksio's tile, tiles that aren't a rectangle, an animal that
isn't in animals/, a playable animal that isn't playable, an animal with no
food on the tile (the clownfish in the taiga), and the fox starting on the
open sea (tests/tile_region/n_415_480_open_sea renamed). A place that breaks
its schema skips the rest.

Usage: python3 tools/test_check_place.py
"""
import copy
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
TILE = "z10_0583_0295"
LAT, LON = 60.33, 25.14   # inside TILE


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def z10(t, tid):
    t = copy.deepcopy(t)
    t["id"] = tid
    t.pop("grid_north", None)
    return t


GOOD = {
    "id": "fi_test_taiga",
    "name": {"en": "Test taiga", "fi": "Testitaiga"},
    "country": "Finland",
    "center": {"lat": LAT, "lon": LON},
    "tiles": [[583, 295]],
    "species": {"playable": ["fox", "moose"], "predators": ["fox"], "prey": []},
    "points": [{"kind": "start", "id": "default", "lat": LAT, "lon": LON, "facing": "north"}],
    "live": True,
}


def run(place, tiles, tmp):
    paths = []
    for i, t in enumerate(tiles):
        p = os.path.join(tmp, f"tile{i}.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(t, f)
        paths.append(p)
    pp = os.path.join(tmp, "place.json")
    with open(pp, "w", encoding="utf-8") as f:
        json.dump(place, f)
    r = subprocess.run([sys.executable, os.path.join(HERE, "check_place.py"), pp, *paths], capture_output=True, text=True, timeout=600)
    return r.returncode, json.loads(r.stdout)


def failed(report):
    return sorted(r["check"] for r in report["results"] if r["status"] == "fail")


def main():
    errors = []
    taiga = z10(load("tests/tiles/n_412_301.json"), TILE)
    sea = z10(load("tests/tile_region/n_415_480_open_sea.tile.json"), TILE)

    def expect(name, place, tiles, want):
        with tempfile.TemporaryDirectory() as tmp:
            code, report = run(place, tiles, tmp)
        got = failed(report)
        if want == [] and (code != 0 or got):
            errors.append(f"{name}: should pass, failed {got}: {json.dumps(report)[:1500]}")
        elif want and (code != 1 or got != want):
            errors.append(f"{name}: should fail {want}, failed {got}")
        print(f"{name}: {'pass' if not got else 'fail ' + ', '.join(got)}")

    expect("a good place", GOOD, [taiga], [])

    p = copy.deepcopy(GOOD)
    p["points"][0]["lat"] = 61.5
    expect("a start outside its tiles", p, [taiga], ["start"])

    expect("a tile not given", GOOD, [], ["tiles"])

    p = copy.deepcopy(GOOD)
    p["tiles"] = [[582, 295], [583, 295]]
    expect("Nuuksio's tile", p, [taiga, z10(taiga, "z10_0582_0295")], ["tiles"])

    p = copy.deepcopy(GOOD)
    p["tiles"] = [[583, 295], [584, 296]]
    expect("tiles that aren't a rectangle", p, [taiga, z10(taiga, "z10_0584_0296")], ["tiles"])

    p = copy.deepcopy(GOOD)
    p["species"]["playable"].append("not_an_animal")
    expect("an animal that isn't there", p, [taiga], ["animals", "habitat", "laid", "playable"])

    p = copy.deepcopy(GOOD)
    p["species"]["playable"].append("vole")
    expect("a playable animal that isn't playable", p, [taiga], ["animals", "laid", "playable"])

    p = copy.deepcopy(GOOD)
    p["species"]["playable"].append("reef_shark")
    expect("a reef animal in the taiga", p, [taiga], ["habitat"])

    expect("the fox starting on the open sea", GOOD, [sea], ["habitat", "laid", "playable", "start"])

    p = copy.deepcopy(GOOD)
    del p["name"]["fi"]
    expect("no Finnish name", p, [taiga], ["schema"])

    for e in errors:
        print("ERROR:", e)
    print(f"check_place tests: {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
