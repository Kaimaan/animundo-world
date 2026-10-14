#!/bin/sh
# Copy content from a checkout of the game repository into this one.
# Used by the core team until the game reads its content from here (decision 0013).
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
echo "Imported from $GAME. CONTRIBUTING.md is not copied: merge changes by hand, keeping the note at the top."
