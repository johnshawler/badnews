; data.s - the NES ROMs, made by tools/make_assets.sh. Read by the CPU only, so any memory will do.
        section romdata,data
        xdef    _nes_prg_data,_nes_chr_data
        cnop    0,4
_nes_prg_data:  incbin  "assets/prg.bin"
        cnop    0,4
_nes_chr_data:  incbin  "assets/chr.bin"

; the game's DMC samples as Paula samples (tools/dmc.py). Paula reads them from chip RAM, but this toolchain's
; linker drops the data_c flag (the hunk loaded into fast RAM and the voices were silent): src/sound.c copies
; them with sys_chip_copy() at start.
        section dmcdata,data
        xdef    _nes_dmc
        cnop    0,4
_nes_dmc:       incbin  "assets/dmc.bin"
        cnop    0,4
