#!/usr/bin/env python3
"""Check every model built by tools/build_model.sh, without Godot.

A port of the game's tools/check_models.gd: it must reject everything that
checker rejects, with the same messages. Each animal (models/<id>.json) must
have a built assets/animals/<id>.glb with a skeleton, a mesh and every
animation clip. Each plant (models/plants/<id>.json) must follow the plant
rules a program can check, have its preview sheet and built model, and have
triangles on at least one of four dates in the starter region's year.

Usage:
    python3 tools/check_models.py              # this checkout, after building the models
    python3 tools/check_models.py --root DIR   # another checkout (also the game's)
"""
import argparse
import json
import math
import os
import re
import struct
import sys

CLIPS = ["idle", "walk", "run", "eat", "sleep"]
SEASONS = ["spring", "summer", "autumn", "winter"]
# Start dates for the northern temperate zone, used when a region gives none (season.gd).
NORTH = {"spring": "04-05", "summer": "05-25", "autumn": "09-20", "winter": "11-25"}
BEFORE = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
DEFAULT_REGION = "fi_nuuksio"
DATES = ["2026-06-10", "2026-08-10", "2026-10-10", "2027-01-20"]
ID = re.compile(r"^[a-z][a-z0-9_]*$")
LATIN = re.compile(r"^[A-Z][a-z]+ [a-z-]+( [a-z-]+)*$")
MARK = re.compile(r"^(spring|summer|autumn|winter)(\+\d+)?$")


def gd(v):
    """A value as Godot prints it in a message."""
    if v is None:
        return "<null>"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return "[" + ", ".join(f'"{x}"' if isinstance(x, str) else gd(x) for x in v) + "]"
    return str(v)


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def gd_int(s):
    """Godot's int() of a string: its leading whole number, or 0."""
    m = re.match(r"\s*[-+]?\d+", s)
    return int(m.group()) if m else 0


# --- reading a .glb ------------------------------------------------------------

COMPONENT = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


class Glb:
    def __init__(self, path):
        with open(path, "rb") as f:
            data = f.read()
        if data[:4] != b"glTF":
            raise ValueError("not a .glb")
        n = struct.unpack("<I", data[12:16])[0]
        self.gltf = json.loads(data[20:20 + n])
        self.bin = b""
        rest = 20 + n
        if rest + 8 <= len(data):
            m = struct.unpack("<I", data[rest:rest + 4])[0]
            self.bin = data[rest + 8:rest + 8 + m]

    def accessor(self, i):
        """The values of an accessor, as a list of tuples (or of numbers for scalars)."""
        acc = self.gltf["accessors"][i]
        view = self.gltf["bufferViews"][acc["bufferView"]]
        fmt = COMPONENT[acc["componentType"]]
        width = WIDTH[acc["type"]]
        size = struct.calcsize("<" + fmt)
        stride = view.get("byteStride") or size * width
        start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
        out = []
        for k in range(acc["count"]):
            v = struct.unpack_from("<" + fmt * width, self.bin, start + k * stride)
            if acc.get("normalized"):
                top = {"b": 127, "B": 255, "h": 32767, "H": 65535}.get(fmt, 1)
                v = tuple(max(x / top, -1.0) for x in v)
            out.append(v[0] if width == 1 else v)
        return out

    def mesh_nodes(self):
        """Nodes with a mesh, in scene order (the order Godot finds them in)."""
        nodes = self.gltf.get("nodes", [])
        out = []

        def walk(i):
            if "mesh" in nodes[i]:
                out.append(nodes[i])
            for c in nodes[i].get("children", []):
                walk(c)
        scenes = self.gltf.get("scenes", [])
        roots = scenes[self.gltf.get("scene", 0)]["nodes"] if scenes else range(len(nodes))
        for r in roots:
            walk(r)
        return out

    def first_surface(self, node):
        return self.gltf["meshes"][node["mesh"]]["primitives"][0]


# --- seasons (the game's season.gd) --------------------------------------------

def day_of_year(md):
    parts = md.split("-")
    if len(parts) < 2:
        return 0
    m = min(max(gd_int(parts[-2]), 1), 12)
    dd = min(max(gd_int(parts[-1]), 1), 31)
    return (BEFORE[m - 1] + dd - 1) % 365


