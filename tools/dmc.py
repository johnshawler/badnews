#!/usr/bin/env python3
"""dmc.py - convert the NES DMC (delta-modulation) samples a game plays into Paula samples, on the host.

usage: dmc.py rom.nes game out.bin       (tools/make_assets.sh runs it when tools/games/<game>.py lists DMC)

tools/games/<game>.py lists the samples as DMC = [(rate, address byte, length byte, initial level), ...]: the
values the game writes to $4010 (rate index, low 4 bits), $4012, $4013 and $4011 before it starts one (find them
with a host driver that prints apu_reg when apu_trig bit 4 is set). The sample is at $C000 + 64 * address, it is
16 * length + 1 bytes long and is read from the fixed bank ($C000-$FFFF), as on the NES.

Each bit moves a 7-bit level up or down by 2. The level is centred (its mean removed), faded in and out over a
few samples (no click), and when the NES rate is above Paula's limit the samples are averaged in pairs.

out.bin (big-endian): 16 entries of 16 bytes  {u8 address, u8 length, u8 rate, u8 0, u32 offset of the PCM data
from the start of the file, u16 words, u16 Paula period (PAL), u16 drawn frames it lasts at 50 Hz, u16 0},
then the PCM data (signed 8-bit, each sample word-aligned). Unused entries are zero.
"""
import sys, os, struct, importlib
NTSC_RATE = [428, 380, 340, 320, 286, 254, 226, 214, 190, 160, 142, 128, 106, 84, 72, 54]   # CPU cycles a bit
CPU = 1789773
PAULA = 3546895
rom, game, out = sys.argv[1:4]
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'games'))
g = importlib.import_module(game)
d = open(rom, 'rb').read()
prg = d[16:16 + d[4] * 16384]
fixed = prg[-16384:]
table, pcm = [], b''
for (rate, addr, length, level) in getattr(g, 'DMC', [])[:16]:
    a = 0xc000 + addr * 64 - 0xc000
    n = length * 16 + 1
    bits, lv = [], level & 0x7f
    for byte in fixed[a:a + n]:
        for b in range(8):
            if (byte >> b) & 1:
                if lv <= 125: lv += 2
            elif lv >= 2: lv -= 2
            bits.append(lv)
    hz = CPU / NTSC_RATE[rate & 15]
    step = 1
    while hz / step > 28000: step += 1
    s = [sum(bits[i:i + step]) / step for i in range(0, len(bits) - step + 1, step)]
    m = sum(s) / len(s)
    fade = 32
    v = []
    for i, x in enumerate(s):
        y = (x - m) * 1.6
        k = min(1.0, (i + 1) / fade, (len(s) - i) / fade)
        v.append(max(-127, min(127, int(round(y * k)))))
    data = bytes((x & 0xff) for x in v)
    if len(data) & 1: data += b'\0'
    period = int(round(PAULA / (hz / step)))
    frames = int(len(v) / (hz / step) * 50) + 1
    table.append((addr, length, rate & 15, len(pcm), len(data) // 2, period, frames))
    pcm += data
hdr = b''
for i in range(16):
    if i < len(table):
        addr, length, rate, off, words, period, frames = table[i]
        hdr += struct.pack('>BBBBIHHHH', addr, length, rate, 0, 256 + off, words, period, frames, 0)
    else:
        hdr += bytes(16)
open(out, 'wb').write(hdr + pcm)
print('dmc: %d samples, %d bytes' % (len(table), len(hdr) + len(pcm)))
