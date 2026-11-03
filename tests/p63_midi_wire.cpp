#include <cassert>
#include <cstdint>
#include "../src/bridge/P63MidiWire.h"

static int push(P63MidiDecoder& d, const unsigned char* bytes, unsigned size, uint32_t* result) {
    int count=0;
    for(unsigned i=0;i<size;++i) if(p63_midi_feed(&d,bytes[i],result)==1)++count;
    return count;
}
int main() {
    P63MidiDecoder decoder{};
    p63_midi_reset(&decoder);
    uint32_t msg=0;
    const unsigned char on[]={0xA5,0x5A,0x90,50,100,
        static_cast<unsigned char>(0x90 ^ 50 ^ 100 ^ 0x5A)};
    assert(push(decoder,on,6,&msg)==1);
    assert(msg == (uint32_t(0x90) | (uint32_t(50)<<8) | (uint32_t(100)<<16)));
    const unsigned char corrupt[]={0xA5,0x5A,0x80,50,0,0x00};
    assert(push(decoder,corrupt,6,&msg)==0);
    const unsigned char reset[]={0xFF,0xA5,0x5A,0xC0,7,0,
        static_cast<unsigned char>(0xC0 ^ 7 ^ 0x5A)};
    assert(push(decoder,reset,7,&msg)==1);
    assert((msg&255)==0xC0 && ((msg>>8)&255)==7);
    const unsigned char illegal[]={0xA5,0x5A,0xC0,7,1,
        static_cast<unsigned char>(0xC0 ^ 7 ^ 1 ^ 0x5A)};
    assert(push(decoder,illegal,6,&msg)==0);
    assert(push(decoder,on,6,&msg)==1);
    return 0;
}
