#!/bin/bash
# Usage: tools/bench_audio.sh <out.wav> <ticks> [extra fs-uae options, e.g. --fast_memory=4096]
# Runs the bench (tools/bench.sh on dist/<NAME>) and records what the emulated Amiga plays: FS-UAE's OpenAL
# output goes to a wave file (OpenAL Soft's "wave" backend), 48 kHz stereo float (left = Paula 0 and 3,
# right = 1 and 2). Then prints where the recording is loud: tools/wavscan.py.
# This is how the silent voice samples were found: the bench numbers and the host sound test were fine, only
# the fast-RAM machine was silent (the samples' hunk lost its chip RAM flag). Build with -DSND_ONLY_DMC to hear
# only the DMC samples.
cd "$(dirname "$0")/.."
. ./port.conf
OUT="$(realpath -m "$1")"; N="$2"; shift 2
CONF=$(mktemp /tmp/alsoft.XXXXXX.conf)
printf 'drivers=wave\n[wave]\nfile=%s\n' "$OUT" > "$CONF"
rm -f "$OUT"
ALSOFT_CONF="$CONF" tools/bench.sh dist "$NAME" "$N" "${OUT%.wav}.png" "$@"
rm -f "$CONF"
python3 tools/wavscan.py "$OUT"
