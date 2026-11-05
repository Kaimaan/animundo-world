# Animundo world

Every place, animal and translation in [Animundo](https://animundo.app), a game where children play real animals in real places, through the real seasons.

This repository is the game's **content**: small data files that anyone can write with the help of an AI assistant. The game's code is kept separately.

## Animundo Builder

[Animundo Builder](https://github.com/Kaimaan/animundo-builder) grows the game's world from this repository. It reads a checkout of it at run time. Code makes plain land for each tile of the game's real-Earth grid from the homes and animals here. Where children reach the edge of the known world, agents on Meta's models research and build the new animals, plants and homes that are missing.

The builder was written with Muse Code during the Meta Global AI Developer Hackathon (from Oct 26, 2026), and it is the hackathon entry. This repository is not: it existed before the event (first commit Oct 14, 2026). We changed it a lot during the event week too (new homes, reference models and checkers). That is ordinary product work by our team, written with Claude Code, and it isn't part of the entry. The history shows those changes.

## What's here

| Folder | What it holds |
|---|---|
| [`regions/`](regions/) | Places in the world: land, plants, colours, seasons and which animals live there |
| [`animals/`](animals/) | Animals: how they live, what they eat, how they spend the year, and what the game tells the player |
| [`models/`](models/README.md) | What animals look like, as specs that Blender turns into 3D models |
| [`locale/`](locale/) | All text in every language |
| [`homes/`](homes/README.md) | Home templates: the land of one habitat, which Animundo Builder uses to make tiles |
| [`animal-list.json`](tools/animal_list.py) | The game's animals, with GBIF IDs, starting models and habitats; Animundo Builder picks each tile's animals from it |
| [`places.json`](tools/places.py) | The game's built places: names in English and Finnish, centre, Wikidata id and animals, from `regions/` |
| [`docs/animals-wanted.md`](docs/animals-wanted.md) | Animals and foods the game needs next |

## How to add something

1. **Get verified.** In the game, a grown-up taps *For parents and teachers*, signs in with their email (a free account) and taps *Get my contributor code*. Post the code in a [Verify me](../../issues/new?template=verify-me.yml) issue, and a bot lets your GitHub name open pull requests. Free and paid players alike can do this.
2. **Ask your AI assistant.** [CONTRIBUTING.md](CONTRIBUTING.md) has a prompt to copy for a new place or a new animal.
3. **Open a pull request.** A bot checks your files. A steward who knows the area checks the facts.
4. **See it in the game.** Once it's released, everyone can play it, and your nickname (`author`) is kept with it as its maker.

Everything should follow the [art guide](ART.md), so the game looks like one world.

## Rules

- Real facts only, with sources.
- Use a nickname, never a child's full name.
- Pull requests change content only: `regions/`, `animals/`, `models/`, `locale/`, plus claiming a row in `wanted.json`. Changes elsewhere are closed automatically.
- At most two open pull requests per person.

## Licence

- © Kai Lemmetty (Animundo). The repository is open source under the [Apache License 2.0](LICENSE). Third-party data in it stays under its own licence (below).
- The 3D models made by Animundo, the specs in `models/` and the `.glb` files built from them in `assets/`, are also free under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (see [LICENSE-models.md](LICENSE-models.md)). Credit them as "<Animal> by Animundo (animundo.app), CC BY 4.0". Each animal's model can be downloaded from its page at [animundo.app/animals/](https://animundo.app/animals/).
- Facts come from the sources cited in each file; map data from OpenStreetMap is © OpenStreetMap contributors, under the [ODbL](https://opendatacommons.org/licenses/odbl/); habitats come from RESOLVE Ecoregions 2017 (Dinerstein et al. 2017), under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
