# Animundo catalogue

Everything in the game, and what it's still missing. **Generated:** don't edit this page. "Have" is read from the game's data files, so it's always up to date. "Wanted" comes from [`wanted.json`](../wanted.json): to claim a row, open a pull request that sets its `status` to `in_progress` with your name in `who`. When your addition is merged, delete its row. Run `python3 tools/catalogue.py` to rebuild this page.

How to add each kind of thing: [CONTRIBUTING.md](../CONTRIBUTING.md). How it should look: [ART.md](../ART.md).

|  | Have | Wanted | In progress |
|---|---|---|---|
| Animals | 9 | 6 | 0 |
| Plants | 5 | 15 | 0 |
| Trees | 5 | 0 | 0 |
| Foods | 5 | 4 | 0 |

## Animals

### Have

| Animal | Lives in | Model | Year | Baby start | Field guide |
|---|---|---|---|---|---|
| **Bumblebee** (*Bombus lucorum*) | fi_nuuksio | built from a spec [preview](../models/previews/bee.png) | yes | no | yes |
| **Bream** (*Abramis brama*) | fi_nuuksio | built from a spec [preview](../models/previews/bream.png) | yes | no | yes |
| **Fox** (*Vulpes vulpes*) | fi_nuuksio | built from a spec [preview](../models/previews/fox.png) | yes | yes | yes |
| **Kestrel** (*Falco tinnunculus*) | fi_nuuksio | built from a spec [preview](../models/previews/kestrel.png) | yes | no | yes |
| **Perch** (*Perca fluviatilis*) | fi_nuuksio | built from a spec [preview](../models/previews/perch.png) | yes | no | yes |
| **Pike** (*Esox lucius*) | fi_nuuksio | built from a spec [preview](../models/previews/pike.png) | yes | no | yes |
| **Rabbit** (*Oryctolagus cuniculus*) | fi_nuuksio | built from a spec [preview](../models/previews/rabbit.png) | yes | no | yes |
| **Roach** (*Rutilus rutilus*) | fi_nuuksio | built from a spec [preview](../models/previews/roach.png) | yes | no | yes |
| **Red squirrel** (*Sciurus vulgaris*) | fi_nuuksio | built from a spec [preview](../models/previews/squirrel.png) | yes | no | yes |

### Wanted

| Animal | Place | Feeds | Needs | Status |
|---|---|---|---|---|
| **Bank vole** (metsämyyrä, *Myodes glareolus*) | fi_nuuksio | Fox (its main food all year), kestrel (its main food), owls later | New model. Tags `small_mammal`, `vole`; the kestrel then `hunts: ["vole"]`. Code: wild prey that isn't a rabbit (`prey.gd` only makes rabbits), and a kestrel that hovers and drops onto prey. | Wanted |
| **Mountain hare** (metsäjänis, *Lepus timidus*) | fi_nuuksio | Fox, later lynx and eagle owl | New model from a spec, with a white `winter` coat. It replaces the "rabbit": European rabbits don't live wild in Nuuksio (ART.md: real species only). | Wanted |
| **Young perch and young roach** (ahvenen ja särjen poikaset) | fi_nuuksio | Perch (its main food from summer on: perch eat small fish, even young perch), pike | No new model: the perch and roach models at baby size, from the baby stage (decision 0010). Tag `fry`; the perch then `hunts: ["fry"]`. Code: hunters only catch prey much smaller than themselves, and the player's fish can chase fish. | Wanted |
| **Common frog** (sammakko, *Rana temporaria*) | fi_nuuksio | Pike (spring), fox, later heron | New model. Code: an animal that lives on land and in water (a new archetype). | Wanted |
| **Common lizard** (sisilisko, *Zootoca vivipara*) | fi_nuuksio | Kestrel (summer) | New model. Cold-blooded, basks on sunny rocks. | Wanted |
| **Chaffinch, with eggs and nestlings** (peippo, *Fringilla coelebs*) | fi_nuuksio | Fox (spring: birds and eggs), later sparrowhawk | New model. Tag `small_bird`. Code: nests with eggs and young. | Wanted |
| **Night animals: bats and owls** (lepakot ja pöllöt) | fi_nuuksio |  | Code first: how night works has to be tested before the first night animal (decision 0014, open). See docs/animals-wanted.md. | Later |

## Plants

### Have

| Plant | Kind | Grows in | Leaves | Preview |
|---|---|---|---|---|
| **Bilberry** (*Vaccinium myrtillus*) | bush | fi_nuuksio | deciduous | [preview](../models/previews/plants/bilberry.png) |
| **Fly agaric** (*Amanita muscaria*) | bush | fi_nuuksio | deciduous | [preview](../models/previews/plants/fly_agaric.png) |
| **Heather** (*Calluna vulgaris*) | bush | fi_nuuksio | evergreen | [preview](../models/previews/plants/heather.png) |
| **Lingonberry** (*Vaccinium vitis-idaea*) | bush | fi_nuuksio | evergreen | [preview](../models/previews/plants/lingonberry.png) |
| **Porcini** (*Boletus edulis*) | bush | fi_nuuksio | deciduous | [preview](../models/previews/plants/porcini.png) |

### Wanted

