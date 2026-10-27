#!/usr/bin/env python3
"""The animal list: the animals a grown-up can ask for in Animundo Builder.

Animal first (spec 04, inbox #40): the builder's first screen asks "Which animal
would you like to be?" and matches the typed text, in the browser, against this
list. Each entry says what we start its model from (a reference model from the
table in models/README.md), the habitats it lives in (each one a home in
homes/ once that home exists), and whether we can make it yet.

The table below is the source. This tool writes animal-list.json from it:

    python3 tools/animal_list.py           # resolve GBIF IDs (needs network), write animal-list.json
    python3 tools/animal_list.py --check   # offline: animal-list.json matches the table and the library

An animal already in animals/ uses that file's GBIF ID and is marked `in_library`.
"""
import argparse
import glob
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "animal-list.json")
API = "https://api.gbif.org/v1/species/match"

HABITATS = {
    "boreal_forest", "boreal_lake",  # the northern forest and its lakes: homes/ has these first
    "forest", "lake", "river", "wetland", "mountain", "tundra", "ice", "sea", "reef",
    "mangrove", "grassland", "savanna", "desert", "rainforest",
}
# why an animal can't be made yet: the web app has an English sentence for each
NOT_YET = {
    "bats": "Bats fly with their arms, and night animals come later.",
    "great_whales": "Great whales are bigger than any place's sea.",
    "dragonflies": "Dragonflies beat two pairs of wings apart.",
    "body_plan": "Animundo can't make this kind of body yet.",
}

