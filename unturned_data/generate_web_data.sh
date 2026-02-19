#!/usr/bin/env bash
# Generate web data with map spawn info for all available maps.
# Run on localAI where the server data lives.

set -euo pipefail

BUNDLES=~/unturned-server/Bundles
OUTPUT=~/code/git/github.com/shitchell/stuff/site/unturned/data.json

# Built-in maps
MAPS=(~/unturned-server/Maps/*)

# Workshop maps
for ws_dir in ~/unturned-server/Servers/MyServer/Workshop/Steam/content/304930/*/; do
    for map_dir in "$ws_dir"*/; do
        [ -d "$map_dir/Spawns" ] && MAPS+=("$map_dir")
    done
done

MAP_ARGS=()
for map in "${MAPS[@]}"; do
    [ -d "$map/Spawns" ] && MAP_ARGS+=(--map "$map")
done

~/bin/unturned-data "$BUNDLES" --format web "${MAP_ARGS[@]}" > "$OUTPUT"
echo "Generated $OUTPUT with ${#MAP_ARGS[@]} maps"
