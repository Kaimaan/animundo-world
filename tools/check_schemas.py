#!/usr/bin/env python3
"""Check content files against the JSON Schemas in schemas/.

Usage:
    python3 tools/check_schemas.py                  # every content file
    python3 tools/check_schemas.py animals/fox.json # some files
    python3 tools/check_schemas.py --root DIR       # the content in another checkout

Needs the jsonschema package (pip install jsonschema). Exits non-zero and lists
every problem. Besides the schemas it checks the few rules that a JSON Schema
can't express, all inside one file or between a model spec and its animal file:
the id equals the file name, a part's colour and bone exist, mirrored names end
in _l, and the bone and triangle budgets in ART.md. Biomes and homes are
checked against the region schema too, as a place without a spot: their four
home fields allowed, the id their own name and the country empty. Everything else that needs
several files is checked by validate_region.py, check_animals.py and check_models.py.
"""
import argparse
import copy
import json
import os
import re
import sys

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMAS = os.path.join(HERE, "..", "schemas")
NAMES = ["region", "animal", "archetypes", "model", "tree", "locale", "wanted", "seas"]
MAX_BONES = 16             # ART.md: up to 16 bones
MAX_WILDLIFE_TRIANGLES = 800  # ART.md: wildlife that is never played, 400 to 800


def load_schemas():
    schemas = {}
    for name in NAMES:
        with open(os.path.join(SCHEMAS, name + ".schema.json"), encoding="utf-8") as f:
            schemas[name] = json.load(f)
    schemas["home"] = home_schema(schemas["region"])
    registry = Registry().with_resources(
        (s["$id"], Resource.from_contents(s)) for s in schemas.values())
    return schemas, registry


