# Animal models

Every animal model in Animundo is made from a **model spec**, one small data file `models/<id>.json`. It lists simple shapes, colours and bones. There's no code to write and no 3D modelling to do. [Blender](https://www.blender.org/download/), which is free, builds the spec into the animated model the game uses, plus a preview sheet for a person to review:

```bash
tools/build_model.sh models/squirrel.json
```

| Output | What it is |
|---|---|
| `assets/animals/<id>.glb` | The model with its animations: `idle`, `walk`, `run`, `eat`, `sleep`, plus `fly` (if it has wings) and `swim` (if it has fins). |
| `models/previews/<id>.png` | The preview sheet: front, side, back and top views, four walk frames, and run, eat and sleep poses. |

![squirrel preview](previews/squirrel.png)

Follow the [art guide](../ART.md): real species, real size, flat natural colours, simple shapes.

## The quick way: ask your AI assistant
> I want to add an animal model to the Animundo game. Read `ART.md`, `models/README.md` and `models/squirrel.json` as the example.
> Make a model spec for a **[ANIMAL]**, using its real size in metres, body proportions and colours.
> Build it with `tools/build_model.sh models/<id>.json`, look at the preview sheet, and fix whatever looks wrong
> (floating parts, gaps, wrong proportions, odd poses). Repeat until it looks right.
> Then run `godot --headless --import` and `godot --headless --script tools/check_models.gd`.

A person reviews the preview sheet in the pull request before it's merged. To add the whole animal to the game (animal file, text, region), follow **Adding animals** in [CONTRIBUTING.md](../CONTRIBUTING.md).

### Fixing what you see in the preview
| You see | Fix |
|---|---|
| A part floats, or there's a gap | Move it (`at`) so it overlaps its neighbour a little. |
| A foot hangs in the air or sinks | Its lowest point should be at `y = 0`: `at[1]` = half its height. |
| A part stays behind when the leg moves | Its `bone` is wrong: use the leg's bone, not `body`. |
| A row of balls looks like beads | Use more balls that overlap more, with `smooth: true`. |
| A pose looks odd (e.g. legs through the body) | Lower that bone's `swing`, or move the bone's `head` to the joint. |
| Wrong colour in a coat | Change the coat in `animals/<id>.json`; no rebuild is needed for the game. |

## The spec
Positions are in the game's coordinates, in **metres**, with the animal standing on the ground at `y = 0` and facing forward:
`x` is the animal's **left**, `y` is **up** and `z` is **forward**. Angles are in degrees.

| Field | What it means |
|---|---|
| `id` | The file name, e.g. `squirrel`. |
| `name`, `author` | The animal (common and Latin name) and who made the spec. |
| `gait` | `walk`: the left and right legs alternate (fox, deer). `bound`: they move together (squirrel, rabbit). |
| `colors` | Named colours, `{"fur": "#b5562a"}`. Parts use these names. |
| `bones` | The skeleton. See below. |
| `parts` | The shapes the body is made of. See below. |

### Bones
Each bone is `{name, head, tail, parent, role}`. `head` is where it bends and `tail` points along it, for example from the hip down to the foot. A bone moves every part attached to it and every bone below it. `parent` is a bone defined earlier, and is `root` (the ground point under the animal) by default.

The `role` decides how the bone moves in each animation:

| Role | Moves like |
|---|---|
| `body` | The trunk, which bends when running. Usually the first bone, with its parent `root`. |
| `head`, `neck` | Looks around, nods while walking, dips to eat and tucks in to sleep. |
| `jaw` | Chews while eating. |
| `leg` | Swings back and forth. `phase` (0–1) says when in the step it swings, e.g. front legs `0` and back legs `0.5`. |
| `tail` | Wags and follows the gait. In a chain of tail bones, raise `phase` a little for each one (0, 0.12, 0.24) so the tail waves. |
| `ear` | Twitches, and flattens back when running and sleeping. |
| `wing` | Flaps in the `fly` animation. |
| `fin` | Swings side to side in the `swim` animation (fish tails). |
| `none` | Doesn't move by itself. |

`swing` (default 1) makes a bone's movement bigger or smaller. `mirror: true` makes a copy for the right side: name the left one with `_l` at the end and the right one is `_r`. In a `walk` gait, the right leg's step is automatically half a step behind the left.

### Parts
Each part is one shape: `{name, shape, size, at, rot, color, bone}`.

