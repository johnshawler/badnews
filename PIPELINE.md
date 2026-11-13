# Development pipeline, reprioritised

What this port taught (see `LEARNINGS.md`) changes the order of work. Part A replaces the milestone order of
BRIEF.md Step 4 for ports of translated binaries (NES/6502 and similar); the gates and the referee
(`tools/port.sh`) are unchanged. Part B is the prioritised backlog for this port.

## Why the order changes

- The deciding number came last in the brief's order: how busy the original CPU is. It is measurable on day one
  with a reference emulator, and it alone decided that 50 Hz on a stock machine was out of reach.
- Correctness tooling paid for itself many times over: every translator bug was found in minutes by "first tick
  that differs, then a RAM dump". Built late, every bug would have been a guess.
- The cheapest large wins were I/O plumbing (OAM DMA, controller, mapper, PPU writes), found only with an
  unbiased profiler. Static cost estimates pointed the wrong way several times.
- Display bugs were found on the host harness, not in the emulator.

## Part A: milestone order for a translated-binary port

| # | Milestone | Gate | Was |
| --- | --- | --- | --- |
| 1 | Reference emulator of the original machine, headless, scripted input, frame dumps | Frames match the real game's screens | new |
| 2 | **Load measurement**: original CPU instructions per frame by scene (exclude wait loops) | Number per scene, written into the feasibility note | new |
| 3 | Feasibility note with the load: instructions/frame × 10–13 colour clocks (stock, chip RAM) or ×5–6 (fast RAM) + the display budget of Step 2, against 57k (80%) | Honest verdict per machine *before* code is written | 1 |
| 4 | Kit skeleton builds and benches | `late=0` | 2 |
| 5 | Traces → static translation to C; frame model (waits, NMI, coroutine) | Translated C equals an instruction interpreter tick by tick for ≥ 20,000 ticks | 3 |
| 6 | Asset script (ROM split, translation) with no manual step | `tools/make_assets.sh` from the ROM alone | 4 |
| 7 | 68k back end (registers in registers, 6502 flags in 68k flags, liveness) | Amiga checksum = host checksum for every tick of the bench | 8 (moved up) |
| 8 | Debug tooling on the Amiga: per-tick checksum and RAM dump, per-tick time, **1 kHz CIA profiler**, per-frame (vblank, tick) log | Profile of the busiest scene names its top routines | new |
| 9 | I/O fast paths and hand-written hot routines, chosen by the profiler, each guarded and proven by the checksum | Logic per tick in the busiest scene within its share of the budget | new |
| 10 | Host display harness (fake kit calls → PPM) | Screens match the reference emulator's | new |
| 11 | Background, scrolling, splits | Harness screenshots, then emulator screenshots, match | 5, 6 |
| 12 | Sprites (hardware first, multiplexed if needed) | No dropped clusters on the harness over the bench | 7 |
| 13 | Display cost: profile the display in the busiest scene, cut instruction count (not memory traffic) | Display + logic under 80% in the busiest scene | new |
| 14 | Sound | Still the same `late` | 9 |
| 15 | Final bench on stock and fast RAM | The brief's gates; report | 10 |

Rules that come with it:
- Measure before optimising, and only in the busiest scene. Re-measure after every change; keep the checksum
  equal after every change.
- If milestone 3 says the stock machine cannot hold 50 Hz, say so in the report early and target the cheapest
  upgrade explicitly. Don't spend days on the stock machine.

## Part B: backlog for this port

Status: stock A1200 33.9 fps, 4 MB fast RAM 43.4 fps, checksum equal (3,000-tick bench: menus, batting, field
play, the change of sides). Per tick of field play: logic ~45k colour clocks stock / ~17k fast RAM (x1.2 per
frame), display ~24k per frame. The late frames on fast RAM are mostly spikes: screen loads (one tick of up to
65,000 6502 instructions), camera cuts (up to 1,700 tile copies in a frame), and runs of frames just over 71k.

| Priority | Item | Expected gain | Effort | How to know it worked |
| --- | --- | --- | --- | --- |
| 1 | Bank-switch cost: 41 calls a tick of `$C36C` (via `$C345/$C34F/$C360`); inline the switch at the call sites in the translator, or skip it when the bank does not change | -3-6k per tick stock | medium | `tools/prof.py` field window; checksum equal |
| 2 | Row-oriented tile drawing in assembly for camera cuts and screen redraws (long writes, 4 tiles at a time) | camera-cut spikes 1/3 | medium | `tools/frames.py` slowest frames; vhost pixel compare |
| 3 | Screen-load loops (`$C1CC` PPU buffer flush, bank 3 `$8081` meta-tile expansion, bank 0 `$8090`) by hand | fewer late frames at screen changes | medium each | `VERIFY_STATS` ticks; late count in menus |
| 4 | Sprite grouping in assembly (4k a frame in C) | -3k per frame | medium | `video.txt` grouping figure |
| 5 | More channels for sprite clusters: a cluster that finds no channel is dropped (title logo, one batter's bat) | correctness | medium | vhost pixel compare, `sprite clusters dropped` |
| 6 | Home-run screen: upper part pans in 8-pixel steps (scroll split by whole tiles); fine scroll would need a second playfield or a display list | correctness | large | screenshot of the home-run screen |
| 7 | Intro: the `$2006` split (vertical scroll change) is not shown | correctness (attract only) | medium | intro screenshots |
| 8 | Measure a 68030 accelerator (the honest "cheapest upgrade" number) | report | small | a third bench line |
| 9 | Listen on the emulator / real speakers; play-test with a person (1 player mode is traced with random input only) | quality | small | a written note |
