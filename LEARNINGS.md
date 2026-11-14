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

## 7. Second round: 4 MB fast RAM, 43.4 -> 48.3 fps (stock went 33.9 -> 37.9 on the way)

The user asked to focus on the fast-RAM machine. Every step kept the checksum equal (and verify.c = host).

| Change | fps (4 MB) |
| --- | --- |
| Start of the round | 43.4 |
| Screens built until 60,000 colour clocks into the frame (time budget, `sys_beam()`), not a fixed tile count | 44.7 |
| Run the next tick in the frame's idle time (`game_tick_ahead`): the fifth frame no longer does two ticks | 45.6 |
| Edges checked only when the camera moves; crowd retile only in spare time | 46.1 |
| Slices: NMI-off screen loads end the tick every 128 $2007 writes (a 600-write load was one tick of 300-900k) | ~46 (other scenes in the bench) |
| Dirty flags cleared at once after a load; budget minimum 8 tiles | 46.9 |
| While black: draw to 30,000, run ahead, then draw on (`video_idle`) | 47.7 |
| Sprite clustering in assembly (checked against C every frame: 0 differences) | 48.2 |
| `spr_put` byte-aligned path; a2 saved (a latent bug); cache keyed by tile pixels; adaptive run-ahead | 48.4 / 48.3 |

What I learnt:
- **Classify the late frames before optimising** (`tools/late.py`): long single ticks, black building frames,
  display spikes, or frames just over. Each class has a different fix; averages hid all of them.
- **Time budgets, not counts**, for work that may be spread: `sys_beam()` tells how much of the frame is left.
- **Run ahead**: on a 60-tick game at 50 Hz the two-tick frames dominate once the average fits. Running the next
  tick in idle time (same input as the loop would pass) flattens them, and the checksum proves it changes nothing.
- **Slices** must be at least what the NES does in a frame: the game's NMI-off bursts are all ~600-write screen
  loads; at 96 writes or fewer the bench never reached field play (not understood; 128 and 112 play normally).
- **Check assembly against C inside debug builds** (both run, outputs compared): it found a latent a2 clobber in
  `spr_put` at once. Debug checks must be opt-in (`-DVIDEO_CHECK`), or they distort the timings.
- The frame model change replays a different game (the RNG follows frame timing): re-check the bench reaches the
  busiest scenes after each such change (`out/benchsearch`-style host driver counting field-play ticks).

What is left (fast RAM): the start-up tick (~15 late), screen loads with two slices in a frame (~40), and play
frames that need two ticks and land a few thousand colour clocks over (~45). Next: cheaper load code (the
meta-tile expansion around the $2007 loop), sprite list bookkeeping in assembly (`build_sprites`, `group_sig`),
a 68030 bench.

## 8. Three problems the user saw on the ADF (none was visible in the bench numbers)

- **Flashing in field play**: the time-budgeted catch-up blanked the picture whenever a scrolled-in row or column
  missed the budget. Only a new screen (or a camera cut) may be shown black now; scrolling always completes.
- **Green border**: everything outside the 256x240 NES picture shows colour 0, which was the NES backdrop. Palette-0
  tiles now put their colour-0 pixels into index 4 (a copy of the backdrop), so index 0 can be black (`tile8` with
  attribute bit 16).
- **The intro**: it uses horizontal mirroring (two nametables stacked) and a `$2006` split where the lower part has
  its own vertical scroll, moved a pixel a frame by moving the split line. The display now keeps per-copy world
  rows for stacked nametables and redraws the upper part over the world each frame. And the frame model granted a
  sprite-0 hit on every read, so the intro loop (synced only by the hit) ran ~250 passes in one tick: a second
  sprite-0 wait in one frame now ends the frame (`nes_s0_frame`, in C, 68k and verify.c). That also removed the
  "start-up tick" of 480,000 instructions. Lesson: look at the attract mode, not only the bench.

## 9. Second ADF round: overscan, silent voices, broken faces

The user played the ADF again and saw three more things that no bench number showed.

- **Overscan in field play**: the first border fix blanked whole columns when they left the picture and kept the
  column next to it (a hysteresis against a wobbling camera), so up to 15 pixels beside the picture showed the
  field. Now the two columns that straddle the picture's edges are drawn through a pixel mask (`tile8m` in
  assembly, masked in registers, so it writes no more than `tile8`); columns wholly outside are drawn black; an
  edge column is drawn again from a cache of each tile's source when the edge moves across it, and only the
  columns near the two edges are checked unless the camera jumps. Sprite clusters are clipped at x 256 as on the
  NES. Pixel comparison: no pixel outside the picture in any of 120 bench frames; the frames inside are as before.
  Cost: about 1 fps with fast RAM (47.4 -> 46.4); first attempt cost 2 fps (masking in C, and columns outside the
  picture drawn and then masked).
- **Silent voices**: the samples were triggered, found and timed correctly on the Amiga (debug counters), and the
  host sound simulation played them. Recording the emulator's audio (`tools/bench_audio.sh`, OpenAL Soft's wave
  backend) showed one 0.4 ms click per voice with 4 MB fast RAM and the full voice on the stock machine: the
  samples' `data_c` hunk had lost its chip RAM flag in the link (no hunk of the executable has it), so with fast
  RAM the samples were loaded where Paula cannot read them. `sys_chip_copy()` at load time fixed it. Lesson: when
  sound is reported missing, listen on the machine configuration the user runs, and read the hunk flags.
