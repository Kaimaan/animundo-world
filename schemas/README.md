# Content schemas

Each content format has a JSON Schema here (draft 2020-12). The schemas describe what the game already accepts. Every list of allowed values and every number range comes from the game's code or from a checker, never from guesswork. They are for people and for AI agents that write content: check a file against its schema before anything else.

| Schema | Describes | Built from |
|---|---|---|
| `region.schema.json` | `regions/<id>.json`, and `biomes/<id>.json` and `homes/<id>.json` as places without a spot (their four home fields allowed, no country, the id their own name) | the region files, CONTRIBUTING.md, `tools/validate_region.py` |
| `animal.schema.json` | `animals/<id>.json` | the animal files, `check_animals.gd`, the game's scripts |
| `archetypes.schema.json` | `animals/archetypes.json` | the archetypes file, `species.gd` |
| `model.schema.json` | `models/<id>.json` (`$defs/animal_model`) and `models/plants/<id>.json` (`$defs/plant_model`) | the specs, `tools/blender/build_model.py`, `build_plant.py`, `check_models.gd`, ART.md |
| `locale.schema.json` | `locale/<lang>/<file>.json` (one definition per file name in `$defs`) and `locale/languages.json` | the locale files |
| `wanted.schema.json` | `wanted.json` | the file, `tools/catalogue.py` |

## Running the checks

```bash
pip install jsonschema
python3 tools/check_schemas.py              # every content file against its schema
python3 tools/check_animals.py              # animals, food web and translations (port of check_animals.gd)
python3 tools/check_models.py               # built models (port of check_models.gd)
python3 tools/check_taxa.py                 # one real species, one file (by GBIF taxon ID)
python3 tools/check_draft.py DRAFT_DIR      # a draft of new content, every check at once, as JSON
python3 tools/taxon.py --verify             # every taxon against GBIF itself (needs the network)
python3 tools/test_broken.py                # broken content must fail the right checks
```

Only `check_schemas.py` needs `jsonschema`. The other checks use plain Python. `check_models.py`, `validate_region.py` and the model file rule in `check_animals.py` need the models built first (`tools/build_model.sh models/*.json models/plants/*.json`). Before that, run `check_animals.py --no-built-models`.

CI (`.github/workflows/check.yml`) runs all of them on every pull request, after building the models.

## What checks what

A JSON Schema can only look at one file. So the work is split:

- **The schemas** check the shape of one file: its keys, types, lists of allowed values and number ranges. Names players read (a place's, its lakes', bogs' and landmarks') are never a placeholder such as "none" or "unknown": a lake, bog or place without a real name is left out (`$defs/name`; Kai, 2026-10-30, after the builder named the Helsinki shore's sea "none" and the game showed it).
- **`check_schemas.py`** also checks the rules inside one file that a schema can't express: the id equals the file name, a model part's colour and bone exist, mirrored names end in `_l`, an archetype extends another one in the same file, and the ART.md budgets that depend on the animal file (at most 16 bones; a model of an animal that isn't playable has at most 800 triangles).
- **`validate_region.py`** checks a region against other files: its animals and plants exist and are built, the ground cover densities add up to 1 or less, and the plant triangle budget.
- **`check_taxa.py`** checks that every animal file and plant spec says which real species it is (`taxon`, the GBIF ID of its accepted name, written by `tools/taxon.py`), that `latin` is that name, and that no two files are the same species unless one is a `stage_of` the other. It is new, not a port of a game checker, so the game's `.gd` checkers don't know these rules.
- **`check_animals.py`** and **`check_models.py`** give the same verdict as the game's `check_animals.gd` and `check_models.gd`, with the same messages. They check what needs several files or an animal merged with its archetypes: the texts a playable animal needs, food first (decision 0011), the rain message rule, family texts, translations and built models.

## Decisions

- **Keys that only some archetypes use are optional everywhere.** `glide_*`, `swim_*`, `school`, `songbird`, `nest`, `climb` and the others are not tied to an archetype with `if`/`then`. The game reads each of them on any animal, whatever its archetype: a seal is a `land_mammal` with `swim_speed`, a flying squirrel is a `land_mammal` that glides, a mallard is a `bird` that swims. Tying keys to archetypes would reject animals the game plays correctly. The checks that really depend on the archetype (rain, digging, hunting texts) need the merged defaults, so they are in `check_animals.py`.
- **Required animal keys** are the ones every animal file has today: `archetype`, `latin`, `tags`, `model`, `year`, `text`. All traits are optional because the archetype gives defaults.
- **Animal keys** are the 45 keys used in the animal files today, plus `move` and `cold_blooded`. Those two are usually set by the archetype, but an animal may set them: `check_animals.gd` checks `move`, and CONTRIBUTING.md lists `cold_blooded` as a trait.
- **Animal text keys** are the 51 used in the animal files today, plus `rain_stop`. `check_animals.gd` requires `rain_stop` from every playable animal, so an animal may need to give its own. Each text's `maxLength` is the longest text with that key today (in the animal files and the archetypes), plus about 30%, rounded up to ten and at least 80.
- **Food kinds.** An animal's `diet` uses the `food.kind.*` keys in `locale/en/food.json`, plus `nectar`, which a region gives with its flowers. A region's `food` list uses `FOOD_KINDS` from `validate_region.py`. It is shorter because mushrooms come from ground-cover plants and nests from birds. A plant in the ground cover uses `PLANT_FOOD_KINDS`. A tree's `food` uses the food kinds.
- **`status`** (`draft`, `reviewed` or `released`; decision 0009) is optional on regions, animals and model specs. Missing means released, so every existing file stays valid. A region whose status is `draft` or `reviewed` (an explored place) needs at least 3 sources.
- **A plant's `top`** can be above 1 (up to 10, to catch typos): the chanterelle's cap is a taper that widens upwards. ART.md's 0 to 1 is kept for animal specs.
- **Skin triangles** are from 400 to 1,500, the range of the ART.md budgets for animals.
- **The broken cases are edits, not copies.** `tests/broken/cases.json` lists 56 ways to break the content, one rule each. Each edits a real file as it is today (JSON Pointer paths) or removes one, and says which checks must fail. Every other check must pass. Copies of whole files would go stale as the content changes, and a stale copy can break for the wrong reason. `python3 tools/test_broken.py --write DIR` saves each broken copy if you want to look at them.

## Keeping the Python checkers the same as the game's

The game's `tools/check_animals.gd` and `tools/check_models.gd` are the reference. When one of them changes, change its Python port in the same way, then compare them on every case:

```bash
cp -R <game checkout> /tmp/game && rm -rf /tmp/game/.git
tools/export_to_game.sh /tmp/game
godot --headless --import --path /tmp/game
python3 tools/test_broken.py --game /tmp/game
```

`--game` runs both checkers on the unchanged content and on every broken case, and lists every error line that only one of them gives. It edits files in that copy of the game and puts them back, so never point it at a checkout you work in.

Known differences:

- Where an animal's archetypes give no default for a key the game reads directly (`playable`, `digs`, `territorial`, `cold_blooded`, `rain_chill`, `move`, `shelter`), `check_animals.gd` stops checking that animal with a script error. `check_animals.py` stops there too, but says so as an error: `<id>: its archetypes give no "<key>", so the rest of its checks can't run`.
- `check_animals.gd` also checks that every `"ui.*"` key in the game's scripts exists in English. `check_animals.py` does this only when `--root` is a game checkout (one with `scripts/`).
- `check_models.gd` lists an animal's clips in Godot's order in "animation is missing (has ...)". `check_models.py` lists them sorted.
