#!/usr/bin/env bash
# Pull mod config files a Steam Deck generated back into this repo's config/,
# as a staged review rather than a blind overwrite:
#   deck/pull-configs.sh [deck@steamdeck.local]
# Files already tracked in config/ are updated in place (review with git diff).
# New files and files for mods no longer in the pack are listed, not copied,
# so Deck-local preferences and leftovers from removed mods stay out.
# Skips BepInEx.cfg (the pack has its own) and ValheimPlus's old-format files.
# Set PULL_SSH_OPTS to add ssh options, e.g. "-o PubkeyAuthentication=no" when
# the Deck answers "too many authentication failures".
set -euo pipefail
host="${1:-deck@steamdeck.local}"
repo="$(cd "$(dirname "$0")/.." && pwd)"
read -r -a ssh_opts <<< "${PULL_SSH_OPTS:-}"
ssh_cmd=(ssh "${ssh_opts[@]}" "$host")

# shellcheck disable=SC2016  # expands on the Deck, not here
remote_dir=$("${ssh_cmd[@]}" 'for d in ~/.local/share/Steam/steamapps/common/Valheim ~/.steam/steam/steamapps/common/Valheim /run/media/*/steamapps/common/Valheim /run/media/*/SteamLibrary/steamapps/common/Valheim /run/media/deck/*/steamapps/common/Valheim; do [ -d "$d/BepInEx/config" ] && { printf "%s\n" "$d/BepInEx/config"; break; }; done')
[ -n "$remote_dir" ] || { echo "pull-configs: no BepInEx/config found on $host" >&2; exit 1; }
echo "pull-configs: $host:$remote_dir"

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
"${ssh_cmd[@]}" "cd \"\$HOME\" && cd '${remote_dir//\'/\'\\\'\'}' && find . -maxdepth 1 -type f \( -name '*.cfg' -o -name '*.yml' -o -name '*.yaml' \) ! -name BepInEx.cfg ! -name 'valheim_plus.cfg*' -print0 | tar --null -T - -czf -" | tar xzf - -C "$stage"

updated=0
for f in "$stage"/*; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    if [ -f "$repo/config/$name" ]; then
        cp "$f" "$repo/config/$name"
        updated=$((updated + 1))
    else
        echo "new on Deck, not copied (add by hand if the pack should ship it): $name"
    fi
done
echo "pull-configs: $updated tracked file(s) updated; review with: git -C '$repo' diff config/"
