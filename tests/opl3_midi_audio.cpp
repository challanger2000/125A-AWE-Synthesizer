#include "Opl3Midi.h"
#include <array>
#include <algorithm>
#include <cstdint>
#include <iostream>
using AWE125::Opl3Midi;
static bool ck(bool ok,const char* label) {
    std::cout<<(ok?"PASS: ":"FAIL: ")<<label<<'\n';return ok;
}
template<size_t N> static bool audible(const std::array<int16_t,N>& a) {
    return std::any_of(a.begin(),a.end(),[](int16_t x){return x!=0;});
}
int main() {
    bool ok=true;
    Opl3Midi whole(44100),split(44100);
    std::array<int16_t,8192> a{},b{};
    whole.NoteOn(0,69,115);split.NoteOn(0,69,115);
    whole.RenderBlock(a.data(),4096);
    split.RenderBlock(b.data(),777);
    split.RenderBlock(b.data()+1554,4096-777);
    ok&=ck(a==b&&audible(a),
        "MIDI note-on -> true FM register PCM, block-partition invariant");
    ok&=ck(whole.PressedVoices()==1,"one note occupies one OPL3 channel");
    whole.NoteOff(0,69);
    ok&=ck(whole.PressedVoices()==0,"matching note-off releases key");
    whole.NoteOn(1,60,100);whole.NoteOn(1,60,100);
    whole.NoteOff(1,60);
    ok&=ck(whole.PressedVoices()==1,"repeated notes pair independently");
    whole.ControlChange(1,64,127);
    whole.NoteOff(1,60);
    whole.ControlChange(1,64,0);
    ok&=ck(whole.PressedVoices()==0,"sustain holds then releases");
    Opl3Midi poly(48000);
    for(int i=0;i<18;++i)poly.NoteOn(0,static_cast<uint8_t>(48+i),100);
    ok&=ck(poly.PressedVoices()==18,"all 18 2-op FM voices available");
    poly.NoteOn(2,100,60);
    ok&=ck(poly.PressedVoices()==18,"19th note steals without overflow");
    std::array<int16_t,2048> chords{};
    poly.RenderBlock(chords.data(),1024);
    ok&=ck(audible(chords),"polyphonic FM renders nonzero stereo PCM");
    poly.AllNotesOff();
    ok&=ck(poly.PressedVoices()==0,"mode switching releases every FM key");

    Opl3Midi delayed(44100,128);
    delayed.NoteOn(0,69,127);
    std::array<int16_t,256> silence{},following{};
    delayed.RenderBlock(silence.data(),128);
    delayed.RenderBlock(following.data(),128);
    ok&=ck(!audible(silence)&&audible(following),
        "FM latency alignment to EMU8000 FIFO");

    Opl3Midi quiet(44100);
    std::array<int16_t,1024> empty{};
    quiet.RenderBlock(empty.data(),512);
    ok&=ck(!audible(empty),"unkeyed OPL3 silence");

    std::cout<<"NOT RUN: original Creative FM bank, CQM, DAW host, project recall\n";
    return ok?0:1;
}
