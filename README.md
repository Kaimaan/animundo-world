# Animundo world

Every place, animal and translation in [Animundo](https://animundo.app), a game where children play real animals in real places, through the real seasons.

This repository is the game's **content**: small data files that anyone can write with the help of an AI assistant. The game's code is kept separately.

Places can also be built by [Animundo Builder](https://github.com/Kaimaan/animundo-builder): a family picks a real place in the game, agents research it and build its animals, the family plays it and submits it, and the [builder bot](docs/builder-bot.md) opens a pull request here for a person to review.

## What's here

| Folder | What it holds |
|---|---|
| [`regions/`](regions/) | Places in the world: land, plants, colours, seasons and which animals live there |
| [`animals/`](animals/) | Animals: how they live, what they eat, how they spend the year, and what the game tells the player |
| [`models/`](models/README.md) | What animals look like, as specs that Blender turns into 3D models |
| [`locale/`](locale/) | All text in every language |
| [`homes/`](homes/README.md) | Home templates: the land of one habitat, copied when a family asks for an animal |
| [`animal-list.json`](tools/animal_list.py) | The animals a family can ask for in Animundo Builder, with GBIF IDs, starting models and habitats |
| [`places.json`](tools/places.py) | The game's built places for Animundo Builder: names in English and Finnish, centre, Wikidata id and animals, from `regions/` |
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
- Sign off every commit (`git commit -s`): see [Licence](#licence).

## Licence

- **Content** (places, animals, models, preview sheets, text): [CC BY 4.0](LICENSE). Anyone may reuse it, with credit to "Animundo and its contributors".
- **Tools and workflows** (`tools/`, `.github/`): [MIT](LICENSE-CODE).
- **Contributing:** every commit carries a `Signed-off-by:` line, which means you agree to the [Developer Certificate of Origin](https://developercertificate.org): you have the right to send it, and it is shared under these licences. The gate closes pull requests with commits that aren't signed off.
- Facts come from the sources cited in each file; map data from OpenStreetMap is © OpenStreetMap contributors, under the [ODbL](https://opendatacommons.org/licenses/odbl/).
