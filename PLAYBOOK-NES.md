# NES → A1200 porting playbook

The accumulated know-how for porting NES games to the Amiga 1200 with this template. **Read it before starting
a NES port, and add to it before finishing one** (section 9). The details of the first port are in
`LEARNINGS.md`; the order of work is in `PIPELINE.md`.

Ports get better only through this file and the tools next to it: a new session remembers nothing else.
To start a new port, see `KICKOFF.md` (with a ready first message). In short: make the new repository from this one ("Use this template" once it is marked as a template,
or a copy) and run `tools/new_port.sh <game> <rom.nes>`: it archives the previous port under `history/`,
resets the per-game files and keeps everything reusable. The Claude skill in `skills/amiga-nes-port/SKILL.md`
(install it in Claude) makes any session start by reading this playbook and end by adding to it.

## 1. What is reusable, what is per game

| Kind | Files | For a new game |
| --- | --- | --- |
| Generic 6502 | `tools/op6502.py`, `tools/dis.py`, `tools/recomp.py`, `tools/back68k.py`, `tools/nesref/verify.c`, `src/coro*.{s,c,h}`, `src/run*.{c,h}`, `src/nes68k.s` (helpers), `src/logic.c` frame model | use as is |
| NES machine | `tools/nesref/nesref.c` (reference NES), `src/nes.{c,h}` (PPU/APU/pad state), `src/video.{c,h}` + `src/video68k.s` (PPU → AGA), `src/sound.{c,h}` (APU → Paula), `tools/vhost.c`, `tools/shost.c` | use; extend for what the game uses |
| Mapper | MMC1 in `nesref.c`, `nes.c`, and the fast paths in `nes68k.s` (`_set_prg`, `_io_wr`) | add the new mapper in all three |
| Per game | `tools/games/<game>.py` (NORETURN, hand-written routines, DMC sample list), `game_bench_input` in `src/logic.c` and `tools/nesref/verify.c`, the flow traces in `tools/flow/` (also `verify_bench.txt` from `VERIFY_COV`), `tools/make_assets.sh` (ROM check), `original/README.md` | write new |
| Starting a port | `tools/new_port.sh`, `skills/amiga-nes-port/SKILL.md` | run once / install once |
| Debugging | `tools/debug_run.sh` (`DEBUG_SECS`, `UAE_OPTS`), `tools/shot_at.sh`, `src/prof68k.s` (1 kHz profiler) + `tools/prof.py` (names the hot routines in a tick range), `tools/frames.py` (late frames per tick range, slowest frames split into logic and display), `LOGIC_TRACE`/`LOGIC_NOSUM`/`LOGIC_DUMP`/`HOLD_AT`/`VP_FROM`,`VP_TO` builds, `VERIFY_STATS`/`VERIFY_COV` in `verify.c`, `-DCOUNT_IO` in `nes.c`, `vhost` env `VDEBUG`/`VSTATE`/`VGROUPS`/`SPRCH`, `nesref -s` (raster-time register writes) and `PROF_FROM`/`PROF_TO` | use as is |
| Sound assets | `tools/dmc.py` (DMC samples -> Paula PCM, run by `make_assets.sh`) | list the game's samples |

## 2. Start of a port: the first day

1. `tools/new_port.sh <game> <rom.nes>`, `tools/setup.sh`; check mapper, PRG/CHR sizes, mirroring, 50/60 Hz
   (`tools/make_assets.sh` refuses what the tools do not support yet: section 8).
2. Run the ROM in `tools/nesref` headless; dump frames; find a **self-playing mode** (attract, "watch game",
   demo, "spectator") for the bench and for coverage. Write the input scripts (`tools/flow/mkin.py`). Script the
   menus tightly: `tools/bench.sh` allows `ticks / 25 + 60` seconds, so a slow stock run of more than ~3,000
   ticks does not finish; make most of the 3,000 ticks game play.
3. **Measure the load before anything else**: `WAITPCS=<wait loop addresses> nesref -s` gives 6502 instructions
   per frame outside wait loops. Take the addresses from `src/gen_waits.txt` (run `tools/make_assets.sh` once
   first): games copy their wait loop into several banks, and some "waits" call a routine while they poll (Bad
   News Baseball stirs its RNG waiting for the sprite-0 flag: ~6,000 instructions a frame that are only waiting).
   Do it per scene. Then the verdict (section 6). Write it in the feasibility note. `nesref -s` also prints
   PPU/MMC1 register writes made while lines are drawn (`split@line:reg=value`): that answers "does it change
   scroll at a split" on day one (reg 0-7 PPU, 8-11 MMC1 control/CHR0/CHR1/PRG).
4. Trace (`nesref -c`) attract, self-play and random input; `tools/recomp.py --game <game>` → C and 68k.
5. `tools/nesref/verify.c` against the host test, tick by tick (NES RAM). Run it with `VERIFY_COV=tools/flow/
   verify_bench.txt` and translate again: the frame model's timing differs from the reference NES, so it reaches
   code the traces never ran (the host test stops with reason 3 at an untranslated address). Then the Amiga
   checksum against the host, tick by tick (`tools/debug_run.sh` + per-tick trace). Only then display and speed.

