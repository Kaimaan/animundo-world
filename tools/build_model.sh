#!/bin/sh
# Build models from their specs with Blender (no window).
#   tools/build_model.sh models/squirrel.json          one animal
#   tools/build_model.sh models/plants/bilberry.json   one plant
#   tools/build_model.sh                               every animal and plant
# Needs Blender (tested with 5.2): https://www.blender.org/download/
cd "$(dirname "$0")/.." || exit 1
BLENDER="${BLENDER:-$(command -v blender || echo /Applications/Blender.app/Contents/MacOS/Blender)}"
[ $# -eq 0 ] && set -- models/*.json models/plants/*.json
status=0
for spec in "$@"; do
	case "$spec" in
		*plants/*) script=tools/blender/build_plant.py ;;
		*) script=tools/blender/build_model.py ;;
	esac
	out=$("$BLENDER" -b --factory-startup -P "$script" -- "$spec" 2>&1)
	echo "$out" | grep -E "^(BUILT|ERROR|  |Traceback|  File|[A-Za-z]*Error)"
	echo "$out" | grep -q "^BUILT" || status=1
done
exit $status
