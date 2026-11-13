/* sound.c - the NES sound (APU) on Paula (Amiga only).
 *
 * The game writes the APU registers; src/nes.c keeps them in apu_reg[] and marks restarted notes in apu_trig.
 * Once per drawn frame this file runs the parts of the APU that change over time (length counters, volume
 * envelopes, the pulse sweep, the triangle's linear counter: the 240 Hz frame sequencer, four steps per NES
 * frame) and sets each Paula channel's period and volume. Paula plays one period of each waveform in a loop:
 *   pulse 1 -> channel 0 (left), pulse 2 -> channel 1 (right), triangle -> channel 2 (right), noise -> 3 (left)
 * DMC samples: converted on the host (tools/dmc.py, the list in tools/games/<game>.py) and linked into chip RAM;
 * a started sample takes Paula channel 3 from the noise for as long as it plays.
 * Nothing here changes the game state, so checksums are unaffected.
 * Paula's registers are written directly: the kit's ptplayer plays modules and one-shot samples, not tones.
 */
#include <proto/exec.h>
#include <exec/memory.h>
#include "sys.h"
#include "nes.h"
#include "logic.h"
#include "sound.h"

#ifndef PAULA                            /* the host harness tools/shost.c points this at a simulated Paula */
#define PAULA custom
#else
extern struct Custom paula;
#endif
#define PAULA_CLOCK 3546895UL           /* PAL */
#define NES_CLOCK   1789773UL
#define NOISE_LEN   4096                /* bytes of the long noise sequence */

static const UBYTE len_tab[32] = { 10,254,20,2,40,4,80,6,160,8,60,10,14,12,26,14,12,16,24,18,48,20,96,22,192,24,72,26,16,28,32,30 };
static const UWORD noise_per[16] = { 4,8,16,32,64,96,128,160,202,254,380,508,762,1016,2034,4068 };
static const UBYTE duty_seq[4] = { 0x40, 0x60, 0x78, 0x9f };   /* NES pulse duty steps, bit 7 = first step */

static BYTE *wave_pulse[4];             /* 8 samples each, chip RAM */
static BYTE *wave_tri;                  /* 16 samples */
static BYTE *wave_noise[2];             /* long and short LFSR sequences */

typedef struct { UBYTE len, env_vol, env_div, env_start, sweep_div, sweep_reload; UWORD timer; } Tone;
static Tone pulse[2], noise;
static UBYTE tri_len, tri_lin, tri_reload;
static ULONG last_frame;
static UBYTE on;
static UWORD cur_per[4], cur_vol[4];
static BYTE *cur_ptr[4];

extern UBYTE nes_dmc[];                 /* assets/dmc.bin: 16 entries of 16 bytes, then the samples (src/data.s) */
static BYTE *silence;                   /* 2 zero bytes: what channel 3 loops after a sample */
static UBYTE dmc_state;                 /* 0 channel 3 plays the noise, 1 its DMA is off, 2 sample started, 3 playing */
static const UBYTE *dmc_e;
static WORD dmc_ticks;                  /* ticks the sample still plays */

static const UBYTE *dmc_find(UBYTE addr, UBYTE len)
{
    int i;
    for (i = 0; i < 16; i++) {
        const UBYTE *e = nes_dmc + i * 16;
        if (!e[6] && !e[7] && !e[8] && !e[9]) break;              /* no more entries */
        if (e[0] == addr && e[1] == len) return e;
    }
    return 0;
}
#define BE16(p) ((UWORD)((p)[0] << 8 | (p)[1]))
#define BE32(p) ((ULONG)(p)[0] << 24 | (ULONG)(p)[1] << 16 | (ULONG)(p)[2] << 8 | (p)[3])

int sound_load(void)
{
    int d, i;
    ULONG lfsr;
    for (d = 0; d < 4; d++) {
        if (!(wave_pulse[d] = sys_alloc(8, MEMF_CHIP))) return 0;
        for (i = 0; i < 8; i++) wave_pulse[d][i] = (duty_seq[d] & (0x80 >> i)) ? 60 : -60;
    }
    if (!(silence = sys_alloc(4, MEMF_CHIP | MEMF_CLEAR))) return 0;
    if (!(wave_tri = sys_alloc(16, MEMF_CHIP))) return 0;
    for (i = 0; i < 16; i++) wave_tri[i] = (BYTE)((i < 8 ? 15 - 2 * i : 2 * i - 17) * 8);
    for (d = 0; d < 2; d++) {                   /* NES noise: 15-bit LFSR, feedback from bit 1 (long) or bit 6 */
        if (!(wave_noise[d] = sys_alloc(NOISE_LEN, MEMF_CHIP))) return 0;
        lfsr = 1;
        for (i = 0; i < NOISE_LEN; i++) {
            ULONG fb = (lfsr ^ (lfsr >> (d ? 6 : 1))) & 1;
            lfsr = (lfsr >> 1) | (fb << 14);
            wave_noise[d][i] = (lfsr & 1) ? -50 : 50;
        }
    }
    return 1;
}

