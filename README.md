# Goose Modpack

A casual quality-of-life modpack for Valheim. Portals carry everything, a
portal-station network, and ValheimPlus for the small tweaks.

## Mods

| Mod | Where | What it does |
| --- | --- | --- |
| [ValheimPlus (Grantapher)](https://thunderstore.io/c/valheim/p/Grantapher/ValheimPlus_Grantapher_Temporary/) | server + client | Craft and build from nearby chests, auto fuel and auto deposit on every station, auto-repair, auto stack-all on chest open, bigger chests and carry weight, no structural integrity, 2x gathering and drops. Settings in `config/org.bepinex.plugins.valheim_plus.cfg`, mostly synced from the server (HUD, FOV and keybinds stay per player). |
| [PortalStations](https://thunderstore.io/c/valheim/p/RustyMods/PortalStations/) | server + client | Buildable portal stations with a pick-any-destination list, plus a personal teleporter. Teleport anything, device needs no fuel, anyone can rename. |
| [TeleportCreatures](https://thunderstore.io/c/valheim/p/OdinPlus/TeleportCreatures/) | server + client | Tames that are following you come through portals (`OnlyFollow` by default). |
| [TeleportCarts](https://thunderstore.io/c/valheim/p/OdinPlus/TeleportCarts/) | server + client | An attached cart comes through portals and dungeon doors with you. |
| [Quick Stack Store Sort Trash Restock](https://thunderstore.io/c/valheim/p/Goldenrevolver/Quick_Stack_Store_Sort_Trash_Restock/) | client only | Restock, trash, sort and quick-stack buttons; area stacking into nearby chests enabled. |
| [PlantEasily](https://thunderstore.io/c/valheim/p/Advize/PlantEasily/) | client only | Plant in rows and grids with the cultivator, bulk harvest, replant on harvest. Controller bindings built in. |
| [BepInExPack_Valheim](https://thunderstore.io/c/valheim/p/denikson/BepInExPack_Valheim/) | server + client | The mod loader. |

Built against Valheim 1.0.21 (ValheimPlus 10.4.0 lists 1.0.20 as tested). Everyone on the server needs the same versions;
`Server.enforceMod` is on, so a client without ValheimPlus is refused.

Client-only mods are listed in `server.json` and are not installed on the
dedicated server. Every value that differs from a mod's default, and why, is in
`docs/config-decisions-2.1.0.md`. The `config/` files are the mods' own
generated defaults with those values applied; `deck/pull-configs.sh` copies
freshly generated files back from a Steam Deck when a mod update changes the
schema.

## Windows (mod manager)

1. Install [r2modman](https://thunderstore.io/c/valheim/p/ebkr/r2modman/) (or
   Thunderstore Mod Manager) and pick Valheim.
2. Online tab → search `goose_modpack` → Install. The manager pulls the mods
   and this pack's `config/` settings.
3. Launch Valheim through the manager's **Start modded** button. The plain
   Steam shortcut launches vanilla, which the server rejects.

Updates: the manager shows a pending update on the profile; click it. The
server and the pack move together, so update when the server tells you to.

Direct link: <https://thunderstore.io/c/valheim/p/anguspiv/goose_modpack/>

Upgrading from 2.0.0 or earlier: delete `BepInEx/config/valheim_plus.cfg` in the
profile folder (r2modman: Settings → Browse profile folder). ValheimPlus 10.x
prefers that old file when present and ignores the pack's new one.

## macOS (script install)

r2modman and Thunderstore Mod Manager have no macOS builds, so on a Mac the
same `deck/install.py` installs the pack straight into the native Steam build
of Valheim.

1. Install Valheim from Steam and let it finish updating. Quit the game.
2. In Terminal (Python 3 ships with the Xcode command line tools; run
   `xcode-select --install` if `python3` is missing):

   ```bash
   curl -fsSL https://raw.githubusercontent.com/anguspiv/valheim-goose-modpack/main/deck/install.py | python3 - --remote
   ```

   It finds `~/Library/Application Support/Steam/steamapps/common/Valheim`
   (or a `SteamLibrary` on an external drive under `/Volumes`) by looking for
   `Valheim.app`; pass `--game-dir` if yours is elsewhere. It installs
   BepInEx and the mods into the same `BepInEx/` layout as the Deck, points
   `start_game_bepinex.sh` at `Valheim.app`, makes it executable, and clears
   the `com.apple.quarantine` flag on `BepInEx/`, `doorstop_libs/` and the
   script so Gatekeeper does not block the Doorstop dylib. On an Intel Mac it
   also sets `archpreference="x86_64"` in the script: the pack's default
   `arm64,x86_64` makes `arch` exit with `Unknown architecture: arm64` before
   the game starts. Apple Silicon keeps the native default; if mods don't
   load there, set `archpreference="x86_64"` by hand to run under Rosetta.
3. Steam → Library → right-click Valheim → Properties → General → Launch
   Options:

   ```
   ./start_game_bepinex.sh %command%
   ```

   Replace anything already there. An older manual BepInEx install used
   `run_bepinex.sh`, which the current pack no longer ships; a launch option
   pointing at it stops the game from starting.

4. Launch Valheim from Steam. `BepInEx/LogOutput.log` in the game folder
   should list the plugins loading, and the main menu shows the ValheimPlus
   version.

Tested on an Intel MacBook Pro (i9-9980HK, macOS 26.7.1), Valheim 1.0.21:
BepInEx 5.4.23.6 loads all 6 plugins natively as x86_64 and the main menu
shows `ValheimPlus 10.4.0.0 (Grantapher)`. Apple Silicon is not tested yet.

If you modded Valheim by hand before, the installer warns about DLLs sitting
loose in `BepInEx/plugins/` (an old `ValheimPlus.dll` there would load next
to the pack's copy). Move them out. To update, re-run the same command. To
go back to vanilla, clear the Launch Options.

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

`deck/install.py --target DIR [--expect-version X.Y.Z]` resolves the same
`manifest.json` into `DIR/BepInEx/plugins`, `DIR/BepInEx/patchers` (if any mod
ships one) and `DIR/BepInEx/config` without touching a game install. It skips
the BepInEx core pack and `config/BepInEx.cfg`, because the server image
supplies its own loader and loader config. `--expect-version` makes an
unattended build fail if the checkout's manifest does not match the tag it
asked for. Zip entries that would escape `DIR` abort the run. The
[valheim-server](https://github.com/anguspiv/valheim-server) image bakes the
pack in at build time from a release tag.

## Releasing a new pack version

1. Bump `version_number` in `manifest.json` (and the dependency pins).
2. Merge to `main`, then tag and push: `git tag v2.1.0 && git push origin v2.1.0`.
3. The release workflow runs the tests, builds `goose_modpack-2.1.0.zip` with
   `scripts/build-thunderstore.py`, and attaches it to the GitHub release.
4. The same workflow publishes the zip to Thunderstore with `tcli` when the
   repository secret `TCLI_AUTH_TOKEN` is set (a service-account token from the
   Thunderstore team page, Settings → Service Accounts). Without the secret,
   upload the zip by hand at <https://thunderstore.io/package/create/> (team
   `anguspiv`, community Valheim). Thunderstore refuses a version it already
   has, so the manifest bump in step 1 is what makes the upload valid.
5. Point the server at the tag (`MODPACK_REF` in the server repo).
