# Learnings from porting Bad News Baseball (NES) to the A1200

The second NES port made from this template (the first, Little League Baseball, is in `history/llb/`). What was
new, what worked, the numbers. The reusable part is folded into `PLAYBOOK-NES.md`; where the brief was unclear is
in `NOTES.md`; the measured results are in `REPORT.txt`; the backlog is `PIPELINE.md` part B.

## 1. Day one paid off

- The tools from the first port took this game from ROM to an equal Amiga checksum in a few hours: same mapper
  (MMC1, 128 + 128 KB), `tools/new_port.sh`, `nesref`, `recomp.py`, `verify.c`, the 68k back end. No translator
  change was needed. The frame model only needed one fix (a sprite-0 split in the main thread, below).
- The load measured on day one (menus 2,500, batting 3,500-4,500, field play 6,600-8,300 6502 instructions a
  frame) predicted the result: field play cannot hold 50 Hz on a stock machine; fast RAM gets close.
- Wait loops must be found before the load means anything. This game has its frame wait copied into several
  banks, and one "wait" (bank 5 `$80BE`) calls the random-number routine while it polls the sprite-0 flag: the
  reference NES counts ~6,000 instructions a frame there that are only waiting. `recomp.py`'s `gen_waits.txt`
  lists the real ones; feed them to `WAITPCS`.

## 2. Correctness

- `verify.c` against the C translation, NES RAM after every tick: equal for 30,000 ticks. Amiga against host:
  equal at every bench length tried (600, 2,500, 3,000 ticks; stock, fast RAM, AROS and Kickstart 3.1).
- New: the frame model reaches code the reference NES never ran with the same input (its frame timing differs).
  `VERIFY_COV=file verify N` now writes the entry points the frame model reaches, in nesref's flow format; the
  translator takes it like any trace. Without it the host test stopped at an untranslated address after 8,871 ticks.
- A hand-written routine broke the Amiga build until X was kept zero-extended in d1 (`moveq #-1,d1` for X = $FF
  made `(a5,d1.w)` index backwards). Now in the playbook.

## 3. Speed

| Change | Effect (stock A1200 unless noted) |
| --- | --- |
| Starting point (translation only) | 18.6 fps in the first 2,500 ticks, logic ~86k colour clocks a tick in field play |
| MMC1 bank switch `$C36C` + controller `$C200` by hand | 32.2 fps; field logic ~45k a tick |
| Metasprite builder `$8012`/`$87FD` by hand | field logic ~45k (was 10% of the time) |
| `$2000/$2001/$2005/$2006` and APU writes in the 68k fast path | +1-2 fps |
| Display: incremental CHR-bank retile, sprite cache per bank, lists reused in place | fast RAM display 27k -> 24k a frame |
| Final | stock 33.9 fps, 4 MB fast RAM 43.4 fps |

- The biggest single win was again I/O plumbing: this game switches PRG banks ~41 times a tick in field play
  (5 serial writes each, the fifth through C). Count I/O in the frame model (`-DCOUNT_IO`), not on the reference
  NES: the reference showed 50 writes a frame in another scene, the frame model 205 a tick in field play.
- On fast RAM the late frames are spikes, not the average: per-frame logic and display times (`tools/frames.py`)
  showed (a) screen loads that are one tick of 22,000-65,000 6502 instructions, (b) camera cuts that need up to
  1,700 tile copies in a frame (the vertical scroll jumps and the y + 240 row copies must be drawn), (c) the
  crowd animation (a CHR bank switch every 16 frames) that redrew the whole background, and (d) the sprite cache
  missing on every bank switch. (c) and (d) are fixed; (a) and (b) are the backlog.
- The 1 kHz profiler needed a script: `tools/prof.py` maps the samples to symbols per hunk and restricts them to a
  tick range (samples come at 1 kHz, `frames.bin` says which tick each vertical blank belonged to). C statics do
  not reach the executable's symbols, so C time shows up under the next exported function.

## 4. Display: what this game needed that the first did not

- **8x16 sprites** (PPUCTRL bit 5): the pattern table comes from tile bit 0, vertical flip swaps the two tiles.
  Clusters are 16 lines per sprite.
- **Sprite-0 split in the main thread**: the game waits for the frame, then for sprite 0, then writes `$2000`,
  `$2005` and the CHR bank. `split_on` must be taken at the frame's end (`nes_wait`), not after the NMI. The split
  line is sprite 0's first opaque row, not its y.
- **Scroll change at a split**: the kit cannot change scroll mid-screen and the brief forbids an own display list.
  A `$2005` write after the split cannot change the vertical scroll (the PPU copies only horizontal bits at each
  line), so only x differs: rows above the split are drawn from the upper part's nametable columns, offset by the
  scroll difference in whole tiles, and redrawn when it changes. Exact for static screens; a pan moves in 8-pixel
  steps.
- **CHR-bank animation**: compare the old and new 4 KB banks tile by tile (256 x 16 bytes, cached per pair), and
  redraw only the visible cells whose tile changed, a few columns a frame. Each column remembers the banks it was
  drawn with; a column being streamed restarts if the bank changes under it (that was a visible bug).
- **Border columns** (the 32 pixels beside the NES picture) are blanked when they leave the picture; the first
  port kept their content, which later vertical redraws filled from the wrong side of the wrap.
- **Pixel comparison** of the display harness (`tools/vhost.c`) against the host reference renderer
  (`src/host_render.c`, now with 8x16 sprites and split banks) every 25 ticks found every remaining display bug.

## 5. Sound

- The game plays four DMC samples (the voice). `tools/dmc.py` converts them on the host from a list in
  `tools/games/bnb.py` (found by printing `apu_reg` whenever `apu_trig` bit 4 was set), halving the 33 kHz rate
  for Paula. `src/sound.c` gives Paula channel 3 to a sample for its duration: DMA off one frame, the sample the
  next, then a 2-byte silence as its loop. `tools/shost.c` now simulates Paula's latching of pointer and length at
  each loop start and DMACON restarts, so this can be checked on the host.

## 6. Practical

- Quoting: `sed` replacing a name inside a single-quoted `printf` wrote `${NAME}_dbg` literally into the Amiga
  startup-sequence; AROS then asked for the volume `ENV:`. If an emulator run shows "Please insert volume ENV",
  look at the startup-sequence first.
- The debug build's per-tick checksum costs ~16 stock frames a tick; use `-DLOGIC_NOSUM` for profiling and
  `DEBUG_SECS` to give a long run time.
- `bench.sh` limits a run to `FRAMES / 25 + 60` seconds: on a stock machine a slow game's 6,000-tick bench does
  not finish. Script the menus quickly and keep the bench at 3,000 ticks of mostly game play.
- The user's Kickstart 3.1 ROM works with `tools/bench.sh ... --kickstart_file=<rom>`; same checksum, about the
  same speed as the AROS ROM.