static void set_chan(int n, BYTE *ptr, UWORD words, UWORD per, UWORD vol)
{
    if (per < 124) per = 124;                   /* Paula's fastest DMA rate */
    if (ptr != cur_ptr[n]) { PAULA->aud[n].ac_ptr = (UWORD *)ptr; PAULA->aud[n].ac_len = words; cur_ptr[n] = ptr; }
    if (per != cur_per[n]) { PAULA->aud[n].ac_per = per; cur_per[n] = per; }
    if (vol != cur_vol[n]) { PAULA->aud[n].ac_vol = vol; cur_vol[n] = vol; }
}

void sound_start(void)
{
    int n;
    for (n = 0; n < 4; n++) { cur_ptr[n] = 0; cur_per[n] = 0; cur_vol[n] = 0xffff; }
    set_chan(0, wave_pulse[2], 4, 400, 0);
    set_chan(1, wave_pulse[2], 4, 400, 0);
    set_chan(2, wave_tri, 8, 400, 0);
    set_chan(3, wave_noise[0], NOISE_LEN / 2, 400, 0);
    PAULA->dmacon = DMAF_SETCLR | DMAF_AUD0 | DMAF_AUD1 | DMAF_AUD2 | DMAF_AUD3;
    last_frame = logic_frames;
    dmc_state = 0;
    on = 1;
}

void sound_stop(void)
{
    int n;
    for (n = 0; n < 4; n++) PAULA->aud[n].ac_vol = 0;
    PAULA->dmacon = DMAF_AUD0 | DMAF_AUD1 | DMAF_AUD2 | DMAF_AUD3;
    on = 0;
}

static void envelope(Tone *t, UBYTE r0)
{
    if (t->env_start) { t->env_start = 0; t->env_vol = 15; t->env_div = r0 & 15; return; }
    if (t->env_div) { t->env_div--; return; }
    t->env_div = r0 & 15;
    if (t->env_vol) t->env_vol--;
    else if (r0 & 0x20) t->env_vol = 15;        /* loop */
}

static UWORD sweep_target(int n)
{
    UBYTE r1 = apu_reg[n * 4 + 1];
    UWORD t = pulse[n].timer, ch = (UWORD)(t >> (r1 & 7));
    if (r1 & 8) return (UWORD)(t - ch - (n == 0 ? 1 : 0));
    return (UWORD)(t + ch);
}

static void quarter(int half)
{
    int n;
    for (n = 0; n < 2; n++) envelope(&pulse[n], apu_reg[n * 4]);
    envelope(&noise, apu_reg[12]);
    if (tri_reload) tri_lin = apu_reg[8] & 0x7f;
    else if (tri_lin) tri_lin--;
    if (!(apu_reg[8] & 0x80)) tri_reload = 0;
    if (!half) return;
    for (n = 0; n < 2; n++) {
        UBYTE r0 = apu_reg[n * 4], r1 = apu_reg[n * 4 + 1];
        if (!(r0 & 0x20) && pulse[n].len) pulse[n].len--;
        if (pulse[n].sweep_div == 0 && (r1 & 0x80) && (r1 & 7) && pulse[n].timer >= 8) {
            UWORD tg = sweep_target(n);
            if (tg <= 0x7ff) pulse[n].timer = tg;
        }
        if (pulse[n].sweep_div == 0 || pulse[n].sweep_reload) { pulse[n].sweep_div = (r1 >> 4) & 7; pulse[n].sweep_reload = 0; }
        else pulse[n].sweep_div--;
    }
    if (!(apu_reg[8] & 0x80) && tri_len) tri_len--;
    if (!(apu_reg[12] & 0x20) && noise.len) noise.len--;
}

