# Food

A place's food is worked out, not written (game proposal 0043, layer 4). [`rules.json`](rules.json) says when each food kind is there and where its names come from: berries, mushrooms, cones, seeds, browse and water plants from the plants and trees that grow there (their `grows` in `models/plants/` and `models/trees/`), grass and bark from the land and the trees, insects and water bugs from the water there, and carrion from the large animals.

```bash
python3 tools/food.py derive homes/sea_717.json   # the worked-out food
python3 tools/food.py report                       # where every home's and region's written food disagrees
```

The game works a tile's food out with the same rules (`scripts/tile_layers.gd`, which reads the mirrored `food/rules.json`), and `tools/check_tile.py` checks a tile's animals against it in the place `tools/tile_region.py` makes (the one converter from a tile to the game's place; golden examples in `tests/tile_region/` hold the game to it). A kind no animal there eats gets weight 0, as in the game. Homes and regions still have their written `food` while the layers move in; the report shows where it has drifted from what's there. What an animal can't find is listed as a gap, never a failure (game decision 0061). CI runs it.

## The food rule (game decision 0061)

An animal eats on a tile when **any** of its `diet` kinds is in the tile's food, or **any** tag it `hunts` belongs to another animal living there. A diet is a menu, not a shopping list. What it can't find there is a gap: content to build, never a reason to leave the animal out, since the survey and its habitats decide where it lives. A player only starts where their animal eats something.

[`eats-cases.json`](eats-cases.json) holds the cases every copy of the rule runs: `tools/food.py` (`eats_here`, `food_gaps`; `tools/test_food.py`), the game's `TileLayers` (`tools/check_food_rule.gd`) and the builder. Change the rule here first, with a case, then in each copy.

A hand-made place is built on a biome as a tile is (game proposal 0043): Nuuksio names `boreal_forest` and Saimaa `boreal_lake` in `biome`, and their animals in `species`. Their land style, plants, small life, fish, migrants and seasons come from the biome; each keeps only its own geography (terrain numbers, named lakes, bogs, streams, landmarks, start spots). `tools/layers.py` `resolve()` builds the full place for every tool that reads a region, as the game does when it loads one.
