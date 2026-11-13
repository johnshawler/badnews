"""bnb.py - what the translator needs to know about Bad News Baseball (Tecmo 1990, NES, MMC1) that it cannot find
out by itself. Loaded by tools/recomp.py (--game bnb). See tools/games/llb.py for the format of each entry.

  NORETURN       subroutines that pop their own return address (jump-table dispatchers)
  HLE            hand-written 68k equivalents of hot 6502 routines, keyed (bank, address), 7 = the fixed bank.
                 Exact: same RAM, same stack bytes left below S, same registers and flags. Proven by the checksum.
  HLE_FALLBACK   those whose text may branch to .orig
Found with the 1 kHz profiler (tools/prof.py) and the I/O counts of the frame model (field play, ticks 2000-2100).
"""
NORETURN = set()
HLE = {}
HLE_FALLBACK = set()

# $C36C: the PRG bank switch, "INC $1C; five times STA $FFFF / LSR; DEC $1C; RTS" (called ~40 times a tick in field
# play, also through $C345/$C34F/$C360, which push and pop the bank number). One step when the shift register is
# idle and A has no reset bit; else the translation (.orig). The register gets A & $1F, A ends shifted right 4
# (carry = bit 3), N and Z come from $1C (INC then DEC leave it as it was).
HLE[(7, 0xc36c)] = '''
    btst #7,d0
    bne .orig
    cmp.b #$10,_mmc_shift
    bne .orig
    moveq #$1f,d4
    and.b d0,d4
    bsr _set_prg
    lsr.b #4,d0
    tst.b $1c-$80(a5)'''
HLE_FALLBACK.add((7, 0xc36c))

# $C200: read both controllers twice ($C22F: strobe, 8 x ($4016, $4017) bit by bit into $01/$02), keep the old
# reading if the two differ, then $17/$18 = newly pressed buttons, $15/$16 = held. Port 2 reads $4017, always 0
# here. Effects worked out from $C200-$C253: $00 = $40 (the last $4017 read), $01/$03 = buttons (A in bit 7),
# $02/$04 = 0; the two JSRs to $C22F leave their return address $C20D below S. Returns A = new presses of pad 1,
# X = $FF, Y = buttons, N=1 Z=0, C=1 (the last CMP of two equal readings). A, X and Y stay zero-extended in
# d0/d1/d2: the translation indexes memory with them; V unchanged.
HLE[(7, 0xc200)] = '''
    moveq #0,d4
    move.b _nes_pad,d4
    move.b (_revtab,d4.w),d4
    move.b #$c2,-1(a2)
    move.b #$0d,-2(a2)
    move.b #$40,$00-$80(a5)
    move.b d4,$01-$80(a5)
    clr.b $02-$80(a5)
    move.b d4,$03-$80(a5)
    clr.b $04-$80(a5)
    moveq #0,d0
    move.b $15-$80(a5),d0
    eor.b d4,d0
    and.b d4,d0
    move.b d0,$17-$80(a5)
    clr.b $18-$80(a5)
    move.b d4,$15-$80(a5)
    clr.b $16-$80(a5)
    move.b #$ff,_pad_shift
    clr.b _pad_strobe
    moveq #0,d2
    move.b d4,d2
    move.l #$ff,d1
    tst.b d1
    ori.b #$10,ccr'''

# $8012 (bank 0) = JMP $87FD: the metasprite builder. A = sprite number; its list (pointer table at $A628) holds
# groups "count (bit 7 = end), x offset, count x (y offset, tile, attribute)": one column of sprites per group.
# x = offset (mirrored: ~offset - 7 when $25 bit 6) + $26, y = offset + $28 - 1 ($28 is decremented first),
# attribute EOR $25; OAM entries from X = $24 on, X left in $24. Returns A = the end byte (N=1 Z=0), Y = its index,
# C and V from the last y addition (C from ASL A when the list is empty). $00/$01 = list, $02 = 0 and $03 = the
# last x (or $28/$A6+C when empty). Guarded: the list must be in this bank, every count non-zero, Y not wrap.
HLE[(0, 0x8012)] = '''
    moveq #0,d7
    move.b d0,d7
    add.w d7,d7
    lea ($a628-$8000,a3),a0
    moveq #0,d6
    move.b 1(a0,d7.w),d6
    lsl.w #8,d6
    move.b (a0,d7.w),d6
    cmp.l #$8000,d6
    bcs .orig
    cmp.l #$bf00,d6
    bcc .orig
    lea (-$8000,a3,d6.l),a0
    move.l a0,a1
.v  moveq #0,d4
    move.b (a1),d4
    bmi.s .vok
    beq .orig
    lea 2(a1),a1
    adda.w d4,a1
    adda.w d4,a1
    adda.w d4,a1
    move.l a1,d4
    sub.l a0,d4
    cmp.l #250,d4
    bhi .orig
    bra.s .v
.vok
    btst #7,d0
    sne d3
    move.b #$28,$02-$80(a5)
    move.b #$a6,$03-$80(a5)
    tst.b d3
    beq.s .a6
    move.b #$a7,$03-$80(a5)
.a6 move.b d6,$00-$80(a5)
    lsr.w #8,d6
    move.b d6,$01-$80(a5)
    subq.b #1,$28-$80(a5)
    move.b $28-$80(a5),d6
    moveq #0,d1
    move.b $24-$80(a5),d1
    move.l a0,a1
.grp
    move.b (a1)+,d0
    bmi.s .end
    move.b d0,d4
    move.b (a1)+,d0
    btst #6,$25-$80(a5)
    beq.s .nm
    not.b d0
    subq.b #7,d0
.nm add.b $26-$80(a5),d0
    move.b d0,d7
    move.b d0,$03-$80(a5)
    clr.b $02-$80(a5)
.ent
    move.b (a1)+,d0
    add.b d6,d0
    scs d3
    svs d5
    move.b d0,($180,a5,d1.w)
    move.b (a1)+,($181,a5,d1.w)
    move.b (a1)+,d0
    move.b $25-$80(a5),d2
    eor.b d2,d0
    move.b d0,($182,a5,d1.w)
    move.b d7,($183,a5,d1.w)
    addq.b #4,d1
    subq.b #1,d4
    bne.s .ent
    bra.s .grp
.end
    move.b d1,$24-$80(a5)
    move.l a1,d2
    sub.l a0,d2
    subq.l #1,d2
    add.b d3,d3
    tst.b d0'''
HLE_FALLBACK.add((0, 0x8012))