# id, English name, latin name, start from (reference model), habitats, not yet (None: we can make it)
TABLE = [
    # already in the library
    ("fox", "Red fox", "Vulpes vulpes", "fox", ["boreal_forest", "grassland", "mountain"], None),
    ("moose", "Moose", "Alces alces", "moose", ["boreal_forest", "boreal_lake", "wetland"], None),
    ("mountain_hare", "Mountain hare", "Lepus timidus", "mountain_hare", ["boreal_forest", "tundra", "mountain"], None),
    ("squirrel", "Red squirrel", "Sciurus vulgaris", "squirrel", ["boreal_forest"], None),
    ("flying_squirrel", "Siberian flying squirrel", "Pteromys volans", "flying_squirrel", ["boreal_forest"], None),
    ("vole", "Bank vole", "Myodes glareolus", "vole", ["boreal_forest"], None),
    ("saimaa_seal", "Saimaa ringed seal", "Pusa hispida saimensis", "saimaa_seal", ["boreal_lake"], None),
    ("kestrel", "Common kestrel", "Falco tinnunculus", "kestrel", ["grassland", "boreal_forest"], None),
    ("great_tit", "Great tit", "Parus major", "great_tit", ["boreal_forest"], None),
    ("chaffinch", "Common chaffinch", "Fringilla coelebs", "chaffinch", ["boreal_forest"], None),
    ("mallard", "Mallard", "Anas platyrhynchos", "mallard", ["boreal_lake", "river", "wetland"], None),
    ("frog", "Common frog", "Rana temporaria", "frog", ["boreal_forest", "boreal_lake", "wetland"], None),
    ("lizard", "Viviparous lizard", "Zootoca vivipara", "lizard", ["boreal_forest", "wetland"], None),
    ("bee", "Buff-tailed bumblebee", "Bombus lucorum", "bee", ["boreal_forest", "grassland"], None),
    ("perch", "European perch", "Perca fluviatilis", "perch", ["boreal_lake", "river"], None),
    ("pike", "Northern pike", "Esox lucius", "pike", ["boreal_lake", "river"], None),
    ("roach", "Roach", "Rutilus rutilus", "roach", ["boreal_lake", "river"], None),
    ("bream", "Common bream", "Abramis brama", "bream", ["boreal_lake", "river"], None),
    # northern forests and lakes
    ("lynx", "Eurasian lynx", "Lynx lynx", "fox", ["boreal_forest", "mountain"], None),
    ("wolf", "Grey wolf", "Canis lupus", "fox", ["boreal_forest", "tundra", "mountain"], None),
    ("brown_bear", "Brown bear", "Ursus arctos", "fox", ["boreal_forest", "mountain"], None),
    ("wolverine", "Wolverine", "Gulo gulo", "fox", ["boreal_forest", "tundra", "mountain"], None),
    ("pine_marten", "Pine marten", "Martes martes", "fox", ["boreal_forest"], None),
    ("otter", "Eurasian otter", "Lutra lutra", "fox", ["boreal_lake", "river"], None),
    ("badger", "European badger", "Meles meles", "fox", ["boreal_forest", "grassland"], None),
    ("stoat", "Stoat", "Mustela erminea", "fox", ["boreal_forest", "tundra", "grassland"], None),
    ("raccoon_dog", "Raccoon dog", "Nyctereutes procyonoides", "fox", ["boreal_forest", "wetland"], None),
    ("beaver", "Eurasian beaver", "Castor fiber", "vole", ["boreal_lake", "river"], None),
    ("reindeer", "Reindeer (caribou)", "Rangifer tarandus", "moose", ["tundra", "boreal_forest"], None),
    ("red_deer", "Red deer", "Cervus elaphus", "moose", ["boreal_forest", "grassland", "mountain"], None),
    ("roe_deer", "Roe deer", "Capreolus capreolus", "moose", ["boreal_forest", "grassland"], None),
    ("white_tailed_deer", "White-tailed deer", "Odocoileus virginianus", "moose", ["boreal_forest"], None),
    ("wild_boar", "Wild boar", "Sus scrofa", "moose", ["boreal_forest"], None),
    ("hedgehog", "European hedgehog", "Erinaceus europaeus", "vole", ["boreal_forest", "grassland"], None),
    ("brown_hare", "European hare", "Lepus europaeus", "mountain_hare", ["grassland"], None),
    ("rabbit", "European rabbit", "Oryctolagus cuniculus", "mountain_hare", ["grassland"], None),
    ("lemming", "Norway lemming", "Lemmus lemmus", "vole", ["tundra", "mountain"], None),
    ("shrew", "Common shrew", "Sorex araneus", "vole", ["boreal_forest", "grassland"], None),
    ("wood_mouse", "Wood mouse", "Apodemus sylvaticus", "vole", ["boreal_forest", "grassland"], None),
    ("muskrat", "Muskrat", "Ondatra zibethicus", "vole", ["boreal_lake", "wetland", "river"], None),
    ("grey_seal", "Grey seal", "Halichoerus grypus", "saimaa_seal", ["sea"], None),
    ("harbour_seal", "Harbour seal", "Phoca vitulina", "saimaa_seal", ["sea"], None),
    ("ural_owl", "Ural owl", "Strix uralensis", "kestrel", ["boreal_forest"], None),
    ("snowy_owl", "Snowy owl", "Bubo scandiacus", "kestrel", ["tundra"], None),
    ("eagle_owl", "Eurasian eagle-owl", "Bubo bubo", "kestrel", ["boreal_forest", "mountain"], None),
    ("golden_eagle", "Golden eagle", "Aquila chrysaetos", "kestrel", ["mountain", "boreal_forest"], None),
    ("white_tailed_eagle", "White-tailed eagle", "Haliaeetus albicilla", "kestrel", ["boreal_lake", "sea"], None),
    ("osprey", "Osprey", "Pandion haliaetus", "kestrel", ["boreal_lake", "river"], None),
    ("buzzard", "Common buzzard", "Buteo buteo", "kestrel", ["boreal_forest", "grassland"], None),
    ("goshawk", "Northern goshawk", "Accipiter gentilis", "kestrel", ["boreal_forest"], None),
    ("peregrine", "Peregrine falcon", "Falco peregrinus", "kestrel", ["mountain", "grassland"], None),
    ("raven", "Common raven", "Corvus corax", "great_tit", ["boreal_forest", "mountain"], None),
    ("magpie", "Eurasian magpie", "Pica pica", "great_tit", ["grassland", "boreal_forest"], None),
    ("jay", "Eurasian jay", "Garrulus glandarius", "great_tit", ["boreal_forest"], None),
    ("robin", "European robin", "Erithacus rubecula", "great_tit", ["boreal_forest"], None),
    ("blue_tit", "Blue tit", "Cyanistes caeruleus", "great_tit", ["boreal_forest"], None),
    ("bullfinch", "Eurasian bullfinch", "Pyrrhula pyrrhula", "chaffinch", ["boreal_forest"], None),
    ("blackbird", "Common blackbird", "Turdus merula", "great_tit", ["boreal_forest"], None),
    ("swallow", "Barn swallow", "Hirundo rustica", "great_tit", ["grassland", "boreal_lake"], None),
    ("great_spotted_woodpecker", "Great spotted woodpecker", "Dendrocopos major", "great_tit", ["boreal_forest"], None),
    ("black_woodpecker", "Black woodpecker", "Dryocopus martius", "great_tit", ["boreal_forest"], None),
    ("crossbill", "Common crossbill", "Loxia curvirostra", "chaffinch", ["boreal_forest"], None),
    ("waxwing", "Bohemian waxwing", "Bombycilla garrulus", "chaffinch", ["boreal_forest"], None),
    ("cuckoo", "Common cuckoo", "Cuculus canorus", "great_tit", ["boreal_forest"], None),
    ("capercaillie", "Western capercaillie", "Tetrao urogallus", "mallard", ["boreal_forest"], None),
    ("black_grouse", "Black grouse", "Lyrurus tetrix", "mallard", ["boreal_forest", "wetland"], None),
    ("ptarmigan", "Rock ptarmigan", "Lagopus muta", "mallard", ["tundra", "mountain"], None),
    ("whooper_swan", "Whooper swan", "Cygnus cygnus", "mallard", ["boreal_lake", "wetland"], None),
    ("mute_swan", "Mute swan", "Cygnus olor", "mallard", ["boreal_lake", "river"], None),
    ("canada_goose", "Canada goose", "Branta canadensis", "mallard", ["boreal_lake", "grassland"], None),
    ("goldeneye", "Common goldeneye", "Bucephala clangula", "mallard", ["boreal_lake"], None),
    ("black_throated_loon", "Black-throated loon", "Gavia arctica", "mallard", ["boreal_lake"], None),
    ("common_crane", "Common crane", "Grus grus", "mallard", ["wetland", "grassland"], None),
    ("grey_heron", "Grey heron", "Ardea cinerea", "mallard", ["boreal_lake", "river", "wetland"], None),
    ("white_stork", "White stork", "Ciconia ciconia", "mallard", ["wetland", "grassland"], None),
    ("common_tern", "Common tern", "Sterna hirundo", "mallard", ["boreal_lake", "sea"], None),
    ("herring_gull", "Herring gull", "Larus argentatus", "mallard", ["sea", "boreal_lake"], None),
    ("kingfisher", "Common kingfisher", "Alcedo atthis", "great_tit", ["river", "boreal_lake"], None),
    ("dipper", "White-throated dipper", "Cinclus cinclus", "great_tit", ["river", "mountain"], None),
    ("atlantic_salmon", "Atlantic salmon", "Salmo salar", "pike", ["river", "sea"], None),
    ("brown_trout", "Brown trout", "Salmo trutta", "pike", ["river", "boreal_lake"], None),
    ("arctic_char", "Arctic char", "Salvelinus alpinus", "pike", ["boreal_lake"], None),
    ("zander", "Zander", "Sander lucioperca", "pike", ["boreal_lake"], None),
    ("burbot", "Burbot", "Lota lota", "pike", ["boreal_lake", "river"], None),
    ("eel", "European eel", "Anguilla anguilla", "grass_snake", ["river", "boreal_lake", "sea"], None),
    ("common_toad", "Common toad", "Bufo bufo", "frog", ["boreal_forest", "wetland"], None),
    ("moor_frog", "Moor frog", "Rana arvalis", "frog", ["wetland", "boreal_lake"], None),
    ("smooth_newt", "Smooth newt", "Lissotriton vulgaris", "lizard", ["boreal_lake", "wetland"], None),
    ("adder", "Common European adder", "Vipera berus", "grass_snake", ["boreal_forest", "wetland"], None),
    ("grass_snake", "Grass snake", "Natrix natrix", "grass_snake", ["boreal_lake", "wetland"], None),
    ("slow_worm", "Slow worm", "Anguis fragilis", "grass_snake", ["boreal_forest", "grassland"], None),
    ("sand_lizard", "Sand lizard", "Lacerta agilis", "lizard", ["grassland"], None),
    ("honey_bee", "Western honey bee", "Apis mellifera", "bee", ["grassland", "boreal_forest"], None),
    ("wasp", "Common wasp", "Vespula vulgaris", "bee", ["boreal_forest", "grassland"], None),
    ("peacock_butterfly", "Peacock butterfly", "Aglais io", "peacock_butterfly", ["grassland", "boreal_forest"], None),
    ("brimstone", "Common brimstone", "Gonepteryx rhamni", "peacock_butterfly", ["boreal_forest", "grassland"], None),
    ("swallowtail", "Old World swallowtail", "Papilio machaon", "peacock_butterfly", ["grassland"], None),
    ("small_tortoiseshell", "Small tortoiseshell", "Aglais urticae", "peacock_butterfly", ["grassland"], None),
    # mountains, tundra and ice
    ("arctic_fox", "Arctic fox", "Vulpes lagopus", "fox", ["tundra", "ice"], None),
    ("polar_bear", "Polar bear", "Ursus maritimus", "fox", ["ice", "sea"], None),
    ("musk_ox", "Muskox", "Ovibos moschatus", "moose", ["tundra"], None),
    ("ibex", "Alpine ibex", "Capra ibex", "moose", ["mountain"], None),
    ("chamois", "Chamois", "Rupicapra rupicapra", "moose", ["mountain"], None),
    ("mountain_goat", "Mountain goat", "Oreamnos americanus", "moose", ["mountain"], None),
    ("bighorn_sheep", "Bighorn sheep", "Ovis canadensis", "moose", ["mountain"], None),
    ("snow_leopard", "Snow leopard", "Panthera uncia", "fox", ["mountain"], None),
    ("marmot", "Alpine marmot", "Marmota marmota", "squirrel", ["mountain"], None),
    ("pika", "American pika", "Ochotona princeps", "mountain_hare", ["mountain"], None),
    ("walrus", "Walrus", "Odobenus rosmarus", "saimaa_seal", ["ice", "sea"], None),
    ("ringed_seal", "Ringed seal", "Pusa hispida", "saimaa_seal", ["ice", "sea"], None),
    ("harp_seal", "Harp seal", "Pagophilus groenlandicus", "saimaa_seal", ["ice", "sea"], None),
    ("emperor_penguin", "Emperor penguin", "Aptenodytes forsteri", "mallard", ["ice", "sea"], None),
    ("king_penguin", "King penguin", "Aptenodytes patagonicus", "mallard", ["ice", "sea"], None),
    ("puffin", "Atlantic puffin", "Fratercula arctica", "mallard", ["sea"], None),
    ("snow_bunting", "Snow bunting", "Plectrophenax nivalis", "chaffinch", ["tundra"], None),
    ("arctic_tern", "Arctic tern", "Sterna paradisaea", "mallard", ["sea", "tundra"], None),
    ("snowshoe_hare", "Snowshoe hare", "Lepus americanus", "mountain_hare", ["boreal_forest"], None),
    # seas and coasts
    ("harbour_porpoise", "Harbour porpoise", "Phocoena phocoena", "harbour_porpoise", ["sea"], None),
    ("bottlenose_dolphin", "Bottlenose dolphin", "Tursiops truncatus", "harbour_porpoise", ["sea"], None),
    ("orca", "Orca", "Orcinus orca", "harbour_porpoise", ["sea"], None),
    ("beluga", "Beluga whale", "Delphinapterus leucas", "harbour_porpoise", ["sea", "ice"], None),
    ("narwhal", "Narwhal", "Monodon monoceros", "harbour_porpoise", ["sea", "ice"], None),
    ("blue_whale", "Blue whale", "Balaenoptera musculus", "harbour_porpoise", ["sea"], "great_whales"),
    ("humpback_whale", "Humpback whale", "Megaptera novaeangliae", "harbour_porpoise", ["sea"], "great_whales"),
    ("sperm_whale", "Sperm whale", "Physeter macrocephalus", "harbour_porpoise", ["sea"], "great_whales"),
    ("sea_otter", "Sea otter", "Enhydra lutris", "fox", ["sea"], None),
    ("sea_lion", "California sea lion", "Zalophus californianus", "saimaa_seal", ["sea"], None),
    ("great_white_shark", "Great white shark", "Carcharodon carcharias", "pike", ["sea"], None),
    ("hammerhead", "Scalloped hammerhead", "Sphyrna lewini", "pike", ["sea", "reef"], None),
    ("whale_shark", "Whale shark", "Rhincodon typus", "pike", ["sea"], "great_whales"),
    ("manta_ray", "Giant manta ray", "Mobula birostris", None, ["sea", "reef"], "body_plan"),
    ("atlantic_cod", "Atlantic cod", "Gadus morhua", "pike", ["sea"], None),
    ("herring", "Atlantic herring", "Clupea harengus", "roach", ["sea"], None),
    ("mackerel", "Atlantic mackerel", "Scomber scombrus", "pike", ["sea"], None),
    ("tuna", "Atlantic bluefin tuna", "Thunnus thynnus", "perch", ["sea"], None),
    ("swordfish", "Swordfish", "Xiphias gladius", "pike", ["sea"], None),
    ("moray_eel", "Green moray", "Gymnothorax funebris", "grass_snake", ["reef"], None),
    ("octopus", "Common octopus", "Octopus vulgaris", None, ["sea", "reef"], "body_plan"),
    ("jellyfish", "Moon jellyfish", "Aurelia aurita", None, ["sea"], "body_plan"),
    ("starfish", "Common starfish", "Asterias rubens", None, ["sea"], "body_plan"),
    ("crab", "Shore crab", "Carcinus maenas", None, ["sea"], "body_plan"),
    ("lobster", "European lobster", "Homarus gammarus", None, ["sea"], "body_plan"),
    ("seahorse", "Long-snouted seahorse", "Hippocampus guttulatus", None, ["sea", "reef"], "body_plan"),
    ("green_sea_turtle", "Green sea turtle", "Chelonia mydas", None, ["sea", "reef"], "body_plan"),
    # coral reefs
    ("clownfish", "Orange clownfish", "Amphiprion percula", "perch", ["reef"], None),
    ("blue_tang", "Blue tang", "Paracanthurus hepatus", "bream", ["reef"], None),
    ("parrotfish", "Stoplight parrotfish", "Sparisoma viride", "perch", ["reef"], None),
    ("butterflyfish", "Threadfin butterflyfish", "Chaetodon auriga", "bream", ["reef"], None),
    ("lionfish", "Red lionfish", "Pterois volitans", "perch", ["reef"], None),
    ("reef_shark", "Blacktip reef shark", "Carcharhinus melanopterus", "pike", ["reef"], None),
    # grasslands and savannas
    ("lion", "Lion", "Panthera leo", "fox", ["savanna", "grassland"], None),
    ("cheetah", "Cheetah", "Acinonyx jubatus", "fox", ["savanna", "grassland"], None),
    ("leopard", "Leopard", "Panthera pardus", "fox", ["savanna", "forest", "rainforest"], None),
    ("hyena", "Spotted hyena", "Crocuta crocuta", "fox", ["savanna"], None),
    ("african_wild_dog", "African wild dog", "Lycaon pictus", "fox", ["savanna"], None),
    ("zebra", "Plains zebra", "Equus quagga", "moose", ["savanna", "grassland"], None),
    ("giraffe", "Giraffe", "Giraffa camelopardalis", "moose", ["savanna"], None),
    ("african_elephant", "African elephant", "Loxodonta africana", None, ["savanna"], "body_plan"),
    ("asian_elephant", "Asian elephant", "Elephas maximus", None, ["forest", "rainforest"], "body_plan"),
    ("rhino", "White rhinoceros", "Ceratotherium simum", "moose", ["savanna"], None),
    ("hippo", "Hippopotamus", "Hippopotamus amphibius", "moose", ["river", "savanna"], None),
    ("wildebeest", "Blue wildebeest", "Connochaetes taurinus", "moose", ["savanna"], None),
    ("gazelle", "Thomson's gazelle", "Eudorcas thomsonii", "moose", ["savanna"], None),
    ("impala", "Impala", "Aepyceros melampus", "moose", ["savanna"], None),
    ("warthog", "Common warthog", "Phacochoerus africanus", "moose", ["savanna"], None),
    ("meerkat", "Meerkat", "Suricata suricatta", "squirrel", ["desert", "savanna"], None),
    ("ostrich", "Common ostrich", "Struthio camelus", None, ["savanna", "desert"], "body_plan"),
    ("bison", "American bison", "Bison bison", "moose", ["grassland"], None),
    ("pronghorn", "Pronghorn", "Antilocapra americana", "moose", ["grassland"], None),
    ("prairie_dog", "Black-tailed prairie dog", "Cynomys ludovicianus", "squirrel", ["grassland"], None),
    ("coyote", "Coyote", "Canis latrans", "fox", ["grassland", "desert", "forest"], None),
    ("kangaroo", "Red kangaroo", "Osphranter rufus", "mountain_hare", ["grassland", "desert"], None),
    ("wombat", "Common wombat", "Vombatus ursinus", "vole", ["forest", "grassland"], None),
    ("emu", "Emu", "Dromaius novaehollandiae", None, ["grassland"], "body_plan"),
    ("horse", "Przewalski's horse", "Equus ferus", "moose", ["grassland"], None),
    # deserts
    ("camel", "Dromedary", "Camelus dromedarius", "moose", ["desert"], None),
    ("fennec_fox", "Fennec fox", "Vulpes zerda", "fox", ["desert"], None),
    ("jerboa", "Lesser Egyptian jerboa", "Jaculus jaculus", "mountain_hare", ["desert"], None),
    ("roadrunner", "Greater roadrunner", "Geococcyx californianus", "mallard", ["desert"], None),
    ("rattlesnake", "Western diamondback rattlesnake", "Crotalus atrox", "grass_snake", ["desert"], None),
    ("gila_monster", "Gila monster", "Heloderma suspectum", "lizard", ["desert"], None),
    ("thorny_devil", "Thorny devil", "Moloch horridus", "lizard", ["desert"], None),
    # rainforests and mangroves
    ("jaguar", "Jaguar", "Panthera onca", "fox", ["rainforest"], None),
    ("tiger", "Tiger", "Panthera tigris", "fox", ["forest", "rainforest", "mangrove"], None),
    ("tapir", "Lowland tapir", "Tapirus terrestris", "moose", ["rainforest"], None),
    ("capybara", "Capybara", "Hydrochoerus hydrochaeris", "vole", ["rainforest", "wetland", "river"], None),
    ("giant_anteater", "Giant anteater", "Myrmecophaga tridactyla", "fox", ["grassland", "rainforest"], None),
    ("okapi", "Okapi", "Okapia johnstoni", "moose", ["rainforest"], None),
    ("red_panda", "Red panda", "Ailurus fulgens", "fox", ["forest", "mountain"], None),
    ("giant_panda", "Giant panda", "Ailuropoda melanoleuca", "fox", ["forest", "mountain"], None),
    ("sun_bear", "Sun bear", "Helarctos malayanus", "fox", ["rainforest"], None),
    ("orangutan", "Bornean orangutan", "Pongo pygmaeus", None, ["rainforest"], "body_plan"),
    ("chimpanzee", "Chimpanzee", "Pan troglodytes", None, ["rainforest"], "body_plan"),
    ("gorilla", "Western gorilla", "Gorilla gorilla", None, ["rainforest"], "body_plan"),
    ("ring_tailed_lemur", "Ring-tailed lemur", "Lemur catta", None, ["forest"], "body_plan"),
    ("sloth", "Brown-throated sloth", "Bradypus variegatus", None, ["rainforest"], "body_plan"),
    ("koala", "Koala", "Phascolarctos cinereus", None, ["forest"], "body_plan"),
    ("toucan", "Toco toucan", "Ramphastos toco", "great_tit", ["rainforest"], None),
    ("scarlet_macaw", "Scarlet macaw", "Ara macao", "great_tit", ["rainforest"], None),
    ("hummingbird", "Ruby-throated hummingbird", "Archilochus colubris", "great_tit", ["forest"], None),
    ("flamingo", "Greater flamingo", "Phoenicopterus roseus", "mallard", ["wetland", "lake"], None),
    ("peacock", "Indian peafowl", "Pavo cristatus", "mallard", ["forest"], None),
    ("harpy_eagle", "Harpy eagle", "Harpia harpyja", "kestrel", ["rainforest"], None),
    ("poison_dart_frog", "Strawberry poison-dart frog", "Oophaga pumilio", "frog", ["rainforest"], None),
    ("red_eyed_tree_frog", "Red-eyed tree frog", "Agalychnis callidryas", "frog", ["rainforest"], None),
    ("green_iguana", "Green iguana", "Iguana iguana", "lizard", ["rainforest"], None),
    ("chameleon", "Veiled chameleon", "Chamaeleo calyptratus", "lizard", ["forest"], None),
    ("komodo_dragon", "Komodo dragon", "Varanus komodoensis", "lizard", ["grassland", "forest"], None),
    ("anaconda", "Green anaconda", "Eunectes murinus", "grass_snake", ["rainforest", "wetland", "river"], None),
    ("python", "Burmese python", "Python bivittatus", "grass_snake", ["rainforest", "wetland"], None),
    ("king_cobra", "King cobra", "Ophiophagus hannah", "grass_snake", ["rainforest"], None),
    ("crocodile", "Saltwater crocodile", "Crocodylus porosus", "lizard", ["mangrove", "river", "sea"], None),
    ("alligator", "American alligator", "Alligator mississippiensis", "lizard", ["wetland", "river"], None),
    ("piranha", "Red-bellied piranha", "Pygocentrus nattereri", "bream", ["river"], None),
    ("blue_morpho", "Blue morpho", "Morpho peleides", "peacock_butterfly", ["rainforest"], None),
    ("monarch", "Monarch butterfly", "Danaus plexippus", "peacock_butterfly", ["grassland", "forest"], None),
    ("mudskipper", "Atlantic mudskipper", "Periophthalmus barbarus", "perch", ["mangrove"], None),
    ("proboscis_monkey", "Proboscis monkey", "Nasalis larvatus", None, ["mangrove", "rainforest"], "body_plan"),
    ("fiddler_crab", "Fiddler crab", "Uca pugnax", None, ["mangrove"], "body_plan"),
    # not possible yet, asked for often
    ("bat", "Common pipistrelle", "Pipistrellus pipistrellus", None, ["forest"], "bats"),
    ("fruit_bat", "Indian flying fox", "Pteropus medius", None, ["forest", "rainforest"], "bats"),
    ("dragonfly", "Emperor dragonfly", "Anax imperator", None, ["lake", "wetland"], "dragonflies"),
    ("tortoise", "Galápagos giant tortoise", "Chelonoidis niger", None, ["grassland"], "body_plan"),
    ("platypus", "Platypus", "Ornithorhynchus anatinus", None, ["river"], "body_plan"),
    ("ladybird", "Seven-spot ladybird", "Coccinella septempunctata", None, ["grassland", "forest"], "body_plan"),
    ("ant", "Red wood ant", "Formica rufa", None, ["forest"], "body_plan"),
    ("spider", "European garden spider", "Araneus diadematus", None, ["forest", "grassland"], "body_plan"),
    ("snail", "Roman snail", "Helix pomatia", None, ["forest", "grassland"], "body_plan"),
]

