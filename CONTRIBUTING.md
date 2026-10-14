# Add your favourite place to Animundo

> **About this repository.** This is Animundo's content repository; the game's code is kept separately. Commands below that use `godot` or `tools/build_web.sh` only work in the game repository for now. Until then, the core team runs the animal checks and plays your change for you. Automatic checks and a *Play it* link on every pull request are coming ([decision 0013](https://github.com/Kaimaan/animundo/blob/main/docs/decisions/0013-public-world-repo.md)).
>
> You need to be a verified player to open a pull request: see [README.md](README.md#how-to-add-something).

Animundo is built by its players' families. Each place in the world is one small **region file** in [`regions/`](regions/). You don't need to know game programming. An AI assistant (Claude, ChatGPT and so on) can write the file with you.

## The quick way: ask your AI assistant
Copy this prompt to your AI assistant and fill in the place:

> I want to add a region to the Animundo game (a low-poly animal survival game).
> Read `CONTRIBUTING.md` and `regions/fi_nuuksio.json` in the repository as the example.
> Create a new region file for **[PLACE, COUNTRY]**. Use real facts about this place:
> its landscape, typical trees, ground plants, colours of the ground, rock and water,
> the sky, and which animals live there. Then run `python3 tools/validate_region.py`
> and fix any problems.

Then test it, and open a pull request (see below).

## The region file
Name it `<country code>_<place>.json`, all lowercase, for example `ke_masai_mara.json` or `us_yellowstone.json`. The `id` inside must match the file name.

| Field | What it means |
|---|---|
| `id`, `name`, `country`, `description`, `author` | Who and what. `author` is your name or nickname. |
| `center.lat`, `center.lon` | Real coordinates of the middle of the area. |
| `terrain.size` (128–2048) | Width of the map in metres (1 block = 1 m). Nuuksio is 512. Only the land around the animal is built, so bigger maps don't load slower. |
| `terrain.base_height` (2–14) | How high the land is above the water. |
| `terrain.relief` (0–16) | How hilly it is. Use 0–4 for flat plains and 12–16 for steep hills. |
| `terrain.frequency` (0.005–0.15) | Size of hills: small numbers give wide, gentle hills. |
| `terrain.rock_ridges` (0–1) | How much bare rock shows on ridges. |
| `terrain.rock_above` (6–28) | Land higher than this is bare rock. |
| `terrain.lakes` (0–1) | How many lakes or ponds. |
| `terrain.edge` | `"lake"` puts water around the edge of the map. |
| `terrain.seed` (any whole number) | Fixes the shape of the land, so the region is the same place in every game and for friends playing together. Try a few numbers and keep the one that looks best. Leave it out to get new land each game. |
| `palette.*` | Colours (`"#rrggbb"`): `ground_lush`, `ground_dry`, `ground_high`, `dirt`, `rock`, `sand`, `water_deep`, `water_shallow`, and optional `ground_autumn` (faded grass) and `snow`. |
| `seasons` | Optional: when each season starts in your place, as month-day: `{"spring": "04-05", "summer": "05-25", "autumn": "09-20", "winter": "11-25", "snow": true}`. The game follows the real calendar, so it is autumn in the game when it is autumn there. Leave it out to use northern-Europe dates (flipped for the southern hemisphere; no seasons near the equator). `snow` says whether snow lies in winter. |
| `sky.*` | Colours of `day`, `horizon`, `dusk`, `night` and `sun`. |
| `trees.density` (0–0.05) | Trees per square metre. Nuuksio's dense forest is 0.02. |
| `trees.mix` | A list of `{shape, weight, leaves, trunk, autumn}`. Give `autumn` (a colour) to trees that drop their leaves: they turn that colour in autumn and stand bare in winter. Shapes: `spruce` (dark cone), `pine` (tall bare trunk, crown on top), `birch` (white trunk, small round crown), `round` (broadleaf tree). |
| `ground_cover.grass`, `flowers`, `stones` (0–1) | How much of the ground has grass tufts, flowers and loose stones. They must add up to 1 or less. |
| `ground_cover.flower_colors` | A list of flower colours. |
| `ground_cover.flower_names` | Optional: the real flower species, one per colour in the same order, e.g. `["harebell", "heather"]`. Bees are told which flower they drank from. |
| `lakes` | Optional named lakes, carved into the land: a list of `{name, x, z, length, width, angle, depth, islands, wreck}`. `x`, `z` (0–1) place the middle on the map, `length` and `width` (0–1) are parts of the map size, `angle` (degrees) turns it, `depth` (2–7) is in metres, `islands` is how many little islands, `wreck: true` sinks an old rowing boat in it. The player is told the lake's name when they reach it. |
| `lake_life.reeds`, `lilies`, `pondweed` (0–1) | How much of the shallows have reeds, of the water has lily pads, and of the deeper bottom has pondweed. |
| `places` | Optional places of interest named on the map: a list of `{name, x, z}` (`x`, `z` 0–1 on the map), or `{name, at: "highest"}` for the top of the highest hill (the hills change with every new world). Lakes and the boat wreck are named on the map by themselves. |
| `fish` | Fish in the lakes: a list of `{kind, count}`, using fish from `animals/` (e.g. `roach`, `bream`, `pike`, `perch`). `count` is about how many swim near the player. |
| `food` | A list of `{kind, weight, names}`. `names` (optional) are the real local species the player is told they ate, e.g. `["bilberries", "lingonberries"]`; one is picked per spawn. Kinds: `clover`, `carrot`, `berries`, `insects` (beetles on the ground), `water_bugs` (drift in lakes). |
| `animals` | `playable`, `predators` and `prey`, using the animals in [`animals/`](animals/) (`rabbit`, `fox`, `kestrel`, `perch`, `bee`, ...). |

If your place needs a tree shape, food or animal that doesn't exist yet, say so in your pull request. Adding new ones is a code change, and someone can help with it.

## Test it
```bash
python3 tools/validate_region.py regions/your_region.json
tools/build_web.sh && python3 tools/serve.py
```
Open `http://localhost:8060/?region=your_region&mode=safe`.

## Send it in (pull request)
1. Fork the repository on GitHub.
2. Add your region file and commit it.
3. Open a pull request. Include a screenshot and one line about why you love the place.

## Adding animals
Everything you make should follow the [art guide](ART.md), so the game looks like one world.

An animal is two data files: its **model** (`models/<id>.json`, what it looks like) and its **animal file** (`animals/<id>.json`, how it lives in the game). Most of the time, a new animal needs no code.

### Food first: the minimum requirement
**An animal can only be added if its main food is already in the region, or you add it in the same pull request** ([decision 0011](docs/decisions/0011-food-first.md)).

- Every food kind in its `diet` must be in the region's `food` list. For example, `berries` needs a `berries` entry in the region.
- Every tag in its `hunts` must belong to another animal in the region. A fox that `hunts` `["small_mammal"]` needs a vole or a hare there.
- If its food is missing, **make the food first.** A prey animal is a new animal: model, animal file and all. A plant or other food kind needs code, so ask the core team in your pull request. To add a predator, you build its prey.
- **Never fake it.** Don't give an animal a food it doesn't really eat just because that's what the game has. A kestrel doesn't eat berries.
- **Think about who eats it too.** Give it `tags` that the region's predators hunt (`small_mammal`, `small_bird`, `small_fish`...), so it joins the food web from both sides.

[docs/animals-wanted.md](docs/animals-wanted.md) lists the animals and foods the game needs now, most wanted first. That's a good place to start. `tools/check_animals.gd` fails if any animal in a region can't find its food.

### Start to finish
The red squirrel was added this way. Its files are a good example.

0. **Food.** List what it really eats in each season. Check every main food is in the region (see [Food first](#food-first-the-minimum-requirement)). If one isn't, add that first, or pick an animal from [docs/animals-wanted.md](docs/animals-wanted.md) instead.
1. **Model.** Write `models/<id>.json` and build it with Blender. See [models/README.md](models/README.md).
   ```bash
   tools/build_model.sh models/<id>.json
   ```
2. **Look at the preview** (`models/previews/<id>.png`). Fix the spec and build again until nothing floats, nothing has gaps, and the animal looks right in every pose and coat.
3. **Animal file.** Copy [`animals/squirrel.json`](animals/squirrel.json) to `animals/<id>.json`. Set its traits, its English `text`, and the `model` entry: the `length` the build printed, and seasonal `coats` if the animal changes colour. Fill in its **`year`**: how it lives through the seasons (see [Its year](#its-year) below).
4. **Translations.** Add `animal.<id>.<message>` to `locale/fi/animals.json` and every other language you can.
5. **Place it.** Add the animal to a region's `animals.playable` list.
6. **Check it.**
   ```bash
   godot --headless --import
   godot --headless --script tools/check_models.gd
   godot --headless --script tools/check_animals.gd
   ```
7. **Play it.** Run `tools/build_web.sh && python3 tools/serve.py` and open `http://localhost:8060/?region=<region>&mode=safe&animal=<id>`. Add `&date=2027-01-20` to see the winter coat.
8. **Pull request.** Include the preview sheet, a screenshot from the game, and where you checked the animal's size and colours. Reviewers use the checklist in [ART.md](ART.md#7-checklist-for-review).

An AI assistant can do steps 1–7 by itself. Give it this prompt:

> Add a **[ANIMAL]** to the Animundo game. Read `ART.md`, `CONTRIBUTING.md` (Adding animals) and `models/README.md`, and use the red squirrel's files as the example.
> Use real facts: size, proportions, colours (and winter colours if it changes), speed and diet.
> Food first: check that everything it really eats is already in the region (its `diet` food kinds and the animals it `hunts`). If its main food is missing, stop and tell me which animal or food to add first; never give it a food it doesn't really eat.
> Fill in its `year` from real facts for this region: what it does in winter (active, hibernates or migrates, with dates), where it sleeps and what it builds, when its young are born, and what it eats in each season. Write down everything it really does, even what the game can't show yet.
> Build the model, look at the preview sheet and fix it until it looks right. Then write the animal file with English and Finnish text,
> add it to `regions/fi_nuuksio.json`, run all the checks, and play it in the browser to check it in summer and winter.

A person always reviews the preview sheet and the screenshot before merging.

### The animal file

- `archetype`: the kind of animal it is, from [`animals/archetypes.json`](animals/archetypes.json): `land_mammal`, `bird` or `fish`. The archetype supplies the defaults: how it moves, where it shelters, how weather affects it, and general messages. Your file only lists what's different.
- `tags` and `hunts`: who eats whom (see [Food first](#food-first-the-minimum-requirement)). **Catching is eating:** a hunter eats its prey the moment it catches it, with one tap of the big button (a fox's Pounce). There's never a second "now eat it" step. The same goes for your animal: when a hunter catches it, it's eaten and that life ends (its `caught_you` text, like "A fox ate you."). A playable hunter also gets a `play_as` text ("Play as a fox"), shown as a button on that screen. Make catching harder or easier by tuning the chase (speed, reach, how fast the prey tires), not by adding buttons. A fox `hunts` `["small_mammal", "small_bird"]`, and a rabbit has the tag `small_mammal`. If you add a vole tagged `small_mammal`, foxes hunt it automatically. `territorial: true` means others of its kind chase you off their land.
- Traits: `diet` (food kinds), `cold_blooded`, `rain_chill` (how much rain cools it; 0 = rain doesn't matter), `digs` (it can dig burrows and tunnels), `dark_vision` (how well it sees in dim light, 0 to 1: a squirrel 0.2, a rabbit 0.6, a fox 0.85; this sets how dark night and burrows look when you play it), and movement numbers (`walk`, `sprint`, `jump`, `box`, camera).
- `model`: the `.glb` file in `assets/animals/`, its `length` in metres, its animation clips, and optional seasonal `coats`. New models are built with Blender from a model spec, a small data file in [`models/`](models/README.md).
- `year`: how it lives through the seasons. Required for every animal; see [Its year](#its-year).
- `family`: optional. Who raises its young, so players can start life as a baby; see [Its family](#its-family).
- `text`: what the game tells the player, in English. An animal only gets a message it (or its archetype) has. For example, fish have their own rain message instead of being told to find shelter. Write whole sentences, never pieces to glue together, so other languages can translate them.
- `latin`: the scientific name, e.g. `"Vulpes vulpes"`. It's shown in the field guide and isn't translated.
- Field guide: in `text`, one or two short sentences a child can read for each of `about_looks` (what it looks like), `about_food` (what it eats), `about_home` (where it lives and sleeps), `about_winter`, `about_young` and `about_fact` (something surprising). Use real facts. Players open it from the title screen's Field guide (every animal, playable or not), the in-game menu and when choosing a mode. An animal without them simply has no field guide button.

### Its year

The game follows the real calendar ([decision 0006](docs/decisions/0006-real-world-seasons.md)), so every animal records how it really lives through the year. Write down everything it does, **even what the game can't show yet**. This is the list of things to build next: a bear's den or a squirrel's hidden seeds start here.

```json
"year": {
  "winter": "hibernates",
  "hibernation": {"from": "09-15", "to": "04-10", "wakes": "never"},
  "shelter": "In autumn each new queen digs a small chamber in soil to sleep in.",
  "young": "The queen raises workers from May; new queens hatch in late summer.",
  "food": {"spring": "Willow catkins.", "summer": "Nectar and pollen.", "autumn": "Heather.", "winter": "Asleep, living on stored fat."},
  "notes": "The workers all die in autumn."
}
```

- `winter`: `active`, `hibernates` or `migrates`.
  - `hibernates` needs `hibernation`: `from` and `to` dates (month-day) and how often it `wakes` (`never`, `rarely` or `often`). For example, a hedgehog wakes every week or two, but a bumblebee queen never does.
  - `migrates` needs `migration`: the dates it `leaves` and `returns`.
- `shelter`: where it sleeps and what it builds or digs (burrow, den, drey, nest), and when it builds it.
- `young`: when its young are born or hatch, and where.
- `food`: what it really eats in `spring`, `summer`, `autumn` and `winter`, using local species names.
- `notes`: optional. Anything else the game should show one day: a winter coat, food caches, a hunting trick.

Use dates for the animal's region (the first region it's added to). The texts are notes for the team, written in English, and are not shown to players.

### Its family

With a `family` section, players can start this animal as a baby: its real family meets it, feeds it and shows it how to survive, and it grows up when it has learned ([decision 0010](docs/decisions/0010-baby-start-with-family.md)). Without one, the animal starts grown up. Use the real family: a fox has a mother and a father, a squirrel only a mother, and fish have no parents at all.

```json
"family": {
  "raised_by": ["mother", "father"],
  "siblings": [2, 3],
  "baby_scale": 0.5,
  "lessons": ["eat", "pounce", "shelter", "sleep"],
  "sources": ["https://en.wikipedia.org/wiki/Red_fox#Reproduction_and_development"]
}
```

- `raised_by`: any of `mother`, `father` and `sisters` (bumblebee workers raise their sisters).
- `siblings`: the fewest and most brothers and sisters the game adds, from 0 to 6.
- `baby_scale`: the baby's size compared with a grown-up, from 0.2 to 0.9.
- `lessons`: what the family teaches, in order: `eat`, `pounce` (only animals that hunt), `shelter` and `sleep` (both in a dug den, so only animals that dig).
- `sources`: where the family facts come from.
- `text` then needs: `family_you` and `grown_up`; for each one in `raised_by`, `family_<who>`, `calling_<who>` and `fed_<who>`; `family_siblings` when it has siblings; and `lesson_<name>` for each lesson. See [`animals/fox.json`](animals/fox.json).

The checker `tools/check_animals.gd` lists every missing message and every message that breaks the rules that keep messages sensible:
```bash
godot --headless --script tools/check_animals.gd
```

## Translating
All text the player sees is in [`locale/`](locale/), one folder per language with flat `{"key": "text"}` files:
- `ui.json`: menus, buttons and general messages. The English originals are in `locale/en/ui.json`.
- `animals.json`: animal messages. The English originals are the `text` in each animal file. Keys are `animal.<id>.<message>` and `archetype.<name>.<message>`.
- `food.json`: food names, keyed by the English name in the region file, e.g. `"food.bilberries": "mustikat"`.
- `regions.json`: place names, e.g. `"region.fi_nuuksio.name": "Nuuksion kansallispuisto"`.

Keep `{placeholders}` such as `{day}` exactly as they are; you can move them anywhere in the sentence. Anything not yet translated shows in English. To add a language, create `locale/<code>/` (two-letter ISO code) and add it to [`locale/languages.json`](locale/languages.json) under its own name (`"fi": "Suomi"`). The checker above reports what's still missing; add `--strict` to treat gaps as errors.
