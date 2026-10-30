# Food

A place's food is worked out, not written (game proposal 0043, layer 4). [`rules.json`](rules.json) says when each food kind is there and where its names come from: berries, mushrooms, cones, seeds, browse and water plants from the plants and trees that grow there (their `grows` in `models/plants/` and `models/trees/`), grass and bark from the land and the trees, insects and water bugs from the water there, and carrion from the large animals.

```bash
python3 tools/food.py derive homes/sea_717.json   # the worked-out food
python3 tools/food.py report                       # where every home's and region's written food disagrees
```

The game works a tile's food out with the same rules (`scripts/tile_layers.gd`, which reads the mirrored `food/rules.json`), and `tools/check_tile.py` checks a tile's animals against it in the place `tools/tile_region.py` makes (the one converter from a tile to the game's place; golden examples in `tests/tile_region/` hold the game to it). A kind no animal there eats gets weight 0, as in the game. Homes and regions still have their written `food` while the layers move in; the report shows where it has drifted from what's there. It fails only when an animal can't find its food (decision 0011). CI runs it.

A hand-made place can be layered too ([`lands/`](../lands/), game proposal 0043): Nuuksio and Saimaa name the `boreal` land style, their `plants` by id and their `small_life` names, and write no colours, plant entries or food. `tools/layers.py` `resolve()` fills those in for every tool that reads a region, as the game does when it loads one.
