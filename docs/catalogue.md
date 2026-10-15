# Animundo catalogue

Everything in the game, and what it's still missing. **Generated:** don't edit this page. "Have" is read from the game's data files, so it's always up to date. "Wanted" comes from [`wanted.json`](../wanted.json): to claim a row, open a pull request that sets its `status` to `in_progress` with your name in `who`. When your addition is merged, delete its row. Run `python3 tools/catalogue.py` to rebuild this page.

How to add each kind of thing: [CONTRIBUTING.md](../CONTRIBUTING.md). How it should look: [ART.md](../ART.md).

|  | Have | Wanted | In progress |
|---|---|---|---|
| Animals | 16 | 1 | 0 |
| Plants | 7 | 13 | 0 |
| Trees | 5 | 0 | 0 |
| Foods | 10 | 3 | 0 |

## Animals

### Have

| Animal | Lives in | Model | Year | Baby start | Field guide |
|---|---|---|---|---|---|
| **Bumblebee** (*Bombus lucorum*) | fi_nuuksio | built from a spec [preview](../models/previews/bee.png) | yes | no | yes |
| **Bream** (*Abramis brama*) | fi_nuuksio | built from a spec [preview](../models/previews/bream.png) | yes | no | yes |
| **Chaffinch** (*Fringilla coelebs*) | fi_nuuksio | built from a spec [preview](../models/previews/chaffinch.png) | yes | no | yes |
| **Fox** (*Vulpes vulpes*) | fi_nuuksio | built from a spec [preview](../models/previews/fox.png) | yes | yes | yes |
| **Common frog** (*Rana temporaria*) | fi_nuuksio | built from a spec [preview](../models/previews/frog.png) | yes | no | yes |
| **Kestrel** (*Falco tinnunculus*) | fi_nuuksio | built from a spec [preview](../models/previews/kestrel.png) | yes | no | yes |
| **Common lizard** (*Zootoca vivipara*) | fi_nuuksio | built from a spec [preview](../models/previews/lizard.png) | yes | no | yes |
| **Moose** (*Alces alces*) | fi_nuuksio | built from a spec [preview](../models/previews/moose.png) | yes | no | yes |
| **Perch** (*Perca fluviatilis*) | fi_nuuksio | built from a spec [preview](../models/previews/perch.png) | yes | no | yes |
| **Pike** (*Esox lucius*) | fi_nuuksio | built from a spec [preview](../models/previews/pike.png) | yes | no | yes |
| **Rabbit** (*Oryctolagus cuniculus*) | fi_nuuksio | built from a spec [preview](../models/previews/rabbit.png) | yes | no | yes |
| **Roach** (*Rutilus rutilus*) | fi_nuuksio | built from a spec [preview](../models/previews/roach.png) | yes | no | yes |
| **Red squirrel** (*Sciurus vulgaris*) | fi_nuuksio | built from a spec [preview](../models/previews/squirrel.png) | yes | no | yes |
| **Bank vole** (*Myodes glareolus*) | fi_nuuksio | built from a spec [preview](../models/previews/vole.png) | yes | no | yes |
| **Young perch** (*Perca fluviatilis*) | fi_nuuksio | downloaded: rebuild from a spec | yes | no | yes |
| **Young roach** (*Rutilus rutilus*) | fi_nuuksio | downloaded: rebuild from a spec | yes | no | yes |

### Wanted

| Animal | Place | Feeds | Needs | Status |
|---|---|---|---|---|
| **Mountain hare** (metsäjänis, *Lepus timidus*) | fi_nuuksio | Fox, later lynx and eagle owl | New model from a spec, with a white `winter` coat. It replaces the "rabbit": European rabbits don't live wild in Nuuksio (ART.md: real species only). | Wanted |
| **Night animals: bats and owls** (lepakot ja pöllöt) | fi_nuuksio |  | Code first: how night works has to be tested before the first night animal (decision 0014, open). See docs/animals-wanted.md. | Later |

## Plants

### Have

