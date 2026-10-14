#!/bin/sh
# Fails if someone changed this repository's content inside the game repo
# instead of here. The sync would overwrite their work, so it stops instead.
# The game's copy must match this repo at the last sync (the game's .world-sync),
# or at the commit being synced now (someone ran export_to_game.sh and committed it).
#   tools/check_game_drift.sh ../animundo
set -e
GAME="$(cd "${1:?usage: tools/check_game_drift.sh <path to game repo>}" && pwd)"
cd "$(dirname "$0")/.."
BASE=$(cat "$GAME/.world-sync")
REPORT=$(mktemp)

# Does the game's copy match this repo at commit $1? Lists the differences in $REPORT.
# Always exports with today's export script, so old commits are compared the same way.
matches() {
	tmp=$(mktemp -d)
	git worktree add -q --detach "$tmp/w" "$1"
	cp tools/export_to_game.sh "$tmp/w/tools/export_to_game.sh"
	mkdir -p "$tmp/g/tools" "$tmp/g/docs"
	"$tmp/w/tools/export_to_game.sh" "$tmp/g" > /dev/null
	: > "$REPORT"
	( cd "$tmp/g" && find . -type f ! -name '*.glb' | sed 's|^\./||' ) | while read -r f; do
		cmp -s "$tmp/g/$f" "$GAME/$f" || echo "  $f" >> "$REPORT"
	done
	for d in regions animals models; do
		( cd "$GAME" && find "$d" -type f ! -name '*.import' ) | while read -r f; do
			[ -f "$tmp/g/$f" ] || echo "  $f (only in the game repo)" >> "$REPORT"
		done
	done
	git worktree remove --force "$tmp/w"
	rm -rf "$tmp"
	[ ! -s "$REPORT" ]
}

if matches "$BASE"; then
	echo "No content was changed in the game repo since the last sync ($BASE)."
	exit 0
fi
cp "$REPORT" "$REPORT.base"
if matches HEAD; then
	echo "The game repo already has this commit's content."
	exit 0
fi
echo "::error::Content was changed in the game repo instead of in animundo-world. Move these changes to animundo-world, then undo them in the game repo:"
cat "$REPORT.base"
exit 1
