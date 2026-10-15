#!/bin/sh
# Copy this repository's content into a checkout of the game repository.
# animundo-world is the source (decision 0013); the game repo holds a mirror.
# Runs automatically on every push to main (.github/workflows/sync-to-game.yml).
# Run it by hand to try a change in the game before committing it here:
#   tools/export_to_game.sh ../animundo
# Then discard those copies in the game repo (git checkout -- .), because the
# sync commits them there itself.
#   --stamp   also record this commit in the game's .world-sync (the sync does this)
set -e
GAME="${1:?usage: tools/export_to_game.sh <path to game repo> [--stamp]}"
cd "$(dirname "$0")/.."
# data files only: a scene, script or other resource can never reach the game this way
for d in regions animals; do
	rsync -a --delete --include '*/' --include '*.json' --exclude '*' "$d/" "$GAME/$d/"
done
rsync -a --delete --include '*/' --include '*.json' --include '*.png' --include '*.md' --include '.gdignore' \
	--exclude '*' models/ "$GAME/models/"
# content text only: menu text (ui, loading, seasons, languages.json) belongs to the game repo
for f in locale/*/animals.json locale/*/food.json locale/*/plants.json locale/*/regions.json; do
	[ -f "$f" ] || continue
	mkdir -p "$GAME/$(dirname "$f")"
	cp "$f" "$GAME/$f"
done
for f in ART.md docs/animals-wanted.md docs/catalogue.md wanted.json \
	tools/validate_region.py tools/build_model.sh tools/catalogue.py; do
	cp "$f" "$GAME/$f"
done
rsync -a --delete --exclude "__pycache__" tools/blender/ "$GAME/tools/blender/"
# built models, when this checkout has built them (never deleted: the game keeps its .import files)
for f in assets/animals/*.glb assets/plants/*.glb; do
	[ -f "$f" ] && mkdir -p "$GAME/$(dirname "$f")" && cp "$f" "$GAME/$f"
done
[ "$2" = "--stamp" ] && git rev-parse HEAD > "$GAME/.world-sync"
echo "Exported to $GAME."
