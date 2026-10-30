#!/usr/bin/env python3
"""Check every animal and every translation, without Godot.

A port of the game's tools/check_animals.gd: it must reject everything that
checker rejects, with the same messages. It reads the files the way the game
does (an animal is its archetype chain's defaults with its own file on top).

Usage:
    python3 tools/check_animals.py                # this checkout
    python3 tools/check_animals.py --strict       # translation gaps are errors too
    python3 tools/check_animals.py --root DIR     # another checkout (also the game's)
    python3 tools/check_animals.py --no-built-models

Exits non-zero and lists every problem; translation gaps are only warnings
(a language can be partly done) unless --strict is given.

Two checks need more than content files. A model file must exist in
assets/animals/, which tools/build_model.sh builds (--no-built-models skips
that, before the models are built). The "ui.*" keys written in the game's
code are checked only when --root is a game checkout with scripts/.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from layers import resolve   # a layered place (game proposal 0043)
except ImportError:   # the game repo's copy of this tool has no layers.py
    def resolve(region):
        return region

REQUIRED_PLAYABLE = ["title", "menu_sub", "menu_wild", "night_hint", "too_exposed",
                     "sheltered", "hungry", "no_food", "rain_start", "rain_stop"]
MODES = ["safe", "survival", "wild"]
# Words that tell the player rain is a danger. An animal that rain doesn't
# chill must never hear them (the "fish told to seek shelter" bug).
RAIN_DANGER = {"en": ["shelter", "warm"], "fi": ["suoja", "lämpi"]}
YEAR_WINTER = ["active", "hibernates", "migrates"]
FAMILY_ROLES = ["mother", "father", "sisters"]
LESSONS = ["eat", "pounce", "shelter", "sleep"]
MOVE = ["ground", "fly", "swim"]
SHELTER = ["earth", "leaves", "leaves_or_earth", "deep_water", "under_tree", "shore"]
ARCHETYPES = "archetypes"
MONTH_DAY = re.compile(r"^(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$")
MODEL_FILE = re.compile(r"^res://assets/animals/[a-z0-9_]+\.glb$")
PLACEHOLDER = re.compile(r"\{[a-z_]+\}")
CODE_KEY = re.compile(r"\"(ui\.[A-Za-z_.]*[A-Za-z_])\"")


class Stop(Exception):
    """The merged animal lacks a default the game reads directly (check_animals.gd stops there with a script error)."""


def need(a, d, key):
    if key not in d:
        raise Stop(f'{a}: its archetypes give no "{key}", so the rest of its checks can\'t run')
    return d[key]


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def gd(v):
    """A value as Godot prints it in a message: lists as ["a", "b"]."""
    if isinstance(v, list):
        return "[" + ", ".join(f'"{x}"' if isinstance(x, str) else gd(x) for x in v) + "]"
    if v is None:
        return "<null>"
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def read_json(path):
    """The parsed file, or None if it can't be read (like Godot's JSON.parse_string)."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def json_files(d):
    return sorted(f for f in os.listdir(d) if f.endswith(".json")) if os.path.isdir(d) else []


class Content:
    """The game's Species, Region and I18n, reading files from one checkout."""

    def __init__(self, root):
        self.root = root
        self.animals_dir = os.path.join(root, "animals")
        self.locale_dir = os.path.join(root, "locale")
        self._defs = {}
        self._archetypes = None
        self.sources = {}   # English text from animal and archetype files: key -> text

    # --- Species ---
    def exists(self, a):
        return isinstance(a, str) and a != "" and a != ARCHETYPES and os.path.isfile(os.path.join(self.animals_dir, a + ".json"))

    def list_ids(self):
        return [f[:-5] for f in json_files(self.animals_dir) if f[:-5] != ARCHETYPES]

    def archetype(self, name):
        if self._archetypes is None:
            parsed = read_json(os.path.join(self.animals_dir, ARCHETYPES + ".json"))
            self._archetypes = parsed if isinstance(parsed, dict) else {}
        v = self._archetypes.get(name, {}) if isinstance(name, str) else {}
        return v if isinstance(v, dict) else {}

    def get_def(self, a):
        """The animal with its archetype defaults filled in."""
        if a in self._defs:
            return self._defs[a]
        own = read_json(os.path.join(self.animals_dir, a + ".json"))
        if not isinstance(own, dict):
            own = {}
        chain = []
        name = own.get("archetype", "")
        while isinstance(name, str) and name != "" and name not in chain:
            chain.insert(0, name)
            name = self.archetype(name).get("extends", "")
        d, text_keys = {}, {}
        for n in chain:
            self._merge(d, self.archetype(n), "archetype." + n, text_keys)
        self._merge(d, own, "animal." + a, text_keys)
        d["id"] = a
        d.pop("extends", None)
        d["text_keys"] = text_keys
        self._defs[a] = d
        return d

    def _merge(self, into, src, prefix, text_keys):
        for k, v in src.items():
            if k == "text":
                for event, text in (v.items() if isinstance(v, dict) else []):
                    key = prefix + "." + event
                    text_keys[event] = key
                    self.sources[key] = text
            elif isinstance(v, dict) and isinstance(into.get(k), dict):
                into[k] = {**into[k], **v}
            else:
                into[k] = v

    def is_hunter_of(self, hunter, prey):
        tags = self.get_def(prey).get("tags", [])
        return any(t in tags for t in self.get_def(hunter).get("hunts", []))

    def can_hunt(self, a):
        return bool(self.get_def(a).get("hunts", []))

    # --- Region ---
    def region_ids(self):
        return [f[:-5] for f in json_files(os.path.join(self.root, "regions"))]

    def region(self, rid):
        data = read_json(os.path.join(self.root, "regions", rid + ".json"))
        return resolve(data) if isinstance(data, dict) else {}

    # --- I18n ---
    def languages(self):
        parsed = read_json(os.path.join(self.locale_dir, "languages.json"))
        return parsed if isinstance(parsed, dict) else {"en": "English"}