def home_schema(region):
    """A biome or home is a region without a spot (homes/README.md): the same
    rules (its lakes, bogs and places named, Kai 2026-10-30), plus its four home
    fields; its id is its own name and it has no country yet."""
    home = copy.deepcopy(region)
    home["$id"] = region["$id"].replace("region.schema.json", "home.schema.json")
    props = home["properties"]
    props["id"] = {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"}
    props["country"] = {"type": "string"}
    props["ecoregions"] = {"type": "array", "items": {"type": "integer"}}
    props["habitat"] = {"$ref": "#/$defs/text"}
    props["based_on"] = {"type": "string"}
    props["about"] = {"type": "string"}
    return home


def schema_for(rel):
    """(schema name, definition in its $defs or None) for a file, or None if no schema covers it."""
    parts = rel.split("/")
    name = parts[-1][:-5] if parts[-1].endswith(".json") else None
    if name is None:
        return None
    if parts[0] == "regions" and len(parts) == 2:
        return "region", None
    if parts[0] == "animals" and len(parts) == 2:
        return ("archetypes", None) if name == "archetypes" else ("animal", None)
    if parts[0] == "models" and len(parts) == 2:
        return "model", "animal_model"
    if parts[:2] == ["models", "plants"] and len(parts) == 3:
        return "model", "plant_model"
    if parts[:2] == ["models", "trees"] and len(parts) == 3:
        return "tree", None
    if rel == "locale/languages.json":
        return "locale", "languages"
    if parts[0] == "locale" and len(parts) == 3:
        return "locale", name
    if rel == "wanted.json":
        return "wanted", None
    if rel == "seas/names.json":
        return "seas", None
    if parts[0] in ("biomes", "homes") and len(parts) == 2:
        return "home", None
    return None


def content_files(root):
    out = ["wanted.json", "seas/names.json"]
    for d in ("regions", "biomes", "homes", "animals", "models", "models/plants", "models/trees", "locale"):
        if os.path.isdir(os.path.join(root, d)):
            out += [f"{d}/{f}" for f in sorted(os.listdir(os.path.join(root, d))) if f.endswith(".json")]
    for lang in sorted(os.listdir(os.path.join(root, "locale"))):
        if os.path.isdir(os.path.join(root, "locale", lang)):
            out += [f"locale/{lang}/{f}" for f in sorted(os.listdir(os.path.join(root, "locale", lang))) if f.endswith(".json")]
    return [p for p in out if os.path.exists(os.path.join(root, p))]


def where(error):
    path = "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in error.absolute_path)
    return path.lstrip(".") or "(top)"


def message(error):
    if error.validator == "not" and error.absolute_path and error.absolute_path[-1] == "name":
        return (f"{error.instance!r} is a placeholder, not a name: a lake, bog or place "
                "without a real name is left out (regions schema, $defs/name)")
    return error.message


def mirrored(name):
    return name[:-2] + "_r" if name.endswith("_l") else None


def model_rules(root, rel, d, file_id):
    """Rules inside a model spec that a schema can't express."""
    errors = []
    if d.get("id") != file_id:
        errors.append(f'"id" must equal the file name ("{file_id}")')
    colors = d.get("colors", {}) if isinstance(d.get("colors"), dict) else {}
    bones = {"root"}
    count = 0
    for b in d.get("bones", []) if isinstance(d.get("bones"), list) else []:
        if not isinstance(b, dict):
            continue
        name = str(b.get("name"))
        if b.get("parent", "root") not in bones:
            errors.append(f'bone "{name}": parent "{b.get("parent")}" must be defined above it')
        if name in bones:
            errors.append(f'bone "{name}" is defined twice')
        bones.add(name)
        count += 1
        if b.get("mirror"):
            if mirrored(name) is None:
                errors.append(f'bone "{name}": a mirrored name must end in _l')
            else:
                bones.add(mirrored(name))
                count += 1
    if rel.startswith("models/plants/") is False and count > MAX_BONES:
        errors.append(f"{count} bones (with mirrored copies); the budget is {MAX_BONES} (ART.md)")
    for p in d.get("parts", []) if isinstance(d.get("parts"), list) else []:
        if not isinstance(p, dict):
            continue
        name = str(p.get("name"))
        if "color" in p and p["color"] not in colors:
            errors.append(f'part "{name}": colour "{p["color"]}" is not in "colors"')
        if "bone" in p and p["bone"] not in bones:
            errors.append(f'part "{name}": bone "{p["bone"]}" is not in "bones"')
        if p.get("mirror") and mirrored(name) is None:
            errors.append(f'part "{name}": a mirrored name must end in _l')
    if isinstance(d.get("seasons"), dict):
        for season, changes in d["seasons"].items():
            for c in changes if isinstance(changes, dict) else []:
                if c not in colors:
                    errors.append(f'"seasons.{season}.{c}" is not a colour in "colors"')
    animal_file = os.path.join(root, "animals", file_id + ".json")
    if not rel.startswith("models/plants/") and os.path.exists(animal_file):
        try:
            with open(animal_file, encoding="utf-8") as f:
                animal = json.load(f)
        except ValueError:
            animal = {}
        skin = d.get("skin", {})
        tris = skin.get("triangles", 1000) if isinstance(skin, dict) else 0
        if isinstance(animal, dict) and not animal.get("playable", False) and tris > MAX_WILDLIFE_TRIANGLES:
            errors.append(f"skin.triangles is {tris}, but animals/{file_id}.json isn't playable: "
                          f"wildlife is at most {MAX_WILDLIFE_TRIANGLES} (ART.md)")
    return errors


def check(root, rel, schemas, registry):
    target = schema_for(rel)
    if target is None:
        return []
    try:
        with open(os.path.join(root, rel), encoding="utf-8") as f:
            d = json.load(f)
    except ValueError as e:
        return [f"not valid JSON: {e}"]
    name, part = target
    schema = schemas[name]
    if part is not None:
        if part not in schema.get("$defs", {}):
            return [f'no definition "{part}" in schemas/{name}.schema.json: is the file name right?']
        schema = {"$schema": schema["$schema"], "$ref": f'{schema["$id"]}#/$defs/{part}'}
    validator = Draft202012Validator(schema, registry=registry)
    errors = [f"{where(e)}: {message(e)}" for e in sorted(validator.iter_errors(d), key=lambda e: list(e.absolute_path))]
    file_id = os.path.basename(rel)[:-5]
    if name in ("region", "home") and isinstance(d, dict) and d.get("id") != file_id:
        errors.append(f'"id" must equal the file name ("{file_id}")')
    if name == "model" and isinstance(d, dict):
        errors += model_rules(root, rel, d, file_id)
    if name == "archetypes" and isinstance(d, dict):
        for a, v in d.items():
            if isinstance(v, dict) and "extends" in v and v["extends"] not in d:
                errors.append(f'{a}: extends "{v["extends"]}", which isn\'t an archetype here')
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--root", default=os.path.join(HERE, ".."))
    args = ap.parse_args()
    root = os.path.realpath(args.root)
    schemas, registry = load_schemas()
    files = [os.path.relpath(os.path.realpath(f), root) for f in args.files] or content_files(root)
    failed = 0
    for rel in files:
        rel = rel.replace(os.sep, "/")
        if schema_for(rel) is None:
            print(f"skip {rel} (no schema)")
            continue
        problems = check(root, rel, schemas, registry)
        if problems:
            failed += 1
            print(f"FAIL {rel}")
            for p in problems:
                print(f"  - {p}")
        else:
            print(f"ok   {rel}")
    print(f"{len(files)} files, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
