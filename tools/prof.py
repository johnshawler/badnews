#!/usr/bin/env python3
"""prof.py - read the 1 kHz profile of a debug run (tools/debug_run.sh) and name the hot routines.

usage: tools/prof.py <debug-out-dir> <exe> [first_tick last_tick] [-n 40]

<debug-out-dir> holds prof.bin (runtime address of reset_fn, of game_tick, then one PC per sample) and
frames.bin (vertical blank, tick and display time at every drawn frame). With a tick range, only the samples taken while the
logic was in that range count (the busiest scene, not the whole run). Symbols come from m68k-amigaos-nm of
<exe> (run in the crosstools Docker image). The translated code (src/gen68k.s with src/nes68k.s included) is
one hunk, placed by reset_fn; the C code is another, placed by game_tick. Samples elsewhere (other assembly
hunks, the OS) are counted as "other".
"""
import sys, struct, subprocess, bisect, collections, os

args = [a for a in sys.argv[1:]]
top = 40
if '-n' in args: i = args.index('-n'); top = int(args[i + 1]); del args[i:i + 2]
out, exe = args[0], args[1]
t0, t1 = (int(args[2]), int(args[3])) if len(args) >= 4 else (0, 1 << 30)

d = open(os.path.join(out, 'prof.bin'), 'rb').read()
base, cbase = struct.unpack('>II', d[:8])
pcs = struct.unpack('>%dI' % ((len(d) - 8) // 4), d[8:])
f = open(os.path.join(out, 'frames.bin'), 'rb').read()
fr = [struct.unpack('>9I', f[i:i + 36])[:3] for i in range(0, len(f) - 35, 36)]      # (vblank, tick) per drawn frame

nm = subprocess.run(['docker', 'run', '--rm', '-v', os.getcwd() + ':/work', '-w', '/work', 'amigadev/crosstools:m68k-amigaos',
                     'm68k-amigaos-nm', exe], capture_output=True, text=True).stdout
asm_syms = set()
for src in ('src/gen68k.s', 'src/nes68k.s'):
    if os.path.exists(src):
        for line in open(src):
            if line[:1] not in ' \t;*\n' and ':' in line: asm_syms.add(line.split(':')[0].strip())
gen, csym = [], []
for line in nm.split('\n'):
    p = line.split()
    if len(p) != 3 or p[1] not in 'Tt': continue
    a, name = int(p[0], 16), p[2]
    (gen if name in asm_syms or name.lstrip('_') in asm_syms or name[:1] == 'F' and name[2:3] == '_' else csym).append((a, name))
gen.sort(); csym.sort()
goff = dict((n, a) for a, n in gen)
# reset_fn points at the reset entry of the translation
reset_name = None
for line in open('src/gen68k.s'):
    if line.startswith('_reset_fn:'): reset_name = line.split()[-1]; break
gbase = base - goff[reset_name]
cofs = dict((n, a) for a, n in csym)
cstart = cbase - cofs['_game_tick']
gend = gbase + (gen[-1][0] + 0x4000)
cend = cstart + csym[-1][0] + 0x1000

# samples come at 1 kHz from the start of the game, vertical blanks at 50 Hz: sample k falls in vertical blank
# k / 20, and frames.bin says which tick the logic had reached by then
fv = [x[0] for x in fr]
def tick_of(k):
    i = bisect.bisect_right(fv, k // 20) - 1
    return fr[i][1] if i >= 0 else 0

cnt = collections.Counter(); total = 0
for k, pc in enumerate(pcs):
    t = tick_of(k)
    if not (t0 <= t < t1): continue
    total += 1
    if gbase <= pc < gend:
        i = bisect.bisect_right(gen, (pc - gbase, '\xff')) - 1
        cnt['68k ' + gen[i][1] if i >= 0 else '68k ?'] += 1
    elif cstart <= pc < cend:
        i = bisect.bisect_right(csym, (pc - cstart, '\xff')) - 1
        cnt['C   ' + csym[i][1] if i >= 0 else 'C ?'] += 1
    else:
        cnt['other'] += 1
print('samples %d in ticks %d..%d (of %d)' % (total, t0, t1, len(pcs)))
for name, c in cnt.most_common(top):
    print('%6d %5.1f%%  %s' % (c, 100.0 * c / max(total, 1), name))