## 3. NES behaviour the frame model must get right

- **One tick = NMI + main thread until it waits.** Wait loops: no writes, fixed addresses, registers
  redefined each pass (RAM poll → `nes_wait`; `$2002` bit 7 → vblank wait; `$2002` bit 6 → sprite-0 wait).
- **The vblank race**: games poll `$2002` while the NMI also reads it. Model it deterministically: NMI first,
  then the vblank flag set for the poller.
- **Sprite-0 splits**: a toggling hit flag ends the wait in two reads and records the split; what the game
  changes after it belongs to the lower part of the picture. The split may be in the NMI (Little League) or in
  the main thread after its frame wait (Bad News Baseball): `split_on` is taken when the frame ends
  (`nes_wait`). The split line is sprite 0's first opaque row (`s0_first_row` in `nes.c`).
- **Stack tricks** (jump tables after JSR, `PLA PLA RTS`, pushed-address RTS): the 6502 stack stays in RAM,
  RTS compares with the caller's expectation and unwinds. Jump-table dispatchers go in `NORETURN`.
- **Lag**: check with the reference whether the original finishes its logic within each frame in the busy
  scenes. If it doesn't, game time on the NES is slower there and the frame model would need cycle budgets
  (not needed for Little League Baseball).
- The checksum covers all 2 KB of RAM including the stack page: anything that changes RAM must be exact.

## 4. Idioms worth looking for first (the cheap big wins)

Found in the first port; look for them in every game with the profiler (`src/prof68k.s`, busiest scene only):

| Idiom | Signature | What to do |
| --- | --- | --- |
| OAM DMA | `STA $4014` with a RAM page (usually 2) | already a `memcpy` in `nes.c` |
| Controller read | 8× `LDA $4016,x / LSR / ROL` loop, often read twice until equal, edge and hold counters after | hand-write the whole routine (`tools/games/llb.py` $CEBD as template) |
| Mapper serial writes | 5× `STA $8000-$FFFF / LSR` (MMC1) | hand-write: one step when the shift register is idle (template: `_mmc_hle`) |
| PPU data port | `STA $2007` loops in the NMI | nametable fast path in `nes68k.s` (`_io_wr`) |
| Jump table | `ASL A; TAY; PLA; STA; PLA; STA; ... JMP (zp)` after JSR | `NORETURN`; hashed dispatch handles the jumps |
| Shift-and-add multiply | 8 or 16 iterations of `ASL/ROL/ADC` | `mulu` + replay only what decides the stack bytes (template: $C378) |
| Metasprite builder | `LDA (ptr),y` streams into `$0200,x` | hand-write with one pointer (template: $E2DE) |

Hand-written routines: guard them (fall back to `.orig`), reproduce registers, all four flags, RAM and the
return addresses left on the stack page, and prove them with the per-tick checksum. A, X and Y must stay
zero-extended in d0/d1/d2 (the translation indexes memory with `d1.w`): never `moveq #-1,d1` for X = $FF, use
`move.l #$ff,d1` then `tst.b d1` for the flags (a crash in Bad News Baseball).

Assembly called from C must save every register gcc treats as callee-saved (d2-d7, a2-a6) *even when it is an
argument* (`__asm("a2")`): gcc 16 keeps values in a2 across the call. `_spr_put` advanced a2 unsaved for two ports;
it showed only when a debug check ran the C twin right after it. Check each new assembly routine against its C
version inside debug builds (both run, results compared, differences counted): it found this in one run.

Count the I/O per tick in the frame model, not on the reference NES: `cc -DCOUNT_IO` with a small driver gives
reads and writes per address (Bad News Baseball: 197 MMC1 writes a tick in field play; the reference NES showed 50
in a different scene). Bank switches dominate when a game calls code in other banks often.

## 5. Translator rules of thumb

- 68k back end, not C, on the Amiga (C costs 3× more: registers through globals at every call).
- 6502 N/Z in 68k N/Z, C in 68k X; protect only live flags. Use address registers for addresses (no flags).
- RAM indexed tables: the index never crosses $07FF in practice; check with the interpreter and use direct
  addressing. `(zp),y` reads are almost always ROM.
- Any I/O done through C costs ~60–80 instructions; anything done per frame dozens of times belongs in assembly.
- After every translator change: regenerate, compare the per-tick checksum with the host over the whole bench.

## 6. The verdict, before writing code

Translated 6502 code on a 14 MHz 68020 costs about **10–13 colour clocks per 6502 instruction from chip RAM**
(stock A1200) and **about half that from fast RAM**. A frame is 71,051 colour clocks, 57k at the 80% gate, and
a 60 Hz NES game runs 1.2 ticks per 50 Hz frame. So, for the busiest scene:

| 6502 instructions per NES frame | Stock A1200 (logic per frame) | 4 MB fast RAM (logic per frame) |
| --- | --- | --- |
| 2,000 | ~30k: 50 Hz possible | ~15k |
| 5,000 | ~70k: no | ~35k: possible with a cheap display |
| 10,000 | ~140k: no | ~60–70k: only with many hand-written routines |

