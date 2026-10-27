# Add your favourite place to Animundo

> **About this repository.** This is where Animundo's content lives; the game's code is kept separately, and every change merged here is copied into the game automatically. Commands below that use `godot` or `tools/build_web.sh` need the game repository: to try a change there before sending it, run `tools/export_to_game.sh <path to the game>`. Otherwise the core team runs the animal checks and plays your change for you. A *Play it* link on every pull request is coming. Menu text (`locale/*/ui.json`, `loading.json`, `seasons.json`) belongs to the game and can't be changed here.
>
> You need to be a verified contributor to open a pull request. A grown-up with a (free) account in the game gets a code under *For parents and teachers*: see [README.md](README.md#how-to-add-something).

Animundo is built by its players' families. Each place in the world is one small **region file** in [`regions/`](regions/). You don't need to know game programming. An AI assistant (Claude, ChatGPT and so on) can write the file with you.

## The quick way: ask your AI assistant
Copy this prompt to your AI assistant and fill in the place:

> I want to add a region to the Animundo game (a low-poly animal survival game).
> Read `CONTRIBUTING.md` and `regions/fi_nuuksio.json` in the repository as the example.
> Create a new region file for **[PLACE, COUNTRY]**. Use real facts about this place:
> its landscape, typical trees, ground plants, colours of the ground, rock and water,
> the sky, and which animals live there. Put the links or books you used in `sources`.
> Then run `python3 tools/validate_region.py` and fix any problems.

Then test it, and open a pull request (see below).

**What's missing?** [docs/catalogue.md](docs/catalogue.md) shows the animals, plants, trees and foods the game has and what it still needs, most wanted first. Pick a row and claim it by setting its `status` to `in_progress` in [`wanted.json`](wanted.json). After adding anything, run `python3 tools/catalogue.py` to update the page.

## The region file
Name it `<country code>_<place>.json`, all lowercase, for example `ke_masai_mara.json` or `us_yellowstone.json`. The `id` inside must match the file name.

| Field | What it means |
|---|---|
| `id`, `name`, `country`, `description`, `author` | Who and what. `author` is your nickname, never a child's full name. |
| `sources` | Where your facts come from: a list of links or book titles. |
| `center.lat`, `center.lon` | Real coordinates of the middle of the area. |
| `terrain.size` (128–2048) | Width of the map in metres (1 block = 1 m). Nuuksio is 512. Only the land around the animal is built, so bigger maps don't load slower. |
| `terrain.height` (32–64) and `terrain.water_level` | The land's height in blocks and the water's level: 32 and 8 for most places. For high mountains or deep sea (fjords, orcas), use up to 64 with the water higher, e.g. 64 and 24; the limits below then grow with it (base height and relief by the extra height, `rock_above` and `ice.glacier_above` up to height − 4, lake depth up to the water level − 1). |
| `terrain.base_height` (2–14) | How high the land is above the water. |
| `terrain.relief` (0–16) | How hilly it is. Use 0–4 for flat plains and 12–16 for steep hills. |
| `terrain.frequency` (0.005–0.15) | Size of hills: small numbers give wide, gentle hills. |
| `terrain.rock_ridges` (0–1) | How much bare rock shows on ridges. |
| `terrain.rock_above` (6–28) | Land higher than this is bare rock. |
| `terrain.lakes` (0–1) | How many lakes or ponds. |
| `terrain.edge` | `"lake"` puts water around the edge of the map. |
| `terrain.seabed` | `"sand"` for a sandy bottom under deep water (warm seas, coral reefs); the default is mud. |
| `terrain.seed` (any whole number) | Fixes the shape of the land, so the region is the same place in every game and for friends playing together. Try a few numbers and keep the one that looks best. Leave it out to get new land each game. |
| `palette.*` | Colours (`"#rrggbb"`): `ground_lush`, `ground_dry`, `ground_high`, `dirt`, `rock`, `sand`, `water_deep`, `water_shallow`, and optional `ice`, `ground_autumn` (faded grass), `heath_autumn` (berry shrubs on the forest floor in autumn colours, like Finnish *maaruska*) and `snow`. |
| `seasons` | Optional: when each season starts in your place, as month-day: `{"spring": "04-05", "summer": "05-25", "autumn": "09-20", "winter": "11-25", "snow": true}`. The game follows the real calendar, so it is autumn in the game when it is autumn there. The sun's height and the length of the day are worked out from `center.lat`. Leave it out to use northern-Europe dates (flipped for the southern hemisphere; no seasons near the equator). `snow` says whether snow lies in winter. |
| `sky.*` | Colours of `day`, `horizon`, `dusk`, `night` and `sun`. |
| `trees.density` (0–0.05) | Trees per square metre. Nuuksio's dense forest is 0.02. |
| `trees.mix` | A list of `{shape, weight, leaves, trunk, autumn, plant, food}`. `plant` names the tree's field guide page (its text is `plant.<plant>.*` in `locale/<lang>/plants.json`), and `food` is what it is to animals here (`browse` for leaves and twigs, `cones`), so its page shows who eats it. Give `autumn` (a colour) to trees that drop their leaves: they turn that colour in autumn and stand bare in winter. Shapes: `spruce` (dark cone), `pine` (tall bare trunk, crown on top), `birch` (white trunk, small round crown), `round` (broadleaf tree, e.g. aspen), `rowan` (small tree; red berry clusters from August into winter), or the id of a **tree spec** in [`models/trees/`](models/README.md#trees) (palms, acacias, cypresses, baobabs, mangroves and more; its colours come from the spec, and `plant` is the spec itself). Leaf colours vary from tree to tree, so in autumn some birches are still green while others are gold or already bare. |
| `ground_cover.grass`, `flowers`, `stones` (0–1) | How much of the ground has grass tufts, flowers and loose stones. Together with the plants below, they must add up to 1 or less. |
| `ground_cover.plants` | Optional plants built from specs in [`models/plants/`](models/README.md#plants): a list of `{model, density, near_trees, on}`. `density` (0–1) is how much of the open ground has it. `near_trees` (blocks, optional) keeps it within that distance of a trunk, for forest plants like bilberry. `on` (optional) is the ground it grows on: any of `grass` (the default), `rock`, `sand` and `seabed` (under water: corals, sea grass), e.g. `["grass", "rock"]` for heather on rocky hilltops. Each plant changes through the year by itself, following this region's `seasons`. A plant can also be **food**: `"food": "mushrooms"` makes the whole plant food (a porcini), and `"food": {"kind": "berries", "part": "berry"}` makes one part of it food (a bilberry bush's berries), only while that part shows; `"names"` are what the player is told they ate (e.g. `["bilberries"]`) and `"amount"` how filling it is (default 20). Eaten plants grow back after a few minutes. Food kinds: `berries`, `mushrooms`, `clover`, `browse`. |
| `ground_cover.flower_colors` | A list of flower colours. |
| `ground_cover.flower_names` | Optional: the real flower species, one per colour in the same order, e.g. `["harebell", "heather"]`. Bees are told which flower they drank from. |
| `lakes` | Optional named lakes, carved into the land: a list of `{name, x, z, length, width, angle, depth, islands, wreck}`. `x`, `z` (0–1) place the middle on the map, `length` and `width` (0–1) are parts of the map size, `angle` (degrees) turns it, `depth` (2–7) is in metres, `islands` is how many islands (0–24); optional `island_radius: [minimum, maximum]` sets their radius in metres (2–80, default 3.5–6). Lake length and width may reach 1.5 for water extending beyond a habitat sample. `wreck: true` sinks an old rowing boat in it. The player is told the lake's name when they reach it. |
| `lake_life.reeds`, `lilies`, `pondweed` (0–1) | How much of the shallows have reeds, of the water has lily pads, and of the deeper bottom has pondweed. |
| `places` | Optional places of interest named on the map: a list of `{name, x, z}` (`x`, `z` 0–1 on the map), or `{name, at: "highest"}` for the top of the highest hill (the hills change with every new world). Lakes and the boat wreck are named on the map by themselves. |
| `migrants` | Optional: birds that fly over on migration, as a V-shaped flock in the sky, with a message the first time. A list of `{kind, names, south, north}`: `kind` is `geese` or `cranes`, `names` the real species, and `south` and `north` the dates they pass over going each way, e.g. `"south": ["09-20", "10-25"]`. |
| `fish` | Fish in the lakes: a list of `{kind, count}`, using fish from `animals/` (e.g. `roach`, `bream`, `pike`, `perch`). `count` is about how many swim near the player. |
| `food` | A list of `{kind, weight, names}`. `names` (optional) are the real local species the player is told they ate, e.g. `["bilberries", "lingonberries"]`; one is picked per spawn. Kinds: `clover`, `carrot`, `berries`, `insects` (beetles on the ground), `water_bugs` (drift in lakes), `seeds` (fallen spruce, pine and birch seeds on the ground), `browse`, `water_plants`, `cones`, `bottom_bugs`, `carrion` (remains of a large animal, found only in winter). Two kinds are part of the land instead of being put down: `grass` is grazed from the grass tufts (not under snow), and `bark` is gnawed from the trunks of trees that drop their leaves (those with an `autumn` colour) while snow lies; their entries need no `weight`, and `amount` sets how filling one mouthful is. Name the bark after the tree, like `"birch bark"`, so the player is told which tree they gnawed. |
| `ice` | Optional, for arctic and mountain places: `glacier_above` (6–28: land this high is a glacier), `icebergs: {amount, height}` (`amount` 0–0.3 of the deep water, `height` 1–8 m above it), and `frozen_water: {from, until, cover}`: the water freezes between two dates (`"12-01"` or a season mark like `"winter+10"`), `cover` (0–0.9) of it, so swimmers always find open water. Its colour is `palette.ice`. Leave it out for no ice. |
| `caves` | Optional caves under the hills: `amount` (0–0.3) of the rock is tunnels and chambers, dark inside like a burrow, and with `entrances` (default true) they open sideways where a slope drops away. They are never beside water, so nothing floods, and nothing grows inside. Leave it out for no caves. |
| `animals` | `playable`, `predators` and `prey`, using the animals in [`animals/`](animals/) (`mountain_hare`, `fox`, `kestrel`, `perch`, `bee`, ...). |

If your place needs a tree shape, food or animal that doesn't exist yet, say so in your pull request. Adding new ones is a code change, and someone can help with it.

## Test it
```bash
python3 tools/validate_region.py regions/your_region.json
```
Playing it needs the game repository, so the core team plays your place for you until *Play it* links on pull requests are ready. With the game repository, run `tools/export_to_game.sh <path to the game>`, then there `tools/build_web.sh && python3 tools/serve.py`, and open `http://localhost:8060/?region=your_region&mode=safe`.

## Send it in (pull request)
1. Fork the repository on GitHub.
2. Add your region file and commit it with a sign-off: `git commit -s` (it adds `Signed-off-by: your name`). That says you agree to the [Developer Certificate of Origin](https://developercertificate.org) and that your work is shared under [CC BY 4.0](LICENSE).
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

[docs/catalogue.md](docs/catalogue.md) lists what the game has and the animals, plants and foods it needs now, most wanted first. That's a good place to start. `tools/check_animals.gd` fails if any animal in a region can't find its food.

### Start to finish
The red squirrel was added this way. Its files are a good example.

0. **Food.** List what it really eats in each season. Check every main food is in the region (see [Food first](#food-first-the-minimum-requirement)). If one isn't, add that first, or pick an animal from [docs/catalogue.md](docs/catalogue.md) instead.
1. **Model.** Write `models/<id>.json` and build it with Blender. See [models/README.md](models/README.md).
   ```bash
   tools/build_model.sh models/<id>.json
   ```
2. **Look at the preview** (`models/previews/<id>.png`). Fix the spec and build again until nothing floats, nothing has gaps, and the animal looks right in every pose and coat.
3. **Animal file.** Copy [`animals/squirrel.json`](animals/squirrel.json) to `animals/<id>.json`. Set its traits, its English `text`, and the `model` entry: the `length` the build printed, and seasonal `coats` if the animal changes colour. Fill in its **`year`**: how it lives through the seasons (see [Its year](#its-year) below).
4. **Translations.** Add `animal.<id>.<message>` to `locale/fi/animals.json` and every other language you can.
5. **Place it.** Add the animal to a region's `animals.playable` list.
6. **Check it.** These run without the game ([schemas/README.md](schemas/README.md)); `check_models.py` needs the models built.
   ```bash
   python3 tools/check_schemas.py
   python3 tools/check_animals.py
   python3 tools/check_models.py
   ```
   With the game repository you can also run its own checks: `godot --headless --import`, then `godot --headless --script tools/check_models.gd` and `tools/check_animals.gd`.
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
- `tags` and `hunts`: who eats whom (see [Food first](#food-first-the-minimum-requirement)). **Catching is eating:** a hunter eats its prey the moment it catches it, with one tap of the big button (a fox's Pounce). There's never a second "now eat it" step. The same goes for your animal: when a hunter catches it, it's eaten and that life ends (its `caught_you` text, like "A fox ate you."). A playable hunter also gets a `play_as` text ("Play as a fox"), shown as a button on that screen. Make catching harder or easier by tuning the chase (speed, reach, how fast the prey tires), not by adding buttons. A fox `hunts` `["small_mammal", "small_bird"]`, and a mountain hare has the tag `small_mammal`. If you add a vole tagged `small_mammal`, foxes hunt it automatically. `territorial: true` means others of its kind chase you off their land.
- Traits: `diet` (food kinds), `cold_blooded`, `rain_chill` (how much rain cools it; 0 = rain doesn't matter), `digs` (it can dig burrows and tunnels), `dark_vision` (how well it sees in dim light, 0 to 1: a squirrel 0.2, a mountain hare 0.7, a fox 0.85; this sets how dark night and burrows look when you play it), `breath` (seconds it can stay under water before it must come up for air: 15 for most land animals, a moose 40, a frog 600; fish don't need it), and movement numbers (`walk`, `sprint`, `jump`, `box`, camera).
- `model`: the `.glb` file in `assets/animals/`, its `length` in metres, its animation clips, and optional seasonal `coats`. New models are built with Blender from a model spec, a small data file in [`models/`](models/README.md).
- `year`: how it lives through the seasons. Required for every animal; see [Its year](#its-year).
- `family`: optional. Who raises its young, so players can start life as a baby; see [Its family](#its-family).
- `text`: what the game tells the player, in English. An animal only gets a message it (or its archetype) has. For example, fish have their own rain message instead of being told to find shelter. Write whole sentences, never pieces to glue together, so other languages can translate them.
- `latin`: the scientific name, e.g. `"Vulpes vulpes"`. It's shown in the field guide and isn't translated.
- `taxon`: which real species it is, from GBIF: run `python3 tools/taxon.py "Vulpes vulpes"` and paste what it prints, or run `python3 tools/taxon.py --fill` to add it to every file without one. **One real species, one file:** first run `python3 tools/taxon.py --same "<latin name>"`. If a file already is that species (perhaps under another name: `red_fox` is `fox`), improve it instead. A young animal shown as its own file (`young_perch`) has `"stage_of": "perch"`. `tools/check_taxa.py` checks all this.
- `sources`: where its facts come from (size, colours, food, year), as a list of links or book titles.
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

The checker `tools/check_animals.py` (a copy of the game's `check_animals.gd` that runs without the game) lists every missing message and every message that breaks the rules that keep messages sensible:
```bash
python3 tools/check_animals.py
```

## Adding plants
A plant is one data file, `models/plants/<id>.json`: its looks and its year. Blender builds it into the model the game uses, plus a preview sheet ([models/README.md](models/README.md#plants)). The game scatters it on the ground of the places that list it, and it changes through the year by itself. A plant needs no code.

Plants can be bushes, dwarf shrubs, ferns, flowers, grasses, mosses or mushrooms. **Trees aren't plant specs yet:** they are still built in code, because animals climb them and hide in them. Ask before starting a tree.

### The rules
Every plant must follow these rules. The checks run on every pull request and stop it if a rule they can test is broken. A reviewer checks the rest.

| # | Rule | Checked by |
|---|---|---|
| 1 | **A real wild species.** Give its scientific name in `latin`. No garden varieties, and no made-up or "generic" plants. | Reviewer |
| 2 | **One species, one file.** Before you start, run `python3 tools/taxon.py --plant --same "<latin name>"`: if a spec already is that species, improve it instead of adding another. Add its `taxon` with `python3 tools/taxon.py --plant "<latin name>"` (mushrooms and lichens are fungi in GBIF; that's fine). | `check_taxa.py`, `check_models.gd` |
| 3 | **Only where it really grows.** List it in a place's `ground_cover.plants` only if it grows wild there today. Your sources must show that. A plant brought in by people that now grows wild (like garden lupin in Finland) is fine; say so in `year.notes`. | Reviewer |
| 4 | **Real looks and size.** Take the size from a field guide, always. Take the shape and colours from photos, or from a reference picture drawn for the purpose (the builder's agents draw one with Muse Image) that you check against a field guide, and follow the [art guide](ART.md). The build prints the size. Keep its field marks, for example the green stems of a bilberry in winter. | Builder, reviewer |
| 5 | **Its real year.** Fill in `year` (see below). Use `show` for flowers, fruit and leaves that are only there part of the year, and `seasons` for colours that change. A plant that drops its leaves must have `show` on its leaves. | `check_models.gd`, reviewer |
| 6 | **Sources.** List in `sources` where its looks and its year come from: links or book titles. | `check_models.gd` |
| 7 | **Made by you, from the spec.** No downloaded models, photos or textures. | Reviewer |
| 8 | **Within budget.** `kind: "ground"` is under 50 triangles and `kind: "bush"` under 300, on the busiest day of the year. A common plant (one that carpets the ground) should be about 120: use `detail` 0.5 or less on leaves and 0.3 or less on berries. | Builder |
| 9 | **Data only.** Change only its spec in `models/plants/`, its preview sheet in `models/previews/plants/` and region files. The built model is made from the spec when it's merged, so don't send it. If the plant needs something the spec can't do (a new shape, or being food, a hiding place or an obstacle), ask in your pull request. | Reviewer |
| 10 | **Realistic amounts, within the place's budget.** Set `density` to how common it really is there. Use `near_trees` for forest plants. Together with grass, flowers and stones, the amounts must add up to 1 or less. All the place's plants together may cost at most 100 triangles per square metre of open ground (each `density` × its triangles), so phones can draw them: a common plant must be cheap. | `validate_region.py` |

A plant is scenery unless the place makes it food. A place's `ground_cover.plants` entry can turn a plant, or one part of it, into food with `"food"` (see the region table): the porcini and the bilberry bushes in Nuuksio are food that way, while their part is in season. Only do that if the animals there really eat it ([Food first](#food-first-the-minimum-requirement)), and never for a plant that's poisonous to people, like the fly agaric: children learn from what the animals eat.

### Its year
Like an animal's, a plant's `year` records what it really does through the seasons. It's written for the place it's first added to. The `show` dates count from that place's own season starts, so one spec stays right in other places too: a bilberry in Lapland flowers later because Lapland's summer starts later.

```json
"year": {
  "leaves": "deciduous",
  "flowers": "Small pinkish bells under the leaves, late May to June.",
  "fruit": "Blue-black berries ripen from mid-July into September.",
  "notes": "Leaves turn red in autumn and fall. The angular stems stay green all winter."
}
```

- `leaves`: `evergreen` or `deciduous` (it drops its leaves).
- `flowers` and `fruit`: when, in a sentence, or `none`.
- `notes`: optional. Anything else true about it, even what the game can't show yet.

Then match the model to it: each part's `show` (`{"from": "summer+50", "until": "autumn+20"}`) and the `seasons` colours. The bottom row of the preview sheet shows four real dates, so check it against your sources.

### Start to finish
1. **Check** that it isn't in `models/plants/` already (rule 2), and that it really grows wild in your place (rule 3). [docs/catalogue.md](docs/catalogue.md) lists the plants the game has and the ones it wants most.
2. **Spec.** Copy [`models/plants/bilberry.json`](models/plants/bilberry.json) to `models/plants/<id>.json`. `<id>` is its English name in lowercase with `_`, e.g. `wood_anemone`. Fill in `name`, `latin`, `author`, `year`, `sources`, then the shapes and colours.
3. **Build** it and look at the preview sheet (`models/previews/plants/<id>.png`). Fix it until it looks right from every side and in every season.
   ```bash
   tools/build_model.sh models/plants/<id>.json
   ```
4. **Place it** in a region's `ground_cover.plants`: `{"model": "<id>", "density": 0.1, "near_trees": 5}`. Add `"on": ["grass", "rock"]` if it also grows on bare rock.
5. **Check it** (step 6 needs the game repository; otherwise the core team plays it for you).
   ```bash
   python3 tools/validate_region.py
   python3 tools/check_schemas.py
   python3 tools/check_models.py
   ```
6. **See it in the game.** Run `tools/build_web.sh && python3 tools/serve.py`, open `http://localhost:8060/?region=<region>&mode=safe`, and add `&date=2026-08-10` (and other dates) to see it through the year.
7. **Pull request.** Include the preview sheet, a screenshot from the game, and your sources. Reviewers use the checklist in [ART.md](ART.md#7-checklist-for-review).

An AI assistant can do steps 1–6 by itself. Give it this prompt:

> Add a **[PLANT]** to the Animundo game, in **[PLACE]**. Read `ART.md`, `CONTRIBUTING.md` (Adding plants) and `models/README.md` (Plants), and use `models/plants/bilberry.json` as the example.
> First check the rules: is it already in `models/plants/`, and does it really grow wild in this place? If not, stop and tell me.
> Use real facts from sources you list: its size, shape and colours, and its year in this place (when it flowers and fruits, whether it drops its leaves, and its autumn colours).
> Build it, look at the preview sheet and fix it until it looks right in every season. Add it to the region at a realistic density, run all the checks, and look at it in the browser in summer, autumn and winter.

A person always reviews the preview sheet and the screenshot before merging.

## Translating
All text the player sees is in [`locale/`](locale/), one folder per language with flat `{"key": "text"}` files:
- `ui.json`: menus, buttons and general messages. The English originals are in `locale/en/ui.json`.
- `animals.json`: animal messages. The English originals are the `text` in each animal file. Keys are `animal.<id>.<message>` and `archetype.<name>.<message>`.
- `food.json`: food names, keyed by the English name in the region file, e.g. `"food.bilberries": "mustikat"`.
- `regions.json`: place names, e.g. `"region.fi_nuuksio.name": "Nuuksion kansallispuisto"`.
- `plants.json`: the field guide pages of plants, mushrooms and trees, in every language including English. Keys are `plant.<id>.<part>`: `title`, `latin` (the same in every language), `about_looks`, `about_grows`, `about_year`, `about_safety`, `about_fact`, and an optional short `warning` shown when a player taps it ("Poisonous! Look, but don't pick."). `<id>` is the plant's id in `models/plants/`, or a tree's `plant` in the region. Safety text must be checked by someone who knows the species.

Keep `{placeholders}` such as `{day}` exactly as they are; you can move them anywhere in the sentence. Anything not yet translated shows in English. To add a language, create `locale/<code>/` (two-letter ISO code) and add it to [`locale/languages.json`](locale/languages.json) under its own name (`"fi": "Suomi"`). The checker above reports what's still missing; add `--strict` to treat gaps as errors.

## Wetland habitats

Regions may define `bogs`: `{name, x, z, radius}` (normalised centre, radius in metres), and `streams`: `{points: [[x,z], ...], width}` (normalised points, width in metres). Channels use the same water level as lakes. Their layout is illustrative unless researched and documented. Plants with `habitat: "bog"` grow only in bogs; omitted habitat means forest. Each habitat has its own density total of at most 1.
