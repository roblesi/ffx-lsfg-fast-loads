#!/usr/bin/env bash
# Remove ffx-fg-switch and turn the loader's access logging back off.
set -euo pipefail

game=${FFX_GAME_DIR:-$HOME/.local/share/Steam/steamapps/common/FINAL FANTASY FFX&FFX-2 HD Remaster}
ini="$game/modules/config/ff10-file-loader.ini"
unit_dir=$HOME/.config/systemd/user
conf=${LSFGVK_CONFIG:-$HOME/.config/lsfg-vk/conf.toml}

# Stopping the service restores the multiplier if it was mid-load.
systemctl --user disable --now ffx-fg-switch.service 2>/dev/null || true
rm -f "$HOME/.local/bin/ffx-fg-switch.py" "$unit_dir/ffx-fg-switch.service"
rm -rf "$unit_dir/ffx-fg-switch.service.d"
rm -f "${conf%/*}/ffx-fg-switch.json"
systemctl --user daemon-reload

if [ -f "$ini" ] && grep -q '^logAccess=true' "$ini"; then
    sed -i 's/^logAccess=true/logAccess=false/' "$ini"
    echo "Turned loader access logging back off."
fi
echo "ffx-fg-switch removed."
