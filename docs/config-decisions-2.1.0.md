# goose_modpack 2.1.0 config decisions (agreed with Angus 2026-11-12)

## Mod list
BepInExPack_Valheim, ValheimPlus_Grantapher_Temporary, PortalStations, TeleportCreatures (direct),
TeleportCarts (direct), Quick_Stack_Store_Sort_Trash_Restock (client), PlantEasily (client).
Removed TeleportEverything (and transitive TeleportBoats, QuickTeleport). Version 2.1.0.

## ValheimPlus: ship org.bepinex.plugins.valheim_plus.cfg, delete valheim_plus.cfg
Base: every key at its 10.4.0 default, then the agreed list (see other-session message), then:
- Brightness: enabled, nightBrightnessMultiplier 5
- LootDrop: enabled, lootDropAmountMultiplier 100 (chance 0)
- Demister: enabled, wispLight 20, wispTorch 24, mistwalker 10
- WispSpawner: enabled, wispSpawnChanceMultiplier 100 (night only, max 3)
- StaminaUsage: enabled, every tool and blocking -25
- Egg: enabled, showHatchTime true, hatchTime 150, growTime 1500
- Procreation: enabled, loveInformation true, offspringInformation true, pregnancyDurationMultiplier -50
- ShieldGenerator: enabled, autoFuel true, autoRange 50
- Ship: enabled, forwardSpeed 25, rudderSpeed 25
- Off: Hotkeys, FreePlacementRotation, GridAlignment, AdvancedBuildingMode, AdvancedEditingMode,
  FirstPerson, Ward, Armor, Shields, PlayerProjectile, MonsterProjectile, Chat, Time, Adrenaline,
  EitrUsage, HealthUsage, Turret

## PortalStations (regenerate 1.4.7 defaults, then)
- 1 - Teleport Anything = On
- 2 - Portable Portal Use Fuel = Off
- Edit = Off, Ownership = Off
- everything else default (Portal To Players Off, static portal fuel Off, build costs default)

## TeleportCreatures
- server yml: defaults (allies on, enemies off)
- local yml: ally mode OnlyFollow

## TeleportCarts: server yml defaults

## Quick Stack (client): AllowAreaStackingInMultiplayerWithoutMUC = true, hotbar behaviour default
## PlantEasily (client): defaults + ReplantOnHarvest = true
