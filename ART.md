# Animundo art guide

How everything in the game world should look: animals, plants, props and places. Follow it, and things made by anyone fit in with things made by everyone else. The logo, brand colours and app icons are in [BRANDING.md](BRANDING.md).

**In one line:** a storybook diorama of the real world. The shapes are simple, rounded and friendly, the colours are flat and natural, and every animal is the real species, recognisable at a glance.

![The red squirrel's preview sheet: a model that follows this guide](models/previews/squirrel.png)

## 1. Real first, then simple
Animundo teaches children about real nature, so **accuracy beats cuteness.**

- **Simple, not realistic.** The game is simple and blocky, and everyone can see a model is not the real animal. Never try to make a model look real, or close to real. It needs only the right body plan, rough size and proportions, main colours and the one or two marks that tell the species apart (a fox's white tail tip, a great tit's black tie). No feathers, fur, scales or other detail; a model is done as soon as a child would recognise the species.
- **The real species.** Every animal, plant and place is a real one. Check proportions, colours and size against photos and a field guide, not other games or cartoons. A reference picture drawn for the purpose is fine for shape and colours if it is checked against a field guide; the size always comes from the field guide. Reference pictures and photos are only looked at: they are never committed or shown in the game.
- **Keep its field marks.** These are the few things that tell a species apart, and they must show from a few metres away: a red squirrel's ear tufts and white belly, a fox's white tail tip and dark legs, a perch's dark stripes. Leave out everything else.
- **Real size in metres.** A squirrel is 0.36 m long and a fox about 1 m. Never scale an animal up to make it easier to see; the camera handles that (`cam_dist` in the animal file). The one exception is the small world (see [Two scales](#two-scales-the-world-and-the-small-world)).
- **No people things.** Animals don't wear clothes, stand on two legs (unless the real one does), smile or have cartoon eyes. They behave like real animals.

**Allowed stylisation:** a head and eyes up to about 15% larger than real, smooth rounded bodies instead of fur and feathers, and simplified shapes. Proportions between body parts stay real.

### Two scales: the world and the small world
The game has two scales, so a moose and a bumblebee can share one forest and both be playable on a phone.

| | What's in it | Size in the game |
|---|---|---|
| **The world** | Every animal with a backbone, however small (mammals, birds, fish, frogs, lizards: an 8 cm frog too), and everything else 10 cm or larger: trees, shrubs, rocks, the ground | **Real size** |
| **The small world** | Insects, spiders, snails and other small animals without a backbone, and the small plant parts they live on: flowers and blossoms, berries, moss, needles | **5 times real size** |

- **Why:** a real 2 cm bumblebee is a speck on a phone screen, and the world's ground isn't detailed enough to play at that size. We tested it: a real-size bee's camera ends up inside a flower. At 5 times, a bee is about 10 cm and easy to see and steer.
- **Sizes stay true inside each scale.** A bee is the right size next to a flower, and a moose the right size next to a fox. Never mix them: no enlarged mammals, and no real-size insects.
- **Young animals keep their family's scale.** A young perch or a baby fox is real size, however small: it belongs to the world, like its parents. The small world is for insects, spiders, snails and their plants.
- **Big and small still meet.** An enlarged ant is about 3 cm, still tiny under a bear's paw, so stepping on ants and bears eating them still work.
- **Build at real size, show at 5 times.** Specs are always in real metres. For a small-world animal, the animal file's `length` is 5 times the length the build prints (the bumblebee: printed 0.017, `length` 0.085).
- **Field guides tell the real size.** Players learn the true size from the text, for example "a bumblebee queen is about 2 cm long", never from the model.

## 2. Shapes
- **Built from simple solids:** balls, boxes, cylinders, cones and tapers, overlapping slightly so there are no gaps. Animals and plants are built from a spec in [`models/`](models/README.md). Trees, grass, flowers, stones and lake plants are still made in code in [`scripts/world.gd`](scripts/world.gd) and [`scripts/art.gd`](scripts/art.gd); new plants should be specs.
- **Low-poly and soft.** Animals are one smooth, softly shaded body, like a clay figure ([decision 0012](docs/decisions/0012-smooth-skin-models.md)). Facets (flat shading) cost about 5 times more for the phone to animate, so they're for props and terrain, not animals.
- **Silhouette first.** If you can't name the animal from its black outline, change the shapes before the colours.
- **Rounded and friendly.** Avoid sharp spikes and thin needles, except where the real thing has them (ear tufts, a pike's teeth, spruce needles as a cone shape).

## 3. Colour
- **Flat colours, no textures.** One colour per part. There are no image textures, no painted-on detail and no shiny or metal surfaces (roughness 1, metallic 0). Light and shade do the rest: the game's materials fall into soft bands of light and shadow.
- **Natural colours from photos.** Pick the colour from a photo in daylight, then make it a little cleaner and more saturated. Name each colour after what it is (`fur`, `belly`, `bark`), not how it looks (`brown2`).
- **No pure black or white.** Use a dark brown-black like `#2a1f1a` and a warm cream like `#efe3cf`. Pure black looks like a hole, and pure white glows in the light.
- **Stand out from the ground.** An animal must read against its region's ground (`palette` in the region file, e.g. Nuuksio's `#5f9445` grass) and against snow (`#eef2f6`). If its real colours blend in, that's real camouflage. Keep it, but make the silhouette and field marks clear.
- **Few colours.** Most animals need 3–6 colours. More turns into noise at game distance.
- **Seasons are real.** Add a seasonal coat only if the real animal changes, e.g. a red squirrel greying in winter or a mountain hare turning white. See [models/README.md](models/README.md#seasonal-coats). Plants change too: autumn leaves, and flowers, berries and leaves that are there only part of the year. See [models/README.md](models/README.md#plants).

## 4. Size on screen and budgets
The game is for millions of players on cheap phones, with many animals on screen at once, so every asset has a budget. What counts is what the player downloads (Godot's converted model, not the `.glb`) and the work the phone does every frame to animate it.

| Asset | Triangles | Bones | Download |
|---|---|---|---|
| Playable animal | 1,000 (up to 1,500 for a large, complex one) | up to 16 | under 50 KB |
| Wildlife that is never played (prey, fish in schools) | 400–800 | up to 12 | under 30 KB |
| Plant spec, `kind: "bush"` (a bilberry, a fern), or a prop or tree | under 300 on any day of the year; **about 120 for a common plant** (one that carpets the ground) | none | `.glb` from a spec, or made in code |
| Ground cover, `kind: "ground"` (grass, a small flower, a stone), drawn thousands of times | under 50 | none | `.glb` from a spec, or made in code |
| **All the plants of a place together** | under **100 per square metre** of open ground: each plant's `density` × its triangles, added up. `validate_region.py` checks it | | |

What we measured ([decision 0012](docs/decisions/0012-smooth-skin-models.md)):
- **Animation is usually the biggest cost.** It grows with bones × clips. The downloaded fox's 51 bones and 12 clips are 407 of its 489 KB; the squirrel's 12 bones and 5 generated clips are 14 KB. Keep bones few.
- **Each triangle costs about 35 bytes** of download with flat shading and about 20 with smooth shading.
- **One material per animal.** Its colours are stored on the vertices, so the phone draws it in one call ([decision 0013](docs/decisions/0013-one-material-per-animal.md)). With one material per colour, 48 animals cost 1,218 draw calls per frame; now they cost 198.
- **Smooth shading moves about 6 times fewer vertices** than flat: 587 for the squirrel against 3,278 for the same body faceted.
- **Plants are drawn thousands of times.** Measured in Nuuksio in August (2026-10-15): with five common plants at about 300 triangles each, the ground cover around the player cost 95–143k triangles and 161–173 draw calls, more than all the terrain and trees. Now each chunk's ground cover is one merged mesh per material (about 4 draw calls), plants are drawn only within about 20 m, and the common plants are about 120 triangles. Cheap plants use `detail` 0.5 or less for 2-triangle leaves and 0.3 or less for 8-triangle berries.

The red squirrel is 1,000 triangles, 12 bones, one material and a 33 KB download. Detail smaller than about 1 cm on a small animal, or 5 cm on a large one, won't show from the game camera, so leave it out.

## 5. Movement
- **Real gaits.** Squirrels and hares `bound` (left and right legs together). Foxes, deer and most mammals `walk` (legs alternate). Fish wave their tail and birds flap.
- **Calm and readable.** Movements are smooth and a little slower than real, never jittery. Idle animals breathe, look around and twitch their ears.
- **Same clip names for everyone:** `idle`, `walk`, `run`, `eat`, `sleep`, plus `fly` and `swim`. The model builder makes these automatically.

## 6. Places
A region should look like the real place on a clear day, painted.
- **Colours from the real landscape** for ground, rock, water and sky (see [CONTRIBUTING.md](CONTRIBUTING.md)). Take them from photos, then make them slightly cleaner.
- **Real plants and animals** for that place only. No palm trees in Finland.
- **Real seasons.** A region follows its real calendar, so set autumn colours (`autumn` on deciduous trees) and snow only where they really happen.

## 7. Checklist for review
Reviewers check new art against this list, using the preview sheet and an in-game screenshot:

- [ ] It's a real species or place, and the pull request says which sources were used.
- [ ] Its field marks show from a few metres away.
- [ ] Its size is real (the build prints it).
- [ ] It uses flat colours only, with no textures, no pure black or white, and 3–6 colours for an animal.
- [ ] Nothing floats, has gaps or clips through other parts in any pose.
- [ ] It's within the triangle, bone and download budgets.
- [ ] It reads clearly against the region's ground and against snow.
- [ ] A seasonal coat is included only if the real animal changes colour.
- [ ] A plant's flowers, berries and leaves come and go at the real time of year (the season row of its preview sheet).

## Older assets
All animals are now built from specs ([decision 0012](docs/decisions/0012-smooth-skin-models.md)). The downloaded fox, rabbit, kestrel and fish were replaced on 2026-10-14.