| Plant | Kind | Grows in | Leaves | Preview |
|---|---|---|---|---|
| **Bilberry** (*Vaccinium myrtillus*) | bush | fi_nuuksio | deciduous | [preview](../models/previews/plants/bilberry.png) |
| **Crowberry** (*Empetrum nigrum*) | bush | fi_nuuksio | evergreen | [preview](../models/previews/plants/crowberry.png) |
| **Fly agaric** (*Amanita muscaria*) | bush | fi_nuuksio | deciduous | [preview](../models/previews/plants/fly_agaric.png) |
| **Heather** (*Calluna vulgaris*) | bush | fi_nuuksio | evergreen | [preview](../models/previews/plants/heather.png) |
| **Lingonberry** (*Vaccinium vitis-idaea*) | bush | fi_nuuksio | evergreen | [preview](../models/previews/plants/lingonberry.png) |
| **Porcini** (*Boletus edulis*) | bush | fi_nuuksio | deciduous | [preview](../models/previews/plants/porcini.png) |
| **Wild raspberry** (*Rubus idaeus*) | bush | fi_nuuksio | deciduous | [preview](../models/previews/plants/wild_raspberry.png) |

### Wanted

| Plant | Place | Feeds | Needs | Status |
|---|---|---|---|---|
| **Red clover and white clover** (puna-apila, valkoapila, *Trifolium pratense*) | fi_nuuksio | Hare (`clover`: players are already told they ate clover), bumblebee | Data only for the look: meadows, roadsides, around old farms, not inside the forest. Two specs, one per species. Mark the flower heads `"nectar": true` so bees drink from them (models/README.md). | Wanted |
| **Wild carrot: check first** (porkkana, *Daucus carota*) | fi_nuuksio | Hare (`carrot`) | Rare in Finland, only a few places on the south coast, so it probably shouldn't be in Nuuksio. Decide with the core team whether to replace the `carrot` food with plants hares really eat there (grasses, herbs, willow twigs). | Check first |
| **Goat willow (as a shrub)** (raita, *Salix caprea*) | fi_nuuksio | Bumblebee (catkins are its first food, April–May), hare (twigs and bark in winter) | Data only for the shrub: forest edges, clearings, lake shores. Mark the catkins `"nectar": true` so bees drink from them (models/README.md). Code: winter browse for hares. | Wanted |
| **Wavy hair-grass** (metsälauha, *Avenella flexuosa*) | fi_nuuksio | Hare and voles (grass) | Data only, `kind: "ground"`. The commonest grass of dry forest floor. Could replace the generic grass tuft inside the forest. | Wanted |
| **Chanterelle** (kantarelli, *Cantharellus cibarius*) | fi_nuuksio | Squirrel (mushrooms) | Data only, `kind: "ground"`. Mossy spruce and mixed forest, July–September. | Wanted |
| **Fireweed** (maitohorsma, *Chamaenerion angustifolium*) | fi_nuuksio | Bumblebee (summer nectar), hare | Data only. Clearings, burnt and open ground, roadsides. Up to 1.5 m: pink spikes July–August (mark them `"nectar": true`), red leaves and white seed fluff in autumn. | Wanted |
| **Wood anemone** (valkovuokko, *Anemone nemorosa*) | fi_nuuksio | Early insects | Data only, `kind: "ground"`. Leafy groves and herb-rich spruce forest. White flowers in early May, gone by midsummer. | Wanted |
| **Reindeer lichen** (poronjäkälä, *Cladonia rangiferina*) | fi_nuuksio |  | Data only, `kind: "ground"`, `on: ["rock"]`. Pale grey-green mats on rocky pine hilltops, the same all year. | Wanted |
| **Red-stemmed feathermoss** (seinäsammal, *Pleurozium schreberi*) | fi_nuuksio | Nest lining for squirrels and birds | Data only, `kind: "ground"`. Green carpets under spruce, nearly everywhere. | Wanted |
| **Juniper** (kataja, *Juniperus communis*) | fi_nuuksio | Birds (berry-cones), later | Data only, `kind: "bush"`. Rocky pine heath and dry slopes. Evergreen; berry-cones take two years to ripen from green to blue-black. | Wanted |
| **Bracken** (sananjalka, *Pteridium aquilinum*) | fi_nuuksio |  | Data only, `kind: "bush"`. Spruce and mixed forest. Fronds unroll in late May, turn brown in autumn and die back in winter; long `leaf` shapes make the fronds. | Wanted |
| **Spiny wood fern** (metsäalvejuuri, *Dryopteris carthusiana*) | fi_nuuksio |  | Data only, `kind: "bush"`. Damp spruce forest. | Wanted |
| **Lily of the valley** (kielo, *Convallaria majalis*) | fi_nuuksio |  | Data only, `kind: "ground"`. Dry leafy groves and forest edges. White bells in June, poisonous red berries in autumn. Finland's national flower. | Wanted |
| **Peat moss** (rahkasammal, *Sphagnum*) | fi_nuuksio |  | Code first: bog ground in the terrain. | Later |
| **Cloudberry** (lakka, *Rubus chamaemorus*) | fi_nuuksio | Fox, birds | Code first: bog ground. Orange berries in July. | Later |
| **Labrador tea** (suopursu, *Rhododendron tomentosum*) | fi_nuuksio |  | Code first: bog ground. White flowers in June. | Later |
| **Hare's-tail cottongrass** (tupasvilla, *Eriophorum vaginatum*) | fi_nuuksio | Hare (early spring shoots) | Code first: bog ground. White fluffy heads in late May and June. | Later |

