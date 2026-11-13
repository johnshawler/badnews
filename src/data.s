; data.s - the NES ROMs, made by tools/make_assets.sh. Read by the CPU only, so any memory will do.
        section romdata,data
        xdef    _nes_prg_data,_nes_chr_data
        cnop    0,4
_nes_prg_data:  incbin  "assets/prg.bin"
        cnop    0,4
_nes_chr_data:  incbin  "assets/chr.bin"

; the game's DMC samples as Paula samples (tools/dmc.py): read by Paula, so chip RAM
        section dmcdata,data_c
        xdef    _nes_dmc
        cnop    0,4
_nes_dmc:       incbin  "assets/dmc.bin"
        cnop    0,4