class Season:
    def __init__(self, region, date):
        center = region.get("center", {}) if isinstance(region.get("center", {}), dict) else {}
        lat = float(center.get("lat", 0.0))
        cfg = region.get("seasons", {}) if isinstance(region.get("seasons", {}), dict) else {}
        self.doy = day_of_year(date)
        self.starts = {}
        if abs(lat) < 23.0 and not cfg:
            return   # tropics: no seasons yet
        for n in SEASONS:
            d = day_of_year(gd(cfg.get(n, NORTH[n])))
            if lat < 0.0 and n not in cfg:
                d = (d + 182) % 365
            self.starts[n] = d

    def mark_day(self, mark):
        season = mark.split("+")[0]
        if season not in self.starts:
            return -1
        offset = gd_int(mark.split("+")[1]) if "+" in mark else 0
        return (self.starts[season] + offset) % 365

    def between(self, a, b):
        if not self.starts:
            return True
        a, b = self.mark_day(a), self.mark_day(b)
        if a < 0 or b < 0:
            return True
        return (self.doy - a + 365) % 365 <= (b - a + 365) % 365


def shown(p, season):
    show = p.get("show", {}) if isinstance(p, dict) else {}
    if not isinstance(show, dict) or not show:
        return True
    return season.between(gd(show.get("from", "")), gd(show.get("until", "")))


# --- the checks ----------------------------------------------------------------