| Field | What it means |
|---|---|
| `shape` | `box`, `ball`, `cylinder`, `cone` (pointed at the top), or `taper` (a cylinder narrower at the top; `top` sets how much, 0–1). |
| `size` | `[width, height, length]` in metres, before rotating. |
| `at` | Where its middle is. |
| `rot` | `[pitch, yaw, roll]` in degrees. Pitch tips the front down, yaw turns it left and roll leans it to the right. `[180, 0, 0]` turns a cone upside down. |
| `color` | One of the names in `colors`. |
| `bone` | The bone it moves with. |
| `mirror` | `true` makes a copy for the right side (name ends in `_l`). If the bone ends in `_l`, the copy uses the `_r` bone. |
| `separate` | `true` keeps the part as its own crisp piece instead of melting it into the body. Use it for eyes, nose, ears and tufts. Parts thinner than two voxels are kept separate anyway. |
| `detail` | How round balls and cylinders are (1 is the default). It only matters for `separate` parts; the body is rebuilt from the melted shape. |

### How the body is made
The builder doesn't use the shapes as they are. It **melts them into one continuous skin**, like clay, smooths it, and reduces it to the triangle budget. Each spot on the skin takes its colour and bone from the nearest part, and the bones' pull is blended across the joints so the skin bends instead of tearing. So write the spec as if you were sculpting with lumps of clay: overlapping shapes become one smooth body.

The settings are tuned for the whole game (see [decision 0012](../docs/decisions/0012-smooth-skin-models.md)). Change them only with a reason, in a `skin` entry in the spec:

| Setting | Default | What it does |
|---|---|---|
| `triangles` | `1000` | Triangle budget for the whole animal. See the budgets in [ART.md](../ART.md#4-size-on-screen-and-budgets). |
| `shading` | `"smooth"` | Soft shading. `"flat"` gives facets, but costs about 5 times more vertices and twice the download. |
| `voxel` | `1/70` | How finely the parts are melted, as a part of the body length. Smaller keeps thinner legs. |
| `smooth` | `4` | Smoothing passes on the melted body. It costs nothing in size. |
| `blend` | `3` | How far a joint's bend spreads along the skin. |
| `keep` | `2` | Parts thinner than this many voxels stay separate. |

`"skin": false` builds the old way, from loose parts. Don't use it for new animals.

### Rules for a good spec
These came from building the squirrel. Each one fixes something that looked wrong in a preview.

- **Overlap generously.** Melted parts need to overlap by about a third of their size, or the skin pinches between them.
- **Chains of balls overlap by half.** A tail or neck made of balls looks like beads unless each ball overlaps the next by at least half its length. Use 5–7 balls for a bushy tail.
- **Separate parts sink in.** Eyes, ears and tufts must reach into what they sit on by a third of their own size. Smoothing can shrink the body slightly, and a part that only touches it will float.
- **Ears are tapers, not cones.** A cone's tip disappears from a few metres away. Use `taper` with `top` about 0.4.
- **Mark the details.** Set `separate: true` on eyes, nose, ears and tufts so they stay crisp.
- **Thin legs stay thick enough.** A leg thinner than about 1/30 of the body length melts away. Make it a little thicker than real if needed.

### Checklist for a good model
- **Real size.** Look the animal up. The build prints its length and height.
- **No gaps.** Parts on the same body overlap a little. Legs reach the ground (`y = 0`), and nothing floats.
- **Recognisable from far away.** The game camera is a few metres back, so silhouette and colour matter more than detail.
- **Bones where the joints are.** The `head` of a leg bone sits at the shoulder or hip, not at the foot.
- **Within budget.** The build prints the triangles; [ART.md](../ART.md#4-size-on-screen-and-budgets) has the limits.

## Seasonal coats
Some animals change colour with the seasons. A red squirrel turns greyer in winter, and a mountain hare turns white. A coat lists only the spec colours that change. It goes in the **animal file**, `animals/<id>.json`, under `model`:

```json
"coats": {"winter": {"fur": "#8a7266", "fur_dark": "#5e4a44"}}
```

Seasons are `spring`, `summer`, `autumn` and `winter`. They follow the region's real calendar. A coat grows in over the first three weeks of its season and fades out over the first three weeks of the next season, like a real moult. The preview sheet shows every coat, and the build stops with an error if a coat names a colour the spec doesn't have. Animals that keep the same coat all year leave `coats` out.

To see a coat in the game, add a date to the URL, e.g. `&date=2027-01-20`.

## Using the model in the game
After building, set the `model` entry in `animals/<id>.json`: `"file": "res://assets/animals/<id>.glb"`, `"yaw": 0.0`, the `length` the build printed (so the model keeps its real size), and the clips by name, e.g. `"anims": {"idle": "idle", "walk": "walk", "run": "run", "eat": "eat", "sleep": "sleep"}`.
