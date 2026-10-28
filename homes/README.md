# Homes

A **home** is the land of one habitat, ready to copy: terrain, trees, ground plants, water, food kinds and fish, with no name, no center and no animals. Animundo Builder's animal-first build (a grown-up picks an animal, then a spot where it lives) copies the home that fits the animal, names it and centres it on the spot, then adds the animal, its food and its neighbours.

| Home | Habitat in `animal-list.json` | Based on |
|---|---|---|
| `boreal_forest.json` | `boreal_forest` | `regions/fi_nuuksio.json` |
| `boreal_lake.json` | `boreal_lake` | `regions/fi_saimaa.json` |

A home is a region file with two extra fields, `based_on` and `about` (a note for builders); its `description` is what players read. Make a region from one with:

```bash
python3 tools/homes.py make boreal_forest --id fi_lynx_forest --name "Lynx forest" --country Finland --lat 61.2 --lon 26.9
```

`python3 tools/homes.py check` makes every home at a sample spot and runs the region checks on it (CI runs it too).

**Adding a home** opens every animal on the list with that habitat. Start from the closest place or example environment, take out its real names (lakes, bogs, places), empty its animals, and give it real plants and trees for that habitat. Then add its row here and run `python3 tools/animal_list.py` so the list knows it exists. The ones families ask for most come first: rainforest, savanna, mountain, sea, reef.

## Making a new home in code

`tools/adapt_home.py` makes a new home from the closest one and a short list of choices: land (flat, rolling, hilly, mountains), the main water (river, lake, pools, sea, none), wetness, ice (none, frozen_in_winter, glaciers, polar), caves (none, some), the seabed (mud, sand), colours, tree shapes and colours, grass, flowers, library plants, water life and foods. Code sets every number, so the land always stands above the water, a river or lake stays clear of the middle where animals start, and only a lake or sea home is an island. A made rainforest whose numbers were written by hand ended up under water.

The special places are choices too, and code sets their numbers: `mountains` makes the world 64 blocks tall with bare rock above the trees; `water: "sea"` raises the water to 16 and cuts a deep bay whose shore is about 80 m from the middle, so seals and fish start in it; `ice` adds frozen water in winter, glaciers on the tops, or polar ice and icebergs; `caves: "some"` digs caves in the hills; `seabed: "sand"` gives warm seas a sandy floor. The sea has no reeds or water lilies. Season dates aren't copied from the base home, so the game's own dates follow the hemisphere.

Each example was made from real research by an AI choices call and looked at in the game: [`rainforest`](examples/rainforest.json), [`savanna`](examples/savanna.json), [`mountain`](examples/mountain.json) (an ibex in the Alps), [`tundra`](examples/tundra.json) (a musk ox in Arctic Canada), [`ice`](examples/ice.json) (a polar bear in Svalbard), [`sea`](examples/sea.json) (a grey seal in Wales), [`reef`](examples/reef.json) (a clownfish on the Great Barrier Reef), [`mangrove`](examples/mangrove.json) (a crocodile near Darwin) and [`desert`](examples/desert.json) (a fennec fox in Tunisia). The reef has no corals and the mangrove no mangrove trees until those specs move from `models/examples/` into the library (`models/plants/`, `models/trees/`):

```bash
python3 tools/adapt_home.py homes/boreal_forest.json homes/examples/savanna.json --check --out homes/savanna.json
```
