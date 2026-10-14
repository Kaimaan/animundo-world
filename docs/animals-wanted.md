# Animals wanted

The lists of what's wanted (animals, plants, trees, foods and the core team work behind them) are now in one page: **[catalogue.md](catalogue.md)**. It shows what the game has, read from the data, next to what it's missing, from [`wanted.json`](../wanted.json). Pick a row there and follow [CONTRIBUTING.md](../CONTRIBUTING.md). Under the food-first rule ([decision 0011](decisions/0011-food-first.md)), a new animal that needs food from the list brings that food with it.

Every hunter follows one rule: **catching is eating**, with one tap and no separate Eat step ([CONTRIBUTING.md](../CONTRIBUTING.md#the-animal-file)). A kestrel's dive and a perch's chase will work like the fox's pounce.

This page keeps the design notes that go with the lists.

## Night animals (later)
Bats (lepakot, such as the northern bat *Eptesicus nilssonii*), owls and other animals that are awake at night. Before the first one arrives, the core team has to test how night should work. Ideas to try ([0014](decisions/0014-day-and-night-pace.md), open: to be tested before deciding):

| Work | Why | Status |
|---|---|---|
| **Night at normal speed:** no fast-forward while day animals sleep. A fixed day of about 15 minutes (about 7 of day, 2 of dusk, 4 of night, 2 of dawn), set in data | Today sleeping makes time 20× faster, so the night is over in seconds. A night animal would have nothing to play. Long days and nights are boring too | Later |
| **Wait or switch:** when your animal falls asleep, ask *"Wait for morning, or play another animal?"* The sleeping animal stays saved in its den. Night animals get the same choice at dawn | One shared clock, so a player who doesn't want to wait goes and plays something else | Later |

### Fixed already
- **One material per animal** (2026-10-14). Colours are stored on the vertices, so each animal is one draw call: 48 animals went from 1,218 draw calls per frame to 198. It also softened the jagged colour edges ([decision 0013](decisions/0013-one-material-per-animal.md)).
- **Kestrel ate berries.** Real kestrels don't, so berries were removed. Until voles arrive (row 1), it eats only beetles.
