#ifndef AWE125_P63_MIDI_WIRE_H
#define AWE125_P63_MIDI_WIRE_H
/*
 * Host -> Win95 COM1 framing; no SF2 interpretation, DSP, ROM, or FM engine.
 * Frame: A5 5A STATUS DATA1 DATA2 CHECKSUM (XOR of preceding MIDI bytes and 5A).
 * MIDI channel messages 80..EF; unused DATA2 must be zero for Cx and Dx.
 * This parser is ANSI C and can run in an original Windows 95 guest.
 */
#include <stdint.h>
typedef struct P63MidiDecoder {
    unsigned char state, status, d1, d2;
} P63MidiDecoder;

static void p63_midi_reset(P63MidiDecoder *d) {
    d->state=0;
    d->status=d->d1=d->d2=0;
}
static int p63_midi_valid(unsigned char status,unsigned char d1,unsigned char d2) {
    unsigned char op=(unsigned char)(status & 0xF0u);
    return status>=0x80u && status<=0xEFu &&
           d1<=0x7Fu && d2<=0x7Fu &&
           ((op!=0xC0u && op!=0xD0u) || d2==0u);
}
/* Returns 1 + packed WinMM short message when complete, 0 for more bytes,
 * -1 on corrupt/unsupported frame. The next valid sync may recover. */
static int p63_midi_feed(P63MidiDecoder *d,unsigned char byte,uint32_t *message) {
    switch(d->state) {
    case 0:
        if(byte==0xA5u)d->state=1;
        return 0;
    case 1:
        if(byte==0x5Au)d->state=2;
        else if(byte!=0xA5u)d->state=0;
        return 0;
    case 2:
        if(byte<0x80u || byte>0xEFu) {
            d->state=(byte==0xA5u)?1:0;
            return -1;
        }
        d->status=byte;d->state=3;return 0;
    case 3:
        if(byte>0x7Fu) {
            d->state=(byte==0xA5u)?1:0;
            return -1;
        }
        d->d1=byte;d->state=4;return 0;
    case 4:
        if(byte>0x7Fu) {
            d->state=(byte==0xA5u)?1:0;
            return -1;
        }
        d->d2=byte;d->state=5;return 0;
    default: {
        unsigned char expected=(unsigned char)(d->status^d->d1^d->d2^0x5Au);
        int valid=(byte==expected && p63_midi_valid(d->status,d->d1,d->d2));
        if(valid) {
            *message=(uint32_t)d->status | ((uint32_t)d->d1<<8) | ((uint32_t)d->d2<<16);
        }
        d->state=(valid?0:((byte==0xA5u)?1:0));
        return valid?1:-1;
    }
    }
}
#endif
