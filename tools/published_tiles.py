#!/usr/bin/env python3
"""The game's published tiles, kept in tiles/published/ for the catalogue's food gaps.

Animundo Builder publishes tiles to Cloud Storage (tiles/v2/<grid>/<group>.json,
listed in tiles/v2/index.json), and live content packs add animals and plants
to them (a pack's additions/tiles.json, game decision 0059). Players download
both. This copies them here, so tools/catalogue.py can list what the animals on
real tiles can't find (game decision 0061) without reaching the cloud.

Usage:
    python3 tools/published_tiles.py fetch --account ACCOUNT   # refresh tiles/published/
    python3 tools/published_tiles.py list                      # the tiles, as the game lays them

fetch needs gcloud, signed in as an account that can read the animundo-dev
bucket and Firestore. It replaces tiles/published/ with:
    index.json               the published index, and the live packs copied
    <grid>/<group>.json      each published group file
    overlays/<pack>.json     each live pack's additions/tiles.json

tiles() gives every published tile with the places (places/, game decision
0057) and the live overlays laid over it, as the game does (Places.lay,
ContentPacks.add_to_tile).
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "tiles", "published")
PROJECT = "animundo-dev"
BUCKET = "gs://animundo-dev.firebasestorage.app"
FIRESTORE = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"
ROLES = ("playable", "predators", "prey")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        f.write("\n")


# --- fetch ------------------------------------------------------------------------

def gcloud(account, *args):
    return subprocess.run(["gcloud", *args, "--account", account, "--project", PROJECT],
                          check=True, capture_output=True, text=True).stdout


def cp(account, src, dest):
    """A Storage file to `dest`; False when it isn't there."""
    try:
        gcloud(account, "storage", "cp", f"{BUCKET}/{src}", dest)
        return True
    except subprocess.CalledProcessError:
        return False


def live_packs(account):
    """{pack id: version} for the packs every player gets (Firestore packs/, status "live")."""
    token = gcloud(account, "auth", "print-access-token").strip()
    import urllib.request
    req = urllib.request.Request(f"{FIRESTORE}/packs?pageSize=300",
                                 headers={"Authorization": f"Bearer {token}", "x-goog-user-project": PROJECT})
    with urllib.request.urlopen(req) as r:
        docs = json.load(r).get("documents", [])
    out = {}
    for d in docs:
        f = d.get("fields", {})
        status = f.get("status", {}).get("stringValue")
        version = f.get("version", {}).get("integerValue")
        if status == "live" and version:
            out[d["name"].rsplit("/", 1)[-1]] = int(version)
    return out


def fetch(account):
    with tempfile.TemporaryDirectory() as tmp:
        new = os.path.join(tmp, "published")
        os.makedirs(new)
        got = os.path.join(tmp, "got.json")
        if not cp(account, "tiles/v2/index.json", got):
            sys.exit("can't read tiles/v2/index.json")
        index = load(got)
        for group in sorted(index.get("groups", {})):
            if not cp(account, f"tiles/v2/{group}.json", got):
                sys.exit(f"can't read tiles/v2/{group}.json")
            write(os.path.join(new, group + ".json"), load(got))
        packs = {}
        for pack, version in sorted(live_packs(account).items()):
            if cp(account, f"packs/{pack}/{version}/additions/tiles.json", got):
                write(os.path.join(new, "overlays", pack + ".json"), load(got))
                packs[pack] = version
        index["packs"] = packs
        write(os.path.join(new, "index.json"), index)
        shutil.rmtree(OUT, ignore_errors=True)
        shutil.copytree(new, OUT)
    n = sum(len(load(os.path.join(OUT, g + ".json")).get("tiles", {})) for g in index["groups"])
    print(f"wrote tiles/published/: {n} tiles in {len(index['groups'])} groups, {len(packs)} live overlays")


# --- the tiles as the game lays them ------------------------------------------------

def tile_id(x, y):
    return f"z10_{x:04d}_{y:04d}"


def join(t, adds):
    """An addition's or place's animals and plants joined to the tile's own, theirs first."""
    species = t.setdefault("species", {})
    for role in ROLES:
        joined = list(adds.get(role, []))
        joined += [a for a in species.get(role, []) if a not in joined]
        species[role] = joined
    req = t.setdefault("requires", {})
    for role in ROLES:
        for a in species[role]:
            if a not in req.setdefault("animals", []):
                req["animals"].append(a)
    for side, plants in (adds.get("plants") or {}).items():
        mine = t.setdefault("plants", {}).setdefault(side, [])
        have = {p.get("id") for p in mine}
        mine += [p for p in plants if p.get("id") not in have]
        req.setdefault("plants", []).extend(p.get("id") for p in plants if p.get("id") not in req.get("plants", []))


def index():
    path = os.path.join(OUT, "index.json")
    return load(path) if os.path.isfile(path) else {}


def tiles():
    """{tile id: tile}: every published tile, with the places and live overlays laid over it."""
    ix = index()
    out = {}
    for group in sorted(ix.get("groups", {})):
        out.update(load(os.path.join(OUT, group + ".json")).get("tiles", {}))
    out = {tid: copy.deepcopy(t) for tid, t in sorted(out.items()) if isinstance(t, dict)}
    places = os.path.join(ROOT, "places")
    for f in sorted(os.listdir(places)) if os.path.isdir(places) else []:
        p = load(os.path.join(places, f)) if f.endswith(".json") else {}
        for x, y in p.get("tiles", []) if p.get("live", True) else []:
            if tile_id(x, y) in out:
                join(out[tile_id(x, y)], p.get("species", {}))
    for pack in sorted(ix.get("packs", {})):
        a = load(os.path.join(OUT, "overlays", pack + ".json"))
        for tid in a.get("tiles", []):
            if tid in out:
                join(out[tid], a)
    return out


def main(argv):
    if argv[:1] == ["fetch"] and len(argv) == 3 and argv[1] == "--account":
        fetch(argv[2])
        return 0
    if argv == ["list"]:
        for tid, t in tiles().items():
            print(tid, t.get("biome", t.get("home")), " ".join(t.get("species", {}).get("playable", [])))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
