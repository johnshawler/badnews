/* shost.c - host only: runs the game logic and src/sound.c with a simulated Paula and writes the sound as a
 * WAV file (22050 Hz stereo, Paula's channels 0+3 left, 1+2 right), to check the NES sound without the emulator.
 *   cc -Itools/hostinc -Ikit -Isrc -DPAULA='(&paula)' tools/shost.c src/sound.c tools/shost_dmc.c src/logic.c src/nes.c src/run_c.c src/coro_host.c src/gen_*.c
 *   shost N out.wav       (N ticks of the bench input; one drawn frame per tick 6 in 5, as on a full-speed Amiga)
 */
#include <stdio.h>
#include <stdlib.h>
#include "exec/types.h"
#include "hardware/custom.h"
#include "nes.h"
#include "logic.h"
#include "sound.h"

struct Custom paula;
uint8_t nes_prg_data[0x20000], nes_chr_data[0x20000];
void *sys_alloc(ULONG size, ULONG f) { (void)f; return calloc(1, size); }

int main(int argc, char **argv)
{
    unsigned n = atoi(argv[1]), t, frame = 0; FILE *g, *w; double pos[4] = {0}; long samples = 0; int c, i;
    UWORD *lptr[4] = {0}; UWORD llen[4] = {0}; int dma_on[4] = {0};    /* what each channel plays: latched at the
                                                                         start of every loop, as Paula does */
    g = fopen("assets/prg.bin", "rb"); if (!g || fread(nes_prg_data, 1, 0x20000, g) != 0x20000) return 2; fclose(g);
    g = fopen("assets/chr.bin", "rb"); if (!g || fread(nes_chr_data, 1, 0x20000, g) != 0x20000) return 2; fclose(g);
    w = fopen(argv[2], "wb"); fseek(w, 44, SEEK_SET);
    game_init(); sound_load(); sound_start();
    for (t = 0; t < n; ) {
        int k = (frame % 5 == 4) ? 2 : 1;                       /* 60 ticks in 50 frames */
        while (k-- && t < n) { game_tick(game_bench_input(t)); t++; }
        sound_frame(); frame++;
        for (c = 0; c < 4; c++) {                               /* DMACON: a channel switched on restarts from its */
            if (paula.dmacon & (1 << c)) {                      /* registers; switched off it is silent            */
                if (paula.dmacon & 0x8000) { if (!dma_on[c]) { lptr[c] = paula.aud[c].ac_ptr; llen[c] = paula.aud[c].ac_len; pos[c] = 0; } dma_on[c] = 1; }
                else dma_on[c] = 0;
            }
        }
        paula.dmacon = 0;
        if (getenv("STATS") && frame % 50 == 0) printf("%3us vol %2d %2d %2d %2d per %4d %4d %4d %4d\n", frame / 50, paula.aud[0].ac_vol, paula.aud[1].ac_vol, paula.aud[2].ac_vol, paula.aud[3].ac_vol, paula.aud[0].ac_per, paula.aud[1].ac_per, paula.aud[2].ac_per, paula.aud[3].ac_per);
        for (i = 0; i < 441; i++) {                             /* 1/50 s at 22050 Hz */
            int lr[2] = {0, 0};
            for (c = 0; c < 4; c++) {
                struct AudChannel *a = &paula.aud[c];
                int len, v;
                if (!dma_on[c]) continue;
                if (!lptr[c]) { lptr[c] = a->ac_ptr; llen[c] = a->ac_len; }
                len = llen[c] * 2;
                if (!lptr[c] || !len || !a->ac_per) continue;
                v = ((signed char *)lptr[c])[(int)pos[c]] * (a->ac_vol > 64 ? 64 : a->ac_vol);
                lr[(c == 0 || c == 3) ? 0 : 1] += v;
                pos[c] += 3546895.0 / a->ac_per / 22050.0;
                if (pos[c] >= len) { pos[c] -= len; lptr[c] = a->ac_ptr; llen[c] = a->ac_len;   /* next loop: the registers now */
                    if (pos[c] >= llen[c] * 2) pos[c] = 0; }
            }
            for (c = 0; c < 2; c++) { int s = lr[c] * 2; short o = (short)(s > 32767 ? 32767 : s < -32768 ? -32768 : s); fputc(o & 255, w); fputc((o >> 8) & 255, w); }
            samples++;
        }
    }
    {   unsigned data = (unsigned)(samples * 4), rate = 22050; unsigned char h[44] = "RIFF____WAVEfmt \x10\0\0\0\1\0\2\0________\4\0\x10\0data____";
        unsigned v[4] = { data + 36, rate, rate * 4, data }; int off[4] = { 4, 24, 28, 40 };
        for (c = 0; c < 4; c++) for (i = 0; i < 4; i++) h[off[c] + i] = (unsigned char)(v[c] >> (8 * i));
        fseek(w, 0, SEEK_SET); fwrite(h, 1, 44, w); fclose(w); }
    printf("%ld samples\n", samples);
    return 0;
}
