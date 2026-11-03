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

## PC (r2modman / Thunderstore)

Install `goose_modpack` from the Valheim community on Thunderstore, or import
this repo's `manifest.json` as a profile.

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
