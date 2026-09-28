#!/usr/bin/env python3
"""Turn off lsfg-vk frame generation for FFX while it loads into and out of battles.

FFX loads a fixed amount per rendered frame, and frame generation caps the
game's real frame rate (4x at 120 Hz = 30 real FPS), which stretches both
loading into a battle and the black screen before the victory summary to ~10 s.

The External File Loader (with logAccess=true in
modules/config/ff10-file-loader.ini) logs every file the game reads to
hook.log. Loading starts are recognizable there:
  btlmap/ file read           -> a battle is loading
  sfx/<lang>/4003.fev read    -> the battle is over and the field is loading
                                 (also read when entering the field from a save)
On either, the FFX profile multiplier is set to 1; once the game has read
nothing for a moment, the previous multiplier is restored.
lsfg-vk hot-reloads the multiplier, so no restart is needed.

Environment overrides:
  FFX_GAME_DIR       game folder (default: the standard Steam library path)
  LSFGVK_CONFIG      lsfg-vk config file (same variable lsfg-vk itself uses)
  FFX_LSFG_PROFILE   name of the FFX profile in that config
"""
import json, os, re, signal, sys, time

GAME = os.environ.get('FFX_GAME_DIR') or os.path.expanduser(
    '~/.local/share/Steam/steamapps/common/FINAL FANTASY FFX&FFX-2 HD Remaster')
HOOK_LOG = os.path.join(GAME, 'hook.log')
CONF = os.environ.get('LSFGVK_CONFIG') or os.path.expanduser('~/.config/lsfg-vk/conf.toml')
STATE = os.path.join(os.path.dirname(CONF), 'ffx-fg-switch.json')
PROFILE = os.environ.get('FFX_LSFG_PROFILE') or 'FINAL FANTASY X/X-2 HD Remaster'
TRIGGERS = (('battle loading', re.compile(r'ps3data/btlmap/')),
            ('battle over', re.compile(r'sound_pc/sfx/[^/]+/4003\.fev')))
QUIET_S = 1.5           # loading counts as done after this long without any reads
GIVE_UP_S = 30.0        # restore anyway if loading never goes quiet
POLL_S = 0.1

def log(msg):
    print(time.strftime('%H:%M:%S'), msg, flush=True)

def profile_span(text):
    start = text.index(f'name = "{PROFILE}"')
    nxt = text.find('[[profile]]', start)
    return start, (nxt if nxt != -1 else len(text))

def get_multiplier():
    """The profile's multiplier, or None if the profile or setting is missing."""
    try:
        text = open(CONF).read()
        a, b = profile_span(text)
    except (OSError, ValueError):
        return None
    m = re.search(r'^multiplier = (\d+)$', text[a:b], re.M)
    return int(m.group(1)) if m else None

def set_multiplier(n):
    text = open(CONF).read()
    a, b = profile_span(text)
    block = re.sub(r'^multiplier = \d+$', f'multiplier = {n}', text[a:b], count=1, flags=re.M)
    with open(CONF, 'w') as f:   # in-place write: lsfg-vk watches this file
        f.write(text[:a] + block + text[b:])
    log(f'multiplier -> {n}')

def save_state(restore):
    with open(STATE, 'w') as f:
        json.dump({'restore': restore}, f)

def load_state():
    try:
        return json.load(open(STATE)).get('restore')
    except (OSError, ValueError):
        return None

def restore_multiplier(reason):
    restore = load_state()
    if restore:
        set_multiplier(restore)
        save_state(None)
    log(reason)

def on_stop(signum, frame):
    if load_state():
        restore_multiplier('stopping mid-load; restored multiplier')
    sys.exit(0)

def main():
    signal.signal(signal.SIGTERM, on_stop)
    if load_state():                       # stopped mid-load last time
        restore_multiplier('restored multiplier left over from last run')
    if get_multiplier() is None:
        log(f'warning: no profile named "{PROFILE}" with a multiplier in {CONF}; '
            'loads will not be sped up until it exists')

    pos = os.path.getsize(HOOK_LOG) if os.path.exists(HOOK_LOG) else 0
    partial = ''
    loading_since = None                   # set while we have frame generation off
    last_read = None
    log('watching ' + HOOK_LOG)
    while True:
        time.sleep(POLL_S)
        try:
            size = os.path.getsize(HOOK_LOG)
        except OSError:
            continue
        if size < pos:                     # game relaunched: the loader starts a new log
            pos, partial = 0, ''
        new = ''
        if size > pos:
            with open(HOOK_LOG, 'rb') as f:
                f.seek(pos)
                new = f.read().decode('utf-8', 'replace')
                pos = f.tell()
        lines = (partial + new).split('\n')
        partial = lines.pop()
        now = time.time()

        for line in lines:
            if loading_since is None:
                trigger = next((label for label, pattern in TRIGGERS if pattern.search(line)), None)
                if trigger:
                    current = get_multiplier()
                    if current is not None and current > 1:
                        save_state(current)
                        set_multiplier(1)
                    loading_since = now
                    log(f'{trigger}: loading started (multiplier was {current})')
            last_read = now

        if loading_since is not None:
            if now - last_read >= QUIET_S:
                took, loading_since = now - loading_since - QUIET_S, None
                restore_multiplier(f'loading done ({took:.1f}s)')
            elif now - loading_since >= GIVE_UP_S:
                loading_since = None
                restore_multiplier('still loading after 30s; restored anyway')

if __name__ == '__main__':
    main()