| Plant | Place | Feeds | Needs | Status |
|---|---|---|---|---|
| **Wild raspberry** (vadelma, *Rubus idaeus*) | fi_nuuksio | Fox, squirrel (`berries`: players are already told they ate wild raspberries) | Data only. Clearings, forest edges, old fields. About 1–1.5 m of upright canes, `kind: "bush"`. White flowers in June, red berries July–August. | Wanted |
| **Crowberry** (variksenmarja, *Empetrum nigrum*) | fi_nuuksio | Fox, squirrel (`berries`: players are already told they ate crowberries), later birds | Data only. Rocky hilltops and pine heath with heather (`on: ["grass", "rock"]`). A low evergreen mat; black berries from August that stay into winter. | Wanted |
| **Red clover and white clover** (puna-apila, valkoapila, *Trifolium pratense*) | fi_nuuksio | Hare (`clover`: players are already told they ate clover), bumblebee | Data only for the look: meadows, roadsides, around old farms, not inside the forest. Two specs, one per species. Code to be the bee's flowers (see core team work). | Wanted |
| **Wild carrot: check first** (porkkana, *Daucus carota*) | fi_nuuksio | Hare (`carrot`) | Rare in Finland, only a few places on the south coast, so it probably shouldn't be in Nuuksio. Decide with the core team whether to replace the `carrot` food with plants hares really eat there (grasses, herbs, willow twigs). | Check first |
| **Goat willow (as a shrub)** (raita, *Salix caprea*) | fi_nuuksio | Bumblebee (catkins are its first food, April–May), hare (twigs and bark in winter) | Data only for the shrub: forest edges, clearings, lake shores. Code: bee food from a plant, and winter browse for hares. | Wanted |
| **Wavy hair-grass** (metsälauha, *Avenella flexuosa*) | fi_nuuksio | Hare and voles (grass) | Data only, `kind: "ground"`. The commonest grass of dry forest floor. Could replace the generic grass tuft inside the forest. | Wanted |
| **Chanterelle** (kantarelli, *Cantharellus cibarius*) | fi_nuuksio | Squirrel (mushrooms) | Data only, `kind: "ground"`. Mossy spruce and mixed forest, July–September. | Wanted |
| **Fireweed** (maitohorsma, *Chamaenerion angustifolium*) | fi_nuuksio | Bumblebee (summer nectar), hare | Data only. Clearings, burnt and open ground, roadsides. Up to 1.5 m: pink spikes July–August, red leaves and white seed fluff in autumn. | Wanted |
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
| `clover` | fi_nuuksio | red clover, white clover | Rabbit |
| `berries` | fi_nuuksio | bilberries (grows there), lingonberries (grows there), wild raspberries, crowberries | Fox, Red squirrel |
| `carrot` | fi_nuuksio | wild carrot | Rabbit |
| `insects` | fi_nuuksio | ground beetle, dung beetle, click beetle | Kestrel |
| `water_bugs` | fi_nuuksio | mayfly larvae, caddisfly larvae, water boatmen | Bream, Perch, Roach |

### Wanted

| Food | Feeds | Needs | Status |
|---|---|---|---|
| **Spruce cones and seeds** (kuusenkävyt) | Squirrel (its main food autumn to spring) | Code: a new food kind. | Wanted |
| **Mushrooms** (sienet) | Squirrel (summer and autumn; it dries them on branches) | Code: a new food kind that uses the mushroom plants. | Wanted |
| **Bark, twigs and buds** (kuori, oksat, silmut) | Mountain hare (winter) | Code: a new food kind. | Wanted |
| **Carrion** (raato) | Fox (winter) | Code: a new food kind. | Wanted |

## Core team work

Code changes that more content depends on. These are for the core team; the data and models they unlock can be made before they're done.

| Area | Work | Why | Status |
|---|---|---|---|
| plants | **Remake the code-made ground cover as specs** | Grass tufts, stones, the four flowers (oxeye daisy, heather, harebell, tormentil), reeds, water lilies and pondweed then follow the same rules, art guide and seasons. The bee's flowers are tied to the bee's code, so they move last. | Wanted |
| plants | **Bee flowers from plant specs** | A plant part (bilberry flowers, clover, willow catkins, heather spikes) counts as a flower a bee can drink from while it's shown. Bilberry flowers and willow catkins are the bumblebee's real spring food. | Wanted |
| plants | **Food on real plants** | A berry food spot uses the plant model (a bilberry with berries) instead of a box, and only has berries while the plant does. | Wanted |
| plants | **Bog ground in the terrain** | Nuuksio has small bogs; bog plants need somewhere to grow. | Later |
| animals | **Swimming land animals** | A generated `swim` clip for every four-legged animal (dog paddle: short fast leg strokes, head up, tail trailing), played while it's in water, with a preview tile. Foxes, squirrels and hares really swim, but in the game they play their walk animation, so they look like they're walking on the lake bottom. | Wanted |
| animals | **Body-plan templates** | A starting spec per body plan (four-legged, bird, fish), so agents and contributors copy the closest one instead of starting from scratch. | Wanted |
| animals | **Swimming birds** | Ducks and grebes floating on the surface. No swimming birds yet. | Later |
| trees | **Trees as recipes** | So contributors can add tree species without code (decision 0013). Undecided: measure first. | Later |