REFERENCES_ELSEWHERE = {"grass_snake", "harbour_porpoise", "peacock_butterfly"}  # models/examples/


def library():
    """animals/ files by id, with their GBIF keys."""
    out = {}
    for path in glob.glob(os.path.join(ROOT, "animals", "*.json")):
        stem = os.path.basename(path)[:-5]
        if stem == "archetypes":
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        out[stem] = data.get("taxon", {}).get("gbif_key")
    return out


def gbif_key(latin):
    query = urllib.parse.urlencode({"name": latin, "kingdom": "Animalia", "strict": "true"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(f"{API}?{query}", timeout=20) as response:
                found = json.load(response)
            break
        except OSError:
            time.sleep(2 ** attempt)
    else:
        raise SystemExit(f"GBIF didn't answer for {latin}")
    if found.get("matchType") != "EXACT" or found.get("rank") not in ("SPECIES", "SUBSPECIES"):
        return None, f"{latin}: GBIF match is {found.get('matchType')} {found.get('rank')}"
    return found.get("acceptedUsageKey") or found.get("usageKey"), None


def entries(resolve):
    lib = library()
    out, problems = [], []
    for animal_id, name, latin, start, habitats, not_yet in TABLE:
        in_library = animal_id if animal_id in lib else None
        if in_library and lib[animal_id]:
            key = lib[animal_id]
        else:
            key, problem = resolve(latin)
            if problem:
                problems.append(problem)
        entry = {"id": animal_id, "name": name, "latin": latin, "gbif_key": key,
                 "start_from": start, "habitats": habitats, "can_make": not_yet is None}
        if not_yet:
            entry["not_yet"] = not_yet
        if in_library:
            entry["in_library"] = in_library
        out.append(entry)
    return out, problems


def table_problems():
    """Offline rules for the table itself."""
    problems, ids, keys = [], set(), {}
    models = {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(ROOT, "models", "*.json"))}
    for animal_id, name, latin, start, habitats, not_yet in TABLE:
        if animal_id in ids:
            problems.append(f"{animal_id}: listed twice")
        if latin in keys:
            problems.append(f"{animal_id}: the same species as {keys[latin]}")
        keys[latin] = animal_id
        ids.add(animal_id)
        for habitat in habitats:
            if habitat not in HABITATS:
                problems.append(f"{animal_id}: unknown habitat {habitat}")
        if not_yet is not None and not_yet not in NOT_YET:
            problems.append(f"{animal_id}: unknown reason {not_yet}")
        if not_yet is None and start not in models | REFERENCES_ELSEWHERE:
            problems.append(f"{animal_id}: start_from {start} is not a reference model")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="offline: compare animal-list.json with the table")
    args = parser.parse_args()
    problems = table_problems()

    if args.check:
        with open(OUT, encoding="utf-8") as f:
            written = json.load(f)
        by_id = {e["id"]: e for e in written["animals"]}
        keep_key = lambda latin: (next((e["gbif_key"] for e in written["animals"] if e["latin"] == latin), None), None)
        expected, _ = entries(keep_key)
        for entry in expected:
            if by_id.get(entry["id"]) != entry:
                problems.append(f"{entry['id']}: animal-list.json is out of date; run tools/animal_list.py")
        if len(by_id) != len(expected):
            problems.append("animal-list.json has animals the table doesn't; run tools/animal_list.py")
        if written.get("not_yet") != NOT_YET or sorted(written.get("habitats", [])) != sorted(HABITATS):
            problems.append("animal-list.json's reasons or habitats are out of date; run tools/animal_list.py")
        homes = sorted(p[:-5] for p in os.listdir(os.path.join(ROOT, "homes")) if p.endswith(".json"))
        if written.get("homes") != homes:
            problems.append("animal-list.json's homes are out of date; run tools/animal_list.py")
        seen = {}
        for e in written["animals"]:
            if not e.get("gbif_key"):
                problems.append(f"{e['id']}: no GBIF key")
            elif e["gbif_key"] in seen:
                problems.append(f"{e['id']}: the same GBIF key as {seen[e['gbif_key']]}")
            seen.setdefault(e.get("gbif_key"), e["id"])
    else:
        animals, found = entries(gbif_key)
        problems += found
        homes = sorted(p[:-5] for p in os.listdir(os.path.join(ROOT, "homes")) if p.endswith(".json"))
        doc = {
            "about": "The animals a grown-up can ask for in Animundo Builder. Written by tools/animal_list.py; edit the table there.",
            "habitats": sorted(HABITATS),
            "homes": homes,
            "not_yet": NOT_YET,
            "animals": animals,
        }
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print(f"wrote animal-list.json: {len(animals)} animals, "
              f"{sum(e['can_make'] for e in animals)} we can make, "
              f"{sum(1 for e in animals if any(h in homes for h in e['habitats']))} with a home ready")

    for line in problems:
        print("FAIL " + line)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
