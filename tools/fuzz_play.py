#!/usr/bin/env python3
"""fuzz_play.py - play a scene the bench never plays with random input, on the host, to find untranslated code
(what crashes the Amiga build) and to collect its entry points for the translator.

usage: tools/fuzz_play.py check FIRST LAST            run tools/play.c (out/play) for seeds FIRST..LAST-1,
                                                      print the seeds that stop at an untranslated address
       tools/fuzz_play.py cov FIRST LAST out.txt      run tools/nesref/verify.c (out/verify) with VERIFY_COV for
                                                      those seeds and write the entry points they reach
                                                      (put the file in tools/flow/ and run tools/make_assets.sh)
Run from the project folder (verify.c reads src/gen_waits.txt from there). The scene is set by SETUP (presses
that start a 1-player game, so the player pitches in the bottom of the first, from about tick 7,750) and by the
random presses after START: down+B, A, other buttons and directions, 1-40 ticks each, until END.
"""
import random, subprocess, sys, os, concurrent.futures as cf
SETUP = "40-43:40 170-173:40 260-263:40 340-343:40 420-423:40 500-503:40 580-583:40"
START, END, TICKS = 7750, 11500, 11600

def script(seed):
    r = random.Random(seed); segs = []; t = START
    while t < END:
        t += r.randint(5, 60); k = r.random()
        if k < 0.5: m = 0x24                                   # down + B (what the user pressed)
        elif k < 0.7: m = 0x10                                 # A: pitch
        elif k < 0.8: m = r.choice([0x20, 0x04, 0x14, 0x34, 0x28, 0x21, 0x22, 0x2c])
        else: m = r.choice([1, 2, 4, 8, 0x11, 0x12, 0x18])
        segs.append('%d-%d:%x' % (t, t + r.randint(1, 40), m))
    return SETUP + ' ' + ' '.join(segs)

def check(seed):
    out = subprocess.run(['out/play', str(TICKS), script(seed)], capture_output=True, text=True).stdout.strip().split('\n')[-1]
    return seed, out

def cov(seed):
    f = 'out/fuzz_cov_%d.txt' % seed
    subprocess.run(['out/verify', str(TICKS), '/dev/null'], env=dict(os.environ, PLAY=script(seed), VERIFY_COV=f), capture_output=True)
    return f

if __name__ == '__main__':
    mode, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    with cf.ThreadPoolExecutor(os.cpu_count() or 4) as ex:
        if mode == 'check':
            bad = 0
            for seed, res in ex.map(check, range(a, b)):
                if 'STOPPED' in res: bad += 1; print(seed, res)
            print('%d of %d runs stopped' % (bad, b - a))
        else:
            lines = set()
            for f in ex.map(cov, range(a, b)):
                if os.path.exists(f): lines.update(open(f).read().splitlines()); os.remove(f)
            open(sys.argv[4], 'w').write('\n'.join(sorted(lines)) + '\n'); print(len(lines), 'entry points')
