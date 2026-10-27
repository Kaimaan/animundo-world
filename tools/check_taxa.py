#!/usr/bin/env python3
"""One real species, one file: check every animal file's and plant spec's taxon.

A species is known by its GBIF taxon ID (`taxon.gbif_key`, written by
tools/taxon.py), not by the file id or the Latin spelling, so "red_fox" can't
quietly be added next to "fox". Offline: it reads the files only; run
`python3 tools/taxon.py --verify` to check the IDs against GBIF itself.

Usage:
    python3 tools/check_taxa.py               # this checkout
    python3 tools/check_taxa.py --root DIR    # another checkout

Rules:
- every animal file (not archetypes.json) and every plant spec has a taxon,
  and its name is the file's latin;
- no two animal files, and no two plant specs, have the same gbif_key, unless
  the others are a stage_of the one (young_perch is a stage of perch);
- a stage_of names an animal file of the same taxon that is not a stage itself;
- every entry in poisonous-plants.json has a name and a gbif_key, and a
  place's ground cover may mark a plant of that taxon as food (animals really
  eat some: Kai, 2026-10-27) only when the plant warns people in
  locale/en/plants.json (`plant.<id>.warning` and `plant.<id>.about_safety`).

Exits non-zero and lists every problem.
"""
import argparse
import json
import os
import sys


def files(root, folder, skip=()):
    d = os.path.join(root, folder)
    out = {}
    for f in sorted(os.listdir(d)):
        if f.endswith(".json") and f not in skip:
            with open(os.path.join(d, f), encoding="utf-8") as fh:
                out[f[:-5]] = json.load(fh)
    return out


def check(kind, docs, errors):
    by_key = {}
    for id, d in docs.items():
        t = d.get("taxon")
        if not isinstance(t, dict) or not isinstance(t.get("gbif_key"), int):
            errors.append(f'{kind} {id}: no taxon (add one with: python3 tools/taxon.py --fill)')
            continue
        if t.get("name") != d.get("latin"):
            errors.append(f'{kind} {id}: latin "{d.get("latin")}" is not its taxon\'s name "{t.get("name")}"')
        by_key.setdefault(t["gbif_key"], []).append(id)
    for id, d in docs.items():
        parent = d.get("stage_of")
        if parent is None:
            continue
        if parent not in docs:
            errors.append(f'{kind} {id}: stage_of "{parent}" is not a file')
        elif docs[parent].get("stage_of") is not None:
            errors.append(f'{kind} {id}: stage_of "{parent}", which is a stage itself')
        elif docs[parent].get("taxon", {}).get("gbif_key") != d.get("taxon", {}).get("gbif_key"):
            errors.append(f'{kind} {id}: stage_of "{parent}", a different species')
    for key, ids in sorted(by_key.items()):
        whole = [i for i in ids if docs[i].get("stage_of") is None]
        if len(whole) > 1:
            name = docs[whole[0]]["taxon"].get("name")
            errors.append(f'{kind}s {", ".join(whole)} are the same species ({name}, GBIF {key}): '
                          f'one species, one file (or mark the others stage_of the first)')


def check_poison(root, plants, errors):
    path = os.path.join(root, "poisonous-plants.json")
    if not os.path.isfile(path):
        errors.append("poisonous-plants.json is missing")
        return
    with open(path, encoding="utf-8") as fh:
        entries = json.load(fh).get("plants", [])
    poison = {}
    for e in entries:
        if not isinstance(e.get("name"), str) or not isinstance(e.get("gbif_key"), int):
            errors.append(f"poisonous-plants.json: an entry needs a name and a gbif_key: {e}")
            continue
        poison[e["gbif_key"]] = e["name"]
    texts = {}
    plant_text = os.path.join(root, "locale", "en", "plants.json")
    if os.path.isfile(plant_text):
        with open(plant_text, encoding="utf-8") as fh:
            texts = json.load(fh)
    regions = files(root, "regions")
    for rid, r in regions.items():
        gc = r.get("ground_cover", {}) if isinstance(r.get("ground_cover"), dict) else {}
        for p in gc.get("plants", []):
            model = p.get("model")
            key = plants.get(model, {}).get("taxon", {}).get("gbif_key")
            if not p.get("food") or key not in poison:
                continue
            # food for animals is fine; people must be told never to eat it
            missing = [k for k in ("warning", "about_safety")
                       if not str(texts.get(f"plant.{model}.{k}", "")).strip()]
            if missing:
                errors.append(f'region {rid}: {model} ({poison[key]}) is poisonous, so as food it needs '
                              f'plant.{model}.{" and plant.{model}.".join(missing)} in locale/en/plants.json')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    args = ap.parse_args()
    errors = []
    animals = files(args.root, "animals", skip=("archetypes.json",))
    plants = files(args.root, os.path.join("models", "plants"))
    if os.path.isdir(os.path.join(args.root, "models", "trees")):   # trees are plants too: one species, one file across both
        plants.update(files(args.root, os.path.join("models", "trees")))
    check("animal", animals, errors)
    check("plant", plants, errors)
    check_poison(args.root, plants, errors)
    for e in errors:
        print("ERROR: " + e, file=sys.stderr)
    print(f"{len(animals)} animals and {len(plants)} plants: {len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
