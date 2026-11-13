# Notes: where the brief was unclear, wrong or missing something

(Earlier ports: history/*/NOTES.md. Add one line for every new place.)

- The brief says the image holds m68k-amigaos-gcc 6.5.0b; `amigadev/crosstools:m68k-amigaos` now holds gcc 16.2.1b. The kit skeleton and this port build and bench with it unchanged; nothing else noticed.
- `tools/bench.sh` gives a run `FRAMES / 25 + 60` seconds of wall time. A stock-machine bench of a game whose logic is slower than real time does not finish in that: 6,000 ticks of this game did not. The bench was shortened to 3,000 ticks (the brief's minimum) and the menus scripted faster so most of it is game play.
- The kit has no way to change the scroll position at a raster line, and the brief forbids writing a display list. This game changes the horizontal scroll at its sprite-0 split on two screens; the port draws the upper part's nametable columns into the rows above the split (whole tiles only), so a difference that is not a multiple of 8 pixels is rounded.
- The brief's sprite rules assume one picture per sprite; a NES game with 8x16 sprites and CHR-bank animation needs its own clustering and caching (src/video.c), and the 15-colour attached pairs limit how many clusters can overlap vertically (four, counting sprite 6).
- "Convert every asset on the host": the NES DMC samples are converted on the host (tools/dmc.py), but which samples a game plays has to be found by running it; the list is per game (tools/games/bnb.py).
- The brief does not mention a Kickstart ROM check beyond "real Kickstart: not verified". The user supplied Kickstart 3.1 (40.68); FS-UAE takes it with `--kickstart_file=` as an extra option of tools/bench.sh, and the bench gave the same checksum (not committed: copyrighted).
- The brief's "Measure after every milestone" gives whole-run numbers; the late frames of a NES port come from spikes (screen loads, camera cuts, CHR-bank animation), which only a per-frame log shows (tools/frames.py).
