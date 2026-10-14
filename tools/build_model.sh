#!/bin/sh
# Build animated animal models from their specs with Blender (no window).
#   tools/build_model.sh models/squirrel.json      one model
#   tools/build_model.sh                           every model in models/
# Needs Blender (tested with 5.2): https://www.blender.org/download/
cd "$(dirname "$0")/.." || exit 1
BLENDER="${BLENDER:-$(command -v blender || echo /Applications/Blender.app/Contents/MacOS/Blender)}"
[ $# -eq 0 ] && set -- models/*.json
status=0
for spec in "$@"; do
	out=$("$BLENDER" -b --factory-startup -P tools/blender/build_model.py -- "$spec" 2>&1)
	echo "$out" | grep -E "^(BUILT|ERROR|  |Traceback|  File|[A-Za-z]*Error)"
	echo "$out" | grep -q "^BUILT" || status=1
done
exit $status
