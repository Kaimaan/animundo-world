#!/usr/bin/env python3
"""Which real species a name is: its GBIF taxon ID.

One real species, one file. A species is known by the GBIF ID of its
accepted name (the `taxon` in every animal file and plant spec), not by the
file id ("fox" and "red_fox" are the same animal) or the Latin spelling
(synonyms, old names and author names differ). tools/check_taxa.py checks
the files offline; this tool asks GBIF (https://api.gbif.org), so it needs
the network.

Usage:
    python3 tools/taxon.py "Vulpes vulpes"            # an animal's taxon, as JSON
    python3 tools/taxon.py --plant "Calluna vulgaris"  # a plant's (or a fungus's)
    python3 tools/taxon.py --fill                      # add a taxon to every file without one
    python3 tools/taxon.py --verify                    # check every file's taxon against GBIF
    python3 tools/taxon.py --same "Esox lucius"        # which existing files are this species

Only an exact match of an accepted name (or of a synonym, giving its accepted
name) is taken. A fuzzy match, or one only at genus level or above, needs a
person: the tool says so and changes nothing.
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
API = "https://api.gbif.org/v1/species/match"
RANKS = ["SPECIES", "SUBSPECIES"]
# Lichens and mushrooms are fungi, so a plant spec may be either.
KINGDOMS = {"animal": ["Animalia"], "plant": ["Plantae", "Fungi"]}


class NeedsPerson(Exception):
    """GBIF gave no exact match of a species or subspecies."""


def resolve(name, what="animal"):
    """{gbif_key, rank, name} of the accepted name for `name`, or NeedsPerson."""
    q = {"name": name, "strict": "true", "verbose": "false"}
    if what == "animal":
        q["kingdom"] = "Animalia"
    with urllib.request.urlopen(API + "?" + urllib.parse.urlencode(q), timeout=20) as r:
        m = json.load(r)
    if m.get("matchType") != "EXACT":
        raise NeedsPerson(f'"{name}": no exact match in GBIF ({m.get("matchType", "NONE")})')
    if m.get("kingdom") not in KINGDOMS[what]:
        raise NeedsPerson(f'"{name}": GBIF has it in {m.get("kingdom")}, not {" or ".join(KINGDOMS[what])}')
    if m.get("rank") not in RANKS:
        raise NeedsPerson(f'"{name}": GBIF matched a {str(m.get("rank")).lower()}, not a species or subspecies')
    if m.get("status") == "ACCEPTED":
        return {"gbif_key": m["usageKey"], "rank": m["rank"], "name": m["canonicalName"]}
    if m.get("acceptedUsageKey"):
        # a synonym: the file's species is the accepted name's
        with urllib.request.urlopen(f"https://api.gbif.org/v1/species/{m['acceptedUsageKey']}", timeout=20) as r:
            a = json.load(r)
        if a.get("rank") not in RANKS:
            raise NeedsPerson(f'"{name}" is a synonym of a {str(a.get("rank")).lower()}')
        return {"gbif_key": a["key"], "rank": a["rank"], "name": a["canonicalName"]}
    raise NeedsPerson(f'"{name}": GBIF calls it {m.get("status")}, with no accepted name')


def content_files():
    """(path, "animal" or "plant") for every animal file and plant spec."""
    out = []
    for f in sorted(os.listdir(os.path.join(ROOT, "animals"))):
        if f.endswith(".json") and f != "archetypes.json":
            out.append((os.path.join(ROOT, "animals", f), "animal"))
    for f in sorted(os.listdir(os.path.join(ROOT, "models", "plants"))):
        if f.endswith(".json"):
            out.append((os.path.join(ROOT, "models", "plants", f), "plant"))
    return out


def read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def add_taxon(path, taxon):
    """Write `taxon` on one line right after the file's "latin" line, so it reads
    next to the name and the rest of the file keeps its hand-made layout."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    at = [i for i, line in enumerate(lines) if line.startswith('  "latin": ') and line.endswith(",")]
    if len(at) != 1:
        raise NeedsPerson('no single top-level "latin" line to put the taxon after')
    lines.insert(at[0] + 1, '  "taxon": ' + json.dumps(taxon, ensure_ascii=False) + ",")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", nargs="?")
    ap.add_argument("--plant", action="store_true", help="the name is a plant or a fungus")
    ap.add_argument("--fill", action="store_true", help="add a taxon to every file that has none")
    ap.add_argument("--verify", action="store_true", help="check every file's taxon against GBIF")
    ap.add_argument("--same", metavar="NAME", help="list the files that are this species")
    args = ap.parse_args()
    problems = 0

    if args.name:
        try:
            print(json.dumps(resolve(args.name, "plant" if args.plant else "animal")))
        except NeedsPerson as e:
            print(e, file=sys.stderr)
            return 1
        return 0

    if args.same:
        try:
            t = resolve(args.same, "plant" if args.plant else "animal")
        except NeedsPerson as e:
            print(e, file=sys.stderr)
            return 1
        hits = [os.path.relpath(p, ROOT) for p, _ in content_files()
                if read(p).get("taxon", {}).get("gbif_key") == t["gbif_key"]]
        print(json.dumps({"taxon": t, "files": hits}, indent=2))
        return 0

    if not (args.fill or args.verify):
        ap.print_help()
        return 1
    for path, what in content_files():
        rel = os.path.relpath(path, ROOT)
        d = read(path)
        if args.fill and "taxon" in d:
            continue
        latin = d.get("latin", "")
        try:
            t = resolve(latin, what)
            if args.fill:
                add_taxon(path, t)
        except NeedsPerson as e:
            print(f"{rel}: {e}", file=sys.stderr)
            problems += 1
            continue
        if args.fill:
            print(f"{rel}: {t['name']} ({t['rank'].lower()}, {t['gbif_key']})")
        elif d.get("taxon") != t:
            print(f"{rel}: taxon is {d.get('taxon')}, GBIF says {t}", file=sys.stderr)
            problems += 1
    print(f"{problems} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
