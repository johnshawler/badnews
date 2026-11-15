/* play.c - host only: play the game with scripted input, to reach a scene the bench never shows (a crash a
 * player found, a game mode the bench does not play). Writes pictures (host_render) and stops at the first
 * untranslated address, which is what crashes the Amiga build.
 *   cc -Itools/hostinc -Ikit -Isrc -o out/play tools/play.c src/host_render.c <HOST_TEST sources but host_test.c>
 *   play N "t0-t1:mask t0-t1:mask ..." [t1,t2,... pictures]     masks: logic.h IN_* bits, in hex
 *   (RIGHT 1, LEFT 2, DOWN 4, UP 8, A 10, B 20, START 40, SELECT 80)
 *   EVERY=k  every k ticks: print the tick, the input and the checksum
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nes.h"
#include "logic.h"
void host_render(const char *path);
uint8_t nes_prg_data[0x20000], nes_chr_data[0x20000];

static unsigned seg0[8192], seg1[8192], segm[8192], nseg;
static unsigned input(unsigned t)
{
    unsigned i, m = 0;
    for (i = 0; i < nseg; i++) if (t >= seg0[i] && t <= seg1[i]) m |= segm[i];
    return m;
}

int main(int argc, char **argv)
{
    unsigned n = (unsigned)atoi(argv[1]), t, every = getenv("EVERY") ? (unsigned)atoi(getenv("EVERY")) : 0;
    char *p = argc > 2 ? argv[2] : "", list[8192], key[32], name[64];
    FILE *f;
    while (*p && nseg < 8192) {
        unsigned a, b, m; int k;
        if (sscanf(p, "%u-%u:%x%n", &a, &b, &m, &k) != 3) break;
        seg0[nseg] = a; seg1[nseg] = b; segm[nseg] = m; nseg++;
        p += k; while (*p == ' ' || *p == ',') p++;
    }
    snprintf(list, sizeof list, ",%s,", argc > 3 ? argv[3] : "");
    f = fopen("assets/prg.bin", "rb"); if (!f || fread(nes_prg_data, 1, 0x20000, f) != 0x20000) return 2; fclose(f);
    f = fopen("assets/chr.bin", "rb"); if (!f || fread(nes_chr_data, 1, 0x20000, f) != 0x20000) return 2; fclose(f);
    game_init();
    for (t = 0; t < n; t++) {
        game_tick((unsigned short)input(t));
        if (every && (t + 1) % every == 0) printf("tick %u in %02x checksum %08x\n", t + 1, input(t), (unsigned)game_checksum());
        snprintf(key, sizeof key, ",%u,", t + 1);
        if (strstr(list, key)) { snprintf(name, sizeof name, "play_%05u.ppm", t + 1); host_render(name); }
        if (nes_fatal_why) { printf("STOPPED at tick %u: reason %d at %04x\n", t + 1, nes_fatal_why, nes_fatal_pc); return 1; }
    }
    printf("ticks=%u checksum=%08x\n", n, (unsigned)game_checksum());
    return 0;
}
