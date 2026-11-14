#!/usr/bin/env python3
"""wavscan.py - where a recording from tools/bench_audio.sh is loud.

usage: tools/wavscan.py file.wav [threshold 0.01] [step seconds 0.1]
Reads a float or 16-bit PCM wave file and prints, per step, the peak of the left and right channels when either
is above the threshold, merged into runs: "30.2-30.6 s  peak L 0.163 R 0.000".
"""
import sys, struct, array
b = open(sys.argv[1], 'rb').read()
thr = float(sys.argv[2]) if len(sys.argv) > 2 else 0.01
step = float(sys.argv[3]) if len(sys.argv) > 3 else 0.1
i = 12; fmt = None; data = b''
while i < len(b) - 8:
    cid = b[i:i + 4]; sz = struct.unpack('<I', b[i + 4:i + 8])[0]
    if cid == b'fmt ': fmt = struct.unpack('<HHIIHH', b[i + 8:i + 24])
    if cid == b'data': data = b[i + 8:i + 8 + sz] if sz else b[i + 8:]; break
    i += 8 + sz + (sz & 1)
ch, rate, bits = fmt[1], fmt[2], fmt[5]
if bits == 32: a = array.array('f'); a.frombytes(data[:len(data) // 4 * 4]); scale = 1.0
else: a = array.array('h'); a.frombytes(data[:len(data) // 2 * 2]); scale = 32768.0
n = len(a) // ch; w = max(1, int(rate * step))
print('%d channels, %d Hz, %.1f s' % (ch, rate, n / rate))
run = None
for k in range(0, n, w):
    seg = a[k * ch:(k + w) * ch]
    pl = max((abs(x) for x in seg[0::ch]), default=0) / scale
    pr = max((abs(x) for x in seg[1::ch]), default=0) / scale if ch > 1 else 0
    t = k / rate
    if max(pl, pr) > thr:
        if run is None: run = [t, t + step, pl, pr]
        else: run[1] = t + step; run[2] = max(run[2], pl); run[3] = max(run[3], pr)
    elif run is not None:
        print('%6.1f-%6.1f s  peak L %.3f R %.3f' % tuple(run)); run = None
if run is not None: print('%6.1f-%6.1f s  peak L %.3f R %.3f' % tuple(run))