class Checker:
    def __init__(self, root):
        self.root = root
        self.errors = []
        self.plant_species = {}   # latin name -> plant id: one spec per species

    def path(self, *parts):
        return os.path.join(self.root, *parts)

    def run(self):
        count = 0
        for d, check in (("models", self.check_animal), (os.path.join("models", "plants"), self.check_plant)):
            if os.path.isdir(self.path(d)):
                for f in sorted(os.listdir(self.path(d))):
                    if f.endswith(".json"):
                        check(f[:-5])
                        count += 1
        return count

    def check_animal(self, mid):
        err = self.errors.append
        rel = f"res://assets/animals/{mid}.glb"
        if not os.path.isfile(self.path("assets", "animals", mid + ".glb")):
            err(f"{mid}: {rel} is missing. Run tools/build_model.sh models/{mid}.json")
            return
        try:
            g = Glb(self.path("assets", "animals", mid + ".glb")).gltf
        except (ValueError, KeyError, struct.error):
            err(f"{mid}: {rel} can't be read. Run tools/build_model.sh models/{mid}.json")
            return
        if not g.get("skins"):
            err(f"{mid}: no skeleton")
        if not any("mesh" in n for n in g.get("nodes", [])):
            err(f"{mid}: no mesh")
        clips = [a.get("name", "") for a in g.get("animations", [])]
        if not clips:
            err(f"{mid}: no animations")
        else:
            for clip in CLIPS:
                if clip not in clips:
                    err(f"{mid}: animation '{clip}' is missing (has {gd(sorted(clips))})")

    def check_plant(self, pid):
        """The community rules for plants (CONTRIBUTING.md, Adding plants) that a program can check."""
        spec = read_json(self.path("models", "plants", pid + ".json"))
        if not isinstance(spec, dict):
            self.errors.append(f"{pid}: models/plants/{pid}.json is not valid JSON")
            return

        def bad(msg):
            self.errors.append(f"{pid}: {msg}")
        if spec.get("id") != pid:
            bad('"id" must equal the file name')
        if not ID.search(pid):
            bad("the file name must be the English common name in lowercase with _, e.g. wood_anemone")
        for key in ["name", "author"]:
            if not (isinstance(spec.get(key), str) and spec[key].strip()):
                bad(f'"{key}" must be a non-empty text')
        latin = spec.get("latin")
        if not (isinstance(latin, str) and LATIN.search(latin)):
            bad('"latin" must be the scientific name, e.g. "Vaccinium myrtillus"')
        elif latin in self.plant_species:
            bad(f"{latin} already has a plant: {self.plant_species[latin]}. One species, one spec")
        else:
            self.plant_species[latin] = pid
        sources = spec.get("sources")
        if not (isinstance(sources, list) and sources and all(isinstance(x, str) and len(x) > 3 for x in sources)):
            bad('"sources" must list where its looks and year come from (links or book titles)')
        if spec.get("kind") not in ["ground", "bush"]:
            bad('"kind" must be "ground" or "bush"')
        parts = spec.get("parts", [])
        parts = parts if isinstance(parts, list) else []
        year = spec.get("year")
        if not isinstance(year, dict):
            bad('"year" is missing: leaves, flowers and fruit (see CONTRIBUTING.md, Its year)')
        else:
            if year.get("leaves") not in ["evergreen", "deciduous"]:
                bad('"year.leaves" must be "evergreen" or "deciduous"')
            for key in ["flowers", "fruit"]:
                if not (isinstance(year.get(key), str) and year[key].strip()):
                    bad(f'"year.{key}" must say when (or "none")')
            if year.get("leaves") == "deciduous" and not any(isinstance(p, dict) and "show" in p for p in parts):
                bad('it drops its leaves, so its leaf parts need "show" (when they are there)')
        for p in parts:
            show = p.get("show") if isinstance(p, dict) else None
            if show is not None and not (isinstance(show, dict) and MARK.search(gd(show.get("from"))) and MARK.search(gd(show.get("until")))):
                bad(f'part "{gd(p.get("name"))}": "show" must be like {{"from": "summer+50", "until": "autumn+20"}}')
        seasons = spec.get("seasons", {})
        colors = spec.get("colors", {}) if isinstance(spec.get("colors", {}), dict) else {}
        for season in seasons if isinstance(seasons, dict) else []:
            if season not in SEASONS:
                bad(f'"seasons": "{season}" isn\'t a season')
            for c in seasons[season] if isinstance(seasons[season], dict) else []:
                if c not in colors:
                    bad(f'"seasons.{season}.{c}" isn\'t a colour in "colors"')
        if not os.path.isfile(self.path("models", "previews", "plants", pid + ".png")):
            bad(f"the preview sheet is missing: run tools/build_model.sh models/plants/{pid}.json")
        glb_path = self.path("assets", "plants", pid + ".glb")
        if not os.path.isfile(glb_path):
            self.errors.append(f"{pid}: assets/plants/{pid}.glb is missing. Run tools/build_model.sh models/plants/{pid}.json")
            return
        region = read_json(self.path("regions", DEFAULT_REGION + ".json"))
        region = region if isinstance(region, dict) else {}
        counts = []
        for date in DATES:
            n = self.triangles(glb_path, parts, Season(region, date))
            if n is None:
                self.errors.append(f"{pid}: can't be built for {date}")
                return
            counts.append(n)
        if max(counts) == 0:
            self.errors.append(f"{pid}: has no triangles in any season")
        if self.built_parts(glb_path) > len(parts):
            bad("the model has more parts than the spec: build it again")
        print(f"plant {pid}: triangles on 10 Jun, 10 Aug, 10 Oct, 20 Jan: {gd(counts)}")

    def triangles(self, glb_path, parts, season):
        """Triangles of the plant on one day (the game's PlantModel), or None if it can't be built."""
        try:
            glb = Glb(glb_path)
            nodes = glb.mesh_nodes()
            if not nodes:
                return None
            prim = glb.first_surface(nodes[0])
            if "TEXCOORD_0" not in prim.get("attributes", {}):
                return None
            uvs = glb.accessor(prim["attributes"]["TEXCOORD_0"])
            idx = glb.accessor(prim["indices"]) if "indices" in prim else list(range(len(uvs)))
        except (ValueError, KeyError, IndexError, struct.error):
            return None
        here = [isinstance(p, dict) and p.get("name", "") != "" and shown(p, season) for p in parts]
        kept = 0
        for t in range(len(idx) // 3):
            part = int(math.floor(uvs[idx[t * 3]][0] + 0.5)) // 64
            if not (part < len(here) and not here[part]):
                kept += 1
        return kept

    def built_parts(self, glb_path):
        """How many spec parts the built model has (from the part marks in its UVs)."""
        most = 0
        try:
            glb = Glb(glb_path)
            for node in glb.mesh_nodes():
                prim = glb.first_surface(node)
                if "TEXCOORD_0" in prim.get("attributes", {}):
                    for uv in glb.accessor(prim["attributes"]["TEXCOORD_0"]):
                        most = max(most, int(math.floor(uv[0] + 0.5)) // 64 + 1)
        except (ValueError, KeyError, IndexError, struct.error):
            pass
        return most


def main():
    ap = argparse.ArgumentParser(description="Check every built model.")
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    args = ap.parse_args()
    ch = Checker(os.path.abspath(args.root))
    count = ch.run()
    for e in ch.errors:
        print("ERROR:", e, file=sys.stderr)
    print(f"{count} models checked, {len(ch.errors)} problems")
    sys.exit(1 if ch.errors else 0)


if __name__ == "__main__":
    main()
