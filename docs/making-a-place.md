# Making a place

The steps for a new hand-made place (a start like the Great Barrier Reef), from the first survey to the game. Places are made one at a time, when we decide to make them: the place's own survey says what it needs, and nothing is prepared in advance.

The builder does the making on its own credits; a reviewer checks every step and commits the result here. Whenever a step below keeps catching the same problem, it should become a check in the builder or in `tools/`, and the step gets shorter. Write what each place taught us under [Lessons](#lessons).

## 1. Survey and plan

```
builder place survey "<place>" --budget <usd> --out <dir>
builder place plan <dir>
```

- Read `survey.json`: the tile is really at the place, `home_from` fits (a tropical sea is never the cold `sea` home), the name is child-friendly, and the animals are ones children know.
- Read `plan.json`. Fix only what its `blocked` list and gaps show, here in the world: a species missing from [`animal-list.json`](../animal-list.json), an animal with no reference that needs `"shape": "new"`, a home missing from `homes/examples/`. Then plan again until `blocked` is empty.
- `missing` in `survey.json` is the place's wanted list: what lives there that the world doesn't have yet. It isn't built now; it's what the place can grow into later (decision 0044).

## 2. Build and review the items

```
builder request build --local <dir>
builder take <job>
```

- Look at every preview sheet. Models are simple, never realistic: done when a child recognises the species.
- The builder writes English only. Add the Finnish at review: names, descriptions, everything a child reads (`locale/`).
- Each animal's food is in the place (food first, [decision 0011](decisions/0011-food-first.md)), and its moves fit its body: swimmers have swim settings, migrations are real.

## 3. The region file

The job writes a draft `region.json`. Review it into `regions/<country>_<place>.json`:

- Every lake and sea has its real name (no unnamed or "none" water). The sea home's water is the real sea's name.
- All text in English and Finnish.
- `python3 tools/validate_region.py regions/<id>.json`, `python3 tools/check_animals.py`, `python3 tools/check_schemas.py` and `python3 tools/check_models.py` pass.
- `python3 tools/places.py` adds the place to [`places.json`](../places.json).
- `python3 tools/catalogue.py` updates [catalogue.md](catalogue.md); take the place's animals and plants off [`wanted.json`](../wanted.json).

## 4. Around the place

- The wanted list is filed for the place's tiles (the builder files `missing` when the job ships), so the game's enrich step can find it: `admin.mjs enrich <region id>` lists what it found.
- The neighbouring tiles: plan the eight tiles around the place's tile. Each is named from this place (not from another one), and gets a home that fits or is blocked, never a wrong home.

## 5. In the game

- Export to the game and run its checks. Checks that assume only the Finnish places exist break when a new place appears; fix the check, not the place.
- Play the place before shipping: start each new animal, swim or walk to the edges, eat, look at the plants (one can hide another). Play on a phone-sized screen too.
- Ship it with the game's deploy, then play it once on animundo.app.

## Lessons

**Great Barrier Reef – Green Island** (`au_great_barrier_reef`, October 2026), the first place made this way:

- The turtle had no swim settings and a wrong migration: caught only by playing it.
- Pondweed hid the seagrass: look at the plants in the game, not only in the sheets.
- The draft region failed its schema, and fish needed wide `bands` marks.
- Game checks assumed only Nuuksio and Saimaa.
- The place had no wanted list, so it couldn't grow (now the survey's `missing`), and its neighbours were named from Saimaa and offered the cold Baltic sea home.