void sound_frame(void)
{
    ULONG ticks = logic_frames - last_frame;
    UBYTE en = apu_reg[0x15], trig = apu_trig;
    int n, q;
    if (!on) return;
    last_frame = logic_frames;
    apu_trig = 0;
    /* restarted notes */
    for (n = 0; n < 2; n++) {
        pulse[n].timer = (UWORD)(apu_reg[n * 4 + 2] | ((apu_reg[n * 4 + 3] & 7) << 8));
        if (trig & (1 << n)) { pulse[n].len = len_tab[apu_reg[n * 4 + 3] >> 3]; pulse[n].env_start = 1; }
    }
    if (trig & 4) { tri_len = len_tab[apu_reg[11] >> 3]; tri_reload = 1; }
    if (trig & 8) { noise.len = len_tab[apu_reg[15] >> 3]; noise.env_start = 1; }
    if (!(en & 1)) pulse[0].len = 0;
    if (!(en & 2)) pulse[1].len = 0;
    if (!(en & 4)) tri_len = 0;
    if (!(en & 8)) noise.len = 0;
    if (ticks > 8) ticks = 8;
    for (q = 0; q < (int)ticks * 4; q++) quarter(q & 1);

    for (n = 0; n < 2; n++) {
        UBYTE r0 = apu_reg[n * 4];
        UWORD t = pulse[n].timer, vol = (r0 & 0x10) ? (r0 & 15) : pulse[n].env_vol;
        int mute = !pulse[n].len || t < 8 || ((apu_reg[n * 4 + 1] & 0x88) == 0x80 && sweep_target(n) > 0x7ff);
        /* 8 samples a NES pulse period: Paula period = PAULA_CLOCK * 16 * (t + 1) / (NES_CLOCK * 8) */
        set_chan(n, wave_pulse[r0 >> 6], 4, (UWORD)((PAULA_CLOCK * 2 / 1000 * (t + 1)) / (NES_CLOCK / 1000)), mute ? 0 : (UWORD)(vol * 3));
    }
    {   UWORD t = (UWORD)(apu_reg[10] | ((apu_reg[11] & 7) << 8));
        int mute = !tri_len || !tri_lin || t < 2;
        /* 16 samples a period (the NES has 32 steps) */
        set_chan(2, wave_tri, 8, (UWORD)((PAULA_CLOCK * 2 / 1000 * (t + 1)) / (NES_CLOCK / 1000)), mute ? 0 : 40);
    }
    /* DMC: a sample started ($4015 bit 4) takes channel 3: DMA off this frame, the sample from the next one, then
       silence as its loop; the channel goes back to the noise when the sample's time is over */
    switch (dmc_state) {
    case 1:
        PAULA->aud[3].ac_ptr = (UWORD *)(nes_dmc + BE32(dmc_e + 4)); PAULA->aud[3].ac_len = BE16(dmc_e + 8);
        PAULA->aud[3].ac_per = BE16(dmc_e + 10); PAULA->aud[3].ac_vol = 50;
        PAULA->dmacon = DMAF_SETCLR | DMAF_AUD3;
        dmc_ticks = (WORD)(BE16(dmc_e + 12) * 6 / 5 + 1);
        dmc_state = 2;
        break;
    case 2:
        PAULA->aud[3].ac_ptr = (UWORD *)silence; PAULA->aud[3].ac_len = 1;
        dmc_state = 3;
        /* fall through */
    case 3:
        dmc_ticks -= (WORD)ticks;
        if (dmc_ticks <= 0 || !(en & 0x10)) { dmc_state = 0; cur_ptr[3] = 0; cur_per[3] = 0; cur_vol[3] = 0xffff; }
        break;
    }
    if ((trig & 0x10) && (en & 0x10) && (dmc_e = dmc_find(apu_reg[0x12], apu_reg[0x13])) != 0) {
        PAULA->dmacon = DMAF_AUD3;
        dmc_state = 1;
    }
    if (dmc_state == 0 && !cur_ptr[3]) PAULA->dmacon = DMAF_SETCLR | DMAF_AUD3;    /* back from a sample */
    if (dmc_state == 0) {   UBYTE r0 = apu_reg[12], r2 = apu_reg[14];
        UWORD vol = (r0 & 0x10) ? (r0 & 15) : noise.env_vol;
        /* one sample per LFSR step */
        set_chan(3, wave_noise[(r2 & 0x80) ? 1 : 0], NOISE_LEN / 2,
                 (UWORD)((PAULA_CLOCK / 1000 * noise_per[r2 & 15]) / (NES_CLOCK / 1000)), noise.len ? (UWORD)(vol * 2) : 0);
    }
}
