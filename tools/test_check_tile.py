#!/usr/bin/env python3
"""check_tile.py says yes to a good tile and no to broken ones, for the right reasons.
Also: a hand-made place with a tile grid section (Proposal 0038) still passes.

tests/tiles/n_412_301.json is a tile next to Nuuksio from the boreal forest
home; it must pass, and so must the same tile with a valid blend. Each broken copy changes one thing and must fail exactly
the check named for it. A group file of the good tile and its east
neighbour passes when their shared side matches and fails "neighbours" when
it doesn't. Nuuksio and Saimaa with a "grid" section and an open edge pass
validate_region.py and the region schema; a wrong grid section fails.

Usage: python3 tools/test_check_tile.py
"""
import copy
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
GOOD = os.path.join(ROOT, "tests", "tiles", "n_412_301.json")
sys.path.insert(0, HERE)
import homes  # noqa: E402


def report(doc, tmp, name):
    path = os.path.join(tmp, name + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f)
    p = subprocess.run([sys.executable, os.path.join(HERE, "check_tile.py"), path], capture_output=True, text=True, timeout=300)
    return p.returncode, json.loads(p.stdout)


def failed(results):
    return sorted(r["check"] for r in results if r["status"] == "fail")


def broken(good):
    """(name, the check (or checks) it must fail, the broken tile)"""
    cases = []
    t = copy.deepcopy(good)   # the fox alone: it hunts, and nothing there is its prey
    t["species"] = {"playable": ["fox"], "prey": [], "predators": []}
    cases.append(("animal without its food", "food", t))
    t = copy.deepcopy(good)
    t["edges"]["n"][20] = 40
    cases.append(("edge over the world's height", "edges", t))
    t = copy.deepcopy(good)
    t["height"] = 64
    cases.append(("64 blocks tall on low land", "edges", t))
    t = copy.deepcopy(good)
    t["level"] = 40
    cases.append(("a level over the tile's height", "edges", t))
    t = copy.deepcopy(good)
    t["level"] = 6
    cases.append(("a land cell under the water level", "edges", t))
    t = copy.deepcopy(good)
    t["edges"]["n"][0] = t["edges"]["w"][64] + 1
    cases.append(("corner that doesn't match", "edges", t))
    t = copy.deepcopy(good)
    t["edges"]["e"] = t["edges"]["e"][:64]
    cases.append(("64 samples on a side", "edges", t))
    t = copy.deepcopy(good)
    t["species"]["playable"].append("lion")
    cases.append(("an animal the library doesn't have", ["animals", "region"], t))
    t = copy.deepcopy(good)
    t["requires"]["animals"].remove("vole")
    cases.append(("requires misses an animal", "animals", t))
    t = copy.deepcopy(good)
    t["home"] = t["habitat"] = "desert"
    t["requires"]["homes"] = ["desert"]
    cases.append(("a home that doesn't exist", ["animals", "region"], t))
    t = copy.deepcopy(good)
    t["ecoregion"] = 780   # the fell birch forest: the tundra home's, not boreal_forest's
    cases.append(("a home that doesn't list the tile's ecoregion", "animals", t))
    t = copy.deepcopy(good)
    t["habitat"] = "boreal_lake"   # boreal_forest and boreal_lake share the taiga: the habitat picks
    cases.append(("a home of another habitat", "animals", t))
    t = copy.deepcopy(good)
    t["blend"] = {"home": "tundra", "share": 0.3}
    cases.append(("a blend requires doesn't list", "animals", t))
    t = copy.deepcopy(good)
    t["blend"] = {"home": "tundra", "share": 0.7}
    t["requires"]["homes"].append("tundra")
    cases.append(("a blend over half the cell", "tile", t))
    return cases


def blended(good):
    """The good tile on the taiga's edge with the fell birch forest: a valid blend."""
    t = copy.deepcopy(good)
    t["blend"] = {"home": "tundra", "share": 0.3}
    t["requires"]["homes"].append("tundra")
    return t