- **Faces between innings**: three batters stand side by side; their face and bat sprites made five clusters on
  the same lines, and the fifth (the third batter's face) was dropped. Before dropping a cluster, `free_chan()`
  merges two narrow clusters on other channels into one 64-pixel sprite. Those frames now match the reference
  exactly (were ~400 pixels off).
- **Crowd at the top of field play** (third report): the game streams the row it is about to scroll in through
  NES lines 0-7, which an NTSC TV never shows; the reference renderer shows it too, so the pixel comparison could
  not flag it. The view is now 224 lines (`view_h`) of NES lines 8-231: one scroll offset and a sprite y shift,
  no cost per frame (46.4 fps, as before). Lesson: show what a TV showed, not the whole 240 lines.

## 10. Judder when the ball is hit, and the ball's sound

- **Judder**: the per-frame log (`tools/debug_run.sh`, `frames.bin`) showed that during the ball's flight frames took
  two vertical blanks and the next one jumped three ticks. The largest part of those frames was the edge masking
  added for the overscan (14,000-37,000 colour clocks: two tile columns of byte writes to chip RAM in every frame
  the camera moved). Doing it with the blitter was worse: with the kit's blitter-hog setting the CPU waits for
  the bus anyway, and a column blit moves six times more data than the CPU writes. The fix costs nothing: the
  display window (`DIWSTRT`/`DIWSTOP`) is narrowed to the 256 x 224 picture at every vertical blank, from the
  kit's vertical-blank hook, after the copper set the kit's 320-pixel window. The chipset then hides the columns
  that cross the edges and the sprites beyond them; edge masks, sprite clipping and blanking columns that leave
  the picture all went. A column outside is redrawn when it comes in only if a cell changed meanwhile. 4 MB fast
  RAM: 46.4 -> 47.7 fps, late frames 177 -> 112. What is left is mostly the 60-to-50 tick pattern (every fifth
  frame shows two ticks) and frames where logic and sprites still do not fit.
- **Ball sound**: the game starts pulse 2 with the hardware sweep on and never writes the period again; the sweep
  raises the pitch while the ball climbs, then the game switches it to falling. `sound_frame` copied the period
  register into the channel every frame, undoing the sweep: a flat tone. The period is now reloaded only when the
  game writes it (`apu_wr`, set by `src/nes.c` and the 68k fast path), and a sweep register write restarts the
  sweep divider. Checked on the host (`PER1=` in `tools/shost.c`) and in an emulator recording of pulse 2 alone
  (`-DSND_ONLY_CH=1`, `tools/bench_audio.sh`): 115 Hz rising to 750 Hz and back down.

## 11. A crash the bench could not find, and shorter black frames between pitching and fielding

- **Crash (down+B while pitching)**: the bench is computer against computer, so the code a player's pitching and
  batting reach was never traced: the game jumped to untranslated addresses ($AAAC pitching, $99D0 batting).
  `tools/play.c` plays scripted input on the host and stops at the first untranslated address; `tools/fuzz_play.py`
  plays hundreds of random half-innings (down+B, A, directions) in a 1-player game. Most pitching runs stopped.
  `verify.c` now takes the same scripts (`PLAY=`), so `VERIFY_COV` collects the entry points of those scenes
  (`tools/flow/verify_pitch.txt`, `verify_bat.txt`); after `tools/make_assets.sh` 590 unseen fuzz runs and 40
  random 20,000-tick games run clean, and a fuzz script that crashed before plays to tick 11,600 on the emulated
  Amiga with the host's checksum. `-DPLAY_SCRIPT -Iout` compiles a script in place of the bench input.
- Two traps on the way: `verify.c` reads `src/gen_waits.txt` from the current folder (run from `out/` it never ends a
  tick and looks hung), and a `-D` with quotes passed through two scripts silently dropped the script, so the
  "Amiga differs from the host" I chased for an hour was the bench input. Check the checksum of the plain bench
  first when a scripted build differs.
- **Black frames**: logged per frame (`video_black` in the debug frame log: NES rendering off, or still drawing).
  A switch from pitching to fielding was 20-38 vertical blanks of black with fast RAM; the reference NES shows 2.
  (1) Slices: the NES spends 2 frames on a full screen load (`tools/nesref -s`), the port 8 ticks at 128 writes a
  slice; now 704. (2) Drawing: a new screen is drawn row by row, four tiles per 32-bit write (`tile4`), only the
  columns the display window shows, until 66,000 colour clocks into the frame, and without the run-ahead tick
  while black. The switch at a hit: 20 -> 11 vertical blanks; the others 35 -> about 20, where the game's own
  logic (25,000 colour clocks a tick) and its catch-up after the load take the rest.
- The bench plays a different game with the new slices (the RNG follows frame timing), with more field play
  (785 ticks of over 20,000 colour clocks of logic against 685): 43.1 fps with fast RAM against 47.7 before. The
  same code with 128-write slices gives 46.8; most of the difference is the busier game.
