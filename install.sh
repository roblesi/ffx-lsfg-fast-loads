#!/usr/bin/env bash
# Install ffx-fg-switch as a systemd user service.
# Optional overrides (also passed on to the service): FFX_GAME_DIR, LSFGVK_CONFIG, FFX_LSFG_PROFILE
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
game=${FFX_GAME_DIR:-$HOME/.local/share/Steam/steamapps/common/FINAL FANTASY FFX&FFX-2 HD Remaster}
ini="$game/modules/config/ff10-file-loader.ini"
unit_dir=$HOME/.config/systemd/user

if [ ! -f "$ini" ]; then
    echo "The FFX External File Loader was not found in: $game" >&2
    echo "Install it first, or set FFX_GAME_DIR to your game folder." >&2
    exit 1
fi

# The switcher reads the loader's access log, so access logging must be on.
if grep -q '^logAccess=true' "$ini"; then
    echo "Loader access logging is already on."
else
    [ -f "$ini.bak" ] || cp "$ini" "$ini.bak"
    sed -i 's/^logAccess=false/logAccess=true/' "$ini"
    if grep -q '^logAccess=true' "$ini"; then
        echo "Turned on loader access logging (original config saved as ${ini##*/}.bak)."
        echo "Restart the game for this to take effect."
    else
        echo "Could not find logAccess in $ini; set logAccess=true there yourself." >&2
        exit 1
    fi
fi

install -Dm755 "$here/ffx-fg-switch.py" "$HOME/.local/bin/ffx-fg-switch.py"
install -Dm644 "$here/ffx-fg-switch.service" "$unit_dir/ffx-fg-switch.service"

# Pass any overrides on to the service.
dropin="$unit_dir/ffx-fg-switch.service.d/override.conf"
env_lines=()
for var in FFX_GAME_DIR LSFGVK_CONFIG FFX_LSFG_PROFILE; do
    [ -n "${!var:-}" ] && env_lines+=("Environment=\"$var=${!var}\"")
done
if [ ${#env_lines[@]} -gt 0 ]; then
    mkdir -p "${dropin%/*}"
    printf '[Service]\n%s\n' "${env_lines[@]}" > "$dropin"
    echo "Wrote overrides to $dropin"
fi

systemctl --user daemon-reload
systemctl --user enable ffx-fg-switch.service
systemctl --user restart ffx-fg-switch.service
sleep 1
systemctl --user --no-pager status ffx-fg-switch.service | head -3
journalctl --user -u ffx-fg-switch --no-pager -n 3 -o cat
