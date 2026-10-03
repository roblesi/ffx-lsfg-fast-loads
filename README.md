# ffx-lsfg-fast-loads

Keep **Final Fantasy X HD Remaster** at 120 FPS with [lsfg-vk](https://lsfg-vk.dev/) frame generation on Linux, **without the ~10-second loads** it causes around every battle and area change.

A small background service turns frame generation off only while the game is loading, then turns it back on:

| Transition | Frame generation always on (4x) | With this service |
|---|---|---|
| Loading into a battle | ~11 s | ~1 s |
| Last enemy dies → victory summary | ~10–14 s | ~1 s |
| Exploring and fighting | 120 FPS | 120 FPS |

During each load the game drops to its native 30 FPS for about a second, which is hard to notice behind the transition.

## Why frame generation slows loading

FFX loads a fixed amount of data for every frame it renders. lsfg-vk only has a vsync pacing mode, where each real frame is shown for `multiplier` refreshes of the display. At 4x on a 120 Hz display the game can never render more than **30 real frames per second, even while loading**. Loading is capped at the same rate, and big texture packs such as FFX Re-Remastered make it much worse.

Measured on the same save: with frame generation off, the ~550 MB loaded after a battle arrived in under half a second. At 4x the same load took about 10 seconds.

## How it works

With `logAccess=true`, ffgriever's [External File Loader](https://www.nexusmods.com/finalfantasyxx2hdremaster/mods/150) writes every file the game reads to `hook.log`, with timestamps. These reads mark the start of the slow loads:

| Read | Meaning |
|---|---|
| any file under `ps3data/btlmap/` | a battle is loading |
| `sound_pc/sfx/<lang>/2xxx.fev` or `4xxx.fev` | a field area's sound banks: the field is loading. This is the first read after a battle ends. |
| `map/<area>/<map>/bin/mapout.vpa` | a field map is loading. This is the first read when moving between areas. |

During a battle the game only reads `0xxx`, `1xxx` and `9999` sound banks, so these rules don't fire mid-fight. Which `4xxx` bank loads depends on the area (for example `4003` in Besaid and `4031` in Kilika), so the rules match the ranges rather than one file.

The service follows `hook.log`, and on either read it sets the FFX profile's `multiplier` to 1 in the lsfg-vk config. Once the game has read nothing for 1.5 s, it restores the previous multiplier. lsfg-vk hot-reloads the multiplier, so the game never needs a restart.

If you change the multiplier yourself (in the config or the Decky plugin), the service restores your new value after each load. If it is stopped mid-load, it restores the multiplier on exit or on its next start.

## Requirements

- FFX/X-2 HD Remaster (Steam) running under Proton
- [FFX/X-2 HD External File Loader](https://www.nexusmods.com/finalfantasyxx2hdremaster/mods/150) (tested with 1.1.2 and 1.2.0; the game update of 30 September 2026 needs **1.2.0 or later**)
- [lsfg-vk](https://lsfg-vk.dev/) 2.x with an FFX profile in `~/.config/lsfg-vk/conf.toml`. [Decky LSFG-VK](https://github.com/xXJSONDeruloXx/decky-lsfg-vk) creates one named `FINAL FANTASY X/X-2 HD Remaster` when you configure the game. It requires owning [Lossless Scaling](https://store.steampowered.com/app/993090/Lossless_Scaling/).
- systemd (user services) and Python 3

Tested on CachyOS (Steam Game Mode), Proton 11.0, lsfg-vk 2.0.0 and Decky LSFG-VK 0.14.4, with the FFX Re-Remastered Extreme texture pack.

## Install

```bash
git clone https://github.com/roblesi/ffx-lsfg-fast-loads.git
cd ffx-lsfg-fast-loads
./install.sh
```

The installer turns on the loader's access logging (backing up its config first), installs the script to `~/.local/bin`, and enables the `ffx-fg-switch` user service. **Restart the game afterwards** so the loader starts logging.

If your setup differs from the defaults, set these when running the installer. They are passed on to the service:

| Variable | Default |
|---|---|
| `FFX_GAME_DIR` | `~/.local/share/Steam/steamapps/common/FINAL FANTASY FFX&FFX-2 HD Remaster` |
| `LSFGVK_CONFIG` | `~/.config/lsfg-vk/conf.toml` |
| `FFX_LSFG_PROFILE` | `FINAL FANTASY X/X-2 HD Remaster` |

For example: `FFX_GAME_DIR=/mnt/games/steamapps/common/"FINAL FANTASY FFX&FFX-2 HD Remaster" ./install.sh`

## Checking that it works

```bash
journalctl --user -u ffx-fg-switch -f
```

Each battle should log something like:

```
multiplier -> 1
battle loading: loading started (multiplier was 4)
multiplier -> 4
loading done (1.2s)
multiplier -> 1
field loading: loading started (multiplier was 4)
multiplier -> 4
loading done (0.6s)
```

## Notes

- `hook.log` grows by about 3.5 MB per hour of play with access logging on. The loader starts a new one each time the game launches.
- The trigger rules are at the top of `ffx-fg-switch.py`. They were worked out from Besaid, the boat and Kilika; if some load in a later area stays slow, its first reads in `hook.log` show what to add.
- Only FFX is handled, not FFX-2.
- On distributions that set `KillUserProcesses=yes` (for example CachyOS's Steam Deck mode), run it as the user service rather than a background process started over SSH.

## Uninstall

```bash
./uninstall.sh
```

This stops and removes the service and turns the loader's access logging back off.

## Credits

- ffgriever for the External File Loader and its access logging
- PancakeTAS and contributors for lsfg-vk
- xXJSONDeruloXx for Decky LSFG-VK
- THS for Lossless Scaling
