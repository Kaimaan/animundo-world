#!/usr/bin/env python3
"""Write docs/catalogue.md: the animals, plants, trees and foods Animundo
has, and what it's missing. (Places are on the game's map; languages are
decided separately.)

Usage:
    python3 tools/catalogue.py           # write docs/catalogue.md
    python3 tools/catalogue.py --check   # fail if docs/catalogue.md is out of date

"What we have" is read from the data itself (regions/, animals/, models/,
models/), so it is always true. "What we're missing" comes from wanted.json,
kept by hand. A wanted row whose id now exists shows as done, and this script
asks for it to be removed from wanted.json.
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "docs", "catalogue.md")
STATUS = {"wanted": "Wanted", "in_progress": "In progress", "check": "Check first", "later": "Later"}


def load(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return json.load(f)


def ids(*parts):
    d = os.path.join(ROOT, *parts)
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json")) if os.path.isdir(d) else []


def cell(text):
    if text == 0:
        return "0"
    return str(text or "").replace("|", "/").replace("\n", " ")


def table(head, rows):
    if not rows:
        return "_None yet._\n"
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(cell(c) for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def yes(flag):
    return "yes" if flag else "no"


def singular(name):
    name = name.lower()
    if name.endswith("ies"):
        return name[:-3] + "y"
    return name[:-1] if name.endswith("s") else name


class Catalogue:
    def __init__(self):
        self.regions = {i: load("regions", i + ".json") for i in ids("regions")}
        self.animals = {i: load("animals", i + ".json") for i in ids("animals") if i != "archetypes"}
        self.plants = {i: load("models", "plants", i + ".json") for i in ids("models", "plants")}
        self.wanted = load("wanted.json")
        self.done = []   # wanted rows that now exist

    # --- what we have -----------------------------------------------------------

    def homes(self, animal_id):
        out = []
        for rid, r in self.regions.items():
            a = r.get("animals", {})
            lists = [a.get(k, []) for k in ("playable", "predators", "prey")] + [[f.get("kind") for f in r.get("fish", [])]]
            if any(animal_id in lst for lst in lists):
                out.append(rid)
        return out

    def plant_places(self, plant_id):
        return [rid for rid, r in self.regions.items()
                if any(p.get("model") == plant_id for p in r.get("ground_cover", {}).get("plants", []))]

    # --- what we're missing ------------------------------------------------------

    def wanted_rows(self, kind, have, cols):
        rows = []
        for w in self.wanted.get(kind, []):
            status = STATUS.get(w.get("status"), w.get("status", ""))
            if w.get("status") == "in_progress" and w.get("who"):
                status += f" ({w['who']})"
            if w.get("id") and w["id"] in have:
                status = "Done: remove from wanted.json"
                self.done.append(f"{kind}: {w['id']}")
            rows.append([c(w) for c in cols] + [status])
        return rows

    @staticmethod
    def named(w):
        bits = [f"**{w.get('name', '')}**"]
        if w.get("local"):
            bits.append(f"({w['local']}")
            bits[-1] += f", *{w['latin']}*)" if w.get("latin") else ")"
        elif w.get("latin"):
            bits.append(f"(*{w['latin']}*)")
        return " ".join(bits)

    # --- the page ------------------------------------------------------------------

    def page(self):
        W = self.wanted
        count = lambda k: sum(1 for w in W.get(k, []) if w.get("status") in ("wanted", "check"))
        busy = lambda k: sum(1 for w in W.get(k, []) if w.get("status") == "in_progress")
        trees = sorted({t.get("shape") for r in self.regions.values() for t in r.get("trees", {}).get("mix", [])})
        foods = [(rid, f) for rid, r in self.regions.items() for f in r.get("food", [])]
        # food plants in the ground cover whose kind the region's food list doesn't name (porcini: mushrooms)
        for rid, r in self.regions.items():
            listed = {f.get("kind") for f in r.get("food", [])}
            extra = {}
            for p in r.get("ground_cover", {}).get("plants", []):
                food = p.get("food")
                kind = food.get("kind") if isinstance(food, dict) else food
                if kind and kind not in listed:
                    extra.setdefault(kind, []).extend(p.get("names", [p.get("model", "")]))
            foods += [(rid, {"kind": k, "names": n}) for k, n in extra.items()]

        s = ["# Animundo catalogue", "",
             "Everything in the game, and what it's still missing. **Generated:** don't edit this page. "
             "\"Have\" is read from the game's data files, so it's always up to date. \"Wanted\" comes from "
             "[`wanted.json`](../wanted.json): to claim a row, open a pull request that sets its `status` to "
             "`in_progress` with your name in `who`. When your addition is merged, delete its row. "
             "Run `python3 tools/catalogue.py` to rebuild this page.", "",
             "How to add each kind of thing: [CONTRIBUTING.md](../CONTRIBUTING.md). "
             "How it should look: [ART.md](../ART.md).", "",
             table(["", "Have", "Wanted", "In progress"], [
                 ["Animals", len(self.animals), count("animals"), busy("animals")],
                 ["Plants", len(self.plants), count("plants"), busy("plants")],
                 ["Trees", len(trees), count("trees"), busy("trees")],
                 ["Foods", len({f.get("kind") for _, f in foods}), count("foods"), busy("foods")],
             ])]

        # animals
        rows = []
        for aid, a in self.animals.items():
            text = a.get("text", {})
            name = text.get("title", aid)
            spec = os.path.exists(os.path.join(ROOT, "models", aid + ".json"))
            preview = f"[preview](../models/previews/{aid}.png)" if os.path.exists(os.path.join(ROOT, "models", "previews", aid + ".png")) else ""
            rows.append([f"**{name}** (*{a.get('latin', '')}*)", ", ".join(self.homes(aid)) or "nowhere yet",
                         ("built from a spec " + preview).strip() if spec
                         else "made in code: wants a spec" if not a.get("model") else "downloaded: rebuild from a spec",
                         yes(a.get("year")), yes(a.get("family")), yes(text.get("about_looks"))])
        s += ["## Animals", "", "### Have", "",
              table(["Animal", "Lives in", "Model", "Year", "Baby start", "Field guide"], rows),
              "### Wanted", "", table(["Animal", "Place", "Feeds", "Needs", "Status"],
                                      self.wanted_rows("animals", self.animals, [self.named, lambda w: w.get("place"), lambda w: w.get("feeds"), lambda w: w.get("needs")]))]

        # plants
        rows = []
        for pid, p in self.plants.items():
            y = p.get("year", {})
            rows.append([f"**{p.get('name', pid)}** (*{p.get('latin', '')}*)", p.get("kind", ""),
                         ", ".join(self.plant_places(pid)) or "nowhere yet", y.get("leaves", ""),
                         f"[preview](../models/previews/plants/{pid}.png)"])
        s += ["## Plants", "", "### Have", "", table(["Plant", "Kind", "Grows in", "Leaves", "Preview"], rows),
              "### Wanted", "", table(["Plant", "Place", "Feeds", "Needs", "Status"],
                                      self.wanted_rows("plants", self.plants, [self.named, lambda w: w.get("place"), lambda w: w.get("feeds"), lambda w: w.get("needs")]))]

        # trees
        rows = [[f"`{t}`", ", ".join(rid for rid, r in self.regions.items() if any(m.get("shape") == t for m in r.get("trees", {}).get("mix", []))),
                 "made in code"] for t in trees]
        s += ["## Trees", "", "Trees are still made in code, because animals climb them and hide in them. Ask the core team before starting one.", "",
              "### Have", "", table(["Shape", "Grows in", "How"], rows),
              "### Wanted", "", table(["Tree", "Place", "Feeds", "Needs", "Status"],
                                      self.wanted_rows("trees", {t: 1 for t in trees}, [self.named, lambda w: w.get("place"), lambda w: w.get("feeds"), lambda w: w.get("needs")]))]

        # foods
        plant_names = {singular(p.get("name", pid)): pid for pid, p in self.plants.items()}
        rows = []
        for rid, f in foods:
            seen = []
            for n in f.get("names", []):
                pid = plant_names.get(singular(n))
                seen.append(f"{n} (grows there)" if pid and rid in self.plant_places(pid) else n)
            eaters = [self.animals[a].get("text", {}).get("title", a) for a in self.animals
                      if f.get("kind") in (self.animals[a].get("diet") or [])]
            rows.append([f"`{f.get('kind')}`", rid, ", ".join(seen), ", ".join(eaters)])
        s += ["## Foods", "", "What animals find to eat. A food name marked \"grows there\" has a plant you can see in that place; "
              "the others still need their plant (see Plants, Wanted).", "",
              "### Have", "", table(["Food", "Place", "Real names", "Eaten by"], rows),
              "### Wanted", "", table(["Food", "Feeds", "Needs", "Status"],
                                      self.wanted_rows("foods", {}, [self.named, lambda w: w.get("feeds"), lambda w: w.get("needs")]))]

        # core team
        s += ["## Core team work", "", "Code changes that more content depends on. These are for the core team; "
              "the data and models they unlock can be made before they're done.", "",
              table(["Area", "Work", "Why", "Status"], [[w.get("area"), f"**{w.get('name')}**", w.get("why"), STATUS.get(w.get("status"), w.get("status"))]
                                                      for w in W.get("core", [])])]
        return "\n".join(s).rstrip() + "\n"


def main():
    cat = Catalogue()
    text = cat.page()
    for d in cat.done:
        print(f"note: {d} is done; delete its row from wanted.json")
    if "--check" in sys.argv:
        current = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if current != text:
            print("docs/catalogue.md is out of date: run python3 tools/catalogue.py")
            sys.exit(1)
        print("ok   docs/catalogue.md")
        return
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote docs/catalogue.md: {len(cat.animals)} animals, {len(cat.plants)} plants")


main()
