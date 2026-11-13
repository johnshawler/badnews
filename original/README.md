# The game to port

**Bad News Baseball** (Tecmo, 1990) for the NES, USA ROM. The ROM is `original/bnb.nes`; it is not in the
repository (copyrighted; `.gitignore` keeps it and everything made from it out). MD5 of the iNES file:
`d8ca2b29417afe17da44f7d317a4a976`.

- Mapper, PRG/CHR sizes, mirroring, 50/60 Hz: MMC1 (SNROM-class board, NES 2.0 header), 128 KB PRG (8 x 16 KB,
  last bank fixed at $C000), 128 KB CHR (4 KB banks), vertical mirroring, NTSC 60 Hz. Sprites are 8x16 in most
  scenes. The background is animated by switching CHR banks (the crowd: banks 6/7 every 16 frames).
- Raster splits: sprite-0 splits done by the main thread after its frame wait (bank 2 $8157): the between-innings
  box score and the home-run screen change the CHR bank and the horizontal scroll/nametable for the lower part.
  The intro changes scroll with $2006 at a split (bank 5 $80BE, which also stirs the random number generator
  while it waits for the sprite-0 flag to clear).
- Sound: 2 pulse, triangle, noise, and four DMC samples (the voice).
- Self-playing mode for the bench: "Spectator mode" on the title menu (computer against computer). START skips
  the intro, DOWN x4 selects it, then one START per set-up screen (teams, orders, pitchers, starting members).
- Controls: pad, A, B, Select, Start (Start also pauses in a game).
- Load (6502 instructions per NES frame outside wait loops, reference NES `tools/nesref -s` with WAITPCS):
  menus ~2,500 (sound driver, controller read twice, metasprite builder, palette upload), batting ~3,500-4,500,
  field play 6,600-8,300, single screen-load frames up to ~10,000; in the frame model some screen loads are
  one tick of 22,000-65,000 instructions (NMI off while the screen is built).

The previous port's description is in history/llb/original-README.md.
