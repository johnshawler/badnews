; video68k.s - the two inner loops of src/video.c, in assembly (they run every frame and stay in the cache).
        section code,code
        xdef    _tile8,_spr_put
        xref    _video_plane,_video_flip

; void tile8(UBYTE *d __asm("a0"), const UBYTE *chr __asm("a1"), ULONG attr __asm("d0"))
; One 8x8 NES tile into 4 bitplanes, 64 bytes a line: planes 0-1 from the CHR tile (8 bytes plane 0,
; 8 bytes plane 1), planes 2-3 filled with the attribute bytes in attr bits 0-7 and 8-15; with attr bit 16,
; plane 2 is set where the tile has colour 0 instead (palette-0 tiles: their backdrop pixels use index 4).
_tile8: movem.l d2/a2-a4,-(sp)          ; unrolled: fixed offsets, no loop
        move.l  _video_plane,d2
        lea     (a0,d2.l),a2
        lea     (a2,d2.l),a3
        lea     (a3,d2.l),a4
        move.w  d0,d1
        lsr.w   #8,d1                   ; plane 3 byte
        btst    #16,d0
        bne     .z4
        move.b  8(a1),(a2)
        move.b  0(a1),(a0)
        move.b  d0,(a3)
        move.b  d1,(a4)
        move.b  9(a1),64(a2)
        move.b  1(a1),64(a0)
        move.b  d0,64(a3)
        move.b  d1,64(a4)
        move.b  10(a1),128(a2)
        move.b  2(a1),128(a0)
        move.b  d0,128(a3)
        move.b  d1,128(a4)
        move.b  11(a1),192(a2)
        move.b  3(a1),192(a0)
        move.b  d0,192(a3)
        move.b  d1,192(a4)
        move.b  12(a1),256(a2)
        move.b  4(a1),256(a0)
        move.b  d0,256(a3)
        move.b  d1,256(a4)
        move.b  13(a1),320(a2)
        move.b  5(a1),320(a0)
        move.b  d0,320(a3)
        move.b  d1,320(a4)
        move.b  14(a1),384(a2)
        move.b  6(a1),384(a0)
        move.b  d0,384(a3)
        move.b  d1,384(a4)
        move.b  15(a1),448(a2)
        move.b  7(a1),448(a0)
        move.b  d0,448(a3)
        move.b  d1,448(a4)
        movem.l (sp)+,d2/a2-a4
        rts
.z4                                     ; attr bit 16: plane 2 = the tile's colour-0 pixels (NES palette 0:
        move.b  8(a1),d2
        move.b  d2,(a2)
        or.b    0(a1),d2
        not.b   d2
        move.b  d2,(a3)
        move.b  0(a1),(a0)
        move.b  d1,(a4)
        move.b  9(a1),d2
        move.b  d2,64(a2)
        or.b    1(a1),d2
        not.b   d2
        move.b  d2,64(a3)
        move.b  1(a1),64(a0)
        move.b  d1,64(a4)
        move.b  10(a1),d2
        move.b  d2,128(a2)
        or.b    2(a1),d2
        not.b   d2
        move.b  d2,128(a3)
        move.b  2(a1),128(a0)
        move.b  d1,128(a4)
        move.b  11(a1),d2
        move.b  d2,192(a2)
        or.b    3(a1),d2
        not.b   d2
        move.b  d2,192(a3)
        move.b  3(a1),192(a0)
        move.b  d1,192(a4)
        move.b  12(a1),d2
        move.b  d2,256(a2)
        or.b    4(a1),d2
        not.b   d2
        move.b  d2,256(a3)
        move.b  4(a1),256(a0)
        move.b  d1,256(a4)
        move.b  13(a1),d2
        move.b  d2,320(a2)
        or.b    5(a1),d2
        not.b   d2
        move.b  d2,320(a3)
        move.b  5(a1),320(a0)
        move.b  d1,320(a4)
        move.b  14(a1),d2
        move.b  d2,384(a2)
        or.b    6(a1),d2
        not.b   d2
        move.b  d2,384(a3)
        move.b  6(a1),384(a0)
        move.b  d1,384(a4)
        move.b  15(a1),d2
        move.b  d2,448(a2)
        or.b    7(a1),d2
        not.b   d2
        move.b  d2,448(a3)
        move.b  7(a1),448(a0)
        move.b  d1,448(a4)                ; they show index 4, the backdrop; index 0 is the black border)
        movem.l (sp)+,d2/a2-a4
        rts

