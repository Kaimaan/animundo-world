#!/bin/sh
# Copy content from a checkout of the game repository into this one.
# Runs automatically on every push to the game's main (.github/workflows/sync-world.yml
# in the game repo), until the game reads its content from here (decision 0013).
#   tools/import_from_game.sh ../animundo
set -e
GAME="${1:?usage: tools/import_from_game.sh <path to game repo>}"
cd "$(dirname "$0")/.."
for d in regions animals models locale; do
	rsync -a --delete --exclude '*.import' "$GAME/$d/" "$d/"
done
cp "$GAME/ART.md" ART.md
cp "$GAME/docs/animals-wanted.md" docs/animals-wanted.md
# the community tracker: what's wanted, and the catalogue generated from it
for f in wanted.json docs/catalogue.md tools/catalogue.py; do
	[ -f "$GAME/$f" ] && cp "$GAME/$f" "$f"
done
cp "$GAME/tools/validate_region.py" "$GAME/tools/build_model.sh" tools/
rsync -a --delete --exclude "__pycache__" "$GAME/tools/blender/" tools/blender/
# CONTRIBUTING.md: the game's version, keeping this repository's note at the top
python3 - "$GAME/CONTRIBUTING.md" <<'PY'
import sys
w = open("CONTRIBUTING.md", encoding="utf-8").read()
start = w.index("> **About this repository.**")
end = w.index("\n\n", w.index("> You need to be a verified player")) + 2
g = open(sys.argv[1], encoding="utf-8").read()
i = g.index("\n") + 1
open("CONTRIBUTING.md", "w", encoding="utf-8").write(g[:i] + "\n" + w[start:end] + g[i:].lstrip("\n"))
PY
echo "Imported from $GAME."
