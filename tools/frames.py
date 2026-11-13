#!/usr/bin/env python3
"""frames.py - from a debug run (tools/debug_run.sh): late vertical blanks and per-tick logic time by tick range.
usage: tools/frames.py <debug-out-dir> [range=250] [first_tick last_tick: list the slowest frames there]
frames.bin: (vertical blank, tick, display colour clocks) at every drawn frame; ticktime.bin: colour clocks of each tick's logic."""
import sys, struct, os
d = sys.argv[1]; step = int(sys.argv[2]) if len(sys.argv) > 2 else 250
f = open(os.path.join(d, 'frames.bin'), 'rb').read()
fr = [struct.unpack('>9I', f[i:i + 36])[:3] for i in range(0, len(f) - 35, 36)]
t = open(os.path.join(d, 'ticktime.bin'), 'rb').read(); tt = struct.unpack('>%dI' % (len(t) // 4), t)
late = {}; shown = {}
for (v0, k0, d0), (v1, k1, d1) in zip(fr, fr[1:]):
    b = k1 // step; shown[b] = shown.get(b, 0) + 1; late[b] = late.get(b, 0) + max(0, v1 - v0 - 1)
print('ticks        frames late   fps   logic/tick: median  p90   max')
for b in sorted(shown):
    s = sorted(tt[b * step:(b + 1) * step]) or [0]
    fps = 50.0 * shown[b] / (shown[b] + late[b])
    print('%5d-%5d  %5d %5d %5.1f   %7d %7d %7d' % (b * step, (b + 1) * step - 1, shown[b], late[b], fps, s[len(s) // 2], s[int(len(s) * .9)], s[-1]))

# the slowest frames: ticks run before them, their logic time, the display time (colour clocks; 71,051 a frame)
if len(sys.argv) > 4:
    a, b = int(sys.argv[3]), int(sys.argv[4])
    rows = []
    for (v0, k0, d0), (v1, k1, d1) in zip(fr, fr[1:]):
        if a <= k1 < b:
            lg = sum(tt[k0:k1]); rows.append((v1 - v0, k1, k1 - k0, lg, d1))
    print('vblanks tick nticks logic display total')
    for r in sorted(rows, key=lambda r: -(r[3] + r[4]))[:25]: print('%3d %6d %3d %7d %7d %7d' % (r[0], r[1], r[2], r[3], r[4], r[3] + r[4]))