; void spr_put(UBYTE *e __asm("a0"), UBYTE *o __asm("a1"), const UBYTE *chr __asm("a2"), ULONG ctl __asm("d0"))
; One 8x8 NES sprite into the lines of a 64-pixel attached sprite pair, over what is there.
; e, o: the sprite's first line in the even and odd sprite's data (16 bytes a line: 8 plane A, 8 plane B).
; ctl: bits 0-5 x in the 64-pixel window, 8 h-flip, 9 v-flip, 10-11 NES sprite palette, 12 o is valid.
_spr_put:
        movem.l d2-d7/a2-a3,-(sp)       ; a2 too: gcc keeps values in it (callee-saved)
        move.l  d0,d7
        moveq   #0,d1
        move.b  d7,d1
        move.w  d1,d2
        lsr.w   #3,d2
        adda.w  d2,a0
        adda.w  d2,a1
        and.w   #7,d1
        beq     .al                     ; byte-aligned: no shifting (sprites of one metasprite, 8 pixels apart)
        moveq   #8,d6
        sub.w   d1,d6                   ; shift: 8 - x mod 8
        lea     _video_flip,a3
        moveq   #7,d5
        moveq   #1,d4
        btst    #9,d7
        beq.s   .row
        addq.l  #7,a2
        moveq   #-1,d4
.row    moveq   #0,d1
        move.b  (a2),d1
        moveq   #0,d2
        move.b  8(a2),d2
        btst    #8,d7
        beq.s   .nh
        move.b  (a3,d1.w),d1
        move.b  (a3,d2.w),d2
.nh     move.w  d1,d3
        or.w    d2,d3
        beq.s   .next
        lsl.w   d6,d1
        lsl.w   d6,d2
        lsl.w   d6,d3                   ; opaque pixels
        move.w  d3,d0
        not.w   d0                      ; keep mask
        and.w   d0,(a0)
        or.w    d1,(a0)
        and.w   d0,8(a0)
        or.w    d2,8(a0)
        btst    #12,d7
        beq.s   .next
        and.w   d0,(a1)
        btst    #10,d7
        beq.s   .p2
        or.w    d3,(a1)
.p2     and.w   d0,8(a1)
        btst    #11,d7
        beq.s   .next
        or.w    d3,8(a1)
.next   lea     16(a0),a0
        lea     16(a1),a1
        adda.w  d4,a2
        dbf     d5,.row
        movem.l (sp)+,d2-d7/a2-a3
        rts

; the byte-aligned case: d6/d1 = what the odd sprite's two planes get where the NES sprite is opaque
.al     lea     _video_flip,a3
        moveq   #7,d5
        moveq   #1,d4
        btst    #9,d7
        beq.s   .av
        addq.l  #7,a2
        moveq   #-1,d4
.av     btst    #12,d7
        beq.s   .a1                     ; no odd sprite (sprite 6): planes A and B only
        moveq   #0,d6
        btst    #10,d7
        beq.s   .ap
        moveq   #-1,d6
.ap     moveq   #0,d1
        btst    #11,d7
        beq.s   .ar
        moveq   #-1,d1
.ar     moveq   #0,d2
        move.b  (a2),d2
        moveq   #0,d3
        move.b  8(a2),d3
        btst    #8,d7
        beq.s   .ah
        move.b  (a3,d2.w),d2
        move.b  (a3,d3.w),d3
.ah     move.b  d2,d0
        or.b    d3,d0
        beq.s   .an
        move.b  d0,-(sp)
        not.b   d0                      ; keep mask
        and.b   d0,(a0)
        or.b    d2,(a0)
        and.b   d0,8(a0)
        or.b    d3,8(a0)
        and.b   d0,(a1)
        and.b   d0,8(a1)
        move.b  (sp)+,d0                ; opaque pixels
        move.b  d0,d2
        and.b   d6,d2
        or.b    d2,(a1)
        and.b   d1,d0
        or.b    d0,8(a1)
.an     lea     16(a0),a0
        lea     16(a1),a1
        adda.w  d4,a2
        dbf     d5,.ar
        movem.l (sp)+,d2-d7/a2-a3
        rts
