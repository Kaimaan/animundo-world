#!/bin/sh
# Fails if someone changed this repository's content inside the game repo
# instead of here. The sync would overwrite their work, so it stops instead.
# Each file in the game's copy must match this repo at the last sync (the game's
# .world-sync) or at the commit being synced now (someone copied it by hand from
# here, or ran export_to_game.sh and committed it). Only a file that matches
# neither is someone's work the sync would lose.
#   tools/check_game_drift.sh ../animundo
set -e
GAME="$(cd "${1:?usage: tools/check_game_drift.sh <path to game repo>}" && pwd)"
cd "$(dirname "$0")/.."
BASE=$(cat "$GAME/.world-sync")
TMP=$(mktemp -d)
REPORT="$TMP/report"
: > "$REPORT"

# Exports this repo at commit $1 into $TMP/$2.
# Always exports with today's export script, so old commits are compared the same way.
export_at() {
	git worktree add -q --detach "$TMP/w" "$1"
	cp tools/export_to_game.sh "$TMP/w/tools/export_to_game.sh"
	mkdir -p "$TMP/$2/tools" "$TMP/$2/docs"
	"$TMP/w/tools/export_to_game.sh" "$TMP/$2" > /dev/null
	git worktree remove --force "$TMP/w"
}
export_at "$BASE" base
export_at HEAD head

# Is the game's file $1 the same as in the export at $2 (both missing counts)?
same() {
	if [ -f "$GAME/$1" ]; then cmp -s "$TMP/$2/$1" "$GAME/$1"
	else [ ! -f "$TMP/$2/$1" ]; fi
}
{
	( cd "$TMP/base" && find . -type f ! -name '*.glb' )
	( cd "$TMP/head" && find . -type f ! -name '*.glb' )
	for d in regions animals models $(cd "$GAME" && ls -d homes places 2>/dev/null); do
		( cd "$GAME" && find "$d" -type f ! -name '*.import' )
	done
} | sed 's|^\./||' | sort -u | while read -r f; do
	case "$f" in   # the game has no homes or places until their first sync
		homes/*) [ -d "$GAME/homes" ] || continue ;;
		places/*) [ -d "$GAME/places" ] || continue ;;
	esac
	same "$f" base || same "$f" head || {
		if [ -f "$GAME/$f" ] && [ ! -f "$TMP/base/$f" ] && [ ! -f "$TMP/head/$f" ]; then
			echo "  $f (only in the game repo)"
		else
			echo "  $f"
		fi
	} >> "$REPORT"
done

if [ ! -s "$REPORT" ]; then
	echo "No content was changed in the game repo since the last sync ($BASE)."
	rm -rf "$TMP"
	exit 0
fi
echo "::error::Content was changed in the game repo instead of in animundo-world. Move these changes to animundo-world, then undo them in the game repo:"
cat "$REPORT"
rm -rf "$TMP"
exit 1
