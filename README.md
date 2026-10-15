# Alien Shooter 2 — Co-op Campaign

A two-player LAN campaign mod for the original **Alien Shooter 2**. It uses the game's native DirectPlay networking and original interface, with campaign scripts adapted for two independent heroes.

**Current release: 0.5.0-preview.** Download the installer or portable ZIP from [Releases](https://github.com/slopmod/AlienShooter2CoopMod/releases). Players do not need Python.

## Requirements

- Windows 10/11 x64 with **Legacy Components → DirectPlay** enabled.
- A complete supported **Russian original Alien Shooter 2 1.1 (v1.1-rus)** installation on each PC. The verified build comes from the Gold edition; the launcher validates the actual files.
- Both players use the **same mod version, mod language and campaign content**.

The supported `AlienShooter.exe` has file version **2.5.0.1**, size **2,244,608 bytes**, and SHA-256:

```text
5128048a4ac922266f4664c1c00e18cc924b1fd3aafd451081799c8c519e3808
```

**Reloaded alone and English game executables are not supported.** Selecting English translates the mod's own text; original dialogue, item names, menus and audio remain in the base game's Russian language.

## Install and play

1. Install the latest release into a **separate writable folder**, accepting the default location if desired. Choose English (default) or Russian. Alternatively, extract the entire portable ZIP.
2. Open `AS2CoopCampaign.exe`, select the original game's folder containing `AlienShooter.exe`, then press **PLAY**. First launch prepares a separate game copy; the original installation is preserved.
3. Both players open **Co-op campaign** in the game's main menu. The host selects **New game → Host game**; the partner uses **Join game**, searches the LAN and joins. Enter the host's local IP if discovery fails.
4. Each player creates a character and presses **Start**. The campaign begins when both confirm. Duplicate portraits, colours and abilities are allowed.

To continue, the host selects an entry under **Saved games**; the partner joins normally. Character creation is skipped and the save transfers automatically. Allow the game through Windows Firewall on your private network if prompted.

Full instructions: [English](INSTALL_EN.txt) · [Русский](INSTALL_RU.txt). The launcher can switch the mod language before starting the game; both players must select the same language.

## Implemented

- Two-player adaptations for all **15 original missions**, plus two bundled Reloaded road missions: `1…7 → 7.2 → 7.3 → 8…15`.
- Personal characters, inventories, equipment and progression; **shared money and shop stock**.
- Original HUD, inventory, character creation and shop screens, including inventory and shop drag-and-drop.
- Cooperative script handling for objectives, interactions, portals, vehicles and mission transitions.
- Mission-boundary autosaves, host save selection, automatic save transfer and both characters restored on load.
- Ally revival: stand beside a fallen partner for **5 seconds**; moving away resets the timer. After both die, the host can right-click to retry the last campaign save.
- English/Russian mod text and installer, with fixed Russian-source dialogue timings.
- In-game display settings, a windowed 800×600 recovery option and optional two-window/infinite-health modes for local checks.

This is a preview. Full manual coverage of every campaign route is incomplete. Saves restart at mission boundaries; progress within an unfinished mission is not saved. Inventory stack splitting, ground drops, implant purchases, repairs, buyback and some personal-panel tabs are not connected. Back up `saves/campaign` before updating. Original single-player saves are not compatible.

## Source and build

This repository contains the production launcher, native patchers, campaign adapters and script templates. Full game data, generated binaries, installed dependencies, private settings and saves are excluded. Release packages include only the two additional maps and their required resource subset; players still supply the complete supported base game.

Use **64-bit Windows Python 3.11+** with Tk and **Inno Setup 6.7.3**. From the repository root:

```powershell
python -m pip install --target tools/vendor -r requirements.txt
python -m pip install --target tools/packaging -r requirements-build.txt
python -B build_campaign_release.py --reloaded-source "D:\Games\Alien Shooter 2 Reloaded" --compiler "C:\Tools\Inno Setup 6\ISCC.exe"
```

The build validates the donor resources and writes the standalone launcher, ZIP, installer and SHA-256 files to `dist/`. Only package developers need the supported Reloaded resource donor; release users do not need a separate Reloaded installation. `--vendor` and `--packaging` can point to existing dependency directories. The release manifest records dependency versions, content hashes and the source commit when Git is available.

For a source session, install `requirements.txt`, set `$env:AS2_COOP_RELOADED_DIR` to the supported Reloaded donor path to enable the two additional maps, then run `python -B campaign_launcher.py` (or `Start Campaign.cmd`). Select the supported original game in the launcher. Without additional content, source sessions use the 15 original missions.

## Code map

| Area | Files |
| --- | --- |
| Launcher, installation and sessions | `campaign_launcher.py`, `launch_old_native_menu.py`, `old_native_installation.py`, `old_native_runtime*.py`, `old_native_process.py` |
| Campaign build and mission registry | `old_native_campaign_build.py`, `old_native_campaign_missions.py`, `old_native_campaign_progression.py` |
| Shared campaign mechanics | `old_native_interaction_registry.py`, `old_native_interaction_schema.py`, `old_native_level*_interactions.py`, `old_native_campaign_portals.py`, `old_native_campaign_revival.py` |
| Native engine patches and network commands | `old_native_*_patch.py`, `old_native_campaign_command_patch.py` |
| Saves and transfer | `old_native_checkpoints.py`, `old_native_campaign_checkpoint.py`, `old_native_campaign_browser.py`, `old_native_campaign_retry.py` |
| Localization and dialogue timing | `old_native_localization.py`, `locales/`, `data/old-russian-dialogue-timing.json` |
| Scripts and resource formats | `templates/`, `tools/map_format.py`, `old_native_reloaded_*.py` |
| Release packaging | `build_campaign_release.py`, `scripts/campaign-installer.iss` |

Native patches are specific to the supported executable and resource hashes. Preserve these checks when extending the mod. Game assets remain the property of their respective rights holders; bundled third-party software notices are provided in each release's `LICENSES` directory.
