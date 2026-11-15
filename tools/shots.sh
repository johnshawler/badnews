#!/bin/bash
# Usage: tools/shots.sh <exe in dist/> <ticks> <outdir> <from_s> <to_s> <step_s> [fs-uae options]
# Boots the emulated A1200 like tools/bench.sh ("<exe> bench <ticks>") and saves a screenshot every <step_s>
# seconds from <from_s> to <to_s> after the emulator starts: to watch a scene the way the Amiga shows it
# (build with -DPLAY_SCRIPT -Iout to play a scripted game in place of the bench input).
cd "$(dirname "$0")/.."
EXE="$1"; N="$2"; OUT="$(realpath -m "$3")"; FROM="$4"; TO="$5"; STEP="$6"; shift 6
HD=$(mktemp -d /tmp/shots.XXXXXX); mkdir -p "$HD/S" "$OUT"; cp "dist/$EXE" "$HD/"
printf '%s bench %s\n' "$EXE" "$N" > "$HD/S/startup-sequence"
for n in $(seq 170 190); do [ ! -e /tmp/.X11-unix/X$n ] && DNUM=$n && break; done
Xvfb :$DNUM -screen 0 1024x768x24 >/dev/null 2>&1 & XP=$!; sleep 1; export DISPLAY=:$DNUM SDL_AUDIODRIVER=dummy
B=$(mktemp -d /tmp/fsb.XXXXXX)
fs-uae --base_dir="$B" --amiga_model=A1200 --hard_drive_0="$HD" --hard_drive_0_label=SYS --fullscreen=0 \
  --window_width=752 --window_height=572 --video_sync=0 --automatic_input_grab=0 --initial_input_grab=0 "$@" >/dev/null 2>&1 & UP=$!
python3 - "$FROM" "$TO" "$STEP" "$OUT" ":$DNUM" <<'PY'
import sys, time, subprocess
a, b, st, out, disp = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), sys.argv[4], sys.argv[5]
t0 = time.time(); k = 0; t = a
while t <= b:
    time.sleep(max(0, t0 + t - time.time()))
    subprocess.run(['import', '-display', disp, '-window', 'root', '%s/shot_%04d.png' % (out, k)]); k += 1; t += st
PY
kill $UP; sleep 1; kill -9 $UP 2>/dev/null; kill $XP; rm -rf "$B" "$HD"
