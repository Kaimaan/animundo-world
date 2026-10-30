# Food

A place's food is worked out, not written (game proposal 0043, layer 4). [`rules.json`](rules.json) says when each food kind is there and where its names come from: berries, mushrooms, cones, seeds, browse and water plants from the plants and trees that grow there (their `grows` in `models/plants/` and `models/trees/`), grass and bark from the land and the trees, insects and water bugs from the water there, and carrion from the large animals.

```bash
python3 tools/food.py derive homes/sea_717.json   # the worked-out food
python3 tools/food.py report                       # where every home's and region's written food disagrees
```

Homes and regions still have their written `food` while the layers move in; the report shows where it has drifted from what's there. It fails only when an animal can't find its food (decision 0011). CI runs it.