Add the display (Little League Baseball, 4 MB, field play: 25–35k per frame with ~40 sprites and scrolling).
Say the verdict in the report from the start; name the upgrade.

## 7. Display and sound recipes

- Background: 4 planes = 16 NES colours (attribute bits as planes 2–3), hardware scroll over an unwrapped world,
  stream tile columns, each tile row at y and y+240 drawing only the shown copy, border columns blank, honour
  PPUMASK's hidden left column. Tile-set-only splits: draw rows with the right tile set.
- Sprites: cluster ≤ 64 px, 64-pixel attached pairs (15 colours), reuse channels down the screen, cache unchanged
  clusters from the previous sprite set, keyed by the 4 KB CHR bank each sprite reads (games animate by bank
  switching), and skip the copy when this sprite-list set already holds the same lines. 8x16 sprites: the table
  from tile bit 0, vertical flip swaps the tiles. Sprite-behind-background priority is not done yet.
- Scroll change at a split (kit: one scroll for the whole screen; no own display list allowed): a `$2005` write
  after the split cannot change the vertical scroll, so only x differs; draw the rows above the split from the
  upper part's nametable columns, offset by the scroll difference in whole tiles. Exact for static screens.
- CHR-bank animation of the background: never redraw everything; compare the two 4 KB banks tile by tile and
  redraw the visible cells whose tile differs, a few columns a frame (`retile_step`). Each column remembers the
  banks it was drawn with; restart a column being streamed when the bank changes.
- Blank the border columns (outside the 256-pixel NES picture) when they leave the picture.
- Sound: APU model (length, envelope, sweep, linear counter, 240 Hz sequencer) → Paula periods and volumes with
  looped one-period waveforms. DMC: list the game's samples in `tools/games/<game>.py` (print `apu_reg` when
  `apu_trig` bit 4 is set), `tools/dmc.py` converts them on the host; a sample takes Paula channel 3 for its time.
- Develop both on the host harnesses (`tools/vhost.c`, `tools/shost.c`), then confirm on the emulator. Compare the
  display harness with `src/host_render.c` pixel by pixel every few ticks: it found every display bug of the
  second port.

## 8. Not done yet (do it when a game needs it)

Other mappers (UxROM, CNROM, MMC3 with its scanline IRQ); scroll changes at a split by less than a tile, and
vertical ones (`$2006`); sprite-behind-background; more than four vertically overlapping sprite clusters (they
are dropped); lag (cycle budgets); a 68030 bench; screen loads that are one long tick (tens of thousands of
6502 instructions with the NMI off: late frames at every screen change); camera cuts that need thousands of
tile copies in one frame (row-oriented drawing in assembly).

## 9. Lessons log (append one entry per port, newest last)

Each entry: game, mapper, verdict numbers, what was new, what to do differently next time. Then update the
sections above if a lesson is general.

### 1. Little League Baseball: Championship Series (SNK 1990), MMC1, 2026-11

- Load: 2,000 (batting) to 11,000 (fielding) 6502 instructions per frame; the NES is 95–100% busy fielding.
- Result: 37.2 fps stock, 44.6 fps with 4 or 8 MB fast RAM; 50 Hz in menus and batting on fast RAM; checksum equal.
- New: the whole toolchain (reference NES, two-back-end translator, frame model, display, sound, profiler).
- Biggest wins were I/O plumbing found by the profiler (OAM DMA, controller, MMC1, PPU writes), not game logic.
- Next time: measure the load on day one (it decided the outcome); build the 1 kHz profiler before optimising
  anything; don't trust static cost estimates; write the display on the host harness first.

### 2. Bad News Baseball (Tecmo 1990), MMC1, 2026-11

- Load: menus ~2,500, batting 3,500-4,500, field play 6,600-8,300 6502 instructions per frame (NES 70-90% busy);
  screen loads up to 65,000 in one tick of the frame model.
- Result: 33.9 fps stock, 43.4 fps with 4 MB fast RAM, checksum equal (also under the user's Kickstart 3.1).
  Menus and quiet field play reach 50 Hz on fast RAM; late frames come from screen loads, camera cuts and logic
  just over the frame.
- New: 8x16 sprites, main-thread sprite-0 splits, scroll split by whole tiles, CHR-bank animation (incremental
  retile), DMC samples, `VERIFY_COV`, `tools/prof.py`, `tools/frames.py`, I/O counting in the frame model, PPU
  and APU writes in the 68k fast path, pixel comparison of the display against the host reference.
- Same lesson as the first port, sharper: the big logic win was the bank switch (41 a tick) and the controller,
  found by counting I/O in the frame model. Three hand-written routines (bank switch, controller, metasprite builder) halved field-play logic.
- Next time: compare the display harness against `host_render` pixel by pixel from the first display milestone;
  log per-frame logic and display time before optimising (the average hid the spikes); make the bench input
  reach game play within ~1,000 ticks from the start.
