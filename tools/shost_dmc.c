/* shost_dmc.c - host only: assets/dmc.bin for tools/shost.c (on the Amiga src/data.s links it into chip RAM). */
#include <stdio.h>
unsigned char nes_dmc[65536];
static int loaded = (int)sizeof nes_dmc;
__attribute__((constructor)) static void load(void)
{
    FILE *f = fopen("assets/dmc.bin", "rb");
    if (f) { loaded = (int)fread(nes_dmc, 1, sizeof nes_dmc, f); fclose(f); }
}
