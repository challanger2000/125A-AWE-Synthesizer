#include "MidiControlMapping.h"
#include <array>
#include <cmath>
#include <iostream>
using namespace AWE125::MidiControlMapping;
static bool check(bool ok,const char* text) {
    std::cout<<(ok?"PASS: ":"FAIL: ")<<text<<"\n";return ok;
}
int main(){
    bool ok=true;
    constexpr std::array<int,17> expected={0,1,6,7,10,11,32,64,91,93,100,101,120,121,123,128,129};
    for(size_t i=0;i<expected.size();++i) {
        ok&=check(Index(expected[i])==int(i),"controller number has stable slot");
        for(int ch=0;ch<16;++ch) {
            const auto id=ParamID(ch,uint32_t(i));
            const auto d=Decode(id);
            ok&=d.valid&&d.channel==ch&&d.number==expected[i];
        }
    }
    ok&=check(!Decode(1000).valid&&!Decode(1002).valid&&
              !Decode(1100).valid&&!Decode(1111).valid&&
              !Decode(1999).valid&&!Decode(ParamID(15,31)).valid,
              "MIDI mapping never collides with existing host parameter IDs");
    ok&=check(Index(64)>=0&&Index(129)>=0&&Index(128)>=0,
              "sustain pitch-bend and aftertouch are mappable");
    ok&=check(Index(99)<0&&Index(130)<0,
              "unsupported and special controller assignments are rejected");
    ok&=check(Byte(0.)==0&&Byte(1.)==127&&Byte(.5)==64,
              "CC 7-bit conversion covers MIDI endpoints");
    ok&=check(PitchBend(0.)==-8192&&PitchBend(.5)==0&&PitchBend(1.)==8191,
              "pitch bend is signed and centered at host normalized 0.5");
    ok&=check(InitialNormalized(kControls[Index(7)])==100./127.&&
              InitialNormalized(kControls[Index(11)])==1.&&
              InitialNormalized(kControls[Index(129)])==.5,
              "per-channel MIDI defaults match actual Synth startup");
    std::cout<<(ok?"P118_MIDI_MAPPING_PASS":"P118_MIDI_MAPPING_FAIL")<<"\n";
    return ok?0:1;
}
