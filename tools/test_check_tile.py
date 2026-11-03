#!/usr/bin/env python3
"""check_tile.py says yes to a good tile and no to broken ones, for the right reasons.
Also: a hand-made place with a tile grid section (Proposal 0038) still passes,
and an open-sea tile (game proposal 0047, tests/tile_region/n_415_480_open_sea)
passes while a land animal, a seal of a lake, a sea with no real name, an
ecoregion, too much land or ground above the water fail it.

tests/tiles/n_412_301.json is a tile next to Nuuksio from the boreal forest
home; it must pass, and so must the same tile with a valid blend. Each broken copy changes one thing and must fail exactly
the check named for it. A group file of the good tile and its east
neighbour passes when their shared side matches and fails "neighbours" when
it doesn't. Nuuksio and Saimaa with a "grid" section and an open edge pass
validate_region.py and the region schema; a wrong grid section fails.
A tile made under game decision 0062 (it writes `plants.left_out`) passes
with all its biome's plants, or with one left out for a reason, and fails a
biome plant dropped without one, an empty reason, a leave-out the biome
hasn't got and a density under 0.001. Game decision 0064: a tile's animals
are its own and then its biome's residents; a resident is left out only in
`species.left_out` with a reason, and the region the game builds has them.

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
SEA = os.path.join(ROOT, "tests", "tile_region", "n_415_480_open_sea.tile.json")   # an open-sea tile (0047)
sys.path.insert(0, HERE)
import homes  # noqa: E402
import tile_region  # noqa: E402


def report(doc, tmp, name):
    path = os.path.join(tmp, name + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f)
    p = subprocess.run([sys.executable, os.path.join(HERE, "check_tile.py"), path], capture_output=True, text=True, timeout=300)
    return p.returncode, json.loads(p.stdout)


def failed(results):
    return sorted(r["check"] for r in results if r["status"] == "fail")


def residents(t):
    """Every resident of the tile's biome (its `animals`, game decision 0064)."""
    with open(os.path.join(ROOT, "biomes", t.get("biome", t.get("home")) + ".json"), encoding="utf-8") as f:
        a = json.load(f).get("animals", {})
    return [x for k in ("playable", "prey", "predators") for x in a.get(k, [])]


def broken(good):
    """(name, the check (or checks) it must fail, the broken tile)"""
    cases = []
    t = copy.deepcopy(good)   # the fox alone: it hunts, and nothing there is its prey (the biome's other residents left out, 0064)
    t["species"] = {"playable": ["fox"], "prey": [], "predators": [],
                    "left_out": [{"id": a, "why": "test: the fox alone"} for a in residents(good) if a != "fox"]}
    cases.append(("animal without its food", "gaps", t))
    t = copy.deepcopy(good)   # game 0064: a resident is left out only with a reason
    t["species"]["left_out"] = [{"id": "herring_gull", "why": " "}]
    cases.append(("a resident left out with no reason", "animals", t))
    t = copy.deepcopy(good)
    t["species"]["left_out"] = [{"id": "lion", "why": "test"}]
    cases.append(("a leave-out the biome hasn't got", "animals", t))
    t = copy.deepcopy(good)
    t["species"]["left_out"] = [{"id": t["species"]["playable"][0], "why": "test"}]
    cases.append(("a leave-out the tile lists", "animals", t))
    t = copy.deepcopy(good)
    t["species"]["left_out"] = ["herring_gull"]
    cases.append(("a leave-out with no reason field", "animals", t))
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
    t = with_plants(good)
    t["plants"]["cover"].append({"id": "kelp", "density": 0.1})
    t["requires"]["plants"].append("kelp")
    cases.append(("a plant the library doesn't have", "tile", t))
    t = with_plants(good)
    t["requires"]["trees"].remove("birch")
    cases.append(("requires misses a tree", "tile", t))
    t = with_plants(good)
    t["plants"]["cover"] = [{"id": "heather", "density": 0.1}] * 25
    cases.append(("over 24 ground plants", "tile", t))
    t = with_plants(good)
    t["plants"]["cover"] = [{"id": "bilberry", "density": 1.0}, {"id": "white_clover", "density": 0.01}]
    cases.append(("over the triangle budget", "region", t))
    t = with_plants(good)
    t["plants"]["trees"] = [{"id": "scots_pine", "share": 1.0}]
    t["requires"]["trees"] = ["scots_pine"]
    t["plants"]["cover"] = [{"id": "wavy_hair_grass", "density": 0.06}]
    t["requires"]["plants"] = ["wavy_hair_grass"]
    t["species"] = {"playable": ["moose"], "prey": [], "predators": []}
    t["requires"]["animals"] = ["moose"]
    cases.append(("the moose's browse and berries aren't on the tile", "gaps", t))
    t = copy.deepcopy(good)
    t["biome"] = "tundra"
    cases.append(("biome and home disagree", "tile", t))
    t = copy.deepcopy(good)   # game 0054: the lake tile's old biome is retired
    t["home"] = t["habitat"] = "boreal_lake"
    t["requires"]["homes"] = ["boreal_lake"]
    cases.append(("a home that is retired", "animals", t))
    t = kept(good)   # game 0062: a tile that writes left_out keeps its biome's plants
    drop(t, "white_clover")
    cases.append(("a biome plant dropped without a reason", "tile", t))
    t = kept(good)
    drop(t, "white_clover")
    t["plants"]["left_out"] = [{"id": "white_clover", "why": " "}]
    cases.append(("a biome plant left out with no reason", "tile", t))
    t = kept(good)
    t["plants"]["left_out"] = [{"id": "kelp", "why": "grows in the sea"}]
    cases.append(("left out a plant the biome hasn't got", "tile", t))
    t = kept(good)
    t["plants"]["cover"][0]["density"] = 0.0005
    cases.append(("a density under 0.001", "tile", t))
    return cases