.a1     moveq   #0,d2
        move.b  (a2),d2
        moveq   #0,d3
        move.b  8(a2),d3
        btst    #8,d7
        beq.s   .bh
        move.b  (a3,d2.w),d2
        move.b  (a3,d3.w),d3
.bh     move.b  d2,d0
        or.b    d3,d0
        beq.s   .bn
        not.b   d0
        and.b   d0,(a0)
        or.b    d2,(a0)
        and.b   d0,8(a0)
        or.b    d3,8(a0)
.bn     lea     16(a0),a0
        adda.w  d4,a2
        dbf     d5,.a1
        movem.l (sp)+,d2-d7/a2-a3
        rts


; int build_groups68(Group **gp __asm("a0"), Group *pool __asm("a1"), const UBYTE *oam __asm("a2"), int sh __asm("d0"))
; build_groups() of src/video.c in assembly, with exactly its decisions: each visible NES sprite (OAM order)
; joins the first of the last four clusters it touches if that stays <= 64 pixels wide and holds < 64 sprites,
; else starts a new one; then each cluster absorbs touching clusters among its next six (OAM order), the last
; cluster moving into a freed slot. Returns the number of clusters in gp[].
; Group (src/video.c): WORD x0, x1, y0, y1; UBYTE n, pal3only; UBYTE idx[64]  (74 bytes)
G_X0    equ     0
G_X1    equ     2
G_Y0    equ     4
G_Y1    equ     6
G_N     equ     8
G_P3    equ     9
G_IDX   equ     10
G_SIZE  equ     74
        xdef    _build_groups68
_build_groups68:
        movem.l d2-d7/a2-a6,-(sp)
        move.w  d0,-(sp)                ; sh at (sp)
        moveq   #0,d5                   ; n
        moveq   #0,d6                   ; i
.spr    moveq   #0,d1
        move.b  (a2),d1                 ; y
        cmp.b   #$ef,d1
        bcc     .nexts
        addq.w  #1,d1                   ; sy
        moveq   #0,d0
        move.b  3(a2),d0                ; x
        move.w  d0,d2
        addq.w  #8,d2                   ; x + 8
        move.w  d1,d3
        add.w   (sp),d3                 ; sy + sh
        lea     (a0,d5.w*4),a6          ; &gp[n]
        move.l  a6,a4
        moveq   #4,d4
.back   cmpa.l  a0,a4                   ; start at gp[max(0, n - 4)]
        beq.s   .cand
        subq.l  #4,a4
        subq.w  #1,d4
        bne.s   .back
.cand   cmpa.l  a6,a4
        bcc     .new
        move.l  (a4)+,a3
        move.w  G_X1(a3),d7
        addq.w  #1,d7
        cmp.w   d7,d0                   ; x > x1 + 1
        bgt.s   .cand
        move.w  G_X0(a3),d7
        subq.w  #1,d7
        cmp.w   d7,d2                   ; x + 8 < x0 - 1
        blt.s   .cand
        move.w  G_Y1(a3),d7
        addq.w  #1,d7
        cmp.w   d7,d1                   ; sy > y1 + 1
        bgt.s   .cand
        move.w  G_Y0(a3),d7
        subq.w  #1,d7
        cmp.w   d7,d3                   ; sy + sh < y0 - 1
        blt.s   .cand
        cmp.b   #64,G_N(a3)
        bcc.s   .cand
        move.w  G_X0(a3),d7             ; nx0 = min(x0, x)
        cmp.w   d0,d7
        ble.s   .m0
        move.w  d0,d7
.m0     move.w  G_X1(a3),d4             ; nx1 = max(x1, x + 8)
        cmp.w   d2,d4
        bge.s   .m1
        move.w  d2,d4
.m1     move.w  d4,a5
        sub.w   d7,d4
        cmp.w   #64,d4
        bgt.s   .cand
        move.w  d7,G_X0(a3)             ; join this cluster
        move.w  a5,G_X1(a3)
        cmp.w   G_Y0(a3),d1
        bge.s   .y0
        move.w  d1,G_Y0(a3)
.y0     cmp.w   G_Y1(a3),d3
        ble.s   .y1
        move.w  d3,G_Y1(a3)
