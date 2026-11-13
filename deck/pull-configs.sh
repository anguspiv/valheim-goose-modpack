#!/usr/bin/env bash
# Copy the mod config files a Steam Deck generated back into this repo's config/.
# Run from a machine that can ssh to the Deck (Desktop Mode sshd enabled):
#   deck/pull-configs.sh [deck@steamdeck.local]
# Pulls BepInEx/config/*.cfg, *.yml and *.yaml. Skips BepInEx.cfg (the pack has its
# own) and ValheimPlus's old-format files. Review the diff before committing.
set -euo pipefail
host="${1:-deck@steamdeck.local}"
repo="$(cd "$(dirname "$0")/.." && pwd)"
remote_dir=$(ssh -o PubkeyAuthentication=no "$host" 'for d in ~/.local/share/Steam/steamapps/common/Valheim /run/media/*/steamapps/common/Valheim; do [ -d "$d/BepInEx/config" ] && { echo "$d/BepInEx/config"; break; }; done')
[ -n "$remote_dir" ] || { echo "pull-configs: no BepInEx/config found on $host" >&2; exit 1; }
echo "pull-configs: $host:$remote_dir -> $repo/config"
ssh -o PubkeyAuthentication=no "$host" "cd '$remote_dir' && tar czf - --exclude=BepInEx.cfg --exclude='valheim_plus.cfg*' *.cfg *.yml *.yaml 2>/dev/null" | tar xzf - -C "$repo/config"
ls -la "$repo/config"