def broken_sea(sea):
    """(name, the check it must fail, a broken open-sea tile), game proposal 0047."""
    cases = []
    t = copy.deepcopy(sea)
    t["species"]["playable"].append("fox")
    t["requires"]["animals"].append("fox")
    cases.append(("a land animal at sea", "animals", t))
    t = copy.deepcopy(sea)
    t["species"]["playable"] = ["saimaa_seal"]
    t["requires"]["animals"] = ["saimaa_seal"]
    cases.append(("the Saimaa seal at sea", "animals", t))
    t = copy.deepcopy(sea)
    del t["sea"]
    cases.append(("a sea with no name", "tile", t))
    t = copy.deepcopy(sea)
    t["name"] = {"en": "Open ocean south of Nuuksio"}
    cases.append(("a made-up name", "tile", t))
    t = copy.deepcopy(sea)
    t["ecoregion"] = 717
    cases.append(("an ecoregion at sea", "tile", t))
    t = copy.deepcopy(sea)
    t["land_share"] = 0.4
    cases.append(("too much land for the open sea", "tile", t))
    t = copy.deepcopy(sea)
    t["land"] = "moon"
    cases.append(("a land style that doesn't exist", "tile", t))
    t = copy.deepcopy(sea)
    t["level"] = 9
    cases.append(("an open sea above the water", "edges", t))
    return cases


def with_plants(good):
    """The good tile on its biome under its old name, with its own plants (0043)."""
    t = copy.deepcopy(good)
    t["biome"] = t.pop("home")
    t["requires"]["biomes"] = t["requires"].pop("homes")
    t["plants"] = {"trees": [{"id": "norway_spruce", "share": 0.5}, {"id": "birch", "share": 0.5}],
                   "cover": [{"id": "bilberry", "density": 0.2}, {"id": "heather", "density": 0.05}, {"id": "white_clover", "density": 0.01}], "water": []}
    t["requires"]["plants"] = ["bilberry", "heather", "white_clover"]
    t["requires"]["trees"] = ["norway_spruce", "birch"]
    return t


def kept(good):
    """The good tile made under game 0062: its biome's plants, nothing left out."""
    t = copy.deepcopy(good)
    with open(os.path.join(ROOT, "biomes", t["home"] + ".json"), encoding="utf-8") as f:
        b = json.load(f)["plants"]
    t["plants"] = {k: copy.deepcopy(b.get(k, [])) for k in ("trees", "cover", "water")}
    t["plants"]["left_out"] = []
    t["requires"]["plants"] = [p["id"] for k in ("cover", "water") for p in t["plants"][k]]
    t["requires"]["trees"] = [p["id"] for p in t["plants"]["trees"]]
    return t