def neighbour(good):
    """The east neighbour of the good tile: its w side is the good tile's e side."""
    t = copy.deepcopy(good)
    t["id"] = "n_413_301"
    t["center"]["lon"] = 25.1
    t["edges"]["w"] = list(good["edges"]["e"])
    t["edges"]["n"] = [good["edges"]["n"][64]] * 65
    t["edges"]["s"] = [good["edges"]["s"][64]] * 65
    t["edges"]["e"] = [t["edges"]["s"][64]] + [15] * 63 + [t["edges"]["n"][64]]
    return t


def grid_sections(errors):
    """T55: hand-made places on the grid."""
    try:
        import check_schemas
        from jsonschema import Draft202012Validator
        schemas, registry = check_schemas.load_schemas()
        schema = Draft202012Validator(schemas["region"], registry=registry)
    except ImportError:
        schema = None
    cases = [("fi_nuuksio", {"grid": "ease2_n25", "tiles": [[412, 301], [413, 301], [412, 302], [413, 302]]}, True),
             ("fi_saimaa", {"grid": "ease2_n25", "tiles": [[430, 290]]}, True),
             ("fi_saimaa", {"grid": "ease2_x25", "tiles": [[430, 290]]}, False),
             ("fi_saimaa", {"grid": "ease2_n25", "tiles": [[430, 720]]}, False),
             ("fi_saimaa", {"grid": "ease2_n25", "tiles": [[430, 290], [430, 290]]}, False),
             ("fi_saimaa", {"grid": "ease2_n25", "tiles": []}, False)]
    for rid, grid, ok in cases:
        with open(os.path.join(ROOT, "regions", rid + ".json"), encoding="utf-8") as f:
            region = json.load(f)
        region["grid"] = grid
        region.setdefault("terrain", {})["edge"] = "open"
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, rid + ".json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(region, f)
            found = homes.validate_region.check(path)
        if schema is not None:   # the schema must agree with validate_region.py
            found_schema = [e.message for e in schema.iter_errors(region)]
            if bool(found_schema) == ok:
                errors.append(f"the region schema {'refuses' if ok else 'accepts'} {rid} with {grid}: {found_schema}")
        if ok and found:
            errors.append(f"{rid} with {grid} should pass: {found}")
        if not ok and not found:
            errors.append(f"{rid} with {grid} should fail validate_region.py")
    return len(cases)


def main():
    errors = []
    with open(GOOD, encoding="utf-8") as f:
        good = json.load(f)
    with tempfile.TemporaryDirectory() as tmp:
        code, r = report(good, tmp, "good")
        if code != 0 or failed(r["results"]):
            errors.append(f"the good tile failed: {[x for x in r['results'] if x['status'] == 'fail']}")
        cases = broken(good)
        for i, (name, check, t) in enumerate(cases):
            code, r = report(t, tmp, f"broken{i}")
            if code != 1 or failed(r["results"]) != (check if isinstance(check, list) else [check]):
                errors.append(f"{name}: should fail exactly {check}, failed {failed(r['results'])} (exit {code})")
        code, r = report(blended(good), tmp, "blend")
        if code != 0 or failed(r["results"]):
            errors.append(f"a valid blend failed: {[x for x in r['results'] if x['status'] == 'fail']}")
        east = neighbour(good)
        group = {"format": 1, "grid": "ease2_n25", "group": [51, 37], "version": 1,
                 "tiles": {"n_412_301": good, "n_413_301": east}, "blocked": {"n_414_301": {"reason": "no_home", "habitat": "tundra"}}}
        code, r = report(group, tmp, "group")
        if code != 0 or not r["ok"]:
            errors.append(f"the good group failed: {r['results']} {[(t['tile'], failed(t['results'])) for t in r['tiles']]}")
        east["edges"]["w"][30] += 1
        code, r = report(group, tmp, "group_bad")
        if code != 1 or failed(r["results"]) != ["neighbours"]:
            errors.append(f"a group whose shared side doesn't match should fail neighbours, failed {failed(r['results'])}")
        ran = 4 + len(cases)
    ran += grid_sections(errors)
    for e in errors:
        print("ERROR: " + e, file=sys.stderr)
    print(f"check_tile: {ran} tiles, groups and grid sections as expected" if not errors else f"{len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