.y1     moveq   #0,d4
        move.b  G_N(a3),d4
        move.b  d6,G_IDX(a3,d4.w)
        addq.b  #1,G_N(a3)
        move.b  2(a2),d4
        and.b   #3,d4
        cmp.b   #3,d4
        beq.s   .nexts
        clr.b   G_P3(a3)
        bra.s   .nexts
.new    move.l  a1,a3                   ; a new cluster from the pool
        lea     G_SIZE(a1),a1
        move.l  a3,(a6)
        addq.w  #1,d5
        move.w  d0,G_X0(a3)
        move.w  d2,G_X1(a3)
        move.w  d1,G_Y0(a3)
        move.w  d3,G_Y1(a3)
        move.b  #1,G_N(a3)
        move.b  d6,G_IDX(a3)
        move.b  2(a2),d4
        and.b   #3,d4
        cmp.b   #3,d4
        seq     G_P3(a3)
        and.b   #1,G_P3(a3)
.nexts  addq.l  #4,a2
        addq.w  #1,d6
        cmp.w   #64,d6
        blt     .spr

; merge pass: i in d6, j in d4
        moveq   #0,d6
.mi     cmp.w   d5,d6
        bge     .done
        move.l  (a0,d6.w*4),a3          ; a = gp[i]
        move.w  d6,d4
.mj     addq.w  #1,d4
        cmp.w   d5,d4
        bge     .ni
        move.w  d4,d7
        sub.w   d6,d7
        cmp.w   #6,d7
        bgt     .ni
        move.l  (a0,d4.w*4),a4          ; b = gp[j]
        move.w  G_X0(a3),d0             ; nx0
        cmp.w   G_X0(a4),d0
        ble.s   .n0
        move.w  G_X0(a4),d0
.n0     move.w  G_X1(a3),d1             ; nx1
        cmp.w   G_X1(a4),d1
        bge.s   .n1
        move.w  G_X1(a4),d1
.n1     move.w  d1,d2
        sub.w   d0,d2
        cmp.w   #64,d2
        bgt.s   .mj
        moveq   #0,d2
        move.b  G_N(a3),d2
        moveq   #0,d3
        move.b  G_N(a4),d3
        add.w   d2,d3
        cmp.w   #64,d3
        bgt.s   .mj
        move.w  G_Y1(a3),d7             ; b.y0 > a.y1 + 1
        addq.w  #1,d7
        cmp.w   G_Y0(a4),d7
        blt.s   .mj
        move.w  G_Y0(a3),d7             ; b.y1 < a.y0 - 1
        subq.w  #1,d7
        cmp.w   G_Y1(a4),d7
        bgt.s   .mj
        move.w  G_X1(a3),d7             ; b.x0 > a.x1 + 1
        addq.w  #1,d7
        cmp.w   G_X0(a4),d7
        blt.s   .mj
        move.w  G_X0(a3),d7             ; b.x1 < a.x0 - 1
        subq.w  #1,d7
        cmp.w   G_X1(a4),d7
        bgt     .mj
        move.w  d0,G_X0(a3)             ; merge b into a
        move.w  d1,G_X1(a3)
        move.w  G_Y0(a4),d7
        cmp.w   G_Y0(a3),d7
        bge.s   .n2
        move.w  d7,G_Y0(a3)
.n2     move.w  G_Y1(a4),d7
        cmp.w   G_Y1(a3),d7
        ble.s   .n3
        move.w  d7,G_Y1(a3)
.n3     lea     G_IDX(a3,d2.w),a5       ; a->idx[a->n ...] = b->idx[...]
        lea     G_IDX(a4),a6
        moveq   #0,d7
        move.b  G_N(a4),d7
        subq.w  #1,d7
.cp     move.b  (a6)+,(a5)+
        dbf     d7,.cp
        move.b  d3,G_N(a3)
        move.b  G_P3(a4),d7
        and.b   d7,G_P3(a3)
        subq.w  #1,d5                   ; gp[j] = gp[--n]; look at slot j again
        move.l  (a0,d5.w*4),(a0,d4.w*4)
        subq.w  #1,d4
        bra     .mj
.ni     addq.w  #1,d6
        bra     .mi
.done   move.l  d5,d0
        addq.l  #2,sp
        movem.l (sp)+,d2-d7/a2-a6
        rts