## Trees

Trees are still made in code, because animals climb them and hide in them. Ask the core team before starting one.

### Have

| Shape | Grows in | How |
|---|---|---|
| `birch` | fi_nuuksio | made in code |
| `pine` | fi_nuuksio | made in code |
| `round` | fi_nuuksio | made in code |
| `rowan` | fi_nuuksio | made in code |
| `spruce` | fi_nuuksio | made in code |

### Wanted

| Tree | Place | Feeds | Needs | Status |
|---|---|---|---|---|
| **Aspen, grey alder, goat willow as trees** (haapa, harmaaleppä, raita) | fi_nuuksio | Hare (bark and twigs), beaver later | Code: trees are still made in code. Trees as data recipes are undecided (decision 0013): measure first. | Later |

## Foods

What animals find to eat. A food name marked "grows there" has a plant you can see in that place; the others still need their plant (see Plants, Wanted).

### Have

| Food | Place | Real names | Eaten by |
|---|---|---|---|
| `clover` | fi_nuuksio | red clover, white clover | Rabbit, Bank vole |
| `berries` | fi_nuuksio | bilberries (grows there), lingonberries (grows there), wild raspberries (grows there), crowberries (grows there) | Fox, Moose, Red squirrel, Bank vole |
| `carrot` | fi_nuuksio | wild carrot | Rabbit |
| `insects` | fi_nuuksio | ground beetle, dung beetle, click beetle | Chaffinch, Fox, Common frog, Kestrel, Common lizard |
| `water_bugs` | fi_nuuksio | mayfly larvae, caddisfly larvae, water boatmen | Bream, Perch, Roach, Young perch, Young roach |
| `browse` | fi_nuuksio | birch leaves and twigs, willow twigs, aspen shoots, rowan leaves | Moose, Rabbit |
| `water_plants` | fi_nuuksio | pondweed, water lily leaves, water horsetail | Moose |
| `cones` | fi_nuuksio | spruce cones, pine cones | Red squirrel |
| `bottom_bugs` | fi_nuuksio | bloodworms, pond snails | Bream, Perch, Roach |
| `seeds` | fi_nuuksio | spruce seeds, pine seeds, birch seeds | Chaffinch |

### Wanted

