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

`tools/adapt_home.py` makes a new home from the closest one and a short list of choices: land (flat, rolling, hilly), the main water (river, lake, pools, sea, none), wetness, colours, tree shapes and colours, grass, flowers, library plants, water life and foods. Code sets every number, so the land always stands above the water, a river or lake stays clear of the middle where animals start, and only a lake or sea home is an island. A made rainforest whose numbers were written by hand ended up under water. The tested examples are [`examples/rainforest.json`](examples/rainforest.json) and [`examples/savanna.json`](examples/savanna.json):

```bash
python3 tools/adapt_home.py homes/boreal_forest.json homes/examples/savanna.json --check --out homes/savanna.json
```
