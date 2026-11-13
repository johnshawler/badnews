#!/usr/bin/env python3
"""late.py - why frames were late in a debug run (tools/debug_run.sh): each late vertical blank is put in one class.
usage: tools/late.py <debug-out-dir> [n examples]
  logic spike   one tick of the frame took more than 60,000 colour clocks (screen loads)
  display       the display took more than 40,000
  steady        neither: the frame was just over the budget
Examples: (tick, late vblanks, logic colour clocks of the frame's ticks, display colour clocks[, display parts:
cells, stream + row sync, sprites, grouping, retile, edges])."""
import sys, struct, os
d = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
f = open(os.path.join(d, 'frames.bin'), 'rb').read(); full = [struct.unpack('>9I', f[i:i + 36]) for i in range(0, len(f) - 35, 36)]
fr = [x[:3] for x in full]; parts = {x[0]: x[3:] for x in full}   # display parts: cells, stream+rows, sprites, grouping, retile, edges
t = open(os.path.join(d, 'ticktime.bin'), 'rb').read(); tt = struct.unpack('>%dI' % (len(t) // 4), t)
cat = {'logic spike': [], 'display': [], 'steady': []}
for (v0, k0, d0), (v1, k1, d1) in zip(fr, fr[1:]):
    late = v1 - v0 - 1
    if late <= 0: continue
    lg = tt[k0:k1]
    c = 'logic spike' if lg and max(lg) > 60000 else 'display' if d1 > 40000 else 'steady'
    cat[c].append((k1, late, sum(lg), d1) + ((parts[v1],) if c == 'display' else ()))
for k, v in cat.items():
    print('%-12s %4d late in %3d frames' % (k, sum(x[1] for x in v), len(v)), v[:n])