| Food | Feeds | Needs | Status |
|---|---|---|---|
| **Bark, twigs and buds** (kuori, oksat, silmut) | Mountain hare (winter) | Twigs and buds exist now (`browse`, young trees) and the rabbit eats them. Still missing: bark gnawed from trees in deep snow (code: a food kind on tree trunks). | Wanted |
| **Carrion** (raato) | Fox (winter) | Code: a new food kind. | Wanted |
| **Grass and herbs** (heinä ja ruohot) | Hare (its main food in summer) | Code: a new food kind, grazing the meadow's grass tufts. Today a hare only finds clover and wild carrot. | Wanted |
| **Ducklings** (ankanpoikaset) | Pike (early summer), fox | New model and a duck family on the lake. Tag `small_bird`. | Later |

## Core team work

Code changes that more content depends on. These are for the core team; the data and models they unlock can be made before they're done.

| Area | Work | Why | Status |
|---|---|---|---|
| plants | **Remake the code-made ground cover as specs** | Grass tufts, stones, the four flowers (oxeye daisy, heather, harebell, tormentil), reeds, water lilies and pondweed then follow the same rules, art guide and seasons. The bee's flowers are tied to the bee's code, so they move last. | Wanted |
| plants | **Bog ground in the terrain** | Nuuksio has small bogs; bog plants need somewhere to grow. | Later |
| animals | **Swimming land animals** | A generated `swim` clip for every four-legged animal (dog paddle: short fast leg strokes, head up, tail trailing), played while it's in water, with a preview tile. Foxes, squirrels and hares really swim, but in the game they play their walk animation, so they look like they're walking on the lake bottom. | Wanted |
| animals | **Body-plan templates** | A starting spec per body plan (four-legged, bird, fish), so agents and contributors copy the closest one instead of starting from scratch. | Wanted |
| animals | **Swimming birds** | Ducks and grebes floating on the surface. No swimming birds yet. | Later |
| trees | **Trees as recipes** | So contributors can add tree species without code (decision 0013). Undecided: measure first. | Later |
| animals | **Stride and eating reach per animal** | Walk, run and eat use fixed angles. Long legs get huge strides (the moose needed `swing` 0.75), and a tall animal can't lower its head to the ground. Let a spec set stride length and how low or high it eats (a grazing hare, a browsing moose). | Wanted |
| animals | **Build report: body and separate parts** | The build prints one triangle total. Separate parts (antlers, fins, spots, eyes) share the budget, and the body never gets fewer than 200, so the budget can be silently exceeded or the body starved. Print the body and the separate parts separately, and warn at the minimum. | Wanted |
| animals | **Bird wings: fold and flap** | The default fold tips the wing out instead of down (roll is applied before yaw), folded wings stay as wide as spread ones, and the flap is a symmetric ±52° around the rest pose. Apply the tip-down tilt after the sweep, narrow folded wings, and make the downstroke shorter than the upstroke. | Wanted |
| animals | **Insect wingbeat that sweeps** | The bee's buzz flips the wings up and down every frame. Real insect wings sweep forward and back; up and down reads as a jittery V. | Later |
| animals | **Fish poses** | Fish use only idle and swim. The generated eat and sleep clips tip a fish over. A hovering idle, a slight head yaw against the tail while swimming, and resting near the bottom would suit fish better. | Later |
| animals | **A body that bends** | Curled-up sleep turns the head and wraps the tail, but the body is one straight bone. A short round animal (the bank vole) curls into a loaf rather than a ball, and the fox's curl stays a C. A spine of two or three body bones that bend in the curl pose would let them sleep in a real ball. | Wanted |
| animals | **A real hop** | Legs are one bone each, so a frog's folded hind legs can only rock as one piece: no kick that straightens them. Knee and ankle bones that unfold in the run clip would give frogs (and hares) a real hop. | Wanted |
| animals | **A lizard's walk** | Tails only wag sideways when idle, and legs swing around the left-right axis, which suits legs under the body. A lizard's legs stick out sideways and swing forward and back around an upright axis, and its body and tail wave side to side as it walks. | Wanted |
| animals | **Marks painted on the skin** | Spots, bars and masks have to be separate pieces (about 30 triangles each): melted into the body they fade or bulge. A frog spends 350 of its 600 triangles on marks. A way to colour a patch of the skin without changing its shape would leave the budget for the body. | Wanted |
