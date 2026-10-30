# Homes

**Homes are made from biomes now** (game proposal 0043, phase 3). A biome, `biomes/<id>.json`, is the same home in layers: a land style (`lands/<id>.json`: colours, sky, roughness), its plants by id from the library where every entry is one, and small-life names instead of a food list, because food is worked out (`food/rules.json`). `homes/<id>.json` is made from it by `python3 tools/biomes.py flatten`, for the tools and the builder that still read whole homes. **Edit the biome, never the home**; CI checks that homes/ is up to date. A new home made with `adapt_home.py` goes in homes/ as before, then becomes a biome with `python3 tools/biomes.py split <id> <land style>`. Which land style a grid cell takes is in `lands/index.json` (by its RESOLVE biome number).

A **home** is the land of one habitat, ready to copy: terrain, trees, ground plants, water, food kinds and fish, with no name, no center and no animals. Animundo Builder's animal-first build (a grown-up picks an animal, then a spot where it lives) copies the home that fits the animal, names it and centres it on the spot, then adds the animal, its food and its neighbours.

| Home | Habitat in `animal-list.json` | RESOLVE ecoregions | Based on |
|---|---|---|---|
| `boreal_forest.json` | `boreal_forest` | 717 Scandinavian and Russian taiga | `regions/fi_nuuksio.json` |
| `boreal_lake.json` | `boreal_lake` | 717 Scandinavian and Russian taiga (the lakes) | `regions/fi_saimaa.json` |
| `tundra.json` | `tundra` | 780 Scandinavian montane birch forest and grasslands (the Lapland fells) | `examples/tundra.json` on `boreal_forest.json` (`adapt_home.py`) |
| `rainforest.json` | `rainforest` | 483 Napo moist forests (Yasuní) | `examples/rainforest.json` on `boreal_forest.json` |
| `savanna.json` | `savanna` | 57 Southern Acacia-Commiphora bushlands and thickets (the Serengeti) | `examples/savanna.json` on `boreal_forest.json` |
| `sea.json` | `sea` | 651 Celtic broadleaf forests (the Welsh coast) | `examples/sea.json` on `boreal_forest.json` |

A home is a region file with four extra fields: `ecoregions`, the [RESOLVE Ecoregions 2017](https://ecoregions.appspot.com) ids (`ECO_ID`, CC BY 4.0) it stands for; `habitat`, its habitat id in `animal-list.json`; `based_on`, the home (or place) it was adapted from; and `about`, a note for builders. Its `description` is what players read. On the tile grid (Proposal 0038) a cell is built from the home that lists its ecoregion and has its habitat: `boreal_forest` and `boreal_lake` share the taiga, and the sea home stands for the Welsh coast's cells, not its inland ones. A new ecoregion gets its own home, adapted from the nearest one. Make a region from one with:

```bash
python3 tools/homes.py make boreal_forest --id fi_lynx_forest --name "Lynx forest" --country Finland --lat 61.2 --lon 26.9
```

The four from the examples were looked at in the game at Proposal 0038's lab spots and approved by Kai (2026-10-28). Animundo Builder's tile maker builds code-made tiles from these homes and checks each with `python3 tools/check_tile.py <tile.json>`.

`python3 tools/homes.py check` makes every home at a sample spot and runs the region checks on it (CI runs it too).

**Adding a home** opens every animal on the list with that habitat. Start from the closest place or example environment, take out its real names (lakes, bogs, places), empty its animals, and give it real plants and trees for that habitat. Then add its row here and run `python3 tools/animal_list.py` so the list knows it exists. The ones families ask for most come first: rainforest, savanna, mountain, sea, reef.

## Making a new home in code

`tools/adapt_home.py` makes a new home from the closest one and a short list of choices: land (flat, rolling, hilly, mountains), the main water (river, lake, pools, sea, none), wetness, ice (none, frozen_in_winter, glaciers, polar), caves (none, some), the seabed (mud, sand), colours, tree shapes and colours, grass, flowers, library plants, water life and foods. Code sets every number, so the land always stands above the water, a river or lake stays clear of the middle where animals start, and only a lake or sea home is an island. A made rainforest whose numbers were written by hand ended up under water.

The special places are choices too, and code sets their numbers: `mountains` makes the world 64 blocks tall with bare rock above the trees; `water: "sea"` cuts a bay 7 blocks deep (the most the one water level, 8, allows: the sea is deep because its floor is low, never because its water is high) whose shore is about 80 m from the middle, so seals and fish start in it; `ice` adds frozen water in winter, glaciers on the tops, or polar ice and icebergs; `caves: "some"` digs caves in the hills; `seabed: "sand"` gives warm seas a sandy floor. The sea has no reeds or water lilies. Season dates aren't copied from the base home, so the game's own dates follow the hemisphere.

Each example was made from real research by an AI choices call and looked at in the game: [`rainforest`](examples/rainforest.json), [`savanna`](examples/savanna.json), [`mountain`](examples/mountain.json) (an ibex in the Alps), [`tundra`](examples/tundra.json) (a musk ox in Arctic Canada), [`ice`](examples/ice.json) (a polar bear in Svalbard), [`sea`](examples/sea.json) (a grey seal in Wales), [`reef`](examples/reef.json) (a clownfish on the Great Barrier Reef), [`mangrove`](examples/mangrove.json) (a crocodile near Darwin) and [`desert`](examples/desert.json) (a fennec fox in Tunisia). The savanna has umbrella thorns. The library's corals and red mangrove are Caribbean and American, so two more examples were written by hand from the AI's: [`reef_caribbean`](examples/reef_caribbean.json) (staghorn coral, brain coral and sea fans on the sandy floor) and [`mangrove_americas`](examples/mangrove_americas.json) (red mangroves on stilt roots along a shallow bay). The Queensland reef and the Darwin mangrove stay without them: only plants that really grow there.

```bash
python3 tools/adapt_home.py homes/boreal_forest.json homes/examples/savanna.json --check --out homes/savanna.json
```
