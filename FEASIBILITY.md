# Feasibility note: Bad News Baseball (milestone 1 of BRIEF.md, milestone 3 of PIPELINE.md part A)

Written from the day-one measurements; the numbers are from `tools/nesref -s` with the wait loops of
`src/gen_waits.txt` excluded (see `original/README.md`).

## Class and route

NES ROM (6502 binary, MMC1, 128 KB PRG + 128 KB CHR, 60 Hz): the brief's "assembly for a 6502 machine" row,
done as in the first port: trace in a reference NES, translate once on the host (C for the host test, 68k for
the Amiga), replace the PPU/APU/controller with plain state and an AGA display / Paula sound.

## Display (`DispCfg` in `src/video.c`)

`planes=4 scroll=1 fetch=0 view_h=240 buf_h=480 level_w=4096 buffers=1 sprite_w=64 sprite_bank=1`

- Colours: 16 background (4 NES sub-palettes of 4, attribute bits as planes 2-3) + 16 sprite = the NES's 25.
- Objects: NES sprites (8x16 in most scenes), up to 64, clustered into 64-pixel attached hardware sprite pairs
  (3 pairs + sprite 6, reused down the screen). No `disp_bob`: nothing is drawn with the blitter.
- Background: NES tiles drawn into the buffer only when they change (scrolled-in columns, nametable writes,
  CHR-bank animation); hardware scroll for the camera.

## Budget (busiest moment: field play)

The brief's object sum does not describe a translated game: the logic is the dominant term.

| Part | Stock A1200 | 4 MB fast RAM |
| --- | --- | --- |
| Logic: 6,600-8,300 6502 instructions a NES frame x 10-13 (stock) / 5-6 (fast) colour clocks, x 1.2 NES frames per Amiga frame | 80-130k | 40-60k |
| Display: tile streaming, sprite clustering and lists (first port: 25-35k) | 25-35k | 25-35k |
| Total against 71k (57k at 80%) | 105-165k: no | 65-95k: no, but close |

Verdict (day one): 50 Hz is out of reach on a stock A1200 in field play; menus could hold it. With 4 MB fast
RAM, batting and menus could hold 50 Hz; field play only with hand-written routines and a cheaper display.
What will be cut: sprite-behind-background priority; scroll changes at a split finer than a tile; sprite
clusters beyond what four hardware channels can show.

## Memory (brief Step 2, chip RAM check), measured on the final build

Program 495,756 bytes (code 122 KB, data 310 KB of which the PRG/CHR copy 256 KB and the DMC samples 30 KB,
bss 64 KB), display buffer 125,184 bytes, sprite lists 65,408 bytes, tile hashes 32,768 bytes: about 720 KB in
all, under the 1.4 MB limit; the largest single section is the 256 KB ROM copy (under 400 KB).

## Outcome (REPORT.txt)

Stock 37.9 fps, 4 MB fast RAM 48.3 fps, checksum equal to the host. 50 Hz is not held on either machine.
