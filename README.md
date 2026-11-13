# Goose Modpack

A casual quality-of-life modpack for Valheim. Portals carry everything, a
portal-station network, and ValheimPlus for the small tweaks.

## Mods

| Mod | What it does |
| --- | --- |
| [ValheimPlus (Grantapher)](https://thunderstore.io/c/valheim/p/Grantapher/ValheimPlus_Grantapher_Temporary/) | Building, beehive, stamina and other QoL tweaks. Settings live in `config/valheim_plus.cfg`. |
| [TeleportEverything](https://thunderstore.io/c/valheim/p/OdinPlus/TeleportEverything/) | Take ore, carts, boats and tames through portals. Configure in-game with Left Shift + Up Arrow. |
| [PortalStations](https://thunderstore.io/c/valheim/p/RustyMods/PortalStations/) | Buildable portal stations with a pick-any-destination list, plus a personal teleporter. |
| [BepInExPack_Valheim](https://thunderstore.io/c/valheim/p/denikson/BepInExPack_Valheim/) | The mod loader. |

Built against Valheim 1.0.20. Everyone on the server needs the same versions.

## Windows and macOS (mod manager)

1. Install [r2modman](https://thunderstore.io/c/valheim/p/ebkr/r2modman/) (or
   Thunderstore Mod Manager) and pick Valheim.
2. Online tab → search `goose_modpack` → Install. The manager pulls the mods
   and this pack's `config/` settings.
3. Launch Valheim through the manager's **Start modded** button. The plain
   Steam shortcut launches vanilla, which the server rejects.

Updates: the manager shows a pending update on the profile; click it. The
server and the pack move together, so update when the server tells you to.

Direct link: <https://thunderstore.io/c/valheim/p/anguspiv/goose_modpack/>

## Steam Deck (launch from Game Mode)

No mod manager needed. The installer puts BepInEx and the mods straight into
the Valheim folder, so the normal Valheim tile in Game Mode launches modded.

One-time prep on the Deck (Desktop Mode, Konsole), so you can reach it over SSH:

```bash
passwd
sudo systemctl enable --now sshd
```

Then from any machine on the same network (or over Tailscale):

```bash
ssh deck@steamdeck.local 'curl -fsSL https://raw.githubusercontent.com/anguspiv/valheim-goose-modpack/main/deck/install.py | python3 - --remote'
```

Finally, on the Deck: Valheim tile → gear icon → Properties → Launch Options:

```
./start_game_bepinex.sh %command%
```

That's it. Launch Valheim from Game Mode as normal.

To update later, re-run the same `ssh ... install.py` line. It downloads
whatever changed in `manifest.json`, removes mods that were dropped from the
pack, and re-applies `config/`.

Notes:

- Valheim must be installed via Steam first. The installer finds it on internal
  storage or an SD card; pass `--game-dir` if it can't.
- If modded launch flashes and dies, add `-compat-force-slr off` after
  `%command%` in Launch Options, or force "Legacy runtime 1.0" under
  Properties → Compatibility.
- To go back to vanilla, clear the Launch Options. The mods stay on disk but
  don't load.
- From a local checkout instead: `python3 deck/install.py`.

## Server images

`deck/install.py --target DIR` resolves the same `manifest.json` into
`DIR/BepInEx/plugins` and `DIR/BepInEx/config` without touching a game install,
skipping the BepInEx core pack (the server image supplies its own). The
[valheim-server](https://github.com/anguspiv/valheim-server) image bakes the
pack in at build time from a release tag.

## Releasing a new pack version

1. Bump `version_number` in `manifest.json` (and the dependency pins).
2. Merge to `main`, then tag and push: `git tag v2.0.0 && git push origin v2.0.0`.
3. The release workflow runs the tests, builds `goose_modpack-2.0.0.zip` with
   `scripts/build-thunderstore.py`, and attaches it to the GitHub release.
4. Upload that zip at <https://thunderstore.io/package/create/> (team
   `anguspiv`, community Valheim). Thunderstore refuses a version it already has,
   so the manifest bump in step 1 is what makes the upload valid.
5. Point the server at the tag (`MODPACK_REF` in the server repo).