class Checker:
    def __init__(self, root, built_models=True):
        self.c = Content(root)
        self.root = root
        self.built_models = built_models
        self.errors = []
        self.warnings = []
        self._cache = {}

    def run(self, strict):
        ids = self.c.list_ids()
        for a in ids:
            self.check_animal(a, ids)
        self.check_regions()
        self.check_code_keys()
        self.check_translations(strict)
        return ids

    # --- one animal ---
    def check_animal(self, a, ids):
        try:
            self._check_animal(a, ids)
        except Stop as e:
            self.errors.append(str(e))

    def _check_animal(self, a, ids):
        err = self.errors.append
        raw = read_json(os.path.join(self.c.animals_dir, a + ".json"))
        if not isinstance(raw, dict):
            err(f"{a}: not valid JSON")
            return
        if raw.get("archetype", "") == "" or not self.c.archetype(raw.get("archetype")):
            err(f'{a}: unknown archetype "{gd(raw.get("archetype", ""))}"')
        d = self.c.get_def(a)
        keys = d["text_keys"]
        has = keys.__contains__
        if need(a, d, "playable"):
            for event in REQUIRED_PLAYABLE:
                if not has(event):
                    err(f'{a}: playable animals need text "{event}"')
            if not has("intro") and not all(has("intro_" + m) for m in MODES):
                err(f'{a}: needs text "intro" (or intro_safe, intro_survival and intro_wild)')
        dv = d.get("dark_vision")
        if not is_num(dv) or dv < 0.0 or dv > 1.0:
            err(f"{a}: dark_vision must be a number from 0 to 1")
        if need(a, d, "digs") and not has("dig"):
            err(f'{a}: digs, so it needs text "dig"')
        if self.c.can_hunt(a) and d["playable"] and not has("safe_tag"):
            err(f'{a}: hunts, so it needs text "safe_tag"')
        if need(a, d, "territorial") and not (has("rival_bite") and has("rival_caught_you")):
            err(f'{a}: territorial, so it needs "rival_bite" and "rival_caught_you"')
        for other in ids:
            if self.c.is_hunter_of(a, other) and not (has("bite") and has("caught_you")):
                err(f'{a}: hunts {other}, so it needs "bite" and "caught_you"')
                break
        # the rule that started this: rain only matters if it chills you
        rain_harmless = bool(need(a, d, "cold_blooded"))
        if not rain_harmless:
            rain_chill = need(a, d, "rain_chill")
            rain_harmless = is_num(rain_chill) and float(rain_chill) <= 0.0
        if rain_harmless and has("rain_start"):
            for lang, words in RAIN_DANGER.items():
                text = str(self.messages(lang).get(keys["rain_start"], "")).lower()
                for word in words:
                    if word in text:
                        err(f'{a}: rain doesn\'t chill it, but its {lang} rain message says "{word}": {text}')
        if "model" in d:
            model = d["model"] if isinstance(d["model"], dict) else {}
            file = str(model.get("file", ""))
            if not MODEL_FILE.search(file):
                err(f"{a}: model file must be res://assets/animals/<id>.glb: {gd(model.get('file', ''))}")
            elif self.built_models and not os.path.isfile(os.path.join(self.root, file[len("res://"):])):
                err(f"{a}: model file not found: {file}")
        self.check_year(a, raw.get("year"))
        if "family" in raw:
            self.check_family(a, raw["family"], d, has)
        for k, allowed in (("move", MOVE), ("shelter", SHELTER)):
            if need(a, d, k) not in allowed:
                err(f'{a}: "{k}" must be one of {gd(allowed)}')

    def check_year(self, a, y):
        """Every animal records how it lives through the seasons (CONTRIBUTING.md, "Its year")."""
        err = self.errors.append
        if not isinstance(y, dict):
            err(f'{a}: needs a "year" section: how it lives through the seasons (see CONTRIBUTING.md)')
            return
        if y.get("winter", "") not in YEAR_WINTER:
            err(f'{a}: "year.winter" must be one of {gd(YEAR_WINTER)}')
        for k, what in (("shelter", "where it sleeps and what it builds"), ("young", "when its young are born")):
            if not (isinstance(y.get(k), str) and y[k].strip() != ""):
                err(f'{a}: "year.{k}" must say {what}')
        food = y.get("food")
        for season in ["spring", "summer", "autumn", "winter"]:
            if not (isinstance(food, dict) and isinstance(food.get(season), str) and food[season].strip() != ""):
                err(f'{a}: "year.food.{season}" must say what it eats then')
        dates = {"hibernates": ("hibernation", ["from", "to"]), "migrates": ("migration", ["leaves", "returns"])}
        winter = y.get("winter", "")
        if isinstance(winter, str) and winter in dates:
            key, fields = dates[winter]
            part = y.get(key)
            for k in fields:
                if not (isinstance(part, dict) and MONTH_DAY.search(gd(part.get(k, "")))):
                    err(f'{a}: "year.{key}.{k}" must be a date like "09-15"')
            if key == "hibernation" and not (isinstance(part, dict) and part.get("wakes", "") in ["never", "rarely", "often"]):
                err(f'{a}: "year.hibernation.wakes" must be never, rarely or often')

    def check_family(self, a, fam, d, has):
        """A baby's family (decision 0010): who raises it, its lessons, and the text for growing up."""
        err = self.errors.append
        if not isinstance(fam, dict):
            err(f'{a}: "family" must be a section')
            return
        raised = fam.get("raised_by", [])
        if not isinstance(raised, list) or any(r not in FAMILY_ROLES for r in raised):
            err(f'{a}: "family.raised_by" must list some of {gd(FAMILY_ROLES)} (or nothing)')
            raised = []
        sib = fam.get("siblings", [0.0, 0.0])
        if not (isinstance(sib, list) and len(sib) == 2 and is_num(sib[0]) and is_num(sib[1]) and 0 <= sib[0] <= sib[1] <= 6):
            err(f'{a}: "family.siblings" must be [fewest, most], from 0 to 6')
            sib = [0, 0]
        sc = fam.get("baby_scale")
        if not (is_num(sc) and 0.2 <= sc <= 0.9):
            err(f'{a}: "family.baby_scale" must be a number from 0.2 to 0.9')
        lessons = fam.get("lessons", [])
        if not isinstance(lessons, list) or not lessons or any(x not in LESSONS for x in lessons):
            err(f'{a}: "family.lessons" must list some of {gd(LESSONS)}')
            lessons = []
        if "pounce" in lessons and not self.c.can_hunt(a):
            err(f'{a}: lesson "pounce" needs an animal that hunts')
        if ("shelter" in lessons or "sleep" in lessons) and not d["digs"]:
            err(f'{a}: lessons "shelter" and "sleep" happen in a dug den, so the animal must dig')
        if not (isinstance(fam.get("sources"), list) and fam["sources"]):
            err(f'{a}: "family.sources" must list where the family facts come from')
        need = ["family_you", "grown_up"]
        for r in raised:
            need += ["family_" + r, "calling_" + r, "fed_" + r]
        if sib[1] > 0:
            need.append("family_siblings")
        for x in lessons:
            need.append("lesson_" + x)
        for event in need:
            if not has(event):
                err(f'{a}: has a family, so it needs text "{event}"')

    # --- regions ---
    def check_regions(self):
        for rid in self.c.region_ids():
            animals = self.c.region(rid).get("animals", {})
            for a in animals.get("playable", []) if isinstance(animals, dict) else []:
                if not self.c.exists(a):
                    self.errors.append(f'region {rid}: playable animal "{a}" has no file animals/{a}.json')
            self.check_food_web(rid)

    def check_food_web(self, rid):
        """Food first (decision 0011): every animal in a region must find all its food there."""
        err = self.errors.append
        r = self.c.region(rid)
        lists = r.get("animals", {}) if isinstance(r.get("animals", {}), dict) else {}
        living = {}
        for key in ["playable", "predators", "prey"]:
            for a in lists.get(key, []):
                living[a] = True
        for f in r.get("fish", []):
            living[f.get("kind", "")] = True
        kinds = {}
        for f in r.get("food", []):
            kinds[f.get("kind", "")] = True
        gc = r.get("ground_cover", {}) if isinstance(r.get("ground_cover", {}), dict) else {}
        for p in gc.get("plants", []):   # food plants in the ground cover: porcini, bilberry bushes
            food = p.get("food")
            if isinstance(food, str):
                kinds[food] = True
            elif isinstance(food, dict):
                kinds[gd(food.get("kind", ""))] = True
        flowers = gc.get("flowers", 0.0)
        if is_num(flowers) and float(flowers) > 0.0 and gc.get("flower_colors", []):
            kinds["nectar"] = True
        for a in living:
            if not self.c.exists(a):
                continue
            d = self.c.get_def(a)
            diet = d.get("diet", [])
            hunts = d.get("hunts", [])
            if not diet and not hunts:
                err(f"{a} in {rid} eats nothing: give it a diet or hunts (food first, decision 0011)")
            for k in diet:
                if k not in kinds:
                    err(f'{a} in {rid} eats "{k}", but the region has no such food. Add it to the region\'s food first (decision 0011)')
            for tag in hunts:
                prey = [b for b in living if b != a and self.c.exists(b) and tag in self.c.get_def(b).get("tags", [])]
                if not prey:
                    err(f'{a} in {rid} hunts "{tag}", but no animal there has that tag. Add its prey to the region first (decision 0011)')

    # --- text ---
    def check_code_keys(self):
        """Every "ui.*" key written in the game's code must exist in English (only in a game checkout)."""
        scripts = os.path.join(self.root, "scripts")
        if not os.path.isdir(scripts):
            return
        known = set(self.messages("en")) | set(self.c.sources)
        for f in sorted(os.listdir(scripts)):
            if not f.endswith(".gd"):
                continue
            with open(os.path.join(scripts, f), encoding="utf-8") as fh:
                for key in CODE_KEY.findall(fh.read()):
                    if key not in known:
                        self.errors.append(f'scripts/{f} uses "{key}" but locale/en has no such key')

    def check_translations(self, strict):
        en = self.messages("en")
        for lang in self.c.languages():
            if lang == "en":
                continue
            tr = self.messages(lang)
            missing = 0
            for key in en:
                if key not in tr:
                    missing += 1
                    # an animal comes with English and Finnish text (CONTRIBUTING.md)
                    if strict or (lang == "fi" and key.startswith(("animal.", "archetype."))):
                        self.errors.append(f'{lang}: missing "{key}"')
                elif placeholders(en[key]) != placeholders(tr[key]):
                    self.errors.append(f'{lang}: "{key}" must use the placeholders {gd(placeholders(en[key]))}')
            for key in tr:
                # food and region names are translated from the English in region files,
                # map animals' names from map-animals.json (tools/map_animals.py checks them)
                if key not in en and not key.startswith(("food.", "flower.", "region.")) and not key.endswith(".map_name"):
                    self.errors.append(f'{lang}: "{key}" doesn\'t exist in English (typo, or removed?)')
            if missing > 0 and not strict:
                self.warnings.append(f"{lang}: {missing} of {len(en)} texts not translated yet (shown in English)")

    def messages(self, lang):
        """Every text in a language. English also has the text in all animal and archetype files."""
        if lang in self._cache:
            return self._cache[lang]
        out = {}
        d = os.path.join(self.c.locale_dir, lang)
        for f in json_files(d):
            parsed = read_json(os.path.join(d, f))
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    out.setdefault(k, v)   # like Godot's merge: the first file wins
            else:
                self.errors.append(f"locale/{lang}/{f}: not valid JSON")
        if lang == "en":
            archetypes = read_json(os.path.join(self.c.animals_dir, ARCHETYPES + ".json"))
            for name, a in (archetypes.items() if isinstance(archetypes, dict) else []):
                for event, text in (a.get("text", {}).items() if isinstance(a, dict) and isinstance(a.get("text"), dict) else []):
                    out[f"archetype.{name}.{event}"] = text
            for a in self.c.list_ids():
                for key in self.c.get_def(a)["text_keys"].values():
                    out[key] = self.c.sources.get(key, key)
        self._cache[lang] = out
        return out


def placeholders(s):
    return sorted(PLACEHOLDER.findall(s if isinstance(s, str) else str(s)))


def main():
    ap = argparse.ArgumentParser(description="Check every animal and every translation.")
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    ap.add_argument("--strict", action="store_true", help="translation gaps are errors")
    ap.add_argument("--no-built-models", action="store_true", help="don't look for the built .glb files")
    args = ap.parse_args()
    ch = Checker(os.path.abspath(args.root), built_models=not args.no_built_models)
    ids = ch.run(args.strict)
    for w in ch.warnings:
        print("warning:", w)
    for e in ch.errors:
        print("ERROR:", e, file=sys.stderr)
    print(f"{len(ids)} animals, {len(ch.c.languages())} languages: {len(ch.errors)} errors, {len(ch.warnings)} warnings")
    sys.exit(1 if ch.errors else 0)


if __name__ == "__main__":
    main()
