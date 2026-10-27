# The builder bot

[Animundo Builder](https://github.com/Kaimaan/animundo-builder) builds a real place and its animals for a family who asked for it. When the family has played it and submits it, the builder bot opens a pull request here. A person reviews it like any other contribution; the bot can't approve or merge anything.

## What the bot can do

- **It is a GitHub App** (`animundo-builder[bot]`), installed on this repository only.
- **Permissions:** Contents read and write, Pull requests read and write, Metadata read. Nothing else: no Administration, Workflows, Actions, Secrets or Members. Without the Workflows permission GitHub refuses any push that changes `.github/workflows/`.
- **Branches:** it pushes only to branches named `builder/*`. `main` needs a pull request with an approving review from [CODEOWNERS](../.github/CODEOWNERS).
- **The gate** treats it like any verified contributor ([gate.yml](../.github/workflows/gate.yml)): only content files may change. Its one difference is a limit of 10 open pull requests instead of 2, because each one is a different family's place.
- **Its commits are signed off** (DCO), like everyone's.
- **Its pull requests** say where the place is, its sources, every check's result, the new species with their preview sheets and the builder's review notes. They never name the family.

## Poisonous plants

[`poisonous-plants.json`](../poisonous-plants.json) lists plants and fungi that are poisonous to people, by their GBIF taxon ID. `tools/check_taxa.py` refuses a place that marks one of them as food. Anyone, the bot too, may propose an addition; the gate closes a pull request that removes or changes an entry.

## Setting it up (the owner)

1. **Create the App** under Settings → Developer settings → GitHub Apps → New: name `animundo-builder`, no webhook URL until the hosted worker exists, the permissions above, "Only on this account". Install it on `animundo-world` only.
2. **Keep the private key** in Secret Manager, readable only by the hosted worker. Never in a file in any repository.
3. **Rulesets** on this repository (Settings → Rules → Rulesets):
   - `main`: require a pull request, 1 approving review, review from Code Owners; block force pushes and deletion. Bypass: repository admins, and the **GitHub Actions** app, because the Verify me workflow commits `.github/contributors.txt` straight to `main` (only workflows already on `main` run with that token). After saving, test one Verify me issue.
   - `everything but builder/*`: target all branches, exclude `builder/**` and `main`; restrict creations, updates and deletions. Bypass: repository admins only. This keeps the bot, and any other writer, to `builder/*` branches.