def drop(t, pid):
    """`t` without the plant `pid` on its cover."""
    t["plants"]["cover"] = [p for p in t["plants"]["cover"] if p["id"] != pid]
    t["requires"]["plants"].remove(pid)


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
            if check == "gaps":   # decision 0061: missing food is a gap, the tile passes
                food = next((x for x in r["results"] if x["check"] == "food"), {})
                if code != 0 or failed(r["results"]) or not food.get("gaps"):
                    errors.append(f"{name}: should pass with food gaps, failed {failed(r['results'])}, gaps {food.get('gaps')} (exit {code})")
                continue
            if code != 1 or failed(r["results"]) != (check if isinstance(check, list) else [check]):
                errors.append(f"{name}: should fail exactly {check}, failed {failed(r['results'])} (exit {code})")
        code, r = report(blended(good), tmp, "blend")
        if code != 0 or failed(r["results"]):
            errors.append(f"a valid blend failed: {[x for x in r['results'] if x['status'] == 'fail']}")
        code, r = report(with_plants(good), tmp, "plants")
        if code != 0 or failed(r["results"]):
            errors.append(f"a tile with its biome and own plants failed: {[x for x in r['results'] if x['status'] == 'fail']}")
        t = kept(good)
        code, r = report(t, tmp, "kept")
        if code != 0 or failed(r["results"]):
            errors.append(f"a tile that keeps its biome's plants failed: {[x for x in r['results'] if x['status'] == 'fail']}")
        drop(t, "white_clover")
        t["plants"]["left_out"] = [{"id": "white_clover", "why": "test: no clover here"}]
        code, r = report(t, tmp, "left_out")
        if code != 0 or failed(r["results"]):
            errors.append(f"a biome plant left out with a reason failed: {[x for x in r['results'] if x['status'] == 'fail']}")
        t = copy.deepcopy(good)   # game 0064: a tile with only the moose still gets the biome's residents
        t["species"] = {"playable": ["moose"], "prey": [], "predators": []}
        t["requires"]["animals"] = ["moose"]
        t["species"]["left_out"] = [{"id": "pike", "why": "test: no water here"}]
        made = tile_region.place(t)
        if "herring_gull" not in made["animals"]["playable"] or "vole" not in made["animals"]["prey"] or "pike" in made["animals"]["playable"]:
            errors.append(f"a moose-only tile doesn't get its biome's residents less its left_out: {made['animals']}")
        code, r = report(t, tmp, "residents")
        if code != 0 or failed(r["results"]):
            errors.append(f"a tile with only its biome's residents failed: {[x for x in r['results'] if x['status'] == 'fail']}")
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
        old = copy.deepcopy(good)   # game 0054: an already-published version keeps its retired biome
        old["home"] = old["habitat"] = "boreal_lake"
        old["requires"]["homes"] = ["boreal_lake"]
        group_old = {"format": 1, "grid": "ease2_n25", "group": [51, 37], "version": 1,
                     "tiles": {"n_412_301": old}, "blocked": {}}
        code, r = report(group_old, tmp, "group_retired")
        if code != 0 or not r["ok"]:
            errors.append(f"a published tile on a retired biome failed: {r['results']} {[(t['tile'], failed(t['results'])) for t in r['tiles']]}")
        with open(SEA, encoding="utf-8") as f:
            sea = json.load(f)
        code, r = report(sea, tmp, "sea")
        if code != 0 or failed(r["results"]):
            errors.append(f"the open-sea tile failed: {[x for x in r['results'] if x['status'] == 'fail']}")
        sea_cases = broken_sea(sea)
        for i, (name, check, t) in enumerate(sea_cases):
            code, r = report(t, tmp, f"sea{i}")
            if code != 1 or failed(r["results"]) != (check if isinstance(check, list) else [check]):
                errors.append(f"{name}: should fail exactly {check}, failed {failed(r['results'])} (exit {code})")
        ran = 8 + len(cases) + len(sea_cases)
    ran += grid_sections(errors)
    for e in errors:
        print("ERROR: " + e, file=sys.stderr)
    print(f"check_tile: {ran} tiles, groups and grid sections as expected" if not errors else f"{len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
