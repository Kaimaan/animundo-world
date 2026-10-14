# Animals wanted

The animals and foods the game needs next, so that every animal already in it can eat what it really eats. Pick one, follow **Adding animals** in [CONTRIBUTING.md](../CONTRIBUTING.md), and open a pull request. Under the food-first rule ([decision 0011](decisions/0011-food-first.md)), a new animal that needs food from this list brings that food with it.

Every hunter follows one rule: **catching is eating**, with one tap and no separate Eat step ([CONTRIBUTING.md](../CONTRIBUTING.md#the-animal-file)). A kestrel's dive and a perch's chase will work like the fox's pounce.

Each row says who it feeds. The more animals it feeds, the higher it is. "Code" means the core team has to build something before the animal can do everything listed; the data and model can be made before that.

## Nuuksio

### Animals
| # | Animal | Feeds | Needs | Status |
|---|---|---|---|---|
| 1 | **Bank vole** (metsämyyrä, *Myodes glareolus*) | Fox (its main food all year), kestrel (its main food), owls later | New model. Tags `small_mammal`, `vole`; the kestrel then `hunts: ["vole"]`. Code: wild prey that isn't a rabbit (`prey.gd` only makes rabbits), and a kestrel that hovers and drops onto prey. | Wanted |
| 2 | **Mountain hare** (metsäjänis, *Lepus timidus*) | Fox, later lynx and eagle owl | New model from a spec, with a white `winter` coat. It replaces the "rabbit": European rabbits don't live wild in Nuuksio ([ART.md](../ART.md): real species only). | Wanted |
| 3 | **Young perch and young roach** (ahvenen ja särjen poikaset) | Perch (its main food from summer on: perch eat small fish, even young perch), pike | No new model: the perch and roach models at baby size, from the baby stage ([decision 0010](decisions/0010-baby-start-with-family.md)). Tag `fry`; the perch then `hunts: ["fry"]`. Code: hunters only catch prey much smaller than themselves, and the player's fish can chase fish. | Wanted |
| 4 | **Common frog** (sammakko, *Rana temporaria*) | Pike (spring), fox, later heron | New model. Code: an animal that lives on land and in water (a new archetype). | Wanted |
| 5 | **Common lizard** (sisilisko, *Zootoca vivipara*) | Kestrel (summer) | New model. Cold-blooded, basks on sunny rocks. | Wanted |
| 6 | **Chaffinch** (peippo, *Fringilla coelebs*), with eggs and nestlings | Fox (spring: birds and eggs), later sparrowhawk | New model. Tag `small_bird`. Code: nests with eggs and young. | Wanted |

### Foods (made in code by the core team)
| Food | Feeds | Status |
|---|---|---|
| Spruce cones and seeds (kuusenkävyt) | Squirrel (its main food autumn to spring) | Wanted |
| Mushrooms (sienet) | Squirrel (summer and autumn; it dries them on branches) | Wanted |
| Bark, twigs and buds (kuori, oksat, silmut) | Mountain hare (winter) | Wanted |
| Carrion (raato) | Fox (winter) | Wanted |

## Model and animation work (core team)
These change the model builder or the game, so every animal gets them at once. See [models/README.md](../models/README.md) and [decision 0012](decisions/0012-smooth-skin-models.md).

| Work | Why | Status |
|---|---|---|
| **Swimming land animals:** a generated `swim` clip for every four-legged animal (dog paddle: short fast leg strokes, head up, tail trailing), played while it's in water, with a preview tile | Foxes, squirrels and hares really swim, but in the game they play their walk animation, so they look like they're walking on the lake bottom | Wanted |
| **One material per animal:** colours stored on the model (or a tiny colour strip) instead of one material per colour; coats swap the colours | Each material is a separate draw call: 4–6 per animal today. Cheap phones struggle with many animals on screen long before triangles matter. Colours per vertex would also fix the jagged colour edges (a perch's bars, a roach's back) left by reducing the triangles | Wanted |
| **Body-plan templates:** a starting spec per body plan (four-legged, bird, fish) | Agents and contributors copy the closest one instead of starting from scratch | Wanted |
| **Swimming birds:** ducks and grebes floating on the surface | No swimming birds yet | Later |

## Night animals (later)
Bats (lepakot, such as the northern bat *Eptesicus nilssonii*), owls and other animals that are awake at night. Before the first one arrives, the core team has to test how night should work. Ideas to try ([0014](decisions/0014-day-and-night-pace.md), open: to be tested before deciding):

| Work | Why | Status |
|---|---|---|
| **Night at normal speed:** no fast-forward while day animals sleep. A fixed day of about 15 minutes (about 7 of day, 2 of dusk, 4 of night, 2 of dawn), set in data | Today sleeping makes time 20× faster, so the night is over in seconds. A night animal would have nothing to play. Long days and nights are boring too | Later |
| **Wait or switch:** when your animal falls asleep, ask *"Wait for morning, or play another animal?"* The sleeping animal stays saved in its den. Night animals get the same choice at dawn | One shared clock, so a player who doesn't want to wait goes and plays something else | Later |

### Fixed already
- **Kestrel ate berries.** Real kestrels don't, so berries were removed. Until voles arrive (row 1), it eats only beetles.
